from django.shortcuts import render, redirect 
from sistema.models import SistemaUsuario, SistemaSector, SistemaEvento, SistemaLectura, SistemaPago, SistemaTarifa
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, logout as auth_login, logout
from django.db.models import Sum, Count
from django.db.models.functions import TruncMonth
from django.http import JsonResponse
# Create your views here.

@login_required
def index(request):
    lecturas = SistemaLectura.objects.all()
    sectores = SistemaSector.objects.all()
    consumo_sector = lecturas.values('usuario__sector__nombre').annotate(total=Sum('consumo')).order_by('-total')[:5]
    recaudos = SistemaTarifa.objects.all()
    recaudos_sector = SistemaPago.objects.values('usuario__sector__nombre').annotate(total=Sum('monto')).order_by('-total')[:5]
    usuarios_total = SistemaUsuario.objects.count()
    
    
    top_consumidores = lecturas.values('usuario__nombres').annotate(total=Sum('consumo')).order_by('-total')[:5]
    eventos = SistemaEvento.objects.all()
    
    
    return render(request, 'index.html', {'sectores': sectores, 
                                          'lecturas': lecturas, 
                                          'consumo_sector': consumo_sector, 
                                          'recaudos': recaudos, 
                                          'usuarios_total': usuarios_total, 
                                          'recaudos_sector': recaudos_sector,     
                                          'top_consumidores': top_consumidores,
                                            'eventos': eventos

                                            
                                          })

# =============Usuarios============
@login_required
def list_users(request):    
    usuarios = SistemaUsuario.objects.all()
    sectores = SistemaSector.objects.all()
    return render(request, 'usuarios/list_users.html', {'usuarios': usuarios, 'sectores': sectores})

@login_required
def edit_user(request, id):
    usuario = SistemaUsuario.objects.get(id=id)
    sectores = SistemaSector.objects.all()
    return render(request, 'usuarios/edit_user.html', {'usuario': usuario, 'sectores': sectores})

@login_required
def save_user(request, id ):
    usuario = SistemaUsuario.objects.get(id=id)
    usuario.dni_cedula = request.POST['dni_cedula']
    usuario.nombres = request.POST['nombres']
    usuario.apellido_paterno = request.POST['apellido_paterno']
    usuario.apellido_materno = request.POST['apellido_materno']
    usuario.telefono = request.POST['telefono']
    usuario.sector = SistemaSector.objects.get(id=request.POST['sector'])
    usuario.save()
    messages.success(request, 'Usuario guardado correctamente')
    return render(request, 'usuarios/list_users.html', {'usuarios': SistemaUsuario.objects.all()})

@login_required
def new_user(request):
    sectores = SistemaSector.objects.all()
    return render(request, 'usuarios/new_user.html', {'sectores': sectores})

@login_required
def save_user_new(request):
    try:
        sector = SistemaSector.objects.get(id=request.POST['sector'])
        usuario = SistemaUsuario()
        usuario.dni_cedula = request.POST['dni_cedula']
        usuario.nombres = request.POST['nombres']
        usuario.apellido_paterno = request.POST['apellido_paterno']
        usuario.apellido_materno = request.POST['apellido_materno']
        usuario.telefono = request.POST['telefono']
        usuario.sector = sector
        usuario.save()
        messages.success(request, 'Usuario guardado correctamente')         
        return render(request, 'usuarios/list_users.html', {'usuarios': SistemaUsuario.objects.all()})
    except Exception as e:
        messages.error(request, 'Error al guardar el usuario')
        return render(request, 'usuarios/list_users.html', {'usuarios': SistemaUsuario.objects.all()})

@login_required
def delete_user(request, id):
    try:
        usuario = SistemaUsuario.objects.get(id=id)
        usuario.delete()
        messages.success(request, 'Usuario eliminado correctamente')
        return render(request, 'usuarios/list_users.html', {'usuarios': SistemaUsuario.objects.all()})
    except Exception as e:
        messages.error(request, 'Error al eliminar el usuario')
        return render(request, 'usuarios/list_users.html', {'usuarios': SistemaUsuario.objects.all()})

# =============Sectores============
@login_required
def list_sectors(request):    
    sectores = SistemaSector.objects.all()
    return render(request, 'sectores/list_sector.html', {'sectores': sectores})

@login_required
def edit_sector(request, id):
    sector = SistemaSector.objects.get(id=id)
    return render(request, 'sectores/edit_sector.html', {'sector': sector})

