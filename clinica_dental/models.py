from django.conf import settings
from django.db import models

class AsistenteDental(models.Model):
    id_asistente = models.IntegerField(primary_key=True)
    id_usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.DO_NOTHING, db_column='id_usuario', blank=True, null=True)
    telefono = models.CharField(max_length=15, blank=True, null=True)
    horarioatencion = models.TimeField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'AsistenteDental'


class Calendario(models.Model):
    id_calendario = models.IntegerField(primary_key=True)
    id_cita = models.ForeignKey('CitaMedica', on_delete=models.DO_NOTHING, db_column='id_cita', blank=True, null=True)
    ano = models.IntegerField(blank=True, null=True)
    nombre_mes = models.CharField(max_length=30, blank=True, null=True)
    numero_mes = models.IntegerField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'calendario'


class CitaMedica(models.Model):
    id_cita = models.IntegerField(primary_key=True)
    id_doctor = models.ForeignKey('Doctor', on_delete=models.DO_NOTHING, db_column='id_doctor', blank=True, null=True)
    fecha = models.DateField(blank=True, null=True)
    hora_inicio = models.TimeField(blank=True, null=True)
    hora_fin = models.TimeField(blank=True, null=True)
    motivo_consulta = models.TextField(blank=True, null=True)
    estado = models.CharField(max_length=50, blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'cita_medica'


class Doctor(models.Model):
    id_doctor = models.IntegerField(primary_key=True)
    id_usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.DO_NOTHING, db_column='id_usuario', blank=True, null=True)
    especialidad = models.CharField(max_length=100, blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'doctor'


class Paciente(models.Model):
    id_paciente = models.IntegerField(primary_key=True)
    id_cita = models.ForeignKey('CitaMedica', on_delete=models.DO_NOTHING, db_column='id_cita', blank=True, null=True)
    rut = models.CharField(unique=True, max_length=100, blank=True, null=True)
    nombre = models.CharField(max_length=100, blank=True, null=True)
    primer_apellido = models.CharField(max_length=100, blank=True, null=True)
    segundo_apellido = models.CharField(max_length=100, blank=True, null=True)
    telefono = models.CharField(max_length=15, blank=True, null=True)
    correo = models.CharField(max_length=100, blank=True, null=True)
    fecha_nacimiento = models.DateField(blank=True, null=True)
    activo = models.BooleanField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'paciente'