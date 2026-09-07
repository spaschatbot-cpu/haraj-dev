"""A URLconf that hands MEDIA_URL to Django — the mistake `core.E001` exists to catch.

The route is written out here rather than obtained from
`django.conf.urls.static.static()` because that helper returns nothing unless
`DEBUG`, and the finding is about the *shape of the route*, not about `DEBUG`.
`test_checks.py` pins the two against each other, so this file cannot drift
into describing a pattern Django no longer builds.
"""

from __future__ import annotations

import re

from django.conf import settings
from django.urls import re_path
from django.views.static import serve

urlpatterns = [
    re_path(
        rf"^{re.escape(str(settings.MEDIA_URL).lstrip('/'))}(?P<path>.*)$",
        serve,
        kwargs={"document_root": settings.MEDIA_ROOT},
    )
]