@login_required
def save_edit_sector(request, id):
    try:
        sector = SistemaSector.objects.get(id=id)
        sector.nombre = request.POST['nombre']
        sector.descripcion = request.POST['descripcion']
        sector.estado = request.POST['estado']
        sector.save()
        messages.success(request, 'Sector editado correctamente')
        return render(request, 'sectores/list_sector.html', {'sectores': SistemaSector.objects.all()})
    except Exception as e:
        messages.error(request, 'Error al editar el sector')
        return render(request, 'sectores/list_sector.html', {'sectores': SistemaSector.objects.all()})

@login_required
def new_sector(request):
    return render(request, 'sectores/new_sector.html')

@login_required
def save_sector_new(request):
    try:
        sector = SistemaSector()        
        sector.nombre = request.POST['nombre']
        sector.descripcion = request.POST['descripcion']
        sector.estado = request.POST['estado']
        sector.save()
        messages.success(request, 'Sector guardado correctamente')
        return render(request, 'sectores/list_sector.html', {'sectores': SistemaSector.objects.all()})
    except Exception as e:
        messages.error(request, 'Error al guardar el sector')
        return render(request, 'sectores/list_sector.html', {'sectores': SistemaSector.objects.all()})

@login_required
def delete_sector(request, id):
    try:
        sector = SistemaSector.objects.get(id=id)
        sector.delete()
        messages.success(request, 'Sector eliminado correctamente')
        return render(request, 'sectores/list_sector.html', {'sectores': SistemaSector.objects.all()})
    except Exception as e:
        messages.error(request, 'Error al eliminar el sector')
        return render(request, 'sectores/list_sector.html', {'sectores': SistemaSector.objects.all()})

# =============Tipos de Eventos============
@login_required
def list_tipo_eventos(request):    
    tipo_eventos = SistemaEvento.objects.all()
    return render(request, 'eventos/list_tipo_evento.html', {'tipo_eventos': tipo_eventos})
@login_required
def edit_tipo_evento(request, id):
    tipo_evento = SistemaEvento.objects.get(id=id)
    return render(request, 'eventos/edit_tipo_evento.html', {'tipo_evento': tipo_evento})
@login_required
def save_edit_tipo_evento(request, id):
    try:
        tipo_evento = SistemaEvento.objects.get(id=id)
        tipo_evento.nombre = request.POST['nombre']
        tipo_evento.fecha = request.POST['fecha']
        tipo_evento.lugar = request.POST['lugar']
        tipo_evento.descripcion = request.POST['descripcion']
        tipo_evento.save()
        messages.success(request, 'Tipo de evento editado correctamente')
        return render(request, 'eventos/list_tipo_evento.html', {'tipo_eventos': SistemaEvento.objects.all()})
    except Exception as e:
        messages.error(request, 'Error al editar el tipo de evento')
    return render(request, 'eventos/list_tipo_evento.html', {'tipo_eventos': SistemaEvento.objects.all()})
@login_required
def new_tipo_evento(request):
    return render(request, 'eventos/new_tipo_evento.html')
@login_required
def save_tipo_evento_new(request):
    try:
        tipo_evento = SistemaEvento()        
        tipo_evento.nombre = request.POST['nombre']
        tipo_evento.fecha = request.POST['fecha']
        tipo_evento.lugar = request.POST['lugar']
        tipo_evento.descripcion = request.POST['descripcion']        
        tipo_evento.save()
        messages.success(request, 'Tipo de evento guardado correctamente')
        return render(request, 'eventos/list_tipo_evento.html', {'tipo_eventos': SistemaEvento.objects.all()})
    except Exception as e:
        messages.error(request, 'Error al guardar el tipo de evento')
        return render(request, 'eventos/list_tipo_evento.html', {'tipo_eventos': SistemaEvento.objects.all()})
@login_required
def delete_tipo_evento(request, id):
    try:
        tipo_evento = SistemaEvento.objects.get(id=id)
        tipo_evento.delete()
        messages.success(request, 'Tipo de evento eliminado correctamente')
        return render(request, 'eventos/list_tipo_evento.html', {'tipo_eventos': SistemaEvento.objects.all()})
    except Exception as e:
        messages.error(request, 'Error al eliminar el tipo de evento')
        return render(request, 'eventos/list_tipo_evento.html', {'tipo_eventos': SistemaEvento.objects.all()})


