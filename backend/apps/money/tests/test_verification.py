"""T119–T120 — the ledger checking itself, and the command that runs it.

Every check gets two tests: one proving it is quiet on a healthy ledger, and
one that deliberately corrupts exactly the thing it watches and proves it
speaks up. A check nobody has seen fail is a check nobody has tested.
"""

import ast
from decimal import Decimal
from io import StringIO
from pathlib import Path

import pytest
from django.core.management import call_command
from django.utils import timezone

from apps.money import services
from apps.money.models import (
    Account,
    AccountKind,
    Entry,
    Hold,
    HoldReason,
    HoldState,
    Invoice,
    InvoiceState,
)
from apps.money.verification import (
    check_cached_balances,
    check_holds_explain_buckets,
    check_locked_not_above_dues,
    check_transactions_balance,
    verify_ledger,
)

pytestmark = pytest.mark.django_db

TEN_K = Decimal("10000.00")


def fund(user, amount=TEN_K):
    return services.deposit_insurance(
        user=user, amount=amount, source="cash", reference=f"SEED:{user.pk}"
    )


# ---------------------------------------------------------------------------
# The independence rule itself
# ---------------------------------------------------------------------------


def test_verification_imports_nothing_from_services():
    """The rule that makes the other tests in this file mean anything.

    If verification borrowed the writer's helpers, a bug in the writer would
    be reproduced identically in the check, and the two would agree while both
    were wrong. Parsing the module is the only way to assert this stays true
    after someone adds a convenience import in a hurry.
    """
    source = Path(services.__file__).parent / "verification.py"
    tree = ast.parse(source.read_text(encoding="utf-8"))

    imported: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            imported.append(node.module)
        elif isinstance(node, ast.Import):
            imported.extend(alias.name for alias in node.names)

    offenders = [name for name in imported if "services" in name]
    assert offenders == [], f"verification.py must not import services: {offenders}"


# ---------------------------------------------------------------------------
# Check 1 — every transaction sums to zero
# ---------------------------------------------------------------------------


class TestTransactionsBalance:
    def test_quiet_on_a_healthy_ledger(self, customer):
        fund(customer)

        assert check_transactions_balance() == []

    def test_it_catches_an_entry_added_behind_the_service(self, customer):
        """Somebody inserts a leg straight into the table — a migration
        script, a stray admin action, the thing Article 1-2 forbids."""
        txn = fund(customer)
        Entry.objects.create(
            transaction=txn,
            account=services.system_account(AccountKind.REVENUE),
            amount=Decimal("5.00"),
        )

        findings = check_transactions_balance()

        assert len(findings) == 1
        assert findings[0].check == "balanced_transactions"
        assert "5.00" in findings[0].detail


# ---------------------------------------------------------------------------
# Check 2 — the cached balance equals the entries
# ---------------------------------------------------------------------------


class TestCachedBalances:
    def test_quiet_on_a_healthy_ledger(self, customer):
        fund(customer)

        assert check_cached_balances() == []

    def test_it_catches_a_tampered_balance(self, customer):
        """The cache is adjusted by delta under a lock, which is fast and
        safe — but only because this check re-derives it from the entries.
        Remove this and the design becomes v1's blind `balance = balance + x`.
        """
        fund(customer)
        account = services.account_for(customer, AccountKind.INSURANCE_FREE)
        Account.objects.filter(pk=account.pk).update(balance=Decimal("99999.00"))

        findings = check_cached_balances()

        assert len(findings) == 1
        assert findings[0].check == "cached_balance"
        assert "99999.00" in findings[0].detail
        assert "10000.00" in findings[0].detail


# ---------------------------------------------------------------------------
# Check 3 — held and locked money is explained by holds
# ---------------------------------------------------------------------------


