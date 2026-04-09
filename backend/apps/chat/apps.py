from django.apps import AppConfig


class ChatConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.chat"
    verbose_name = "Chat"

    def ready(self):
        from apps.core.feature_config import feature_config

        if feature_config.is_system_enabled("chat"):
            import apps.chat.admin  # noqa: F401
