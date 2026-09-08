"""لكلّ شاشةٍ طريقُ عودة، ولا أبَ يحتاج وسائط. T864.

العطل الذي وُجد لأجله
=====================
صفحاتُ التفصيل تُفتح من قائمةٍ ولا مدخلَ لها في الشريط الجانبي: مركبةٌ بعينها،
قرارُ شريكٍ بعينه، فاتورةٌ بعينها. فالخروجُ منها كان بسهم المتصفّح وحده.

وسهمُ المتصفّح يعود إلى **الطلب** السابق لا إلى الشاشة السابقة: بعد `POST`
وإعادة توجيهٍ يعود إلى الاستمارة المرسَلة، وفي تبويبٍ فُتح برابطٍ مباشر يخرج
من اللوحة كلّها إلى ما كان قبلها.

القاعدتان
=========
١. كلُّ صفحةٍ في `DETAIL_PAGES` تُصرّح بـ`parent`. وصفحاتُ الشريط لا تحتاجه —
   جميعها تعود إلى الجذر.
٢. والأبُ **مسارٌ بلا وسائط**. أبٌ يحتاج `pk` يعني رابطاً يُبنى بيدٍ في كل
   قالب، وذاك ما يرفضه `console_urls_are_named` — وقد انتقلت لوحاتُ v1 بين
   بادئاتٍ ثلاثَ مرّات، وانكسر كلُّ رابطٍ مكتوبٍ بيده في كل مرّة صامتاً.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.dev")


def main() -> int:
    import django

    django.setup()

    from django.urls import NoReverseMatch, reverse

    from apps.console.navigation import DETAIL_PAGES, PAGES, back_for

    if not DETAIL_PAGES:
        print("لا صفحةَ تفصيلٍ في السجلّ — الفحص لا يجد ما يحرسه.")
        return 1

    bad: list[str] = []

    for page in DETAIL_PAGES:
        if not page.parent:
            bad.append(f"{page.url_name} («{page.label}») بلا `parent` — لا طريق عودة منها.")
            continue
        target = back_for(page.url_name)
        if target is None:
            bad.append(f"{page.url_name}: `parent` هو {page.parent!r} ولا صفحةَ بهذا الاسم.")
            continue
        try:
            reverse(target.url_name)
        except NoReverseMatch:
            bad.append(
                f"{page.url_name}: أبوه {target.url_name} يحتاج وسائط — "
                "والآباءُ قوائمُ بلا وسائط."
            )

    # والجذرُ بلا زرّ، وما عداه من صفحات الشريط يعود إليه.
    for page in PAGES:
        target = back_for(page.url_name)
        if page.url_name == "console:home":
            if target is not None:
                bad.append("console:home لها زرُّ رجوع — ولا شيء فوق الجذر.")
        elif target is None:
            bad.append(f"{page.url_name} («{page.label}») لا تعود إلى شيء.")

    if bad:
        print("شاشةٌ بلا طريق عودة:\n")
        for line in bad:
            print(f"  {line}")
        return 1

    print(
        f"لكلّ شاشةٍ طريقُ عودة — {len(DETAIL_PAGES)} صفحةَ تفصيلٍ إلى آبائها، "
        f"و{len(PAGES) - 1} إلى الجذر."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
