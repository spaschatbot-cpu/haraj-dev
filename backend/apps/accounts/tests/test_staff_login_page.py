"""T819 — staff sign-in wears the console's skin, not Django's.

`admin.site.login` renders `admin/login.html`; placing ours in `templates/`
replaces the skin while the view — and its throttle in `apps.accounts.login` —
stays untouched. These tests pin the contract that makes that safe: the same
endpoint, the same field names, the same hidden `next`.
"""

from __future__ import annotations

import pytest
from django.urls import reverse

pytestmark = pytest.mark.django_db


def test_staff_login_renders_the_console_skin(client) -> None:
    response = client.get(reverse("admin-login"))

    assert response.status_code == 200
    body = response.content.decode()
    # Absolute, with the leading slash: a relative "static/…" resolves against
    # the page, so `/admin/login/` asked `/admin/static/…` for it and the skin
    # never loaded — which is exactly how this file's first version shipped.
    assert 'href="/static/console/app.css"' in body
    assert "لوحة حراج" in body
    assert "env-badge" in body
    # The animated scene and the password peek are part of the skin.
    assert body.count('class="orb ') == 3
    assert 'id="peek"' in body
    assert 'type="button"' in body
    # And no template comment leaks onto it (the console's topbar wore two).
    assert "{#" not in body
    assert "#}" not in body
    # Django's own admin chrome is gone.
    assert 'id="header"' not in body


def test_the_console_frame_links_the_same_stylesheet(client, staff) -> None:
    """The same relative-URL trap, on the console's own pages."""
    client.force_login(staff)
    body = client.get(reverse("console:home")).content.decode()

    assert 'href="/static/console/app.css"' in body


def test_staff_login_posts_the_fields_the_view_expects(client) -> None:
    body = client.get(reverse("admin-login")).content.decode()

    assert 'name="username"' in body
    assert 'name="password"' in body
    assert 'name="next"' in body


def test_a_wrong_password_rerenders_the_same_skin_with_its_error(client, staff) -> None:
    response = client.post(
        reverse("admin-login"),
        {"username": staff.phone, "password": "wrong-password", "next": "/console/"},
    )

    assert response.status_code == 200
    body = response.content.decode()
    assert 'href="/static/console/app.css"' in body
    assert "notice error" in body


def test_a_bare_sign_in_lands_in_the_console_not_django_admin(client, staff) -> None:
    """`?next=` still wins, but a bare visit must not drop an operator on a
    developer screen with no way forward."""
    response = client.post(
        reverse("admin-login"),
        {"username": staff.phone, "password": "x"},
    )

    assert response.status_code == 302
    assert response["Location"] == "/console/"


def test_the_raw_admin_index_hands_over_to_the_console(client, staff) -> None:
    """No `?next=` survives contact with `/admin/`: signed in or not, the raw
    index is a developer screen, and staff belong in the console."""
    assert client.get("/admin/")["Location"] == "/console/"

    client.force_login(staff)
    response = client.get("/admin/")

    assert response.status_code == 302
    assert response["Location"] == "/console/"
