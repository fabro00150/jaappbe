from django.shortcuts import render, redirect 
from sistema.models import SistemaUsuario, SistemaSector, SistemaEvento, SistemaLectura, SistemaPago, SistemaTarifa
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, logout as auth_login, logout
from django.db.models import Sum, Count, Q, Prefetch, F, Exists, OuterRef
from django.db.models.functions import TruncMonth
from django.http import JsonResponse
from decimal import Decimal
from datetime import date
from django.urls import reverse
from django.utils import timezone
import json
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User, Group, Permission
from django.contrib.auth.hashers import make_password
from django.contrib.contenttypes.models import ContentType
from django.db import transaction
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.utils.decorators import method_decorator

@login_required
def index(request):
    hoy = date.today()
    anio_actual = hoy.year
    mes_actual = hoy.month
    
    # ==================== KPIs PRINCIPALES ====================
    
    # Total usuarios
    usuarios_total = SistemaUsuario.objects.count()
    
    # Total medidores
    medidores_total = SistemaMedidor.objects.count()
    
    # Lecturas del mes actual
    lecturas_mes = SistemaLectura.objects.filter(
        anio=anio_actual, 
        mes=mes_actual
    ).count()
    
    # Consumo total del mes
    lecturas = SistemaLectura.objects.all()
    lecturas_mes_qs = lecturas.filter(anio=anio_actual, mes=mes_actual)
    consumo_mes_total = lecturas_mes_qs.aggregate(
        total=Sum('consumo')
    )['total'] or 0
    
    # ==================== PAGOS Y RECAUDACIÓN ====================
    
    # Pagos realizados del mes
    pagos_mes = SistemaPago.objects.filter(
        fecha_pago__year=anio_actual,
        fecha_pago__month=mes_actual,
        estado=True
    )
    
    # Total recaudado del mes
    recaudado_mes = pagos_mes.aggregate(
        total=Sum('monto')
    )['total'] or Decimal('0.00')
    
    # Pagos pendientes (todos los tiempos)
    pagos_pendientes = SistemaPago.objects.filter(estado=False).count()
    
    # Total que debería haberse recaudado (para eficiencia)
    total_esperado = lecturas_mes_qs.count() * (SistemaTarifa.objects.filter(activa=True).first().tarifa or Decimal('1'))
    if total_esperado > 0:
        eficiencia_recaudacion = round((recaudado_mes / total_esperado) * 100, 1)
    else:
        eficiencia_recaudacion = 0
    
    # ==================== DATOS POR SECTOR ====================
    
    sectores = SistemaSector.objects.filter(estado=True)
    
    # Consumo por sector
    consumo_sector = (lecturas
        .values('usuario__sector__nombre')
        .annotate(total=Sum('consumo'))
        .order_by('-total')[:5]
    )

    # Recaudación por sector
    recaudos_sector = (SistemaPago.objects
        .filter(estado=True)
        .values('usuario__sector__nombre')
        .annotate(total=Sum('monto'))
        .order_by('-total')[:5]
    )
    
    # Usuarios por sector
    usuarios_por_sector = SistemaUsuario.objects.values('sector_id').annotate(
        total=Count('id')
    )
    
    # Pagos pendientes por sector
    pendientes_por_sector = SistemaPago.objects.filter(
        estado=False
    ).values('usuario__sector_id').annotate(
        total=Count('id')
    )
    
    # ==================== TOP CONSUMIDORES ====================
    
    top_consumidores = (lecturas
        .values('usuario__apellido_paterno', 'usuario__nombres')
        .annotate(total=Sum('consumo'))
        .order_by('-total')[:5]
    )
    
    # ==================== EVENTOS ====================
    
    eventos = SistemaEvento.objects.filter(
        fecha__gte=hoy
    ).order_by('fecha')[:5]
    
    # ==================== GRÁFICO ====================
    
    consumo_mensual = (lecturas
        .values('anio', 'mes')
        .annotate(total=Sum('consumo'))
        .order_by('anio', 'mes')
    )

    pagos_mensuales = (SistemaPago.objects
        .filter(estado=True)
        .values('lectura__anio', 'lectura__mes')
        .annotate(total=Sum('monto'))
        .order_by('lectura__anio', 'lectura__mes')
    )

    labels = []
    consumo_data = []
    recaudo_data = []

    pagos_dict = {
        (p['lectura__anio'], p['lectura__mes']): p['total']
        for p in pagos_mensuales
    }

    for row in consumo_mensual:
        labels.append(f"{row['mes']:02d}/{row['anio']}")
        consumo_data.append(float(row['total'] or 0))
        recaudo_data.append(float(pagos_dict.get((row['anio'], row['mes']), 0) or 0))

    chart_data = {
        "labels": labels,
        "series": [
            {"name": "Consumo (m³)", "data": consumo_data},
            {"name": "Recaudado ($)", "data": recaudo_data},
        ],
    }
    
    # Nombres de meses
    meses_nombres = {
        1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril",
        5: "Mayo", 6: "Junio", 7: "Julio", 8: "Agosto",
        9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre"
    }

    return render(request, 'index.html', {
        # KPIs principales
        'usuarios_total': usuarios_total,
        'medidores_total': medidores_total,
        'lecturas_mes': lecturas_mes,
        'recaudado_mes': recaudado_mes,
        'pagos_pendientes': pagos_pendientes,
        'consumo_mes_total': consumo_mes_total,
        'eficiencia_recaudacion': eficiencia_recaudacion,
        'mes_actual': meses_nombres.get(mes_actual, ''),
        
        # Datos por sector
        'sectores': sectores,
        'consumo_sector': consumo_sector,
        'recaudos_sector': recaudos_sector,
        'usuarios_por_sector': usuarios_por_sector,
        'pendientes_por_sector': pendientes_por_sector,
        
        # Otros
        'top_consumidores': top_consumidores,
        'eventos': eventos,
        'chart_data_json': json.dumps(chart_data),
    })
    
# =============Medidores============
@login_required
@permission_required('sistema.view_sistemamedidor', raise_exception=True)
def list_medidores(request):
    medidores = (
        SistemaMedidor.objects
        .select_related('usuario')
        .annotate(
            tiene_lecturas=Exists(
                SistemaLectura.objects.filter(medidor=OuterRef('pk'))
            )
        )
    )
    return render(request, 'medidores/list_medidores.html', {
        'medidores': medidores
    })


@login_required
@permission_required('sistema.add_sistemamedidor', raise_exception=True)
def new_medidor(request):
    usuarios = SistemaUsuario.objects.all()
    return render(request, 'medidores/new_medidor.html', {
        'usuarios': usuarios
    })


@login_required
@permission_required('sistema.add_sistemamedidor', raise_exception=True)
def save_new_medidor(request):
    if request.method == 'POST':
        try:
            usuario = SistemaUsuario.objects.get(id=request.POST['usuario_id'])

            medidor = SistemaMedidor()
            medidor.numero_serie = request.POST['numero_serie']
            medidor.coordenadas = request.POST['coordenadas']  # "lat,lng"
            medidor.observaciones = request.POST.get('observaciones', '')
            medidor.fecha_instalacion = request.POST['fecha_instalacion']
            medidor.usuario = usuario
            medidor.save()

            messages.success(request, 'Medidor creado correctamente')
        except Exception as e:
            messages.error(request, f'Error al crear medidor: {e}')

    return redirect('list_medidores')


