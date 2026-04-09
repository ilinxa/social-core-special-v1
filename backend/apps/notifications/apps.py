from django.apps import AppConfig


class NotificationsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.notifications"
    verbose_name = "Notifications"

    def ready(self):
        from apps.core.feature_config import feature_config

        if feature_config.is_system_enabled("notifications"):
            import apps.notifications.admin  # noqa: F401
