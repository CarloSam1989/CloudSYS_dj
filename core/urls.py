# Ubicación: core/urls.py

from django.urls import path
from . import views

urlpatterns = [
    # Rutas de autenticación
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    
    # Ruta principal
    path('', views.dashboard_view, name='dashboard'),
    
    # --- Rutas del Módulo de Proveedores ---
    path('proveedores/', views.proveedores_view, name='proveedores'),
    path('proveedores/<int:pk>/editar/', views.editar_proveedor_view, name='editar_proveedor'),
    path('proveedores/<int:pk>/eliminar/', views.eliminar_proveedor_view, name='eliminar_proveedor'),

    # --- Rutas del Módulo de Inventario ---
    path('inventario/', views.inventario_view, name='inventario'),
    path('inventario/<int:pk>/editar/', views.editar_producto_view, name='editar_producto'),
    path('inventario/<int:pk>/eliminar/', views.eliminar_producto_view, name='eliminar_producto'),
    
    # --- NUEVAS RUTAS AJAX PARA LOS MODALES DE INVENTARIO ---
    path('inventario/ajax/agregar-categoria/', views.agregar_categoria_ajax, name='agregar_categoria_ajax'),
    path('inventario/ajax/agregar-marca/', views.agregar_marca_ajax, name='agregar_marca_ajax'),
    path('inventario/ajax/agregar-modelo/', views.agregar_modelo_ajax, name='agregar_modelo_ajax'),

    # --- Rutas para los otros módulos (placeholders) ---
    path('ventas/', views.ventas_view, name='ventas'),
    path('facturacion-electronica/', views.facturacion_view, name='facturacion_electronica'),
    path('configuracion-empresa/', views.config_empresa_view, name='config_empresa'),
    path('configuracion/', views.config_view, name='configuracion'), 
    path('compras/', views.compras_view, name='compras'),
    path('ajax/buscar-productos/', views.buscar_productos_ajax, name='buscar_productos_ajax'),
    path('compras/<int:pk>/anular/', views.anular_compra_view, name='anular_compra'),
    path('compras/<int:pk>/pdf/', views.compra_pdf_view, name='compra_pdf'),
    path('compras/<int:pk>/anular/', views.anular_compra_view, name='anular_compra'),
    path('compras/<int:pk>/restaurar/', views.restaurar_compra_view, name='restaurar_compra'),
    path('compras/<int:pk>/corregir/', views.corregir_compra_view, name='corregir_compra'),
    path('ventas/', views.ventas_view, name='ventas'),
    path('ventas/<int:pk>/pdf/', views.venta_pdf_view, name='venta_pdf'),
    path('ventas/<int:pk>/anular/', views.anular_venta_view, name='anular_venta'),
    path('ajax/buscar-clientes/', views.buscar_clientes_ajax, name='buscar_clientes_ajax'),
    path('ajax/agregar-cliente/', views.agregar_cliente_ajax, name='agregar_cliente_ajax'),
    path('ajax/agregar-metodo-pago/', views.agregar_metodo_pago_ajax, name='agregar_metodo_pago_ajax'),
    path('configuracion-empresa/', views.config_empresa_view, name='config_empresa'),
    path('configuracion-empresa/punto-venta/<int:pk>/editar/', views.editar_puntoventa_view, name='editar_puntoventa'),
    path('facturacion-electronica/', views.facturacion_view, name='facturacion_electronica'),
    path('facturacion-electronica/procesar/', views.procesar_factura_ajax, name='procesar_factura_ajax'),
    path('facturacion-electronica/consultar-estado/', views.consultar_estado_sri_ajax, name='consultar_estado_sri_ajax'),
    path('facturacion-electronica/reenviar/', views.reenviar_factura_ajax, name='reenviar_factura_ajax'),
    path('clientes/', views.clientes_view, name='clientes'),
    path('facturacion-electronica/xml-generado/<int:factura_id>/', views.descargar_xml_generado_view, name='descargar_xml_generado'),
    path('facturacion-electronica/xml-firmado/<int:factura_id>/', views.descargar_xml_firmado_view, name='descargar_xml_firmado'),
    path('facturacion-electronica/xml/<int:factura_id>/', views.descargar_xml_view, name='descargar_xml'),
    path('ajax/buscar-proveedores/', views.buscar_proveedores_ajax, name='buscar_proveedores_ajax'),
    path('ajax/agregar-proveedor/', views.agregar_proveedor_ajax, name='agregar_proveedor_ajax'),


   
   

    
]