import base64
from datetime import datetime
from lxml import etree
import zeep

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.serialization import pkcs12, Encoding

# ==============================================================================
# CONSTANTES
# ==============================================================================
URL_RECEPCION_PRUEBAS = "https://celcer.sri.gob.ec/comprobantes-electronicos-ws/RecepcionComprobantesOffline?wsdl"
URL_AUTORIZACION_PRUEBAS = "https://celcer.sri.gob.ec/comprobantes-electronicos-ws/AutorizacionComprobantesOffline?wsdl"

# ==============================================================================
# FUNCIONES AUXILIARES
# ==============================================================================
def determinar_tipo_identificacion(identificacion):
    if len(identificacion) == 13: return '04'
    elif len(identificacion) == 10: return '05'
    elif identificacion == '9999999999999': return '07'
    else: return '06'

def calcular_digito_verificador(numero):
    factores = [2, 3, 4, 5, 6, 7] * (len(numero) // 6 + 1)
    suma = sum(int(digito) * factor for digito, factor in zip(reversed(numero), factores))
    resultado = 11 - (suma % 11)
    if resultado == 11: return 0
    if resultado == 10: return 1
    return resultado

# ==============================================================================
# GENERACIÓN DE XML
# ==============================================================================
def generar_xml_factura(factura):
    factura_xml = etree.Element('factura', id='comprobante', version='1.1.0')
    infoTributaria = etree.SubElement(factura_xml, 'infoTributaria')
    etree.SubElement(infoTributaria, 'ambiente').text = factura.ambiente
    etree.SubElement(infoTributaria, 'tipoEmision').text = factura.tipo_emision
    etree.SubElement(infoTributaria, 'razonSocial').text = factura.empresa.nombre
    etree.SubElement(infoTributaria, 'ruc').text = factura.empresa.ruc
    etree.SubElement(infoTributaria, 'claveAcceso').text = factura.clave_acceso
    etree.SubElement(infoTributaria, 'codDoc').text = '01'
    etree.SubElement(infoTributaria, 'estab').text = factura.punto_venta.codigo_establecimiento
    etree.SubElement(infoTributaria, 'ptoEmi').text = factura.punto_venta.codigo_punto_emision
    etree.SubElement(infoTributaria, 'secuencial').text = factura.secuencial
    etree.SubElement(infoTributaria, 'dirMatriz').text = factura.empresa.direccion
    infoFactura = etree.SubElement(factura_xml, 'infoFactura')
    etree.SubElement(infoFactura, 'fechaEmision').text = factura.fecha_emision.strftime('%d/%m/%Y')
    etree.SubElement(infoFactura, 'dirEstablecimiento').text = factura.empresa.direccion
    etree.SubElement(infoFactura, 'obligadoContabilidad').text = 'NO'
    etree.SubElement(infoFactura, 'tipoIdentificacionComprador').text = determinar_tipo_identificacion(factura.cliente.ruc)
    etree.SubElement(infoFactura, 'razonSocialComprador').text = factura.cliente.nombre
    etree.SubElement(infoFactura, 'identificacionComprador').text = factura.cliente.ruc
    etree.SubElement(infoFactura, 'totalSinImpuestos').text = f"{factura.total_sin_impuestos:.2f}"
    etree.SubElement(infoFactura, 'totalDescuento').text = f"{factura.total_descuento:.2f}"
    totalConImpuestos = etree.SubElement(infoFactura, 'totalConImpuestos')
    for imp_total in factura.total_con_impuestos.get('totalImpuesto', []):
        totalImpuesto = etree.SubElement(totalConImpuestos, 'totalImpuesto')
        etree.SubElement(totalImpuesto, 'codigo').text = imp_total['codigo']
        etree.SubElement(totalImpuesto, 'codigoPorcentaje').text = imp_total['codigoPorcentaje']
        etree.SubElement(totalImpuesto, 'baseImponible').text = imp_total['baseImponible']
        etree.SubElement(totalImpuesto, 'valor').text = imp_total['valor']
    etree.SubElement(infoFactura, 'propina').text = f"{factura.propina:.2f}"
    etree.SubElement(infoFactura, 'importeTotal').text = f"{factura.importe_total:.2f}"
    etree.SubElement(infoFactura, 'moneda').text = factura.moneda
    detalles = etree.SubElement(factura_xml, 'detalles')
    for detalle_obj in factura.detalles.all():
        detalle = etree.SubElement(detalles, 'detalle')
        etree.SubElement(detalle, 'codigoPrincipal').text = detalle_obj.producto.codigo
        etree.SubElement(detalle, 'descripcion').text = detalle_obj.producto.nombre
        etree.SubElement(detalle, 'cantidad').text = f"{detalle_obj.cantidad:.2f}"
        etree.SubElement(detalle, 'precioUnitario').text = f"{detalle_obj.precio_unitario:.4f}"
        etree.SubElement(detalle, 'descuento').text = f"{detalle_obj.descuento:.2f}"
        etree.SubElement(detalle, 'precioTotalSinImpuesto').text = f"{detalle_obj.precio_total_sin_impuesto:.2f}"
        impuestos_detalle = etree.SubElement(detalle, 'impuestos')
        for imp_det in detalle_obj.impuestos.get('impuestos', []):
            impuesto = etree.SubElement(impuestos_detalle, 'impuesto')
            etree.SubElement(impuesto, 'codigo').text = imp_det['codigo']
            etree.SubElement(impuesto, 'codigoPorcentaje').text = imp_det['codigoPorcentaje']
            etree.SubElement(impuesto, 'tarifa').text = '15'
            etree.SubElement(impuesto, 'baseImponible').text = imp_det['baseImponible']
            etree.SubElement(impuesto, 'valor').text = imp_det['valor']
    return etree.tostring(factura_xml, xml_declaration=True, encoding='utf-8')

# ==============================================================================
# FIRMA DIGITAL
# ==============================================================================
def firmar_xml(xml_data, p12_path, p12_password):
    try:
        root = etree.fromstring(xml_data)
        
        with open(p12_path, "rb") as f:
            p12 = pkcs12.load_key_and_certificates(f.read(), p12_password.encode('utf-8'), default_backend())
        
        private_key, certificate = p12[0], p12[1]

        NS_MAP = {
            'ds': 'http://www.w3.org/2000/09/xmldsig#',
            'etsi': 'http://uri.etsi.org/01903/v1.3.2#'
        }
        
        signature = etree.Element(etree.QName(NS_MAP['ds'], 'Signature'), Id='SignatureID', nsmap=NS_MAP)
        signed_info = etree.SubElement(signature, etree.QName(NS_MAP['ds'], 'SignedInfo'))
        
        etree.SubElement(signed_info, etree.QName(NS_MAP['ds'], 'CanonicalizationMethod'), Algorithm='http://www.w3.org/TR/2001/REC-xml-c14n-20010315')
        etree.SubElement(signed_info, etree.QName(NS_MAP['ds'], 'SignatureMethod'), Algorithm='http://www.w3.org/2000/09/xmldsig#rsa-sha1')

        # --- CONSTRUCCIÓN DEL OBJETO Y PROPIEDADES PRIMERO ---
        obj = etree.SubElement(signature, etree.QName(NS_MAP['ds'], 'Object'))
        qualifying_props = etree.SubElement(obj, etree.QName(NS_MAP['etsi'], 'QualifyingProperties'), Target='#SignatureID')
        signed_props = etree.SubElement(qualifying_props, etree.QName(NS_MAP['etsi'], 'SignedProperties'), Id='SignedPropertiesID')
        signed_sig_props = etree.SubElement(signed_props, etree.QName(NS_MAP['etsi'], 'SignedSignatureProperties'))
        etree.SubElement(signed_sig_props, etree.QName(NS_MAP['etsi'], 'SigningTime')).text = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')
        signing_cert = etree.SubElement(signed_sig_props, etree.QName(NS_MAP['etsi'], 'SigningCertificate'))
        cert_node = etree.SubElement(signing_cert, etree.QName(NS_MAP['etsi'], 'Cert'))
        cert_digest_node = etree.SubElement(cert_node, etree.QName(NS_MAP['etsi'], 'CertDigest'))
        etree.SubElement(cert_digest_node, etree.QName(NS_MAP['ds'], 'DigestMethod'), Algorithm='http://www.w3.org/2000/09/xmldsig#sha1')
        cert_data = certificate.public_bytes(Encoding.DER)
        cert_hash = hashes.Hash(hashes.SHA1(), backend=default_backend())
        cert_hash.update(cert_data)
        etree.SubElement(cert_digest_node, etree.QName(NS_MAP['ds'], 'DigestValue')).text = base64.b64encode(cert_hash.finalize()).decode()
        issuer_serial = etree.SubElement(cert_node, etree.QName(NS_MAP['etsi'], 'IssuerSerial'))
        etree.SubElement(issuer_serial, etree.QName(NS_MAP['ds'], 'X509IssuerName')).text = certificate.issuer.rfc4514_string()
        etree.SubElement(issuer_serial, etree.QName(NS_MAP['ds'], 'X509SerialNumber')).text = str(certificate.serial_number)
        
        # --- CONSTRUCCIÓN DE KEYINFO ANTES DE REFERENCIARLO ---
        key_info = etree.SubElement(signature, etree.QName(NS_MAP['ds'], 'KeyInfo'), Id='CertificateID')
        
        # --- 👇👇 LÍNEA CORREGIDA: DEFINIMOS 'x509_data' ANTES DE USARLO 👇👇 ---
        x509_data = etree.SubElement(key_info, etree.QName(NS_MAP['ds'], 'X509Data'))
        etree.SubElement(x509_data, etree.QName(NS_MAP['ds'], 'X509Certificate')).text = base64.b64encode(cert_data).decode()
        
        # --- CREACIÓN DE REFERENCIAS EN EL ORDEN CORRECTO ---
        # 1. Referencia a SignedProperties
        ref_props = etree.SubElement(signed_info, etree.QName(NS_MAP['ds'], 'Reference'), URI='#SignedPropertiesID', Type='http://uri.etsi.org/01903#SignedProperties')
        etree.SubElement(ref_props, etree.QName(NS_MAP['ds'], 'DigestMethod'), Algorithm='http://www.w3.org/2000/09/xmldsig#sha1')
        props_c14n = etree.tostring(signed_props, method='c14n', exclusive=False, with_comments=False)
        digest_props = hashes.Hash(hashes.SHA1(), backend=default_backend())
        digest_props.update(props_c14n)
        etree.SubElement(ref_props, etree.QName(NS_MAP['ds'], 'DigestValue')).text = base64.b64encode(digest_props.finalize()).decode()
        
        # 2. Referencia a KeyInfo
        ref_key = etree.SubElement(signed_info, etree.QName(NS_MAP['ds'], 'Reference'), URI=f'#CertificateID')
        etree.SubElement(ref_key, etree.QName(NS_MAP['ds'], 'DigestMethod'), Algorithm='http://www.w3.org/2000/09/xmldsig#sha1')
        key_info_c14n = etree.tostring(key_info, method='c14n', exclusive=False, with_comments=False)
        digest_key = hashes.Hash(hashes.SHA1(), backend=default_backend())
        digest_key.update(key_info_c14n)
        etree.SubElement(ref_key, etree.QName(NS_MAP['ds'], 'DigestValue')).text = base64.b64encode(digest_key.finalize()).decode()

        # 3. Referencia al Comprobante
        ref_doc = etree.SubElement(signed_info, etree.QName(NS_MAP['ds'], 'Reference'), URI='#comprobante')
        transforms = etree.SubElement(ref_doc, etree.QName(NS_MAP['ds'], 'Transforms'))
        etree.SubElement(transforms, etree.QName(NS_MAP['ds'], 'Transform'), Algorithm='http://www.w3.org/2000/09/xmldsig#enveloped-signature')
        etree.SubElement(ref_doc, etree.QName(NS_MAP['ds'], 'DigestMethod'), Algorithm='http://www.w3.org/2000/09/xmldsig#sha1')
        doc_c14n = etree.tostring(root, method='c14n', exclusive=False, with_comments=False)
        digest_doc = hashes.Hash(hashes.SHA1(), backend=default_backend())
        digest_doc.update(doc_c14n)
        etree.SubElement(ref_doc, etree.QName(NS_MAP['ds'], 'DigestValue')).text = base64.b64encode(digest_doc.finalize()).decode()

        # --- CÁLCULO Y ORDEN FINAL DE LOS ELEMENTOS ---
        signed_info_c14n = etree.tostring(signed_info, method='c14n', exclusive=False, with_comments=False)
        signature_hash = private_key.sign(signed_info_c14n, padding.PKCS1v15(), hashes.SHA1())
        
        etree.SubElement(signature, etree.QName(NS_MAP['ds'], 'SignatureValue')).text = base64.b64encode(signature_hash).decode()
        
        # Reordenar elementos para el orden final: SignedInfo, SignatureValue, KeyInfo, Object
        signature.insert(1, signature.find(etree.QName(NS_MAP['ds'], 'SignatureValue')))
        signature.insert(2, key_info)
        signature.insert(3, obj)
        
        root.append(signature)
        return etree.tostring(root, xml_declaration=True, encoding='utf-8')

    except Exception as e:
        raise Exception(f"Error definitivo al firmar XML: {e}")

# ==============================================================================
# COMUNICACIÓN CON SRI
# ==============================================================================
def enviar_comprobante_sri(xml_firmado):
    try:
        xml_base64 = base64.b64encode(xml_firmado).decode('utf-8')
        cliente_sri = zeep.Client(URL_RECEPCION_PRUEBAS)
        respuesta = cliente_sri.service.validarComprobante(xml_base64)
        if respuesta.estado == 'RECIBIDA':
            return {'status': 'ok', 'estado': 'RECIBIDA'}
        else:
            errores = respuesta.comprobantes.comprobante[0].mensajes.mensaje
            msg = f"{errores[0].identificador} - {errores[0].mensaje}: {errores[0].informacionAdicional}"
            raise Exception(msg)
    except Exception as e:
        raise Exception(f"Error al conectar con SRI (Recepción): {e}")

def consultar_autorizacion_sri(clave_acceso):
    try:
        cliente_sri = zeep.Client(URL_AUTORIZACION_PRUEBAS)
        respuesta = cliente_sri.service.autorizacionComprobante(clave_acceso)
        
        if respuesta and respuesta.autorizaciones and respuesta.autorizaciones.autorizacion:
            autorizacion = respuesta.autorizaciones.autorizacion[0]
            estado = autorizacion.estado
            
            if estado == 'AUTORIZADO':
                return {'status': 'ok', 'estado': 'A', 'fecha_autorizacion': autorizacion.fechaAutorizacion, 'xml_autorizado': autorizacion.comprobante}
            elif estado == 'NO AUTORIZADO':
                msg = autorizacion.mensajes.mensaje[0]
                error = f"{msg.identificador} - {msg.mensaje}: {msg.informacionAdicional or ''}"
                return {'status': 'error', 'estado': 'R', 'mensaje': error}
        
        return {'status': 'procesando', 'estado': 'P'}

    except Exception as e:
        raise Exception(f"Error al conectar con SRI (Autorización): {e}")