@login_required
@permission_required('sistema.change_sistemamedidor', raise_exception=True)
def edit_medidor(request, id):
    medidor = get_object_or_404(SistemaMedidor, id=id)
    usuarios = SistemaUsuario.objects.all()
    return render(request, 'medidores/edit_medidor.html', {
        'medidor': medidor,
        'usuarios': usuarios
    })


@login_required
@permission_required('sistema.change_sistemamedidor', raise_exception=True)
def save_edit_medidor(request, id):
    medidor = get_object_or_404(SistemaMedidor, id=id)

    if request.method == 'POST':
        try:
            usuario = SistemaUsuario.objects.get(id=request.POST['usuario_id'])

            medidor.numero_serie = request.POST['numero_serie']
            medidor.coordenadas = request.POST['coordenadas']
            medidor.observaciones = request.POST.get('observaciones', '')
            medidor.fecha_instalacion = request.POST['fecha_instalacion']
            medidor.usuario = usuario
            medidor.save()

            messages.success(request, 'Medidor actualizado correctamente')
        except Exception as e:
            messages.error(request, f'Error al actualizar medidor: {e}')

    return redirect('list_medidores')


@login_required
@permission_required('sistema.delete_sistemamedidor', raise_exception=True)
def delete_medidor(request, id):
    medidor = get_object_or_404(SistemaMedidor, id=id)

    tiene_lecturas = SistemaLectura.objects.filter(medidor=medidor).exists()


    if tiene_lecturas:
        messages.error(
            request,
            "No se puede eliminar el medidor porque tiene lecturas asociadas."
        )
        return redirect('list_medidores')

    try:
        medidor.delete()
        messages.success(request, 'Medidor eliminado correctamente')
    except Exception as e:
        messages.error(request, f'Error al eliminar medidor: {e}')

    return redirect('list_medidores')

@login_required
@permission_required('sistema.view_sistemamedidor', raise_exception=True)
def mapa_general_medidores(request):
    medidores = (
        SistemaMedidor.objects
        .select_related("usuario", "usuario__sector")
        .all()
    )

    puntos = []
    for m in medidores:
        if not m.coordenadas:
            continue
        try:
            lat_str, lng_str = m.coordenadas.split(",")
            lat = float(lat_str.strip())
            lng = float(lng_str.strip())
        except (ValueError, AttributeError):
            continue

        puntos.append({
            "id": m.id,
            "lat": lat,
            "lng": lng,
            "numero_serie": m.numero_serie,
            "usuario": f"{m.usuario.apellido_paterno} {m.usuario.apellido_materno} {m.usuario.nombres}",
            "dni": m.usuario.dni_cedula,
            "sector": m.usuario.sector.nombre if m.usuario.sector else "",
            "observaciones": m.observaciones or "",
        })

    return render(request, "medidores/mapa_general.html", {
        "puntos_json": json.dumps(puntos),
    })

# =============Usuarios============
@login_required
@permission_required('sistema.view_sistemausuario', raise_exception=True)
def list_users(request):    
    usuarios = SistemaUsuario.objects.all()
    sectores = SistemaSector.objects.all()
    return render(request, 'usuarios/list_users.html', {'usuarios': usuarios, 'sectores': sectores})

@login_required
@permission_required('sistema.change_sistemausuario', raise_exception=True)
def edit_user(request, id):
    usuario = SistemaUsuario.objects.get(id=id)
    sectores = SistemaSector.objects.all()
    return render(request, 'usuarios/edit_user.html', {'usuario': usuario, 'sectores': sectores})

@login_required
@permission_required('sistema.change_sistemausuario', raise_exception=True)
def save_user(request, id):
    usuario = SistemaUsuario.objects.get(id=id)
          
    usuario.nombres = request.POST.get('nombres', '').strip().upper()
    usuario.apellido_paterno = request.POST.get('apellido_paterno', '').strip().upper()
    usuario.apellido_materno = request.POST.get('apellido_materno', '').strip().upper()
    usuario.telefono = request.POST.get('telefono', '').strip()
          
    
    sector_id = request.POST.get('sector')
    if sector_id:
        usuario.sector = SistemaSector.objects.get(id=sector_id)
    
    usuario.save()
    messages.success(request, 'Usuario guardado correctamente')
    return redirect('list_users')

@login_required
@permission_required('sistema.add_sistemausuario', raise_exception=True)
def new_user(request):
    sectores = SistemaSector.objects.all()
    return render(request, 'usuarios/new_user.html', {'sectores': sectores})

@login_required
@permission_required('sistema.add_sistemausuario', raise_exception=True)
def save_user_new(request):
    try:
        sector = SistemaSector.objects.get(id=request.POST.get('sector'))
        usuario = SistemaUsuario()
        usuario.dni_cedula = request.POST.get('dni_cedula', '').strip().upper()
        usuario.nombres = request.POST.get('nombres', '').strip().upper()
        usuario.apellido_paterno = request.POST.get('apellido_paterno', '').strip().upper()
        usuario.apellido_materno = request.POST.get('apellido_materno', '').strip().upper()
        usuario.telefono = request.POST.get('telefono', '').strip()
        usuario.sector = sector
        usuario.save()
        messages.success(request, 'Usuario guardado correctamente')
        return redirect('list_users')
    except Exception as e:
        messages.error(request, f'Error al guardar el usuario: {e}')
        return redirect('list_users')

@login_required
@permission_required('sistema.delete_sistemausuario', raise_exception=True)
def delete_user(request, id):
    try:
        usuario = SistemaUsuario.objects.get(id=id)
        usuario.delete()
        messages.success(request, 'Usuario eliminado correctamente')
        return redirect('list_users')
    except Exception as e:
        messages.error(request, f'Error al eliminar el usuario: {e}')
        return redirect('list_users')
    
# =============Sectores============
@login_required
@permission_required('sistema.view_sistemasector', raise_exception=True)
def list_sectors(request):    
    sectores = SistemaSector.objects.all()
    return render(request, 'sectores/list_sector.html', {'sectores': sectores})

@login_required
@permission_required('sistema.change_sistemasector', raise_exception=True)
def edit_sector(request, id):
    sector = SistemaSector.objects.get(id=id)
    return render(request, 'sectores/edit_sector.html', {'sector': sector})

@login_required
@permission_required('sistema.change_sistemasector', raise_exception=True)
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
@permission_required('sistema.add_sistemasector', raise_exception=True)
def new_sector(request):
    return render(request, 'sectores/new_sector.html')

