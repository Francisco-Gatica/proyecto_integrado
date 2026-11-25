import datetime
from functools import wraps
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from django.core.exceptions import PermissionDenied
from django.db.models import Max, Q
from django.shortcuts import (
    render,
    redirect,
    get_object_or_404
)
from .models import AsistenteDental, Calendario, CitaMedica, Doctor, Paciente
from .services import enviar_recordatorio_whatsapp, mensaje_prueba
from .validators import formatear_telefono_cl, parsear_fecha, validar_rut

def _obtener_siguiente_id(modelo, campo_pk):
    """
    Obtiene el siguiente ID entero para el modelo en caso de claves primarias no autoincrementales.
    """
    max_id = modelo.objects.aggregate(Max(campo_pk))[f'{campo_pk}__max']
    return (max_id or 0) + 1

# Bloques horarios de atención clínica (09:00 - 13:00 y 15:00 - 20:00)
SLOTS_HORARIOS = [
    # Mañana: 09:00 a 13:00
    {'hora_str': '09:00 - 10:00', 'inicio': datetime.time(9, 0), 'fin': datetime.time(10, 0)},
    {'hora_str': '10:00 - 11:00', 'inicio': datetime.time(10, 0), 'fin': datetime.time(11, 0)},
    {'hora_str': '11:00 - 12:00', 'inicio': datetime.time(11, 0), 'fin': datetime.time(12, 0)},
    {'hora_str': '12:00 - 13:00', 'inicio': datetime.time(12, 0), 'fin': datetime.time(13, 0)},
    # Tarde: 15:00 a 20:00
    {'hora_str': '15:00 - 16:00', 'inicio': datetime.time(15, 0), 'fin': datetime.time(16, 0)},
    {'hora_str': '16:00 - 17:00', 'inicio': datetime.time(16, 0), 'fin': datetime.time(17, 0)},
    {'hora_str': '17:00 - 18:00', 'inicio': datetime.time(17, 0), 'fin': datetime.time(18, 0)},
    {'hora_str': '18:00 - 19:00', 'inicio': datetime.time(18, 0), 'fin': datetime.time(19, 0)},
    {'hora_str': '19:00 - 20:00', 'inicio': datetime.time(19, 0), 'fin': datetime.time(20, 0)},
]

def login_view(request):
    """
    Vista de inicio de sesión.
    Si el usuario ya está autenticado, lo redirige al inicio.
    """
    if request.user.is_authenticated:
        return redirect('index')
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            nombre_usuario = user.get_full_name() or user.username
            messages.success(request, f'¡Bienvenido(a), {nombre_usuario}!')
            next_url = request.POST.get('next') or request.GET.get('next')
            if next_url and next_url != '':
                return redirect(next_url)
            return redirect('index')
        else:
            messages.error(request, 'Usuario o contraseña incorrectos. Por favor, intenta nuevamente.')
    else:
        form = AuthenticationForm()
    next_url = request.GET.get('next', '')
    return render(request, 'login.html', {'form': form, 'next': next_url})

def logout_view(request):
    """
    Vista para cerrar sesión.
    """
    logout(request)
    messages.info(request, 'Has cerrado sesión exitosamente.')
    return redirect('login')

