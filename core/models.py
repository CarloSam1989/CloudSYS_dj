# Ubicación: core/models.py
from django.db import models
from django.db.models import Sum
from django.contrib.auth.models import User
from decimal import Decimal
from dateutil.relativedelta import relativedelta
import json
# ==============================================================================
# 1. MODELOS CENTRALES (MULTITENANCY Y CONFIGURACIÓN)
# ==============================================================================
class DecimalEncoder(json.JSONEncoder):
    """
    Esta clase ayuda a convertir objetos Decimal a string
    para que puedan ser guardados en un campo JSON.
    """
    def default(self, obj):
        if isinstance(obj, Decimal):
            return str(obj)
        return super().default(obj)

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
    iva_porcentaje = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        default=12.00, 
        verbose_name="Porcentaje de IVA (%)",
        help_text="Valor actual del IVA. Ej: 12.00 para 12%, 5.00 para 5%."
    )

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
    user = models.OneToOneField(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='perfil_cliente',
        verbose_name="Usuario de Acceso (Home Banking)"
    )

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
    total_con_impuestos = models.JSONField(default=dict, encoder=DecimalEncoder)
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
    
# ==============================================================================
# 5. MODELOS DE COTIZACIONES / PRESUPUESTOS
# ==============================================================================

class Cotizacion(models.Model):
    
    ESTADO_CHOICES = [
        ('B', 'Borrador'),      # Creada pero no enviada al cliente
        ('E', 'Enviada'),        # Enviada al cliente, esperando respuesta
        ('A', 'Aceptada'),       # El cliente aceptó la cotización
        ('R', 'Rechazada'),      # El cliente rechazó la cotización
        ('V', 'Vencida'),        # La cotización expiró
        ('F', 'Facturada'),      # La cotización ya se convirtió en factura
    ]

    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE)
    cliente = models.ForeignKey(Cliente, on_delete=models.PROTECT)
    usuario = models.ForeignKey(User, on_delete=models.PROTECT)

    # El campo clave para enlazar con la factura una vez que se genere.
    factura_generada = models.OneToOneField(
        Factura, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='cotizacion_origen',
        verbose_name="Factura Generada"
    )

    # Información general
    numero_cotizacion = models.CharField(max_length=50, unique=True, editable=False)
    fecha_emision = models.DateField(auto_now_add=True)
    fecha_vencimiento = models.DateField(verbose_name="Válida hasta")
    estado = models.CharField(max_length=1, choices=ESTADO_CHOICES, default='B')
    terminos_y_condiciones = models.TextField(blank=True, null=True, verbose_name="Términos y Condiciones")

    # Totales (idénticos a los de la factura para facilitar la conversión)
    total_sin_impuestos = models.DecimalField(max_digits=12, decimal_places=2)
    total_descuento = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_con_impuestos = models.JSONField(default=dict, encoder=DecimalEncoder)
    importe_total = models.DecimalField(max_digits=12, decimal_places=2)

    def __str__(self):
        return f"Cotización {self.numero_cotizacion} para {self.cliente.nombre}"

    class Meta:
        verbose_name = "Cotización"
        verbose_name_plural = "Cotizaciones"
        ordering = ['-fecha_emision']

class CotizacionDetalle(models.Model):
    """
    Líneas de detalle de la cotización. Es casi un espejo de FacturaDetalle.
    """
    cotizacion = models.ForeignKey(Cotizacion, related_name='detalles', on_delete=models.CASCADE)
    producto = models.ForeignKey(Producto, on_delete=models.PROTECT)
    cantidad = models.DecimalField(max_digits=12, decimal_places=4)
    precio_unitario = models.DecimalField(max_digits=12, decimal_places=4)
    descuento = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    precio_total_sin_impuesto = models.DecimalField(max_digits=12, decimal_places=2)
    impuestos = models.JSONField(default=dict)

    def __str__(self):
        return f"Detalle de {self.producto.nombre} en cotización {self.cotizacion.id}"
    
# ==============================================================================
# 6. MÓDULO DE FINANZAS: CAJA CHICA Y PRÉSTAMOS
# ==============================================================================

class CajaChica(models.Model):
    """
    Define una caja menor (ej: Caja Administración, Caja Ventas).
    """
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE)
    responsable = models.ForeignKey(User, on_delete=models.PROTECT, verbose_name="Custodio")
    nombre = models.CharField(max_length=100, help_text="Ej: Caja Chica Administración")
    saldo_actual = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    fecha_apertura = models.DateField(auto_now_add=True)
    fecha_cierre = models.DateField(null=True, blank=True)
    activo = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.nombre} - Saldo: ${self.saldo_actual}"

