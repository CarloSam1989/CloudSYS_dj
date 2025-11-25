# tasks.py

from celery import shared_task, Task
from .models import Factura
from . import sri_services
import logging
from django.core.mail import EmailMessage
from django.template.loader import render_to_string
from weasyprint import HTML
from django.conf import settings
import os
from lxml import etree

logger = logging.getLogger(__name__)

# --- Función de validación (sin cambios, está perfecta) ---
def validar_xml_xsd(xml_bytes, xsd_path):
    try:
        schema_doc = etree.parse(xsd_path)
        schema = etree.XMLSchema(schema_doc)
        xml_doc = etree.fromstring(xml_bytes)
        schema.assertValid(xml_doc)
        return True, None
    except Exception as e:
        return False, str(e)

# --- TAREA 1: Enviar la factura al SRI ---
@shared_task(bind=True, max_retries=3, default_retry_delay=60) # bind=True para acceder a 'self', y reintentos automáticos
def enviar_factura_sri_task(self, factura_id):
    """
    Genera, firma, valida y envía el XML al SRI.
    Si el SRI la recibe, agenda la tarea de consulta de autorización.
    """
    try:
        factura = Factura.objects.get(pk=factura_id)
        empresa = factura.empresa

        # 1. Generar XML
        xml_generado_bytes = sri_services.generar_xml_factura(factura)
        factura.xml_generado = xml_generado_bytes.decode('utf-8')

        # 2. Firmar XML
        p12_path = empresa.firma_electronica.path
        p12_password = empresa.clave_firma
        xml_firmado_bytes = sri_services.firmar_xml(xml_generado_bytes, p12_path, p12_password)
        factura.xml_firmado = xml_firmado_bytes.decode('utf-8')

        # 3. Validar contra XSD
        ruta_xsd = os.path.join(settings.BASE_DIR, "static", "xsd", "factura_V1.1.0.xsd")
        es_valido, error_xsd = validar_xml_xsd(xml_firmado_bytes, ruta_xsd)
        if not es_valido:
            factura.estado_sri = 'R'
            factura.sri_error = f"Error validando XML contra XSD: {error_xsd}"
            factura.save()
            return f"Factura {factura_id} rechazada por XSD: {error_xsd}"
        
        # 4. Enviar a SRI
        respuesta_recepcion = sri_services.enviar_comprobante_sri(xml_firmado_bytes)
        
        if respuesta_recepcion['estado'] == 'RECIBIDA':
            factura.estado_sri = 'P' # 'P' de 'Procesando' o 'Pendiente de autorización'
            factura.sri_error = None
            factura.save()
            
            # ¡CLAVE! Agendamos la siguiente tarea para que se ejecute en 2 minutos
            consultar_autorizacion_sri_task.apply_async(args=[factura_id], countdown=120)
            return f"Factura {factura_id} RECIBIDA por el SRI. Se consultará autorización."
        else:
            # Si el SRI devuelve DEVUELTA, es un error que guardamos
            factura.estado_sri = 'R'
            factura.sri_error = respuesta_recepcion.get('mensaje', 'El SRI devolvió la factura sin un mensaje claro.')
            factura.save()
            return f"Factura {factura_id} DEVUELTA por el SRI."

    except Factura.DoesNotExist:
        logger.error(f"Intento de procesar factura con ID {factura_id} que no existe.")
        return f"Factura con ID {factura_id} no encontrada."
    except Exception as e:
        # Si hay un error de red o similar, Celery reintentará la tarea
        logger.error(f"Error en enviar_factura_sri_task para factura {factura_id}: {e}")
        raise self.retry(exc=e)


# --- TAREA 2: Consultar la autorización en el SRI ---
@shared_task(bind=True, max_retries=5, default_retry_delay=300) # Reintenta 5 veces, cada 5 minutos
def consultar_autorizacion_sri_task(self, factura_id):
    """
    Consulta al SRI el estado de una factura ya recibida.
    Si es autorizada, se puede encadenar el envío de email.
    """
    try:
        factura = Factura.objects.get(pk=factura_id)
        respuesta_autorizacion = sri_services.consultar_autorizacion_sri(factura.clave_acceso)
        
        estado = respuesta_autorizacion['estado']

        if estado == 'A': # Autorizado
            factura.estado_sri = 'A'
            factura.fecha_autorizacion = respuesta_autorizacion['fecha_autorizacion']
            factura.xml_autorizado = respuesta_autorizacion['xml_autorizado']
            factura.sri_error = None
            factura.save()

            # Opcional pero recomendado: Llama a la tarea de email desde aquí
            enviar_factura_email_task.delay(factura.id)

            return f"Factura {factura_id} AUTORIZADA."
        elif estado == 'R': # Rechazado
            factura.estado_sri = 'R'
            factura.sri_error = respuesta_autorizacion.get('mensaje', 'SRI: Rechazado sin mensaje.')
            factura.save()
            return f"Factura {factura_id} RECHAZADA por el SRI."
        else:
            # Si el estado no es 'A' ni 'R', probablemente sigue en proceso. Reintentamos.
            raise self.retry(countdown=180) # Reintentamos en 3 minutos

    except Factura.DoesNotExist:
        logger.error(f"Intento de consultar autorización de factura {factura_id} que no existe.")
        return f"Factura con ID {factura_id} no encontrada."
    except Exception as e:
        logger.error(f"Error en consultar_autorizacion_sri_task para factura {factura_id}: {e}")
        raise self.retry(exc=e)


# --- TAREA 3: Enviar el email (con reintentos) ---
@shared_task(bind=True, max_retries=3, default_retry_delay=120) # Reintenta si falla el servidor de correo
def enviar_factura_email_task(self, factura_id):
    try:
        factura = Factura.objects.get(pk=factura_id, estado_sri='A') # Asegurarnos que solo se envíen las autorizadas
        
        html_string = render_to_string('venta_pdf.html', {'venta': factura})
        pdf_file = HTML(string=html_string).write_pdf()
        
        subject = f"Comprobante Electrónico: Factura {factura.secuencial}"
        body = render_to_string('email_factura.html', {'factura': factura})
        
        email = EmailMessage(
            subject,
            body,
            factura.empresa.email_remitente,
            [factura.cliente.email]
        )
        email.content_subtype = "html"
        email.attach(f'factura_{factura.secuencial}.pdf', pdf_file, 'application/pdf')
        email.attach(f'factura_{factura.secuencial}.xml', factura.xml_autorizado, 'application/xml')
        
        email.send()
        
        return f"Correo de factura {factura_id} enviado a {factura.cliente.email}."
    except Factura.DoesNotExist:
        logger.warning(f"Se intentó enviar email de la factura {factura_id} pero no se encontró o no está autorizada.")
        return f"No se envió email: Factura {factura_id} no encontrada o no autorizada."
    except Exception as e:
        logger.error(f"Error al enviar correo para factura {factura_id}: {e}")
        raise self.retry(exc=e)