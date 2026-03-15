from django.contrib.auth.decorators import login_required
from decimal import Decimal
from django.contrib import messages
from django.shortcuts import render, redirect
from .forms import *
from .models import *
import json
from django.http import JsonResponse
from django.views.decorators.http import require_POST

@login_required
def dashboard_cobros(request):
    cobros = PrestamoCobro.objects.all().order_by('-id')

    if request.method == 'POST':
        form = PrestamoCobroForm(request.POST)
        if form.is_valid():
            cobro = form.save(commit=False)
            cobro.usuario = request.user
            cobro.numero = f"COB-{PrestamoCobro.objects.count() + 1:06d}"

            monto = cobro.monto or Decimal('0.00')
            interes = cobro.interes or Decimal('0.00')

            cobro.total = monto + (monto * interes / Decimal('100'))
            cobro.saldo = cobro.total

            # Si tu modelo requiere empresa:
            # cobro.empresa = request.user.empresa

            cobro.save()
            messages.success(request, 'Operación registrada correctamente.')
            return redirect('cobros:lista_cobros')
    else:
        form = PrestamoCobroForm()

    return render(request, 'cobros/cobros.html', {
        'form': form,
        'cobros': cobros,
    })

@login_required
def cuentas_por_cobrar(request):
    return render(request, 'cobros/cuentas_por_cobrar.html')

@login_required
def prestamos_cobros(request):
    return render(request, 'cobros/prestamos.html')


@login_required
@require_POST
def ajax_cliente_crear(request):
    try:
        data = json.loads(request.body)

        nombre = (data.get("nombre") or "").strip()
        identificacion = (data.get("identificacion") or "").strip()
        telefono = (data.get("telefono") or "").strip()
        direccion = (data.get("direccion") or "").strip()
        email = (data.get("email") or "").strip()

        if not nombre:
            return JsonResponse(
                {"errors": {"nombre": ["El nombre es obligatorio."]}},
                status=400
            )

        empresa = request.user.empresa

        cliente = Cliente.objects.create(
            empresa=empresa,
            nombre=nombre,
            identificacion=identificacion if identificacion else None,
            telefono=telefono if telefono else None,
            direccion=direccion if direccion else None,
            email=email if email else None,
        )

        return JsonResponse({
            "id": cliente.id,
            "text": str(cliente.nombre),
        })

    except Exception as e:
        return JsonResponse({"detail": str(e)}, status=400)


@login_required
@require_POST
def ajax_categoria_crear(request):
    try:
        data = json.loads(request.body)
        nombre = (data.get("nombre") or "").strip()

        if not nombre:
            return JsonResponse(
                {"errors": {"nombre": ["El nombre es obligatorio."]}},
                status=400
            )

        empresa = request.user.empresa

        categoria, creada = CategoriaCobro.objects.get_or_create(
            empresa=empresa,
            nombre=nombre,
            defaults={"activo": True}
        )

        if not creada and not categoria.activo:
            categoria.activo = True
            categoria.save(update_fields=["activo"])

        return JsonResponse({
            "id": categoria.id,
            "text": categoria.nombre,
        })

    except Exception as e:
        return JsonResponse({"detail": str(e)}, status=400)


@login_required
@require_POST
def ajax_metodo_pago_crear(request):
    try:
        data = json.loads(request.body)
        nombre = (data.get("nombre") or "").strip()

        if not nombre:
            return JsonResponse(
                {"errors": {"nombre": ["El nombre es obligatorio."]}},
                status=400
            )

        empresa = request.user.empresa

        metodo = MetodoPago.objects.create(
            empresa=empresa,
            nombre=nombre
        )

        return JsonResponse({
            "id": metodo.id,
            "text": metodo.nombre,
        })

    except Exception as e: 
        return JsonResponse({"detail": str(e)}, status=400)
    
@login_required
def compras_financiadas(request):
    compras = CompraFinanciada.objects.filter(
        empresa=request.user.empresa
    ).order_by('-id')

    if request.method == 'POST':
        form = CompraFinanciadaForm(request.POST)
        if form.is_valid():
            compra = form.save(commit=False)
            compra.empresa = request.user.empresa
            compra.usuario = request.user
            compra.numero = f"CF-{CompraFinanciada.objects.filter(empresa=request.user.empresa).count() + 1:06d}"

            monto = compra.monto_producto or Decimal('0.00')
            cuota_inicial = compra.cuota_inicial or Decimal('0.00')
            interes = compra.interes or Decimal('0.00')

            base_financiada = monto - cuota_inicial
            if base_financiada < 0:
                base_financiada = Decimal('0.00')

            compra.total = base_financiada + (base_financiada * interes / Decimal('100'))
            compra.total_abonado = cuota_inicial
            compra.saldo = compra.total

            compra.save()

            # Registrar cargo inicial
            MovimientoCompraFinanciada.objects.create(
                empresa=request.user.empresa,
                compra=compra,
                cliente=compra.cliente,
                tipo='CARGO_INICIAL',
                monto=compra.total,
                metodo_pago=None,
                referencia='',
                observacion='Registro inicial de compra financiada',
                usuario=request.user,
            )

            # Registrar cuota inicial si aplica
            if cuota_inicial > 0:
                MovimientoCompraFinanciada.objects.create(
                    empresa=request.user.empresa,
                    compra=compra,
                    cliente=compra.cliente,
                    tipo='ABONO_EXTRA',
                    monto=cuota_inicial,
                    metodo_pago=None,
                    referencia='',
                    observacion='Cuota inicial',
                    usuario=request.user,
                )

            messages.success(request, 'Compra financiada registrada correctamente.')
            return redirect('cobros:compras_financiadas')
    else:
        form = CompraFinanciadaForm()

    return render(request, 'cobros/compras_financiadas.html', {
        'form': form,
        'compras': compras,
    })

@login_required
def cobros_del_dia(request):
    return render(request, 'cobros/cobros_del_dia.html')

@login_required
def reportes_cobros(request):
    return render(request, 'cobros/reportes.html')

@login_required
def prestamos_cobros(request):
    prestamos = PrestamoCobro.objects.filter(
        empresa=request.user.empresa
    ).select_related('cliente', 'usuario').order_by('-id')

    if request.method == 'POST':
        form = PrestamoCobroForm(request.POST)
        if form.is_valid():
            prestamo = form.save(commit=False)
            prestamo.empresa = request.user.empresa
            prestamo.usuario = request.user
            prestamo.numero = f"PRE-{PrestamoCobro.objects.filter(empresa=request.user.empresa).count() + 1:06d}"

            monto = prestamo.monto or Decimal('0.00')
            interes = prestamo.interes or Decimal('0.00')

            prestamo.total = monto + (monto * interes / Decimal('100'))
            prestamo.saldo = prestamo.total

            prestamo.save()

            MovimientoPrestamoCobro.objects.create(
                empresa=request.user.empresa,
                prestamo=prestamo,
                cliente=prestamo.cliente,
                tipo='DESEMBOLSO',
                monto=prestamo.total,
                saldo_anterior=Decimal('0.00'),
                saldo_nuevo=prestamo.total,
                usuario=request.user,
                observacion='Desembolso inicial del préstamo'
            )

            messages.success(request, 'Préstamo registrado correctamente.')
            return redirect('cobros:prestamos')
    else:
        form = PrestamoCobroForm()

    return render(request, 'cobros/prestamos.html', {
        'form': form,
        'prestamos': prestamos,
    })