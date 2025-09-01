# Ubicación: core/models.py
from django.db import models
from django.db.models import Sum
from django.contrib.auth.models import User

# ==============================================================================
# 1. MODELOS CENTRALES (MULTITENANCY Y CONFIGURACIÓN)
# ==============================================================================

class Empresa(models.Model):
    nombre = models.CharField(max_length=200, verbose_name="Nombre/Razón Social")
    ruc = models.CharField(max_length=13, unique=True, verbose_name="RUC")
    direccion = models.CharField(max_length=300, verbose_name="Dirección Matriz")
    telefono = models.CharField(max_length=20, blank=True, null=True, verbose_name="Teléfono")
    firma_electronica = models.FileField(upload_to='firmas/', blank=True, null=True, verbose_name="Archivo de Firma (.p12)")
    clave_firma = models.CharField(max_length=255, blank=True, null=True, verbose_name="Clave de la Firma")
    ambiente_sri = models.CharField(max_length=1, choices=[('1', 'Pruebas'), ('2', 'Producción')], default='1', verbose_name="Ambiente SRI")
    activa = models.BooleanField(default=True, verbose_name="Suscripción Activa")
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.nombre

class Perfil(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='perfil')
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE)

    def __str__(self):
        return f"Perfil de {self.user.username} en {self.empresa.nombre}"

class PuntoVenta(models.Model):
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name='puntos_venta')
    nombre = models.CharField(max_length=100)
    codigo_establecimiento = models.CharField(max_length=3, verbose_name="Código de Establecimiento (SRI)")
    codigo_punto_emision = models.CharField(max_length=3, verbose_name="Código de Punto de Emisión (SRI)")
    secuencial_factura = models.PositiveIntegerField(default=1)
    secuencial_nota_credito = models.PositiveIntegerField(default=1)
    secuencial_retencion = models.PositiveIntegerField(default=1)
    activo = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.nombre} ({self.codigo_establecimiento}-{self.codigo_punto_emision})"
        
    class Meta:
        unique_together = ('empresa', 'codigo_establecimiento', 'codigo_punto_emision')

# ==============================================================================
# 2. MODELOS DE DATOS MAESTROS (CLIENTES, PROVEEDORES, PRODUCTOS)
# ==============================================================================

class Cliente(models.Model):
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE)
    ruc = models.CharField(max_length=13, verbose_name="RUC/Cédula")
    nombre = models.CharField(max_length=200, verbose_name="Nombre/Razón Social")
    email = models.EmailField(verbose_name="Correo Electrónico")
    direccion = models.CharField(max_length=300, verbose_name="Dirección")
    telefono = models.CharField(max_length=20, blank=True, null=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de Creación")

    def __str__(self):
        return self.nombre

class Proveedor(models.Model):
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE)
    razon_social = models.CharField(
        max_length=200, 
        verbose_name="Razón Social", 
        null=True, 
        blank=True
    )
    ruc = models.CharField(max_length=13)
    nombre = models.CharField(max_length=200)
    email = models.EmailField(blank=True, null=True)
    direccion = models.CharField(max_length=300, blank=True, null=True)
    telefono = models.CharField(max_length=20, blank=True, null=True)

    def __str__(self):
       return self.razon_social or f"Proveedor ID: {self.id}"

    class Meta:
        verbose_name_plural = "Proveedores"

class Categoria(models.Model):
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE)
    nombre = models.CharField(max_length=100)
    
    def __str__(self):
        return self.nombre

class Marca(models.Model):
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE)
    nombre = models.CharField(max_length=100)

    def __str__(self):
        return self.nombre

class Modelo(models.Model):
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE)
    marca = models.ForeignKey(Marca, on_delete=models.CASCADE)
    nombre = models.CharField(max_length=100)

    def __str__(self):
        return f"{self.marca.nombre} {self.nombre}"

