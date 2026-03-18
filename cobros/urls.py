from django.urls import path
from . import views

app_name = 'cobros'

urlpatterns = [
    path('', views.dashboard_cobros, name='lista_cobros'),
    path('prestamos/', views.prestamos_cobros, name='prestamos'),
    path('prestamos/pago/<int:pk>/', views.registrar_pago_prestamo, name='pago_prestamo'),
    path('compras-financiadas/', views.compras_financiadas, name='compras_financiadas'),
    path('cobros-del-dia/', views.cobros_del_dia, name='cobros_del_dia'),
    path('cuentas-por-cobrar/', views.cuentas_por_cobrar, name='cuentas_por_cobrar'),
    path('reportes/', views.reportes_cobros, name='reportes_cobros'),

    path('cuentas/', views.cuentas_financieras_cobro, name='cuentas_financieras'),

    path('ajax/clientes/crear/', views.ajax_cliente_crear, name='ajax_cliente_crear'),
    path('ajax/cuentas/crear/', views.ajax_cuenta_crear, name='ajax_cuenta_crear'),
    path('ajax/categorias/crear/', views.ajax_categoria_crear, name='ajax_categoria_crear'),
    path('ajax/metodos-pago/crear/', views.ajax_metodo_pago_crear, name='ajax_metodo_pago_crear'),
]