class MovimientoCaja(models.Model):
    """
    Registra entradas (reposición) y salidas (gastos) de la caja chica.
    """
    TIPO_MOVIMIENTO = [
        ('ING', 'Ingreso / Reposición'),
        ('EGR', 'Egreso / Gasto'),
    ]

    caja = models.ForeignKey(CajaChica, on_delete=models.CASCADE, related_name='movimientos')
    usuario = models.ForeignKey(User, on_delete=models.PROTECT) # Quién registró el movimiento
    fecha = models.DateTimeField(auto_now_add=True)
    tipo = models.CharField(max_length=3, choices=TIPO_MOVIMIENTO)
    monto = models.DecimalField(max_digits=12, decimal_places=2)
    concepto = models.CharField(max_length=255, verbose_name="Descripción del gasto/ingreso")
    
    # Comprobante del gasto (Factura física escaneada, recibo, etc.)
    comprobante = models.FileField(
        upload_to='comprobantes/caja_chica/%Y/%m/', 
        null=True, 
        blank=True,
        verbose_name="Evidencia/Recibo"
    )

    def save(self, *args, **kwargs):
        # Lógica de actualización de saldo de la caja
        es_nuevo = self.pk is None
        super().save(*args, **kwargs)
        
        if es_nuevo:
            if self.tipo == 'ING':
                self.caja.saldo_actual += self.monto
            else:
                self.caja.saldo_actual -= self.monto
            self.caja.save()
            
            # Auditoría Automática (Reutilizando tu modelo Bitacora)
            Bitacora.objects.create(
                usuario=self.usuario,
                empresa=self.caja.empresa,
                accion=f"Movimiento Caja {self.caja.nombre}: {self.tipo} de ${self.monto}. Ref: {self.concepto}"
            )

    def __str__(self):
        return f"{self.tipo} - {self.monto} ({self.fecha.strftime('%Y-%m-%d')})"

class Prestamo(models.Model):
    ESTADO_PRESTAMO = [
        ('A', 'Activo'),
        ('P', 'Pagado/Cerrado'),
        ('M', 'Mora/Vencido'),
        ('N', 'Anulado')
    ]

    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE)
    # Se puede ligar a un Cliente existente o usar un nombre genérico
    beneficiario_cliente = models.ForeignKey(Cliente, on_delete=models.SET_NULL, null=True, blank=True, help_text="Si el beneficiario es un cliente registrado")
    beneficiario_nombre = models.CharField(max_length=200, help_text="Nombre del beneficiario si no es cliente")
    ruc_cedula = models.CharField(max_length=13, verbose_name="RUC/Cédula")
    plazo_meses = models.PositiveIntegerField(default=12, verbose_name="Plazo (Meses)")
    fecha_inicio = models.DateField()
    fecha_vencimiento = models.DateField()
    
    monto_capital = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="Capital Prestado")
    tasa_interes_mensual = models.DecimalField(max_digits=5, decimal_places=2, verbose_name="Tasa Interés %")
    
    observaciones = models.TextField(blank=True, null=True)
    estado = models.CharField(max_length=1, choices=ESTADO_PRESTAMO, default='A')

    # Campos calculados / de control
    saldo_capital_pendiente = models.DecimalField(max_digits=12, decimal_places=2)
    interes_acumulado_pendiente = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    def __str__(self):
        nombre = self.beneficiario_cliente.nombre if self.beneficiario_cliente else self.beneficiario_nombre
        return f"Préstamo a {nombre} - ${self.monto_capital}"

    def save(self, *args, **kwargs):
        if not self.pk:
            # Al crear, el saldo pendiente es igual al monto prestado
            self.saldo_capital_pendiente = self.monto_capital
        super().save(*args, **kwargs)
    def generar_tabla_amortizacion(self):
        """
        Calcula y guarda las cuotas usando el Sistema Francés.
        Formula: R = P * ( i * (1+i)^n ) / ( (1+i)^n - 1 )
        """
        # Limpiamos tabla anterior si existe
        self.cuotas.all().delete()
        
        capital = float(self.monto_capital)
        tasa = float(self.tasa_interes_mensual) / 100
        plazo = self.plazo_meses

        # Evitar división por cero
        if tasa > 0:
            cuota_fija = capital * (tasa * pow(1 + tasa, plazo)) / (pow(1 + tasa, plazo) - 1)
        else:
            cuota_fija = capital / plazo

        saldo = capital
        fecha_pago = self.fecha_inicio

        for i in range(1, plazo + 1):
            # Calcular componentes
            interes_cuota = saldo * tasa
            capital_cuota = cuota_fija - interes_cuota
            saldo -= capital_cuota
            
            # Avanzar un mes para la fecha de pago
            fecha_pago += relativedelta(months=1)

            # Ajuste final para evitar decimales residuales en la última cuota
            if i == plazo and saldo != 0:
                capital_cuota += saldo
                saldo = 0

            # Guardar en Base de Datos
            CuotaPrestamo.objects.create(
                prestamo=self,
                numero_cuota=i,
                fecha_vencimiento=fecha_pago,
                valor_cuota=Decimal(cuota_fija),
                interes=Decimal(interes_cuota),
                capital=Decimal(capital_cuota),
                saldo_pendiente=Decimal(saldo if saldo > 0 else 0)
            )

