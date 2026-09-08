"""نداءُ اتصالٍ للتحقّق من الربط بأودو — قراءةٌ فقط، لا يكتب شيئاً.

يستعمل نفسَ مسار التطبيق (`apps.odoo.client.call`) فيثبت أن العنوان والتوكن
وTLS تعمل معاً. يُميّز ثلاث نتائج:

* **وصل واستُجيب** — الرابط تامّ.
* **وصل ورُفض (4xx)** — الشبكةُ والتوكنُ يعملان لكن أودو ردّ «لا» (رقمُ دفعةٍ
  وهميّ مثلاً)، وهو ما يزال إثباتاً للوصول والمصادقة.
* **لم يصل / 401** — الرابطُ أو التوكنُ معطَّل، فيُقال بوضوح.

الاستعمال:
    python manage.py odoo_ping                # /get/payment/status بمعرّفٍ وهميّ
    python manage.py odoo_ping --payment 123  # معرّفٌ حقيقيّ
"""

from __future__ import annotations

from django.conf import settings
from django.core.management.base import BaseCommand

from apps.odoo.client import OdooDisabled, OdooUnreachable, call


class Command(BaseCommand):
    help = "اختبار اتصالٍ للقراءة بأودو (يثبت العنوان والتوكن وTLS)."

    def add_arguments(self, parser):
        parser.add_argument("--payment", type=int, default=0)
        parser.add_argument(
            "--endpoint", default="get/payment/status",
            help="نقطة قراءة (الافتراضي get/payment/status).",
        )

    def handle(self, *args, **opts):
        self.stdout.write(f"ODOO_ENABLED = {settings.ODOO_ENABLED}")
        self.stdout.write(f"ODOO_BASE_URL = {settings.ODOO_BASE_URL or '(فارغ)'}")
        self.stdout.write(
            "التوكن: "
            + ("موجود" if (settings.ODOO_API_KEY or "").strip() else "غائب")
            + f" · TLS insecure = {getattr(settings, 'ODOO_INSECURE_TLS', False)}"
        )

        pid = opts["payment"] or 999999999
        payload = {"jsonrpc": "2.0", "method": "call", "id": 1, "params": {"payment_id": pid}}
        try:
            result = call(opts["endpoint"], payload, reference=f"ping-{pid}")
        except OdooDisabled as exc:
            self.stderr.write(self.style.WARNING(
                f"مطفأ: {exc}\nفعِّل مؤقتاً في backend/.env: ODOO_ENABLED=True"
            ))
            return
        except OdooUnreachable as exc:
            self.stderr.write(self.style.ERROR(
                f"لم يصل — الرابط أو الشبكة معطَّل: {exc}"
            ))
            return
        except ValueError as exc:
            # 4xx: وصل ورُفض. 401/403 = توكن؛ غيرها = رفضٌ تجاريّ (ما يزال وصولاً).
            msg = str(exc)
            if "401" in msg or "403" in msg:
                self.stderr.write(self.style.ERROR(f"وصل لكن رُفضت المصادقة (توكن): {msg}"))
            else:
                self.stdout.write(self.style.SUCCESS(
                    f"وصل وأُصيبت المصادقة — أودو ردّ رفضاً تجاريّاً (متوقَّع لمعرّفٍ وهميّ):\n{msg}"
                ))
            return

        self.stdout.write(self.style.SUCCESS("وصل واستُجيب — الرابط تامّ."))
        self.stdout.write(str(result)[:800])
