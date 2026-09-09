"""The only place an auction's or a vehicle's state changes.

Every move goes through :func:`move_auction` or :func:`move_vehicle`, which
consult the table in :mod:`apps.auctions.states` and write the column under a
row lock. No view, serializer, task, admin action or management command
assigns `.state` itself — `ops/checks/auction_state_single_writer.py` fails CI
if one does.

Why one writer, when a state column looks harmless next to the ledger: in v1
six paths could end an auction and each had grown its own idea of what "end"
meant, so a car could be awarded twice and a deposit released against an
auction that was still taking bids. The money engine has one writer for the
same reason; this is the same discipline applied to the thing that tells the
money engine what happened.

Nothing here touches `apps.money`. Settlement — releasing holds, issuing the
winner's invoice — belongs to phase 006 and calls in from outside.
"""

from __future__ import annotations

import logging
from datetime import datetime
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from apps.core import uploads

from .models import Auction, PartnerDecision, Vehicle, VehicleImage
from .states import (
    AuctionState,
    VehicleState,
    check_auction_move,
    check_vehicle_move,
)
from .visibility import can_view, visible_vehicles  # noqa: F401  (re-exported)

log = logging.getLogger(__name__)

__all__ = [
    "activate",
    "activate_due",
    "add_image",
    "award",
    "can_view",
    "cancel",
    "cascade_auction_vehicles",
    "due_to_activate",
    "due_to_end",
    "end",
    "end_due",
    "invoice",
    "list_for_sale",
    "mark_paid",
    "move_auction",
    "move_vehicle",
    "open_bidding",
    "reject",
    "release",
    "relist",
    "remove_image",
    "schedule",
    "send_to_owner",
    "set_cover",
    "settle",
    "unschedule",
    "visible_vehicles",
    "withdraw",
]


# ---------------------------------------------------------------------------
# Auction
# ---------------------------------------------------------------------------


def move_auction(
    auction: Auction, target: str, *, now: datetime | None = None
) -> Auction:
    """Move one auction, or refuse.

    The row is re-read under `SELECT ... FOR UPDATE` before the table is
    consulted, so two workers reaching the same auction in the same second
    cannot both see `scheduled` and both activate it. The caller's instance is
    updated to match, because a caller holding a stale object is how the
    second write in v1 got made.
    """
    now = now or timezone.now()

    with transaction.atomic():
        locked = Auction.objects.select_for_update().get(pk=auction.pk)
        move = check_auction_move(locked, target, now)

        locked.state = target
        locked.save(update_fields=["state", "updated_at"])

    auction.state = locked.state
    auction.updated_at = locked.updated_at
    log.info("auction %s: %s → %s (%s)", auction.pk, move.source, move.target, move.why)
    return auction


def schedule(auction: Auction, *, now: datetime | None = None) -> Auction:
    """اجدُل المزاد — **واحجز تسويتَه للحظة انتهائه** في الوقت نفسه.

    الحجزُ هنا لا في كرونٍ يستطلع: مهمّةٌ واحدةٌ لكل مزادٍ بموعدٍ هو `ends_at`
    نفسه. ولا يُسقط الجدولةَ إن تعذّر (وسيطٌ غائبٌ في التطوير) — والمحرّكُ يقرأ
    الساعة، فلا مزايدةَ تمرّ بعد الإغلاق ولو تأخّرت التسوية.
    """
    moved = move_auction(auction, AuctionState.SCHEDULED, now=now)
    from apps.bidding.tasks import book_settlement

    book_settlement(moved)
    return moved


def unschedule(auction: Auction, *, now: datetime | None = None) -> Auction:
    return move_auction(auction, AuctionState.DRAFT, now=now)


def activate(auction: Auction, *, now: datetime | None = None) -> Auction:
    return move_auction(auction, AuctionState.LIVE, now=now)


def end(auction: Auction, *, now: datetime | None = None) -> Auction:
    return move_auction(auction, AuctionState.ENDED, now=now)


def settle(auction: Auction, *, now: datetime | None = None) -> Auction:
    return move_auction(auction, AuctionState.SETTLED, now=now)


def cancel(auction: Auction, *, now: datetime | None = None) -> Auction:
    return move_auction(auction, AuctionState.CANCELLED, now=now)


# ---------------------------------------------------------------------------
# The calendar
# ---------------------------------------------------------------------------


def due_to_activate(now: datetime | None = None):
    """Scheduled auctions whose start moment has passed.

    The comparison is UTC on both sides — `starts_at` as stored against
    `timezone.now()`. Saudi time exists at the edges only: an operator types
    a Riyadh wall clock, `apps.core.time.from_display` turns it into UTC once,
    and no query ever converts anything (Article 3-1).
    """
    from .engine import due_to_start

    return due_to_start(now=now).order_by("starts_at")


