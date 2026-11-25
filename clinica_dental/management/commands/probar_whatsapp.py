import json
from django.core.management.base import BaseCommand, CommandError
from clinica_dental.services import mensaje_prueba


class Command(BaseCommand):
    help = "Envía un mensaje de prueba mediante WhatsApp Cloud API para comprobar la integración."

    def add_arguments(self, parser):
        parser.add_argument(
            "telefono",
            type=str,
            help="Número de destino con código de país (ej: 56912345678 o +56912345678).",
        )
        parser.add_argument(
            "--modo",
            choices=["plantilla", "texto"],
            default="plantilla",
            help="Tipo de mensaje: 'plantilla' (hello_world) o 'texto' (mensaje libre).",
        )
        parser.add_argument(
            "--nombre",
            type=str,
            default="Paciente de Prueba",
            help="Nombre de referencia para el mensaje de prueba.",
        )
        parser.add_argument(
            "--mensaje",
            type=str,
            default=None,
            help="Texto personalizado cuando --modo=texto.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Genera el payload sin realizar la llamada HTTP real a Meta.",
        )

    def handle(self, *args, **options):
        resultado = mensaje_prueba(
            telefono_paciente=options["telefono"],
            nombre_paciente=options["nombre"],
            modo=options["modo"],
            mensaje=options["mensaje"],
            dry_run=options["dry_run"],
        )

        self.stdout.write(json.dumps(resultado, indent=2, ensure_ascii=False))

        if not resultado["ok"]:
            raise CommandError(f"Error al enviar mensaje de prueba: {resultado['error']}")

        if options["dry_run"]:
            self.stdout.write(self.style.SUCCESS("Payload de prueba generado correctamente (modo dry-run)."))
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Mensaje de prueba enviado exitosamente. ID: {resultado.get('message_id')}"
                )
            )
