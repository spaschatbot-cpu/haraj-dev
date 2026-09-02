from django.apps import AppConfig


class BiddingConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.bidding"
    label = "bidding"

    def ready(self) -> None:
        # Importing registers this app's deploy checks — the same one thing
        # `apps.accounts` does here, and for the same reason: no signals are
        # connected anywhere in this project.
        from apps.bidding import checks  # noqa: F401
