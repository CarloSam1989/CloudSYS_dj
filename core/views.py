from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, Http404
from .services import crear_nueva_venta
from datetime import date
from .sri_services import generar_clave_acceso, IVA_MAP
from erp_project.celery import app
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
import time
# ------------------------------
# LOGIN Y LOGOUT
# ------------------------------
@login_required
def home_banking_view(request):
    try:
        # 1. Identificar quién es el cliente basado en el usuario logueado
        # Gracias al OneToOneField, podemos acceder con request.user.perfil_cliente
        cliente_actual = request.user.perfil_cliente
        
        # 2. Buscar SOLO las cuentas de este cliente
        mis_cuentas = cliente_actual.cuentas_bancarias.all() # Usando el related_name del modelo CuentaBancaria
        
        # 3. Buscar los últimos movimientos (opcional, uniendo todas las cuentas)
        ultimos_movimientos = []
        for cuenta in mis_cuentas:
            ultimos_movimientos.extend(cuenta.transacciones.all().order_by('-fecha')[:5])

        return render(request, 'banco/dashboard.html', {
            'cliente': cliente_actual,
            'cuentas': mis_cuentas,
            'movimientos': ultimos_movimientos
        })

    except AttributeError:
        # Caso de error: El usuario se logueó, pero no está asignado a ningún Cliente en la BD
        return render(request, 'banco/error_no_cliente.html', {
            'mensaje': 'Tu usuario no tiene un perfil bancario asociado. Contacta al banco.'
        })

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
    Vista híbrida:
    1. Si es Cliente Banco -> Lo manda a su Home Banking.
    2. Si es Empleado ERP -> Le calcula y muestra el Dashboard Contable.
    """
    
    # --- 1. FILTRO DE BANQUITO (PRIORIDAD ALTA) ---
    # Si el usuario es un Cliente del Banco, lo sacamos de aquí inmediatamente.
    if hasattr(request.user, 'perfil_cliente') and request.user.perfil_cliente is not None:
        return redirect('home_banking')

    # --- 2. LÓGICA ERP (TU CÓDIGO MEJORADO) ---
    try:
        # Intentamos obtener la empresa. Si falla aquí, es porque no es empleado.
        empresa_actual = request.user.perfil.empresa 
        today = timezone.now()

        # === AQUI EMPIEZA TU LÓGICA DE CÁLCULO ===
        
        # A. Indicadores
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

        # B. Gráfico
        fecha_inicio = today - relativedelta(months=5)
        fecha_inicio = fecha_inicio.replace(day=1)

        ventas_por_mes = Factura.objects.filter(
            empresa=empresa_actual,
            fecha_emision__gte=fecha_inicio
        ).annotate(mes=TruncMonth('fecha_emision')).values('mes').annotate(
            total_ventas=Sum('importe_total')
        ).order_by('mes')

        compras_por_mes = Compra.objects.filter(
            empresa=empresa_actual,
            fecha__gte=fecha_inicio
        ).annotate(mes=TruncMonth('fecha')).values('mes').annotate(
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

        # C. Clientes Nuevos
        clientes_nuevos_mes = Cliente.objects.filter(
            empresa=empresa_actual,
            fecha_creacion__year=today.year,
            fecha_creacion__month=today.month
        ).count()

        context = {
            'empresa': empresa_actual, # Importante para que el header sepa qué empresa es
            'indicadores': indicadores,
            'clientes_nuevos': clientes_nuevos_mes,
            'grafico_json': json.dumps(grafico_data),
        }

        return render(request, 'dashboard.html', context)
        # === FIN DE TU LÓGICA ===

    except AttributeError:
        # --- 3. RED DE SEGURIDAD ---
        # Si el usuario NO tiene perfil de empleado y NO es cliente del banco
        # (Ej: un usuario superadmin nuevo que olvidaste configurar)
        if request.user.is_superuser:
            return redirect('/admin/')
            
        return render(request, 'banco/error_no_cliente.html', {
            'mensaje': 'Tu usuario no tiene rol asignado (Ni Empresa, ni Banca).'
        })

# ------------------------------
# VISTAS DE MÓDULOS (PLACEHOLDERS)
# ------------------------------

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

def crear_nueva_venta(factura_data, detalles_data, empresa, usuario):
    """
    Función de servicio para crear una factura (venta) con su detalle.
    Contiene toda la lógica de negocio.
    """
    with transaction.atomic():
        punto_venta = factura_data['punto_venta']

        # 1. Manejar el secuencial
        secuencial_actual = punto_venta.secuencial_factura
        punto_venta.secuencial_factura += 1
        punto_venta.save()
        secuencial_str = str(secuencial_actual).zfill(9)

        # 2. Generar la clave de acceso REAL
        clave_acceso = generar_clave_acceso(
            fecha=factura_data['fecha_emision'],
            tipo_comprobante='01',
            ruc=empresa.ruc,
            ambiente=empresa.ambiente_sri,
            serie=f"{punto_venta.codigo_establecimiento}{punto_venta.codigo_punto_emision}",
            secuencial=secuencial_str
        )

        # 3. Crear el objeto Factura en memoria
        factura = Factura(
            cliente=factura_data['cliente'],
            punto_venta=punto_venta,
            fecha_emision=factura_data['fecha_emision'],
            metodo_pago=factura_data.get('metodo_pago'),
            empresa=empresa,
            usuario=usuario,
            secuencial=secuencial_str,
            clave_acceso=clave_acceso,
            ambiente=empresa.ambiente_sri,
            tipo_emision='1',
            estado_sri='P',  # Procesando
        )

        # 4. Calcular totales
        total_sin_impuestos = 0
        base_imponible_iva = 0
        iva_total = 0
        iva_porcentaje = empresa.iva_porcentaje
        iva_rate = iva_porcentaje / 100
        codigo_porcentaje_iva = IVA_MAP.get(str(int(iva_porcentaje)), '2')

        for detalle_data in detalles_data:
            cantidad = detalle_data.get('cantidad', 0)
            precio = detalle_data.get('precio_unitario', 0)
            descuento = detalle_data.get('descuento', 0)
            producto = detalle_data.get('producto')
            
            subtotal_linea = (cantidad * precio) - descuento
            total_sin_impuestos += subtotal_linea
            
            if producto and producto.maneja_iva:
                base_imponible_iva += subtotal_linea
                iva_total += subtotal_linea * iva_rate
        
        # 5. Asignar totales a la factura y guardar
        factura.total_sin_impuestos = total_sin_impuestos
        factura.importe_total = total_sin_impuestos + iva_total
        factura.total_con_impuestos = {
            'totalImpuesto': [{'codigo': '2', 'codigoPorcentaje': codigo_porcentaje_iva, 'baseImponible': f"{base_imponible_iva:.2f}", 'valor': f"{iva_total:.2f}"}]
        }
        factura.save()

        # 6. Crear y guardar los detalles
        detalles_a_crear = []
        for detalle_data in detalles_data:
            detalle = FacturaDetalle(
                factura=factura,
                producto=detalle_data['producto'],
                cantidad=detalle_data['cantidad'],
                precio_unitario=detalle_data['precio_unitario'],
                descuento=detalle_data['descuento'],
            )
            subtotal_detalle = (detalle.cantidad * detalle.precio_unitario) - detalle.descuento
            detalle.precio_total_sin_impuesto = subtotal_detalle
            if detalle.producto.maneja_iva:
                iva_detalle = subtotal_detalle * iva_rate
                detalle.impuestos = {'impuestos': [{'codigo': '2', 'codigoPorcentaje': codigo_porcentaje_iva, 'tarifa': str(int(iva_porcentaje)), 'baseImponible': f"{subtotal_detalle:.2f}", 'valor': f"{iva_detalle:.2f}"}]}
            detalles_a_crear.append(detalle)
        
        FacturaDetalle.objects.bulk_create(detalles_a_crear)

        # 7. Lanzar la tarea de Celery
        app.send_task('core.tasks.enviar_factura_sri_task', args=[factura.id])

        return factura

@login_required
def ventas_view(request):
    empresa = request.user.perfil.empresa
    
    # Configuración inicial del Formset
    if request.method == 'POST':
        factura_form = FacturaForm(request.POST, empresa=empresa)
        detalle_formset = DetalleFacturaFormSet(request.POST)
        
        if factura_form.is_valid() and detalle_formset.is_valid():
            try:
                with transaction.atomic():
                    # 1. Preparar la Cabecera (Factura)
                    factura = factura_form.save(commit=False)
                    factura.empresa = empresa
                    factura.usuario = request.user
                    
                    # Generar Secuencial (Lógica simple basada en Punto de Venta)
                    punto_venta = factura.punto_venta
                    factura.secuencial = str(punto_venta.secuencial_factura).zfill(9)
                    # Generar Clave de Acceso (Dummy por ahora, requerida por el modelo)
                    import uuid
                    factura.clave_acceso = str(uuid.uuid4())
                    
                    # Valores temporales para guardar y obtener ID (se recalculan abajo)
                    factura.total_sin_impuestos = 0
                    factura.importe_total = 0
                    factura.save()
                    
                    # 2. Guardar Detalles y Actualizar Stock
                    detalles = detalle_formset.save(commit=False)
                    total_sin_impuestos = Decimal(0)
                    
                    for detalle in detalles:
                        detalle.factura = factura
                        detalle.precio_total_sin_impuesto = detalle.cantidad * detalle.precio_unitario
                        detalle.save()
                        
                        total_sin_impuestos += detalle.precio_total_sin_impuesto
                        
                        # -- MOVIMIENTO DE INVENTARIO (DESCONTAR STOCK) --
                        producto = detalle.producto
                        producto.stock -= detalle.cantidad
                        producto.save()
                        
                        MovimientoInventario.objects.create(
                            empresa=empresa,
                            producto=producto,
                            tipo='S', # Salida
                            cantidad=detalle.cantidad,
                            detalle_factura=detalle
                        )
                    
                    # Para manejar los eliminados en el formset
                    for obj in detalle_formset.deleted_objects:
                        obj.delete()

                    # 3. Actualizar Totales Finales de la Factura
                    # (Lógica simplificada de impuestos, ajustar según necesidad)
                    iva_total = total_sin_impuestos * (empresa.iva_porcentaje / 100)
                    factura.total_sin_impuestos = total_sin_impuestos
                    factura.total_con_impuestos = {"iva": str(iva_total)} # JSON
                    factura.importe_total = total_sin_impuestos + iva_total
                    
                    # Aumentar secuencial del punto de venta
                    punto_venta.secuencial_factura += 1
                    punto_venta.save()
                    
                    factura.save()
                    
                    return redirect('ventas') # Redirigir a la misma página (limpia)
                    
            except Exception as e:
                print(f"Error en transacción: {e}")
                # Aquí podrías agregar un mensaje de error al usuario
    else:
        factura_form = FacturaForm(empresa=empresa, initial={'fecha_emision': date.today()})
        detalle_formset = DetalleFacturaFormSet()

    # Obtener historial de ventas
    ultimas_ventas = Factura.objects.filter(empresa=empresa).order_by('-id')[:10]

    context = {
        'factura_form': factura_form,
        'detalle_formset': detalle_formset,
        'ventas': ultimas_ventas
    }
    return render(request, 'ventas.html', context)

# --- VISTAS AJAX (JSON) ---

@login_required
def buscar_productos_ajax(request):
    """ Busca productos por nombre o código para el Select2 """
    query = request.GET.get('q', '')
    empresa = request.user.perfil.empresa
    
    productos = Producto.objects.filter(
        Q(nombre__icontains=query) | Q(codigo__icontains=query),
        empresa=empresa,
        activo=True
    )[:20] # Limitar resultados
    
    results = []
    for p in productos:
        results.append({
            'id': p.id,
            'text': f"{p.codigo} - {p.nombre}", # Lo que ve el usuario
            'precio': str(p.precio),            # Datos extra para JS
            'stock': str(p.stock)
        })
    
    return JsonResponse({'results': results})

@login_required
def buscar_clientes_ajax(request):
    """ Busca clientes para el Select2 """
    query = request.GET.get('q', '')
    empresa = request.user.perfil.empresa
    
    clientes = Cliente.objects.filter(
        Q(nombre__icontains=query) | Q(ruc__icontains=query),
        empresa=empresa
    )[:20]
    
    results = [{'id': c.id, 'text': c.nombre} for c in clientes]
    return JsonResponse({'results': results})

@login_required
def agregar_cliente_ajax(request):
    if request.method == 'POST':
        form = ClienteAjaxForm(request.POST)
        if form.is_valid():
            cliente = form.save(commit=False)
            cliente.empresa = request.user.perfil.empresa
            cliente.save()
            return JsonResponse({'status': 'success', 'id': cliente.id, 'text': cliente.nombre})
    return JsonResponse({'status': 'error'})

@login_required
def agregar_metodo_pago_ajax(request):
    if request.method == 'POST':
        form = MetodoPagoAjaxForm(request.POST)
        if form.is_valid():
            metodo = form.save(commit=False)
            metodo.empresa = request.user.perfil.empresa
            metodo.save()
            return JsonResponse({'status': 'success', 'id': metodo.id, 'text': metodo.nombre})
    return JsonResponse({'status': 'error'})

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
            
            factura.estado_sri = 'P' # 'P' de Procesando
            factura.save()
            
            # 2. LLAMA A LA TAREA USANDO SU NOMBRE COMO STRING
            # El nombre es 'nombre_app.tasks.nombre_funcion'
            app.send_task('core.tasks.enviar_factura_sri_task', args=[factura_id])
            
            return JsonResponse({'status': 'ok', 'message': 'La factura ha sido enviada a procesar.'})
        except Factura.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Factura no encontrada.'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': f'Error inesperado: {str(e)}'})
            
    return JsonResponse({'status': 'error', 'message': 'Método no permitido.'})

@login_required
def consultar_estado_sri_ajax(request):
    """Esta vista está bien, no necesita cambios."""
    factura_id = request.GET.get('factura_id')
    try:
        factura = Factura.objects.get(pk=factura_id, empresa=request.user.perfil.empresa)
        
        status_colors = {'A': 'success', 'R': 'danger', 'P': 'primary'}
        color = status_colors.get(factura.estado_sri, 'secondary')
        
        return JsonResponse({
            'status': 'ok',
            'estado_sri': factura.get_estado_sri_display(),
            'estado_code': factura.estado_sri,
            'color': color,
            'sri_error': factura.sri_error, # Añadido: Envía el mensaje de error del SRI si existe
        })
    except Factura.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Factura no encontrada.'})

@login_required
def reenviar_factura_ajax(request):
    if request.method == 'POST':
        factura_id = request.POST.get('factura_id')
        try:
            factura = Factura.objects.get(pk=factura_id, empresa=request.user.perfil.empresa)
            
            if factura.estado_sri == 'A':
                # 3. LLAMA A LA TAREA DE REENVÍO TAMBIÉN POR SU NOMBRE
                app.send_task('core.tasks.enviar_factura_email_task', args=[factura_id])
                
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

@login_required
def convertir_cotizacion_a_factura_ajax(request):
    """
    Vista AJAX para convertir una cotización aceptada en una factura.
    Espera recibir 'cotizacion_id' y 'punto_venta_id' en la petición POST.
    """
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Método no permitido.'}, status=405)

    cotizacion_id = request.POST.get('cotizacion_id')
    punto_venta_id = request.POST.get('punto_venta_id')

    if not cotizacion_id or not punto_venta_id:
        return JsonResponse({'status': 'error', 'message': 'Faltan datos requeridos (cotización o punto de venta).'})

    try:
        empresa = request.user.perfil.empresa
        cotizacion = Cotizacion.objects.get(pk=cotizacion_id, empresa=empresa)
        punto_venta = PuntoVenta.objects.get(pk=punto_venta_id, empresa=empresa)

        if cotizacion.estado != 'A':
            return JsonResponse({'status': 'error', 'message': 'Solo se pueden facturar cotizaciones aceptadas.'})

        if cotizacion.factura_generada:
            return JsonResponse({'status': 'error', 'message': f'Esta cotización ya fue facturada (Factura #{cotizacion.factura_generada.id}).'})

        with transaction.atomic():
            # 1. Manejar el secuencial
            secuencial_actual = punto_venta.secuencial_factura
            punto_venta.secuencial_factura += 1
            punto_venta.save()
            secuencial_str = str(secuencial_actual).zfill(9)
            
            # ==========================================================
            #                 INICIO DE LA CORRECCIÓN
            # ==========================================================
            # Reemplazamos el texto fijo por una llamada a la función de servicio
            clave_acceso_generada = generar_clave_acceso(
                fecha=timezone.now().date(),
                tipo_comprobante='01',
                ruc=empresa.ruc,
                ambiente=empresa.ambiente_sri,
                serie=f"{punto_venta.codigo_establecimiento}{punto_venta.codigo_punto_emision}",
                secuencial=secuencial_str
            )
            # ==========================================================
            #                   FIN DE LA CORRECCIÓN
            # ==========================================================
            
            # 3. Crear el objeto Factura con la clave de acceso correcta
            nueva_factura = Factura.objects.create(
                empresa=empresa,
                cliente=cotizacion.cliente,
                punto_venta=punto_venta,
                usuario=request.user,
                ambiente=empresa.ambiente_sri,
                tipo_emision='1',
                secuencial=secuencial_str,
                clave_acceso=clave_acceso_generada, # <-- Ahora es una clave válida
                fecha_emision=timezone.now().date(),
                total_sin_impuestos=cotizacion.total_sin_impuestos,
                total_descuento=cotizacion.total_descuento,
                total_con_impuestos=cotizacion.total_con_impuestos,
                importe_total=cotizacion.importe_total,
                estado_sri='P',
                estado_pago='P',
            )

            # 4. Copiar los detalles
            detalles_a_crear = []
            for detalle_cot in cotizacion.detalles.all():
                detalles_a_crear.append(
                    FacturaDetalle(
                        factura=nueva_factura,
                        producto=detalle_cot.producto,
                        cantidad=detalle_cot.cantidad,
                        precio_unitario=detalle_cot.precio_unitario,
                        descuento=detalle_cot.descuento,
                        precio_total_sin_impuesto=detalle_cot.precio_total_sin_impuesto,
                        impuestos=detalle_cot.impuestos,
                    )
                )
            FacturaDetalle.objects.bulk_create(detalles_a_crear)

            # 5. Actualizar y enlazar la cotización
            cotizacion.factura_generada = nueva_factura
            cotizacion.estado = 'F'
            cotizacion.save()

        # 6. Enviar la tarea a Celery
        app.send_task('core.tasks.enviar_factura_sri_task', args=[nueva_factura.id])

        return JsonResponse({
            'status': 'ok',
            'message': 'Factura generada exitosamente y enviada a procesar.',
            'factura_id': nueva_factura.id
        })

    except (Cotizacion.DoesNotExist, PuntoVenta.DoesNotExist):
        return JsonResponse({'status': 'error', 'message': 'El recurso no existe o no pertenece a su empresa.'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': f'Error inesperado: {e}'})

def cotizaciones(request):
    """Vista principal de Cotizaciones (Lista + Formulario de Creación)"""
    if request.method == 'POST':
        form = CotizacionForm(request.POST)
        formset = DetalleCotizacionFormSet(request.POST)
        
        if form.is_valid() and formset.is_valid():
            try:
                with transaction.atomic():
                    cotizacion = form.save(commit=False)
                    # Calculamos total temporal (se puede recalcular despues)
                    cotizacion.total = 0 
                    cotizacion.save()
                    
                    total = 0
                    detalles = formset.save(commit=False)
                    for detalle in detalles:
                        detalle.cotizacion = cotizacion
                        detalle.subtotal = detalle.cantidad * detalle.precio_unitario
                        total += detalle.subtotal
                        detalle.save()
                    
                    # Actualizar total cabecera
                    cotizacion.total = total
                    cotizacion.save()
                    
                    messages.success(request, 'Cotización guardada correctamente.')
                    return redirect('cotizaciones')
            except Exception as e:
                messages.error(request, f'Error al guardar: {e}')
        else:
            messages.error(request, 'Error en el formulario. Revise los datos.')
    else:
        form = CotizacionForm()
        formset = DetalleCotizacionFormSet()

    # Listado para la tabla inferior
    cotizaciones_list = Cotizacion.objects.all().order_by('-fecha_emision')

    return render(request, 'cotizacion_lista.html', {
        'cotizacion_form': form,
        'detalle_formset': formset,
        'cotizaciones': cotizaciones_list
    })

def buscar_clientes_ajax(request):
    """AJAX: Busca clientes para el Select2"""
    query = request.GET.get('q', '')
    data = []
    if query:
        qs = Cliente.objects.filter(
            Q(nombre__icontains=query) | Q(dni__icontains=query)
        ).values('id', 'nombre', 'dni')[:20]
        for c in qs:
            data.append({'id': c['id'], 'text': f"{c['nombre']} ({c['dni']})"})
    return JsonResponse({'results': data})

@login_required
def detalle_cotizacion(request, cotizacion_id):
    """
    Muestra el detalle de una cotización específica.
    """
    empresa = request.user.perfil.empresa
    cotizacion = get_object_or_404(Cotizacion, pk=cotizacion_id, empresa=empresa)
    puntos_venta = PuntoVenta.objects.filter(empresa=empresa, activo=True)

    # ==========================================================
    #                 INICIO DE LA CORRECCIÓN
    # ==========================================================
    # Extraemos el valor del IVA de la estructura JSON guardada.
    iva_calculado = Decimal('0.00') # Valor por defecto
    try:
        # 1. Obtenemos la lista de impuestos (normalmente solo tendrá uno)
        total_impuesto_lista = cotizacion.total_con_impuestos.get('totalImpuesto', [])
        if total_impuesto_lista:
            # 2. Obtenemos el primer diccionario de la lista
            impuesto_dict = total_impuesto_lista[0]
            # 3. Obtenemos el valor y lo convertimos a Decimal
            iva_calculado = Decimal(impuesto_dict.get('valor', '0.00'))
    except (TypeError, IndexError):
        # Si el JSON está mal formado o vacío, iva_calculado se queda en 0.
        pass

    context = {
        'cotizacion': cotizacion,
        'puntos_venta': puntos_venta,
        'iva_porcentaje': empresa.iva_porcentaje, # Pasamos el % para mostrarlo en la etiqueta
        'iva_calculado': iva_calculado, # Pasamos el valor extraído del JSON
    }
    # ==========================================================
    #                   FIN DE LA CORRECCIÓN
    # ==========================================================
    
    return render(request, 'cotizacion_detalle.html', context)

@login_required
def crear_cotizacion(request):
    """
    Gestiona la creación (GET) y el procesamiento (POST) de una nueva cotización.
    """
    # Se define 'empresa' al inicio para que esté disponible en toda la vista.
    empresa = request.user.perfil.empresa

    if request.method == 'POST':
        form = CotizacionForm(request.POST, empresa=empresa)
        formset = CotizacionDetalleFormSet(request.POST, prefix='detalles', queryset=CotizacionDetalle.objects.none())

        if form.is_valid() and formset.is_valid():
            try:
                # Usamos una transacción para asegurar que toda la operación sea atómica.
                with transaction.atomic():
                    # 1. Preparar la cotización principal sin guardarla en la BD todavía
                    cotizacion = form.save(commit=False)
                    cotizacion.empresa = empresa
                    cotizacion.usuario = request.user
                    cotizacion.numero_cotizacion = f"COT-{int(time.time())}" # Generar número único

                    # 2. Calcular los totales a partir de los datos validados del formset
                    total_sin_impuestos = 0
                    base_imponible_iva = 0
                    iva_total = 0
                    iva_porcentaje = empresa.iva_porcentaje
                    iva_rate = iva_porcentaje / 100
                    
                    codigo_porcentaje_iva = IVA_MAP.get(str(int(iva_porcentaje)), '2')

                    # Filtramos las filas que no están marcadas para borrarse
                    detalles_validos = [f for f in formset.cleaned_data if f and not f.get('DELETE', False)]

                    if not detalles_validos:
                        raise Exception("Se debe añadir al menos un producto a la cotización.")

                    for detalle_data in detalles_validos:
                        cantidad = detalle_data.get('cantidad', 0)
                        precio = detalle_data.get('precio_unitario', 0)
                        descuento = detalle_data.get('descuento', 0)
                        producto = detalle_data.get('producto')
                        
                        subtotal_linea = (cantidad * precio) - descuento
                        total_sin_impuestos += subtotal_linea
                        
                        if producto and producto.maneja_iva:
                            base_imponible_iva += subtotal_linea
                            iva_total += subtotal_linea * iva_rate
                    
                    # 3. Asignar los totales calculados al objeto de cotización
                    cotizacion.total_sin_impuestos = total_sin_impuestos
                    cotizacion.importe_total = total_sin_impuestos + iva_total
                    cotizacion.total_con_impuestos = {
                        'totalImpuesto': [{
                            'codigo': '2', # Código para IVA
                            'codigoPorcentaje': codigo_porcentaje_iva,
                            'baseImponible': f"{base_imponible_iva:.2f}",
                            'valor': f"{iva_total:.2f}"
                        }]
                    }
                    
                    # 4. Guardar el objeto principal en la Base de Datos
                    cotizacion.save()

                    # 5. Guardar las líneas de detalle asociándolas a la cotización
                    detalles = formset.save(commit=False)
                    for detalle in detalles:
                        detalle.cotizacion = cotizacion
                        detalle.precio_total_sin_impuesto = (detalle.cantidad * detalle.precio_unitario) - detalle.descuento
                        
                        if detalle.producto.maneja_iva:
                            subtotal_detalle = detalle.precio_total_sin_impuesto
                            iva_detalle = subtotal_detalle * iva_rate
                            detalle.impuestos = {'impuestos': [{
                                'codigo': '2',
                                'codigoPorcentaje': codigo_porcentaje_iva,
                                'tarifa': str(int(iva_porcentaje)),
                                'baseImponible': f"{subtotal_detalle:.2f}",
                                'valor': f"{iva_detalle:.2f}"
                            }]}
                        detalle.save()

                messages.success(request, f"Cotización #{cotizacion.numero_cotizacion} creada exitosamente.")
                return redirect('cotizacion_detalle', cotizacion_id=cotizacion.id)

            except Exception as e:
                messages.error(request, f"Error al guardar la cotización: {e}")
        else:
            # Si el formulario no es válido, se construye un mensaje de error detallado
            error_string = "Por favor, corrige los errores: "
            for field, errors in form.errors.items():
                error_string += f"({field}: {', '.join(errors)}) "
            for i, form_errors in enumerate(formset.errors):
                if form_errors:
                    error_string += f"Línea {i+1}: {form_errors} "
            messages.error(request, error_string)

    else: # Método GET: Mostrar el formulario vacío
        form = CotizacionForm(empresa=empresa)
        formset = CotizacionDetalleFormSet(queryset=CotizacionDetalle.objects.none(), prefix='detalles')

    # Preparar el contexto para la plantilla
    productos = Producto.objects.filter(empresa=empresa, activo=True).values('id', 'nombre', 'precio', 'maneja_iva')
    iva_rate_decimal = empresa.iva_porcentaje / 100

    context = {
        'form': form,
        'formset': formset,
        'productos_json': list(productos),
        'iva_rate': iva_rate_decimal,
        'iva_porcentaje': empresa.iva_porcentaje,
    }
    return render(request, 'cotizacion_form.html', context)

@login_required
def configuracion_empresa(request):
    # Obtenemos la empresa del usuario que ha iniciado sesión
    empresa = request.user.perfil.empresa

    if request.method == 'POST':
        # Pasamos los datos del POST, los archivos y la instancia a actualizar
        form = EmpresaConfigForm(request.POST, request.FILES, instance=empresa)
        if form.is_valid():
            form.save()
            messages.success(request, '¡La configuración de la empresa se ha guardado exitosamente!')
            return redirect('config_empresa') # Redirigimos a la misma página
        else:
            messages.error(request, 'Por favor, corrige los errores en el formulario.')
    else:
        # Mostramos el formulario pre-llenado con los datos actuales de la empresa
        form = EmpresaConfigForm(instance=empresa)

    context = {
        'form': form
    }
    return render(request, 'configuracion_empresa.html', context)

@login_required
def cambiar_estado_cotizacion_ajax(request):
    if request.method == 'POST':
        cotizacion_id = request.POST.get('cotizacion_id')
        nuevo_estado = request.POST.get('nuevo_estado')
        
        # Validamos que el nuevo estado sea una opción válida
        valid_statuses = [choice[0] for choice in Cotizacion.ESTADO_CHOICES]
        if nuevo_estado not in valid_statuses:
            return JsonResponse({'status': 'error', 'message': 'Estado no válido.'})

        try:
            cotizacion = Cotizacion.objects.get(pk=cotizacion_id, empresa=request.user.perfil.empresa)
            cotizacion.estado = nuevo_estado
            cotizacion.save()
            return JsonResponse({'status': 'ok', 'message': f'Estado de la cotización actualizado a "{cotizacion.get_estado_display()}".'})
        except Cotizacion.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Cotización no encontrada.'})
            
    return JsonResponse({'status': 'error', 'message': 'Método no permitido.'})

@login_required
def generar_cotizacion_pdf(request, cotizacion_id):
    """
    Genera un archivo PDF para una cotización específica.
    """
    try:
        # 1. Obtener la cotización, asegurando que pertenezca a la empresa del usuario
        cotizacion = Cotizacion.objects.get(pk=cotizacion_id, empresa=request.user.perfil.empresa)

        # 2. Renderizar la plantilla HTML a una cadena de texto
        html_string = render_to_string('cotizacion_pdf.html', {'cotizacion': cotizacion})

        # 3. Usar WeasyPrint para convertir la cadena HTML a PDF
        html = HTML(string=html_string, base_url=request.build_absolute_uri())
        pdf_file = html.write_pdf()

        # 4. Crear una respuesta HTTP con el PDF
        response = HttpResponse(pdf_file, content_type='application/pdf')
        # Esta cabecera hace que el PDF se muestre en el navegador en lugar de descargarse
        response['Content-Disposition'] = f'inline; filename="cotizacion_{cotizacion.id}.pdf"'
        
        return response

    except Cotizacion.DoesNotExist:
        return HttpResponse("Cotización no encontrada.", status=404)
    
def caja_chica_detail(request, pk):
    caja = get_object_or_404(CajaChica, pk=pk)
    return render(request, 'finanzas/caja_detail.html', {'caja': caja})

def registrar_movimiento_caja(request, pk):
    # Aquí iría la lógica del formulario de ingreso/egreso
    return HttpResponse(f"Formulario para registrar movimiento en caja {pk}")

def prestamo_list(request):
    prestamos = Prestamo.objects.all()
    return render(request, 'finanzas/prestamo_list.html', {'prestamos': prestamos})

def prestamo_create(request):
    # Aquí iría el formulario de creación de préstamo
    return HttpResponse("Formulario nuevo préstamo")

def registrar_abono_prestamo(request, pk):
    # Aquí iría la lógica para subir el comprobante y registrar pago
    return HttpResponse(f"Formulario para abonar al préstamo {pk}")

def generar_tabla_view(request, pk):
    prestamo = get_object_or_404(Prestamo, pk=pk)
    # Ejecutamos la lógica matemática
    prestamo.generar_tabla_amortizacion()
    return redirect('core:prestamo_detail', pk=pk)

def prestamo_detail(request, pk):
    prestamo = get_object_or_404(Prestamo, pk=pk)
    cuotas = prestamo.cuotas.all().order_by('numero_cuota')
    return render(request, 'finanzas/prestamo_detail.html', {
        'prestamo': prestamo,
        'cuotas': cuotas
    })

def buscar_productos_venta_ajax(request):
    """
    Busca productos para Ventas/Cotizaciones.
    Devuelve 'precio' (PVP) en lugar de costo.
    """
    query = request.GET.get('q', '')
    data = []

    if query:
        # Busca por nombre o código
        productos = Producto.objects.filter(
            Q(nombre__icontains=query) | Q(codigo__icontains=query)
        ).values('id', 'codigo', 'nombre', 'precio', 'stock')[:20]

        for p in productos:
            data.append({
                'id': p['id'],
                'text': f"{p['codigo']} - {p['nombre']} (Stock: {p['stock']})",
                'precio': float(p['precio']), # Importante: Precio de Venta
                'stock': p['stock']
            })
    
    return JsonResponse({'results': data})

def gestion_cajas_view(request):
    # Obtener empresa del usuario actual (asumiendo lógica de Perfil)
    empresa_actual = request.user.perfil.empresa 
    
    if request.method == 'POST':
        nombre = request.POST.get('nombre')
        responsable_id = request.POST.get('responsable')
        
        if nombre and responsable_id:
            usuario_responsable = User.objects.get(id=responsable_id)
            CajaChica.objects.create(
                empresa=empresa_actual,
                nombre=nombre,
                responsable=usuario_responsable,
                saldo_actual=0 # Inicia en 0
            )
            return redirect('caja_list') # Recarga la página limpia

    # Contexto para el GET
    cajas = CajaChica.objects.filter(empresa=empresa_actual, activo=True)
    usuarios = User.objects.filter(perfil__empresa=empresa_actual) # Solo usuarios de la misma empresa
    
    return render(request, 'finanzas/caja_list.html', {
        'cajas': cajas,
        'usuarios': usuarios
    })

# 1. VISTA EDITAR
def editar_caja_view(request, pk):
    caja = get_object_or_404(CajaChica, pk=pk)
    
    if request.method == 'POST':
        nombre = request.POST.get('nombre')
        responsable_id = request.POST.get('responsable')
        
        if nombre and responsable_id:
            caja.nombre = nombre
            caja.responsable_id = responsable_id
            caja.save()
            messages.success(request, f'Caja "{caja.nombre}" actualizada correctamente.')
        else:
            messages.error(request, 'Todos los campos son obligatorios.')
            
    # Redirige a tu lista de cajas (ajusta el nombre si en tu url se llama diferente)
    return redirect('caja_list') 

# 2. VISTA CERRAR (Arqueo final)
def cerrar_caja_view(request, pk):
    caja = get_object_or_404(CajaChica, pk=pk)
    
    # Lógica: Solo cerramos si está activa
    if caja.activo:
        caja.activo = False
        caja.fecha_cierre = timezone.now() # Fecha de hoy
        caja.save()
        messages.warning(request, f'La caja "{caja.nombre}" ha sido CERRADA. No podrá registrar nuevos movimientos.')
    
    return redirect('caja_list')

# 3. VISTA ELIMINAR
def eliminar_caja_view(request, pk):
    caja = get_object_or_404(CajaChica, pk=pk)
    
    try:
        nombre_temp = caja.nombre
        caja.delete()
        messages.success(request, f'La caja "{nombre_temp}" fue eliminada permanentemente.')
    except Exception as e:
        # Esto pasa si la caja tiene movimientos vinculados (Protección de base de datos)
        messages.error(request, f'No se puede eliminar "{caja.nombre}" porque tiene movimientos registrados. Mejor opta por CERRARLA.')
    
    return redirect('caja_list')