"""The sidebar, injected into every console template.

A context processor and not a per-view context entry, deliberately: a view that
forgot to add the navigation would render a console with no way out of it, and
"this page has no menu" is the kind of bug that reaches production because it
looks like a styling problem.
"""

from __future__ import annotations

from django.conf import settings

from .exports import PARAM
from .icons import path_of
from .navigation import back_for, sidebar_for


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
        "environment": settings.ENVIRONMENT_NAME,
        "app_base": settings.APP_BASE,
        "export_url": _export_url(request),
        # الخروج سطرٌ في ذيل الشريط كما في v1، ورسمُه يأتي من هنا لأنه **ليس**
        # صفّاً في `PAGES`: الصفّ هناك يعني رابطاً، ورابطٌ ينهي الجلسة على
        # `GET` ينهيها من أي `<img src>` — و`test_entry_points.py` يشترط
        # غيابه. فهو نموذجٌ يُرسَم بيده، ويأخذ رسمَه من السجلّ نفسه.
        "sign_out_icon": path_of("exit-door"),
        # زرُّ «رجوع» على كل شاشة — من السجلّ لا من تاريخ المتصفّح. T864
        #
        # ومعالجُ سياق لا سطرٌ في كل عرض: الشاشاتُ ستٌّ وتسعون، وواحدةٌ تُنسى
        # هي الشاشة التي يعلق فيها الموظّف. والحسابُ رخيص — مسحُ سجلٍّ ثابتٍ
        # في الذاكرة، بلا استعلام.
        "back_to": _back_to(request),
    }


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
