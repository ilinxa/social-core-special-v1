from django.apps import AppConfig


class ExploreConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.explore"
    verbose_name = "Explore"

    def ready(self):
        from apps.core.feature_config import feature_config

        if feature_config.is_system_enabled("explore"):
            import apps.explore.admin  # noqa: F401