# =============Lecturas============
from datetime import date
from django.shortcuts import get_object_or_404
@login_required
def list_sec_lec(request):    
    sectores = SistemaSector.objects.all()
    return render(request, 'lecturas/list_sec_lec.html', {'sectores': sectores})
@login_required
def lectura_sector(request, id):
    hoy = date.today()
    # lee de GET; si no viene, usa actual
    anio_actual = int(request.GET.get("anio", hoy.year))
    mes_actual = int(request.GET.get("mes", hoy.month))

    lista_anios = list(range(hoy.year - 5, hoy.year + 5))
    lista_meses = [
        (1, "Enero"), (2, "Febrero"), (3, "Marzo"), (4, "Abril"),
        (5, "Mayo"), (6, "Junio"), (7, "Julio"), (8, "Agosto"),
        (9, "Septiembre"), (10, "Octubre"), (11, "Noviembre"), (12, "Diciembre"),
    ]

    sector = get_object_or_404(SistemaSector, id=id)
    usuarios = SistemaUsuario.objects.filter(sector_id=id).order_by('apellido_paterno', 'apellido_materno', 'nombres')

    datos = []
    for usuario in usuarios:
        lectura_actual = SistemaLectura.objects.filter(
            usuario=usuario, anio=anio_actual, mes=mes_actual
        ).first()

        # mes anterior
        if mes_actual == 1:
            anio_anterior, mes_anterior = anio_actual - 1, 12
        else:
            anio_anterior, mes_anterior = anio_actual, mes_actual - 1

        lectura_anterior = SistemaLectura.objects.filter(
            usuario=usuario, anio=anio_anterior, mes=mes_anterior
        ).first()

        consumo = None
        if lectura_actual and lectura_anterior:
            consumo = lectura_actual.consumo - lectura_anterior.consumo

        datos.append({
            "usuario": usuario,
            "lectura_actual": lectura_actual.consumo if lectura_actual else "",
            "lectura_anterior": lectura_anterior.consumo if lectura_anterior else "",
            "consumo": consumo if consumo is not None else "",
        })

    return render(request, "lecturas/lectura_sector.html", {
        "sector": sector,
        "sector_id": id,
        "anio_actual": anio_actual,
        "mes_actual": mes_actual,
        "lista_anios": lista_anios,
        "lista_meses": lista_meses,
        "usuarios": datos,
    })
@login_required
def save_lectura(request, id):
    sector = get_object_or_404(SistemaSector, id=id)

    if request.method == "POST":
        anio = int(request.POST.get("anio"))
        mes = int(request.POST.get("mes"))

        usuarios = SistemaUsuario.objects.filter(sector=sector)

        for usuario in usuarios:
            campo = f"lectura_actual_{usuario.id}"
            valor = request.POST.get(campo)

            if valor:  # si se ingresó lectura
                valor = int(valor)

                lectura, created = SistemaLectura.objects.update_or_create(
                    usuario=usuario,
                    anio=anio,
                    mes=mes,
                    defaults={"consumo": valor}
                )

                # 👇 Crear pago pendiente si la lectura es nueva
                if created:
                    SistemaPago.objects.create(
                        lectura=lectura,
                        usuario=usuario,
                        monto=0,          # se calculará al pagar
                        fecha_pago=date.today(),  # aún no pagado
                        estado=False      # pendiente
                    )

        messages.success(request, f"Lecturas de {sector.nombre} guardadas correctamente")
        return render(request, 'lecturas/list_sec_lec.html', {'sectores': SistemaSector.objects.all()})

    messages.error(request, "Método inválido")
    return render(request, 'lecturas/list_sec_lec.html', {'sectores': SistemaSector.objects.all()})


#=====TARIFAS====
@login_required
def list_tarifas(request):
    tarifas = SistemaTarifa.objects.all()
    return render(request, 'tarifas/list_tarifas.html', {'tarifas': tarifas})
@login_required
def new_tarifa(request):
    return render(request, 'tarifas/new_tarifa.html')
