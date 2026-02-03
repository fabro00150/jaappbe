from rest_framework import viewsets, status, mixins
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils import timezone
from .models import SistemaUsuario
from .serializers import SistemaUsuarioSerializer
from django.utils.dateparse import parse_datetime
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from rest_framework.authtoken.models import Token



from rest_framework import viewsets
from .models import (
    SistemaUsuario, SistemaEvento, SistemaAsistencia,
    SistemaLectura, SistemaPago, SistemaMedidor, SistemaSector, SistemaTarifa
)
from .serializers import (
    SistemaUsuarioSerializer, SistemaEventoSerializer, SistemaAsistenciaSerializer,
    SistemaLecturaSerializer, SistemaPagoSerializer, SistemaMedidorSerializer,
    SistemaSectorSerializer, SistemaTarifaSerializer
)

class SistemaSectorViewSet(viewsets.ModelViewSet):
    queryset = SistemaSector.objects.all()
    serializer_class = SistemaSectorSerializer

class SistemaUsuarioViewSet(viewsets.ModelViewSet):
    queryset = SistemaUsuario.objects.all()
    serializer_class = SistemaUsuarioSerializer

    def create(self, request, *args, **kwargs):
        print(f"📝 POST data: {request.data}")
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            print(f"❌ Errores: {serializer.errors}")
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        self.perform_create(serializer)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        print(f"📝 PUT data: {request.data}")
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        if not serializer.is_valid():
            print(f"❌ Errores: {serializer.errors}")
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        self.perform_update(serializer)
        return Response(serializer.data)

    @action(detail=False, methods=['post'])
    def sync(self, request):
        """Endpoint para sincronizar usuarios desde Flutter"""
        updated_after = request.data.get('updated_after')
        
        if updated_after:
            from django.utils.dateparse import parse_datetime
            queryset = self.get_queryset().filter(updated_at__gte=parse_datetime(updated_after))
        else:
            queryset = self.get_queryset()
        
        serializer = self.get_serializer(queryset, many=True)
        return Response({
            'timestamp': timezone.now().isoformat(),
            'data': serializer.data
        })
        

class SistemaEventoViewSet(viewsets.ModelViewSet):
    queryset = SistemaEvento.objects.all()
    serializer_class = SistemaEventoSerializer

    @action(detail=False, methods=['post'])
    def sync(self, request):
        """Endpoint para sincronizar eventos desde Flutter"""
        updated_after = request.data.get('updated_after')

        if updated_after:
            queryset = self.get_queryset().filter(
                updated_at__gte=parse_datetime(updated_after)
            )
        else:
            queryset = self.get_queryset()

        serializer = self.get_serializer(queryset, many=True)
        return Response({
            'timestamp': timezone.now().isoformat(),
            'data': serializer.data
        })

class SistemaAsistenciaViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet
):
    queryset = SistemaAsistencia.objects.all()
    serializer_class = SistemaAsistenciaSerializer
    
    def update(self, request, *args, **kwargs):        
        try:
            return super().update(request, *args, **kwargs)
        except SistemaAsistencia.DoesNotExist:
                # Si falla (porque el ID no existe), intentamos crear
                # Nota: Esto requiere que el frontend envie todos los datos necesarios
                serializer = self.get_serializer(data=request.data)
                serializer.is_valid(raise_exception=True)
                self.perform_create(serializer)
                headers = self.get_success_headers(serializer.data)
                return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
            
    @action(detail=False, methods=['post'])
    def sync(self, request):
        """
        Endpoint para sincronizar asistencias hacia Flutter (solo descarga).
        La app NO crea asistencias; solo las lee y actualiza.
        Opcionalmente puede filtrar por evento.
        """
        updated_after = request.data.get('updated_after')
        evento_id = request.data.get('evento')  # opcional

        queryset = self.get_queryset()

        if evento_id:
            queryset = queryset.filter(evento_id=evento_id)

        if updated_after:
            queryset = queryset.filter(
                updated_at__gte=parse_datetime(updated_after)
            )

        serializer = self.get_serializer(queryset, many=True)
        return Response({
            'timestamp': timezone.now().isoformat(),
            'data': serializer.data
        })
