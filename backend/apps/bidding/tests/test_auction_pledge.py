"""HR-01 — one deposit per auction, and it is the auction's own.

Two failures, one cause. Winning locked insurance **per invoice** out of
``insurance_free``, and after settlement a winner's deposit is not in
``insurance_free`` — it is in ``insurance_held``, where their own bid put it.

* A winner who deposited exactly what the auction asked had nothing free left,
  so ``lock_for_invoice`` refused and **no invoice could be issued at all**.
  One winner, one car, and the platform could not bill them.
* A winner of two cars in one auction was asked for two deposits. That is v1's
  double-pledge incident verbatim: 20,000 pinned against one purchase, the
  customer's available balance zero, and their bidding refused though they had
  paid in full.

Neither was caught because ``a_bidder()`` in ``test_settlement.py`` funds every
bidder with 50,000 while the auction asks 10,000 — so forty thousand stayed
free and the per-invoice lock always found something to take. **Every amount in
this module is the production amount**: the deposit is ten thousand exactly
(``PHASE_02`` §1-1), which is what a real bidder holds.

The rule (``PHASE_02`` §1-3): "one deposit in ``held`` covers all of an
auction's cars. Winning two pledges one deposit. Paying the first invoice does
not release it; it is released when every invoice of that auction is paid."
"""

from __future__ import annotations

from decimal import Decimal

import pytest
from django.utils import timezone

from apps.auctions.models import Auction, Vehicle
from apps.auctions.states import AuctionState, VehicleState
from apps.bidding import services as bidding
from apps.bidding import settlement
from apps.money import services as money
from apps.money.models import AccountKind, Hold, HoldReason, HoldState, InvoiceState
from apps.money.verification import verify_ledger

pytestmark = pytest.mark.django_db

#: What the auction asks, and what a real bidder deposits. Not a round number
#: picked for a test — it is the rule.
DEPOSIT = Decimal("10000.00")
NOTHING = Decimal("0.00")


@pytest.fixture
def auction(db) -> Auction:
    now = timezone.now()
    return Auction.objects.create(
        number=910,
        title="مزاد الرهن",
        starts_at=now - timezone.timedelta(hours=2),
        ends_at=now + timezone.timedelta(hours=1),
        state=AuctionState.LIVE,
        deposit_required=DEPOSIT,
    )


def a_car(auction: Auction, lot: int, reserve: str = "40000.00") -> Vehicle:
    return Vehicle.objects.create(
        auction=auction,
        lot_number=lot,
        make="تويوتا",
        model="كامري",
        year=2020,
        state=VehicleState.LISTED,
        reserve_price=Decimal(reserve),
    )


def a_bidder(django_user_model, phone: str, funds: Decimal = DEPOSIT):
    """A bidder funded with **exactly** the deposit, as production bidders are."""
    user = django_user_model.objects.create_user(
        phone=phone, full_name="مزايد", national_id=phone[-10:]
    )
    user.phone_verified_at = timezone.now()
    user.save(update_fields=["phone_verified_at"])
    money.deposit_insurance(
        user=user, amount=funds, source="cash", reference=f"seed/{phone}"
    )
    return user


def buckets(user) -> dict[str, Decimal]:
    return {
        "free": money.account_for(user, AccountKind.INSURANCE_FREE).balance,
        "held": money.account_for(user, AccountKind.INSURANCE_HELD).balance,
        "locked": money.account_for(user, AccountKind.INSURANCE_LOCKED).balance,
    }


def pledges(user, auction) -> list[Hold]:
    return list(
        Hold.objects.filter(
            owner=user, auction=auction, state=HoldState.ACTIVE, reason=HoldReason.DUES
        )
    )


def win(user, car, amount: str) -> None:
    bidding.place_bid(user=user, vehicle=car, amount=Decimal(amount))


# ---------------------------------------------------------------------------
# The winner who deposited exactly what was asked
# ---------------------------------------------------------------------------


def test_a_winner_with_exactly_the_required_deposit_can_be_invoiced(
    auction, django_user_model
):
    """The defect, at the amount it happens at.

    Before HR-01 this raised ``MoneyError: لا يوجد تأمين متاح لقفله`` — with
    available 0.00 — and the sale had no invoice at all.
    """
    car = a_car(auction, 1)
    winner = a_bidder(django_user_model, "966501111111")

    win(winner, car, "70000.00")
    settlement.settle_auction(auction)
    car.refresh_from_db()
    assert buckets(winner) == {"free": NOTHING, "held": DEPOSIT, "locked": NOTHING}

    invoice = settlement.invoice_award(car)

    assert invoice.state == InvoiceState.OPEN
    # The deposit did not go out and come back; it moved across, in place.
    assert buckets(winner) == {"free": NOTHING, "held": NOTHING, "locked": DEPOSIT}
    assert verify_ledger() == []


def test_the_pledge_is_the_same_row_the_bid_created(auction, django_user_model):
    """Re-purposed, not released and re-taken — so no free moment exists."""
    car = a_car(auction, 1)
    winner = a_bidder(django_user_model, "966501111111")
    win(winner, car, "70000.00")
    hold = Hold.objects.get(owner=winner, auction=auction)

    settlement.settle_auction(auction)
    car.refresh_from_db()
    settlement.invoice_award(car)

    hold.refresh_from_db()
    assert hold.state == HoldState.ACTIVE
    assert hold.reason == HoldReason.DUES
    assert hold.auction_id == auction.pk, "الرهن يبقى يسمّي مزاده"
    assert Hold.objects.filter(owner=winner, auction=auction).count() == 1


# ---------------------------------------------------------------------------
# The winner of two cars — one deposit, not two
# ---------------------------------------------------------------------------