@login_required
@permission_required('sistema.add_sistemasector', raise_exception=True)
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
@permission_required('sistema.delete_sistemasector', raise_exception=True)
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
@permission_required('sistema.view_sistemaevento', raise_exception=True)
def list_tipo_eventos(request):    
    tipo_eventos = SistemaEvento.objects.all()
    return render(request, 'eventos/list_tipo_evento.html', {'tipo_eventos': tipo_eventos})
@login_required
@permission_required('sistema.change_sistemaevento', raise_exception=True)
def edit_tipo_evento(request, id):
    tipo_evento = SistemaEvento.objects.get(id=id)
    return render(request, 'eventos/edit_tipo_evento.html', {'tipo_evento': tipo_evento})
@login_required
@permission_required('sistema.change_sistemaevento', raise_exception=True)
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
@permission_required('sistema.add_sistemaevento', raise_exception=True)
def new_tipo_evento(request):
    return render(request, 'eventos/new_tipo_evento.html')
@login_required
@permission_required('sistema.add_sistemaevento', raise_exception=True)
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
@permission_required('sistema.delete_sistemaevento', raise_exception=True)
def delete_tipo_evento(request, id):
    try:
        tipo_evento = SistemaEvento.objects.get(id=id)
        tipo_evento.delete()
        messages.success(request, 'Tipo de evento eliminado correctamente')
        return render(request, 'eventos/list_tipo_evento.html', {'tipo_eventos': SistemaEvento.objects.all()})
    except Exception as e:
        messages.error(request, 'Error al eliminar el tipo de evento')
        return render(request, 'eventos/list_tipo_evento.html', {'tipo_eventos': SistemaEvento.objects.all()})
    
from django.db.models.signals import post_save
from django.dispatch import receiver

@receiver(post_save, sender=SistemaEvento)
def crear_asistencias_para_evento(sender, instance, created, **kwargs):
    if not created:
        return
    usuarios = SistemaUsuario.objects.all()
    for usuario in usuarios:
        SistemaAsistencia.objects.get_or_create(
            evento=instance,
            usuario=usuario,
            defaults={
                "fecha_hora": instance.fecha,
                "asistio": False,
            }
        )



# =============Lecturas============
from datetime import date
from django.shortcuts import get_object_or_404

@login_required
@permission_required('sistema.view_sistemalectura', raise_exception=True)
def list_meses_lecturas(request):    
    meses = (SistemaLectura.objects
             .values('anio', 'mes')
             .order_by('anio', 'mes')
             .distinct())

    return render(request, 'lecturas/list_sec_lec.html', {
        'meses': meses,
    })
    
@login_required
@permission_required('sistema.view_sistemalectura', raise_exception=True)
def lecturas_globales(request):
    hoy = date.today()
    anio_actual = int(request.GET.get("anio", hoy.year))
    mes_actual = int(request.GET.get("mes", hoy.month))

    lista_anios = list(range(hoy.year - 5, hoy.year + 5))
    lista_meses = [
        (1, "Enero"), (2, "Febrero"), (3, "Marzo"), (4, "Abril"),
        (5, "Mayo"), (6, "Junio"), (7, "Julio"), (8, "Agosto"),
        (9, "Septiembre"), (10, "Octubre"), (11, "Noviembre"), (12, "Diciembre"),
    ]

    medidores = (
        SistemaMedidor.objects
        .select_related("usuario", "usuario__sector")
        .order_by(
            "usuario__sector__nombre",
            "usuario__apellido_paterno",
            "usuario__apellido_materno",
            "usuario__nombres",
            "numero_serie",
        )
    )

    datos = []
    for med in medidores:
        usuario = med.usuario

        lectura_actual = SistemaLectura.objects.filter(
            usuario=usuario, medidor=med, anio=anio_actual, mes=mes_actual
        ).first()

        # mes anterior
        if mes_actual == 1:
            anio_anterior, mes_anterior = anio_actual - 1, 12
        else:
            anio_anterior, mes_anterior = anio_actual, mes_actual - 1

        lectura_anterior = SistemaLectura.objects.filter(
            usuario=usuario, medidor=med, anio=anio_anterior, mes=mes_anterior
        ).first()

        consumo = None
        if lectura_actual and lectura_anterior:
            consumo = (lectura_actual.consumo or 0) - (lectura_anterior.consumo or 0)

        pago = None
        pagado = False
        if lectura_actual:
            pago = SistemaPago.objects.filter(
                lectura=lectura_actual, usuario=usuario
            ).first()
            pagado = bool(pago and pago.estado)

        datos.append({
            "usuario": usuario,
            "medidor": med,
            "lectura_actual": lectura_actual.consumo if lectura_actual else "",
            "lectura_anterior": lectura_anterior.consumo if lectura_anterior else "",
            "consumo": consumo,
            "pagado": pagado,
            "foto_url": lectura_actual.foto.url if (lectura_actual and lectura_actual.foto) else None,
        })

    # ordenar y consumo_str como ya definimos antes
    datos.sort(
        key=lambda x: (
            not (x["consumo"] is not None and x["consumo"] > 20),
            x["usuario"].sector.nombre,
            x["usuario"].apellido_paterno,
            x["usuario"].apellido_materno,
            x["usuario"].nombres,
            x["medidor"].numero_serie,
        )
    )
    for d in datos:
        d["consumo_str"] = "" if d["consumo"] is None else d["consumo"]


    return render(request, "lecturas/lecturas_globales.html", {
        "anio_actual": anio_actual,
        "mes_actual": mes_actual,
        "lista_anios": lista_anios,
        "lista_meses": lista_meses,
        "usuarios": datos,
    })
    
@login_required
@permission_required('sistema.change_sistemalectura', raise_exception=True)
def save_lecturas_globales(request):
    if request.method != "POST":
        messages.error(request, "Método inválido")
        return redirect("lecturas_globales")

    anio = int(request.POST.get("anio"))
    mes = int(request.POST.get("mes"))

    medidores = SistemaMedidor.objects.select_related("usuario").all()
    errores = []

    for med in medidores:
        usuario = med.usuario
        campo = f"lectura_actual_{med.id}"
        valor_str = request.POST.get(campo)

        if not valor_str:
            continue

        try:
            valor = int(valor_str)
        except ValueError:
            errores.append(f"Lectura inválida para {usuario.dni_cedula} (medidor {med.numero_serie}).")
            continue

        if mes == 1:
            anio_ant, mes_ant = anio - 1, 12
        else:
            anio_ant, mes_ant = anio, mes - 1

        lectura_anterior = SistemaLectura.objects.filter(
            usuario=usuario, medidor=med, anio=anio_ant, mes=mes_ant
        ).first()
        anterior_val = lectura_anterior.consumo if lectura_anterior else 0

        if valor < anterior_val:
            errores.append(
                f"Lectura actual ({valor}) menor que la lectura anterior ({anterior_val}) "
                f"para {usuario.dni_cedula} (medidor {med.numero_serie})."
            )
            continue

        lectura, created = SistemaLectura.objects.update_or_create(
            usuario=usuario,
            medidor=med,
            anio=anio,
            mes=mes,
            defaults={"consumo": valor}
        )

        if created:
            SistemaPago.objects.create(
                lectura=lectura,
                usuario=usuario,
                monto=Decimal("0.00"),
                fecha_pago=None,
                estado=False,
            )

    if errores:
        for e in errores:
            messages.error(request, e)
    else:
        messages.success(request, "Lecturas de todos los medidores guardadas correctamente")

    return redirect("list_meses_lec")

