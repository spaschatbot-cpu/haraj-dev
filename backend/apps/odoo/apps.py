from django.apps import AppConfig


class OdooConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.odoo"
    label = "odoo"

    def ready(self) -> None:
        # استيرادٌ يسجّل فحوصَ النشر التي يملكها هذا التطبيق — وهو الشيءُ
        # الوحيد الذي يفعله `ready`، كما في `accounts` و`core` و`bidding`.
        # لا إشاراتٍ تُوصَل هنا ولا واحدة في المشروع (T008).
        from apps.odoo import checks  # noqa: F401
