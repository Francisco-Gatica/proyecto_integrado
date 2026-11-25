import datetime
import re
import requests
from django.conf import settings


def normalizar_telefono(telefono):
    """
    Limpia un número telefónico dejándolo en formato numérico internacional (sin '+' ni espacios).
    """
    if not telefono:
        raise ValueError("El número de teléfono es obligatorio.")
    digitos = re.sub(r"\D", "", str(telefono))
    if len(digitos) < 8:
        raise ValueError(
            "El número de teléfono debe incluir código de país y tener al menos 8 dígitos (ej: 56912345678)."
        )
    return digitos


def _construir_resultado(ok, status_code=None, message_id=None, data=None, error=None, payload=None):
    return {
        "ok": ok,
        "status_code": status_code,
        "message_id": message_id,
        "data": data,
        "error": error,
        "payload": payload,
    }


def _enviar_payload_whatsapp(payload, dry_run=False):
    """
    Envía un payload a la WhatsApp Cloud API de Meta y retorna un diccionario estandarizado.
    """
    if dry_run:
        return _construir_resultado(ok=True, status_code=None, message_id="dry-run", payload=payload)

    token = getattr(settings, "WHATSAPP_TOKEN", None)
    phone_id = getattr(settings, "WHATSAPP_PHONE_ID", None)
    api_version = getattr(settings, "WHATSAPP_API_VERSION", "v21.0") or "v21.0"

    if not token or not phone_id:
        return _construir_resultado(
            ok=False,
            error="Faltan las credenciales WHATSAPP_TOKEN o WHATSAPP_PHONE_ID en la configuración (.env).",
            payload=payload,
        )

    url = f"https://graph.facebook.com/{api_version}/{phone_id}/messages"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=15)
    except requests.RequestException as exc:
        return _construir_resultado(
            ok=False,
            error=f"Error de conexión con WhatsApp API: {exc}",
            payload=payload,
        )

    try:
        data = response.json()
    except ValueError:
        data = {"raw": response.text}

    if response.ok:
        mensajes = data.get("messages") if isinstance(data, dict) else None
        message_id = mensajes[0].get("id") if mensajes and isinstance(mensajes[0], dict) else None
        return _construir_resultado(
            ok=True,
            status_code=response.status_code,
            message_id=message_id,
            data=data,
            payload=payload,
        )

    error_info = data.get("error", {}) if isinstance(data, dict) else {}
    error_msg = error_info.get("message") or f"Error HTTP {response.status_code} desde WhatsApp API."
    if error_info.get("code"):
        error_msg = f"[{error_info['code']}] {error_msg}"

    return _construir_resultado(
        ok=False,
        status_code=response.status_code,
        data=data,
        error=error_msg,
        payload=payload,
    )


def enviar_mensaje_plantilla(
    telefono,
    nombre_plantilla=None,
    codigo_idioma=None,
    parametros=None,
    dry_run=False,
):
    """
    Envía un mensaje usando una plantilla aprobada en WhatsApp Cloud API.
    Por defecto utiliza la plantilla de prueba 'hello_world' (en_US).
    """
    try:
        telefono_limpio = normalizar_telefono(telefono)
    except ValueError as exc:
        return _construir_resultado(ok=False, error=str(exc))

    plantilla = nombre_plantilla or getattr(settings, "WHATSAPP_TEST_TEMPLATE", "hello_world") or "hello_world"
    idioma = codigo_idioma or getattr(settings, "WHATSAPP_TEST_LANGUAGE", "en_US") or "en_US"

    template_obj = {
        "name": plantilla,
        "language": {"code": idioma},
    }
    if parametros:
        template_obj["components"] = [
            {
                "type": "body",
                "parameters": [{"type": "text", "text": str(p)} for p in parametros],
            }
        ]

    payload = {
        "messaging_product": "whatsapp",
        "to": telefono_limpio,
        "type": "template",
        "template": template_obj,
    }
    return _enviar_payload_whatsapp(payload, dry_run=dry_run)