# =============Tarifas============

@login_required
@permission_required('sistema.view_sistematarifa', raise_exception=True)
def list_tarifas(request):
    tarifas = SistemaTarifa.objects.all()
    return render(request, 'tarifas/list_tarifas.html', {'tarifas': tarifas})


@login_required
@permission_required('sistema.add_sistematarifa', raise_exception=True)
def new_tarifa(request):
    return render(request, 'tarifas/new_tarifa.html')


@login_required
@permission_required('sistema.add_sistematarifa', raise_exception=True)
def save_new_tarifa(request):
    if request.method == "POST":
        try:
            valor = request.POST.get("tarifa")
            activa = request.POST.get("activa") == "on"

            if activa:
                SistemaTarifa.objects.update(activa=False)

            SistemaTarifa.objects.create(
                tarifa=valor,
                activa=activa
            )

            messages.success(request, "Tarifa guardada correctamente")
            return redirect("list_tarifas")

        except Exception as e:
            messages.error(request, f"Error al guardar la tarifa: {e}")
            return redirect("list_tarifas")

    return redirect("list_tarifas")


@login_required
@permission_required('sistema.change_sistematarifa', raise_exception=True)
def edit_tarifa(request, id):
    tarifa = get_object_or_404(SistemaTarifa, id=id)

    if request.method == "POST":
        try:
            valor = request.POST.get("tarifa")
            activa = request.POST.get("activa") == "on"

            if activa:
                SistemaTarifa.objects.exclude(id=tarifa.id).update(activa=False)

            tarifa.tarifa = valor
            tarifa.activa = activa
            tarifa.save()

            messages.success(request, "Tarifa actualizada correctamente")
            return redirect("list_tarifas")

        except Exception as e:
            messages.error(request, f"Error al actualizar la tarifa: {e}")
            return redirect("list_tarifas")
    
    return render(request, "tarifas/edit_tarifa.html", {"tarifa": tarifa})


@login_required
@permission_required('sistema.delete_sistematarifa', raise_exception=True)
def delete_tarifa(request, id):
    try:
        tarifa = SistemaTarifa.objects.get(id=id)
        tarifa.delete()
        messages.success(request, 'Tarifa eliminada correctamente')
    except Exception:
        messages.error(request, 'Error al eliminar la tarifa')

    return redirect('list_tarifas')

#======== PAGOS ==================
@login_required
@permission_required('sistema.view_sistemapago', raise_exception=True)
def list_pag_usuarios(request):
    usuarios = SistemaUsuario.objects.all()
    sectores = SistemaSector.objects.all()
    return render(request, 'pagos/list_pag_usuarios.html', {'usuarios': usuarios, 'sectores': sectores})

@login_required
@permission_required('sistema.view_sistemapago', raise_exception=True)
def process_pag_usuario(request, id):
    usuario = get_object_or_404(SistemaUsuario, id=id)
    sector = get_object_or_404(SistemaSector, id=usuario.sector_id)
    tarifa_activa = SistemaTarifa.objects.filter(activa=True).first()
    tarifa_valor = tarifa_activa.tarifa if tarifa_activa else Decimal("0.00")

    medidores_usuario = SistemaMedidor.objects.filter(usuario=usuario).order_by("numero_serie")
    
    medidor_id = request.GET.get("medidor_id", "")
    if medidor_id == "":
        medidor_id_int = None
    else:
        medidor_id_int = int(medidor_id)

    lecturas_qs = (
        SistemaLectura.objects
        .filter(usuario=usuario)
        .select_related('medidor')
        .order_by('anio', 'mes', 'medidor_id')
    )
    # si se seleccionó un medidor, se filtran lecturas para el recibo/gráfico;
    lecturas_filtradas = lecturas_qs
    if medidor_id_int:
        lecturas_filtradas = lecturas_qs.filter(medidor_id=medidor_id_int)

    datos = []
    labels = []
    consumos = []
    lectura_anterior = None

    for lectura in lecturas_filtradas:
        pago = SistemaPago.objects.filter(lectura=lectura, usuario=usuario).first()

        if lectura_anterior is not None and lectura_anterior.medidor_id == lectura.medidor_id:
            consumo_periodo = max(
                (lectura.consumo or 0) - (lectura_anterior.consumo or 0),
                0
            )
        else:
            consumo_periodo = lectura.consumo or 0

        if pago and pago.estado:
            monto = pago.monto
            pagado = True
            fecha_pago = pago.fecha_pago
        else:
            monto = Decimal(consumo_periodo) * tarifa_valor
            pagado = False
            fecha_pago = None

        item = {
            "anio": lectura.anio,
            "mes": lectura.mes,
            "consumo": consumo_periodo,
            "pagado": pagado,
            "monto": monto,
            "fecha_pago": fecha_pago,
            "foto_url": lectura.foto.url if lectura.foto else None,
            "pago_id": pago.id if pago else None,
            "medidor": lectura.medidor,
            "medidor_id": lectura.medidor.id if lectura.medidor else 0,
        }
        datos.append(item)

        labels.append(f"{lectura.mes:02d}-{lectura.anio}")
        consumos.append(consumo_periodo)

        lectura_anterior = lectura

    # lógica de lectura_recibo igual, pero sobre datos (ya filtrados por medidor)
    anio_recibo = request.GET.get("anio")
    mes_recibo = request.GET.get("mes")
    lectura_recibo = None
    auto_print = request.GET.get("auto_print") == "1"

    if anio_recibo and mes_recibo:
        anio_recibo = int(anio_recibo)
        mes_recibo = int(mes_recibo)
        for item in datos:
            if item["anio"] == anio_recibo and item["mes"] == mes_recibo:
                lectura_recibo = item
                break

    if not lectura_recibo and datos:
        for item in reversed(datos):
            if not item["pagado"]:
                lectura_recibo = item
                break
        if not lectura_recibo:
            lectura_recibo = datos[-1]

    return render(request, "pagos/process_pago_user.html", {
        "usuario": usuario,
        "sector": sector,
        "lecturas": datos,
        "lectura_recibo": lectura_recibo,
        "labels": labels,
        "consumos": consumos,
        "tarifa": tarifa_valor,
        "auto_print": auto_print,
        "medidores": medidores_usuario,
        "medidor_id": medidor_id,  # para saber cuál está seleccionado
    })

    
