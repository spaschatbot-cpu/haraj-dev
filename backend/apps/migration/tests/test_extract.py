"""T305 — one layer reads v1, and Arabic survives it.

The failure this guards against does not raise. A connection negotiated in the
wrong charset returns rows, and the rows look like rows — `عبد الله` arrives as
`Ø¹Ø¨Ø¯ Ø§Ù„Ù„Ù‡`, the builder writes it, the ledger is built on top of it, and
somebody notices a month after cutover when a customer opens their own name.

The task states the mechanism: "الأنابيب عبر `ssh → mysql` تفسد العربي؛ الاتصال
المباشر بـPDO/utf8mb4 لا". A pipe through another process inherits that
process's locale. A driver connection carries the charset in its handshake.

**What is and is not proven here.** There is no MySQL server in this
environment, so the live half — that a real v1 hands these bytes back intact —
is not proven and is not claimed. What is proven is everything that does not
need a server: that the charset is stated in the connection, that the session
is checked against the server's own answer before a byte is read, that Arabic
survives the layer's own decoding path, and that nothing but a read can be sent
through it. The remainder waits on T301.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from django.test import override_settings

from apps.migration import extract

DSN = "mysql://reader:s3cret@10.0.0.5:3306/hara_clone_v1"

#: Copied out of the committed snapshot, not invented here. If the seed changes
#: shape, `test_the_snapshot_still_carries_arabic` fails and says so.
SEED = (
    Path(__file__).resolve().parents[3].parent
    / "specs"
    / "004-data-migration"
    / "v1-seed.sql"
)


# ---------------------------------------------------------------------------
# Off by default, and it says so
# ---------------------------------------------------------------------------


@override_settings(V1_DSN="")
def test_no_dsn_means_no_connection_and_a_reason():
    """A migration that connects to nothing must not look like one that ran."""
    assert extract.is_configured() is False

    with pytest.raises(extract.V1Disabled) as raised:
        extract.connection_settings()

    assert "V1_DSN" in str(raised.value)
    assert "صفر صفوف" in str(raised.value), "الرسالة لا تقول لماذا يهمّ الفارغ"


@override_settings(V1_DSN=DSN)
def test_a_dsn_means_configured():
    assert extract.is_configured() is True


@override_settings(V1_DSN="postgres://x:y@h/db")
def test_a_dsn_that_is_not_mysql_is_refused():
    with pytest.raises(extract.V1Disabled):
        extract.connection_settings()


# ---------------------------------------------------------------------------
# The charset — the whole reason this module exists
# ---------------------------------------------------------------------------


@override_settings(V1_DSN=DSN)
def test_the_connection_states_utf8mb4():
    """Asserted on the arguments, so it holds without a server to ask."""
    kwargs = extract.connection_settings()

    assert kwargs["charset"] == "utf8mb4"
    assert kwargs["use_unicode"] is True


@override_settings(V1_DSN=DSN)
def test_the_dsn_is_read_whole():
    kwargs = extract.connection_settings()

    assert kwargs["host"] == "10.0.0.5"
    assert kwargs["port"] == 3306
    assert kwargs["user"] == "reader"
    assert kwargs["password"] == "s3cret"
    assert kwargs["database"] == "hara_clone_v1"


@override_settings(V1_DSN=DSN)
def test_reads_do_not_hold_a_transaction_open():
    """A migration that never commits holds one snapshot for its whole run."""
    assert extract.connection_settings()["autocommit"] is True


class FakeCursor:
    def __init__(self, rows, answers=None):
        self._rows = rows
        self._answers = answers or ("utf8mb4", "utf8mb4")
        self.executed = []

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def execute(self, sql, params=()):
        self.executed.append((sql, params))

    def fetchone(self):
        return self._answers

    def __iter__(self):
        return iter(self._rows)


class FakeConnection:
    def __init__(self, rows=(), answers=None):
        self.cursor_made = FakeCursor(list(rows), answers)
        self.closed = False

    def cursor(self, *args, **kwargs):
        return self.cursor_made

    def close(self):
        self.closed = True


def test_a_session_that_is_not_utf8_is_refused():
    """Asking for utf8mb4 is not the same as having it — `init_connect` can win."""
    conn = FakeConnection(answers=("latin1", "latin1"))

    with pytest.raises(RuntimeError) as raised:
        extract._assert_session_charset(conn)

    assert "utf8mb4" in str(raised.value)
    assert "بصمت" in str(raised.value), "الرسالة لا تقول أن العطل صامت"


def test_a_utf8_session_passes():
    extract._assert_session_charset(FakeConnection(answers=("utf8mb4", "utf8mb4")))


# ---------------------------------------------------------------------------
# Arabic through the layer
# ---------------------------------------------------------------------------


ARABIC = [
    "بيانات اختبار مُصطنَعة (customer_links)",
    "تجريبي 1 — auction_vehicles",
    "عبد الله بن عبد العزيز",
    "شركة الحراج المتّحدة للمزادات",
]


@pytest.mark.parametrize("name", ARABIC)
def test_arabic_arrives_whole(name):
    """Through `rows`, character for character — including the tatweel and shadda."""
    conn = FakeConnection(rows=[{"arabic_name": name}])

    got = list(extract.rows("SELECT arabic_name FROM userss", conn=conn))

    assert got == [{"arabic_name": name}]
    assert "Ø" not in got[0]["arabic_name"], "mojibake — قُرئت utf8 على أنها latin1"


def test_the_classic_mojibake_is_what_this_test_would_catch():
    """The failure named, so the assertion above is read as more than a tautology.

    This is what `عبد` becomes when utf8 bytes are decoded as latin1. It does
    not raise anywhere; it just becomes the customer's name.
    """
    broken = "عبد".encode().decode("latin1")

    assert broken == "Ø¹Ø¨Ø¯"
    assert broken != "عبد"


def test_the_snapshot_still_carries_arabic():
    """The strings above are copied from the seed, so the seed must still have them."""
    assert SEED.exists(), f"اللقطة غير موجودة: {SEED}"
    text = SEED.read_text(encoding="utf-8")

    assert "بيانات اختبار مُصطنَعة (customer_links)" in text
    assert "تجريبي 1 — auction_vehicles" in text


# ---------------------------------------------------------------------------
# Reads only
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "sql",
    [
        "UPDATE userss SET wallet = 0",
        "DELETE FROM bids",
        "INSERT INTO userss (phone) VALUES ('1')",
        "DROP TABLE invoices_odoo",
        "TRUNCATE bids",
        "  update userss set wallet = 0",
    ],
)
def test_a_write_is_refused(sql):
    """Criterion D6. The grant is the guard; this is the sentence in front of it."""
    conn = FakeConnection()

    with pytest.raises(extract.NotAReadOnlyStatement):
        list(extract.rows(sql, conn=conn))

    assert conn.cursor_made.executed == [], "وصلت العبارة إلى الخادم"


@pytest.mark.parametrize(
    "sql",
    ["SELECT 1", "  select * from userss", "SHOW TABLES", "DESCRIBE userss"],
)
def test_a_read_goes_through(sql):
    conn = FakeConnection(rows=[{"n": 1}])

    list(extract.rows(sql, conn=conn))

    assert conn.cursor_made.executed, "لم تصل القراءة"


# ---------------------------------------------------------------------------
# Identifiers, and the helper the field map needs
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "name", ["userss; DROP TABLE x", "user-ss", "`userss`", "", "1users"]
)
def test_a_bad_identifier_is_refused(name):
    """Names cannot be parameters, so they are checked rather than escaped."""
    with pytest.raises(ValueError):
        extract._table(name)


def test_counting_asks_for_a_count():
    conn = FakeConnection(rows=[{"n": 44039}])

    assert extract.count("userss", conn=conn) == 44039
    sql = conn.cursor_made.executed[0][0]
    assert "COUNT(*)" in sql
    assert "`userss`" in sql


def test_distinct_values_answers_the_field_maps_open_questions():
    """Eight of the ten questions in `field-map.md` are one GROUP BY each.

    The committed seed cannot answer them — every `status` in it is the literal
    `'test'` — so this is the shape of the query that will, the day T301 opens.
    """
    conn = FakeConnection(
        rows=[
            {"value": "active", "n": 8123},
            {"value": "ended", "n": 4102},
            {"value": "relater", "n": 3},
        ]
    )

    counts = extract.distinct_values("auctions", "status", conn=conn)

    assert counts == {"active": 8123, "ended": 4102, "relater": 3}
    sql = conn.cursor_made.executed[0][0]
    assert "GROUP BY" in sql
    # Ordered by frequency, because "a value on three rows" and "a value on four
    # thousand" are a fold and a decision for the owner — and the reader needs
    # to see which is which without counting.
    assert "ORDER BY n DESC" in sql
