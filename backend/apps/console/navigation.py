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
    Page("console:home", "الرئيسية", Capability.CONSOLE_ACCESS, "daily"),
    Page("console:auctions", "المزادات", Capability.AUCTIONS_VIEW, "daily"),
    Page("console:vehicles", "المركبات", Capability.AUCTIONS_VIEW, "daily"),
    Page(
        "console:why-no-bid",
        "ليه ما يقدرش يزايد؟",
        Capability.DIAGNOSTICS_VIEW,
        "diagnostics",
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