def due_to_end(now: datetime | None = None):
    """Live auctions whose end moment has passed."""
    from .engine import due_to_finish

    return due_to_finish(now=now).order_by("ends_at")


def activate_due(now: datetime | None = None) -> list[int]:
    now = now or timezone.now()
    started: list[int] = []
    for auction in due_to_activate(now):
        activate(auction, now=now)
        started.append(auction.pk)
    return started


def end_due(now: datetime | None = None) -> list[int]:
    now = now or timezone.now()
    ended: list[int] = []
    for auction in due_to_end(now):
        end(auction, now=now)
        ended.append(auction.pk)
    return ended


# ---------------------------------------------------------------------------
# Vehicle
# ---------------------------------------------------------------------------


class PartnerRulingPending(Exception):
    """قرارٌ على سيارةِ شريكٍ لم يحكم فيها بعد."""


#: النصُّ الموحَّد — كما في v1، فلا تتناقض الشاشات في ما تقوله.
PARTNER_LOCK_MESSAGE = (
    "هذه السيارة للتسويق وبانتظار قرار التعاونية. "
    "لا يمكن اتخاذ قرار عليها قبل أن يقرّر الشريك."
)

#: النقلتان اللتان هما «قرارٌ على السيارة» — وعليهما وحدهما يقع القفل.
_DECISION_TARGETS = (VehicleState.AWARDED, VehicleState.REJECTED)


def partner_lock_reason(vehicle: Vehicle, target: str) -> str:
    """سببُ منع القرار على سيارة شريك، أو `""` إن كان مسموحاً.

    القاعدة من v1: سيارةُ التسويق قرارُها للشريك أولاً — لا تُقبل عليها عرضٌ
    ولا تُرفض قبل أن يحكم. والفرقان عن v1 اثنان، وكلاهما مقصود:

    **بوّابةٌ واحدة عند الكاتب، لا نسخةٌ في كل شاشة.** v1 كتب القاعدة في
    `OwnersAuctionBidsController` وحدها، فمرّت اللوحاتُ القديمة من تحتها —
    ونادت خدمةَ القبول مباشرةً وهي لا تقرأ المركبة — فقُبل عرضٌ بـ١٦٢٬٣٥٠ على
    مركبةِ شريكٍ وحقلُ قراره خالٍ (٢٠٢٦-٠٨-٢٢). ثم نُسخت القاعدة في صنفٍ
    مشترك، وبقيت نسختان. وهنا موضعٌ واحد: `move_vehicle` هو الكاتبُ الوحيد
    لعمود الحالة، فما لا يمرّ به لا يغيّر قراراً.

    **وتفشل مغلقةً، لا مفتوحة.** v1 يسمح عند أي خطأ أو عمودٍ غائب — «ميزةٌ
    للشريك يجب ألّا تحبس المالك». والثمنُ أن كلَّ عطلٍ يصير إذناً. هنا الحقول
    موجودةٌ بالقيد لا بالاحتمال، والغياب لا يُسأل عنه أصلاً.
    """
    if target not in _DECISION_TARGETS:
        return ""
    if not vehicle.is_marketing:
        return ""
    if vehicle.partner_decided_at is not None:
        return ""
    return PARTNER_LOCK_MESSAGE


def move_vehicle(vehicle: Vehicle, target: str, *, extra: dict | None = None) -> Vehicle:
    """Move one vehicle, or refuse.

    `extra` carries the fields a move needs alongside the state — the winner
    and price of an award, say. They are written in the same transaction as
    the state, because a car recorded as `awarded` with no winner is a row the
    database check constraint would refuse anyway, and two statements would
    leave a window where it existed.
    """
    with transaction.atomic():
        locked = Vehicle.objects.select_for_update().get(pk=vehicle.pk)

        fields = ["state", "updated_at"]
        for name, value in (extra or {}).items():
            setattr(locked, name, value)
            fields.append(name)

        move = check_vehicle_move(locked, target)

        # قفلُ الشريك يُقرأ من **الصفّ المقفول** لا من النسخة في الذاكرة: حكمٌ
        # وصل بين قراءةِ الشاشة والضغطِ على الزرّ يُرى هنا.
        refusal = partner_lock_reason(locked, target)
        if refusal:
            raise PartnerRulingPending(refusal)

        locked.state = target
        locked.save(update_fields=fields)

    for name, value in (extra or {}).items():
        setattr(vehicle, name, value)
    vehicle.state = locked.state
    vehicle.updated_at = locked.updated_at
    log.info("vehicle %s: %s → %s (%s)", vehicle.pk, move.source, move.target, move.why)
    return vehicle


