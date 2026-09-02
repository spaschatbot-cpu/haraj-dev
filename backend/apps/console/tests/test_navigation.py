"""T802 and T804 — one list, and no link written by hand.

**I2 is checked by walking, not by reading.** For each role this signs in, asks
the sidebar what it offers, then opens *every* page in the registry and records
which ones answer. The two sets must be equal. A page guarded by one capability
and listed under another fails here, and so does a page in the registry that
nobody can open.

That equivalence is what v1 lacked: the menu was one list and the access rules
were another, so a page added to the second and forgotten in the first was
invisible to the people allowed to use it, and a page added to the first and
forgotten in the second was a link everybody could see and nobody could open.
Both happened.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest
from django.urls import reverse

from apps.accounts.models import StaffGrant, User
from apps.console.navigation import PAGES, capability_for, pages_for, sidebar_for
from apps.core.permissions import Capability, Role

pytestmark = pytest.mark.django_db

CHECKS = Path(__file__).resolve().parents[4] / "ops" / "checks"
BACKEND = Path(__file__).resolve().parents[3]


def load(name: str):
    spec = importlib.util.spec_from_file_location(name, CHECKS / f"{name}.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def staff(role: str, phone: str = "966501111111") -> User:
    user = User.objects.create_user(
        phone=phone, full_name="موظف", password="console-pass"
    )
    user.is_staff = True
    user.console_role = role
    user.save(update_fields=["is_staff", "console_role"])
    return user


def signed_in(client, user: User):
    client.force_login(user)
    return client


# ---------------------------------------------------------------------------
# I2 — the sidebar and the guards are the same list
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "role", [Role.OWNER, Role.OPERATIONS, Role.FINANCE, Role.SUPPORT]
)
def test_the_sidebar_offers_exactly_what_the_role_can_open(client, role):
    """The acceptance criterion, walked rather than asserted from the registry."""
    user = staff(role)
    signed_in(client, user)

    offered = {page.url_name for page in pages_for(user)}

    opens = set()
    for page in PAGES:
        response = client.get(reverse(page.url_name))
        if response.status_code == 200:
            opens.add(page.url_name)

    assert offered == opens, (
        f"القائمة تعرض {sorted(offered)} والصفحات التي تفتح {sorted(opens)}"
    )


def test_a_page_the_role_cannot_open_is_a_403_not_a_blank_page(client):
    """Refused loudly. A page that renders empty is how v1 shipped a broken one."""
    user = staff(Role.OPERATIONS)
    StaffGrant.objects.create(
        user=user,
        capability=Capability.DIAGNOSTICS_VIEW,
        granted=False,
        reason="تحت المراجعة",
    )
    signed_in(client, user)

    response = client.get(reverse("console:why-no-bid"))

    assert response.status_code == 403


def test_a_customer_cannot_reach_the_console_at_all(client):
    customer = User.objects.create_user(
        phone="966509999999", full_name="عميل", password="x"
    )
    signed_in(client, customer)

    assert client.get(reverse("console:home")).status_code == 403


def test_an_anonymous_visitor_is_sent_to_sign_in(client):
    response = client.get(reverse("console:home"))

    assert response.status_code in (302, 403)


def test_every_page_in_the_registry_has_a_capability():
    """A page with no capability is a page with no guard."""
    for page in PAGES:
        assert page.capability, f"{page.url_name} بلا صلاحية"
        assert capability_for(page.url_name) == page.capability


def test_every_page_in_the_registry_actually_resolves():
    """A registry row naming a url that does not exist is a sidebar 500."""
    for page in PAGES:
        assert reverse(page.url_name)


def test_an_empty_section_is_not_shown(client):
    """A heading with nothing under it is a promise the reader cannot use."""
    user = staff(Role.OPERATIONS)
    StaffGrant.objects.create(
        user=user,
        capability=Capability.DIAGNOSTICS_VIEW,
        granted=False,
        reason="لا يحتاجها",
    )

    labels = {section["label"] for section in sidebar_for(user)}

    assert "التشخيص" not in labels


def test_the_rendered_sidebar_shows_the_pages_the_person_has(client):
    """I6 in miniature: the page is read, not merely counted as a 200."""
    user = staff(Role.SUPPORT)
    signed_in(client, user)

    body = client.get(reverse("console:home")).content.decode()

    assert "ليه ما يقدرش يزايد؟" in body
    assert reverse("console:why-no-bid") in body


def test_the_environment_is_named_on_every_page(client, settings):
    """Article 5-6, so nobody acts on production thinking it is staging."""
    signed_in(client, staff(Role.OWNER))

    body = client.get(reverse("console:home")).content.decode()

    assert settings.ENVIRONMENT_NAME in body


# ---------------------------------------------------------------------------
# T804 — the prefix is a setting, so no link may be a literal
# ---------------------------------------------------------------------------


def test_the_console_lives_under_app_base(settings):
    assert reverse("console:home") == f"/{settings.APP_BASE}/"


def test_no_link_in_the_tree_is_written_by_hand():
    assert load("console_urls_are_named").violations() == []


HAND_WRITTEN_HREF = """
<a href="/console/vehicles">المركبات</a>
"""

HAND_WRITTEN_ACTION = """
<form action="/admin2/save" method="post"></form>
"""

RELATIVE_PATH = """
<a href="/some/other/page">صفحة</a>
"""


@pytest.mark.parametrize(
    "markup",
    [
        pytest.param(HAND_WRITTEN_HREF, id="an href to a console path"),
        pytest.param(HAND_WRITTEN_ACTION, id="a form posting to a v1 panel path"),
        pytest.param(RELATIVE_PATH, id="any absolute path at all"),
    ],
)
def test_the_check_speaks_on_a_hand_written_link(tmp_path: Path, markup):
    (tmp_path / "page.html").write_text(markup, encoding="utf-8")

    found = load("console_urls_are_named").violations(templates=tmp_path, python=[])

    assert found, "الفحص سكت عن رابط مكتوب بيده"


PYTHON_PATH_LITERAL = """
def go():
    return redirect("/console/home")
"""


def test_the_check_speaks_on_a_python_path_literal(tmp_path: Path):
    (tmp_path / "views.py").write_text(PYTHON_PATH_LITERAL, encoding="utf-8")

    found = load("console_urls_are_named").violations(
        templates=tmp_path / "nothing", python=[tmp_path]
    )

    assert found


@pytest.mark.parametrize(
    "markup",
    [
        pytest.param("<a href=\"{% url 'console:home' %}\">x</a>", id="a url tag"),
        pytest.param('<a href="{{ next }}">x</a>', id="a variable"),
        pytest.param('<a href="#top">x</a>', id="a fragment"),
        pytest.param('<a href="https://example.com">x</a>', id="an external link"),
    ],
)
def test_the_check_is_quiet_on_a_link_that_follows_the_prefix(tmp_path: Path, markup):
    """A check that fires on correct code is one people switch off."""
    (tmp_path / "page.html").write_text(markup, encoding="utf-8")

    assert load("console_urls_are_named").violations(templates=tmp_path, python=[]) == []
