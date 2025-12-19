from django import forms
from django.forms import inlineformset_factory, formset_factory, modelformset_factory
from .models import *

# ==========================================
# 1. CONFIGURACIÓN Y MANTENIMIENTOS BÁSICOS
# ==========================================

class EmpresaConfigForm(forms.ModelForm):
    class Meta:
        model = Empresa
        fields = ['iva_porcentaje', 'firma_electronica', 'clave_firma']
        widgets = {
            'iva_porcentaje': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'firma_electronica': forms.FileInput(attrs={'class': 'form-control'}),
            'clave_firma': forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Ingrese la clave solo si desea cambiarla'}),
        }
        help_texts = {
            'firma_electronica': 'Sube un nuevo archivo .p12 solo si deseas reemplazar el actual.',
        }

class PuntoVentaForm(forms.ModelForm):
    class Meta:
        model = PuntoVenta
        fields = ['nombre', 'codigo_establecimiento', 'codigo_punto_emision', 'activo']
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control'}),
            'codigo_establecimiento': forms.TextInput(attrs={'class': 'form-control'}),
            'codigo_punto_emision': forms.TextInput(attrs={'class': 'form-control'}),
            'activo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

class MetodoPagoForm(forms.ModelForm):
    class Meta:
        model = MetodoPago
        fields = ['nombre']
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control'}),
        }

class ClienteForm(forms.ModelForm):
    class Meta:
        model = Cliente
        fields = ['nombre', 'ruc', 'email', 'direccion', 'telefono']
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control form-control-sm', 'placeholder': 'Nombre'}),
            'ruc': forms.TextInput(attrs={'class': 'form-control form-control-sm', 'placeholder': 'RUC'}),
            'email': forms.EmailInput(attrs={'class': 'form-control form-control-sm', 'placeholder': 'Email'}),
            'telefono': forms.TextInput(attrs={'class': 'form-control form-control-sm', 'placeholder': 'Teléfono'}),
            'direccion': forms.Textarea(attrs={'class': 'form-control form-control-sm', 'rows': 1, 'placeholder': 'Dirección'}),
        }

class ProveedorForm(forms.ModelForm):
    class Meta:
        model = Proveedor
        fields = ['nombre', 'ruc', 'telefono', 'email', 'direccion']
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control form-control-sm', 'placeholder': 'Nombre de la empresa'}),
            'ruc': forms.TextInput(attrs={'class': 'form-control form-control-sm', 'placeholder': 'RUC'}),
            'telefono': forms.TextInput(attrs={'class': 'form-control form-control-sm'}),
            'email': forms.EmailInput(attrs={'class': 'form-control form-control-sm'}),
            'direccion': forms.Textarea(attrs={'class': 'form-control form-control-sm', 'rows': 1}),
        }

# ==========================================
# 2. INVENTARIO (PRODUCTOS, MARCAS, ETC)
# ==========================================

class CategoriaForm(forms.ModelForm):
    class Meta:
        model = Categoria
        fields = ['nombre']
        widgets = {'nombre': forms.TextInput(attrs={'class': 'form-control'})}

class MarcaForm(forms.ModelForm):
    class Meta:
        model = Marca
        fields = ['nombre']
        widgets = {'nombre': forms.TextInput(attrs={'class': 'form-control'})}

