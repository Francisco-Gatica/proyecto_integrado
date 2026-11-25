import logging
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import CitaMedica
from .services import enviar_recordatorio_whatsapp

logger = logging.getLogger(__name__)


@receiver(post_save, sender=CitaMedica)
def notificar_paciente_cita(sender, instance, created, **kwargs):
    """
    Envía un recordatorio por WhatsApp cuando una cita confirmada (o recién creada con paciente)
    tiene un paciente con teléfono registrado. Nunca interrumpe el guardado ante fallos de red.
    """
    if not (created or instance.estado == "Confirmada"):
        return

    paciente = instance.paciente_set.first()
    if not (paciente and paciente.telefono):
        return

    try:
        resultado = enviar_recordatorio_whatsapp(
            telefono_paciente=paciente.telefono,
            nombre_paciente=paciente.nombre,
            fecha_cita=instance.fecha,
            hora_cita=instance.hora_inicio,
        )
        if not resultado.get("ok"):
            logger.warning("No se pudo enviar recordatorio WhatsApp (cita %s): %s", instance.id_cita, resultado.get("error"))
    except Exception as exc:
        logger.exception("Error inesperado enviando recordatorio WhatsApp (cita %s): %s", instance.id_cita, exc)
