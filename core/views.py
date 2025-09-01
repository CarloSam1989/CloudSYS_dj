from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, Http404
from .services import crear_nueva_venta
from . import sri_services
from .tasks import procesar_factura_electronica_task
from .tasks import reenviar_factura_email_task
from decimal import Decimal
from django.core.serializers.json import DjangoJSONEncoder
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.db.models import Sum
from django.db.models.functions import TruncMonth
from datetime import datetime
from dateutil.relativedelta import relativedelta
from django.db import transaction
import json
from django.http import JsonResponse
from django.db.models import Q 
from django.http import HttpResponse
from django.template.loader import render_to_string
from weasyprint import HTML
# Importa tus modelos
from .models import *
from .forms import *

# ------------------------------
# LOGIN Y LOGOUT
# ------------------------------

def login_view(request):
    """ Vista para iniciar sesión """
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':
        username_from_form = request.POST.get('username')
        password_from_form = request.POST.get('password')

        user = authenticate(request, username=username_from_form, password=password_from_form)

        if user is not None:
            login(request, user)
            return redirect('dashboard')
        else:
            messages.error(request, 'Usuario o contraseña incorrectos.')
            return render(request, 'login.html')

    return render(request, 'login.html')

def logout_view(request):
    """ Cierra sesión y redirige al login """
    logout(request)
    messages.success(request, 'Has cerrado sesión exitosamente.')
    return redirect('login')

# ------------------------------
# DASHBOARD
# ------------------------------

@login_required
def dashboard_view(request):
    """
    Controla toda la lógica para mostrar los datos en el panel principal.
    """
    empresa_actual = request.user.perfil.empresa
    today = timezone.now()

    # --- 1. INDICADORES ---
    total_vendido_mes = Factura.objects.filter(
        empresa=empresa_actual,
        fecha_emision__year=today.year,
        fecha_emision__month=today.month
    ).aggregate(total=Sum('importe_total'))['total'] or 0

    total_comprado_mes = Compra.objects.filter(
        empresa=empresa_actual,
        fecha__year=today.year,
        fecha__month=today.month,
        estado='A'
    ).aggregate(total=Sum('total'))['total'] or 0

    stock_bajo = Producto.objects.filter(
        empresa=empresa_actual,
        stock__lt=5
    ).count()

    facturas_pendientes_sri = Factura.objects.filter(
        empresa=empresa_actual,
        estado_sri='P'
    ).count()

    indicadores = {
        'total_vendido': f"{total_vendido_mes:,.2f}",
        'total_comprado': f"{total_comprado_mes:,.2f}",
        'stock_bajo': stock_bajo,
        'facturas_pendientes': facturas_pendientes_sri,
    }

    # --- 2. GRÁFICO COMPRAS VS VENTAS ---
    fecha_inicio = today - relativedelta(months=5)
    fecha_inicio = fecha_inicio.replace(day=1)

    ventas_por_mes = Factura.objects.filter(
        empresa=empresa_actual,
        fecha_emision__gte=fecha_inicio
    ).annotate(
        mes=TruncMonth('fecha_emision')
    ).values('mes').annotate(
        total_ventas=Sum('importe_total')
    ).order_by('mes')

    compras_por_mes = Compra.objects.filter(
        empresa=empresa_actual,
        fecha__gte=fecha_inicio
    ).annotate(
        mes=TruncMonth('fecha')
    ).values('mes').annotate(
        total_compras=Sum('total')
    ).order_by('mes')

    ventas_dict = {v['mes'].strftime('%b %Y'): float(v['total_ventas']) for v in ventas_por_mes}
    compras_dict = {c['mes'].strftime('%b %Y'): float(c['total_compras']) for c in compras_por_mes}

    labels_grafico = [(fecha_inicio + relativedelta(months=i)).strftime('%b %Y') for i in range(6)]
    data_ventas = [ventas_dict.get(label, 0) for label in labels_grafico]
    data_compras = [compras_dict.get(label, 0) for label in labels_grafico]

    grafico_data = {
        "labels": labels_grafico,
        "ventas": data_ventas,
        "compras": data_compras,
    }

    # --- 3. CLIENTES NUEVOS ESTE MES ---
    clientes_nuevos_mes = Cliente.objects.filter(
        empresa=empresa_actual,
        fecha_creacion__year=today.year,
        fecha_creacion__month=today.month
    ).count()

    # --- CONTEXTO FINAL ---
    context = {
        'indicadores': indicadores,
        'clientes_nuevos': clientes_nuevos_mes,
        'grafico_json': json.dumps(grafico_data),
    }

    return render(request, 'dashboard.html', context)