@login_required(login_url='login')
def index(request):
    """
    Página principal / Calendario semanal de atención.
    Permite visualizar, crear, modificar y eliminar citas médicas.
    """
    fecha_param = request.GET.get('fecha')
    try:
        fecha_ref = parsear_fecha(fecha_param) or datetime.date.today()
    except ValueError:
        fecha_ref = datetime.date.today()

    # Calcular lunes y viernes de la semana actual/seleccionada
    lunes = fecha_ref - datetime.timedelta(days=fecha_ref.weekday())
    viernes = lunes + datetime.timedelta(days=4)

    semana_anterior = (lunes - datetime.timedelta(days=7)).strftime('%d/%m/%Y')
    semana_siguiente = (lunes + datetime.timedelta(days=7)).strftime('%d/%m/%Y')
    hoy_str = datetime.date.today().strftime('%d/%m/%Y')

    # Citas médicas de la semana (Lunes a Viernes)
    citas_semana = list(
        CitaMedica.objects.filter(fecha__range=[lunes, viernes])
        .select_related('id_doctor__id_usuario')
        .prefetch_related('paciente_set')
    )
    for c in citas_semana:
        c.paciente = c.paciente_set.first()
    nombres_dias = ['LUNES', 'MARTES', 'MIERCOLES', 'JUEVES', 'VIERNES']
    dias_semana = []
    for i in range(5):
        dia_fecha = lunes + datetime.timedelta(days=i)
        slots_dia = []
        citas_asignadas = set()

        for slot in SLOTS_HORARIOS:
            citas_bloque = []
            for c in citas_semana:
                if c.fecha == dia_fecha and c.hora_inicio:
                    if slot['inicio'] <= c.hora_inicio < slot['fin'] or (c.hora_inicio.hour == slot['inicio'].hour):
                        citas_bloque.append(c)
                        citas_asignadas.add(c.id_cita)
            slots_dia.append({
                'slot': slot,
                'citas': citas_bloque
            })
        # Citas fuera de rango estándar para ese día
        citas_extra = [c for c in citas_semana if c.fecha == dia_fecha and c.id_cita not in citas_asignadas]
        if citas_extra and slots_dia:
            slots_dia[-1]['citas'].extend(citas_extra)
        dias_semana.append({
            'nombre': nombres_dias[i],
            'fecha': dia_fecha,
            'fecha_str': dia_fecha.strftime('%d/%m/%Y'),
            'fecha_iso': dia_fecha.isoformat(),
            'slots': slots_dia,
        })
    pacientes = Paciente.objects.all().order_by('nombre', 'primer_apellido')
    doctores = Doctor.objects.all().select_related('id_usuario')
    # Nombre amigable del rango de fechas
    meses_es = ['', 'Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio', 'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre']
    rango_semana_str = f"Semana del {lunes.day} al {viernes.day} de {meses_es[lunes.month]} {lunes.year}"
    if lunes.month != viernes.month:
        rango_semana_str = f"Semana del {lunes.day} de {meses_es[lunes.month]} al {viernes.day} de {meses_es[viernes.month]} {lunes.year}"
    context = {
        'dias_semana': dias_semana,
        'slots_horarios': SLOTS_HORARIOS,
        'lunes': lunes,
        'viernes': viernes,
        'semana_anterior': semana_anterior,
        'semana_siguiente': semana_siguiente,
        'hoy_str': hoy_str,
        'hoy_iso': hoy_str,
        'fecha_seleccionada': fecha_ref.strftime('%d/%m/%Y'),
        'rango_semana_str': rango_semana_str,
        'pacientes': pacientes,
        'doctores': doctores,
        'total_citas_semana': len(citas_semana),
    }
    return render(request, 'index.html', context)

@login_required(login_url='login')
def main(request):
    """
    Redirige a la página principal.
    """
    return redirect('index')

