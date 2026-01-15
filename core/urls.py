from django.urls import path
from . import views

# IMPORTANTE: Definir el namespace para que funcione {% url 'core:...' %}
app_name = 'core'

urlpatterns = [
    # ==========================================
    # AUTENTICACIÓN Y DASHBOARD
    # ==========================================
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('', views.dashboard_view, name='dashboard'),
    
    # ==========================================
    # MÓDULO DE PROVEEDORES
    # ==========================================
    path('proveedores/', views.proveedores_view, name='proveedores'),
    path('proveedores/<int:pk>/editar/', views.editar_proveedor_view, name='editar_proveedor'),
    path('proveedores/<int:pk>/eliminar/', views.eliminar_proveedor_view, name='eliminar_proveedor'),

    # ==========================================
    # MÓDULO DE CLIENTES
    # ==========================================
    path('clientes/', views.clientes_view, name='clientes'),
    # path('clientes/agregar-ajax/', views.agregar_cliente_ajax, name='agregar_cliente_ajax'), # (Opcional si usas la de abajo)

    # ==========================================
    # MÓDULO DE INVENTARIO
    # ==========================================
    path('inventario/', views.inventario_view, name='inventario'),
    path('inventario/<int:pk>/editar/', views.editar_producto_view, name='editar_producto'),
    path('inventario/<int:pk>/eliminar/', views.eliminar_producto_view, name='eliminar_producto'),
    
    # AJAX Inventario
    path('inventario/ajax/agregar-categoria/', views.agregar_categoria_ajax, name='agregar_categoria_ajax'),
    path('inventario/ajax/agregar-marca/', views.agregar_marca_ajax, name='agregar_marca_ajax'),
    path('inventario/ajax/agregar-modelo/', views.agregar_modelo_ajax, name='agregar_modelo_ajax'),

    # ==========================================
    # MÓDULO DE COMPRAS
    # ==========================================
    path('compras/', views.compras_view, name='compras'),
    path('compras/<int:pk>/pdf/', views.compra_pdf_view, name='compra_pdf'),
    path('compras/<int:pk>/anular/', views.anular_compra_view, name='anular_compra'),
    path('compras/<int:pk>/restaurar/', views.restaurar_compra_view, name='restaurar_compra'),
    path('compras/<int:pk>/corregir/', views.corregir_compra_view, name='corregir_compra'),

    # ==========================================
    # MÓDULO DE VENTAS Y FACTURACIÓN
    # ==========================================
    path('ventas/', views.ventas_view, name='ventas'),
    path('ventas/<int:pk>/pdf/', views.venta_pdf_view, name='venta_pdf'),
    path('ventas/<int:pk>/anular/', views.anular_venta_view, name='anular_venta'),
    
    # Cotizaciones
    path('cotizaciones/', views.cotizaciones, name='cotizaciones'),
    path('cotizaciones/crear/', views.crear_cotizacion, name='cotizacion_crear'),
    path('cotizaciones/<int:cotizacion_id>/', views.detalle_cotizacion, name='cotizacion_detalle'),
    path('cotizaciones/<int:cotizacion_id>/pdf/', views.generar_cotizacion_pdf, name='cotizacion_pdf'),
    
    # Facturación Electrónica (SRI)
    path('facturacion-electronica/', views.facturacion_view, name='facturacion_electronica'),
    path('facturacion-electronica/procesar/', views.procesar_factura_ajax, name='procesar_factura_ajax'),
    path('facturacion-electronica/consultar-estado/', views.consultar_estado_sri_ajax, name='consultar_estado_sri_ajax'),
    path('facturacion-electronica/reenviar/', views.reenviar_factura_ajax, name='reenviar_factura_ajax'),
    
    # Descargas XML
    path('facturacion-electronica/xml-generado/<int:factura_id>/', views.descargar_xml_generado_view, name='descargar_xml_generado'),
    path('facturacion-electronica/xml-firmado/<int:factura_id>/', views.descargar_xml_firmado_view, name='descargar_xml_firmado'),
    path('facturacion-electronica/xml/<int:factura_id>/', views.descargar_xml_view, name='descargar_xml'),

    # ==========================================
    # RUTAS DE FINANZAS: TESORERÍA Y CAJAS
    # ==========================================
    # Actualizado para coincidir con el template y la vista nueva
    path('finanzas/cajas/', views.gestion_cajas_view, name='gestion_cajas'), 
    
    # Necesitas crear esta vista (caja_detail_view) para ver los movimientos
    path('finanzas/cajas/<int:id>/', views.caja_detail_view, name='caja_detail'), 
    
    path('finanzas/cajas/<int:pk>/movimiento/', views.registrar_movimiento_caja, name='caja_movimiento'),

    # ==========================================
    # RUTAS DE FINANZAS: PRÉSTAMOS
    # ==========================================
    path('finanzas/prestamos/', views.prestamo_list, name='prestamo_list'),
    path('finanzas/prestamos/nuevo/', views.prestamo_create, name='prestamo_create'),
    path('finanzas/prestamos/<int:pk>/', views.prestamo_detail, name='prestamo_detail'),
    path('finanzas/prestamos/<int:pk>/calcular/', views.generar_tabla_view, name='prestamo_generar_tabla'),
    path('finanzas/prestamos/<int:pk>/abonar/', views.registrar_abono_prestamo, name='prestamo_abono'),

    # ==========================================
    # HOME BANKING (CLIENTES)
    # ==========================================
    path('mi-banco/', views.home_banking_view, name='home_banking'),

    # ==========================================
    # CONFIGURACIÓN
    # ==========================================
    path('configuracion/', views.config_view, name='configuracion'), 
    path('configuracion-empresa/', views.config_empresa_view, name='config_empresa'),
    path('configuracion/empresa/', views.configuracion_empresa, name='config_empresa_alt'), # Renombrado para evitar colisión
    path('configuracion-empresa/punto-venta/<int:pk>/editar/', views.editar_puntoventa_view, name='editar_puntoventa'),

    # ==========================================
    # RUTAS AJAX GENERALES (BUSQUEDAS)
    # ==========================================
    path('ajax/buscar-productos/', views.buscar_productos_ajax, name='buscar_productos_ajax'),
    path('busqueda/productos-venta/', views.buscar_productos_venta_ajax, name='buscar_productos_venta_ajax'),
    
    path('ajax/buscar-clientes/', views.buscar_clientes_ajax, name='buscar_clientes_ajax'),
    path('busqueda/clientes/', views.buscar_clientes_ajax, name='buscar_clientes_ajax_alt'), # Alias si se usa en otro lado
    
    path('ajax/agregar-cliente/', views.agregar_cliente_ajax, name='agregar_cliente_ajax'),
    
    path('ajax/buscar-proveedores/', views.buscar_proveedores_ajax, name='buscar_proveedores_ajax'),
    path('ajax/agregar-proveedor/', views.agregar_proveedor_ajax, name='agregar_proveedor_ajax'),
    
    path('ajax/agregar-metodo-pago/', views.agregar_metodo_pago_ajax, name='agregar_metodo_pago_ajax'),
    
    path('ajax/convertir-cotizacion/', views.convertir_cotizacion_a_factura_ajax, name='ajax_convertir_cotizacion'),
    path('ajax/cambiar-estado-cotizacion/', views.cambiar_estado_cotizacion_ajax, name='ajax_cambiar_estado_cotizacion'),
]