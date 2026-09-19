"""The sidebar, injected into every console template.

A context processor and not a per-view context entry, deliberately: a view that
forgot to add the navigation would render a console with no way out of it, and
"this page has no menu" is the kind of bug that reaches production because it
looks like a styling problem.
"""

from __future__ import annotations

from django.conf import settings
from django.utils.functional import SimpleLazyObject

from .exports import PARAM
from .icons import path_of
from .navigation import back_for, icon_for, sidebar_for
from .sensitive import shown_to


def navigation(request) -> dict:
    """`sidebar` and `environment`, on every page that renders a template.

    `environment` is here rather than in each view because Article 5-6 asks
    every screen to say which environment it is, and a rule that has to be
    remembered per view is a rule that is eventually forgotten on the one page
    somebody uses to do something irreversible.
    """
    user = getattr(request, "user", None)
    return {
        "sidebar": sidebar_for(user),
        # `shown.money` و`shown.customer` لكلّ قالبٍ في اللوحة — **بالحجّة
        # التي فوق حرفياً**. T901
        #
        # العرضُ الذي ينسى الحارسَ يرسم شاشةً فيها جوّالُ عميلٍ ومبلغُ فاتورته
        # لمن لا يملك قدرتَهما، وهو عطلٌ لا يُرى على الشاشة — يُرى في «عرض
        # المصدر» بعد أن يكون قد مرّ. وقد وقع هذا في تسع شاشاتٍ في ثلاث
        # جولات، آخرُها هذه.
        #
        # وهنا لأن `vehicle_detail` عرضُه في `auctions.py` وهو خارج نصيب هذه
        # الجولة: القالبُ يحتاج الجوابَ ولا سبيلَ إليه من عرضه. والعروضُ التي
        # تحسبه بنفسها تُبقي `show_money`/`show_customer` كما هي — هذا لا
        # يلغيها، إنّما يجعل النسيانَ غيرَ ممكن.
        #
        # و`SimpleLazyObject` لا قيمةً محسوبة: `shown_to` استعلاما `StaffGrant`،
        # وستٌّ وتسعون شاشةً لا تقرؤه كلُّها. فلا يُدفع الثمنُ إلّا حيث يُقرأ.
        "shown": SimpleLazyObject(lambda: shown_to(user)),
        "environment": settings.ENVIRONMENT_NAME,
        "app_base": settings.APP_BASE,
        "export_url": _export_url(request),
        # الخروج سطرٌ في ذيل الشريط كما في v1، ورسمُه يأتي من هنا لأنه **ليس**
        # صفّاً في `PAGES`: الصفّ هناك يعني رابطاً، ورابطٌ ينهي الجلسة على
        # `GET` ينهيها من أي `<img src>` — و`test_entry_points.py` يشترط
        # غيابه. فهو نموذجٌ يُرسَم بيده، ويأخذ رسمَه من السجلّ نفسه.
        "sign_out_icon": path_of("exit-door"),
        # أزرارُ الشريط العلويّ ودرجِ المظهر. كانت محارفَ نصّية — `☰` و`◐`
        # و`✕` — نجت من T837 لأنها ليست صفّاً في `PAGES` ولا بطاقةً في
        # `STAT_ICONS`، فلم يمرّ عليها أحد. وعليها حجّة T837 نفسُها حرفياً:
        # **نظام التشغيل هو الذي يرسمها**، بأسلوبه لا بأسلوب اللوحة، ومختلفةً
        # بين ويندوز وماك وأندرويد. و`◐` بعينه مذكورٌ في T837 ضمن ما أُخرج من
        # بطاقات الأرقام — ثم بقي هنا.
        #
        # ومن السجلّ نفسه لا مرسومةً في القالب بيدها: سجلٌّ واحدٌ لقرّائه.
        "nav_toggle_icon": path_of("menu"),
        "themer_icon": path_of("moon"),
        "close_icon": path_of("close"),
        # زرُّ «رجوع» على كل شاشة — من السجلّ لا من تاريخ المتصفّح. T864
        #
        # ومعالجُ سياق لا سطرٌ في كل عرض: الشاشاتُ ستٌّ وتسعون، وواحدةٌ تُنسى
        # هي الشاشة التي يعلق فيها الموظّف. والحسابُ رخيص — مسحُ سجلٍّ ثابتٍ
        # في الذاكرة، بلا استعلام.
        "back_to": _back_to(request),
        # رسمُ الشاشة الحالية لرأسها — من السجلّ نفسِه الذي يرسم سطرَها في
        # الشريط، فلا يفترقان.
        "page_icon": _page_icon(request),
    }


