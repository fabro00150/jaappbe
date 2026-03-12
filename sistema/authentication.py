# sistema/authentication.py

from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.exceptions import AuthenticationFailed


class AppMovilJWTAuthentication(JWTAuthentication):
    """
    Autenticación JWT que verifica si el usuario es Operador o Superuser.
    Invalida tokens de usuarios que perdieron el grupo.
    """
    
    def authenticate(self, request):
        # Obtener el usuario normalmente con JWT
        result = super().authenticate(request)
        
        if result is None:
            return None
        
        user, validated_token = result
        
        # Verificar si el usuario está activo
        if not user.is_active:
            raise AuthenticationFailed('Usuario inactivo.')
        
        # Verificar si es Operador o Superuser
        es_operador = user.groups.filter(name='Operador').exists()
        es_superuser = user.is_superuser
        
        if not (es_operador or es_superuser):
            # INVALIDAR el token
            raise AuthenticationFailed(
                'No tienes permisos para usar la aplicación móvil. '
                'Contacta al administrador.'
            )
        
        return user, validated_token