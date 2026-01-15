# Ubicación: core/urls.py

from django.urls import path
from . import views

urlpatterns = [
    # ==========================================
    # 1. AUTENTICACIÓN Y DASHBOARD
    # ==========================================
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('', views.dashboard_view, name='dashboard'),

    # ==========================================
    # 2. MÓDULO DE CLIENTES Y HOME BANKING
    # ==========================================
    path('clientes/', views.clientes_view, name='clientes'),
    path('mi-banco/', views.home_banking_view, name='home_banking'),
    
    # Ajax Clientes
    path('ajax/buscar-clientes/', views.buscar_clientes_ajax, name='buscar_clientes_ajax'),
    path('ajax/agregar-cliente/', views.agregar_cliente_ajax, name='agregar_cliente_ajax'),

    # ==========================================
    # 3. MÓDULO DE PROVEEDORES
    # ==========================================
    path('proveedores/', views.proveedores_view, name='proveedores'),
    path('proveedores/<int:pk>/editar/', views.editar_proveedor_view, name='editar_proveedor'),
    path('proveedores/<int:pk>/eliminar/', views.eliminar_proveedor_view, name='eliminar_proveedor'),
    
    # Ajax Proveedores
    path('ajax/buscar-proveedores/', views.buscar_proveedores_ajax, name='buscar_proveedores_ajax'),
    path('ajax/agregar-proveedor/', views.agregar_proveedor_ajax, name='agregar_proveedor_ajax'),

    # ==========================================
    # 4. MÓDULO DE INVENTARIO
    # ==========================================
    path('inventario/', views.inventario_view, name='inventario'),
    path('inventario/<int:pk>/editar/', views.editar_producto_view, name='editar_producto'),
    path('inventario/<int:pk>/eliminar/', views.eliminar_producto_view, name='eliminar_producto'),
    
    # Ajax Inventario (Modales)
    path('inventario/ajax/agregar-categoria/', views.agregar_categoria_ajax, name='agregar_categoria_ajax'),
    path('inventario/ajax/agregar-marca/', views.agregar_marca_ajax, name='agregar_marca_ajax'),
    path('inventario/ajax/agregar-modelo/', views.agregar_modelo_ajax, name='agregar_modelo_ajax'),

    # ==========================================
    # 5. MÓDULO DE COMPRAS
    # ==========================================
    path('compras/', views.compras_view, name='compras'),
    path('compras/<int:pk>/pdf/', views.compra_pdf_view, name='compra_pdf'),
    path('compras/<int:pk>/anular/', views.anular_compra_view, name='anular_compra'),
    path('compras/<int:pk>/restaurar/', views.restaurar_compra_view, name='restaurar_compra'),
    path('compras/<int:pk>/corregir/', views.corregir_compra_view, name='corregir_compra'),

    # ==========================================
    # 6. MÓDULO DE VENTAS
    # ==========================================
    path('ventas/', views.ventas_view, name='ventas'),
    path('ventas/<int:pk>/pdf/', views.venta_pdf_view, name='venta_pdf'),
    path('ventas/<int:pk>/anular/', views.anular_venta_view, name='anular_venta'),
    
    # Ajax Ventas
    path('ajax/buscar-productos/', views.buscar_productos_ajax, name='buscar_productos_ajax'),
    path('busqueda/productos-venta/', views.buscar_productos_venta_ajax, name='buscar_productos_venta_ajax'),
    path('ajax/agregar-metodo-pago/', views.agregar_metodo_pago_ajax, name='agregar_metodo_pago_ajax'),

    # ==========================================
    # 7. MÓDULO DE COTIZACIONES
    # ==========================================
    path('cotizaciones/', views.cotizaciones, name='cotizaciones'),
    path('cotizaciones/crear/', views.crear_cotizacion, name='cotizacion_crear'),
    path('cotizaciones/<int:cotizacion_id>/', views.detalle_cotizacion, name='cotizacion_detalle'),
    path('cotizaciones/<int:cotizacion_id>/pdf/', views.generar_cotizacion_pdf, name='cotizacion_pdf'),
    
    # Acciones Cotizaciones
    path('ajax/convertir-cotizacion/', views.convertir_cotizacion_a_factura_ajax, name='ajax_convertir_cotizacion'),
    path('ajax/cambiar-estado-cotizacion/', views.cambiar_estado_cotizacion_ajax, name='ajax_cambiar_estado_cotizacion'),

    # ==========================================
    # 8. FACTURACIÓN ELECTRÓNICA (SRI)
    # ==========================================
    path('facturacion-electronica/', views.facturacion_view, name='facturacion_electronica'),
    path('facturacion-electronica/procesar/', views.procesar_factura_ajax, name='procesar_factura_ajax'),
    path('facturacion-electronica/consultar-estado/', views.consultar_estado_sri_ajax, name='consultar_estado_sri_ajax'),
    path('facturacion-electronica/reenviar/', views.reenviar_factura_ajax, name='reenviar_factura_ajax'),
    
    # Descargas XML
    path('facturacion-electronica/xml-generado/<int:factura_id>/', views.descargar_xml_generado_view, name='descargar_xml_generado'),
    path('facturacion-electronica/xml-firmado/<int:factura_id>/', views.descargar_xml_firmado_view, name='descargar_xml_firmado'),
    path('facturacion-electronica/xml/<int:factura_id>/', views.descargar_xml_view, name='descargar_xml'),

    # ==========================================
    # 9. FINANZAS: CUENTAS BANCARIAS
    # ==========================================
    path('finanzas/cuentas/', views.gestion_cuentas_view, name='gestion_cuentas'),
    path('finanzas/cuentas/<int:pk>/editar/', views.editar_cuenta_view, name='editar_cuenta'),
    path('finanzas/cuentas/<int:pk>/eliminar/', views.eliminar_cuenta_view, name='eliminar_cuenta'),
    path('finanzas/cuentas/<int:pk>/movimientos/', views.cuenta_movimientos_view, name='cuenta_movimientos'),

    # ==========================================
    # 10. FINANZAS: PRÉSTAMOS
    # ==========================================
    path('finanzas/prestamos/', views.prestamo_list, name='prestamo_list'),
    path('finanzas/prestamos/nuevo/', views.prestamo_create, name='prestamo_create'),
    path('finanzas/prestamos/<int:pk>/', views.prestamo_detail, name='prestamo_detail'),
    path('finanzas/prestamos/<int:pk>/calcular/', views.generar_tabla_view, name='prestamo_generar_tabla'),
    path('finanzas/prestamos/<int:pk>/abonar/', views.registrar_abono_prestamo, name='prestamo_abono'),

    # ==========================================
    # 11. CONFIGURACIÓN
    # ==========================================
    path('configuracion/', views.config_view, name='configuracion'), 
    path('configuracion-empresa/', views.config_empresa_view, name='config_empresa'),
    
    # Nota: Tenías dos rutas con name='config_empresa', he mantenido ambas pero ten cuidado con el reverse
    path('configuracion/empresa/', views.configuracion_empresa, name='config_empresa_alt'), 
    path('configuracion-empresa/punto-venta/<int:pk>/editar/', views.editar_puntoventa_view, name='editar_puntoventa'),
]