class ModeloForm(forms.ModelForm):
    class Meta:
        model = Modelo
        fields = ['marca', 'nombre']
        widgets = {
            'marca': forms.Select(attrs={'class': 'form-select'}),
            'nombre': forms.TextInput(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        empresa = kwargs.pop('empresa', None)
        super(ModeloForm, self).__init__(*args, **kwargs)
        if empresa:
            self.fields['marca'].queryset = Marca.objects.filter(empresa=empresa)

class ProductoForm(forms.ModelForm):
    class Meta:
        model = Producto
        fields = ['nombre', 'codigo', 'descripcion', 'categoria', 'marca', 'modelo', 'stock', 'costo', 'precio', 'maneja_iva']
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control'}),
            'codigo': forms.TextInput(attrs={'class': 'form-control'}),
            'descripcion': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'categoria': forms.Select(attrs={'class': 'form-select'}),
            'marca': forms.Select(attrs={'class': 'form-select'}),
            'modelo': forms.Select(attrs={'class': 'form-select'}),
            'stock': forms.NumberInput(attrs={'class': 'form-control'}),
            'costo': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'precio': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'maneja_iva': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        empresa = kwargs.pop('empresa', None)
        super(ProductoForm, self).__init__(*args, **kwargs)
        if empresa:
            self.fields['categoria'].queryset = Categoria.objects.filter(empresa=empresa)
            self.fields['marca'].queryset = Marca.objects.filter(empresa=empresa)
            self.fields['modelo'].queryset = Modelo.objects.filter(empresa=empresa)

# ==========================================
# 3. COMPRAS
# ==========================================

class CompraForm(forms.ModelForm):
    class Meta:
        model = Compra
        fields = ['proveedor', 'fecha']
        widgets = {
            'fecha': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'proveedor': forms.Select(attrs={'class': 'form-select'}),
        }
    
    def __init__(self, *args, **kwargs):
        empresa = kwargs.pop('empresa', None)
        super(CompraForm, self).__init__(*args, **kwargs)
        if empresa:
            self.fields['proveedor'].queryset = Proveedor.objects.filter(empresa=empresa)

class CompraDetalleForm(forms.ModelForm):
    class Meta:
        model = CompraDetalle
        fields = ['producto', 'cantidad', 'costo_unitario']
        widgets = {
            'producto': forms.Select(attrs={'class': 'form-select producto-select'}),
            'cantidad': forms.NumberInput(attrs={'class': 'form-control cantidad', 'step': '1'}),
            'costo_unitario': forms.NumberInput(attrs={'class': 'form-control costo', 'step': '0.01'}),
        }

    def __init__(self, *args, **kwargs):
        empresa = kwargs.pop('empresa', None)
        super(CompraDetalleForm, self).__init__(*args, **kwargs)
        if empresa:
            self.fields['producto'].queryset = Producto.objects.filter(empresa=empresa)

CompraDetalleFormSet = formset_factory(CompraDetalleForm, extra=1)

# ==========================================
# 4. COTIZACIONES
# ==========================================

class CotizacionForm(forms.ModelForm):
    cliente = forms.ModelChoiceField(
        queryset=Cliente.objects.none(),
        widget=forms.Select(attrs={'class': 'form-control select2'})
    )

    class Meta:
        model = Cotizacion
        fields = ['cliente', 'fecha_vencimiento', 'terminos_y_condiciones']
        widgets = {
            'fecha_vencimiento': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'terminos_y_condiciones': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        empresa = kwargs.pop('empresa', None)
        super().__init__(*args, **kwargs)
        if empresa:
            self.fields['cliente'].queryset = Cliente.objects.filter(empresa=empresa)

class CotizacionDetalleForm(forms.ModelForm):
    producto = forms.ModelChoiceField(
        queryset=Producto.objects.all(),
        widget=forms.HiddenInput()
    )
    class Meta:
        model = CotizacionDetalle
        fields = ['producto', 'cantidad', 'precio_unitario', 'descuento']
        widgets = {
            'cantidad': forms.NumberInput(attrs={'class': 'form-control cantidad', 'step': '0.01'}),
            'precio_unitario': forms.NumberInput(attrs={'class': 'form-control precio-unitario', 'step': '0.01'}),
            'descuento': forms.NumberInput(attrs={'class': 'form-control descuento', 'step': '0.01'}),
        }

CotizacionDetalleFormSet = modelformset_factory(
    CotizacionDetalle,
    form=CotizacionDetalleForm,
    extra=0,
    can_delete=True,
    can_delete_extra=True
)

# ==========================================
# 5. VENTAS / FACTURACIÓN (NUEVO CÓDIGO)
# ==========================================

class FacturaForm(forms.ModelForm):
    class Meta:
        model = Factura
        fields = ['cliente', 'punto_venta', 'metodo_pago', 'fecha_emision']
        widgets = {
            'cliente': forms.Select(attrs={'class': 'form-select form-select-sm'}),
            'punto_venta': forms.Select(attrs={'class': 'form-select form-select-sm'}),
            'metodo_pago': forms.Select(attrs={'class': 'form-select form-select-sm'}),
            'fecha_emision': forms.DateInput(attrs={'class': 'form-control form-control-sm', 'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        empresa = kwargs.pop('empresa', None)
        super(FacturaForm, self).__init__(*args, **kwargs)
        if empresa:
            self.fields['cliente'].queryset = Cliente.objects.filter(empresa=empresa)
            self.fields['punto_venta'].queryset = PuntoVenta.objects.filter(empresa=empresa, activo=True)
            self.fields['metodo_pago'].queryset = MetodoPago.objects.filter(empresa=empresa)

class FacturaDetalleForm(forms.ModelForm):
    class Meta:
        model = FacturaDetalle
        fields = ['producto', 'cantidad', 'precio_unitario']
        widgets = {
            # Las clases CSS aquí son CRÍTICAS para que funcione el JavaScript de cálculo
            'producto': forms.Select(attrs={'class': 'form-select form-select-sm producto-select'}),
            'cantidad': forms.NumberInput(attrs={'class': 'form-control form-control-sm text-center cantidad-input', 'step': '0.01'}),
            'precio_unitario': forms.NumberInput(attrs={'class': 'form-control form-control-sm text-end precio-input', 'step': '0.01'}),
        }

# Usamos inlineformset_factory para manejar la relación Factura -> Detalles automáticamente
DetalleFacturaFormSet = inlineformset_factory(
    Factura, 
    FacturaDetalle, 
    form=FacturaDetalleForm,
    extra=1,           
    can_delete=True     
)

# --- Formularios Ligeros para AJAX (Modals en Ventas) ---

class ClienteAjaxForm(forms.ModelForm):
    class Meta:
        model = Cliente
        fields = ['nombre', 'ruc', 'email', 'telefono', 'direccion']

class MetodoPagoAjaxForm(forms.ModelForm):
    class Meta:
        model = MetodoPago
        fields = ['nombre']