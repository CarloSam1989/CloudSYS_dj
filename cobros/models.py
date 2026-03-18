from django.db import models
from django.conf import settings
from decimal import Decimal
from core.models import *
from django.core.exceptions import ValidationError
from django.utils import timezone
# ==============================
# CATEGORÍAS DE COBRANZA
# ==============================
class CategoriaCobro(models.Model):
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name='categorias_cobro')
    nombre = models.CharField(max_length=100)
    activo = models.BooleanField(default=True)

    class Meta:
        unique_together = ('empresa', 'nombre')
        verbose_name = "Categoría de cobro"
        verbose_name_plural = "Categorías de cobro"

    def __str__(self):
        return self.nombre

# ==============================
# ESTADO DE CUENTA DE FACTURAS
# ==============================
class EstadoCuentaCobro(models.Model):
    ESTADO_CHOICES = [
        ('PENDIENTE', 'Pendiente'),
        ('ABONADO', 'Abonado'),
        ('PAGADO', 'Pagado'),
        ('VENCIDO', 'Vencido'),
        ('ANULADO', 'Anulado'),
    ]

    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name='estados_cuenta_cobro')
    cliente = models.ForeignKey(Cliente, on_delete=models.PROTECT, related_name='estados_cuenta_cobro')
    factura = models.OneToOneField(Factura, on_delete=models.CASCADE, related_name='estado_cuenta_cobro')

    fecha_emision = models.DateField()
    fecha_vencimiento = models.DateField(null=True, blank=True)

    total_documento = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_abonado = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    saldo = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    categoria = models.ForeignKey(
        CategoriaCobro,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='estados_cuenta'
    )

    estado = models.CharField(max_length=10, choices=ESTADO_CHOICES, default='PENDIENTE')
    observacion = models.TextField(blank=True, null=True)

    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Estado de cuenta por cobrar"
        verbose_name_plural = "Estados de cuenta por cobrar"
        indexes = [
            models.Index(fields=['empresa', 'cliente', 'estado']),
            models.Index(fields=['empresa', 'fecha_vencimiento']),
        ]

    def __str__(self):
        return f"{self.factura} - Saldo: {self.saldo}"

    def recalcular_saldo(self):
        total_abonos = self.movimientos.filter(
            tipo='ABONO',
            anulado=False
        ).aggregate(total=models.Sum('monto'))['total'] or Decimal('0.00')

        total_cargos = self.movimientos.filter(
            tipo__in=['CARGO', 'INTERES', 'MORA', 'AJUSTE_CARGO'],
            anulado=False
        ).aggregate(total=models.Sum('monto'))['total'] or Decimal('0.00')

        total_descuentos = self.movimientos.filter(
            tipo__in=['DESCUENTO', 'AJUSTE_ABONO'],
            anulado=False
        ).aggregate(total=models.Sum('monto'))['total'] or Decimal('0.00')

        self.total_abonado = total_abonos
        self.saldo = (self.total_documento + total_cargos) - (total_abonos + total_descuentos)

        if self.estado == 'ANULADO':
            pass
        elif self.saldo <= 0:
            self.estado = 'PAGADO'
        elif self.total_abonado > 0:
            self.estado = 'ABONADO'
        else:
            self.estado = 'PENDIENTE'

        self.save(update_fields=['total_abonado', 'saldo', 'estado', 'fecha_actualizacion'])