def _page_icon(request) -> str:
    """رسمُ الشاشة الحالية، أو الفراغ لما ليس شاشةً في السجلّ."""
    match = getattr(request, "resolver_match", None)
    if match is None or not match.view_name:
        return ""
    return icon_for(match.view_name)


def _back_to(request):
    """صفحةُ الرجوع لهذا الطلب، أو ``None`` للجذر وما ليس شاشةَ لوحة."""
    match = getattr(request, "resolver_match", None)
    if match is None or not match.view_name:
        return None
    return back_for(match.view_name)


def _export_url(request) -> str:
    """This page, with its current filters, asking for the workbook instead (I5).

    Built here rather than assembled in each template, for two reasons that are
    really one. A template writing `?{{ request.GET.urlencode }}&export=xlsx` is
    a hand-written link, and `ops/checks/console_urls_are_named.py` refuses one
    on principle — the console has moved prefix three times and every hand-built
    link broke silently each time. And naming the page's own url with `{% url %}`
    would make every list template repeat its own name, which is a second place
    to get it wrong for no gain: the export is *this* request with one parameter
    added, and `request.path` already is this request.

    The filter comes along by construction. An export that quietly ignored the
    search box would be worse than none, because it looks like it worked — that
    is what v1 shipped, and people went back to copying rows off the screen.
    """
    if request is None or not hasattr(request, "path"):
        return ""

    query = request.GET.copy() if hasattr(request, "GET") else {}
    if hasattr(query, "setlist"):
        query.setlist(PARAM, ["xlsx"])
        query.pop("page", None)
        return f"{request.path}?{query.urlencode()}"
    return f"{request.path}?{PARAM}=xlsx"


#: بصمةُ ورقة الأنماط — من **وقت تعديل الملفّ** لا من رقمٍ يُكتب بيد.
#:
#: كان القالبُ يحمل `?v=1133` مكتوباً حرفاً، ويُنتظَر ممّن يعدّل `app.css` أن
#: يتذكّر زيادتَه. ولا يتذكّر: الملفُّ تغيّر مرّاتٍ والرقمُ ثابت، وNginx يقول
#: للمتصفّح `max-age=604800` — **فسبعةُ أيامٍ ولا يرى أحدٌ التعديل**. قاله
#: المالك: «التعديل مش ظاهر عندي»، وهو كذلك على كلّ متصفّحٍ فتح الصفحةَ قبله.
#:
#: ويُقرأ الوقتُ مرّةً عند الإقلاع لا مع كلّ طلب: `stat` على كلّ صفحةٍ تُفتح
#: إنفاقٌ بلا مقابل، وإعادةُ تشغيل الخدمة جزءٌ من كلّ نشرٍ أصلاً.
def _asset_stamp() -> str:
    from pathlib import Path

    from django.contrib.staticfiles import finders

    newest = 0.0
    # كلُّ ملفٍّ ثابتٍ يحمل بصمةً في قالبٍ ما — والبصمةُ **أحدثُها**، فتعديلُ
    # أيٍّ منها يُبطل الكاشَ لجميعها. وذلك أرخصُ من بصمةٍ لكلّ ملفّ: الملفّاتُ
    # أربعةٌ والتعديلُ فيها متلازمٌ غالباً، وبصمةٌ واحدة لا تُنسى.
    for name in (
        "console/app.css",
        "console/theme.js",
        "console/fonts.css",
        "console/after_sales.js",
    ):
        found = finders.find(name)
        if found and Path(found).exists():
            newest = max(newest, Path(found).stat().st_mtime)
    return str(int(newest)) if newest else "0"


#: تُحسَب مرّةً، ويقرؤها القالبُ من السياق.
ASSET_STAMP = SimpleLazyObject(_asset_stamp)


def assets(request) -> dict:
    """بصمةُ الملفّات الثابتة، ليضعها القالبُ على روابطها."""
    return {"asset_stamp": ASSET_STAMP}