def list_for_sale(vehicle: Vehicle) -> Vehicle:
    return move_vehicle(vehicle, VehicleState.LISTED)


def open_bidding(vehicle: Vehicle) -> Vehicle:
    return move_vehicle(vehicle, VehicleState.BIDDING)


def send_to_owner(vehicle: Vehicle) -> Vehicle:
    """Highest bid is below the reserve — the owner decides, not the system."""
    return move_vehicle(vehicle, VehicleState.AWAITING_DECISION)


def award(
    vehicle: Vehicle,
    winner,
    price: Decimal,
    *,
    now: datetime | None = None,
) -> Vehicle:
    """Record who won and for how much.

    The money side of winning — locking the winner's deposit against the
    invoice — is phase 006's, and calling it from here would put a second
    writer in front of the ledger.
    """
    return move_vehicle(
        vehicle,
        VehicleState.AWARDED,
        extra={
            "awarded_to": winner,
            "awarded_price": price,
            "awarded_at": now or timezone.now(),
        },
    )


def reject(vehicle: Vehicle) -> Vehicle:
    return move_vehicle(vehicle, VehicleState.REJECTED)


def invoice(vehicle: Vehicle) -> Vehicle:
    return move_vehicle(vehicle, VehicleState.INVOICED)


def mark_paid(vehicle: Vehicle) -> Vehicle:
    return move_vehicle(vehicle, VehicleState.PAID)


def release(vehicle: Vehicle) -> Vehicle:
    return move_vehicle(vehicle, VehicleState.RELEASED)


def withdraw(vehicle: Vehicle) -> Vehicle:
    return move_vehicle(vehicle, VehicleState.WITHDRAWN)


def relist(vehicle: Vehicle) -> Vehicle:
    return move_vehicle(vehicle, VehicleState.RELISTED)


# ---------------------------------------------------------------------------
# Images
# ---------------------------------------------------------------------------


def add_image(vehicle: Vehicle, file, *, position: int = 0, cover: bool = False):
    """Attach an image and generate **every rendered tier** in the same call.

    Generation is explicit rather than a `post_save` signal (T008 forbids
    signals project-wide): a row saved by a fixture, a migration or a shell
    should not silently start resizing files, and a reader of this function
    can see everything that happens on upload.

    **Nothing the uploader sent is stored.** `apps.core.uploads.sanitise_image`
    decides from the bytes whether this is a picture at all, refuses it in
    Arabic when it is not, and hands back a freshly encoded copy — so a file
    that is a valid PNG *and* a valid PHP script arrives here and leaves as a
    PNG only (T912). The name is minted by the field's `upload_to` callable for
    the same reason. This is the single door: every path that stores a vehicle
    photograph calls this function.
    """
    from .images import RENDERED_SUFFIX, TIERS, render

    sanitised = uploads.sanitise_image(file)

    with transaction.atomic():
        if cover:
            VehicleImage.objects.filter(vehicle=vehicle, is_cover=True).update(
                is_cover=False
            )

        image = VehicleImage(vehicle=vehicle, position=position, is_cover=cover)
        # `save=False`: the name comes from the field's `upload_to` callable and
        # the row is written once, below, rather than twice.
        image.image.save(f"upload{sanitised.suffix}", sanitised.content, save=False)
        image.save()
        # Every tier in the table, not a list written again here: a size added
        # to `images.TIERS` is generated by this loop with no edit (HR-12).
        for tier in TIERS:
            getattr(image, tier.field).save(
                f"{tier.field}{RENDERED_SUFFIX}", render(image.image, tier), save=False
            )
        image.save(update_fields=[tier.field for tier in TIERS])

    return image


