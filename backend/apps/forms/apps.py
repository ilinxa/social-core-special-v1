from django.apps import AppConfig


class FormsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.forms"
    verbose_name = "Form Builder"

    def ready(self):
        """Import signals when app is ready."""
        import apps.forms.signals  # noqa: F401
        from apps.core.feature_config import feature_config

        if feature_config.is_system_enabled("forms"):
            import apps.forms.admin  # noqa: F401