@login_required
@permission_required('sistema.change_sistemapago', raise_exception=True)
def registrar_pago(request, usuario_id, anio, mes, medidor_id):
    usuario = get_object_or_404(SistemaUsuario, id=usuario_id)

    # filtros para la lectura actual
    filtros_lectura = {"usuario": usuario, "anio": anio, "mes": mes}
    if medidor_id != 0:
        filtros_lectura["medidor_id"] = medidor_id
    else:
        filtros_lectura["medidor__isnull"] = True

    lectura = SistemaLectura.objects.filter(**filtros_lectura).first()
    if not lectura:
        messages.error(request, f"No existe lectura para {mes}/{anio} con ese medidor")
        return redirect("process_pag_usuario", id=usuario.id)

    pago_existente = SistemaPago.objects.filter(lectura=lectura, usuario=usuario).first()
    if pago_existente and pago_existente.estado:
        messages.warning(request, f"La lectura de {mes}/{anio} ya está pagada")
        return redirect("process_pag_usuario", id=usuario.id)

    tarifa_activa = SistemaTarifa.objects.filter(activa=True).first()
    if not tarifa_activa:
        messages.error(request, "No existe tarifa activa para calcular el pago")
        return redirect("process_pag_usuario", id=usuario.id)

    # calcular mes anterior (para el mismo medidor)
    if mes == 1:
        anio_anterior, mes_anterior = anio - 1, 12
    else:
        anio_anterior, mes_anterior = anio, mes - 1

    filtros_ant = {"usuario": usuario, "anio": anio_anterior, "mes": mes_anterior}
    if medidor_id != 0:
        filtros_ant["medidor_id"] = medidor_id
    else:
        filtros_ant["medidor__isnull"] = True

    lectura_anterior = SistemaLectura.objects.filter(**filtros_ant).first()

    if lectura_anterior:
        consumo_periodo = max(
            (lectura.consumo or 0) - (lectura_anterior.consumo or 0),
            0
        )
    else:
        consumo_periodo = lectura.consumo or 0

    monto = consumo_periodo * tarifa_activa.tarifa

    # asociar medidor si la lectura no tiene (caso usuario con 1 medidor y medidor_id=0)
    if lectura.medidor_id is None and medidor_id == 0:
        medidores = list(SistemaMedidor.objects.filter(usuario=usuario).order_by("id"))
        if len(medidores) == 1:
            lectura.medidor = medidores[0]
            lectura.save(update_fields=["medidor"])

    pago, created = SistemaPago.objects.update_or_create(
        lectura=lectura,
        usuario=usuario,
        defaults={
            "monto": monto,
            "fecha_pago": date.today(),
            "estado": True,
        },
    )

    messages.success(request, f"Pago registrado para {mes}/{anio}, monto: {monto:.2f}")
    url = reverse("process_pag_usuario", kwargs={"id": usuario.id})
    return redirect(f"{url}?anio={anio}&mes={mes}&medidor_id={medidor_id}&auto_print=1")

@login_required
@permission_required('sistema.change_sistemapago', raise_exception=True)
def anular_pago(request, pago_id):
    pago = get_object_or_404(SistemaPago, id=pago_id)
    usuario_id = pago.usuario.id    
    pago.estado = False    
    pago.save()

    messages.success(request, "Pago marcado como pendiente nuevamente.")
    return redirect("process_pag_usuario", id=usuario_id)


# =============Login y Logout=============
def login(request):
    return render(request, "registration/login.html")


def exit(request):
    logout(request)    
    return redirect("index")

# =============Asistencias a Eventos============
@login_required
@permission_required('sistema.view_sistemaasistencia', raise_exception=True)
def asistencia_evento(request, evento_id):
    evento = get_object_or_404(SistemaEvento, id=evento_id)

    # crear asistencias faltantes para usuarios nuevos
    usuarios = SistemaUsuario.objects.all()
    for usuario in usuarios:
        SistemaAsistencia.objects.get_or_create(
            evento=evento,
            usuario=usuario,
            defaults={
                "fecha_hora": evento.fecha,
                "asistio": False,
            }
        )

    asistencias = (
        SistemaAsistencia.objects
        .filter(evento=evento)
        .select_related("usuario__sector")
        .order_by("usuario__sector__nombre", "usuario__apellido_paterno", "usuario__apellido_materno")
    )

    return render(request, "eventos/asistencia_evento.html", {
        "evento": evento,
        "asistencias": asistencias
    })

@login_required
@permission_required('sistema.change_asistencia', raise_exception=True)
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


# reportes
# sistema/views.py

@login_required
@permission_required('sistema.view_sistemapago', raise_exception=True)
def reporte_pagos(request):
    hoy = date.today()

    # filtros
    anio = int(request.GET.get("anio", hoy.year))
    mes = request.GET.get("mes")              # "" o "1".."12"
    sector_id = request.GET.get("sector", "") # "" o id
    estado = request.GET.get("estado", "")    # "" / "pagado" / "pendiente"

    usuarios_qs = (
        SistemaUsuario.objects
        .select_related("sector")
        .order_by("sector__nombre", "apellido_paterno", "apellido_materno", "nombres")
    )

    if sector_id:
        usuarios_qs = usuarios_qs.filter(sector_id=sector_id)

    filas = []
    
    # Obtener todos los medidores con sus lecturas
    medidores_qs = SistemaMedidor.objects.select_related('usuario__sector').all()
    
    for medidor in medidores_qs:
        usuario = medidor.usuario
        
        # Filtrar por sector si se especifica
        if sector_id and str(usuario.sector_id) != sector_id:
            continue
        
        # Filtrar lecturas por año y mes
        lecturas_qs = SistemaLectura.objects.filter(
            usuario=usuario, 
            medidor=medidor,
            anio=anio
        )
        if mes:
            lecturas_qs = lecturas_qs.filter(mes=int(mes))
        
        for lectura in lecturas_qs:
            # Obtener o crear pago
            pago = SistemaPago.objects.filter(lectura=lectura, usuario=usuario).first()
            
            # Calcular consumo (diferencia con lectura anterior)
            if lectura.mes == 1:
                anio_ant, mes_ant = anio - 1, 12
            else:
                anio_ant, mes_ant = anio, lectura.mes - 1
            
            lectura_anterior = SistemaLectura.objects.filter(
                usuario=usuario,
                medidor=medidor,
                anio=anio_ant,
                mes=mes_ant
            ).first()
            
            if lectura_anterior:
                consumo = max((lectura.consumo or 0) - (lectura_anterior.consumo or 0), 0)
            else:
                consumo = lectura.consumo or 0
            
            pagado = bool(pago and pago.estado)
            
            # Filtro por estado
            if estado == "pagado" and not pagado:
                continue
            if estado == "pendiente" and pagado:
                continue
            
            # Calcular monto
            tarifa_activa = SistemaTarifa.objects.filter(activa=True).first()
            tarifa_valor = tarifa_activa.tarifa if tarifa_activa else Decimal("0.00")
            
            if pagado and pago:
                monto = pago.monto
                fecha_pago = pago.fecha_pago
            else:
                monto = Decimal(str(consumo)) * tarifa_valor
                fecha_pago = None
            
            filas.append({
                "anio": anio,
                "mes": lectura.mes,
                "usuario": usuario,
                "sector": usuario.sector,
                "medidor": medidor,
                "lectura_actual": lectura.consumo,
                "consumo": consumo,
                "pagado": pagado,
                "monto": monto,
                "fecha_pago": fecha_pago,
            })

    # Ordenar filas
    filas.sort(key=lambda x: (
        x["sector"].nombre if x["sector"] else "",
        x["usuario"].apellido_paterno,
        x["usuario"].apellido_materno or "",
        x["usuario"].nombres,
        x["medidor"].numero_serie if x["medidor"] else "",
        x["mes"]
    ))

    lista_anios = list(range(hoy.year - 5, hoy.year + 1))
    lista_meses = [
        (1, "Enero"), (2, "Febrero"), (3, "Marzo"), (4, "Abril"),
        (5, "Mayo"), (6, "Junio"), (7, "Julio"), (8, "Agosto"),
        (9, "Septiembre"), (10, "Octubre"), (11, "Noviembre"), (12, "Diciembre"),
    ]
    sectores = SistemaSector.objects.all().order_by("nombre")

    # Totales
    total_consumo = sum(f["consumo"] or 0 for f in filas)
    total_monto = sum(f["monto"] or 0 for f in filas)
    total_pagados = sum(1 for f in filas if f["pagado"])
    total_pendientes = len(filas) - total_pagados

    context = {
        "filas": filas,
        "anio": anio,
        "mes": int(mes) if mes else "",
        "sector_id": sector_id,
        "estado": estado,
        "lista_anios": lista_anios,
        "lista_meses": lista_meses,
        "sectores": sectores,
        "usuario_logueado": request.user,  # Usuario que exporta
        "total_consumo": total_consumo,
        "total_monto": total_monto,
        "total_pagados": total_pagados,
        "total_pendientes": total_pendientes,
        "total_registros": len(filas),
    }
    return render(request, "reportes/reporte_pagos.html", context)


