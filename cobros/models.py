from django.db import models
from django.conf import settings
from decimal import Decimal
from core.models import *

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
class PrestamoCobro(models.Model):
    ESTADO_CHOICES = [
        ('ACTIVO', 'Activo'),
        ('PAGADO', 'Pagado'),
        ('VENCIDO', 'Vencido'),
        ('ANULADO', 'Anulado'),
    ]

    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name='prestamos_cobro')
    cliente = models.ForeignKey(Cliente, on_delete=models.PROTECT, related_name='prestamos_cobro')

    numero = models.CharField(max_length=30)
    fecha = models.DateField()
    monto = models.DecimalField(max_digits=12, decimal_places=2)
    interes = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
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