# ------------------------------
# VISTAS DE MÓDULOS (PLACEHOLDERS)
# ------------------------------
@login_required
def inventario_view(request):
    return render(request, 'base.html') # Temporalmente muestra la base

@login_required
def proveedores_view(request):
    empresa_actual = request.user.perfil.empresa

    # Lógica para procesar el formulario cuando se envía (POST)
    if request.method == 'POST':
        form = ProveedorForm(request.POST)
        if form.is_valid():
            # No guardes todavía, primero asigna la empresa
            proveedor = form.save(commit=False)
            proveedor.empresa = empresa_actual
            proveedor.save()
            
            messages.success(request, '¡Proveedor guardado exitosamente!')
            return redirect('proveedores') # Redirige a la misma página para limpiar el form
        else:
            # Si el formulario tiene errores, se mostrarán en el modal
            messages.error(request, 'Por favor, corrige los errores en el formulario.')

    # Lógica para mostrar la página (GET)
    else:
        form = ProveedorForm()

    # Obtener todos los proveedores de la empresa actual para mostrarlos en la tabla
    proveedores = Proveedor.objects.filter(empresa=empresa_actual).order_by('nombre')
    
    context = {
        'proveedores': proveedores,
        'form': form, # Pasamos el formulario a la plantilla
    }
    
    return render(request, 'proveedores.html', context)

@login_required
def editar_proveedor_view(request, pk):
    empresa_actual = request.user.perfil.empresa
    # Busca el proveedor por su ID (pk) y asegúrate de que pertenezca a la empresa del usuario
    proveedor = get_object_or_404(Proveedor, pk=pk, empresa=empresa_actual)

    if request.method == 'POST':
        # Si se envía el formulario, procesa los datos
        form = ProveedorForm(request.POST, instance=proveedor)
        if form.is_valid():
            form.save()
            messages.success(request, f'Proveedor "{proveedor.nombre}" actualizado exitosamente.')
            return redirect('proveedores')
    else:
        # Si solo se está viendo la página, muestra el formulario con los datos del proveedor
        form = ProveedorForm(instance=proveedor)

    context = {
        'form': form
    }
    return render(request, 'editar_proveedor.html', context)

@login_required
def eliminar_proveedor_view(request, pk):
    empresa_actual = request.user.perfil.empresa
    proveedor = get_object_or_404(Proveedor, pk=pk, empresa=empresa_actual)

    if request.method == 'POST':
        nombre_proveedor = proveedor.nombre
        proveedor.delete()
        messages.success(request, f'Proveedor "{nombre_proveedor}" eliminado exitosamente.')
        return redirect('proveedores')

    context = {
        'proveedor': proveedor
    }
    return render(request, 'eliminar_proveedor.html', context)

@login_required
def facturacion_view(request):
    empresa_actual = request.user.perfil.empresa
    facturas = Factura.objects.filter(
        empresa=empresa_actual
    ).order_by('-fecha_emision', '-id')
    
    context = {
        'facturas': facturas,
    }
    return render(request, 'facturacion.html', context)

@login_required
def config_empresa_view(request):
    return render(request, 'base.html') # Temporalmente muestra la base

@login_required
def config_view(request): 
    return render(request, 'base.html') # Temporalmente muestra la base

@login_required
def inventario_view(request):
    empresa_actual = request.user.perfil.empresa
    
    if request.method == 'POST':
        form = ProductoForm(request.POST, empresa=empresa_actual)
        if form.is_valid():
            producto = form.save(commit=False)
            producto.empresa = empresa_actual
            producto.save()
            messages.success(request, '¡Producto guardado exitosamente!')
            return redirect('inventario')
        else:
            messages.error(request, 'Por favor, corrige los errores en el formulario.')
    else:
        form = ProductoForm(empresa=empresa_actual)

    productos = Producto.objects.filter(empresa=empresa_actual).order_by('nombre')
    
    context = {
        'productos': productos,
        'form': form,
    }
    return render(request, 'inventario.html', context)

