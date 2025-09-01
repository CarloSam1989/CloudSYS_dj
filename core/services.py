# Ubicación: core/services.py

from django.db import transaction
from decimal import Decimal
from . import sri_services
from .models import Factura, FacturaDetalle

@transaction.atomic
def crear_nueva_venta(factura_data, detalles_data, empresa, usuario):
    """
    Servicio para crear una nueva factura, sus detalles y actualizar el stock.
    Maneja toda la lógica de negocio en una transacción segura.
    """
    # 1. Crear la instancia de la factura (aún sin guardar)
    factura = Factura(**factura_data)
    factura.empresa = empresa
    factura.usuario = usuario
    factura.ambiente = '1'  # Ambiente de Pruebas
    factura.tipo_emision = '1' # Emisión Normal
    
    # 2. Procesar detalles para calcular totales
    total_sin_impuestos = Decimal('0.00')
    total_iva = Decimal('0.00')
    iva_rate = Decimal('0.15')         # Tasa de IVA ajustada al 14%
    codigo_porcentaje_iva = "4" 
   
    detalles_a_crear = []
    for data in detalles_data:
        detalle = FacturaDetalle(**data)
        subtotal_linea = (detalle.cantidad * detalle.precio_unitario).quantize(Decimal('0.01'))
        detalle.precio_total_sin_impuesto = subtotal_linea
        total_sin_impuestos += subtotal_linea

        if detalle.producto.maneja_iva:
            valor_iva_linea = (subtotal_linea * iva_rate).quantize(Decimal('0.01'))
            total_iva += valor_iva_linea
            detalle.impuestos = {"impuestos": [{"codigo": "2", "codigoPorcentaje": codigo_porcentaje_iva, "baseImponible": f"{subtotal_linea:.2f}", "valor": f"{valor_iva_linea:.2f}"}]}
        else:
            detalle.impuestos = {"impuestos": []}
        
        detalles_a_crear.append(detalle)

    # 3. Asignar totales a la factura
    factura.total_sin_impuestos = total_sin_impuestos
    factura.importe_total = total_sin_impuestos + total_iva
    
    if total_iva > 0:
        factura.total_con_impuestos = {"totalImpuesto": [{"codigo": "2", "codigoPorcentaje": codigo_porcentaje_iva, "baseImponible": f"{total_sin_impuestos:.2f}", "valor": f"{total_iva:.2f}"}]}
    else:
        factura.total_con_impuestos = {"totalImpuesto": []}

    # 4. Generar la clave de acceso
    punto_venta = factura.punto_venta
    secuencial_str = str(punto_venta.secuencial_factura).zfill(9)
    fecha_str = factura.fecha_emision.strftime('%d%m%Y')
    
    clave_sin_dv = (
        f"{fecha_str}"
        f"01"  # Cód. Doc: Factura
        f"{empresa.ruc}"
        f"{factura.ambiente}"
        f"{punto_venta.codigo_establecimiento}{punto_venta.codigo_punto_emision}"
        f"{secuencial_str}"
        f"12345678"  # Código numérico (puede ser aleatorio)
        f"{factura.tipo_emision}"
    )
    dv = sri_services.calcular_digito_verificador(clave_sin_dv)
    factura.clave_acceso = f"{clave_sin_dv}{dv}"
    factura.secuencial = secuencial_str

    # 5. Determinar estado de pago
    if factura.metodo_pago.es_contado:
        factura.estado_pago = 'C'  # Pagada
    else:
        factura.estado_pago = 'P'  # Pendiente

    # 6. Guardar todo en la base de datos
    factura.save()  # Guarda la factura para obtener un ID

    for detalle in detalles_a_crear:
        detalle.factura = factura
        detalle.save()
        
        # Actualizar stock del producto
        producto = detalle.producto
        producto.stock -= detalle.cantidad
        producto.save(update_fields=['stock'])

    # 7. Actualizar el secuencial para la próxima factura
    punto_venta.secuencial_factura += 1
    punto_venta.save(update_fields=['secuencial_factura'])

    return factura