# ==============================
# KARDEX / MOVIMIENTOS DE COBRANZA
# ==============================
class MovimientoCobro(models.Model):
    TIPO_CHOICES = [
        ('CARGO', 'Cargo inicial'),
        ('ABONO', 'Abono'),
        ('INTERES', 'Interés'),
        ('MORA', 'Mora'),
        ('DESCUENTO', 'Descuento'),
        ('AJUSTE_CARGO', 'Ajuste cargo'),
        ('AJUSTE_ABONO', 'Ajuste abono'),
    ]

    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name='movimientos_cobro')
    estado_cuenta = models.ForeignKey(
        EstadoCuentaCobro,
        on_delete=models.CASCADE,
        related_name='movimientos'
    )
    cliente = models.ForeignKey(Cliente, on_delete=models.PROTECT, related_name='movimientos_cobro')
    factura = models.ForeignKey(Factura, on_delete=models.CASCADE, related_name='movimientos_cobro')

    fecha = models.DateTimeField(auto_now_add=True)
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES)
    monto = models.DecimalField(max_digits=12, decimal_places=2)

    saldo_anterior = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    saldo_nuevo = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    metodo_pago = models.ForeignKey(MetodoPago, on_delete=models.PROTECT, null=True, blank=True)
    referencia = models.CharField(max_length=100, blank=True, null=True)
    observacion = models.TextField(blank=True, null=True)

    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    anulado = models.BooleanField(default=False)

    class Meta:
        verbose_name = "Movimiento de cobro"
        verbose_name_plural = "Movimientos de cobro"
        ordering = ['fecha', 'id']
        indexes = [
            models.Index(fields=['empresa', 'cliente', 'fecha']),
            models.Index(fields=['empresa', 'factura', 'tipo']),
        ]

    def __str__(self):
        return f"{self.get_tipo_display()} - {self.monto}"

    def save(self, *args, **kwargs):
        es_nuevo = self.pk is None

        if es_nuevo and self.estado_cuenta_id:
            saldo_actual = self.estado_cuenta.saldo or Decimal('0.00')
            self.saldo_anterior = saldo_actual

            if self.tipo in ['ABONO', 'DESCUENTO', 'AJUSTE_ABONO']:
                self.saldo_nuevo = saldo_actual - self.monto
            else:
                self.saldo_nuevo = saldo_actual + self.monto

        super().save(*args, **kwargs)

        if self.estado_cuenta_id:
            self.estado_cuenta.recalcular_saldo()

# ==============================
# PROMESAS DE PAGO
# ==============================
class PromesaPago(models.Model):
    ESTADO_CHOICES = [
        ('PENDIENTE', 'Pendiente'),
        ('CUMPLIDA', 'Cumplida'),
        ('INCUMPLIDA', 'Incumplida'),
        ('ANULADA', 'Anulada'),
    ]

    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name='promesas_pago')
    estado_cuenta = models.ForeignKey(EstadoCuentaCobro, on_delete=models.CASCADE, related_name='promesas_pago')
    cliente = models.ForeignKey(Cliente, on_delete=models.PROTECT, related_name='promesas_pago')

    fecha_promesa = models.DateField()
    monto_prometido = models.DecimalField(max_digits=12, decimal_places=2)

    estado = models.CharField(max_length=12, choices=ESTADO_CHOICES, default='PENDIENTE')
    observacion = models.TextField(blank=True, null=True)

    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Promesa de pago"
        verbose_name_plural = "Promesas de pago"
        indexes = [
            models.Index(fields=['empresa', 'fecha_promesa', 'estado']),
        ]

    def __str__(self):
        return f"{self.cliente} - {self.monto_prometido}"

# ==============================
# COBRANZA DE PRÉSTAMOS
# ==============================
class CuentaFinancieraCobro(models.Model):
    TIPO_CHOICES = [
        ('BANCO', 'Banco'),
        ('CAJA', 'Caja'),
        ('EFECTIVO', 'Efectivo'),
        ('BILLETERA', 'Billetera'),
    ]

    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name='cuentas_financieras_cobro')
    nombre = models.CharField(max_length=100)
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES, default='BANCO')
    banco = models.CharField(max_length=100, blank=True, null=True)
    numero_cuenta = models.CharField(max_length=50, blank=True, null=True)
    titular = models.CharField(max_length=150, blank=True, null=True)
    saldo_actual = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    activo = models.BooleanField(default=True)
    observacion = models.TextField(blank=True, null=True)

    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Cuenta financiera"
        verbose_name_plural = "Cuentas financieras"
        unique_together = ('empresa', 'nombre')
        indexes = [
            models.Index(fields=['empresa', 'tipo', 'activo']),
        ]

    def __str__(self):
        return f"{self.nombre} ({self.get_tipo_display()})"