@login_required
def editar_producto_view(request, pk):
    empresa_actual = request.user.perfil.empresa
    producto = get_object_or_404(Producto, pk=pk, empresa=empresa_actual)

    if request.method == 'POST':
        form = ProductoForm(request.POST, instance=producto, empresa=empresa_actual)
        if form.is_valid():
            form.save()
            messages.success(request, f'Producto "{producto.nombre}" actualizado exitosamente.')
            return redirect('inventario')
    else:
        form = ProductoForm(instance=producto, empresa=empresa_actual)

    context = {'form': form}
    return render(request, 'editar_producto.html', context)

@login_required
def eliminar_producto_view(request, pk):
    empresa_actual = request.user.perfil.empresa
    producto = get_object_or_404(Producto, pk=pk, empresa=empresa_actual)

    if request.method == 'POST':
        nombre_producto = producto.nombre
        producto.delete()
        messages.success(request, f'Producto "{nombre_producto}" eliminado exitosamente.')
        return redirect('inventario')

    context = {'producto': producto}
    return render(request, 'eliminar_producto.html', context)

@login_required
def agregar_categoria_ajax(request):
    if request.method == 'POST':
        form = CategoriaForm(request.POST)
        if form.is_valid():
            categoria = form.save(commit=False)
            categoria.empresa = request.user.perfil.empresa
            categoria.save()
            # Devuelve el nuevo objeto como JSON
            return JsonResponse({'status': 'success', 'id': categoria.id, 'nombre': categoria.nombre})
        return JsonResponse({'status': 'error', 'errors': form.errors})
    return JsonResponse({'status': 'error', 'message': 'Método no permitido'})

@login_required
def agregar_marca_ajax(request):
    if request.method == 'POST':
        form = MarcaForm(request.POST)
        if form.is_valid():
            marca = form.save(commit=False)
            marca.empresa = request.user.perfil.empresa
            marca.save()
            return JsonResponse({'status': 'success', 'id': marca.id, 'nombre': marca.nombre})
        return JsonResponse({'status': 'error', 'errors': form.errors})
    return JsonResponse({'status': 'error', 'message': 'Método no permitido'})

@login_required
def agregar_modelo_ajax(request):
    if request.method == 'POST':
        # Pasamos la empresa actual al formulario para filtrar las marcas
        form = ModeloForm(request.POST, empresa=request.user.perfil.empresa)
        if form.is_valid():
            modelo = form.save(commit=False)
            modelo.empresa = request.user.perfil.empresa
            modelo.save()
            # Devolvemos el nombre completo, ej: "Toyota Corolla"
            return JsonResponse({'status': 'success', 'id': modelo.id, 'nombre': str(modelo)})
        return JsonResponse({'status': 'error', 'errors': form.errors})
    return JsonResponse({'status': 'error', 'message': 'Método no permitido'})

@login_required
def compras_view(request):
    empresa_actual = request.user.perfil.empresa
    
    if request.method == 'POST':
        # Instanciamos el formulario principal y el formset con los datos POST
        compra_form = CompraForm(request.POST, empresa=empresa_actual)
        detalle_formset = CompraDetalleFormSet(request.POST, form_kwargs={'empresa': empresa_actual})

        # Verificamos que ambos sean válidos
        if compra_form.is_valid() and detalle_formset.is_valid():
            try:
                # Usamos una transacción para asegurar que todo se guarde o nada se guarde
                with transaction.atomic():
                    # Guardamos la cabecera de la compra
                    compra = compra_form.save(commit=False)
                    compra.empresa = empresa_actual
                    compra.save() # Se genera el ID de la compra

                    # Iteramos sobre los detalles del formset
                    total_compra = 0
                    for detalle_form in detalle_formset:
                        detalle = detalle_form.save(commit=False)
                        detalle.compra = compra # Asignamos la compra recién creada
                        
                        # Calculamos el subtotal de la línea
                        subtotal = detalle.cantidad * detalle.costo_unitario
                        total_compra += subtotal
                        
                        detalle.save()
                        
                        # Actualizar el stock del producto
                        producto = detalle.producto
                        producto.stock += detalle.cantidad
                        producto.save()
                    
                    # Actualizamos el total en la cabecera de la compra
                    compra.total = total_compra
                    compra.subtotal = total_compra # Asumiendo que no hay IVA por ahora
                    compra.save()

                messages.success(request, '¡Compra registrada exitosamente!')
                return redirect('compras')

            except Exception as e:
                messages.error(request, f'Ocurrió un error al guardar la compra: {e}')
        else:
            messages.error(request, 'Por favor, corrige los errores en el formulario.')

    else:
        # Si es GET, mostramos los formularios vacíos
        compra_form = CompraForm(empresa=empresa_actual)
        detalle_formset = CompraDetalleFormSet(form_kwargs={'empresa': empresa_actual})
    
    # Obtenemos las compras existentes para mostrarlas en la tabla
    compras = Compra.objects.filter(empresa=empresa_actual).order_by('-fecha')
    
    context = {
        'compras': compras,
        'compra_form': compra_form,
        'detalle_formset': detalle_formset,
    }
    return render(request, 'compras.html', context)