@login_required(login_url='login')
def cita_crear(request):
    """
    Crea una nueva cita médica y la asocia al paciente y doctor seleccionados.
    """
    if request.method == 'POST':
        fecha_str = request.POST.get('fecha')
        hora_inicio_str = request.POST.get('hora_inicio')
        hora_fin_str = request.POST.get('hora_fin')
        motivo = request.POST.get('motivo_consulta', '').strip()
        estado = request.POST.get('estado', 'Pendiente')
        doctor_id = request.POST.get('id_doctor')
        tipo_paciente = request.POST.get('tipo_paciente', 'existente')
        paciente_id = request.POST.get('id_paciente')

        if not fecha_str or not hora_inicio_str:
            messages.error(request, 'La fecha y la hora de inicio son requeridas.')
            return redirect('index')
        try:
            fecha_val = parsear_fecha(fecha_str, obligatorio=True)
            hora_inicio_val = datetime.time.fromisoformat(hora_inicio_str)
            if hora_fin_str:
                hora_fin_val = datetime.time.fromisoformat(hora_fin_str)
            else:
                hora_fin_val = (datetime.datetime.combine(fecha_val, hora_inicio_val) + datetime.timedelta(hours=1)).time()
        except ValueError as exc:
            messages.error(request, str(exc) if 'fecha' in str(exc).lower() else 'Formato de fecha u hora no válido (use DD/MM/YYYY).')
            return redirect('index')

        # Validar datos de paciente nuevo antes de guardar la cita
        datos_nuevo_paciente = None
        if tipo_paciente == 'nuevo':
            nombre = request.POST.get('nombre_paciente', '').strip()
            primer_apellido = request.POST.get('primer_apellido_paciente', '').strip()
            segundo_apellido = request.POST.get('segundo_apellido_paciente', '').strip()
            rut_raw = request.POST.get('rut_paciente', '').strip()
            telefono_raw = request.POST.get('telefono_paciente', '').strip()
            correo = request.POST.get('correo_paciente', '').strip()
            fecha_nacimiento_str = request.POST.get('fecha_nacimiento_paciente', '').strip()
            try:
                rut = validar_rut(rut_raw)
                telefono = formatear_telefono_cl(telefono_raw)
                fecha_nacimiento = parsear_fecha(fecha_nacimiento_str)
            except ValueError as exc:
                messages.error(request, str(exc))
                return redirect('index')
            datos_nuevo_paciente = {
                'nombre': nombre,
                'primer_apellido': primer_apellido,
                'segundo_apellido': segundo_apellido,
                'rut': rut,
                'telefono': telefono,
                'correo': correo,
                'fecha_nacimiento': fecha_nacimiento,
            }

        doctor = None
        if doctor_id:
            doctor = Doctor.objects.filter(id_doctor=doctor_id).first()
        nueva_cita = CitaMedica(
            id_cita=_obtener_siguiente_id(CitaMedica, 'id_cita'),
            fecha=fecha_val,
            hora_inicio=hora_inicio_val,
            hora_fin=hora_fin_val,
            motivo_consulta=motivo,
            estado=estado,
            id_doctor=doctor
        )
        nueva_cita.save()
        # Vincular o crear paciente
        paciente_vinculado = None
        if tipo_paciente == 'nuevo' and datos_nuevo_paciente:
            nombre = datos_nuevo_paciente['nombre']
            primer_apellido = datos_nuevo_paciente['primer_apellido']
            segundo_apellido = datos_nuevo_paciente['segundo_apellido']
            rut = datos_nuevo_paciente['rut']
            telefono = datos_nuevo_paciente['telefono']
            correo = datos_nuevo_paciente['correo']
            fecha_nacimiento = datos_nuevo_paciente['fecha_nacimiento']
            if nombre and primer_apellido:
                paciente_existente = None
                if rut:
                    paciente_existente = Paciente.objects.filter(rut=rut).first()
                if paciente_existente:
                    paciente_existente.id_cita = nueva_cita
                    if fecha_nacimiento and not paciente_existente.fecha_nacimiento:
                        paciente_existente.fecha_nacimiento = fecha_nacimiento
                    if telefono and not paciente_existente.telefono:
                        paciente_existente.telefono = telefono
                    paciente_existente.save()
                    paciente_vinculado = paciente_existente
                else:
                    nuevo_p = Paciente(
                        id_paciente=_obtener_siguiente_id(Paciente, 'id_paciente'),
                        rut=rut,
                        nombre=nombre,
                        primer_apellido=primer_apellido,
                        segundo_apellido=segundo_apellido,
                        telefono=telefono,
                        correo=correo if correo else None,
                        fecha_nacimiento=fecha_nacimiento,
                        id_cita=nueva_cita,
                        activo=True
                    )
                    nuevo_p.save()
                    paciente_vinculado = nuevo_p
        elif paciente_id:
            paciente = Paciente.objects.filter(id_paciente=paciente_id).first()
            if paciente:
                paciente.id_cita = nueva_cita
                paciente.save()
                paciente_vinculado = paciente
        # Notificar por WhatsApp al número del paciente al agendar una nueva cita
        if nueva_cita.estado != 'Cancelada' and paciente_vinculado and paciente_vinculado.telefono:
            resultado_ws = enviar_recordatorio_whatsapp(
                telefono_paciente=paciente_vinculado.telefono,
                nombre_paciente=paciente_vinculado.nombre,
                fecha_cita=nueva_cita.fecha,
                hora_cita=nueva_cita.hora_inicio,
            )
            if resultado_ws.get('ok'):
                messages.info(request, f'Mensaje de WhatsApp enviado a {paciente_vinculado.telefono}.')
            else:
                messages.warning(
                    request,
                    f"No se pudo enviar el WhatsApp al paciente: {resultado_ws.get('error')}",
                )
        # Registro en Calendario si aplica
        try:
            meses_nombres = ['', 'Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio', 'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre']
            Calendario.objects.create(
                id_calendario=_obtener_siguiente_id(Calendario, 'id_calendario'),
                id_cita=nueva_cita,
                ano=nueva_cita.fecha.year,
                numero_mes=nueva_cita.fecha.month,
                nombre_mes=meses_nombres[nueva_cita.fecha.month]
            )
        except Exception:
            pass
        messages.success(request, f'Cita médica agendada correctamente para el {nueva_cita.fecha.strftime("%d/%m/%Y")} a las {nueva_cita.hora_inicio.strftime("%H:%M")}.')
        return redirect(f"{redirect('index').url}?fecha={nueva_cita.fecha.strftime('%d/%m/%Y')}")
    return redirect('index')

