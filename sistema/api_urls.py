from django.urls import path, include
from . import api_views
from rest_framework.authtoken.views import obtain_auth_token
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)

# 1. Importamos SOLO SimpleRouter
from rest_framework.routers import SimpleRouter 

# 2. Instanciamos SimpleRouter
router = SimpleRouter()

# 3. Registramos tus vistas (esto se queda igual)
router.register(r'usuarios', api_views.SistemaUsuarioViewSet, basename='usuario')
router.register(r'eventos', api_views.SistemaEventoViewSet, basename='evento')
router.register(r'asistencias', api_views.SistemaAsistenciaViewSet, basename='asistencia')
router.register(r'tarifas', api_views.SistemaTarifaViewSet, basename='tarifa')
router.register(r'medidores', api_views.SistemaMedidorViewSet, basename='medidor')
router.register(r'lecturas', api_views.SistemaLecturaViewSet, basename='lectura')
router.register(r'pagos', api_views.SistemaPagoViewSet, basename='pago')
router.register(r'sectores', api_views.SistemaSectorViewSet, basename='sector')

urlpatterns = [
    # Al usar SimpleRouter, la ruta raíz '' ya NO mostrará la lista de endpoints
    path('', include(router.urls)),
    
    path('login/', api_views.login_view, name='login'),
    path('api-token-auth/', obtain_auth_token, name='api_token_auth'),
    path('token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('me/', api_views.me_view, name='me'),
]