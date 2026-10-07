"""امشِ اللوحةَ كلَّها: كلُّ شاشةٍ وكلُّ رابطٍ فيها، بقراءةٍ لا كتابة.

نظيرُ `walk_customer_cycle` لجهة الموظّف. **ليست حزمةَ اختبارات** — لا `pytest`
ولا `conftest` (CLAUDE.md، المادة المحذوفة). مشيةٌ واحدةٌ على قاعدةٍ حقيقيّة
تُطبع نتيجتُها بأرقامها: «٧٧ شاشةً، ٢١٤ رابطاً، ٢١٤ ردّت ٢٠٠».

## كيف تمشي

تبدأ من صفوف الشريط الجانبيّ (`navigation.PAGES`) وتتبع كلَّ رابطٍ داخل
`/console/` تجده في الصفحة — فتصل إلى صفحات التفاصيل (مزادٌ بعينه، عميلٌ،
فاتورة) من الروابط الحقيقيّة التي يضغطها الموظّف، لا من معرّفاتٍ تُخمَّن.
وتأخذ **عيّنتين من كلّ نمط مسار** لا كلَّ صفّ: عشرةُ آلاف عميلٍ هي شاشةٌ
واحدةٌ مكرّرة.

## ما لا تفعله

* **`GET` وحده.** كلُّ فعلٍ في اللوحة استمارةُ `POST` — فالمشيةُ لا تُرسي ولا
  تشحن ولا تحذف شيئاً. والقاعدةُ بعدها كما كانت قبلها.
* لا تفتح التصديرَ (`export`) ولا الخروج (`logout`): الأوّلُ ملفٌّ يُبنى من
  الجدول كلِّه، والثاني يُنهي الجلسة التي تمشي بها.

    python manage.py walk_console
    python manage.py walk_console --per-pattern 3
"""

from __future__ import annotations

import re
import time
from collections import defaultdict

from django.conf import settings
from django.core.management.base import BaseCommand
from django.urls import Resolver404, resolve, reverse

#: أنماطٌ لا تُفتح — انظر رأس الملفّ.
SKIP = re.compile(r"export|logout|sign-out|signout|download|\.csv|\.xlsx", re.I)
HREF = re.compile(r'href="(/console/[^"#?]*)(?:\?[^"#]*)?"')


class Command(BaseCommand):
    help = "امشِ كلَّ شاشات اللوحة وروابطها بقراءةٍ لا كتابة، واطبع ما ردّ."

    def add_arguments(self, parser):
        parser.add_argument("--per-pattern", type=int, default=2)
        parser.add_argument("--limit", type=int, default=600)

    def handle(self, *args, **options):
        from django.contrib.auth import get_user_model
        from django.test import Client

        from apps.console.navigation import PAGES

        staff = (
            get_user_model()
            .objects.filter(is_superuser=True, is_staff=True, is_active=True)
            .order_by("pk")
            .first()
        )
        if staff is None:
            self.stderr.write("لا مديرَ نشِطٌ في القاعدة — لا تُمشى اللوحة بلا صلاحيات.")
            return

        client = Client()
        client.force_login(staff)
        hosts = [h for h in settings.ALLOWED_HOSTS if h and not h.startswith("*")]
        host = dict(SERVER_NAME=hosts[0] if hosts else "testserver", secure=True)

        queue: list[tuple[str, str]] = []
        for page in PAGES:
            try:
                queue.append((reverse(page.url_name), "الشريط"))
            except Exception as error:  # noqa: BLE001
                self.stdout.write(f"❌ {page.url_name}: لا يُبنى مسارُه — {error}")

        seen: set[str] = set()
        per_pattern: dict[str, int] = defaultdict(int)
        results: list[tuple[str, str, int, float, str]] = []

        while queue and len(results) < options["limit"]:
            path, came_from = queue.pop(0)
            if path in seen or SKIP.search(path):
                continue
            seen.add(path)
            try:
                name = resolve(path).view_name
            except Resolver404:
                results.append((path, "?", 404, 0.0, f"لا مسارَ له — رابطٌ في {came_from}"))
                continue
            if per_pattern[name] >= options["per_pattern"]:
                continue
            per_pattern[name] += 1

            started = time.monotonic()
            try:
                response = client.get(path, **host)
                status = response.status_code
                note = ""
                if status in (301, 302):
                    note = "← " + response.get("Location", "")
                body = response.content.decode("utf-8", "replace") if status == 200 else ""
            except Exception as error:  # noqa: BLE001
                status, note, body = 500, f"{type(error).__name__}: {error}"[:200], ""
            took = time.monotonic() - started
            results.append((path, name, status, took, note))

            for link in HREF.findall(body):
                if link not in seen:
                    queue.append((link, path))

        bad = [row for row in results if row[2] >= 400]
        slow = sorted(results, key=lambda row: -row[3])[:5]
        names = {row[1] for row in results}

        for path, name, status, took, note in results:
            mark = "✅" if status < 300 else ("↪️" if status < 400 else "❌")
            self.stdout.write(f"{mark} {status} {took:5.2f}s  {name:<40} {path} {note}")

        self.stdout.write("\n" + "─" * 72)
        self.stdout.write(
            f"{len(names)} نمطَ مسار · {len(results)} صفحةً فُتحت · "
            f"{len(results) - len(bad)} ردّت بلا خطأ · {len(bad)} بخطأ"
        )
        self.stdout.write("الأبطأ: " + " · ".join(f"{r[1]} {r[3]:.1f}s" for r in slow))
        for path, name, status, _took, note in bad:
            self.stdout.write(f"   ❌ {status} {name} {path} {note}")