class Producto(models.Model):
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE)
    codigo = models.CharField(max_length=50)
    nombre = models.CharField(max_length=200)
    descripcion = models.TextField(blank=True, null=True)
    categoria = models.ForeignKey(Categoria, on_delete=models.PROTECT, null=True, blank=True)
    marca = models.ForeignKey(Marca, on_delete=models.PROTECT, null=True, blank=True)
    modelo = models.ForeignKey(Modelo, on_delete=models.PROTECT, null=True, blank=True)
    costo = models.DecimalField(max_digits=12, decimal_places=4, default=0, verbose_name="Costo Unitario")
    precio = models.DecimalField(max_digits=12, decimal_places=4, verbose_name="Precio Unitario de Venta")
    stock = models.DecimalField(max_digits=12, decimal_places=4, default=0)
    maneja_iva = models.BooleanField(default=True, verbose_name="Grava IVA")
    activo = models.BooleanField(default=True)
    
    def __str__(self):
        return self.nombre

# ==============================================================================
# 3. MODELOS TRANSACCIONALES (COMPRAS Y VENTAS/FACTURACIÓN)
# ==============================================================================

class Compra(models.Model):
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE)
    proveedor = models.ForeignKey(Proveedor, on_delete=models.PROTECT)
    fecha = models.DateField()
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    iva = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    ESTADO_CHOICES = [('A', 'Activa'), ('N', 'Anulada')]
    estado = models.CharField(max_length=1, choices=ESTADO_CHOICES, default='A')
    
    def __str__(self):
        return f"Compra #{self.id} a {self.proveedor.nombre}"
    
class CompraDetalle(models.Model):
    compra = models.ForeignKey(Compra, related_name='detalles', on_delete=models.CASCADE)
    producto = models.ForeignKey(Producto, on_delete=models.PROTECT)
    cantidad = models.DecimalField(max_digits=12, decimal_places=4)
    costo_unitario = models.DecimalField(max_digits=12, decimal_places=4)

    @property
    def subtotal(self):
        return self.cantidad * self.costo_unitario
    
class MetodoPago(models.Model):
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE)
    nombre = models.CharField(max_length=100)
    es_contado = models.BooleanField(default=True, help_text="Marcar si este método de pago se considera inmediato (Pagado).")


    def __str__(self):
        return self.nombre

class Factura(models.Model):
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE)
    cliente = models.ForeignKey(Cliente, on_delete=models.PROTECT)
    punto_venta = models.ForeignKey(PuntoVenta, on_delete=models.PROTECT)
    usuario = models.ForeignKey(User, on_delete=models.PROTECT)

    # InfoTributaria (SRI)
    ambiente = models.CharField(max_length=1, choices=[('1', 'Pruebas'), ('2', 'Producción')])
    tipo_emision = models.CharField(max_length=1, default='1') # 1=Normal
    secuencial = models.CharField(max_length=9, editable=False)
    clave_acceso = models.CharField(max_length=49, unique=True, editable=False)

    # InfoFactura (SRI)
    fecha_emision = models.DateField()
    total_sin_impuestos = models.DecimalField(max_digits=12, decimal_places=2)
    total_descuento = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_con_impuestos = models.JSONField(default=dict)
    propina = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    importe_total = models.DecimalField(max_digits=12, decimal_places=2)
    moneda = models.CharField(max_length=15, default='DOLAR')
    pagos = models.JSONField(default=dict)

    # Control de estado SRI
    ESTADO_SRI_CHOICES = [('P', 'Procesando'), ('A', 'Autorizada'), ('R', 'Rechazada'), ('C', 'Cancelada'),
        ('F', 'Firmado')]
    estado_sri = models.CharField(max_length=1, choices=ESTADO_SRI_CHOICES, default='P')
    fecha_autorizacion = models.DateTimeField(null=True, blank=True)
    xml_generado = models.TextField(blank=True, null=True)
    xml_autorizado = models.TextField(blank=True, null=True)
    xml_firmado = models.TextField(null=True, blank=True)
    
    sri_error = models.TextField(null=True, blank=True, help_text="Mensaje de error devuelto por el SRI, si lo hubiera.")

    
    # Control de estado de pago interno
    ESTADO_PAGO_CHOICES = [('P', 'Pendiente'), ('A', 'Abonada'), ('C', 'Pagada'), ('N', 'Anulada')]
    metodo_pago = models.ForeignKey(MetodoPago, on_delete=models.PROTECT, null=True, blank=True)
    estado_pago = models.CharField(max_length=1, choices=ESTADO_PAGO_CHOICES, default='P')

    def __str__(self):
        return f"Factura {self.punto_venta.codigo_establecimiento}-{self.punto_venta.codigo_punto_emision}-{self.secuencial}"
    
    @property
    def total_abonado(self):
        return self.pagos_recibidos.aggregate(total=Sum('monto'))['total'] or 0
    
    @property
    def saldo_pendiente(self):
        return self.importe_total - self.total_abonado

