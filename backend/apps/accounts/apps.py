from django.apps import AppConfig


class AccountsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.accounts"
    label = "accounts"

    def ready(self) -> None:
        # Importing registers this app's deploy checks. It is the one thing
        # `ready` does — no signals are connected here, and none exist in this
        # project (T008: an audit trail is written from the line that decided,
        # not from a receiver nobody can see).
        from apps.accounts import checks  # noqa: F401
