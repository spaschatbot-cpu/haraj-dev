"""Every page in the console, declared once. T802.

The sidebar and the guard on each page read **the same rows**. That is the whole
design, and it is the answer to a specific v1 failure: there, the menu was one
list and the access rules were another, so a page added to the second and
forgotten in the first was invisible to the people who were allowed to use it —
and a page added to the first and forgotten in the second was a link everybody
could see and nobody could open. Both happened.

So a page here is a :class:`Page` row: a url name, a label, and the one
capability that both shows it in the sidebar and lets it be opened. Adding a
screen means adding a row; there is no second place to forget.

`test_navigation.py` proves the equivalence the hard way rather than by reading
this docstring: it signs in as each role, walks every url in the registry, and
asserts that the set of pages that answer 200 is exactly the set the sidebar
offered. A page guarded by one capability and listed under another fails it.
"""

from __future__ import annotations

from dataclasses import dataclass

from apps.core.permissions import Capability, can


@dataclass(frozen=True)
class Page:
    """One console screen: where it is, what it is called, who may open it."""

    #: Django url name, namespaced. Resolved with `{% url %}` and never written
    #: out as a path — see `ops/checks/console_urls_are_named.py` (T804).
    url_name: str

    label: str

    #: The single capability that both reveals this page in the sidebar and
    #: admits a caller to it. One field, because two would be the v1 bug.
    capability: str

    #: Which group the sidebar shows it under. Presentation only; it never
    #: affects access.
    section: str

    #: سطرٌ يقول ما تفعله هذه الشاشة — تقرأه الصفحةُ الرئيسية وحدها.
    #:
    #: الشريط الجانبي يعرض الأسماء، فرئيسيةٌ تعرض الأسماء نفسها تحت العناوين
    #: نفسها تكون نسخةً حرفية مما يراه القارئ بجانبها في اللحظة ذاتها. الاسم
    #: يقول أين تذهب، وهذا السطر يقول لماذا — وهو الفرق الوحيد الذي يجعل
    #: للصفحة سبب وجود.
    #:
    #: فارغٌ لصفحات التفصيل: لا تُعرض في شبكةٍ ولا في شريط، فلا أحد يقرأه.
    blurb: str = ""


@dataclass(frozen=True)
class Section:
    key: str
    label: str


SECTIONS: tuple[Section, ...] = (
    Section("daily", "التشغيل اليومي"),
    Section("money", "المال"),
    Section("diagnostics", "التشخيص"),
    Section("admin", "الإدارة"),
)


#: The console, in full. A screen that is not here does not exist as far as the
#: sidebar or the guards are concerned — which is deliberate: an unlisted page
#: reachable by url is exactly the shape of an accidental leak.
PAGES: tuple[Page, ...] = (
    Page(
        "console:home",
        "الرئيسية",
        Capability.CONSOLE_ACCESS,
        "daily",
        "ما تملك فتحه، وما تفعله كل شاشة.",
    ),
    Page(
        "console:auctions",
        "المزادات",
        Capability.AUCTIONS_VIEW,
        "daily",
        "المزاد الأسبوعي وحالته، وجدولته وبدؤه وإنهاؤه.",
    ),
    Page(
        "console:vehicles",
        "المركبات",
        Capability.AUCTIONS_VIEW,
        "daily",
        "كل مركبة وحالتها ولوتها وسعر وقوفها.",
    ),
    Page(
        "console:vehicles-import",
        "استيراد المركبات",
        Capability.AUCTIONS_IMPORT,
        "daily",
        "رفع دفعة مركبات من ملف، ومراجعة ما رُفض منها بسببه.",
    ),
    Page(
        "console:partner-decisions",
        "قرارات الشركاء",
        Capability.PARTNERS_DECIDE,
        "daily",
        "مركبات انتهت مزايدتها دون سعر الوقوف — يقبل المالك أو يرفض.",
    ),
    Page(
        "console:customers",
        "المستخدمون",
        Capability.USERS_VIEW,
        "daily",
        "العملاء والشركات وبياناتهم الموثّقة.",
    ),
    Page(
        "console:invoices",
        "الفواتير",
        Capability.INVOICES_VIEW,
        "money",
        "فواتير الفوز وما سُدّد منها وما تأخّر.",
    ),
    Page(
        "console:money-ledger",
        "دفتر التأمينات",
        Capability.MONEY_VIEW,
        "money",
        "كل ريال دخل أو خرج أو حُجز — للقراءة، والحركة تُصنع من أفعال المال.",
    ),
    Page(
        "console:audit",
        "سجل التدقيق",
        Capability.AUDIT_VIEW,
        "admin",
        "من غيّر ماذا ومتى، بالقيمة قبل وبعد.",
    ),
    Page(
        "console:odoo-inbox",
        "صندوق وارد أودو",
        Capability.ODOO_INBOX,
        "diagnostics",
        "ما وصل من أودو، وما فشل منه ولماذا، وإعادة تشغيله.",
    ),
    Page(
        "console:money-health",
        "صحة المال",
        Capability.DIAGNOSTICS_VIEW,
        "diagnostics",
        "أربعة فحوص مستقلّة على الدفتر، وكل خلاف تقوله بصراحة.",
    ),
    Page(
        "console:why-no-bid",
        "ليه ما يقدرش يزايد؟",
        Capability.DIAGNOSTICS_VIEW,
        "diagnostics",
        "عميلٌ ومركبة، والجواب: أي شرطٍ بالضبط منعه.",
    ),
)


