from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal
from django.contrib import messages
from django.shortcuts import get_object_or_404, render, redirect
from .forms import *
from .models import *
import json
from django.http import JsonResponse
from django.views.decorators.http import require_POST

@login_required
def dashboard_cobros(request):
    empresa = request.user.perfil.empresa

    prestamos = PrestamoCobro.objects.filter(
        empresa=empresa
    ).order_by('-id')[:10]

    total_prestado = PrestamoCobro.objects.filter(
        empresa=empresa
    ).aggregate(total=models.Sum('monto'))['total'] or 0

    total_saldo = PrestamoCobro.objects.filter(
        empresa=empresa
    ).aggregate(total=models.Sum('saldo'))['total'] or 0

    hoy = timezone.now().date()

    cobrado_hoy = MovimientoPrestamoCobro.objects.filter(
        empresa=empresa,
        fecha__date=hoy,
        tipo='CUOTA'
    ).aggregate(total=models.Sum('monto'))['total'] or 0

    prestamos_vencidos = PrestamoCobro.objects.filter(
        empresa=empresa,
        estado='VENCIDO'
    ).count()

    cuentas = CuentaFinancieraCobro.objects.filter(
        empresa=empresa
    )

    return render(request, 'cobros/dashboard.html', {
        'prestamos': prestamos,
        'total_prestado': total_prestado,
        'total_saldo': total_saldo,
        'cobrado_hoy': cobrado_hoy,
        'prestamos_vencidos': prestamos_vencidos,
        'cuentas': cuentas,
    })

@login_required
def cuentas_por_cobrar(request):
    return render(request, 'cobros/cuentas_por_cobrar.html')

@login_required
def prestamos_cobros(request):
    empresa_actual = request.user.perfil.empresa

    prestamos = PrestamoCobro.objects.filter(
        empresa=empresa_actual
    ).select_related('cliente', 'usuario', 'cuenta_desembolso').order_by('-id')

    if request.method == 'POST':
        form = PrestamoCobroForm(request.POST)
        if form.is_valid():
            try:
                with transaction.atomic():
                    prestamo = form.save(commit=False)
                    prestamo.empresa = empresa_actual
                    prestamo.usuario = request.user
                    prestamo.numero = f"PRE-{PrestamoCobro.objects.filter(empresa=empresa_actual).count() + 1:06d}"

                    prestamo.total = prestamo.calcular_total()
                    prestamo.cuota_estimada = prestamo.calcular_cuota_estimada()
                    prestamo.saldo = prestamo.total

                    if not prestamo.fecha_vencimiento:
                        prestamo.fecha_vencimiento = prestamo.fecha + timedelta(
                            days=(prestamo.cuotas * prestamo.frecuencia_dias)
                        )

                    cuenta = prestamo.cuenta_desembolso
                    monto_desembolso = prestamo.monto or Decimal('0.00')

                    if cuenta and cuenta.saldo_actual < monto_desembolso:
                        messages.error(
                            request,
                            f"No hay saldo suficiente en la cuenta {cuenta.nombre}."
                        )
                        return redirect('cobros:prestamos')

                    prestamo.save()

                    MovimientoPrestamoCobro.objects.create(
                        empresa=empresa_actual,
                        prestamo=prestamo,
                        cliente=prestamo.cliente,
                        cuenta=cuenta,
                        tipo='DESEMBOLSO',
                        monto=prestamo.total,
                        saldo_anterior=Decimal('0.00'),
                        saldo_nuevo=prestamo.total,
                        usuario=request.user,
                        observacion='Registro inicial del préstamo'
                    )

                    if cuenta:
                        MovimientoCuentaCobro.objects.create(
                            empresa=empresa_actual,
                            cuenta=cuenta,
                            tipo='EGRESO',
                            origen='PRESTAMO',
                            monto=monto_desembolso,
                            referencia=prestamo.numero,
                            observacion=f'Desembolso del préstamo {prestamo.numero}',
                            usuario=request.user,
                        )

                    messages.success(request, 'Préstamo registrado correctamente.')
                    return redirect('cobros:prestamos')

            except Exception as e:
                messages.error(request, f'No se pudo registrar el préstamo: {e}')
    else:
        form = PrestamoCobroForm()

    return render(request, 'cobros/prestamos.html', {
        'form': form,
        'prestamos': prestamos,
    })

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

        empresa = request.user.perfil.empresa

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

        empresa = request.user.perfil.empresa

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

        empresa = request.user.perfil.empresa

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
    empresa_actual = request.user.perfil.empresa

    prestamos = PrestamoCobro.objects.filter(
        empresa=empresa_actual
    ).select_related('cliente', 'usuario', 'cuenta_desembolso').order_by('-id')

    if request.method == 'POST':
        form = PrestamoCobroForm(request.POST)
        if form.is_valid():
            try:
                with transaction.atomic():
                    prestamo = form.save(commit=False)
                    prestamo.empresa = empresa_actual
                    prestamo.usuario = request.user
                    prestamo.numero = f"PRE-{PrestamoCobro.objects.filter(empresa=empresa_actual).count() + 1:06d}"

                    prestamo.total = prestamo.calcular_total()
                    prestamo.cuota_estimada = prestamo.calcular_cuota_estimada()
                    prestamo.saldo = prestamo.total

                    if not prestamo.fecha_vencimiento:
                        prestamo.fecha_vencimiento = prestamo.fecha + timedelta(
                            days=(prestamo.cuotas * prestamo.frecuencia_dias)
                        )

                    cuenta = prestamo.cuenta_desembolso
                    monto_desembolso = prestamo.monto or Decimal('0.00')

                    if cuenta and cuenta.saldo_actual < monto_desembolso:
                        messages.error(
                            request,
                            f"No hay saldo suficiente en la cuenta {cuenta.nombre}."
                        )
                        return redirect('cobros:prestamos')

                    prestamo.save()

                    MovimientoPrestamoCobro.objects.create(
                        empresa=empresa_actual,
                        prestamo=prestamo,
                        cliente=prestamo.cliente,
                        cuenta=cuenta,
                        tipo='DESEMBOLSO',
                        monto=prestamo.total,
                        saldo_anterior=Decimal('0.00'),
                        saldo_nuevo=prestamo.total,
                        usuario=request.user,
                        observacion='Registro inicial del préstamo'
                    )

                    if cuenta:
                        MovimientoCuentaCobro.objects.create(
                            empresa=empresa_actual,
                            cuenta=cuenta,
                            tipo='EGRESO',
                            origen='PRESTAMO',
                            monto=monto_desembolso,
                            referencia=prestamo.numero,
                            observacion=f'Desembolso del préstamo {prestamo.numero}',
                            usuario=request.user,
                        )

                    messages.success(request, 'Préstamo registrado correctamente.')
                    return redirect('cobros:prestamos')

            except Exception as e:
                messages.error(request, f'No se pudo registrar el préstamo: {e}')
    else:
        form = PrestamoCobroForm()

    return render(request, 'cobros/prestamos.html', {
        'form': form,
        'prestamos': prestamos,
    })