class TestHoldsExplainBuckets:
    def test_quiet_on_a_healthy_ledger(self, customer, auction):
        fund(customer)
        services.hold_for_auction(user=customer, auction=auction, amount=TEN_K)

        assert check_holds_explain_buckets() == []

    def test_it_catches_held_money_with_no_hold_naming_it(self, customer, auction):
        """Reserved money nobody can explain is money nobody can release."""
        fund(customer)
        hold = services.hold_for_auction(user=customer, auction=auction, amount=TEN_K)
        Hold.objects.filter(pk=hold.pk).update(state=HoldState.RELEASED)

        findings = check_holds_explain_buckets()

        assert len(findings) == 1
        assert findings[0].check == "holds_explain_bucket"
        assert "10000.00" in findings[0].detail

    def test_it_catches_a_hold_claiming_money_that_is_not_there(
        self, customer, auction, other_auction
    ):
        """The mirror image. Checking only one direction leaves the other
        open, and this is the direction F-003 produced: a hold row claiming a
        deposit that never left `insurance_free`."""
        fund(customer)
        first = services.hold_for_auction(user=customer, auction=auction, amount=TEN_K)
        Hold.objects.create(
            owner=customer,
            auction=other_auction,
            amount=TEN_K,
            reason=HoldReason.BIDDING,
            created_by_transaction=first.created_by_transaction,
        )

        findings = check_holds_explain_buckets()

        assert findings != []
        assert findings[0].check == "holds_explain_bucket"


# ---------------------------------------------------------------------------
# Check 4 — locked insurance never exceeds the debt
# ---------------------------------------------------------------------------


class TestLockedNotAboveDues:
    @pytest.fixture
    def invoice(self, customer, vehicle):
        return Invoice.objects.create(
            customer=customer,
            number="INV/V/0001",
            amount=Decimal("7000.00"),
            vehicle=vehicle,
            state=InvoiceState.OPEN,
            issued_at=timezone.now(),
        )

    def test_quiet_when_the_lock_matches_the_debt(self, customer, invoice):
        fund(customer)
        services.lock_for_invoice(user=customer, invoice=invoice)

        assert check_locked_not_above_dues() == []

    def test_it_catches_a_lock_larger_than_the_debt(self, customer, invoice):
        """A lock is a guarantee, not a penalty. Holding more than is owed is
        a refund the customer was entitled to and did not get."""
        fund(customer)
        services.lock_for_invoice(user=customer, invoice=invoice)
        invoice.amount = Decimal("1000.00")
        invoice.save(update_fields=["amount"])

        findings = check_locked_not_above_dues()

        assert len(findings) == 1
        assert findings[0].check == "locked_not_above_dues"
        assert "7000.00" in findings[0].detail
        assert "1000.00" in findings[0].detail

    def test_a_cancelled_invoice_stops_justifying_a_lock(self, customer, invoice):
        fund(customer)
        services.lock_for_invoice(user=customer, invoice=invoice)
        invoice.state = InvoiceState.CANCELLED
        invoice.save(update_fields=["state"])

        findings = check_locked_not_above_dues()

        assert len(findings) == 1


# ---------------------------------------------------------------------------
# T120 — the management command
# ---------------------------------------------------------------------------


class TestVerifyLedgerCommand:
    def test_a_clean_ledger_exits_zero(self, customer, auction):
        fund(customer)
        services.hold_for_auction(user=customer, auction=auction, amount=TEN_K)
        out = StringIO()

        call_command("verify_ledger", stdout=out)

        assert "نظيف" in out.getvalue()

    def test_a_dirty_ledger_exits_non_zero_and_names_the_account(self, customer):
        """The exit code is what makes this usable in CI and in a cron. A
        report nobody reads and a job that always succeeds are the same thing.
        """
        fund(customer)
        account = services.account_for(customer, AccountKind.INSURANCE_FREE)
        Account.objects.filter(pk=account.pk).update(balance=Decimal("1.00"))
        out, err = StringIO(), StringIO()

        with pytest.raises(SystemExit) as exited:
            call_command("verify_ledger", stdout=out, stderr=err)

        assert exited.value.code != 0
        report = out.getvalue() + err.getvalue()
        assert "cached_balance" in report
        assert "insurance_free" in report
        assert "10000.00" in report


def test_verify_ledger_runs_all_four_checks(customer):
    fund(customer)

    assert verify_ledger() == []