class MovimientoCuentaCobro(models.Model):
    TIPO_CHOICES = [
        ('INGRESO', 'Ingreso'),
        ('EGRESO', 'Egreso'),
        ('TRANSFERENCIA_ENTRADA', 'Transferencia entrada'),
        ('TRANSFERENCIA_SALIDA', 'Transferencia salida'),
        ('AJUSTE_MAS', 'Ajuste más'),
        ('AJUSTE_MENOS', 'Ajuste menos'),
    ]

    ORIGEN_CHOICES = [
        ('PRESTAMO', 'Préstamo'),
        ('COMPRA_FINANCIADA', 'Compra financiada'),
        ('VENTA', 'Venta'),
        ('COBRO', 'Cobro'),
        ('OTRO', 'Otro'),
    ]

    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name='movimientos_cuenta_cobro')
    cuenta = models.ForeignKey(CuentaFinancieraCobro, on_delete=models.PROTECT, related_name='movimientos')

    fecha = models.DateTimeField(default=timezone.now)
    tipo = models.CharField(max_length=25, choices=TIPO_CHOICES)
    origen = models.CharField(max_length=25, choices=ORIGEN_CHOICES, default='OTRO')

    monto = models.DecimalField(max_digits=14, decimal_places=2)
    saldo_anterior = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    saldo_nuevo = models.DecimalField(max_digits=14, decimal_places=2, default=0)

    referencia = models.CharField(max_length=100, blank=True, null=True)
    observacion = models.TextField(blank=True, null=True)

    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    anulado = models.BooleanField(default=False)

    class Meta:
        verbose_name = "Movimiento de cuenta"
        verbose_name_plural = "Movimientos de cuentas"
        ordering = ['fecha', 'id']
        indexes = [
            models.Index(fields=['empresa', 'cuenta', 'fecha']),
        ]

    def __str__(self):
        return f"{self.cuenta.nombre} - {self.get_tipo_display()} - {self.monto}"

    def save(self, *args, **kwargs):
        es_nuevo = self.pk is None

        if es_nuevo and self.cuenta_id:
            saldo_actual = self.cuenta.saldo_actual or Decimal('0.00')
            self.saldo_anterior = saldo_actual

            if self.tipo in ['INGRESO', 'TRANSFERENCIA_ENTRADA', 'AJUSTE_MAS']:
                self.saldo_nuevo = saldo_actual + self.monto
            else:
                if saldo_actual < self.monto:
                    raise ValidationError(
                        f"No hay saldo suficiente en la cuenta '{self.cuenta.nombre}'. "
                        f"Disponible: {saldo_actual}, requerido: {self.monto}"
                    )
                self.saldo_nuevo = saldo_actual - self.monto

        super().save(*args, **kwargs)

        if es_nuevo and self.cuenta_id:
            self.cuenta.saldo_actual = self.saldo_nuevo
            self.cuenta.save(update_fields=['saldo_actual'])

class PrestamoCobro(models.Model):
    ESTADO_CHOICES = [
        ('ACTIVO', 'Activo'),
        ('PAGADO', 'Pagado'),
        ('VENCIDO', 'Vencido'),
        ('ANULADO', 'Anulado'),
    ]

    TIPO_INTERES_CHOICES = [
        ('MENSUAL', 'Mensual'),
        ('ANUAL', 'Anual'),
    ]
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name='prestamos_cobro')
    cliente = models.ForeignKey(Cliente, on_delete=models.PROTECT, related_name='prestamos_cobro')
    cuenta_desembolso = models.ForeignKey(
        CuentaFinancieraCobro,
        on_delete=models.PROTECT,
        related_name='prestamos_desembolsados',
        null=True,
        blank=True
    )

    numero = models.CharField(max_length=30)
    fecha = models.DateField()

    monto = models.DecimalField(max_digits=12, decimal_places=2)
    interes = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    tipo_interes = models.CharField(
        max_length=10,
        choices=TIPO_INTERES_CHOICES,
        default='MENSUAL'
    )

    cuotas = models.PositiveIntegerField(default=1)
    frecuencia_dias = models.PositiveIntegerField(default=30)
    fecha_vencimiento = models.DateField(null=True, blank=True)

    total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    cuota_estimada = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    saldo = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    estado = models.CharField(max_length=10, choices=ESTADO_CHOICES, default='ACTIVO')
    observacion = models.TextField(blank=True, null=True)

    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Préstamo de cobranza"
        verbose_name_plural = "Préstamos de cobranza"
        unique_together = ('empresa', 'numero')
        indexes = [
            models.Index(fields=['empresa', 'cliente', 'estado']),
        ]

    def __str__(self):
        return f"{self.numero} - {self.cliente}"

    def calcular_total(self):
        monto = self.monto or Decimal('0.00')
        interes = self.interes or Decimal('0.00')

        total = monto + (monto * interes / Decimal('100'))
        return total.quantize(Decimal('0.01'))

    def calcular_cuota_estimada(self):
        total = self.calcular_total()
        cuotas = self.cuotas or 1
        if cuotas <= 0:
            cuotas = 1
        return (total / Decimal(cuotas)).quantize(Decimal('0.01'))
    