# sistema/views.py

@login_required
@permission_required('sistema.view_sistemalectura', raise_exception=True)
def reporte_lecturas(request):
    hoy = date.today()

    anio = int(request.GET.get("anio", hoy.year))
    mes = request.GET.get("mes")
    sector_id = request.GET.get("sector", "")

    # Query base de medidores con lecturas
    medidores_qs = SistemaMedidor.objects.select_related('usuario__sector').all()
    
    if sector_id:
        medidores_qs = medidores_qs.filter(usuario__sector_id=sector_id)

    filas = []
    total_consumo = 0
    total_lecturas = 0

    for medidor in medidores_qs:
        usuario = medidor.usuario
        
        # Filtrar lecturas
        lecturas_qs = SistemaLectura.objects.filter(
            usuario=usuario,
            medidor=medidor,
            anio=anio
        )
        
        if mes:
            lecturas_qs = lecturas_qs.filter(mes=int(mes))
        
        for lectura in lecturas_qs:
            # Calcular consumo (diferencia con lectura anterior)
            if lectura.mes == 1:
                anio_ant, mes_ant = anio - 1, 12
            else:
                anio_ant, mes_ant = anio, lectura.mes - 1
            
            lectura_anterior = SistemaLectura.objects.filter(
                usuario=usuario,
                medidor=medidor,
                anio=anio_ant,
                mes=mes_ant
            ).first()
            
            if lectura_anterior:
                consumo = max((lectura.consumo or 0) - (lectura_anterior.consumo or 0), 0)
            else:
                consumo = lectura.consumo or 0
            
            filas.append({
                "usuario": usuario,
                "lectura": lectura,
                "medidor": medidor,
                "consumo": consumo,
            })
            
            total_consumo += consumo
            total_lecturas += 1

    # Ordenar
    filas.sort(key=lambda x: (
        x["usuario"].sector.nombre if x["usuario"].sector else "",
        x["usuario"].apellido_paterno,
        x["usuario"].apellido_materno or "",
        x["usuario"].nombres,
        x["lectura"].mes if x["lectura"] else 0
    ))

    lista_anios = list(range(hoy.year - 5, hoy.year + 1))
    lista_meses = [
        (1, "Enero"), (2, "Febrero"), (3, "Marzo"), (4, "Abril"),
        (5, "Mayo"), (6, "Junio"), (7, "Julio"), (8, "Agosto"),
        (9, "Septiembre"), (10, "Octubre"), (11, "Noviembre"), (12, "Diciembre"),
    ]
    sectores = SistemaSector.objects.all().order_by("nombre")

    context = {
        "filas": filas,
        "anio": anio,
        "mes": int(mes) if mes else "",
        "sector_id": sector_id,
        "lista_anios": lista_anios,
        "lista_meses": lista_meses,
        "sectores": sectores,
        "usuario_logueado": request.user,
        "total_consumo": total_consumo,
        "total_lecturas": total_lecturas,
        "total_registros": len(filas),
    }
    return render(request, "reportes/reporte_lecturas.html", context)

# =============Descargar APK============
import os
from django.conf import settings
from django.http import FileResponse, Http404
@login_required
@permission_required('sistema.view_lectura', raise_exception=True)
def descargar_apk(request):
    apk_path = os.path.join(settings.MEDIA_ROOT, 'apk', 'app-release.apk')
    if not os.path.exists(apk_path):
        raise Http404("Archivo APK no encontrado.")

    return FileResponse(
        open(apk_path, 'rb'),
        as_attachment=True,
        filename='jaap-app.apk',
        content_type='application/vnd.android.package-archive',
    )

from rest_framework import viewsets, permissions
import json
from rest_framework.permissions import DjangoModelPermissions
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
    permission_classes = [permissions.IsAuthenticated, DjangoModelPermissions]

class SistemaEventoViewSet(viewsets.ModelViewSet):
    queryset = SistemaEvento.objects.all()
    serializer_class = SistemaEventoSerializer
    permission_classes = [permissions.IsAuthenticated, DjangoModelPermissions]

class SistemaAsistenciaViewSet(viewsets.ModelViewSet):
    queryset = SistemaAsistencia.objects.all()
    serializer_class = SistemaAsistenciaSerializer
    permission_classes = [permissions.IsAuthenticated, DjangoModelPermissions]

class SistemaTarifaViewSet(viewsets.ModelViewSet):
    queryset = SistemaTarifa.objects.all()
    serializer_class = SistemaTarifaSerializer
    permission_classes = [permissions.IsAuthenticated, DjangoModelPermissions]

class SistemaMedidorViewSet(viewsets.ModelViewSet):
    queryset = SistemaMedidor.objects.all()
    serializer_class = SistemaMedidorSerializer
    permission_classes = [permissions.IsAuthenticated, DjangoModelPermissions]

class SistemaLecturaViewSet(viewsets.ModelViewSet):
    queryset = SistemaLectura.objects.all()
    serializer_class = SistemaLecturaSerializer
    permission_classes = [permissions.IsAuthenticated, DjangoModelPermissions]

class SistemaPagoViewSet(viewsets.ModelViewSet):
    queryset = SistemaPago.objects.all()
    serializer_class = SistemaPagoSerializer
    permission_classes = [permissions.IsAuthenticated, DjangoModelPermissions]