@login_required
def buscar_productos_ajax(request):
    empresa_actual = request.user.perfil.empresa
    search_term = request.GET.get('term', '')
    
    productos = Producto.objects.filter(
        Q(nombre__icontains=search_term) | Q(codigo__icontains=search_term),
        empresa=empresa_actual
    )[:10]
    
    results = []
    for producto in productos:
        results.append({
            'id': producto.id,
            'text': f"{producto.nombre} ({producto.codigo}) - Stock: {producto.stock}",
            'stock': producto.stock,
            'precio_venta': producto.precio 
        })

    return JsonResponse({'results': results})

@login_required
def anular_compra_view(request, pk):
    empresa_actual = request.user.perfil.empresa
    compra = get_object_or_404(Compra, pk=pk, empresa=empresa_actual)

    if compra.estado == 'A':
        try:
            with transaction.atomic():
                compra.estado = 'N' # Cambia el estado a Anulada
                compra.save()

                # Revertir el stock de cada producto en el detalle
                for detalle in compra.detalles.all():
                    producto = detalle.producto
                    producto.stock -= detalle.cantidad
                    # Aquí podrías recalcular el costo promedio si lo necesitas
                    producto.save()
            
            messages.success(request, f'Compra #{compra.id} anulada y stock revertido.')
        except Exception as e:
            messages.error(request, f'Error al anular la compra: {e}')
    else:
        messages.warning(request, 'Esta compra ya está anulada.')

    return redirect('compras')