class CuotaPrestamo(models.Model):
    """
    Representa cada fila de la tabla de amortización.
    """
    ESTADO_CUOTA = [
        ('PEN', 'Pendiente'),
        ('PAG', 'Pagada'),
        ('VEN', 'Vencida'),
    ]

    prestamo = models.ForeignKey(Prestamo, on_delete=models.CASCADE, related_name='cuotas')
    numero_cuota = models.PositiveIntegerField()
    fecha_vencimiento = models.DateField()
    
    # Valores monetarios
    valor_cuota = models.DecimalField(max_digits=12, decimal_places=2)
    capital = models.DecimalField(max_digits=12, decimal_places=2, help_text="Parte que reduce la deuda")
    interes = models.DecimalField(max_digits=12, decimal_places=2, help_text="Ganancia del banco")
    saldo_pendiente = models.DecimalField(max_digits=12, decimal_places=2)
    
    estado = models.CharField(max_length=3, choices=ESTADO_CUOTA, default='PEN')
    fecha_pago_real = models.DateField(null=True, blank=True)

    def __str__(self):
        return f"Cuota {self.numero_cuota}/{self.prestamo.plazo_meses} - ${self.valor_cuota}"

class AbonoPrestamo(models.Model):
    """
    Registra los pagos que hace el beneficiario para cubrir el préstamo.
    Permite subir el comprobante de depósito bancario.
    """
    prestamo = models.ForeignKey(Prestamo, on_delete=models.CASCADE, related_name='abonos')
    usuario = models.ForeignKey(User, on_delete=models.PROTECT) # Quien registra el cobro
    fecha_pago = models.DateTimeField(auto_now_add=True)
    
    # Distribución del pago
    monto_capital = models.DecimalField(max_digits=12, decimal_places=2, default=0, help_text="Cuánto de este pago va a reducir la deuda original")
    monto_interes = models.DecimalField(max_digits=12, decimal_places=2, default=0, help_text="Cuánto de este pago es ganancia por intereses")
    
    codigo_deposito = models.CharField(max_length=50, blank=True, null=True, verbose_name="# Referencia Bancaria")
    
    # Aquí se sube la foto del voucher o comprobante
    comprobante_deposito = models.FileField(
        upload_to='comprobantes/prestamos/%Y/%m/', 
        verbose_name="Comprobante de Depósito",
        null=True, 
        blank=True
    )

    @property
    def total_pagado(self):
        return self.monto_capital + self.monto_interes

    def save(self, *args, **kwargs):
        # Lógica para descontar la deuda del préstamo
        es_nuevo = self.pk is None
        super().save(*args, **kwargs)

        if es_nuevo:
            # Actualizamos los saldos del préstamo padre
            self.prestamo.saldo_capital_pendiente -= self.monto_capital
            # El interés pendiente podría manejarse aquí si tuvieras una lógica de devengo diario,
            # pero por ahora simplemente registramos que se pagó interés.
            
            # Verificamos si se terminó de pagar
            if self.prestamo.saldo_capital_pendiente <= 0:
                self.prestamo.saldo_capital_pendiente = 0
                self.prestamo.estado = 'P' # Pagado
            
            self.prestamo.save()

            # Auditoría Automática
            Bitacora.objects.create(
                usuario=self.usuario,
                empresa=self.prestamo.empresa,
                accion=f"Abono Préstamo #{self.prestamo.id}: Capital ${self.monto_capital} + Interés ${self.monto_interes}. Ref: {self.codigo_deposito}"
            )

    def __str__(self):
        return f"Abono ${self.total_pagado} ({self.fecha_pago.strftime('%Y-%m-%d')})"
    
class CuentaBancaria(models.Model):
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, null=True, blank=True)
    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE, null=True, blank=True)
    banco = models.CharField(max_length=100, default='Banco General', verbose_name="Nombre del Banco")
    numero_cuenta = models.CharField(max_length=20, unique=True)
    tipo = models.CharField(max_length=3, choices=[('AH', 'Ahorros'), ('CTE', 'Corriente')])
    saldo = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    activa = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.banco} - {self.numero_cuenta}"

# Y necesitas registrar las transacciones de esas cuentas
class TransaccionBancaria(models.Model):
    cuenta = models.ForeignKey(CuentaBancaria, on_delete=models.CASCADE, related_name='transacciones')
    fecha = models.DateTimeField(auto_now_add=True)
    tipo = models.CharField(max_length=3, choices=[('DEP', 'Depósito'), ('RET', 'Retiro')])
    monto = models.DecimalField(max_digits=12, decimal_places=2)
    descripcion = models.CharField(max_length=200)
    
    def save(self, *args, **kwargs):
        # Actualizar saldo automáticamente
        if not self.pk:
            if self.tipo == 'DEP':
                self.cuenta.saldo += self.monto
            elif self.tipo == 'RET':
                self.cuenta.saldo -= self.monto
            self.cuenta.save()
        super().save(*args, **kwargs)