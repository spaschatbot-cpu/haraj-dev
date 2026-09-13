from django.apps import AppConfig


class MoneyConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.money"
    label = "money"

    def ready(self) -> None:
        # استيرادٌ يسجّل فحوصَ النشر التي يملكها هذا التطبيق — وهو الشيءُ
        # الوحيد الذي يفعله `ready`، كما في `accounts` و`core` و`bidding`.
        from apps.money import checks  # noqa: F401