@login_required
def save_new_tarifa(request):
    if request.method == "POST":
        try:
            valor = request.POST.get("tarifa")
            activa = request.POST.get("activa") == "on"  # checkbox en el formulario

            # Si se marca como activa, desactivar las demás
            if activa:
                SistemaTarifa.objects.update(activa=False)

            starifa = SistemaTarifa(
                tarifa=valor,
                activa=activa
            )
            starifa.save()

            messages.success(request, "Tarifa guardada correctamente")
            return render(request, "tarifas/list_tarifas.html", {"tarifas": SistemaTarifa.objects.all()})

        except Exception as e:
            messages.error(request, f"Error al guardar la tarifa: {e}")
            return render(request, "tarifas/list_tarifas.html", {"tarifas": SistemaTarifa.objects.all()})

    return redirect("list_tarifas")
@login_required
def edit_tarifa(request, id):
    tarifa = get_object_or_404(SistemaTarifa, id=id)

    if request.method == "POST":
        try:
            valor = request.POST.get("tarifa")
            activa = request.POST.get("activa") == "on"

            # Si se marca como activa, desactivar las demás
            if activa:
                SistemaTarifa.objects.exclude(id=tarifa.id).update(activa=False)

            tarifa.tarifa = valor
            tarifa.activa = activa
            tarifa.save()

            messages.success(request, "Tarifa actualizada correctamente")
            return render(request, "tarifas/list_tarifas.html", {"tarifas": SistemaTarifa.objects.all()})

        except Exception as e:
            messages.error(request, f"Error al actualizar la tarifa: {e}")
            return render(request, "tarifas/list_tarifas.html", {"tarifas": SistemaTarifa.objects.all()})

    return render(request, "tarifas/edit_tarifa.html", {"tarifa": tarifa})

@login_required
def save_edit_tarifa(request, id):
    if request.method == "POST":
        try:
            id = request.POST.get("id")
            valor = request.POST.get("tarifa")
            activa = request.POST.get("activa") == "on"  # checkbox en el formulario

            # Si se marca como activa, desactivar las demás
            if activa:
                SistemaTarifa.objects.update(activa=False)

            SistemaTarifa.objects.filter(id=id).update(
                tarifa=valor,
                activa=activa
            )

            messages.success(request, "Tarifa editada correctamente")
            return render(request, "tarifas/list_tarifas.html", {"tarifas": SistemaTarifa.objects.all()})

        except Exception as e:
            messages.error(request, f"Error al editar la tarifa: {e}")
            return render(request, "tarifas/list_tarifas.html", {"tarifas": SistemaTarifa.objects.all()})

    return redirect("list_tarifas")
@login_required
def delete_tarifa(request, id):
    try:
        tarifa = SistemaTarifa.objects.get(id=id)
        tarifa.delete()
        messages.success(request, 'Tarifa eliminada correctamente')
        return render(request, 'tarifas/list_tarifas.html', {'tarifas': SistemaTarifa.objects.all()})
    except Exception as e:
        messages.error(request, 'Error al eliminar la tarifa')
        return render(request, 'tarifas/list_tarifas.html', {'tarifas': SistemaTarifa.objects.all()})

#======== PAGOS ==================
@login_required
def list_pag_usuarios(request):
    usuarios = SistemaUsuario.objects.all()
    sectores = SistemaSector.objects.all()
    return render(request, 'pagos/list_pag_usuarios.html', {'usuarios': usuarios, 'sectores': sectores})
@login_required
def process_pag_usuario(request, id):
    usuario = get_object_or_404(SistemaUsuario, id=id)
    sector = get_object_or_404(SistemaSector, id=usuario.sector_id)

    # todas las lecturas del usuario ordenadas por año/mes
    lecturas = SistemaLectura.objects.filter(usuario=usuario).order_by('-anio', '-mes')

    datos = []
    for lectura in lecturas:
        pago = SistemaPago.objects.filter(lectura=lectura, usuario=usuario).first()
        datos.append({
            "anio": lectura.anio,
            "mes": lectura.mes,
            "consumo": lectura.consumo,
            "pagado": True if pago and pago.estado else False,
            "monto": pago.monto if pago else None,
            "fecha_pago": pago.fecha_pago if pago else None,
        })

    return render(request, "pagos/process_pago_user.html", {
        "usuario": usuario,
        "sector": sector,
        "lecturas": datos,
    })