@login_required
def compra_pdf_view(request, pk):
    empresa_actual = request.user.perfil.empresa
    compra = get_object_or_404(Compra, pk=pk, empresa=empresa_actual)
    
    # Renderizamos una plantilla HTML
    html_string = render_to_string('compra_pdf.html', {'compra': compra})

    # Convertimos el HTML a PDF
    html = HTML(string=html_string)
    pdf = html.write_pdf()

    # Devolvemos el PDF como una respuesta de archivo
    response = HttpResponse(pdf, content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="compra_{compra.id}.pdf"'
    return response

@login_required
def restaurar_compra_view(request, pk):
    empresa_actual = request.user.perfil.empresa
    compra = get_object_or_404(Compra, pk=pk, empresa=empresa_actual)

    if compra.estado == 'N':
        try:
            with transaction.atomic():
                compra.estado = 'A' # Cambia el estado a Activa
                compra.save()

                # Re-aplicar el stock y recalcular costo promedio
                for detalle in compra.detalles.all():
                    producto = detalle.producto
                    stock_antiguo = producto.stock
                    costo_antiguo = producto.costo
                    cantidad_nueva = detalle.cantidad
                    costo_nuevo_compra = detalle.costo_unitario
                    
                    nuevo_stock = stock_antiguo + cantidad_nueva
                    if nuevo_stock > 0:
                        producto.costo = ((stock_antiguo * costo_antiguo) + (cantidad_nueva * costo_nuevo_compra)) / nuevo_stock
                    else:
                        producto.costo = costo_nuevo_compra
                    
                    producto.stock = nuevo_stock
                    producto.save()
            
            messages.success(request, f'Compra #{compra.id} restaurada y stock actualizado.')
        except Exception as e:
            messages.error(request, f'Error al restaurar la compra: {e}')
    else:
        messages.warning(request, 'Esta compra no está anulada.')

    return redirect('compras')

@login_required
def corregir_compra_view(request, pk):
    empresa_actual = request.user.perfil.empresa
    compra_original = get_object_or_404(Compra, pk=pk, empresa=empresa_actual)

    if compra_original.estado == 'A':
        # ... (la lógica de anulación no cambia) ...
        try:
            with transaction.atomic():
                compra_original.estado = 'N'
                compra_original.save()
                for detalle in compra_original.detalles.all():
                    producto = detalle.producto
                    producto.stock -= detalle.cantidad
                    producto.save()
            messages.info(request, f'Compra #{compra_original.id} anulada. Por favor, guarde la nueva versión corregida.')
        except Exception as e:
            messages.error(request, f'Error al anular la compra original para corrección: {e}')
            return redirect('compras')
    else:
        messages.warning(request, 'Solo se pueden corregir compras activas.')
        return redirect('compras')

    # Preparar datos para el nuevo formulario
    compra_initial_data = {
        'proveedor': compra_original.proveedor,
        'fecha': compra_original.fecha.strftime('%Y-%m-%d'),
    }
    
    detalle_initial_data = []
    # Preparamos una lista separada para el JavaScript
    detalle_json_data = [] 
    for detalle in compra_original.detalles.all():
        detalle_initial_data.append({
            'producto': detalle.producto,
            'cantidad': detalle.cantidad,
            'costo_unitario': detalle.costo_unitario,
        })
        # Añadimos el precio de venta a nuestra lista para JS
        detalle_json_data.append({
            'precio_venta': detalle.producto.precio
        })
    
    compra_form = CompraForm(initial=compra_initial_data, empresa=empresa_actual)
    CompraDetalleFormSetEdit = formset_factory(CompraDetalleForm, extra=0)
    detalle_formset = CompraDetalleFormSetEdit(initial=detalle_initial_data, form_kwargs={'empresa': empresa_actual})

    compras = Compra.objects.filter(empresa=empresa_actual).order_by('-fecha')
    
    context = {
        'compras': compras,
        'compra_form': compra_form,
        'detalle_formset': detalle_formset,
        'open_modal_on_load': True,
        # Pasamos los datos extra como JSON a la plantilla
        'detalle_json_data': json.dumps(detalle_json_data, cls=DjangoJSONEncoder),
    }
    return render(request, 'compras.html', context)

@login_required
def ventas_view(request):
    empresa_actual = request.user.perfil.empresa
    
    if request.method == 'POST':
        factura_form = FacturaForm(request.POST, empresa=empresa_actual)
        detalle_formset = FacturaDetalleFormSet(request.POST, form_kwargs={'empresa': empresa_actual}, prefix='detalle')

        if factura_form.is_valid() and detalle_formset.is_valid():
            
            # Filtramos para quedarnos solo con las filas que tienen productos
            detalles_validos = [
                form.cleaned_data for form in detalle_formset 
                if form.has_changed() and form.cleaned_data.get('producto')
            ]

            if not detalles_validos:
                messages.error(request, "Error: La venta debe tener al menos un producto.")
            else:
                try:
                    # --- LLAMADA AL SERVICIO ---
                    # Toda la lógica compleja ahora vive en una sola función
                    factura = crear_nueva_venta(
                        factura_data=factura_form.cleaned_data,
                        detalles_data=detalles_validos,
                        empresa=empresa_actual,
                        usuario=request.user
                    )
                    messages.success(request, f'Venta #{factura.secuencial} registrada exitosamente!')
                    return redirect('ventas')
                
                except Exception as e:
                    messages.error(request, f'Ocurrió un error inesperado al guardar la venta: {e}')
        else:
            errores = {**factura_form.errors, **detalle_formset.errors}
            messages.error(request, f"Por favor, corrige los errores en el formulario: {errores}")

    # Lógica para la petición GET (no cambia)
    factura_form = FacturaForm(empresa=empresa_actual)
    detalle_formset = FacturaDetalleFormSet(form_kwargs={'empresa': empresa_actual}, prefix='detalle')
    ventas = Factura.objects.filter(empresa=empresa_actual).order_by('-fecha_emision')
    
    context = {
        'ventas': ventas,
        'factura_form': factura_form,
        'detalle_formset': detalle_formset,
    }
    return render(request, 'ventas.html', context)

@login_required
def anular_venta_view(request, pk):
    empresa_actual = request.user.perfil.empresa
    venta = get_object_or_404(Factura, pk=pk, empresa=empresa_actual)

    if venta.estado_pago != 'N':
        try:
            with transaction.atomic():
                venta.estado_pago = 'N'
                venta.save()
                for detalle in venta.detalles.all():
                    producto = detalle.producto
                    producto.stock += detalle.cantidad
                    producto.save()
            messages.success(request, f'Venta #{venta.secuencial} anulada y stock restaurado.')
        except Exception as e:
            messages.error(request, f'Error al anular la venta: {e}')
    else:
        messages.warning(request, 'Esta venta ya se encuentra anulada.')
    
    return redirect('ventas')

@login_required
def buscar_clientes_ajax(request):
    empresa_actual = request.user.perfil.empresa
    search_term = request.GET.get('term', '')
    
    clientes = Cliente.objects.filter(
        Q(nombre__icontains=search_term) | Q(ruc__icontains=search_term),
        empresa=empresa_actual
    )[:10]
    
    results = [{'id': cliente.id, 'text': f"{cliente.nombre} - {cliente.ruc}"} for cliente in clientes]
    return JsonResponse({'results': results})

@login_required
def agregar_cliente_ajax(request):
    if request.method == 'POST':
        form = ClienteForm(request.POST)
        if form.is_valid():
            cliente = form.save(commit=False)
            cliente.empresa = request.user.perfil.empresa
            cliente.save()
            return JsonResponse({'status': 'success', 'id': cliente.id, 'text': f"{cliente.nombre} - {cliente.ruc}"})
        return JsonResponse({'status': 'error', 'errors': form.errors})
    return JsonResponse({'status': 'error', 'message': 'Método no permitido'})

@login_required
def agregar_metodo_pago_ajax(request):
    if request.method == 'POST':
        form = MetodoPagoForm(request.POST)
        if form.is_valid():
            metodo = form.save(commit=False)
            metodo.empresa = request.user.perfil.empresa
            metodo.save()
            return JsonResponse({'status': 'success', 'id': metodo.id, 'nombre': metodo.nombre})
        return JsonResponse({'status': 'error', 'errors': form.errors})
    return JsonResponse({'status': 'error', 'message': 'Método no permitido'})

@login_required
def anular_venta_view(request, pk):
    empresa_actual = request.user.perfil.empresa
    venta = get_object_or_404(Factura, pk=pk, empresa=empresa_actual)

    if venta.estado_pago != 'N': # 'N' es Anulada
        try:
            with transaction.atomic():
                venta.estado_pago = 'N'
                venta.save()
                # Devolver el stock de los productos
                for detalle in venta.detalles.all():
                    producto = detalle.producto
                    producto.stock += detalle.cantidad
                    producto.save()
            messages.success(request, f'Venta #{venta.secuencial} anulada y stock restaurado.')
        except Exception as e:
            messages.error(request, f'Error al anular la venta: {e}')
    else:
        messages.warning(request, 'Esta venta ya se encuentra anulada.')
    
    return redirect('ventas')

@login_required
def venta_pdf_view(request, pk):
    empresa_actual = request.user.perfil.empresa
    venta = get_object_or_404(Factura, pk=pk, empresa=empresa_actual)
    
    html_string = render_to_string('venta_pdf.html', {'venta': venta})
    html = HTML(string=html_string)
    pdf = html.write_pdf()

    response = HttpResponse(pdf, content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="venta_{venta.secuencial}.pdf"'
    return response

@login_required
def config_empresa_view(request):
    empresa_actual = request.user.perfil.empresa

    if request.method == 'POST':
        form = PuntoVentaForm(request.POST)
        if form.is_valid():
            punto_venta = form.save(commit=False)
            punto_venta.empresa = empresa_actual
            punto_venta.save()
            messages.success(request, '¡Punto de Venta guardado exitosamente!')
            return redirect('config_empresa')
        else:
            messages.error(request, 'Hubo un error en el formulario. Por favor, revisa los datos.')
    else:
        form = PuntoVentaForm()

    puntos_venta = PuntoVenta.objects.filter(empresa=empresa_actual)
    context = {
        'form': form,
        'puntos_venta': puntos_venta,
        'empresa': empresa_actual, # Pasamos los datos de la empresa para mostrarlos
    }
    return render(request, 'config_empresa.html', context)

@login_required
def editar_puntoventa_view(request, pk):
    empresa_actual = request.user.perfil.empresa
    punto_venta = get_object_or_404(PuntoVenta, pk=pk, empresa=empresa_actual)

    if request.method == 'POST':
        form = PuntoVentaForm(request.POST, instance=punto_venta)
        if form.is_valid():
            form.save()
            messages.success(request, f'Punto de Venta "{punto_venta.nombre}" actualizado.')
            return redirect('config_empresa')
    else:
        form = PuntoVentaForm(instance=punto_venta)

    context = {
        'form': form,
    }
    return render(request, 'editar_puntoventa.html', context)

@login_required
def procesar_factura_ajax(request):
    if request.method == 'POST':
        factura_id = request.POST.get('factura_id')
        try:
            factura = Factura.objects.get(pk=factura_id, empresa=request.user.perfil.empresa)
            
            # Cambia el estado para que el usuario vea que se está procesando
            factura.estado_sri = 'P' # 'P' de Procesando
            factura.save()
            
            # Lanza la tarea en segundo plano
            procesar_factura_electronica_task.delay(factura_id)
            
            return JsonResponse({'status': 'ok', 'message': 'La factura ha sido enviada a procesar.'})
        except Factura.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Factura no encontrada.'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': f'Error inesperado: {str(e)}'})
            
    return JsonResponse({'status': 'error', 'message': 'Método no permitido.'})