class SistemaTarifaViewSet(viewsets.ModelViewSet):
    queryset = SistemaTarifa.objects.all()
    serializer_class = SistemaTarifaSerializer

class SistemaMedidorViewSet(viewsets.ModelViewSet):
    queryset = SistemaMedidor.objects.all()
    serializer_class = SistemaMedidorSerializer
    
    @action(detail=False, methods=['post'])
    def sync(self, request):
        """Endpoint para sincronizar medidores desde Flutter"""
        updated_after = request.data.get('updated_after')

        if updated_after:
            queryset = self.get_queryset().filter(
                updated_at__gte=parse_datetime(updated_after)
            )
        else:
            queryset = self.get_queryset()

        serializer = self.get_serializer(queryset, many=True)
        return Response({
            'timestamp': timezone.now().isoformat(),
            'data': serializer.data,
        })

class SistemaLecturaViewSet(viewsets.ModelViewSet):
    queryset = SistemaLectura.objects.all()
    serializer_class = SistemaLecturaSerializer
    
    @action(
        detail=False,
        methods=['post'],
        parser_classes=[MultiPartParser, FormParser],
    )
    def upload_foto(self, request):
        print('📥 upload_foto data:', request.data)
        print('📥 upload_foto files:', request.FILES)

        usuario_id = request.data.get('usuario')
        anio = request.data.get('anio')
        mes = request.data.get('mes')
        foto = request.FILES.get('foto')

        if not foto:
            print('❌ No se recibió archivo foto')
            return Response({'detail': 'No se envió archivo foto'}, status=400)

        lectura = SistemaLectura.objects.filter(
            usuario_id=usuario_id,
            anio=anio,
            mes=mes,
        ).order_by('-id').first()

        if not lectura:
            print('❌ Lectura no encontrada para', usuario_id, anio, mes)
            return Response({'detail': 'Lectura no encontrada'}, status=404)

        lectura.foto = foto
        lectura.save()
        print('✅ Foto guardada en:', lectura.foto.name)

        return Response({'detail': 'Foto subida'}, status=200)

    def create(self, request, *args, **kwargs):
        print(f"📝 POST /lecturas/ data: {request.data}")
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            print(f"❌ Errores: {serializer.errors}")
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        self.perform_create(serializer)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        print(f"📝 PUT /lecturas/ data: {request.data}")
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        if not serializer.is_valid():
            print(f"❌ Errores: {serializer.errors}")
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        self.perform_update(serializer)
        return Response(serializer.data)

    @action(detail=False, methods=['post'])
    def sync(self, request):
        updated_after = request.data.get('updated_after')

        if updated_after:
            from django.utils.dateparse import parse_datetime
            queryset = self.get_queryset().filter(
                updated_at__gte=parse_datetime(updated_after)
            )
        else:
            queryset = self.get_queryset()

        serializer = self.get_serializer(queryset, many=True)
        return Response({
            'timestamp': timezone.now().isoformat(),
            'data': serializer.data
        })

class SistemaPagoViewSet(viewsets.ModelViewSet):
    queryset = SistemaPago.objects.all()
    serializer_class = SistemaPagoSerializer


@api_view(['POST'])
@permission_classes([AllowAny])
def login_view(request):
    username = request.data.get('username')
    password = request.data.get('password')

    if not username or not password:
        return Response(
            {'detail': 'username y password son requeridos'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    user = authenticate(username=username, password=password)
    if user is None or not user.is_active:
        return Response(
            {'detail': 'Credenciales inválidas'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    token, _ = Token.objects.get_or_create(user=user)

    return Response(
        {
            'id': user.id,
            'username': user.username,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'email': user.email,
            'token': token.key,
        },
        status=status.HTTP_200_OK,
    )
    
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def me_view(request):
    user = request.user
    return Response({
        'id': user.id,
        'username': user.username,
        'first_name': user.first_name,
        'last_name': user.last_name,
        'email': user.email,
    })