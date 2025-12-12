from django.contrib import admin
from .models import *
# ==============================================================================
# 1. ADMINS CENTRALES (MULTITENANCY Y CONFIGURACIÓN)
# ==============================================================================

@admin.register(Empresa)
class EmpresaAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'ruc', 'ambiente_sri', 'activa')
    list_filter = ('activa', 'ambiente_sri')
    search_fields = ('nombre', 'ruc')

@admin.register(Perfil)
class PerfilAdmin(admin.ModelAdmin):
    list_display = ('user', 'empresa')
    list_filter = ('empresa',)
    autocomplete_fields = ['user']

@admin.register(PuntoVenta)
class PuntoVentaAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'empresa', 'codigo_establecimiento', 'codigo_punto_emision', 'secuencial_factura', 'activo')
    list_filter = ('empresa', 'activo')
    search_fields = ('nombre', 'codigo_establecimiento', 'codigo_punto_emision')

# ==============================================================================
# 2. ADMINS DE DATOS MAESTROS (CLIENTES, PROVEEDORES, PRODUCTOS)
# ==============================================================================

@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'ruc', 'email', 'empresa')
    search_fields = ('nombre', 'ruc')
    list_filter = ('empresa',)

@admin.register(Producto)
class ProductoAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'codigo', 'categoria', 'marca', 'precio', 'stock', 'maneja_iva', 'activo')
    list_filter = ('empresa', 'categoria', 'marca', 'maneja_iva', 'activo')
    search_fields = ('nombre', 'codigo')
    list_editable = ('precio', 'stock', 'activo')

# Registramos modelos más simples directamente
admin.site.register(Categoria)
admin.site.register(Marca)
admin.site.register(Modelo)
admin.site.register(Proveedor)
admin.site.register(MetodoPago)


# ==============================================================================
# 3. ADMINS TRANSACCIONALES (COTIZACIONES Y FACTURAS CON DETALLES INLINE)
# ==============================================================================

class CotizacionDetalleInline(admin.TabularInline):
    """Permite añadir/editar detalles de la cotización DENTRO de la cotización."""
    model = CotizacionDetalle
    extra = 1 # Número de filas extra para añadir
    autocomplete_fields = ['producto']

@admin.register(Cotizacion)
class CotizacionAdmin(admin.ModelAdmin):
    list_display = ('id', 'cliente', 'fecha_emision', 'fecha_vencimiento', 'estado', 'importe_total', 'factura_generada')
    list_filter = ('estado', 'empresa', 'fecha_emision')
    search_fields = ('id', 'cliente__nombre')
    readonly_fields = ('total_sin_impuestos', 'total_descuento', 'total_con_impuestos', 'importe_total', 'factura_generada', 'usuario')
    autocomplete_fields = ['cliente']
    inlines = [CotizacionDetalleInline]
    
    def save_model(self, request, obj, form, change):
        if not obj.pk: # Si es un objeto nuevo
            obj.usuario = request.user
        super().save_model(request, obj, form, change)

class FacturaDetalleInline(admin.TabularInline):
    """Permite añadir/editar detalles de la factura DENTRO de la factura."""
    model = FacturaDetalle
    extra = 0 # No mostrar extras, ya que se generan desde una cotización
    readonly_fields = ('producto', 'cantidad', 'precio_unitario', 'descuento', 'precio_total_sin_impuesto', 'impuestos')
    can_delete = False

@admin.register(Factura)
class FacturaAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'cliente', 'fecha_emision', 'estado_sri', 'importe_total')
    list_filter = ('estado_sri', 'empresa', 'fecha_emision')
    search_fields = ('secuencial', 'cliente__nombre', 'clave_acceso')
    readonly_fields = (
        'empresa', 'cliente', 'punto_venta', 'usuario', 'ambiente', 'tipo_emision',
        'secuencial', 'clave_acceso', 'fecha_emision', 'total_sin_impuestos',
        'total_descuento', 'total_con_impuestos', 'propina', 'importe_total',
        'moneda', 'pagos', 'fecha_autorizacion', 'xml_generado',
        'xml_autorizado', 'xml_firmado', 'sri_error'
    )
    inlines = [FacturaDetalleInline]

# ==============================================================================
# 4. OTROS MODELOS
# ==============================================================================
admin.site.register(Bitacora)
admin.site.register(MovimientoInventario)
# Registro básico
admin.site.register(Empresa)


# Registro avanzado para Cuentas
@admin.register(CuentaBancaria)
class CuentaBancariaAdmin(admin.ModelAdmin):
    list_display = ('numero_cuenta', 'cliente', 'tipo', 'saldo', 'activa')
    search_fields = ('numero_cuenta', 'cliente__nombre')
    list_filter = ('tipo', 'activa')

# Registro para ver las transacciones
@admin.register(TransaccionBancaria)
class TransaccionBancariaAdmin(admin.ModelAdmin):
    list_display = ('fecha', 'cuenta', 'tipo', 'monto')
    list_filter = ('tipo', 'fecha')