from django.apps import AppConfig


class SystemConfigConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "system_config"

    def ready(self):
        import system_config.signals  # noqa: F401
