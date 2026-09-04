"""Shared helpers for the console's screen tests.

`screen_of` exists because four tests asked "does this read-only screen offer
anything that writes?" by scanning the whole rendered page — and the whole page
includes the chrome. When T821 put the sign-out form in the topbar, all four
went red on a form that is not on their screen and never was.

Scanning `<main>` is what those tests meant all along: their own docstrings say
"a button added **to the screen**". The chrome is shared, so it is asserted
once — `test_the_chrome_writes_nothing_but_the_way_out` below — rather than
re-asserted incidentally by every screen that happens to render it.
"""

from __future__ import annotations

import re

import pytest
from django.urls import reverse

MAIN = re.compile(r"<main\b[^>]*>(.*?)</main>", re.S | re.I)


def screen_of(body: str) -> str:
    """The page's own content, without the sidebar and topbar around it."""
    match = MAIN.search(body)
    assert match, "الصفحة بلا <main> — القالب الأساسي تغيّر"
    return match.group(1)


@pytest.mark.django_db
def test_the_chrome_writes_nothing_but_the_way_out(client, staff) -> None:
    """The hole `screen_of` opens, closed here.

    Narrowing those four assertions to `<main>` stops them from seeing the
    chrome at all — so the chrome needs its own claim: exactly one thing in it
    posts, and it is signing out.
    """
    client.force_login(staff)
    body = client.get(reverse("console:home")).content.decode()
    chrome = body.replace(screen_of(body), "")

    forms = re.findall(r"<form\b[^>]*>", chrome, re.I)
    assert len(forms) == 1, f"نموذج جديد في الإطار: {forms}"
    assert reverse("console:sign-out") in chrome
