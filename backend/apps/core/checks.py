"""Deployment checks this app owns: the upload directory (T912) and the
limits at the edge (T914).

`manage.py check --deploy` is already a blocking CI step, so these findings
reach the same gate as Django's own. They are checks rather than import-time
guards for the reason `apps.accounts.checks` gives: `settings/test.py` inherits
from `prod.py` on purpose, and a `raise` there would refuse to let the test
settings load at all.

What they are about: in v1 a webshell lived for months inside the photographs
directory. `apps.core.uploads` makes sure a script cannot *become* a stored
file; these make sure the stored directory cannot become a place things run
from. The two halves are independent, and neither is sufficient alone.
"""

from __future__ import annotations

from pathlib import Path

from django.conf import settings
from django.core.checks import Error, Tags, register

from apps.core import ratelimit


@register(Tags.security, deploy=True)
def uploads_are_never_served_by_the_application(app_configs, **kwargs) -> list:
    """Nothing under MEDIA_ROOT is reachable through Django or through staticfiles.

    Two ways that goes wrong, and both are one line somebody added to make
    local development convenient:

    * a `static(settings.MEDIA_URL, ...)` line left in `config/urls.py`, which
      serves the directory through Django in production;
    * MEDIA_ROOT placed inside STATIC_ROOT or on a STATICFILES_DIRS path, which
      hands every upload to `collectstatic` and to whatever serves static files
      — a server that is often configured to run what it finds.
    """
    findings: list = []

    media_root = Path(settings.MEDIA_ROOT).resolve()

    from django.urls import get_resolver

    media_prefix = str(settings.MEDIA_URL).lstrip("/")
    for served in _routes_of(get_resolver()) if media_prefix else ():
        if served.startswith(media_prefix):
            findings.append(
                Error(
                    f"MEDIA_URL ({settings.MEDIA_URL}) is routed through Django "
                    f"by {served!r}.",
                    hint="Serve uploads from the web server as inert bytes — see "
                    "docs/runbooks/uploads.md. Django serving them puts the "
                    "upload directory inside the application.",
                    id="core.E001",
                )
            )

    static_root = getattr(settings, "STATIC_ROOT", None)
    if static_root and _is_within(media_root, Path(static_root).resolve()):
        findings.append(
            Error(
                f"MEDIA_ROOT ({media_root}) is inside STATIC_ROOT ({static_root}).",
                hint="Uploads must not be collected or served as static files. "
                "Point MEDIA_ROOT at a directory of its own, outside the "
                "document root.",
                id="core.E002",
            )
        )

    for directory in getattr(settings, "STATICFILES_DIRS", []):
        if _is_within(media_root, Path(str(directory)).resolve()):
            findings.append(
                Error(
                    f"MEDIA_ROOT ({media_root}) is inside STATICFILES_DIRS "
                    f"entry {directory}.",
                    hint="collectstatic would copy every upload into the "
                    "served static tree.",
                    id="core.E003",
                )
            )

    return findings


def _is_within(candidate: Path, parent: Path) -> bool:
    return candidate == parent or parent in candidate.parents


def _routes_of(resolver, prefix: str = ""):
    """Every URL this resolver can reach, as the route a browser would type.

    Two things the naive reading of `url_patterns` gets wrong, and both make the
    check silent about exactly the line it was written for:

    * a route is not its pattern's text. `path()` gives a `RoutePattern` whose
      text is the route (`media/<path:path>`), but `re_path()` — and therefore
      `django.conf.urls.static.static()`, the one-liner in the docstring above —
      gives a `RegexPattern` whose text is `^media/(?P<path>.*)$`. Comparing
      that to a `media/` prefix is a comparison that can never be true.
    * `url_patterns` is one level. Nobody edits `config/urls.py` to serve their
      uploads; they add the line to the app they already have open, and the
      include hides it from a top-level walk.
    """
    from django.urls import URLResolver

    for entry in resolver.url_patterns:
        # `lstrip('^')` not `removeprefix`: an included regex contributes its
        # own caret at every level, and what we are assembling is the route,
        # not a regex that still has to match.
        route = prefix + str(getattr(entry, "pattern", "")).lstrip("^")
        if isinstance(entry, URLResolver):
            yield from _routes_of(entry, route)
        else:
            yield route


#: Every scope `apps.core.ratelimit` can be asked about. Listed here rather than
#: derived, so that deleting a limit is a deliberate edit in two files rather
#: than a limit that quietly stopped being required.
REQUIRED_EDGE_SCOPES = (
    "odoo_webhook",
    "payment_callback",
    "staff_login_ip",
    "staff_login_account",
)


@register(Tags.security, deploy=True)
def the_edge_is_metered_in_a_deployed_environment(app_configs, **kwargs) -> list:
    """The limits DRF's throttles cannot reach, and the number that makes them real.

    All `Error`, not `Warning`. An unmetered password path is a guessing budget
    with no floor under it; an unmetered webhook is a table anybody who can
    reach the URL may fill; and a caller identity read out of a header the
    caller writes is not an identity at all — it is every limit in the project,
    silently off.
    """
    findings: list = []

    rates = getattr(settings, "EDGE_THROTTLE_RATES", {})
    missing = [scope for scope in REQUIRED_EDGE_SCOPES if not rates.get(scope)]
    if missing:
        findings.append(
            Error(
                "Edge rate limits are not configured for: " + ", ".join(missing) + ".",
                hint="Set them in EDGE_THROTTLE_RATES. Staff sign-in is the one "
                "that matters most: it is a password, and it opens money.act.",
                id="core.E004",
            )
        )

    for scope, rate in rates.items():
        try:
            ratelimit.parse_rate(rate)
        except (ValueError, TypeError):
            findings.append(
                Error(
                    f"EDGE_THROTTLE_RATES[{scope!r}] is {rate!r}, which does not "
                    "parse as a rate.",
                    hint="Write it as count/period, e.g. '600/minute'.",
                    id="core.E005",
                )
            )

    # The two readings of "who is calling" must be the same number. If they
    # drift, one family of limits meters the proxy and the other meters a
    # header — and nothing in the settings says which.
    hops = getattr(settings, "TRUSTED_PROXY_HOPS", 0)
    drf_proxies = settings.REST_FRAMEWORK.get("NUM_PROXIES")
    if drf_proxies != hops:
        findings.append(
            Error(
                f"REST_FRAMEWORK['NUM_PROXIES'] is {drf_proxies!r} but "
                f"TRUSTED_PROXY_HOPS is {hops!r}.",
                hint="They answer the same question and must be one number. "
                "Unset NUM_PROXIES is the dangerous case: DRF then keys every "
                "per-address limit on the whole X-Forwarded-For header, which "
                "the caller writes.",
                id="core.E006",
            )
        )

    return findings
