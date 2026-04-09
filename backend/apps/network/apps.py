from django.apps import AppConfig


class NetworkConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.network"
    verbose_name = "Network"

    def ready(self):
        from apps.core.feature_config import feature_config

        if feature_config.is_system_enabled("network"):
            import apps.network.admin  # noqa: F401
