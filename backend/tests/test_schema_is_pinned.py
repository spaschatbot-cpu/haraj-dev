"""T621 — the schema is a file in the repository, and drifting from it fails.

Two clients are generated from `/api/schema/` and neither is written by hand:
the Flutter app (T702) and the web client (T1002). That makes the schema a
*contract*, and a contract that is recomputed on every request is one nobody can
review: a field renamed in a serializer would reach both generated clients as a
silent breaking change, discovered when a screen stopped rendering.

So the schema lives at `backend/openapi/schema.yaml`, committed. These tests say
the committed copy is what the code actually produces, and the diff a reviewer
sees in a pull request is the API change under discussion.

Regenerate with `just schema` after any change to a serializer, a view, or a
route. That is not a chore bolted on: it is the moment the API change becomes
visible to the people consuming it.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from django.core.management import call_command
from django.urls import get_resolver

BACKEND = Path(__file__).resolve().parents[1]
PINNED = BACKEND / "openapi" / "schema.yaml"


def generate(tmp_path: Path) -> str:
    """Build the schema the way CI does — validated, and warnings are failures.

    `--fail-on-warn` is the half that matters. drf-spectacular warns rather than
    errors when it cannot work out a serializer or a path parameter's type, and
    a warning there becomes `dynamic` or `Object` in the generated Dart — a
    client that compiles and carries the wrong type.
    """
    out = tmp_path / "generated.yaml"
    call_command("spectacular", "--validate", "--fail-on-warn", "--file", str(out))
    return out.read_text(encoding="utf-8")


def test_the_committed_schema_is_what_the_code_produces(tmp_path):
    """The one that fails when somebody edits an API and forgets `just schema`."""
    assert PINNED.exists(), "backend/openapi/schema.yaml is missing"

    produced = generate(tmp_path)
    committed = PINNED.read_text(encoding="utf-8")

    assert produced == committed, (
        "المخطط المرفوع لا يطابق ما يولّده الكود. "
        "شغّل `just schema` وارفع الفرق — هو تغيير العقد الذي يراجعه غيرك."
    )


def test_the_schema_builds_without_a_single_warning(tmp_path):
    """`--fail-on-warn` raises; this test exists so the failure has a name."""
    generate(tmp_path)


def test_every_api_route_reaches_the_schema(tmp_path):
    """A route that exists but is not published is a route no client can call.

    drf-spectacular quietly skips a view it cannot introspect, so an endpoint
    can ship, work in a curl, and be invisible to both generated clients. This
    counts the routes the project registers under `/api/v1/` and insists each
    one appears — the failure names the missing path rather than leaving it to
    be noticed by a screen that has nothing to call.
    """
    import yaml

    document = yaml.safe_load(generate(tmp_path))
    published = set(document.get("paths", {}))

    registered = {
        "/" + pattern.pattern._route.rstrip("$").lstrip("^")
        for pattern in _api_patterns()
    }

    missing = {
        route
        for route in registered
        if route not in published and _normalised(route) not in published
    }

    assert not missing, f"مسارات مسجَّلة ولا تظهر في المخطط: {sorted(missing)}"


def _api_patterns():
    """Every leaf URL pattern mounted under `api/v1/`, with its full route."""
    from django.urls.resolvers import URLPattern, URLResolver

    found = []

    def walk(resolver, prefix: str):
        for entry in resolver.url_patterns:
            route = prefix + str(entry.pattern)
            if isinstance(entry, URLResolver):
                walk(entry, route)
            elif isinstance(entry, URLPattern) and route.startswith("api/v1/"):
                found.append((route, entry))

    walk(get_resolver(), "")
    return [_Fake(route) for route, _ in found]


class _Fake:
    """Carries a route string in the shape the assertion above reads."""

    def __init__(self, route: str):
        self.pattern = self
        self._route = route


def _normalised(route: str) -> str:
    """Django's route language rendered in OpenAPI's.

    Two translations, and the second is the one that bites: `<int:pk>` becomes
    `{id}`, not `{pk}` — drf-spectacular renames the primary key because `id` is
    what the resource is called in its own schema, and a client generated from
    `{pk}` would carry Django's vocabulary into a public contract.
    """
    import re

    converted = re.sub(r"<[^:>]+:([^>]+)>", r"{\1}", route)
    converted = re.sub(r"<([^:>]+)>", r"{\1}", converted)
    return converted.replace("{pk}", "{id}")


@pytest.mark.parametrize(
    "path",
    [
        "/api/v1/auth/code/",
        "/api/v1/auth/verify/",
        "/api/v1/auth/phone/change/",
        "/api/v1/auth/phone/change/confirm/",
        "/api/v1/wallet/",
    ],
)
def test_the_paths_the_screens_depend_on_are_published(path, tmp_path):
    """A named sample, so a total collapse of the schema is legible in the report.

    The set-comparison above catches more, but reads as one failure; these say
    *which* screen lost its endpoint.
    """
    import yaml

    document = yaml.safe_load(PINNED.read_text(encoding="utf-8"))

    assert path in document["paths"]


def test_the_security_scheme_the_clients_need_is_declared():
    """Without it every generated client ships with no way to attach a token.

    T601 found this the hard way: the schema knew nothing about the new bearer
    authentication, so `swagger_parser` would have produced a client that could
    call every endpoint and authenticate to none of them.
    """
    import yaml

    document = yaml.safe_load(PINNED.read_text(encoding="utf-8"))
    schemes = document.get("components", {}).get("securitySchemes", {})

    assert "bearerAuth" in schemes, "المخطط لا يعرف كيف يُرفَق الرمز"
