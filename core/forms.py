from django.forms import formset_factory, modelformset_factory
from django import forms
from .models import *

class ProveedorForm(forms.ModelForm):
    class Meta:
        model = Proveedor
        # Define los campos del modelo que quieres en tu formulario
        fields = ['nombre', 'ruc', 'telefono', 'direccion', 'email']
        
        # Opcional: Personaliza cómo se ven los campos en el HTML
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control'}),
            'ruc': forms.TextInput(attrs={'class': 'form-control'}),
            'telefono': forms.TextInput(attrs={'class': 'form-control'}),
            'direccion': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
        }

class ProductoForm(forms.ModelForm):
    class Meta:
        model = Producto
        fields = ['nombre', 'codigo', 'descripcion', 'categoria', 'marca', 'modelo', 'stock', 'costo', 'precio', 'maneja_iva']
        
        # AÑADIMOS WIDGETS PARA LOS ESTILOS DE BOOTSTRAP
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

class CategoriaForm(forms.ModelForm):
    class Meta:
        model = Categoria
        fields = ['nombre']
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control'}),
        }

class MarcaForm(forms.ModelForm):
    class Meta:
        model = Marca
        fields = ['nombre']
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control'}),
        }

class ModeloForm(forms.ModelForm):
    class Meta:
        model = Modelo
        fields = ['marca', 'nombre']
        widgets = {
            'marca': forms.Select(attrs={'class': 'form-select'}),
            'nombre': forms.TextInput(attrs={'class': 'form-control'}),
        }

    # Esta función es clave: asegura que en el formulario de "Nuevo Modelo"
    # solo aparezcan las marcas de la empresa del usuario actual.
    def __init__(self, *args, **kwargs):
        empresa = kwargs.pop('empresa', None)
        super(ModeloForm, self).__init__(*args, **kwargs)
        if empresa:
            self.fields['marca'].queryset = Marca.objects.filter(empresa=empresa)