def enviar_mensaje_texto(telefono, cuerpo_mensaje, dry_run=False):
    """
    Envía un mensaje de texto libre mediante WhatsApp Cloud API.
    Requiere que el destinatario haya iniciado una conversación en las últimas 24 horas.
    """
    try:
        telefono_limpio = normalizar_telefono(telefono)
    except ValueError as exc:
        return _construir_resultado(ok=False, error=str(exc))

    texto = (cuerpo_mensaje or "").strip()
    if not texto:
        return _construir_resultado(ok=False, error="El cuerpo del mensaje de texto no puede estar vacío.")

    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": telefono_limpio,
        "type": "text",
        "text": {
            "preview_url": False,
            "body": texto,
        },
    }
    return _enviar_payload_whatsapp(payload, dry_run=dry_run)


def enviar_recordatorio_whatsapp(telefono_paciente, nombre_paciente, fecha_cita, hora_cita=None, dry_run=False):
    """
    Envía un recordatorio de cita dental al paciente.
    Usa WHATSAPP_REMINDER_TEMPLATE si está configurada; de lo contrario envía un mensaje de texto.
    """
    plantilla_recordatorio = getattr(settings, "WHATSAPP_REMINDER_TEMPLATE", "")
    idioma_recordatorio = getattr(settings, "WHATSAPP_REMINDER_LANGUAGE", "es") or "es"
    nombre = nombre_paciente or "Paciente"
    fecha_str = fecha_cita.strftime("%d/%m/%Y") if hasattr(fecha_cita, "strftime") else str(fecha_cita)

    if plantilla_recordatorio:
        parametros = [nombre, fecha_str]
        if hora_cita:
            hora_str = hora_cita.strftime("%H:%M") if hasattr(hora_cita, "strftime") else str(hora_cita)
            parametros.append(hora_str)
        return enviar_mensaje_plantilla(
            telefono=telefono_paciente,
            nombre_plantilla=plantilla_recordatorio,
            codigo_idioma=idioma_recordatorio,
            parametros=parametros,
            dry_run=dry_run,
        )

    hora_texto = ""
    if hora_cita:
        hora_str = hora_cita.strftime("%H:%M") if hasattr(hora_cita, "strftime") else str(hora_cita)
        hora_texto = f" a las {hora_str}"

    cuerpo = (
        f"Hola {nombre}, le recordamos su cita dental en Clínica Dr. Hebel "
        f"para el día {fecha_str}{hora_texto}."
    )
    return enviar_mensaje_texto(telefono_paciente, cuerpo, dry_run=dry_run)


def mensaje_prueba(
    telefono_paciente,
    nombre_paciente="Paciente de Prueba",
    fecha_cita=None,
    modo="plantilla",
    mensaje=None,
    dry_run=False,
):
    """
    Genera y envía un mensaje de prueba para comprobar que la integración con WhatsApp funciona.
    - modo='plantilla': envía la plantilla de prueba de Meta (por defecto 'hello_world').
    - modo='texto': envía un mensaje de texto personalizado de prueba.
    """
    if modo == "texto":
        fecha_ref = fecha_cita or datetime.date.today().strftime("%d/%m/%Y")
        if hasattr(fecha_ref, "strftime"):
            fecha_ref = fecha_ref.strftime("%d/%m/%Y")
        cuerpo = (mensaje or "").strip() or (
            f"Mensaje de prueba - Clínica Dental Dr. Hebel. "
            f"Hola {nombre_paciente}, la integración con WhatsApp API está funcionando correctamente "
            f"(fecha de referencia: {fecha_ref})."
        )
        return enviar_mensaje_texto(telefono_paciente, cuerpo, dry_run=dry_run)

    return enviar_mensaje_plantilla(telefono_paciente, dry_run=dry_run)
