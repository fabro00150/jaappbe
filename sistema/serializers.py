# serializers.py
from rest_framework import serializers
from .models import (
    SistemaUsuario, SistemaEvento, SistemaAsistencia,
    SistemaLectura, SistemaPago, SistemaMedidor, SistemaSector, SistemaTarifa
)

class SistemaSectorSerializer(serializers.ModelSerializer):
    class Meta:
        model = SistemaSector
        fields = ['id', 'nombre', 'descripcion', 'estado', 'created_at', 'updated_at']

class SistemaUsuarioSerializer(serializers.ModelSerializer):
    sector_nombre = serializers.CharField(source='sector.nombre', read_only=True)
    
    class Meta:
        model = SistemaUsuario
        fields = ['id', 'dni_cedula', 'apellido_paterno', 'apellido_materno', 
                  'nombres', 'telefono', 'sector', 'sector_nombre', 'created_at', 'updated_at']

class SistemaEventoSerializer(serializers.ModelSerializer):
    class Meta:
        model = SistemaEvento
        fields = ['id', 'nombre', 'fecha', 'lugar', 'descripcion', 'created_at', 'updated_at']

class SistemaAsistenciaSerializer(serializers.ModelSerializer):
    evento_nombre = serializers.CharField(source='evento.nombre', read_only=True)
    usuario_nombre = serializers.CharField(source='usuario.nombres', read_only=True)
    
    class Meta:
        model = SistemaAsistencia
        fields = ['id', 'fecha_hora', 'asistio', 'evento', 'evento_nombre', 
                  'usuario', 'usuario_nombre', 'created_at', 'updated_at']

class SistemaTarifaSerializer(serializers.ModelSerializer):
    class Meta:
        model = SistemaTarifa
        fields = ['id', 'tarifa', 'activa', 'created_at', 'updated_at']

class SistemaMedidorSerializer(serializers.ModelSerializer):
    usuario_nombre = serializers.CharField(source='usuario.nombres', read_only=True)
    
    class Meta:
        model = SistemaMedidor
        fields = ['id', 'numero_serie', 'coordenadas', 'fecha_instalacion', 
                  'usuario', 'usuario_nombre', 'created_at', 'updated_at']

class SistemaLecturaSerializer(serializers.ModelSerializer):
    usuario_nombre = serializers.CharField(source='usuario.nombres', read_only=True)
    
    class Meta:
        model = SistemaLectura
        fields = ['id', 'consumo', 'mes', 'anio', 'usuario', 'usuario_nombre', 
                  'created_at', 'updated_at', 'foto']

class SistemaPagoSerializer(serializers.ModelSerializer):
    lectura_consumo = serializers.IntegerField(source='lectura.consumo', read_only=True)
    usuario_nombre = serializers.CharField(source='usuario.nombres', read_only=True)
    
    class Meta:
        model = SistemaPago
        fields = ['id', 'monto', 'fecha_pago', 'estado', 'lectura', 
                  'lectura_consumo', 'usuario', 'usuario_nombre', 'created_at', 'updated_at']
