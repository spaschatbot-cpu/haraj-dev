"""T866 — معرضُ صور المركبة من صفّ المزاد: يفتح، ويرفع، ويحذف، ويعيّن غلافاً.

**العطل الذي بُني لأجل ألّا يتكرّر** ليس غيابَ الشاشة وحده. في v2 كان عمود
«الصور» في صفّ المزاد رقماً لا يُفتح: يقرأ الموظّف «بلا صور» ولا يجد من مكانه
سبيلاً إلى الرفع، فيؤجّل — وتُشحن السيارةُ بلا صورة. وبطاقةُ العميل تقرأ
**الغلاف وحده** (`cards._cover`), فسيارةٌ لها عشرُ صورٍ بلا غلافٍ بطاقةٌ فارغة.

ولذلك ثلاثةٌ من هذه الاختبارات لا تسأل «هل أجابت ٢٠٠؟» بل تسأل عن الغلاف بعد
الفعل: هو الحقلُ الوحيد الذي يظهر أثرُه عند العميل، وهو الذي ينكسر صامتاً.
"""

from __future__ import annotations

from io import BytesIO

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from django.utils import timezone
from PIL import Image

from apps.accounts.models import User
from apps.auctions.models import Auction, Vehicle, VehicleImage
from apps.auctions.states import AuctionState, VehicleState
from apps.core.models import AuditLog
from apps.core.permissions import Role

from .conftest import screen_of

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def media_root(settings, tmp_path):
    """صورٌ حقيقية تُكتب على القرص، في مجلّدٍ يموت مع الاختبار.

    ولا تُزوَّر بـ`Mock`: `add_image` يمرّ بـPIL ويولّد طبقتين، فاختبارٌ يقفز
    فوق ذلك يُبقي أوّلَ ما ينكسر في الإنتاج خارج الحزمة.
    """
    settings.MEDIA_ROOT = tmp_path
    return tmp_path


def a_photograph(name: str = "car.png") -> SimpleUploadedFile:
    buffer = BytesIO()
    Image.new("RGB", (800, 600), (120, 140, 160)).save(buffer, format="PNG")
    return SimpleUploadedFile(name, buffer.getvalue(), content_type="image/png")


def staff(role: str, phone: str) -> User:
    user = User.objects.create_user(phone=phone, full_name="موظف", password="x")
    user.is_staff = True
    user.console_role = role
    user.save(update_fields=["is_staff", "console_role"])
    return user


@pytest.fixture
def operator(client):
    client.force_login(staff(Role.OPERATIONS, "966500000866"))
    return client


@pytest.fixture
def viewer(client):
    """دورٌ يقرأ ولا يكتب — الشاشةُ تحذف وترفع، فلا تُفتح له."""
    client.force_login(staff(Role.SUPPORT, "966500000867"))
    return client


@pytest.fixture
def car(db) -> Vehicle:
    now = timezone.now()
    auction = Auction.objects.create(
        number=8660,
        title="مزاد الصور",
        starts_at=now + timezone.timedelta(days=1),
        ends_at=now + timezone.timedelta(days=2),
        state=AuctionState.DRAFT,
    )
    return Vehicle.objects.create(
        auction=auction,
        lot_number=1,
        make="تويوتا",
        model="كامري",
        year=2020,
        state=VehicleState.DRAFT,
    )


def gallery_url(car: Vehicle) -> str:
    return reverse("console:vehicle-images", args=[car.pk])


# ---------------------------------------------------------------------------
# الباب
# ---------------------------------------------------------------------------


def test_the_row_opens_the_gallery(operator, car):
    """عمودُ «الصور» في صفّ المزاد رابطٌ، لا رقمٌ يُقرأ ويُترك.

    هذا هو العطل حرفياً: من يرى «بلا صور» يجب أن يصل إلى الرفع من مكانه.
    """
    page = operator.get(reverse("console:auction-detail", args=[car.auction.pk]))
    assert gallery_url(car) in screen_of(page.content.decode())


