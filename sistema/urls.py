from django.urls import path
from . import views
urlpatterns = [
    path('index', views.index, name='index'),

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
    path('list_sec_lec', views.list_sec_lec, name='list_sec_lec'),
    path('lectura_sector/<int:id>', views.lectura_sector, name='lectura_sector'),
    path('save_lectura/<int:id>', views.save_lectura, name='save_lectura'),
    
    # Tarifas
    path('list_tarifas', views.list_tarifas, name='list_tarifas'),
    path('new_tarifa', views.new_tarifa, name='new_tarifa'),
    path('save_new_tarifa', views.save_new_tarifa, name='save_new_tarifa'),
    path('edit_tarifa/<int:id>', views.edit_tarifa, name='edit_tarifa'),
    path('save_edit_tarifa/<int:id>', views.save_edit_tarifa, name='save_edit_tarifa'),
    path('delete_tarifa/<int:id>', views.delete_tarifa, name='delete_tarifa'),

    # Pagos
    path('list_pag_usuarios', views.list_pag_usuarios, name='list_pag_usuarios'),
    path('process_pag_usuario/<int:id>', views.process_pag_usuario, name='process_pag_usuario'),
    path('registrar_pago/<int:usuario_id>/<int:anio>/<int:mes>', views.registrar_pago, name='registrar_pago'),
    
    # Asistencias
    path('evento/<int:evento_id>/asistencias/', views.asistencia_evento, name='asistencia_evento'),
    path('evento/<int:evento_id>/asistencias/save/', views.save_asistencias, name='save_asistencias'),
    
    
    

    # Login
    path('', views.login, name='login'),
    path('logout', views.exit, name='exit'),
    
    # Dashboard        
    
    
    
]