@login_required
def consultar_estado_sri_ajax(request):
    factura_id = request.GET.get('factura_id')
    try:
        factura = Factura.objects.get(pk=factura_id, empresa=request.user.perfil.empresa)
        
        # Mapeo de estados a colores de Bootstrap
        status_colors = {'A': 'success', 'R': 'danger', 'P': 'primary'}
        color = status_colors.get(factura.estado_sri, 'secondary')
        
        return JsonResponse({
            'status': 'ok',
            'estado_sri': factura.get_estado_sri_display(),
            'estado_code': factura.estado_sri,
            'color': color
        })
    except Factura.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Factura no encontrada.'})

@login_required
def reenviar_factura_ajax(request):
    """
    Vista AJAX para recibir la solicitud de reenvío de una factura por correo.
    """
    # 1. Se asegura de que la petición sea de tipo POST
    if request.method == 'POST':
        factura_id = request.POST.get('factura_id')
        try:
            # 2. Busca la factura y verifica que pertenezca a la empresa del usuario
            factura = Factura.objects.get(pk=factura_id, empresa=request.user.perfil.empresa)
            
            # 3. Verifica que la factura esté AUTORIZADA ('A')
            if factura.estado_sri == 'A':
                # 4. Delega el trabajo pesado a la tarea de Celery
                reenviar_factura_email_task.delay(factura_id)
                
                # 5. Responde inmediatamente al navegador con un mensaje de éxito
                return JsonResponse({'status': 'ok', 'message': f'La factura se está enviando a {factura.cliente.email}.'})
            else:
                return JsonResponse({'status': 'error', 'message': 'Solo se pueden reenviar facturas autorizadas.'})
        
        except Factura.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Factura no encontrada.'})
            
    return JsonResponse({'status': 'error', 'message': 'Método no permitido.'})

