from django.apps import AppConfig


class FormsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.forms"
    verbose_name = "Form Builder"

    def ready(self):
        """Import signals when app is ready."""
        import apps.forms.signals  # noqa: F401
