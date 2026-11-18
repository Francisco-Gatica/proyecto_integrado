from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import CitaMedica
from .services import enviar_recordatorio_whatsapp

@receiver(post_save, sender=CitaMedica)
def notificar_paciente_cita(sender, instance, created, **kwargs):
    if created or instance.estado == 'Confirmada':
        paciente = instance.paciente_set.first() 
        
        if paciente and paciente.telefono:
            telefono_limpio = paciente.telefono.replace('+', '').replace(' ', '')
            
            enviar_recordatorio_whatsapp(
                telefono_paciente=telefono_limpio,
                nombre_paciente=paciente.nombre,
                fecha_cita=instance.fecha
            )