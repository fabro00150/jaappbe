from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import api_views

router = DefaultRouter()
router.register(r'usuarios', api_views.SistemaUsuarioViewSet, basename='usuario')
router.register(r'eventos', api_views.SistemaEventoViewSet, basename='evento')
router.register(r'asistencias', api_views.SistemaAsistenciaViewSet, basename='asistencia')
router.register(r'tarifas', api_views.SistemaTarifaViewSet, basename='tarifa')
router.register(r'medidores', api_views.SistemaMedidorViewSet, basename='medidor')
router.register(r'lecturas', api_views.SistemaLecturaViewSet, basename='lectura')
router.register(r'pagos', api_views.SistemaPagoViewSet, basename='pago')
router.register(r'sectores', api_views.SistemaSectorViewSet, basename='sector')

urlpatterns = [
    path('', include(router.urls)),
    path('login/', api_views.login_view, name='login'),
]
