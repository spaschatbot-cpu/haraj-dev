"""The console's own pages, and the decorator every console page wears.

A view here does what every view in this project does: reads a request, calls a
service, renders. What is specific to the console is the guard — and the guard
takes a **page name**, not a capability, so the rule that admits a caller and
the rule that shows the link are the same row in
:mod:`apps.console.navigation` rather than two strings that agree today.
"""

from __future__ import annotations

from functools import wraps

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ImproperlyConfigured, PermissionDenied
from django.shortcuts import render

from apps.core.permissions import can

from .navigation import capability_for


def console_page(url_name: str):
    """Guard a view with the capability its page is listed under.

    Naming the page rather than the capability is the point. A decorator taking
    a capability would be a second place to write it down, and v1's console
    broke precisely because the menu's copy and the guard's copy drifted.

    An unknown page name raises at import time. A guard that silently allows
    everything because somebody mistyped its name is worse than no guard, and
    the mistype is exactly what a typo-prone string invites.
    """
    capability = capability_for(url_name)
    if capability is None:
        raise ImproperlyConfigured(f"{url_name} is not in apps.console.navigation.PAGES")

    def decorate(view):
        @wraps(view)
        @login_required
        def guarded(request, *args, **kwargs):
            if not can(request.user, capability):
                raise PermissionDenied(f"{capability} غير مسموحة لهذا المستخدم")
            return view(request, *args, **kwargs)

        return guarded

    return decorate


@console_page("console:home")
def home(request):
    """What this person can do, as their own list rather than a generic menu.

    The landing page is the sidebar written large on purpose: the first thing a
    support agent needs is to know which of their questions this console can
    answer, and a dashboard of numbers they cannot act on is what v1's home page
    was.
    """
    return render(
        request,
        "console/home.html",
        {"environment": settings.ENVIRONMENT_NAME},
    )