@login_required(login_url='login')
def cita_editar(request, id_cita):
    """
    Modifica los datos de una cita médica existente.
    """
    cita = get_object_or_404(CitaMedica, id_cita=id_cita)
    if request.method == 'POST':
        fecha_str = request.POST.get('fecha')
        hora_inicio_str = request.POST.get('hora_inicio')
        hora_fin_str = request.POST.get('hora_fin')
        motivo = request.POST.get('motivo_consulta', '').strip()
        estado = request.POST.get('estado', 'Pendiente')
        doctor_id = request.POST.get('id_doctor')
        paciente_id = request.POST.get('id_paciente')
        try:
            if fecha_str:
                cita.fecha = parsear_fecha(fecha_str, obligatorio=True)
            if hora_inicio_str:
                cita.hora_inicio = datetime.time.fromisoformat(hora_inicio_str)
            if hora_fin_str:
                cita.hora_fin = datetime.time.fromisoformat(hora_fin_str)
        except ValueError as exc:
            messages.error(request, str(exc))
            return redirect('index')
        cita.motivo_consulta = motivo
        cita.estado = estado
        if doctor_id:
            cita.id_doctor = Doctor.objects.filter(id_doctor=doctor_id).first()
        else:
            cita.id_doctor = None
        cita.save()
        if paciente_id:
            Paciente.objects.filter(id_cita=cita).exclude(id_paciente=paciente_id).update(id_cita=None)
            paciente = Paciente.objects.filter(id_paciente=paciente_id).first()
            if paciente:
                paciente.id_cita = cita
                paciente.save()
        messages.success(request, 'Cita médica modificada exitosamente.')
        return redirect(f"{redirect('index').url}?fecha={cita.fecha.strftime('%d/%m/%Y')}")
    return redirect('index')

@login_required(login_url='login')
def cita_eliminar(request, id_cita):
    """
    Elimina una cita médica y desvincula al paciente.
    """
    cita = get_object_or_404(CitaMedica, id_cita=id_cita)
    fecha_str = cita.fecha.strftime('%d/%m/%Y') if cita.fecha else ''
    if request.method == 'POST':
        Paciente.objects.filter(id_cita=cita).update(id_cita=None)
        Calendario.objects.filter(id_cita=cita).delete()
        cita.delete()
        messages.success(request, 'Cita médica eliminada correctamente.')
        if fecha_str:
            return redirect(f"{redirect('index').url}?fecha={fecha_str}")
    return redirect('index')

@login_required(login_url='login')
def paciente_crear(request):
    """
    Crea un nuevo paciente en la clínica.
    """
    if request.method == 'POST':
        nombre = request.POST.get('nombre', '').strip()
        primer_apellido = request.POST.get('primer_apellido', '').strip()
        segundo_apellido = request.POST.get('segundo_apellido', '').strip()
        rut_raw = request.POST.get('rut', '').strip()
        telefono_raw = request.POST.get('telefono', '').strip()
        correo = request.POST.get('correo', '').strip()
        fecha_nacimiento_str = request.POST.get('fecha_nacimiento', '').strip()

        referer = request.META.get('HTTP_REFERER')
        redirect_target = 'pacientes' if (referer and 'pacientes' in referer) else 'index'

        if not nombre or not primer_apellido:
            messages.error(request, 'El nombre y primer apellido son obligatorios.')
            return redirect(redirect_target)
        if not fecha_nacimiento_str:
            messages.error(request, 'La fecha de nacimiento es obligatoria.')
            return redirect(redirect_target)

        try:
            fecha_nacimiento = parsear_fecha(fecha_nacimiento_str, obligatorio=True)
            rut = validar_rut(rut_raw)
            telefono = formatear_telefono_cl(telefono_raw)
        except ValueError as exc:
            messages.error(request, str(exc))
            return redirect(redirect_target)

        if rut and Paciente.objects.filter(rut=rut).exists():
            messages.error(request, f'Ya existe un paciente con el RUT {rut}.')
            return redirect(redirect_target)
        paciente = Paciente(
            id_paciente=_obtener_siguiente_id(Paciente, 'id_paciente'),
            rut=rut,
            nombre=nombre,
            primer_apellido=primer_apellido,
            segundo_apellido=segundo_apellido,
            telefono=telefono,
            correo=correo if correo else None,
            fecha_nacimiento=fecha_nacimiento,
            activo=True
        )
        paciente.save()
        messages.success(request, f'Paciente {nombre} {primer_apellido} registrado con éxito.')
        return redirect(redirect_target)
    return redirect('index')

