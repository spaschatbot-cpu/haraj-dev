"""The sidebar, injected into every console template.

A context processor and not a per-view context entry, deliberately: a view that
forgot to add the navigation would render a console with no way out of it, and
"this page has no menu" is the kind of bug that reaches production because it
looks like a styling problem.
"""

from __future__ import annotations

from django.conf import settings

from .navigation import sidebar_for


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
    }