class MovimientoPrestamoCobro(models.Model):
    TIPO_CHOICES = [
        ('DESEMBOLSO', 'Desembolso'),
        ('CUOTA', 'Cuota'),
        ('ABONO_CAPITAL', 'Abono a capital'),
        ('INTERES', 'Interés'),
        ('MORA', 'Mora'),
        ('AJUSTE_CARGO', 'Ajuste cargo'),
        ('AJUSTE_ABONO', 'Ajuste abono'),
    ]

    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name='movimientos_prestamo_cobro')
    prestamo = models.ForeignKey(PrestamoCobro, on_delete=models.CASCADE, related_name='movimientos')
    cliente = models.ForeignKey(Cliente, on_delete=models.PROTECT, related_name='movimientos_prestamo_cobro')
    cuenta = models.ForeignKey(
        CuentaFinancieraCobro,
        on_delete=models.PROTECT,
        related_name='movimientos_prestamo',
        null=True,
        blank=True
    )

    fecha = models.DateTimeField(auto_now_add=True)
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES)
    monto = models.DecimalField(max_digits=12, decimal_places=2)

    saldo_anterior = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    saldo_nuevo = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    metodo_pago = models.ForeignKey(MetodoPago, on_delete=models.PROTECT, null=True, blank=True)
    referencia = models.CharField(max_length=100, blank=True, null=True)
    observacion = models.TextField(blank=True, null=True)

    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    anulado = models.BooleanField(default=False)

    class Meta:
        verbose_name = "Movimiento de préstamo"
        verbose_name_plural = "Movimientos de préstamo"
        ordering = ['fecha', 'id']
        indexes = [
            models.Index(fields=['empresa', 'cliente', 'fecha']),
        ]

    def __str__(self):
        return f"{self.prestamo.numero} - {self.get_tipo_display()}"

    def save(self, *args, **kwargs):
        es_nuevo = self.pk is None

        if es_nuevo and self.prestamo_id:
            saldo_actual = self.prestamo.saldo or Decimal('0.00')
            self.saldo_anterior = saldo_actual

            if self.tipo in ['CUOTA', 'ABONO_CAPITAL', 'AJUSTE_ABONO']:
                self.saldo_nuevo = saldo_actual - self.monto
            else:
                self.saldo_nuevo = saldo_actual + self.monto

        super().save(*args, **kwargs)

        if self.prestamo_id:
            total_abonos = self.prestamo.movimientos.filter(
                tipo__in=['CUOTA', 'ABONO_CAPITAL', 'AJUSTE_ABONO'],
                anulado=False
            ).aggregate(total=models.Sum('monto'))['total'] or Decimal('0.00')

            total_cargos = self.prestamo.movimientos.filter(
                tipo__in=['DESEMBOLSO', 'INTERES', 'MORA', 'AJUSTE_CARGO'],
                anulado=False
            ).aggregate(total=models.Sum('monto'))['total'] or Decimal('0.00')

            self.prestamo.saldo = total_cargos - total_abonos

            if self.prestamo.estado != 'ANULADO':
                self.prestamo.estado = 'PAGADO' if self.prestamo.saldo <= 0 else 'ACTIVO'

            self.prestamo.save(update_fields=['saldo', 'estado'])
            