TRADUCCIONES_PERMISOS = {
    # SistemaAsistencia
    'add_sistemaasistencia': 'Agregar asistencia',
    'change_sistemaasistencia': 'Editar asistencia',
    'delete_sistemaasistencia': 'Eliminar asistencia',
    'view_sistemaasistencia': 'Ver asistencia',
    
    # SistemaEvento
    'add_sistemaevento': 'Agregar evento',
    'change_sistemaevento': 'Editar evento',
    'delete_sistemaevento': 'Eliminar evento',
    'view_sistemaevento': 'Ver evento',
    
    # SistemaLectura
    'add_sistemalectura': 'Agregar lectura',
    'change_sistemalectura': 'Editar lectura',
    'delete_sistemalectura': 'Eliminar lectura',
    'view_sistemalectura': 'Ver lectura',
    
    # SistemaMedidor
    'add_sistemamedidor': 'Agregar medidor',
    'change_sistemamedidor': 'Editar medidor',
    'delete_sistemamedidor': 'Eliminar medidor',
    'view_sistemamedidor': 'Ver medidor',
    
    # SistemaPago
    'add_sistemapago': 'Agregar pago',
    'change_sistemapago': 'Editar pago',
    'delete_sistemapago': 'Eliminar pago',
    'view_sistemapago': 'Ver pago',
    
    # SistemaSector
    'add_sistemasector': 'Agregar sector',
    'change_sistemasector': 'Editar sector',
    'delete_sistemasector': 'Eliminar sector',
    'view_sistemasector': 'Ver sector',
    
    # SistemaTarifa
    'add_sistematarifa': 'Agregar tarifa',
    'change_sistematarifa': 'Editar tarifa',
    'delete_sistematarifa': 'Eliminar tarifa',
    'view_sistematarifa': 'Ver tarifa',
    
    # SistemaUsuario
    'add_sistemausuario': 'Agregar usuario',
    'change_sistemausuario': 'Editar usuario',
    'delete_sistemausuario': 'Eliminar usuario',
    'view_sistemausuario': 'Ver usuario',
}

NOMBRES_MODELOS = {
    'sistemaasistencia': 'Asistencia',
    'sistemaevento': 'Evento',
    'sistemalectura': 'Lectura',
    'sistemamedidor': 'Medidor',
    'sistemapago': 'Pago',
    'sistemasector': 'Sector',
    'sistematarifa': 'Tarifa',
    'sistemausuario': 'Usuario',
}


def obtener_permisos_sistema():
    """Obtiene solo los permisos de los modelos del sistema, traducidos"""
    # Lista de modelos permitidos
    modelos_permitidos = [
        'sistemaasistencia',
        'sistemaevento', 
        'sistemalectura',
        'sistemamedidor',
        'sistemapago',
        'sistemasector',
        'sistematarifa',
        'sistemausuario',
    ]
    
    # Obtener content types de estos modelos
    content_types = ContentType.objects.filter(
        app_label='sistema',
        model__in=modelos_permitidos
    )
    
    # Obtener permisos
    permisos = Permission.objects.filter(
        content_type__in=content_types
    ).select_related('content_type').order_by('content_type__model', 'codename')
    
    # Agrupar por modelo con traducción
    permisos_agrupados = {}
    for p in permisos:
        modelo_key = p.content_type.model
        modelo_nombre = NOMBRES_MODELOS.get(modelo_key, modelo_key.title())
        
        if modelo_nombre not in permisos_agrupados:
            permisos_agrupados[modelo_nombre] = []
        
        # Traducir el nombre del permiso
        permiso_traducido = TRADUCCIONES_PERMISOS.get(p.codename, p.name)
        
        permisos_agrupados[modelo_nombre].append({
            'id': p.id,
            'codename': p.codename,
            'name': permiso_traducido,
        })
    
    return permisos_agrupados

def es_admin(user):
    """Verifica si el usuario es superusuario o staff"""
    return user.is_superuser or user.is_staff

@login_required
def admin_grupos(request):
    """Lista de grupos"""
    if not es_admin(request.user):
        messages.error(request, 'No tienes permisos para acceder.')
        return redirect('index')
    
    grupos = Group.objects.prefetch_related('permissions').all()
    
    return render(request, 'admin/grupos_lista.html', {
        'grupos': grupos,
    })
@login_required
def admin_grupo_eliminar(request, grupo_id):
    """Eliminar grupo"""
    if not es_admin(request.user):
        messages.error(request, 'No tienes permisos para acceder.')
        return redirect('index')
    
    grupo = get_object_or_404(Group, id=grupo_id)
    
    # Verificar si tiene usuarios asignados
    usuarios_count = grupo.user_set.count()
    if usuarios_count > 0:
        messages.error(request, f'No se puede eliminar el grupo. Tiene {usuarios_count} usuario(s) asignado(s).')
        return redirect('admin_grupos')
    
    nombre = grupo.name
    grupo.delete()
    messages.success(request, f'Grupo "{nombre}" eliminado exitosamente.')
    return redirect('admin_grupos')

@login_required
def admin_usuarios_sistema(request):
    """Lista de usuarios del sistema"""
    if not es_admin(request.user):
        messages.error(request, 'No tienes permisos para acceder.')
        return redirect('index')
    
    usuarios = User.objects.all().prefetch_related('groups', 'user_permissions')
    
    return render(request, 'admin/usuarios_lista.html', {
        'usuarios': usuarios,
    })

@login_required
def admin_usuario_eliminar(request, usuario_id):
    """Eliminar usuario del sistema"""
    if not es_admin(request.user):
        messages.error(request, 'No tienes permisos para acceder.')
        return redirect('index')
    
    usuario = get_object_or_404(User, id=usuario_id)
    
    if usuario == request.user:
        messages.error(request, 'No puedes eliminarte a ti mismo.')
        return redirect('admin_usuarios_sistema')
    
    if usuario.is_superuser:
        messages.error(request, 'No se puede eliminar un superusuario.')
        return redirect('admin_usuarios_sistema')
    
    username = usuario.username
    usuario.delete()
    messages.success(request, f'Usuario "{username}" eliminado exitosamente.')
    return redirect('admin_usuarios_sistema')

@login_required
def admin_grupo_crear(request):
    """Crear nuevo grupo"""
    if not es_admin(request.user):
        messages.error(request, 'No tienes permisos para acceder.')
        return redirect('index')
    
    permisos_agrupados = obtener_permisos_sistema()
    
    if request.method == 'POST':
        nombre = request.POST.get('nombre', '').strip()
        permisos_ids = request.POST.getlist('permisos')
        
        if not nombre:
            messages.error(request, 'El nombre del grupo es obligatorio.')
            return redirect('admin_grupo_crear')
        
        if Group.objects.filter(name=nombre).exists():
            messages.error(request, f'El grupo "{nombre}" ya existe.')
            return redirect('admin_grupo_crear')
        
        grupo = Group.objects.create(name=nombre)
        
        for permiso_id in permisos_ids:
            try:
                grupo.permissions.add(Permission.objects.get(id=permiso_id))
            except Permission.DoesNotExist:
                pass
        
        messages.success(request, f'Grupo "{nombre}" creado exitosamente.')
        return redirect('admin_grupos')
    
    return render(request, 'admin/grupo_form.html', {
        'permisos_agrupados': permisos_agrupados,
        'accion': 'Crear',
    })


