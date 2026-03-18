from django import forms
from .models import *

class CategoriaCobroForm(forms.ModelForm):
    class Meta:
        model = CategoriaCobro
        fields = ['nombre', 'activo']

class EstadoCuentaCobroForm(forms.ModelForm):
    class Meta:
        model = EstadoCuentaCobro
        fields = [
            'cliente',
            'factura',
            'fecha_emision',
            'fecha_vencimiento',
            'total_documento',
            'categoria',
            'estado',
            'observacion',
        ]

class MovimientoCobroForm(forms.ModelForm):
    class Meta:
        model = MovimientoCobro
        fields = [
            'tipo',
            'monto',
            'metodo_pago',
            'referencia',
            'observacion',
        ]

class PromesaPagoForm(forms.ModelForm):
    class Meta:
        model = PromesaPago
        fields = [
            'fecha_promesa',
            'monto_prometido',
            'estado',
            'observacion',
        ]

class PrestamoCobroForm(forms.ModelForm):
    class Meta:
        model = PrestamoCobro
        fields = [
            'fecha',
            'cliente',
            'cuenta_desembolso',
            'monto',
            'interes',
            'tipo_interes',
            'estado',
            'observacion',
        ]
        widgets = {
            'fecha': forms.DateInput(attrs={
                'class': 'form-control form-control-sm',
                'type': 'date'
            }),
            'cliente': forms.Select(attrs={
                'class': 'form-select form-select-sm',
                'id': 'id_cliente'
            }),
            'cuenta_desembolso': forms.Select(attrs={
                'class': 'form-select form-select-sm',
                'id': 'id_cuenta_desembolso'
            }),
            'monto': forms.NumberInput(attrs={
                'class': 'form-control form-control-sm',
                'step': '0.01'
            }),
            'interes': forms.NumberInput(attrs={
                'class': 'form-control form-control-sm',
                'step': '0.01'
            }),
            'tipo_interes': forms.Select(attrs={
                'class': 'form-select form-select-sm',
                'id': 'id_tipo_interes'
            }),
            'estado': forms.Select(attrs={
                'class': 'form-select form-select-sm'
            }),
            'observacion': forms.Textarea(attrs={
                'class': 'form-control form-control-sm',
                'rows': 2
            }),
        }
        
class CuentaFinancieraCobroForm(forms.ModelForm):
    class Meta:
        model = CuentaFinancieraCobro
        fields = [
            'nombre',
            'tipo',
            'banco',
            'numero_cuenta',
            'titular',
            'saldo_actual',
            'activo',
            'observacion',
        ]
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control form-control-sm'}),
            'tipo': forms.Select(attrs={'class': 'form-select form-select-sm'}),
            'banco': forms.TextInput(attrs={'class': 'form-control form-control-sm'}),
            'numero_cuenta': forms.TextInput(attrs={'class': 'form-control form-control-sm'}),
            'titular': forms.TextInput(attrs={'class': 'form-control form-control-sm'}),
            'saldo_actual': forms.NumberInput(attrs={'class': 'form-control form-control-sm', 'step': '0.01'}),
            'activo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'observacion': forms.Textarea(attrs={'class': 'form-control form-control-sm', 'rows': 2}),
        }

class MovimientoPrestamoCobroForm(forms.ModelForm):
    class Meta:
        model = MovimientoPrestamoCobro
        fields = [
            'tipo',
            'monto',
            'metodo_pago',
            'referencia',
            'observacion',
        ]

class CompraFinanciadaForm(forms.ModelForm):
    class Meta:
        model = CompraFinanciada
        fields = [
            'fecha',
            'cliente',
            'descripcion',
            'monto_producto',
            'cuota_inicial',
            'interes',
            'cuotas',
            'frecuencia_dias',
            'estado',
            'observacion',
        ]
        widgets = {
            'fecha': forms.DateInput(attrs={'class': 'form-control form-control-sm', 'type': 'date'}),
            'cliente': forms.Select(attrs={'class': 'form-select form-select-sm'}),
            'descripcion': forms.TextInput(attrs={'class': 'form-control form-control-sm'}),
            'monto_producto': forms.NumberInput(attrs={'class': 'form-control form-control-sm', 'step': '0.01'}),
            'cuota_inicial': forms.NumberInput(attrs={'class': 'form-control form-control-sm', 'step': '0.01'}),
            'interes': forms.NumberInput(attrs={'class': 'form-control form-control-sm', 'step': '0.01'}),
            'cuotas': forms.NumberInput(attrs={'class': 'form-control form-control-sm', 'min': '1'}),
            'frecuencia_dias': forms.NumberInput(attrs={'class': 'form-control form-control-sm', 'min': '1'}),
            'estado': forms.Select(attrs={'class': 'form-select form-select-sm'}),
            'observacion': forms.Textarea(attrs={'class': 'form-control form-control-sm', 'rows': 2}),
        }

class MovimientoPrestamoCobroForm(forms.ModelForm):
    class Meta:
        model = MovimientoPrestamoCobro
        fields = [
            'tipo',
            'monto',
            'metodo_pago',
            'referencia',
            'observacion',
        ]
        widgets = {
            'tipo': forms.Select(attrs={
                'class': 'form-select form-select-sm'
            }),
            'monto': forms.NumberInput(attrs={
                'class': 'form-control form-control-sm',
                'step': '0.01'
            }),
            'metodo_pago': forms.Select(attrs={
                'class': 'form-select form-select-sm'
            }),
            'referencia': forms.TextInput(attrs={
                'class': 'form-control form-control-sm'
            }),
            'observacion': forms.Textarea(attrs={
                'class': 'form-control form-control-sm',
                'rows': 2
            }),
        }

class MovimientoCompraFinanciadaForm(forms.ModelForm):
    class Meta:
        model = MovimientoCompraFinanciada
        fields = [
            'tipo',
            'monto',
            'metodo_pago',
            'referencia',
            'observacion',
        ]
        widgets = {
            'tipo': forms.Select(attrs={'class': 'form-select form-select-sm'}),
            'monto': forms.NumberInput(attrs={'class': 'form-control form-control-sm', 'step': '0.01'}),
            'metodo_pago': forms.Select(attrs={'class': 'form-select form-select-sm'}),
            'referencia': forms.TextInput(attrs={'class': 'form-control form-control-sm'}),
            'observacion': forms.Textarea(attrs={'class': 'form-control form-control-sm', 'rows': 2}),
        }