# ==============================
# COMPRAS FINANCIADAS
# ==============================
class CompraFinanciada(models.Model):
    ESTADO_CHOICES = [
        ('ACTIVA', 'Activa'),
        ('PAGADA', 'Pagada'),
        ('VENCIDA', 'Vencida'),
        ('ANULADA', 'Anulada'),
    ]

    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name='compras_financiadas')
    cliente = models.ForeignKey(Cliente, on_delete=models.PROTECT, related_name='compras_financiadas')

    numero = models.CharField(max_length=30)
    fecha = models.DateField()

    descripcion = models.CharField(max_length=255)
    monto_producto = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    cuota_inicial = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    interes = models.DecimalField(max_digits=5, decimal_places=2, default=0)

    total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_abonado = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    saldo = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    cuotas = models.PositiveIntegerField(default=1)
    frecuencia_dias = models.PositiveIntegerField(default=30)

    estado = models.CharField(max_length=10, choices=ESTADO_CHOICES, default='ACTIVA')
    observacion = models.TextField(blank=True, null=True)

    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Compra financiada"
        verbose_name_plural = "Compras financiadas"
        unique_together = ('empresa', 'numero')
        indexes = [
            models.Index(fields=['empresa', 'cliente', 'estado']),
            models.Index(fields=['empresa', 'fecha']),
        ]

    def __str__(self):
        return f"{self.numero} - {self.cliente}"

    def recalcular_saldo(self):
        total_abonos = self.movimientos.filter(
            tipo__in=['CUOTA', 'ABONO_EXTRA', 'AJUSTE_ABONO'],
            anulado=False
        ).aggregate(total=models.Sum('monto'))['total'] or Decimal('0.00')

        total_cargos = self.movimientos.filter(
            tipo__in=['CARGO_INICIAL', 'INTERES', 'MORA', 'AJUSTE_CARGO'],
            anulado=False
        ).aggregate(total=models.Sum('monto'))['total'] or Decimal('0.00')

        self.total_abonado = total_abonos
        self.saldo = total_cargos - total_abonos

        if self.estado != 'ANULADA':
            self.estado = 'PAGADA' if self.saldo <= 0 else 'ACTIVA'

        self.save(update_fields=['total_abonado', 'saldo', 'estado'])

class MovimientoCompraFinanciada(models.Model):
    TIPO_CHOICES = [
        ('CARGO_INICIAL', 'Cargo inicial'),
        ('CUOTA', 'Cuota'),
        ('ABONO_EXTRA', 'Abono extra'),
        ('INTERES', 'Interés'),
        ('MORA', 'Mora'),
        ('AJUSTE_CARGO', 'Ajuste cargo'),
        ('AJUSTE_ABONO', 'Ajuste abono'),
    ]

    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name='movimientos_compra_financiada')
    compra = models.ForeignKey(CompraFinanciada, on_delete=models.CASCADE, related_name='movimientos')
    cliente = models.ForeignKey(Cliente, on_delete=models.PROTECT, related_name='movimientos_compra_financiada')

    fecha = models.DateTimeField(auto_now_add=True)
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES)
    monto = models.DecimalField(max_digits=12, decimal_places=2)

    saldo_anterior = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    saldo_nuevo = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    metodo_pago = models.ForeignKey(MetodoPago, on_delete=models.PROTECT, null=True, blank=True)
    referencia = models.CharField(max_length=100, blank=True, null=True)
    observacion = models.TextField(blank=True, null=True)

    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    anulado = models.BooleanField(default=False)

    class Meta:
        verbose_name = "Movimiento de compra financiada"
        verbose_name_plural = "Movimientos de compras financiadas"
        ordering = ['fecha', 'id']
        indexes = [
            models.Index(fields=['empresa', 'cliente', 'fecha']),
        ]

    def __str__(self):
        return f"{self.compra.numero} - {self.get_tipo_display()}"

    def save(self, *args, **kwargs):
        es_nuevo = self.pk is None

        if es_nuevo and self.compra_id:
            saldo_actual = self.compra.saldo or Decimal('0.00')
            self.saldo_anterior = saldo_actual

            if self.tipo in ['CUOTA', 'ABONO_EXTRA', 'AJUSTE_ABONO']:
                self.saldo_nuevo = saldo_actual - self.monto
            else:
                self.saldo_nuevo = saldo_actual + self.monto

        super().save(*args, **kwargs)

        if self.compra_id:
            self.compra.recalcular_saldo()

# ==============================
# CUENTAS FINANCIERAS / BANCOS
# ==============================

