from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import api_views
from rest_framework.authtoken.views import obtain_auth_token
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)


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
    path('api-token-auth/', obtain_auth_token, name='api_token_auth'),
    path('token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('me/', api_views.me_view, name='me'),

]