def test_the_gallery_shows_the_photographs_it_has(operator, car):
    from apps.auctions import services

    services.add_image(car, a_photograph("a.png"), cover=True)
    services.add_image(car, a_photograph("b.png"))

    page = operator.get(gallery_url(car))
    assert page.status_code == 200
    body = screen_of(page.content.decode())
    # صفٌّ لكل صورة، مرسومٌ بصورةٍ حقيقية لا بحالة 200 (المعيار I6).
    assert body.count("<img") == 2
    assert "صورة العرض" in body


def test_a_reader_may_not_open_it(viewer, car):
    """الشاشةُ ترفع وتحذف، فحارسُها `AUCTIONS_MANAGE` لا `AUCTIONS_VIEW`."""
    assert viewer.get(gallery_url(car)).status_code == 403


# ---------------------------------------------------------------------------
# الرفع
# ---------------------------------------------------------------------------


def test_uploading_stores_the_photograph_and_makes_the_first_one_the_cover(
    operator, car
):
    """أوّلُ صورةٍ لمركبةٍ بلا غلاف تصير الغلاف.

    ولولا ذلك لرُفعت الصور ولبقيت بطاقةُ العميل فارغة — وهي الشكوى نفسها التي
    وُلد منها عمودُ الصور.
    """
    response = operator.post(
        gallery_url(car), {"op": "upload", "images": [a_photograph()]}
    )
    assert response.status_code == 302

    shot = VehicleImage.objects.get(vehicle=car)
    assert shot.is_cover is True
    # الطبقتان تُولَّدان في الرفع لا عند القراءة (HR-12).
    assert shot.thumbnail and shot.preview


def test_uploading_a_second_photograph_does_not_steal_the_cover(operator, car):
    from apps.auctions import services

    first = services.add_image(car, a_photograph("a.png"), cover=True)
    operator.post(gallery_url(car), {"op": "upload", "images": [a_photograph("b.png")]})

    first.refresh_from_db()
    assert first.is_cover is True
    assert VehicleImage.objects.filter(vehicle=car, is_cover=True).count() == 1


def test_a_batch_larger_than_the_limit_is_refused_before_anything_is_written(
    operator, car
):
    """الرفضُ قبل أوّل كتابة.

    ولو فُحص الحدُّ داخل الحلقة لكُتب بعضُها ثم سقط الطلب — ويقرأ الموظّف
    «فشل» ويجد نصفَ الصور مرفوعة.
    """
    from apps.console.vehicle_images import BATCH

    too_many = [a_photograph(f"{i}.png") for i in range(BATCH + 1)]
    operator.post(gallery_url(car), {"op": "upload", "images": too_many})

    assert VehicleImage.objects.filter(vehicle=car).count() == 0


def test_a_file_that_is_not_a_photograph_is_refused_by_name(operator, car):
    """البوّابةُ تقرأ البايتات لا الترويسة.

    v1 يفحص `$_FILES['type']` وحده — وهي ترويسةٌ يكتبها المرسل
    (AuctionController.php:4535). وهنا الملفُّ يُرفض ويُسمّى في رسالةٍ يقرؤها
    الموظّف، ولا يُبتلع صامتاً.
    """
    not_an_image = SimpleUploadedFile(
        "shell.png", b"<?php echo 1; ?>", content_type="image/png"
    )
    response = operator.post(
        gallery_url(car), {"op": "upload", "images": [not_an_image]}, follow=True
    )

    assert VehicleImage.objects.filter(vehicle=car).count() == 0
    assert "shell.png" in response.content.decode()


# ---------------------------------------------------------------------------
# الغلاف
# ---------------------------------------------------------------------------