class FacturaDetalle(models.Model):
    factura = models.ForeignKey('Factura', related_name='detalles', on_delete=models.CASCADE)
    producto = models.ForeignKey(Producto, on_delete=models.PROTECT)
    cantidad = models.DecimalField(max_digits=12, decimal_places=4)
    precio_unitario = models.DecimalField(max_digits=12, decimal_places=4)
    descuento = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    precio_total_sin_impuesto = models.DecimalField(max_digits=12, decimal_places=2)
    precio_total_sin_impuesto = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    impuestos = models.JSONField(default=dict)

class PagoFactura(models.Model):
    factura = models.ForeignKey('Factura', related_name='pagos_recibidos', on_delete=models.CASCADE)
    fecha = models.DateTimeField(auto_now_add=True)
    monto = models.DecimalField(max_digits=12, decimal_places=2)
    metodo_pago = models.ForeignKey(MetodoPago, on_delete=models.PROTECT)
    observacion = models.TextField(blank=True, null=True)

class FacturaDetalle(models.Model):
    factura = models.ForeignKey('Factura', related_name='detalles', on_delete=models.CASCADE)
    producto = models.ForeignKey(Producto, on_delete=models.PROTECT)
    cantidad = models.DecimalField(max_digits=12, decimal_places=4)
    precio_unitario = models.DecimalField(max_digits=12, decimal_places=4)
    descuento = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    precio_total_sin_impuesto = models.DecimalField(max_digits=12, decimal_places=2)
    impuestos = models.JSONField()

# ==============================================================================
# 4. MODELOS DE INVENTARIO, PROMOCIONES Y AUDITORÍA
# ==============================================================================

class MovimientoInventario(models.Model):
    TIPO_CHOICES = [('E', 'Entrada/Compra'), ('S', 'Salida/Venta'), ('AJ_E', 'Ajuste de Entrada'), ('AJ_S', 'Ajuste de Salida')]
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE)
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE)
    tipo = models.CharField(max_length=4, choices=TIPO_CHOICES)
    cantidad = models.DecimalField(max_digits=12, decimal_places=4)
    fecha = models.DateTimeField(auto_now_add=True)
    detalle_factura = models.ForeignKey(FacturaDetalle, null=True, blank=True, on_delete=models.SET_NULL)
    detalle_compra = models.ForeignKey(CompraDetalle, null=True, blank=True, on_delete=models.SET_NULL)

class Promocion(models.Model):
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE)
    nombre = models.CharField(max_length=100)
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE)
    porcentaje_descuento = models.DecimalField(max_digits=5, decimal_places=2)
    fecha_inicio = models.DateField()
    fecha_fin = models.DateField()
    activa = models.BooleanField(default=True)

class Bitacora(models.Model):
    usuario = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE)
    accion = models.TextField()
    fecha_hora = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"[{self.fecha_hora.strftime('%Y-%m-%d %H:%M')}] {self.usuario.username}: {self.accion[:50]}..."