@login_required
def registrar_pago(request, usuario_id, anio, mes):
    usuario = get_object_or_404(SistemaUsuario, id=usuario_id)

    # buscar la lectura del mes/año
    lectura = SistemaLectura.objects.filter(usuario=usuario, anio=anio, mes=mes).first()
    if not lectura:
        messages.error(request, f"No existe lectura para {mes}/{anio}")
        return redirect("process_pag_usuario", id=usuario.id)

    # verificar si ya existe pago
    pago_existente = SistemaPago.objects.filter(lectura=lectura, usuario=usuario).first()
    if pago_existente and pago_existente.estado:
        messages.warning(request, f"La lectura de {mes}/{anio} ya está pagada")
        return redirect("process_pag_usuario", id=usuario.id)

    # calcular monto con tarifa activa
    tarifa_activa = SistemaTarifa.objects.filter(activa=True).first()
    if not tarifa_activa:
        messages.error(request, "No existe tarifa activa para calcular el pago")
        return redirect("process_pag_usuario", id=usuario.id)

    monto = lectura.consumo * tarifa_activa.tarifa if lectura.consumo else 0

    # crear o actualizar pago
    pago, created = SistemaPago.objects.update_or_create(
        lectura=lectura,
        usuario=usuario,
        defaults={
            "monto": monto,
            "fecha_pago": date.today(),  # fecha real del pago
            "estado": True
        }
    )

    messages.success(request, f"Pago registrado para {mes}/{anio}, monto: {monto:.2f}")
    return redirect("process_pag_usuario", id=usuario.id)

# Login y Logout
def login(request):
    return render(request, "registration/login.html")


def exit(request):
    logout(request)    
    return redirect("index")

# =============Asistencias a Eventos============
@login_required
def asistencia_evento(request, evento_id):
    evento = get_object_or_404(SistemaEvento, id=evento_id)

    # Si no existen asistencias, crearlas automáticamente
    if not SistemaAsistencia.objects.filter(evento=evento).exists():
        usuarios = SistemaUsuario.objects.all()  # o filtra por sector si aplica
        for usuario in usuarios:
            SistemaAsistencia.objects.create(
                evento=evento,
                usuario=usuario,
                fecha_hora=evento.fecha,  # o date.today()
                asistio=False
            )

    asistencias = SistemaAsistencia.objects.filter(evento=evento).select_related("usuario__sector")
    return render(request, "eventos/asistencia_evento.html", {
        "evento": evento,
        "asistencias": asistencias
    })

@login_required
def save_asistencias(request, evento_id):
    evento = get_object_or_404(SistemaEvento, id=evento_id)
    if request.method == "POST":
        asistencias = SistemaAsistencia.objects.filter(evento=evento)
        for asistencia in asistencias:
            campo = f"asistio_{asistencia.id}"
            asistencia.asistio = campo in request.POST
            asistencia.save()
        messages.success(request, "Asistencias actualizadas correctamente")
        return redirect("asistencia_evento", evento_id=evento.id)



# tu_app/views.py
from rest_framework import viewsets
import json
from .models import (
    SistemaUsuario, SistemaEvento, SistemaAsistencia,
    SistemaLectura, SistemaPago, SistemaMedidor, SistemaTarifa
)
from .serializers import (
    SistemaUsuarioSerializer, SistemaEventoSerializer, SistemaAsistenciaSerializer,
    SistemaLecturaSerializer, SistemaPagoSerializer, SistemaMedidorSerializer,
    SistemaTarifaSerializer
)

class SistemaUsuarioViewSet(viewsets.ModelViewSet):
    queryset = SistemaUsuario.objects.all()
    serializer_class = SistemaUsuarioSerializer

class SistemaEventoViewSet(viewsets.ModelViewSet):
    queryset = SistemaEvento.objects.all()
    serializer_class = SistemaEventoSerializer

class SistemaAsistenciaViewSet(viewsets.ModelViewSet):
    queryset = SistemaAsistencia.objects.all()
    serializer_class = SistemaAsistenciaSerializer

class SistemaTarifaViewSet(viewsets.ModelViewSet):
    queryset = SistemaTarifa.objects.all()
    serializer_class = SistemaTarifaSerializer

class SistemaMedidorViewSet(viewsets.ModelViewSet):
    queryset = SistemaMedidor.objects.all()
    serializer_class = SistemaMedidorSerializer

class SistemaLecturaViewSet(viewsets.ModelViewSet):
    queryset = SistemaLectura.objects.all()
    serializer_class = SistemaLecturaSerializer

class SistemaPagoViewSet(viewsets.ModelViewSet):
    queryset = SistemaPago.objects.all()
    serializer_class = SistemaPagoSerializer
