"""T821 — the console's door: the way in, and the way out.

Neither was a screen, so neither had a test, and both were broken. Visiting "/"
met the debug 404 that lists every route; every guarded page bounced to
Django's unrouted default `/accounts/login/`, which 404s; and once inside there
was no way out at all — no route, and nothing in the topbar.

`parity.md` §ب names both rows. They are the only two there that are defects
rather than questions for the owner: nobody signs off on whether staff may sign
in and out.
"""

from __future__ import annotations

import pytest
from django.conf import settings
from django.urls import reverse

pytestmark = pytest.mark.django_db


# ---- the way in ---------------------------------------------------------


def test_the_bare_host_hands_over_to_the_console(client) -> None:
    response = client.get("/")

    assert response.status_code == 302
    assert response.headers["Location"] == reverse("console:home")


def test_a_signed_out_operator_reaches_sign_in_from_the_bare_host(client) -> None:
    """The whole chain, hop by hop — "/" is only useful if it ends somewhere."""
    response = client.get("/", follow=True)

    assert response.status_code == 200
    landed = response.redirect_chain[-1][0]
    assert landed.startswith(reverse("admin-login"))
    assert f"next={reverse('console:home')}" in landed
    # And it is the sign-in page itself, not merely a page that answered 200.
    assert 'name="password"' in response.content.decode()


def test_a_signed_in_operator_lands_in_the_console_not_on_sign_in(client, staff) -> None:
    client.force_login(staff)

    response = client.get("/", follow=True)

    assert response.status_code == 200
    assert response.redirect_chain[-1][0] == reverse("console:home")


def test_the_login_url_is_a_route_this_project_serves() -> None:
    """Django's default is `/accounts/login/`; nothing here answers on it."""
    assert settings.LOGIN_URL == "admin-login"
    assert reverse(settings.LOGIN_URL) == "/admin/login/"


# ---- the way out --------------------------------------------------------


def test_the_topbar_offers_the_way_out(client, staff) -> None:
    client.force_login(staff)

    body = client.get(reverse("console:home")).content.decode()

    assert reverse("console:sign-out") in body
    assert "خروج" in body
    # A form, because the route is POST-only — a link here would be a button
    # that does nothing, which is worse than no button.
    assert 'method="post"' in body


def test_signing_out_ends_the_session(client, staff) -> None:
    client.force_login(staff)
    assert client.get(reverse("console:home")).status_code == 200

    response = client.post(reverse("console:sign-out"))

    assert response.status_code == 302
    assert response.headers["Location"] == reverse("admin-login")
    # The session is actually gone: the next page bounces back to sign-in.
    after = client.get(reverse("console:home"))
    assert after.status_code == 302
    assert after.headers["Location"].startswith(reverse("admin-login"))


def test_a_get_cannot_end_a_session(client, staff) -> None:
    """Otherwise any `<img src="…/sign-out/">` signs the operator out."""
    client.force_login(staff)

    response = client.get(reverse("console:sign-out"))

    assert response.status_code == 405
    assert client.get(reverse("console:home")).status_code == 200


def test_signing_out_is_not_a_page_in_the_registry() -> None:
    """It is an action, and no capability gates it — everyone in gets out."""
    from apps.console.navigation import PAGES

    assert "console:sign-out" not in {page.url_name for page in PAGES}
