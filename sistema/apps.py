from django.apps import AppConfig


class SistemaConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "sistema"
    
    def ready(self):
        import sistema.signals
