from django.apps import AppConfig


class StrainsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.strains'

    def ready(self):
        # Import signals to register them
        import apps.strains.signals  # noqa: F401
