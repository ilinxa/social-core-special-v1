from django.apps import AppConfig


class CmsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.cms"
    verbose_name = "Content Management"

    def ready(self):
        from apps.core.feature_config import feature_config

        if feature_config.is_system_enabled("cms"):
            import apps.cms.admin  # noqa: F401
