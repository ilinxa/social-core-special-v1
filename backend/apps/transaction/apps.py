from django.apps import AppConfig


class TransactionConfig(AppConfig):
    name = "apps.transaction"
    default_auto_field = "django.db.models.BigAutoField"
    verbose_name = "Transaction System"

    def ready(self):
        import apps.transaction.signals  # noqa: F401
        from apps.transaction.outcome_handlers import register_all_handlers

        register_all_handlers()
