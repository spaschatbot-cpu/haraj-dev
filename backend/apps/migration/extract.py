"""The only place that reads v1. T305.

One layer, because a second connection is a second chance to get the encoding
wrong — and getting it wrong here does not fail, it succeeds with the customer's
name spelled as `Ø¹Ø¨Ø¯`. Nobody notices until a person opens a screen months
later, and by then the ledger was built on those rows.

Three things hold this module together:

* **`utf8mb4`, stated in the connection and asserted in a test.** The task's own
  reason: "الأنابيب عبر `ssh → mysql` تفسد العربي؛ الاتصال المباشر بـPDO/utf8mb4
  لا". A pipe through another process inherits that process's locale; a driver
  connection carries the charset in the handshake.
* **Reads only, and it refuses to do anything else.** The real guard is the
  database grant (T301, Article D6) — this is the readable sentence in front of
  it, so a mistake is caught in review rather than by a `GRANT` that may not
  have been applied yet.
* **Off by default.** `V1_DSN` empty means no connection is attempted and the
  caller is told why. A migration layer that quietly connects to nothing and
  returns no rows reports "0 customers migrated" as a success.
"""

from __future__ import annotations

import logging
import re
from collections.abc import Iterator
from typing import Any

from django.conf import settings

log = logging.getLogger(__name__)

#: What the driver is told, in the handshake, before a byte of data moves.
CHARSET = "utf8mb4"

#: And the collation, because a server whose default is `latin1_swedish_ci`
#: will happily hand back `utf8mb4` bytes compared under the wrong rules.
COLLATION = "utf8mb4_unicode_ci"

CONNECT_TIMEOUT_SECONDS = 20

#: Statements this layer will send. Anything else is a programming error here,
#: not an access-control decision — the grant decides that.
_READ_ONLY = re.compile(r"^\s*(SELECT|SHOW|DESCRIBE|DESC|EXPLAIN)\b", re.IGNORECASE)


class V1Disabled(RuntimeError):
    """No v1 connection is configured for this environment, on purpose."""


class NotAReadOnlyStatement(RuntimeError):
    """Something tried to write through the read-only layer."""


def is_configured() -> bool:
    """Is there a v1 to read at all?

    Callers ask this rather than catching :class:`V1Disabled`, so "we cannot
    reach v1" reads differently from "we reached it and found nothing".
    """
    return bool(getattr(settings, "V1_DSN", ""))


def connection_settings() -> dict[str, Any]:
    """Every argument the driver is given — built here so a test can read it.

    Separated from :func:`connect` deliberately. The charset is the whole point
    of this module, and a value that only exists inside a function that needs a
    live server is a value no test can pin.
    """
    dsn = getattr(settings, "V1_DSN", "")
    if not dsn:
        raise V1Disabled(
            "لا اتصال بقاعدة v1 في هذه البيئة — اضبط V1_DSN. "
            "الترحيل بلا مصدرٍ يقرأه يبلّغ عن صفر صفوفٍ كأنها نجاح."
        )

    from urllib.parse import unquote, urlparse

    parts = urlparse(dsn)
    if parts.scheme not in ("mysql", "mariadb"):
        raise V1Disabled(f"V1_DSN ليس عنوان MySQL: {parts.scheme!r}")

    return {
        "host": parts.hostname or "127.0.0.1",
        "port": parts.port or 3306,
        "user": unquote(parts.username or ""),
        "password": unquote(parts.password or ""),
        "database": (parts.path or "/").lstrip("/"),
        # The three that matter, and the reason this function exists.
        "charset": CHARSET,
        "use_unicode": True,
        "connect_timeout": CONNECT_TIMEOUT_SECONDS,
        # A read that begins a transaction and never ends it holds a snapshot
        # open for the length of the migration. Autocommit on a read-only
        # account costs nothing and releases each read as it finishes.
        "autocommit": True,
    }


def connect():
    """Open the connection. Raises rather than returning a dead handle."""
    import pymysql

    kwargs = connection_settings()
    log.info(
        "v1: connecting to %s:%s/%s as %s (charset=%s)",
        kwargs["host"],
        kwargs["port"],
        kwargs["database"],
        kwargs["user"],
        kwargs["charset"],
    )
    conn = pymysql.connect(**kwargs)
    _assert_session_charset(conn)
    return conn


def _assert_session_charset(conn) -> None:
    """Ask the server what it thinks the charset is, and refuse if it disagrees.

    The handshake can be overridden by the server's own `init_connect`, and a
    connection that *asked* for utf8mb4 is not the same as one that *has* it.
    Checking costs one round trip at the start of a migration that will make
    millions, and it is the difference between finding mojibake now and finding
    it in a customer's name a month after cutover.
    """
    with conn.cursor() as cursor:
        cursor.execute("SELECT @@character_set_client, @@character_set_results")
        row = cursor.fetchone()
    if row and not all(str(value).startswith("utf8") for value in row):
        raise RuntimeError(
            f"جلسة v1 ليست utf8mb4 — العميل {row[0]!r} والنتائج {row[1]!r}. "
            "قراءةٌ بهذه الجلسة تُفسد كل اسمٍ عربي بصمت."
        )


def rows(sql: str, params: tuple = (), *, conn=None) -> Iterator[dict[str, Any]]:
    """Stream a read as dictionaries, one row at a time.

    A generator and not a list: `bids` alone is 119,985 rows and `notifications`
    half a million. Reading a table into memory to count it is how a migration
    that works on a laptop fails on the real database.
    """
    if not _READ_ONLY.match(sql):
        raise NotAReadOnlyStatement(
            f"هذه الطبقة تقرأ فقط، والعبارة تبدأ بـ{sql.split()[0]!r} — "
            "الكتابة على v1 ممنوعة (المعيار D6)"
        )

    import pymysql.cursors

    own = conn is None
    conn = conn or connect()
    try:
        with conn.cursor(pymysql.cursors.SSDictCursor) as cursor:
            cursor.execute(sql, params)
            yield from cursor
    finally:
        if own:
            conn.close()


def count(table: str, *, conn=None) -> int:
    """How many rows a table holds. Named because every builder starts here."""
    for row in rows(f"SELECT COUNT(*) AS n FROM `{_table(table)}`", conn=conn):
        return int(row["n"])
    return 0


def distinct_values(table: str, column: str, *, conn=None) -> dict[str, int]:
    """Every value in a column and how often it occurs.

    This is the answer to eight of the ten open questions in
    `specs/004-data-migration/field-map.md`. The seed committed to the
    repository is synthetic — every `status` in it is the literal `'test'` — so
    the vocabulary of the real columns cannot be read from it, only from here.
    """
    sql = (
        f"SELECT `{_column(column)}` AS value, COUNT(*) AS n "
        f"FROM `{_table(table)}` GROUP BY `{_column(column)}` ORDER BY n DESC"
    )
    return {str(row["value"]): int(row["n"]) for row in rows(sql, conn=conn)}


_IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def _table(name: str) -> str:
    return _identifier(name, "جدول")


def _column(name: str) -> str:
    return _identifier(name, "عمود")


def _identifier(name: str, kind: str) -> str:
    """Refuse anything that is not a plain identifier.

    Table and column names cannot be passed as parameters, so they are checked
    instead of escaped. The names come from our own inventory rather than from a
    request, which makes this a guard against a typo becoming a query — but a
    guard that only holds while that stays true is one worth having anyway.
    """
    if not _IDENTIFIER.match(name):
        raise ValueError(f"اسم {kind} غير صالح: {name!r}")
    return name