def test_winning_two_cars_in_one_auction_pledges_one_deposit(auction, django_user_model):
    """v1's double-pledge incident, refused by construction.

    Asking a second deposit is what left a customer who had paid in full with
    an available balance of zero, and barred from bidding.
    """
    first, second = a_car(auction, 1), a_car(auction, 2, reserve="60000.00")
    winner = a_bidder(django_user_model, "966501111111")

    win(winner, first, "70000.00")
    win(winner, second, "80000.00")
    settlement.settle_auction(auction)

    for car in (first, second):
        car.refresh_from_db()
        settlement.invoice_award(car)

    assert len(pledges(winner, auction)) == 1, "وديعتان لمزاد واحد"
    assert buckets(winner)["locked"] == DEPOSIT, "رُهن أكثر من وديعة واحدة"
    assert verify_ledger() == []


def test_paying_the_first_invoice_does_not_release_the_pledge(auction, django_user_model):
    """The rule's own sentence, asserted.

    Releasing here is the 1004 incident: a winner's deposit handed back while
    another of their cars is still unpaid, and the platform holding nothing.
    """
    first, second = a_car(auction, 1), a_car(auction, 2, reserve="60000.00")
    winner = a_bidder(django_user_model, "966501111111")
    win(winner, first, "70000.00")
    win(winner, second, "80000.00")
    settlement.settle_auction(auction)
    first.refresh_from_db()
    second.refresh_from_db()
    invoice_one = settlement.invoice_award(first)
    settlement.invoice_award(second)

    money.record_payment(
        invoice=invoice_one,
        amount=invoice_one.amount,
        source="cash",
        reference="pay/one",
    )

    invoice_one.refresh_from_db()
    assert invoice_one.state == InvoiceState.PAID
    assert pledges(winner, auction), "أُفرج عن الرهن وفاتورة أخرى قائمة"
    assert buckets(winner)["free"] == NOTHING
    assert verify_ledger() == []


def test_paying_the_last_invoice_releases_the_pledge(auction, django_user_model):
    """And it does come back — the deposit is a guarantee, not a fee."""
    first, second = a_car(auction, 1), a_car(auction, 2, reserve="60000.00")
    winner = a_bidder(django_user_model, "966501111111")
    win(winner, first, "70000.00")
    win(winner, second, "80000.00")
    settlement.settle_auction(auction)
    first.refresh_from_db()
    second.refresh_from_db()
    invoices = [settlement.invoice_award(first), settlement.invoice_award(second)]

    for invoice in invoices:
        money.record_payment(
            invoice=invoice,
            amount=invoice.amount,
            source="cash",
            reference=f"pay/{invoice.pk}",
        )

    assert pledges(winner, auction) == []
    assert buckets(winner) == {"free": DEPOSIT, "held": NOTHING, "locked": NOTHING}
    assert verify_ledger() == []


# ---------------------------------------------------------------------------
# HR-01ب — التجهيزة لا تعود إلى وسادةٍ لا يملكها مزايد
# ---------------------------------------------------------------------------


def test_no_settlement_fixture_funds_a_bidder_above_the_deposit():
    """كل تجهيزةٍ تمرّ بالفوترة تودع مقدار الوديعة، لا أكثر.

    هذا الحارس مكتوبٌ عن عطلٍ وقع، لا احتياطاً. كانت ``a_bidder()`` في
    ``test_settlement.py`` تودع خمسين ألفاً والمزاد يطلب عشرة، فتبقى أربعون
    ألفاً حرّة بعد حجز المزايدة — ووسادةٌ بهذا الحجم تجعل ``lock_for_invoice``
    تجد ما تأخذه دائماً. فمرّت الحزمة كلّها خضراء على HR-01: فائزٌ أودع ما
    طُلب منه بالضبط لا تصدر له فاتورة أصلاً.

    **الوسادة لا تُنتج فشلاً، إنما تُخفيه** — ولذلك لا يمسكها مراجعٌ يقرأ
    التغيير، ولا اختبارٌ يفحص سلوكاً. تُمسك هنا وحدها: بقراءة الملفات التي
    تمرّ بالفوترة، والبحث عن إيداعٍ يتجاوز الوديعة.

    والاستثناء ممكن — بوسيطٍ صريح ``funds=`` عند موضع النداء، حيث يراه القارئ
    ويسأل عنه. الممنوع هو الافتراض الصامت في التجهيزة.
    """
    import re
    from pathlib import Path

    tests = Path(__file__).resolve().parent.parent.parent
    #: الملفات التي تمرّ فعلاً بـ`invoice_award` — وهي وحدها التي تُخفي HR-01.
    through_invoicing = [
        tests / "bidding" / "tests" / "test_settlement.py",
        tests / "console" / "tests" / "test_partner_decisions.py",
    ]

    oversized = []
    for path in through_invoicing:
        source = path.read_text(encoding="utf-8")
        for match in re.finditer(
            r"deposit_insurance\((?:[^()]|\([^()]*\))*?\)", source, re.DOTALL
        ):
            call = match.group(0)
            #: نداءٌ يمرّر مبلغه من وسيطٍ (`amount=Decimal(funds)`) يُقرَّر عند
            #: موضع الاستدعاء لا هنا — والافتراض نفسه مفحوصٌ بالسطر التالي.
            amounts = re.findall(r'Decimal\("(\d+(?:\.\d+)?)"\)', call)
            for raw in amounts:
                if Decimal(raw) > DEPOSIT:
                    line = source[: match.start()].count(chr(10)) + 1
                    oversized.append(f"{path.name}:{line} يودع {raw}")

    assert oversized == [], (
        "تجهيزةٌ تودع أكثر من الوديعة في ملفٍّ يمرّ بالفوترة — "
        f"وتلك وسادةٌ تُخفي HR-01: {oversized}"
    )
