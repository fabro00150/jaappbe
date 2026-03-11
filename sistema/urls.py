from django.contrib.auth import views as auth_views
from django.urls import path
from . import views
from rest_framework_simplejwt.views import TokenRefreshView

urlpatterns = [
    path('', views.index, name='index'),

    # Medidores
    path('medidores/', views.list_medidores, name='list_medidores'),
    path('medidores/nuevo/', views.new_medidor, name='new_medidor'),
    path('medidores/guardar/', views.save_new_medidor, name='save_new_medidor'),
    path('medidores/<int:id>/editar/', views.edit_medidor, name='edit_medidor'),
    path('medidores/<int:id>/guardar/', views.save_edit_medidor, name='save_edit_medidor'),
    path('medidores/<int:id>/eliminar/', views.delete_medidor, name='delete_medidor'),
    path("medidores/mapa/", views.mapa_general_medidores, name="mapa_general_medidores"),

    # Usuarios
    path('list_users', views.list_users, name='list_users'),    
    path('edit_user/<int:id>', views.edit_user, name='edit_user'),
    path('save_user/<int:id>', views.save_user, name='save_user'),
    path('new_user', views.new_user, name='new_user'),
    path('save_user_new', views.save_user_new, name='save_user_new'),
    path('delete_user/<int:id>', views.delete_user, name='delete_user'),

    # Sectores
    path('list_sectors', views.list_sectors, name='list_sectors'),
    path('edit_sector/<int:id>', views.edit_sector, name='edit_sector'),
    path('save_edit_sector/<int:id>', views.save_edit_sector, name='save_edit_sector'),
    path('new_sector', views.new_sector, name='new_sector'),
    path('save_sector_new', views.save_sector_new, name='save_sector_new'),
    path('delete_sector/<int:id>', views.delete_sector, name='delete_sector'),

    # Tipos de Eventos
    path('list_tipo_eventos', views.list_tipo_eventos, name='list_tipo_eventos'),
    path('edit_tipo_evento/<int:id>', views.edit_tipo_evento, name='edit_tipo_evento'),
    path('save_edit_tipo_evento/<int:id>', views.save_edit_tipo_evento, name='save_edit_tipo_evento'),
    path('new_tipo_evento', views.new_tipo_evento, name='new_tipo_evento'),
    path('save_tipo_evento_new', views.save_tipo_evento_new, name='save_tipo_evento_new'),
    path('delete_tipo_evento/<int:id>', views.delete_tipo_evento, name='delete_tipo_evento'),

    # Lecturas    
    path("lecturas/", views.lecturas_globales, name="lecturas_globales"),
    path("lecturas/guardar/", views.save_lecturas_globales, name="save_lecturas_globales"),
    path('lecturas/meses/', views.list_meses_lecturas, name='list_meses_lec'),
    
    # Tarifas
    path('list_tarifas', views.list_tarifas, name='list_tarifas'),
    path('new_tarifa', views.new_tarifa, name='new_tarifa'),
    path('save_new_tarifa', views.save_new_tarifa, name='save_new_tarifa'),
    path('edit_tarifa/<int:id>', views.edit_tarifa, name='edit_tarifa'),    
    path('delete_tarifa/<int:id>', views.delete_tarifa, name='delete_tarifa'),

    # Pagos
    path('list_pag_usuarios', views.list_pag_usuarios, name='list_pag_usuarios'),
    path('process_pag_usuario/<int:id>', views.process_pag_usuario, name='process_pag_usuario'),
    path("pagos/registrar/<int:usuario_id>/<int:anio>/<int:mes>/<int:medidor_id>/",views.registrar_pago,name="registrar_pago",),
    path('anular/<int:pago_id>/', views.anular_pago, name='anular_pago'),
    
    # Asistencias
    path('evento/<int:evento_id>/asistencias/', views.asistencia_evento, name='asistencia_evento'),
    path('evento/<int:evento_id>/asistencias/save/', views.save_asistencias, name='save_asistencias'),
    
    # Reportes
    path("reportes/pagos/", views.reporte_pagos, name="reporte_pagos"),
    path("reportes/lecturas/", views.reporte_lecturas, name="reporte_lecturas"),
            
    # Login usando vistas integradas de Django
    path('login/', auth_views.LoginView.as_view(
        template_name='registration/login.html',
        redirect_authenticated_user=True  # ← Redirige si ya está logueado
    ), name='login'),
    
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    
    
    # descargar apk
    path('descargar-apk/', views.descargar_apk, name='descargar_apk'),
    
    
     # Admin personalizado - Grupos
    path('admin-sistema/grupos/', views.admin_grupos, name='admin_grupos'),
    path('admin-sistema/grupos/crear/', views.admin_grupo_crear, name='admin_grupo_crear'),
    path('admin-sistema/grupos/<int:grupo_id>/editar/', views.admin_grupo_editar, name='admin_grupo_editar'),
    path('admin-sistema/grupos/<int:grupo_id>/eliminar/', views.admin_grupo_eliminar, name='admin_grupo_eliminar'),
    
    # Admin personalizado - Usuarios
    path('admin-sistema/usuarios/', views.admin_usuarios_sistema, name='admin_usuarios_sistema'),
    path('admin-sistema/usuarios/crear/', views.admin_usuario_crear, name='admin_usuario_crear'),
    path('admin-sistema/usuarios/<int:usuario_id>/editar/', views.admin_usuario_editar, name='admin_usuario_editar'),
    path('admin-sistema/usuarios/<int:usuario_id>/eliminar/', views.admin_usuario_eliminar, name='admin_usuario_eliminar'),
    
    
    # ============= API APP MÓVIL =============
    path('api/token/', views.AppMovilTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
]