def set_cover(image: VehicleImage) -> VehicleImage:
    """اجعل صورةً **قائمة** غلافَ مركبتها. T866.

    `add_image(cover=True)` يرفع صورةً جديدة ويجعلها الغلاف، وهو الباب الوحيد
    الذي كان موجوداً — فمن أراد غلافاً آخر من صورٍ مرفوعةٍ أصلاً لم يكن أمامه
    إلا رفعُ نسخةٍ ثانيةٍ من الصورة نفسها. وهذا ما يفعله v1 حرفياً
    (`setDisplayImage`, AuctionController.php:4637): يُدخل صفّاً جديداً بالبايتات
    نفسها ويرفع عليه `is_primary`، فتظهر الصورة مرّتين في المعرض.

    و`is_cover` ليس عموداً حرّاً: عليه `UniqueConstraint` بشرط `is_cover=True`
    لكل مركبة (`models.py`). فإنزالُ القديم ورفعُ الجديد فعلٌ **واحد** في
    معاملةٍ واحدة — ولو انفصلا لسقطت الكتابةُ الثانية على القيد وبقيت المركبة
    بلا غلافٍ إطلاقاً.
    """
    with transaction.atomic():
        VehicleImage.objects.filter(vehicle=image.vehicle, is_cover=True).exclude(
            pk=image.pk
        ).update(is_cover=False)
        if not image.is_cover:
            image.is_cover = True
            image.save(update_fields=["is_cover"])
    return image


def remove_image(image: VehicleImage) -> Vehicle:
    """احذف صورةً من معرض مركبتها، ورقِّ غيرها إن كانت هي الغلاف. T866.

    **الترقية ليست لطفاً بالمستخدم.** بطاقةُ السيارة عند العميل تقرأ الغلاف
    وحده (`cards._cover`), فمركبةٌ لها عشرُ صورٍ وحُذف غلافُها تصير بطاقةً
    بلا صورة — والصورُ التسع موجودة. فالوارثُ أوّلُ الباقي بـ`position` ثم
    `pk`: ترتيبُ المعرض نفسه، فلا يفاجأ من يحذف بغلافٍ جاء من آخر القائمة.

    **والبايتات على القرص لا تُمسّ** — كما في v1 (`deleteVehicleImage`,
    AuctionController.php:4578: حذفُ صفٍّ بلا `unlink`). حذفُ الملفّ من هنا
    يعني أن نسخةً احتياطيةً استُرجعت أو صفّاً أُعيد إدراجه يجد فراغاً، وتنظيفُ
    الأيتام مهمّةٌ دوريّةٌ تُقارن بالقرص — لا أثرٌ جانبيٌّ لضغطةِ زرّ.
    """
    vehicle = image.vehicle
    was_cover = image.is_cover
    with transaction.atomic():
        image.delete()
        if was_cover:
            heir = (
                VehicleImage.objects.filter(vehicle=vehicle)
                .order_by("position", "pk")
                .first()
            )
            if heir is not None:
                heir.is_cover = True
                heir.save(update_fields=["is_cover"])
    return vehicle


def cascade_auction_vehicles(auction: Auction, old_status: str, new_status: str) -> int:
    """Cascade auction status change to matching vehicles (T849).

    In v1: only vehicles whose status was in sync with the auction's previous
    status follow the change. In v2: when an auction becomes active (live),
    listed vehicles move to bidding. When scheduled/soon/upcoming, draft
    vehicles move to listed.
    """
    cascaded = 0
    if new_status == "active":
        for vehicle in auction.vehicles.filter(state=VehicleState.LISTED):
            open_bidding(vehicle)
            cascaded += 1
    elif new_status in ("soon", "upcoming", "later", "scheduled"):
        for vehicle in auction.vehicles.filter(state=VehicleState.DRAFT):
            list_for_sale(vehicle)
            cascaded += 1
    return cascaded