#: Pages that take an id and therefore cannot appear in a sidebar — a link to
#: "the vehicle" means nothing without saying which. They are still rows here
#: because the guard reads this registry and nothing else, and a detail page
#: with no row would be a page with no guard.
DETAIL_PAGES: tuple[Page, ...] = (
    Page("console:auction-detail", "تفاصيل المزاد", Capability.AUCTIONS_VIEW, ""),
    Page("console:vehicle-detail", "تفاصيل المركبة", Capability.AUCTIONS_VIEW, ""),
    Page(
        "console:vehicle-state",
        "تغيير حالة المركبة",
        Capability.AUCTIONS_MANAGE,
        "",
    ),
    Page("console:auction-new", "مزاد جديد", Capability.AUCTIONS_MANAGE, ""),
    Page("console:auction-edit", "تعديل مزاد", Capability.AUCTIONS_MANAGE, ""),
    Page("console:vehicle-new", "مركبة جديدة", Capability.AUCTIONS_MANAGE, ""),
    Page("console:vehicle-edit", "تعديل مركبة", Capability.AUCTIONS_MANAGE, ""),
    # Downloads, not pages: a sidebar entry that starts a file download is a
    # link an operator clicks by accident.
    Page(
        "console:vehicles-export",
        "تصدير المركبات",
        Capability.AUCTIONS_IMPORT,
        "",
    ),
    Page(
        "console:vehicles-import-errors",
        "الصفوف المرفوضة",
        Capability.AUCTIONS_IMPORT,
        "",
    ),
    Page("console:partner-offers", "العروض", Capability.PARTNERS_DECIDE, ""),
    Page("console:partner-award", "الترسية", Capability.PARTNERS_DECIDE, ""),
    Page("console:partner-reject", "رفض المالك", Capability.PARTNERS_DECIDE, ""),
    Page("console:customer-detail", "بيانات العميل", Capability.USERS_VIEW, ""),
    Page("console:customer-edit", "تعديل العميل", Capability.USERS_MANAGE, ""),
    Page("console:company-edit", "تعديل الشركة", Capability.USERS_MANAGE, ""),
    # ليست `users.manage`: تعديلُ بيانات عميلٍ وتوسيعُ ما يستطيعه موظّف في
    # اللوحة كلّها ثقتان مختلفتان، وv1 جمعهما في علمٍ واحد.
    Page("console:staff-grants", "صلاحيات موظف", Capability.STAFF_GRANT, ""),
    Page("console:invoice-detail", "تفاصيل الفاتورة", Capability.INVOICES_VIEW, ""),
    Page("console:money-customer", "دفتر عميل", Capability.MONEY_VIEW, ""),
    # The three writes. `money-actions` carries `money.act`, and granting an
    # exception carries `money.exception` on top of it — the one action that
    # puts a bidder in an auction with nothing behind their bid is not the same
    # trust as confiscating a deposit that is already ours to take.
    Page("console:money-actions", "أفعال مالية", Capability.MONEY_ACT, ""),
    Page("console:money-confiscate", "مصادرة حجز", Capability.MONEY_ACT, ""),
    Page("console:money-correct", "تصحيح حركة", Capability.MONEY_ACT, ""),
    Page(
        "console:money-exception",
        "منح استثناء مزايدة",
        Capability.MONEY_EXCEPTION,
        "",
    ),
    Page("console:odoo-message", "رسالة واردة", Capability.ODOO_INBOX, ""),
    Page("console:odoo-replay", "إعادة تشغيل رسالة", Capability.ODOO_INBOX, ""),
)


def pages_for(user) -> tuple[Page, ...]:
    """The pages ``user`` may open — and therefore exactly what they are shown."""
    return tuple(page for page in PAGES if can(user, page.capability))


def sidebar_for(user) -> list[dict]:
    """The sidebar, grouped into sections, with empty sections dropped.

    An empty section heading is a promise of a page the reader cannot open, and
    a reader who sees "المال" with nothing under it goes and asks support why
    their access is broken.
    """
    allowed = pages_for(user)
    grouped = []

    for section in SECTIONS:
        items = [page for page in allowed if page.section == section.key]
        if items:
            grouped.append({"label": section.label, "pages": items})

    return grouped


def capability_for(url_name: str) -> str | None:
    """Which capability guards ``url_name``, or None when it is not a page here.

    Used by the guard decorator so a view names its page rather than repeating
    the capability — repeating it is how the two drift apart.
    """
    for page in (*PAGES, *DETAIL_PAGES):
        if page.url_name == url_name:
            return page.capability
    return None


__all__ = [
    "DETAIL_PAGES",
    "PAGES",
    "SECTIONS",
    "Page",
    "Section",
    "capability_for",
    "pages_for",
    "sidebar_for",
]
