"""The decorator every console page wears.

The guard takes a **page name**, not a capability, so the rule that admits a
caller and the rule that shows the link are the same row in
:mod:`apps.console.navigation` rather than two strings that agree today.

This module held `console:home` too, back when the root was a grid of cards
explaining each screen. The root is the analytics board now — as it is in v1 —
and the explaining line lives on each sidebar link, so the grid is gone and
what is left here is the guard alone.
"""

from __future__ import annotations

from functools import wraps

from django.contrib.auth.decorators import login_required
from django.core.exceptions import ImproperlyConfigured, PermissionDenied
from django.shortcuts import redirect

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
            # كلمةٌ كتبها غيرُه تُغيَّر قبل أي شيء (T839). ويُستثنى مسارُ
            # التغيير نفسه وإلّا دار على نفسه، والخروجُ ليس صفحةً هنا أصلاً.
            if (
                getattr(request.user, "must_change_password", False)
                and url_name != "console:password-change"
            ):
                return redirect("console:password-change")
            if not can(request.user, capability):
                raise PermissionDenied(f"{capability} غير مسموحة لهذا المستخدم")
            return view(request, *args, **kwargs)

        return guarded

    return decorate