@login_required(login_url='login')
def pacientes_view(request):
    """
    Directorio de pacientes de la clínica.
    """
    query = request.GET.get('q', '').strip()
    if query:
        pacientes = Paciente.objects.filter(
            Q(nombre__icontains=query) |
            Q(primer_apellido__icontains=query) |
            Q(segundo_apellido__icontains=query) |
            Q(rut__icontains=query)
        ).order_by('nombre')
    else:
        pacientes = Paciente.objects.all().order_by('nombre', 'primer_apellido')
    return render(request, 'clinica/pacientes.html', {'pacientes': pacientes, 'query': query})

@login_required(login_url='login')
def paciente_editar(request, id_paciente):
    """
    Modifica los datos de un paciente existente.
    """
    paciente = get_object_or_404(Paciente, id_paciente=id_paciente)
    if request.method == 'POST':
        nombre = request.POST.get('nombre', '').strip()
        primer_apellido = request.POST.get('primer_apellido', '').strip()
        segundo_apellido = request.POST.get('segundo_apellido', '').strip()
        rut_raw = request.POST.get('rut', '').strip()
        telefono_raw = request.POST.get('telefono', '').strip()
        correo = request.POST.get('correo', '').strip()
        fecha_nacimiento_str = request.POST.get('fecha_nacimiento', '').strip()
        activo_str = request.POST.get('activo')
        if not nombre or not primer_apellido:
            messages.error(request, 'El nombre y primer apellido son obligatorios.')
            return redirect('pacientes')
        if not fecha_nacimiento_str:
            messages.error(request, 'La fecha de nacimiento es obligatoria.')
            return redirect('pacientes')
        try:
            fecha_nacimiento = parsear_fecha(fecha_nacimiento_str, obligatorio=True)
            rut = validar_rut(rut_raw)
            telefono = formatear_telefono_cl(telefono_raw)
        except ValueError as exc:
            messages.error(request, str(exc))
            return redirect('pacientes')
        # Verificar si el RUT ya está en uso por otro paciente
        if rut and Paciente.objects.filter(rut=rut).exclude(id_paciente=id_paciente).exists():
            messages.error(request, f'Ya existe otro paciente con el RUT {rut}.')
            return redirect('pacientes')
        paciente.nombre = nombre
        paciente.primer_apellido = primer_apellido
        paciente.segundo_apellido = segundo_apellido
        paciente.rut = rut
        paciente.telefono = telefono
        paciente.correo = correo if correo else None
        paciente.fecha_nacimiento = fecha_nacimiento
        if activo_str is not None:
            paciente.activo = activo_str in ['true', '1', 'True', True, 'on']
        paciente.save()
        messages.success(request, f'Datos del paciente {paciente.nombre} {paciente.primer_apellido} actualizados correctamente.')
        return redirect('pacientes')
    return redirect('pacientes')
# Alias para compatibilidad
pacientes_modify = paciente_editar


@login_required(login_url='login')
def whatsapp_prueba(request):
    """
    Envía un mensaje de prueba vía WhatsApp Cloud API para verificar la integración.
    """
    if request.method == 'POST':
        telefono = request.POST.get('telefono', '').strip()
        modo = request.POST.get('modo', 'plantilla').strip()
        nombre_paciente = request.POST.get('nombre_paciente', '').strip() or 'Paciente de Prueba'
        mensaje = request.POST.get('mensaje', '').strip() or None

        if modo not in ('plantilla', 'texto'):
            modo = 'plantilla'

        resultado = mensaje_prueba(
            telefono_paciente=telefono,
            nombre_paciente=nombre_paciente,
            modo=modo,
            mensaje=mensaje,
        )

        if resultado['ok']:
            msg_id = resultado.get('message_id') or 'enviado'
            messages.success(
                request,
                f'Mensaje de prueba de WhatsApp enviado exitosamente a {telefono} (ID: {msg_id}).',
            )
        else:
            messages.error(
                request,
                f"No se pudo enviar el mensaje de prueba de WhatsApp: {resultado.get('error')}",
            )
    return redirect('index')
