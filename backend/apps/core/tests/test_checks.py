"""`core.E001` — the deploy check that says nobody routed MEDIA_URL through Django.

`manage.py check --deploy` is the only automated guard named for this risk in
`config/settings/base.py` and `docs/runbooks/uploads.md`. A guard that cannot
report is worse than no guard: it is a line in a runbook that says the danger
is covered. So these tests put the real mistake in front of it and demand a
finding.
"""

from __future__ import annotations

import re

from django.conf import settings
from django.conf.urls.static import static
from django.test import override_settings

from apps.core.checks import uploads_are_never_served_by_the_application

MEDIA_URLCONF = "apps.core.tests.urls_serving_media"
NESTED_MEDIA_URLCONF = "apps.core.tests.urls_serving_media_from_an_include"


def _ids(findings) -> list[str]:
    return [finding.id for finding in findings]


@override_settings(ROOT_URLCONF=MEDIA_URLCONF)
def test_a_media_route_left_in_the_urlconf_is_reported():
    """The one-line local convenience that ships.

    The route Django builds is a regex — `^media/(?P<path>.*)$` — so anything
    matching the bare `media/` prefix against the pattern's own text never
    matches, and the check stays silent about the exact line it names.
    """
    assert _ids(uploads_are_never_served_by_the_application(None)) == ["core.E001"]


@override_settings(ROOT_URLCONF=NESTED_MEDIA_URLCONF)
def test_a_media_route_inside_an_include_is_reported():
    """Nobody adds it to `config/urls.py`; they add it to the app they are editing."""
    assert _ids(uploads_are_never_served_by_the_application(None)) == ["core.E001"]


def test_the_route_under_test_is_the_one_django_builds():
    """Pins the fixture to `static()` so it cannot drift into a straw man.

    `static()` is a no-op unless DEBUG, which is why the fixture writes the
    pattern out; this is the assertion that keeps the two the same route.
    """
    from apps.core.tests import urls_serving_media

    with override_settings(DEBUG=True):
        produced = static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

    assert [str(p.pattern) for p in produced] == [
        str(p.pattern) for p in urls_serving_media.urlpatterns
    ]
    # And that route really is a regex whose text starts with a caret — the
    # reason the prefix comparison could never be true.
    assert str(produced[0].pattern).startswith("^")


def test_the_projects_own_urlconf_is_clean():
    """The check must stay quiet on what we actually ship, or it is noise."""
    assert _ids(uploads_are_never_served_by_the_application(None)) == []


@override_settings(MEDIA_ROOT=str(settings.BASE_DIR / "media"))
def test_media_root_inside_static_root_is_reported():
    """The other half of T912: `collectstatic` handing every upload to the web server."""
    with override_settings(STATIC_ROOT=str(settings.BASE_DIR)):
        assert "core.E002" in _ids(uploads_are_never_served_by_the_application(None))


def test_the_media_prefix_is_read_the_way_django_writes_it():
    """MEDIA_URL is normalised to a leading slash; the check must not compare raw."""
    assert str(settings.MEDIA_URL).startswith("/")
    assert re.match(r"^/[^/]+/$", str(settings.MEDIA_URL))
