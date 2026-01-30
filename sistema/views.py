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
# Create your views here.
@login_required
def index(request):
    lecturas = SistemaLectura.objects.all()
    sectores = SistemaSector.objects.all()
    consumo_sector = (lecturas
                      .values('usuario__sector__nombre')
                      .annotate(total=Sum('consumo'))
                      .order_by('-total')[:5])

    recaudos = SistemaTarifa.objects.all()
    recaudos_sector = (SistemaPago.objects
                       .values('usuario__sector__nombre')
                       .annotate(total=Sum('monto'))
                       .order_by('-total')[:5])

    usuarios_total = SistemaUsuario.objects.count()
    top_consumidores = (lecturas
                        .values('usuario__apellido_paterno', 'usuario__nombres')
                        .annotate(total=Sum('consumo'))
                        .order_by('-total')[:5])
    eventos = SistemaEvento.objects.all()

    # --- Consumo mensual (por fecha de lectura; si no hay DateField, usa anio/mes) ---
    # Si tu modelo solo tiene anio/mes, haz el agregado manual:
    consumo_mensual = (lecturas
                       .values('anio', 'mes')
                       .annotate(total=Sum('consumo'))
                       .order_by('anio', 'mes'))

    pagos_mensuales = (SistemaPago.objects
                       .values('lectura__anio', 'lectura__mes')
                       .annotate(total=Sum('monto'))
                       .order_by('lectura__anio', 'lectura__mes'))

    # Normalizar a una misma lista de labels
    labels = []
    consumo_data = []
    recaudo_data = []

    # Convertir pagos_mensuales en dict para fácil acceso
    pagos_dict = {
        (p['lectura__anio'], p['lectura__mes']): p['total']
        for p in pagos_mensuales
    }

    for row in consumo_mensual:
        anio = row['anio']
        mes = row['mes']
        labels.append(f"{mes:02d}/{anio}")
        total_consumo = row['total'] or 0
        consumo_data.append(float(total_consumo))

        total_recaudo = pagos_dict.get((anio, mes), 0) or 0
        recaudo_data.append(float(total_recaudo))

    chart_data = {
        "labels": labels,
        "series": [
            {"name": "Consumo (m³)", "data": consumo_data},
            {"name": "Recaudado ($)", "data": recaudo_data},
        ],
    }

    return render(request, 'index.html', {
        'sectores': sectores,
        'lecturas': lecturas,
        'consumo_sector': consumo_sector,
        'recaudos': recaudos,
        'usuarios_total': usuarios_total,
        'recaudos_sector': recaudos_sector,
        'top_consumidores': top_consumidores,
        'eventos': eventos,
        'chart_data_json': json.dumps(chart_data),
    })
    
# =============Medidores============
@login_required
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
def new_medidor(request):
    usuarios = SistemaUsuario.objects.all()
    return render(request, 'medidores/new_medidor.html', {
        'usuarios': usuarios
    })


@login_required
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
def edit_medidor(request, id):
    medidor = get_object_or_404(SistemaMedidor, id=id)
    usuarios = SistemaUsuario.objects.all()
    return render(request, 'medidores/edit_medidor.html', {
        'medidor': medidor,
        'usuarios': usuarios
    })


@login_required
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
def list_meses_lecturas(request):    
    meses = (SistemaLectura.objects
             .values('anio', 'mes')
             .order_by('anio', 'mes')
             .distinct())

    return render(request, 'lecturas/list_sec_lec.html', {
        'meses': meses,
    })
    
@login_required
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
def list_pag_usuarios(request):
    usuarios = SistemaUsuario.objects.all()
    sectores = SistemaSector.objects.all()
    return render(request, 'pagos/list_pag_usuarios.html', {'usuarios': usuarios, 'sectores': sectores})

@login_required
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
@login_required
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

    for usuario in usuarios_qs:
        lecturas_qs = SistemaLectura.objects.filter(usuario=usuario, anio=anio)
        if mes:
            lecturas_qs = lecturas_qs.filter(mes=int(mes))

        # si manejas una lectura por mes/medidor, aquí puedes decidir:
        lectura = lecturas_qs.first()

        if lectura:
            pago = SistemaPago.objects.filter(lectura=lectura, usuario=usuario).first()
        else:
            pago = None

        pagado = bool(pago and pago.estado)

        # filtro por estado (pagado/pendiente)
        if estado == "pagado" and not pagado:
            continue
        if estado == "pendiente" and pagado:
            continue

        filas.append({
            "anio": anio,
            "mes": int(mes) if mes else "",
            "usuario": usuario,
            "sector": usuario.sector,
            "lectura_actual": lectura.consumo if lectura else None,
            "consumo": lectura.consumo if lectura else None,  # o calcula diferencia con mes anterior
            "pagado": pagado,
            "monto": pago.monto if pago else None,
            "fecha_pago": pago.fecha_pago if pago else None,
        })

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
        "estado": estado,
        "lista_anios": lista_anios,
        "lista_meses": lista_meses,
        "sectores": sectores,
    }
    return render(request, "reportes/reporte_pagos.html", context)

@login_required
def reporte_lecturas(request):
    hoy = date.today()

    anio = int(request.GET.get("anio", hoy.year))
    mes = request.GET.get("mes")          # "" o "1".."12"
    sector_id = request.GET.get("sector", "")

    usuarios_qs = (
        SistemaUsuario.objects
        .select_related("sector")
        .order_by("sector__nombre", "apellido_paterno", "apellido_materno", "nombres")
    )

    if sector_id:
        usuarios_qs = usuarios_qs.filter(sector_id=sector_id)

    filas = []

    for usuario in usuarios_qs:
        if mes:
            lecturas_qs = SistemaLectura.objects.filter(
                usuario=usuario,
                anio=anio,
                mes=int(mes)
            )
        else:
            lecturas_qs = SistemaLectura.objects.filter(
                usuario=usuario,
                anio=anio,
            )

        # si quieres solo una fila por usuario (p.ej. mes concreto):
        lectura = lecturas_qs.first()

        filas.append({
            "usuario": usuario,
            "lectura": lectura,
        })

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
    }
    return render(request, "reportes/reporte_lecturas.html", context)


# =============Descargar APK============
import os
from django.conf import settings
from django.http import FileResponse, Http404
@login_required
def descargar_apk(request):
    apk_path = os.path.join(settings.MEDIA_ROOT, 'apk', 'app-debug.apk')
    if not os.path.exists(apk_path):
        raise Http404("Archivo APK no encontrado.")

    return FileResponse(
        open(apk_path, 'rb'),
        as_attachment=True,
        filename='jaap-app.apk',
        content_type='application/vnd.android.package-archive',
    )

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
