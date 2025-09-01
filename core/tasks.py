from celery import shared_task
from .models import Factura
from . import sri_services
import time
import logging
from django.core.mail import EmailMessage
from django.template.loader import render_to_string
from weasyprint import HTML
from django.conf import settings
import os
from lxml import etree

logger = logging.getLogger(__name__)

def validar_xml_xsd(xml_bytes, xsd_path):
    """
    Valida el XML contra un XSD específico.
    """
    try:
        schema_doc = etree.parse(xsd_path)
        schema = etree.XMLSchema(schema_doc)
        xml_doc = etree.fromstring(xml_bytes)
        schema.assertValid(xml_doc)
        return True, None
    except Exception as e:
        return False, str(e)


@shared_task
def procesar_factura_electronica_task(factura_id):
    factura = None
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

        # 3. Validar contra XSD ANTES de enviar al SRI
        ruta_xsd = os.path.join(settings.BASE_DIR, "static", "xsd", "factura_V1.1.0.xsd")
        es_valido, error_xsd = validar_xml_xsd(xml_firmado_bytes, ruta_xsd)
        if not es_valido:
            factura.estado_sri = 'R'
            factura.sri_error = f"Error validando XML contra XSD: {error_xsd}"
            factura.save()
            return f"Factura {factura_id} rechazada por XSD: {error_xsd}"

        # 4. Guardar estado
        factura.save() 

        # 5. Enviar a SRI
        respuesta_recepcion = sri_services.enviar_comprobante_sri(xml_firmado_bytes)
        
        if respuesta_recepcion['estado'] == 'RECIBIDA':
            time.sleep(3)
            respuesta_autorizacion = sri_services.consultar_autorizacion_sri(factura.clave_acceso)
            
            factura.estado_sri = respuesta_autorizacion['estado']
            if respuesta_autorizacion['estado'] == 'A':
                factura.fecha_autorizacion = respuesta_autorizacion['fecha_autorizacion']
                factura.xml_autorizado = respuesta_autorizacion['xml_autorizado']
                factura.sri_error = None
            elif respuesta_autorizacion['estado'] == 'R':
                factura.sri_error = respuesta_autorizacion.get('mensaje', 'Error desconocido.')
            
            factura.save()
            return f"Factura {factura_id} procesada. Estado: {factura.get_estado_sri_display()}"

    except Exception as e:
        if factura:
            factura.estado_sri = 'R'
            factura.sri_error = str(e)
            factura.save()
        return f"Error procesando factura {factura_id}: {e}"

@shared_task 
def reenviar_factura_email_task(factura_id): 
    try: 
        factura = Factura.objects.get(pk=factura_id) 
        # 1. Generar el PDF en memoria 
        html_string = render_to_string('venta_pdf.html', {'venta': factura}) 
        pdf_file = HTML(string=html_string).write_pdf() 
        # 2. Preparar el contenido del correo 
        subject = f"Comprobante Electrónico: Factura {factura.secuencial}" 
        body = render_to_string('email_factura.html', {'factura': factura}) 
        email = EmailMessage( subject, body, factura.empresa.email_remitente,[factura.cliente.email]) 
        email.content_subtype = "html" # El cuerpo del correo es HTML 
        # 3. Adjuntar el PDF y el XML autorizado 
        email.attach(f'factura_{factura.secuencial}.pdf', pdf_file, 'application/pdf') 
        email.attach(f'factura_{factura.secuencial}.xml', factura.xml_autorizado, 'application/xml') 
        # 4. Enviar el correo 
        email.send() 
        return f"Correo de factura {factura_id} enviado exitosamente a {factura.cliente.email}." 
    except Exception as e: 
        return f"Error al enviar correo para factura {factura_id}: {str(e)}"