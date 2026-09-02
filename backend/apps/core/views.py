"""Endpoints that belong to no domain.

Right now that is ``/health``: the answer to "which build is this, and is it
talking to anything?".
"""

from __future__ import annotations

import logging
from functools import lru_cache
from pathlib import Path

from django.conf import settings
from django.db import connection
from django.http import HttpRequest, JsonResponse
from django.views.decorators.cache import never_cache

log = logging.getLogger(__name__)

#: Short enough that a load balancer's own timeout never fires first.
REDIS_TIMEOUT_SECONDS = 1.0


def _check_database() -> tuple[bool, str]:
    """Can we actually reach PostgreSQL, right now?

    A real round trip, not ``connection.is_usable()``: a pooled connection can
    look healthy while the server behind it is gone.
    """
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
    except Exception as exc:
        # Never the exception's text: psycopg puts the whole DSN — password
        # included — into some connection errors, and this endpoint is public.
        log.warning("health: database unreachable: %s", exc)
        return False, "unreachable"
    return True, "ok"


def _check_redis() -> tuple[bool, str]:
    """Is Redis answering?

    Redis is deliberately not running in this deployment, so a failure here is
    reported and does **not** change the endpoint's status code. Only the
    database can make this endpoint say 503, because only the database being
    gone means no request can be served at all. A caller that needs Redis reads
    ``checks.redis.ok``; making /health fail on it would take the whole service
    out of a load balancer over a queue that nothing is currently using.
    """
    url = getattr(settings, "CELERY_BROKER_URL", "")
    if not url.startswith(("redis://", "rediss://", "unix://")):
        return False, "not_configured"
    try:
        import redis

        client = redis.from_url(
            url,
            socket_connect_timeout=REDIS_TIMEOUT_SECONDS,
            socket_timeout=REDIS_TIMEOUT_SECONDS,
        )
        client.ping()
    except Exception as exc:
        # Same reasoning as the database: the URL can carry a password.
        log.info("health: redis unreachable: %s", exc)
        return False, "unreachable"
    return True, "ok"


@lru_cache(maxsize=1)
def commit_hash() -> str:
    """The build's commit, from the environment or, failing that, from git.

    Production stamps ``GIT_COMMIT`` at build time; the git fallback is what
    makes the endpoint useful on a developer's machine, where nobody stamps
    anything. Any failure yields ``"unknown"`` — an unlabelled build is a
    nuisance, an exception on the health endpoint is an outage.
    """
    stamped = getattr(settings, "GIT_COMMIT", "")
    if stamped:
        return stamped[:40]
    try:
        return _read_git_head(Path(settings.BASE_DIR).parent)[:40] or "unknown"
    except Exception:  # pragma: no cover - depends on the checkout's shape
        return "unknown"


def _read_git_head(repo_root: Path) -> str:
    """Resolve HEAD without shelling out to git, worktrees included."""
    dot_git = repo_root / ".git"
    if dot_git.is_file():
        # A linked worktree: the file points at the real git directory.
        dot_git = Path(dot_git.read_text(encoding="utf-8").split(":", 1)[1].strip())
    if not dot_git.is_dir():
        return ""

    head = (dot_git / "HEAD").read_text(encoding="utf-8").strip()
    if not head.startswith("ref:"):
        return head

    ref = head.split(":", 1)[1].strip()
    # A worktree keeps its own HEAD but shares refs with the main checkout.
    common = dot_git
    commondir = dot_git / "commondir"
    if commondir.exists():
        common = (dot_git / commondir.read_text(encoding="utf-8").strip()).resolve()

    for base in (dot_git, common):
        loose = base / ref
        if loose.exists():
            return loose.read_text(encoding="utf-8").strip()
        packed = base / "packed-refs"
        if packed.exists():
            for line in packed.read_text(encoding="utf-8").splitlines():
                if line.endswith(f" {ref}"):
                    return line.split(" ", 1)[0]
    return ""


@never_cache
def health(request: HttpRequest) -> JsonResponse:
    """Which environment, which build, and what it can reach.

    Deliberately a plain Django view: it must answer while DRF's authentication,
    throttling and renderers are all irrelevant, and it must answer to an
    unauthenticated load balancer. It returns 503 only when the database is
    gone — see :func:`_check_redis` for why Redis does not get a vote.
    """
    database_ok, database_reason = _check_database()
    redis_ok, redis_reason = _check_redis()

    if not database_ok:
        overall = "down"
    elif not redis_ok:
        overall = "degraded"
    else:
        overall = "ok"

    body = {
        "status": overall,
        "environment": settings.ENVIRONMENT_NAME,
        "commit": commit_hash(),
        "checks": {
            "database": {"ok": database_ok, "reason": database_reason},
            "redis": {"ok": redis_ok, "reason": redis_reason},
        },
    }
    return JsonResponse(body, status=200 if database_ok else 503)