@login_required
def clientes_view(request):
    empresa_actual = request.user.perfil.empresa
    
    # --- LÓGICA PARA CREAR UN NUEVO CLIENTE (POST) ---
    if request.method == 'POST':
        form = ClienteForm(request.POST)
        if form.is_valid():
            cliente = form.save(commit=False)
            cliente.empresa = empresa_actual # Asigna la empresa del usuario actual
            cliente.save()
            messages.success(request, '¡Cliente creado exitosamente!')
            return redirect('clientes') # Redirige a la misma página para ver el nuevo cliente en la lista
        else:
            # Si el formulario no es válido, muestra los errores
            messages.error(request, f'Por favor, corrige los errores: {form.errors}')

    # --- LÓGICA PARA MOSTRAR LA PÁGINA (GET) ---
    form = ClienteForm() # Un formulario vacío para crear un nuevo cliente
    clientes = Cliente.objects.filter(empresa=empresa_actual)
    
    context = {
        'form': form,
        'clientes': clientes
    }
    return render(request, 'clientes.html', context)

@login_required
def descargar_xml_view(request, factura_id):
    try:
        # Busca la factura, asegurándose de que pertenezca a la empresa del usuario
        factura = Factura.objects.get(
            pk=factura_id, 
            empresa=request.user.perfil.empresa
        )
        
        # Verifica que la factura esté autorizada y tenga un XML guardado
        if factura.estado_sri == 'A' and factura.xml_autorizado:
            # Crea una respuesta HTTP con el contenido del XML
            response = HttpResponse(factura.xml_autorizado, content_type='application/xml')
            
            # Añade una cabecera para que el navegador lo trate como un archivo adjunto
            response['Content-Disposition'] = f'attachment; filename="factura-{factura.secuencial}.xml"'
            
            return response
        else:
            # Si no está autorizada o no hay XML, devuelve un error 404
            raise Http404("El XML para esta factura no está disponible.")
            
    except Factura.DoesNotExist:
        raise Http404("Factura no encontrada.")
    
