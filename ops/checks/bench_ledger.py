"""T123 — measure the three reads that matter, on a ledger big enough to hurt.

Generates a ledger of roughly a million entries and times the queries a real
screen makes. Numbers, not opinions: the acceptance bar is a customer
statement under 200ms, and anything slower needs an index or a written reason.

Run:  cd backend && uv run python ../ops/checks/bench_ledger.py
"""

from __future__ import annotations

import os
import statistics
import sys
import time
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.dev")

import django  # noqa: E402

django.setup()

from django.contrib.auth import get_user_model  # noqa: E402
from django.db import connection, reset_queries  # noqa: E402
from django.utils import timezone  # noqa: E402

from apps.money.models import (  # noqa: E402
    Account,
    AccountKind,
    Entry,
    Transaction,
    TransactionKind,
)
from apps.money.verification import verify_ledger  # noqa: E402

# ويندوز: cp1252 لا يمثّل العربية، فجملة النجاح نفسها ترمي `UnicodeEncodeError`
# ويخرج الحارس بـ1 وهو ناجح. وحارسٌ يُبلَّغ عنه فاشلاً وهو ناجح يُطفَأ بعد
# ثالث مرة — وهذا أسوأ من حارسٍ لا يعمل، لأنه يُطفأ عن قناعة.
#
# و`hasattr` ليست حذراً زائداً: `tests/test_no_float_check.py` يستورد هذا
# الملف، وpytest يكون قد استبدل `sys.stdout` بكائن التقاطٍ بلا `reconfigure`.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

CUSTOMERS = 2_000
TRANSACTIONS_PER_CUSTOMER = 250  # 2 entries each -> ~1,000,000 entries
BATCH = 5_000


def timed(label, fn, repeats=5):
    samples = []
    for _ in range(repeats):
        reset_queries()
        started = time.perf_counter()
        result = fn()
        samples.append((time.perf_counter() - started) * 1000)
        del result
    median = statistics.median(samples)
    print(f"  {label:<46} {median:8.1f} ms   (min {min(samples):.1f})")
    return median


def build():
    """Fill the ledger. Bulk inserts only — this is a fixture, not a test of
    `post`; the posting path has its own tests and is far too slow at this
    volume to say anything useful about read performance."""
    User = get_user_model()
    print(f"building ~{CUSTOMERS * TRANSACTIONS_PER_CUSTOMER * 2:,} entries…")

    cash, _ = Account.objects.get_or_create(
        owner=None, kind=AccountKind.EXTERNAL_CASH
    )
    users = User.objects.bulk_create(
        [
            User(phone=f"9665{i:08d}", full_name=f"عميل {i}", is_active=True)
            for i in range(CUSTOMERS)
        ],
        batch_size=BATCH,
        ignore_conflicts=True,
    )
    users = list(User.objects.order_by("pk")[:CUSTOMERS])

    accounts = Account.objects.bulk_create(
        [
            Account(owner=user, kind=AccountKind.INSURANCE_FREE, balance=Decimal("0.00"))
            for user in users
        ],
        batch_size=BATCH,
        ignore_conflicts=True,
    )
    accounts = list(
        Account.objects.filter(kind=AccountKind.INSURANCE_FREE).order_by("pk")
    )

    now = timezone.now()
    amount = Decimal("100.00")
    total = 0
    for start in range(0, TRANSACTIONS_PER_CUSTOMER, 10):
        txns, entries = [], []
        for round_index in range(start, min(start + 10, TRANSACTIONS_PER_CUSTOMER)):
            for account in accounts:
                txns.append(
                    Transaction(
                        kind=TransactionKind.INSURANCE_TOPUP,
                        idempotency_key=f"bench:{account.pk}:{round_index}",
                        occurred_at=now,
                    )
                )
        txns = Transaction.objects.bulk_create(txns, batch_size=BATCH)
        for txn in txns:
            account_pk = int(txn.idempotency_key.split(":")[1])
            entries.append(Entry(transaction=txn, account_id=account_pk, amount=amount))
            entries.append(Entry(transaction=txn, account=cash, amount=-amount))
        Entry.objects.bulk_create(entries, batch_size=BATCH)
        total += len(entries)
        print(f"    {total:,} entries", end="\r")

    Account.objects.filter(kind=AccountKind.INSURANCE_FREE).update(
        balance=amount * TRANSACTIONS_PER_CUSTOMER
    )
    Account.objects.filter(pk=cash.pk).update(
        balance=-amount * TRANSACTIONS_PER_CUSTOMER * len(accounts)
    )
    print(f"\n  {Entry.objects.count():,} entries in the book")
    return accounts[len(accounts) // 2]


def main():
    if Entry.objects.count() < 500_000:
        account = build()
    else:
        account = Account.objects.filter(kind=AccountKind.INSURANCE_FREE).first()
        print(f"reusing existing ledger: {Entry.objects.count():,} entries")

    owner_id = account.owner_id
    print("\nreads:")
    statement = timed(
        "customer statement (200 most recent entries)",
        lambda: list(
            Entry.objects.filter(owner_id=owner_id)
            .select_related("transaction")
            .order_by("-id")[:200]
        ),
    )
    balance = timed(
        "one bucket balance",
        lambda: Account.objects.get(owner_id=owner_id, kind=AccountKind.INSURANCE_FREE),
    )
    page = timed(
        "transactions page (50, newest first)",
        lambda: list(Transaction.objects.order_by("-id")[:50]),
    )

    print("\nverification:")
    started = time.perf_counter()
    findings = verify_ledger()
    verify_ms = (time.perf_counter() - started) * 1000
    print(f"  verify_ledger()                                {verify_ms:8.1f} ms")
    print(f"  findings: {len(findings)}")

    print("\nversus the 200 ms bar:")
    for label, value in (
        ("statement", statement),
        ("balance", balance),
        ("page", page),
    ):
        print(f"  {label:<12} {'PASS' if value < 200 else 'SLOW'}  ({value:.1f} ms)")

    connection.close()


if __name__ == "__main__":
    main()