@login_required
def cuentas_financieras_cobro(request):
    empresa_actual = request.user.perfil.empresa

    cuentas = CuentaFinancieraCobro.objects.filter(
        empresa=empresa_actual
    ).order_by('nombre')

    if request.method == 'POST':
        form = CuentaFinancieraCobroForm(request.POST)
        if form.is_valid():
            cuenta = form.save(commit=False)
            cuenta.empresa = empresa_actual
            cuenta.save()
            messages.success(request, 'Cuenta registrada correctamente.')
            return redirect('cobros:cuentas_financieras')
    else:
        form = CuentaFinancieraCobroForm()

    return render(request, 'cobros/cuentas.html', {
        'form': form,
        'cuentas': cuentas,
    })

@login_required
def registrar_pago_prestamo(request, pk):
    empresa_actual = request.user.perfil.empresa

    prestamo = get_object_or_404(
        PrestamoCobro,
        pk=pk,
        empresa=empresa_actual
    )

    if request.method == 'POST':
        form = MovimientoPrestamoCobroForm(request.POST)
        if form.is_valid():
            try:
                with transaction.atomic():
                    movimiento = form.save(commit=False)
                    movimiento.empresa = empresa_actual
                    movimiento.prestamo = prestamo
                    movimiento.cliente = prestamo.cliente
                    movimiento.usuario = request.user
                    movimiento.tipo = 'CUOTA'
                    movimiento.save()

                    # INGRESO A CUENTA
                    if movimiento.cuenta:
                        MovimientoCuentaCobro.objects.create(
                            empresa=empresa_actual,
                            cuenta=movimiento.cuenta,
                            tipo='INGRESO',
                            origen='COBRO',
                            monto=movimiento.monto,
                            referencia=prestamo.numero,
                            observacion=f'Pago préstamo {prestamo.numero}',
                            usuario=request.user,
                        )

                    messages.success(request, 'Pago registrado correctamente.')
                    return redirect('cobros:prestamos')

            except Exception as e:
                messages.error(request, f'Error: {e}')
    else:
        form = MovimientoPrestamoCobroForm()

    return render(request, 'cobros/movimiento_prestamo.html', {
        'form': form,
        'prestamo': prestamo
    })

@login_required
@require_POST
def ajax_cuenta_crear(request):
    try:
        data = json.loads(request.body)

        nombre = (data.get("nombre") or "").strip()
        tipo = (data.get("tipo") or "BANCO").strip()
        banco = (data.get("banco") or "").strip()
        numero_cuenta = (data.get("numero_cuenta") or "").strip()
        titular = (data.get("titular") or "").strip()
        saldo_actual = data.get("saldo_actual") or 0

        if not nombre:
            return JsonResponse(
                {"errors": {"nombre": ["El nombre de la cuenta es obligatorio."]}},
                status=400
            )

        empresa = request.user.perfil.empresa

        cuenta = CuentaFinancieraCobro.objects.create(
            empresa=empresa,
            nombre=nombre,
            tipo=tipo,
            banco=banco if banco else None,
            numero_cuenta=numero_cuenta if numero_cuenta else None,
            titular=titular if titular else None,
            saldo_actual=saldo_actual or 0,
            activo=True,
        )

        return JsonResponse({
            "id": cuenta.id,
            "text": str(cuenta.nombre),
        })

    except Exception as e:
        return JsonResponse({"detail": str(e)}, status=400)
