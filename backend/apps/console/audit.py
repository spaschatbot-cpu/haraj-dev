"""سجل التدقيق — searchable by who, by what, and by when. T815.

Read-only, and the one screen in the console that is *about* the console. Three
filters, because there are three ways a question about a past change actually
arrives:

* **بالمنفّذ** — "what did this person do last Thursday?", which is how a
  dispute about an operator starts;
* **بالكيان** — "everything that ever happened to this hold / this invoice /
  this customer", which is how a dispute about a *balance* starts, and is the
  reason `AuditLog` carries `(entity_type, entity_id, -at)` as an index;
* **بالفترة** — a window, because "sometime around the end of the month" is
  what people remember.

The actions dropdown is built from the rows, not from a list
----------------------------------------------------------
`ACTIONS` is `AuditLog.objects.values_list("action").distinct()` and nothing
else. A hardcoded set of choices is a filter that silently stops offering an
action the day somebody adds one — and the action nobody can filter for is the
action nobody audits. It costs one grouped query on a well-indexed column, which
is a fair price for a filter that cannot go stale.

What is not here
----------------
Any way to edit or delete. `AuditLog.save` refuses a second write and `delete`
refuses outright (phase 001), so this is not a rule the screen has to keep — but
it is worth saying that no button was written for it either. An audit trail that
can be edited proves nothing about the trail it exists to protect.
"""

from __future__ import annotations

from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import render
from django.utils import timezone

from apps.accounts.services import find_by_phone
from apps.core.models import AuditLog

from .views import console_page

#: Rows per page. An audit search is read in bulk — somebody is reconstructing a
#: sequence, not looking at one row.
PAGE_SIZE = 50


def _day_bounds(text: str, *, end: bool):
    """Parse a `YYYY-MM-DD` box into an aware datetime, or None.

    A date typed into a filter means the whole day in the operator's mind, so
    "to 2026-09-03" includes everything that happened on the third. Treating it
    as midnight would silently drop a day's worth of rows — and the row somebody
    is looking for is disproportionately often the last one.
    """
    from datetime import datetime, time

    try:
        day = datetime.strptime(text.strip(), "%Y-%m-%d").date()
    except (AttributeError, ValueError):
        return None

    moment = datetime.combine(day, time.max if end else time.min)
    return timezone.make_aware(moment, timezone.get_current_timezone())


def search(*, actor: str = "", entity: str = "", action: str = "", since="", until=""):
    """The audit trail, narrowed by whatever was typed. Empty filters narrow nothing.

    Kept out of the view so the acceptance test can ask the question directly:
    the criterion is that every admin money action *is findable*, and that is a
    property of this function rather than of an HTML page.
    """
    rows = AuditLog.objects.select_related("actor")

    actor = (actor or "").strip()
    if actor:
        # A phone number is what an operator has to hand — the person is on the
        # phone or in a ticket — so it is matched the way every other staff
        # screen matches one, then falls back to a name.
        person = find_by_phone(actor)
        rows = (
            rows.filter(actor=person)
            if person is not None
            else rows.filter(actor__full_name__icontains=actor)
        )

    entity = (entity or "").strip()
    if entity:
        # "money.hold", "money.hold:41" or just "41". The colon form is what the
        # rows themselves print, so a subject copied off another screen pastes
        # straight in.
        entity_type, _, entity_id = entity.partition(":")
        terms = Q(entity_type__icontains=entity_type)
        if entity_id:
            terms &= Q(entity_id=entity_id.strip())
        elif entity_type.isdigit():
            terms = Q(entity_id=entity_type)
        rows = rows.filter(terms)

    action = (action or "").strip()
    if action:
        rows = rows.filter(action=action)

    start = _day_bounds(since, end=False)
    if start is not None:
        rows = rows.filter(at__gte=start)

    finish = _day_bounds(until, end=True)
    if finish is not None:
        rows = rows.filter(at__lte=finish)

    return rows


@console_page("console:audit")
def audit(request):
    """The search box, and whatever it found."""
    rows = search(
        actor=request.GET.get("actor", ""),
        entity=request.GET.get("entity", ""),
        action=request.GET.get("action", ""),
        since=request.GET.get("since", ""),
        until=request.GET.get("until", ""),
    )

    return render(
        request,
        "console/audit.html",
        {
            "page": Paginator(rows, PAGE_SIZE).get_page(request.GET.get("page")),
            # From the rows, never from a list somebody maintains: the action
            # nobody can filter for is the action nobody audits.
            "actions": sorted(
                AuditLog.objects.values_list("action", flat=True).distinct()
            ),
            "actor": request.GET.get("actor", ""),
            "entity": request.GET.get("entity", ""),
            "action": request.GET.get("action", ""),
            "since": request.GET.get("since", ""),
            "until": request.GET.get("until", ""),
        },
    )


__all__ = ["audit", "search"]