@login_required
def admin_grupo_editar(request, grupo_id):
    """Editar grupo existente"""
    if not es_admin(request.user):
        messages.error(request, 'No tienes permisos para acceder.')
        return redirect('index')
    
    grupo = get_object_or_404(Group, id=grupo_id)
    
    permisos_agrupados = obtener_permisos_sistema()
    
    # IDs de permisos actuales
    permisos_actuales = list(grupo.permissions.values_list('id', flat=True))
    
    if request.method == 'POST':
        nombre = request.POST.get('nombre', '').strip()
        permisos_ids = request.POST.getlist('permisos')
        
        if not nombre:
            messages.error(request, 'El nombre del grupo es obligatorio.')
            return redirect('admin_grupo_editar', grupo_id=grupo.id)
        
        if Group.objects.filter(name=nombre).exclude(id=grupo.id).exists():
            messages.error(request, f'El grupo "{nombre}" ya existe.')
            return redirect('admin_grupo_editar', grupo_id=grupo.id)
        
        grupo.name = nombre
        grupo.save()
        
        grupo.permissions.clear()
        for permiso_id in permisos_ids:
            try:
                grupo.permissions.add(Permission.objects.get(id=permiso_id))
            except Permission.DoesNotExist:
                pass
        
        messages.success(request, f'Grupo "{nombre}" actualizado exitosamente.')
        return redirect('admin_grupos')
    
    return render(request, 'admin/grupo_form.html', {
        'grupo': grupo,
        'permisos_agrupados': permisos_agrupados,
        'permisos_actuales': permisos_actuales,
        'accion': 'Editar',
    })


@login_required
def admin_usuario_crear(request):
    """Crear usuario del sistema"""
    if not es_admin(request.user):
        messages.error(request, 'No tienes permisos para acceder.')
        return redirect('index')
    
    grupos = Group.objects.all()
    permisos_agrupados = obtener_permisos_sistema()
    
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        email = request.POST.get('email', '').strip()
        password = request.POST.get('password', '')
        first_name = request.POST.get('first_name', '').strip().upper()
        last_name = request.POST.get('last_name', '').strip().upper()
        is_staff = request.POST.get('is_staff') == 'on'
        is_active = request.POST.get('is_active') == 'on'
        grupos_ids = request.POST.getlist('grupos')
        permisos_ids = request.POST.getlist('permisos')
        
        if not username or not password:
            messages.error(request, 'Usuario y contraseña son obligatorios.')
            return redirect('admin_usuario_crear')
        
        if User.objects.filter(username=username).exists():
            messages.error(request, f'El usuario "{username}" ya existe.')
            return redirect('admin_usuario_crear')
        
        usuario = User.objects.create(
            username=username,
            email=email,
            password=make_password(password),
            first_name=first_name,
            last_name=last_name,
            is_staff=is_staff,
            is_active=is_active,
        )
        
        for grupo_id in grupos_ids:
            try:
                usuario.groups.add(Group.objects.get(id=grupo_id))
            except Group.DoesNotExist:
                pass
        
        for permiso_id in permisos_ids:
            try:
                usuario.user_permissions.add(Permission.objects.get(id=permiso_id))
            except Permission.DoesNotExist:
                pass
        
        messages.success(request, f'Usuario "{username}" creado exitosamente.')
        return redirect('admin_usuarios_sistema')
    
    return render(request, 'admin/usuario_form.html', {
        'grupos': grupos,
        'permisos_agrupados': permisos_agrupados,
        'accion': 'Crear',
    })


@login_required
def admin_usuario_editar(request, usuario_id):
    """Editar usuario existente"""
    if not es_admin(request.user):
        messages.error(request, 'No tienes permisos para acceder.')
        return redirect('index')
    
    usuario = get_object_or_404(User, id=usuario_id)
    
    grupos = Group.objects.all()
    permisos_agrupados = obtener_permisos_sistema()
    
    grupos_actuales = list(usuario.groups.values_list('id', flat=True))
    permisos_actuales = list(usuario.user_permissions.values_list('id', flat=True))
    
    if request.method == 'POST':
        email = request.POST.get('email', '').strip()
        first_name = request.POST.get('first_name', '').strip().upper()
        last_name = request.POST.get('last_name', '').strip().upper()
        is_staff = request.POST.get('is_staff') == 'on'
        is_active = request.POST.get('is_active') == 'on'
        new_password = request.POST.get('new_password', '')
        grupos_ids = request.POST.getlist('grupos')
        permisos_ids = request.POST.getlist('permisos')
        
        usuario.email = email
        usuario.first_name = first_name
        usuario.last_name = last_name
        usuario.is_staff = is_staff
        usuario.is_active = is_active
        
        if new_password:
            usuario.password = make_password(new_password)
        
        usuario.save()
        
        usuario.groups.clear()
        for grupo_id in grupos_ids:
            try:
                usuario.groups.add(Group.objects.get(id=grupo_id))
            except Group.DoesNotExist:
                pass
        
        usuario.user_permissions.clear()
        for permiso_id in permisos_ids:
            try:
                usuario.user_permissions.add(Permission.objects.get(id=permiso_id))
            except Permission.DoesNotExist:
                pass
        
        messages.success(request, f'Usuario "{usuario.username}" actualizado exitosamente.')
        return redirect('admin_usuarios_sistema')
    
    return render(request, 'admin/usuario_form.html', {
        'usuario': usuario,
        'grupos': grupos,
        'permisos_agrupados': permisos_agrupados,
        'grupos_actuales': grupos_actuales,
        'permisos_actuales': permisos_actuales,
        'accion': 'Editar',
    })


# sistema/views.py

from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth import get_user_model

User = get_user_model()


class AppMovilTokenObtainPairView(TokenObtainPairView):
    """
    Login personalizado para la app móvil.
    Rechaza si el usuario no es Operador o Superuser.
    """
    
    def post(self, request, *args, **kwargs):
        username = request.data.get('username')
        
        # Verificar si el usuario existe
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            return Response(
                {'detail': 'Credenciales inválidas.'},
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        # Verificar si está activo
        if not user.is_active:
            return Response(
                {'detail': 'Usuario inactivo. Contacte al administrador.'},
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        # Verificar si es Operador o Superuser
        es_operador = user.groups.filter(name='Operador').exists()
        es_superuser = user.is_superuser
        
        if not (es_operador or es_superuser):
            return Response(
                {
                    'detail': 'No tienes permisos para usar la aplicación móvil.',
                    'error_code': 'NOT_OPERATOR'
                },
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Si pasa las validaciones, obtener el token
        return super().post(request, *args, **kwargs)