def test_promoting_an_existing_photograph_moves_the_cover(operator, car):
    """ترقيةُ صورةٍ قائمة — وهو ما لا يستطيعه v1 أصلاً.

    v1 يرفع نسخةً ثانيةً بالبايتات نفسها ويرفع عليها `is_primary`
    (AuctionController.php:4637)، فتظهر الصورةُ مرّتين في المعرض.
    """
    from apps.auctions import services

    cover = services.add_image(car, a_photograph("a.png"), cover=True)
    other = services.add_image(car, a_photograph("b.png"))

    operator.post(gallery_url(car), {"op": "cover", "image": other.pk})

    cover.refresh_from_db()
    other.refresh_from_db()
    assert other.is_cover is True
    assert cover.is_cover is False
    # القيدُ في السكيمة يقول «غلافٌ واحد»؛ وهذا يقول إنّ الشاشة تحترمه.
    assert VehicleImage.objects.filter(vehicle=car, is_cover=True).count() == 1


# ---------------------------------------------------------------------------
# الحذف
# ---------------------------------------------------------------------------


def test_deleting_the_cover_promotes_the_next_one(operator, car):
    """المركبةُ لا تبقى بلا غلافٍ وصورُها موجودة.

    **وهذا هو الاختبار الذي يمسك العطل الصامت**: الحذفُ ينجح، والصفحةُ تقول
    «حُذفت»، وبطاقةُ العميل تصير فارغة ولا شيء يصرخ.
    """
    from apps.auctions import services

    cover = services.add_image(car, a_photograph("a.png"), cover=True)
    heir = services.add_image(car, a_photograph("b.png"), position=1)

    operator.post(gallery_url(car), {"op": "delete", "image": cover.pk})

    heir.refresh_from_db()
    assert heir.is_cover is True
    assert not VehicleImage.objects.filter(pk=cover.pk).exists()


def test_deleting_the_last_photograph_leaves_no_cover_and_says_so(operator, car):
    from apps.auctions import services

    only = services.add_image(car, a_photograph(), cover=True)
    response = operator.post(
        gallery_url(car), {"op": "delete", "image": only.pk}, follow=True
    )

    assert VehicleImage.objects.filter(vehicle=car).count() == 0
    assert "لم يبقَ للمركبة غلاف" in response.content.decode()


def test_a_photograph_of_another_vehicle_is_not_deletable_from_here(operator, car):
    """معرّفٌ مكتوبٌ بيدٍ لا يحذف صورةَ مركبةٍ أخرى.

    نظيرُ `vehicle_bulk._chosen`: الترشيحُ على المالك ليس تجميلاً — بدونه يكفي
    معرّفٌ لتُحذف صورةٌ في شاشةٍ لا تُفتح أصلاً.
    """
    from apps.auctions import services

    stranger = Vehicle.objects.create(
        auction=car.auction,
        lot_number=2,
        make="نيسان",
        model="التيما",
        year=2019,
        state=VehicleState.DRAFT,
    )
    theirs = services.add_image(stranger, a_photograph(), cover=True)

    operator.post(gallery_url(car), {"op": "delete", "image": theirs.pk})

    assert VehicleImage.objects.filter(pk=theirs.pk).exists()


# ---------------------------------------------------------------------------
# الأثر
# ---------------------------------------------------------------------------


def test_every_write_leaves_an_audit_row(operator, car):
    """ثلاثةُ أفعالٍ، ثلاثةُ قيود — وv1 لا يكتب واحداً منها.

    ولا واحدةٌ من نقاط الصور الخمس في v1 تتحقّق من CSRF أصلاً
    (AuctionController.php:4507، 4555، 4608).
    """
    operator.post(gallery_url(car), {"op": "upload", "images": [a_photograph()]})
    shot = VehicleImage.objects.get(vehicle=car)
    operator.post(gallery_url(car), {"op": "cover", "image": shot.pk})
    operator.post(gallery_url(car), {"op": "delete", "image": shot.pk})

    actions = set(
        AuditLog.objects.filter(action__startswith="console.vehicle_image").values_list(
            "action", flat=True
        )
    )
    assert actions == {
        "console.vehicle_images_upload",
        "console.vehicle_image_cover",
        "console.vehicle_image_delete",
    }