class CompraForm(forms.ModelForm):
    class Meta:
        model = Compra
        fields = ['proveedor', 'fecha']
        widgets = {
            # Usamos un DateInput que sea compatible con los calendarios de HTML5
            'fecha': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            # El proveedor se manejará con Select2 en la plantilla
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

# Creamos el FormSet a partir del formulario de detalle
CompraDetalleFormSet = formset_factory(CompraDetalleForm, extra=1)
# 'extra=1' significa que el formulario se mostrará con una fila vacía por defecto.
class CotizacionForm(forms.ModelForm):
    cliente = forms.ModelChoiceField(
        queryset=Cliente.objects.none(), # Se llenará en la vista
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
    # Campo para seleccionar el producto, se filtrará por empresa en la vista/template
    producto = forms.ModelChoiceField(
        queryset=Producto.objects.all(), # El queryset puede ser genérico
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

# Usamos un FormSet para manejar múltiples líneas de detalle en el formulario
CotizacionDetalleFormSet = modelformset_factory(
    CotizacionDetalle,
    form=CotizacionDetalleForm,
    extra=0, # Muestra un formulario vacío por defecto
    can_delete=True, # Permite eliminar líneas
    can_delete_extra=True
)


class FacturaForm(forms.ModelForm):
    punto_venta = forms.ModelChoiceField(
        queryset=PuntoVenta.objects.none(),
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    class Meta:
        model = Factura
        fields = ['cliente', 'punto_venta', 'fecha_emision', 'metodo_pago'] # Campos principales
        widgets = {
            'fecha_emision': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        empresa = kwargs.pop('empresa', None)
        super().__init__(*args, **kwargs)
        if empresa:
            self.fields['cliente'].queryset = Cliente.objects.filter(empresa=empresa)
            self.fields['punto_venta'].queryset = PuntoVenta.objects.filter(empresa=empresa, activo=True)
            self.fields['metodo_pago'].queryset = MetodoPago.objects.filter(empresa=empresa)
            self.fields['cliente'].widget.attrs.update({'class': 'form-control select2'})
FacturaDetalleForm = CotizacionDetalleForm

FacturaDetalleFormSet = modelformset_factory(
    FacturaDetalle,
    form=FacturaDetalleForm,
    extra=0,
    can_delete=True,
    can_delete_extra=True
)

class FacturaDetalleForm(forms.ModelForm):
    class Meta:
        model = FacturaDetalle
        fields = ['producto', 'cantidad', 'precio_unitario'] # El precio se autocompletará
        widgets = {
            'producto': forms.Select(attrs={'class': 'form-select producto-select'}),
            'cantidad': forms.NumberInput(attrs={'class': 'form-control cantidad', 'step': '1'}),
            'precio_unitario': forms.NumberInput(attrs={'class': 'form-control precio', 'step': '0.01'}),
        }

    def __init__(self, *args, **kwargs):
        empresa = kwargs.pop('empresa', None)
        super(FacturaDetalleForm, self).__init__(*args, **kwargs)
        if empresa:
            self.fields['producto'].queryset = Producto.objects.filter(empresa=empresa, activo=True)

FacturaDetalleFormSet = formset_factory(FacturaDetalleForm, extra=1)

class ClienteForm(forms.ModelForm):
    class Meta:
        model = Cliente
        fields = ['nombre', 'ruc', 'email', 'direccion', 'telefono']
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control form-control-sm', 'placeholder': 'Nombre'}),
            'ruc': forms.TextInput(attrs={'class': 'form-control form-control-sm', 'placeholder': 'RUC'}),
            'email': forms.EmailInput(attrs={'class': 'form-control form-control-sm', 'placeholder': 'Email'}),
            'telefono': forms.TextInput(attrs={'class': 'form-control form-control-sm', 'placeholder': 'Teléfono'}),
            # rows: 1 hace que la dirección ocupe solo una línea de alto
            'direccion': forms.Textarea(attrs={'class': 'form-control form-control-sm', 'rows': 1, 'placeholder': 'Dirección'}),
        }

class MetodoPagoForm(forms.ModelForm):
    class Meta:
        model = MetodoPago
        fields = ['nombre']
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control'}),
        }

class PuntoVentaForm(forms.ModelForm):
    class Meta:
        model = PuntoVenta
        # Excluimos los secuenciales porque se manejan automáticamente
        fields = ['nombre', 'codigo_establecimiento', 'codigo_punto_emision', 'activo']
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control'}),
            'codigo_establecimiento': forms.TextInput(attrs={'class': 'form-control'}),
            'codigo_punto_emision': forms.TextInput(attrs={'class': 'form-control'}),
            'activo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        labels = {
            'nombre': 'Nombre descriptivo (Ej: Matriz, Sucursal Quito)',
            'codigo_establecimiento': 'Código de Establecimiento (SRI, ej: 001)',
            'codigo_punto_emision': 'Código de Punto de Emisión (SRI, ej: 001)',
            'activo': 'Este punto de venta está activo',
        }

class ProveedorForm(forms.ModelForm):
    class Meta:
        model = Proveedor
        # Campos que el usuario llenará en el modal
        fields = ['empresa','ruc','nombre','email','telefono','direccion']

class EmpresaConfigForm(forms.ModelForm):
    class Meta:
        model = Empresa
        # Definimos los únicos campos que el usuario podrá editar desde esta pantalla
        fields = ['iva_porcentaje', 'firma_electronica', 'clave_firma']
        widgets = {
            'iva_porcentaje': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01'
            }),
            'firma_electronica': forms.FileInput(attrs={
                'class': 'form-control'
            }),
            'clave_firma': forms.PasswordInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ingrese la clave solo si desea cambiarla'
            }),
        }
        help_texts = {
            'firma_electronica': 'Sube un nuevo archivo .p12 solo si deseas reemplazar el actual.',
        }