def record_partner_ruling(
    vehicle: Vehicle, *, decision: str, actor, bid=None, now=None
) -> Vehicle:
    """اختِم حكمَ شريك التسويق على سيارته — وهو ما يفكّ `partner_lock_reason`.

    الشرطُ من v1 حرفياً: **لا قرارَ قبل انتهاء المزاد** (`auctionEndedForVehicle`
    ترفض بـ409 «لا يمكن اتخاذ القرار قبل انتهاء المزاد») — فالشريك لا يحسم
    عرضاً والمظاريف لم تُفتح بعد.

    وثلاثةُ فروقٍ عن v1، كلُّها لأن حكمَ الشريك **واقعةٌ** لا خانةٌ تُكتب:

    * **لا يُختَم مرّتين.** v1 يُحدِّث الأعمدة بأي نداء، فتراجعٌ صامتٌ ممكن.
      وهنا الحكمُ الأول يبقى، والثاني يُرفض — ونقضُه فعلٌ له بابُه.
    * **يُسمّي صاحبه** (`partner_decided_by` مفتاحٌ لا نصّ): v1 يكتب اسم
      المستخدم نصّاً، فحسابٌ يُعاد تسميته يترك قراراً بلا صاحب.
    * **لا يُحرّك حالةَ السيارة.** الحكمُ إذنٌ للمنصّة أن تقرّر، لا قرارُها.
    """
    if decision not in PartnerDecision.values:
        raise ValueError(f"unknown partner decision {decision!r}")
    if not vehicle.is_marketing:
        raise ValueError(f"vehicle {vehicle.pk} is not a marketing vehicle")

    now = now or timezone.now()
    if vehicle.auction.ends_at > now:
        raise PartnerRulingPending(
            "لا يمكن اتخاذ القرار قبل انتهاء المزاد — المظاريف لم تُفتح بعد."
        )

    with transaction.atomic():
        locked = Vehicle.objects.select_for_update().select_related("auction").get(
            pk=vehicle.pk
        )
        if locked.partner_decided_at is not None:
            raise PartnerRulingPending(
                f"حكم الشريك مسجَّلٌ سلفاً ({locked.get_partner_decision_display()})."
            )
        locked.partner_decision = decision
        locked.partner_decided_at = now
        locked.partner_decided_by = actor
        locked.partner_decision_bid = bid
        locked.save(
            update_fields=[
                "partner_decision",
                "partner_decided_at",
                "partner_decided_by",
                "partner_decision_bid",
                "updated_at",
            ]
        )

    for name in (
        "partner_decision",
        "partner_decided_at",
        "partner_decided_by",
        "partner_decision_bid",
    ):
        setattr(vehicle, name, getattr(locked, name))
    log.info("vehicle %s: partner ruled %s", vehicle.pk, decision)
    return vehicle


def queue_auction_reminder(auction: Auction, *, actor=None, now=None) -> dict:
    """أدرِج تذكيرَ «المزاد يقترب» في طابور الإشعارات. لا يُرسل ولا يُنفق.

    الحقلُ `sms_reminder_at` موجودٌ في v1 منذ سنة وتملؤه الاستمارة — **ولا سطرَ
    واحدٌ يقرؤه**: لا كرون ولا خدمةَ رسائل. فالميزةُ موعودةٌ ولم تُبنَ، لا في
    القديم ولا هنا.

    وتُبنى هنا **إدراجاً في الطابور لا إرسالاً**: صفُّ `Notification` بحالة
    `QUEUED` لا يكلّف هللة، والتسليمُ شأنُ من يملك البوّابة ومفتاحَها. والمادة
    ٥-٢ تمنع مهمّةً مجدولةً تُنفق بلا موافقةٍ صريحة — وإدراجٌ يراه إنسانٌ ويضغطه
    ليس إنفاقاً بلا عين.

    **الجمهور: من وضع سيارةً من هذا المزاد في مفضّلته.** وهو اختيارٌ لا تفصيل:
    التذكيرُ قبل الانطلاق، فلا مزايدَ بعد ولا حجزَ تأمينٍ يُستدلّ به؛ والمفضّلةُ
    أقربُ ما يقوله العميلُ بنفسه عن نيّته. وإرسالُه إلى أربعةٍ وأربعين ألفاً
    إعلانٌ لا تذكير، وثمنُه يُقاس بالآلاف.

    ولا يُدرَج مرّتين: `reminder_sent_at` يُختَم في المعاملة نفسها.
    """
    from apps.notifications.models import Channel, Notification

    from .favourites import Favourite

    now = now or timezone.now()
    if auction.sms_reminder_at is None:
        raise ValueError(f"auction {auction.pk} has no reminder time")

    with transaction.atomic():
        locked = Auction.objects.select_for_update().get(pk=auction.pk)
        if locked.reminder_sent_at is not None:
            raise ValueError(
                f"reminder for auction {locked.number} was queued at {locked.reminder_sent_at}"
            )

        audience = list(
            Favourite.objects.filter(vehicle__auction=locked)
            .values_list("user_id", flat=True)
            .distinct()
        )
        body = (
            f"مزاد {locked.number} — {locked.title} يبدأ "
            f"{timezone.localtime(locked.starts_at):%Y-%m-%d %H:%M}. "
            "سيارةٌ في مفضّلتك تُعرض فيه."
        )
        Notification.objects.bulk_create(
            [
                Notification(
                    user_id=uid,
                    channel=Channel.SMS,
                    template="auction_reminder",
                    body=body,
                    data={"auction": locked.number, "auction_id": locked.pk},
                )
                for uid in audience
            ],
            batch_size=1000,
        )
        locked.reminder_sent_at = now
        locked.save(update_fields=["reminder_sent_at", "updated_at"])

    auction.reminder_sent_at = locked.reminder_sent_at
    log.info("auction %s: queued %s reminders", auction.pk, len(audience))
    return {"auction": auction.pk, "queued": len(audience)}
