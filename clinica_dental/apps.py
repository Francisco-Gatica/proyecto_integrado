from django.apps import AppConfig


class ClinicaDentalConfig(AppConfig):
    name = 'clinica_dental'

    def ready(self):
        import clinica_dental.signals  # noqa: F401
