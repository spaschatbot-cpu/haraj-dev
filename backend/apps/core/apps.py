from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.core"
    label = "core"

    def ready(self) -> None:
        # Importing registers this app's deploy checks (T912). No signals are
        # connected here, and none exist in this project (T008: an audit trail
        # is written from the line that decided, not from a receiver nobody
        # can see).
        from apps.core import checks  # noqa: F401