# Ubicación: core/views.py

@login_required
def descargar_xml_generado_view(request, factura_id):
    try:
        factura = Factura.objects.get(pk=factura_id, empresa=request.user.perfil.empresa)
        
        if factura.xml_generado:
            response = HttpResponse(factura.xml_generado, content_type='application/xml')
            response['Content-Disposition'] = f'attachment; filename="factura-generada-{factura.secuencial}.xml"'
            return response
        else:
            raise Http404("El XML generado para esta factura no está disponible.")
            
    except Factura.DoesNotExist:
        raise Http404("Factura no encontrada.")
    
@login_required
def descargar_xml_firmado_view(request, factura_id):
    """
    Busca una factura que ya ha sido procesada y devuelve su XML firmado
    (antes de la autorización del SRI) para ser descargado.
    """
    try:
        # Busca la factura por su ID, asegurándose de que pertenezca a la empresa del usuario actual.
        factura = Factura.objects.get(
            pk=factura_id, 
            empresa=request.user.perfil.empresa
        )
        
        # Verifica que el campo xml_firmado contenga datos.
        if factura.xml_firmado:
            # 1. Crea una respuesta HTTP con el contenido del XML y el tipo de contenido correcto.
            response = HttpResponse(factura.xml_firmado, content_type='application/xml')
            
            # 2. Añade una cabecera para que el navegador lo trate como un archivo adjunto para descargar.
            #    El nombre del archivo será, por ejemplo, "factura-firmada-000000001.xml".
            response['Content-Disposition'] = f'attachment; filename="factura-firmada-{factura.secuencial}.xml"'
            
            return response
        else:
            # Si el campo está vacío, significa que el XML firmado no está disponible.
            raise Http404("El XML firmado para esta factura no está disponible. Asegúrese de procesarla primero.")
            
    except Factura.DoesNotExist:
        # Si no se encuentra una factura con ese ID, devuelve un error 404.
        raise Http404("Factura no encontrada.")
    
@login_required
def buscar_proveedores_ajax(request):
    """
    Busca proveedores por nombre o RUC para el autocompletado de Select2.
    """
    search_term = request.GET.get('q', '').strip()
    
    if search_term:
        # Busca proveedores cuya razón social O RUC contenga el término de búsqueda
        proveedores = Proveedor.objects.filter(
            Q(nombre__icontains=search_term) | Q(ruc__icontains=search_term),
            empresa=request.user.perfil.empresa
        ).order_by('nombre')[:10] # Limita a 10 resultados por eficiencia

        results = [
            {'id': p.id, 'text': f"{p.razon_social} - {p.ruc}"} 
            for p in proveedores
        ]
    else:
        results = []

    return JsonResponse({'results': results})

@login_required
def agregar_proveedor_ajax(request):
    """
    Recibe datos por POST para crear un nuevo proveedor sin recargar la página.
    """
    if request.method == 'POST':
        form = ProveedorForm(request.POST)
        if form.is_valid():
            proveedor = form.save(commit=False)
            proveedor.empresa = request.user.perfil.empresa
            proveedor.save()
            # Respuesta para Select2: el 'id' y el 'text' que se mostrará
            return JsonResponse({
                'status': 'success',
                'id': proveedor.id,
                'text': f"{proveedor.razon_social} - {proveedor.ruc}"
            })
        # Si el formulario no es válido, devuelve los errores
        return JsonResponse({'status': 'error', 'errors': form.errors})
    
    return JsonResponse({'status': 'error', 'message': 'Método no permitido'})