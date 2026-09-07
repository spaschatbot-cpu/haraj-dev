"""T408 and HR-12 — every rendered copy exists before the first visitor asks.

The acceptance criterion is about bytes, not requests: a page of fifty cars
must never reference a full-size photograph. So the test looks at what the
card hands out and at the size of what was written to disk, rather than at how
many queries happened — that is a different test, in `test_cards.py`.

**HR-12 adds the middle tier and the tests that walk the table.** Everything
below that could be written once per tier is written once *over* `TIERS`
instead, because a size added to that table with no test is a size nobody
measured — and the failure it produces is not an exception, it is a screen
that quietly loads the original.
"""

from __future__ import annotations

from io import BytesIO

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from PIL import Image

from apps.auctions import services
from apps.auctions.cards import card_queryset, vehicle_card
from apps.auctions.images import THUMBNAIL_SIZE, TIERS
from apps.auctions.models import Vehicle, VehicleImage
from apps.auctions.states import AuctionState, VehicleState

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def media_root(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    return tmp_path


def a_photograph(name="car.png", size=(2400, 1600)) -> SimpleUploadedFile:
    buffer = BytesIO()
    Image.new("RGB", size, (120, 140, 160)).save(buffer, format="PNG")
    return SimpleUploadedFile(name, buffer.getvalue(), content_type="image/png")


@pytest.fixture
def vehicle(make_auction, make_vehicle):
    return make_vehicle(make_auction(state=AuctionState.LIVE), state=VehicleState.LISTED)


def test_uploading_an_image_writes_a_thumbnail(vehicle, media_root):
    image = services.add_image(vehicle, a_photograph(), cover=True)

    assert image.thumbnail
    with Image.open(media_root / image.thumbnail.name) as thumb:
        assert thumb.width <= THUMBNAIL_SIZE[0]
        assert thumb.height <= THUMBNAIL_SIZE[1]


def test_the_thumbnail_is_much_smaller_than_the_original(vehicle):
    image = services.add_image(vehicle, a_photograph(), cover=True)

    assert image.thumbnail.size < image.image.size / 10


def test_a_card_never_hands_out_the_full_size_file(vehicle):
    """The whole point. A card that leaks the original undoes the thumbnail."""
    image = services.add_image(vehicle, a_photograph(), cover=True)

    card = vehicle_card(card_queryset(Vehicle.objects.all()).get(pk=vehicle.pk))

    assert card["thumbnail_url"] == image.thumbnail.url
    assert image.image.url not in card.values()
    assert "thumbs/" in card["thumbnail_url"]


def test_a_second_cover_replaces_the_first_rather_than_colliding(vehicle):
    """The database allows one cover per vehicle; the service is what makes
    "make this the cover" a usable action instead of an IntegrityError."""
    first = services.add_image(vehicle, a_photograph("a.png"), cover=True)
    second = services.add_image(vehicle, a_photograph("b.png"), position=1, cover=True)

    covers = VehicleImage.objects.filter(vehicle=vehicle, is_cover=True)
    assert list(covers) == [second]
    assert VehicleImage.objects.get(pk=first.pk).is_cover is False


def test_images_keep_the_order_they_were_given(vehicle):
    services.add_image(vehicle, a_photograph("b.png"), position=1)
    services.add_image(vehicle, a_photograph("a.png"), position=0)

    positions = list(vehicle.images.values_list("position", flat=True))
    assert positions == [0, 1]


# ---------------------------------------------------------------------------
# HR-12 — every tier in the table, and the table is the only list
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("tier", TIERS, ids=lambda tier: tier.field)
def test_uploading_writes_every_tier_in_the_table(vehicle, media_root, tier):
    """Parametrised over `TIERS` on purpose.

    A tier added to the table joins this test by existing. Written out per
    tier instead, the second size would have been the one with no test — and
    HR-12 exists because the second size was the one with no code.
    """
    image = services.add_image(vehicle, a_photograph(), cover=True)

    stored = getattr(image, tier.field)
    assert stored, f"لم تُولَّد نسخة {tier.field}"
    with Image.open(media_root / stored.name) as rendered:
        assert rendered.width <= tier.box[0]
        assert rendered.height <= tier.box[1]


@pytest.mark.parametrize("tier", TIERS, ids=lambda tier: tier.field)
def test_every_tier_is_smaller_than_the_original(vehicle, tier):
    """The whole purpose, asserted in bytes rather than in intent.

    A "preview" that is not smaller than the original is the original wearing
    another name, and the page freezes exactly as before.
    """
    image = services.add_image(vehicle, a_photograph(), cover=True)

    assert getattr(image, tier.field).size < image.image.size


def test_the_tiers_go_from_smallest_to_largest_and_none_repeats(vehicle):
    """Two tiers of the same size are one tier and a wasted render.

    Ordering matters beyond tidiness: a card is meant to cost less than a
    detail screen, and a table whose second row is smaller than its first has
    that backwards without anything failing.
    """
    image = services.add_image(vehicle, a_photograph(), cover=True)

    sizes = [getattr(image, tier.field).size for tier in TIERS]

    assert sizes == sorted(sizes), "الترتيب من الأصغر إلى الأكبر انقلب"
    assert len(set(sizes)) == len(sizes), "طبقتان بالحجم نفسه"


def test_a_tier_is_stored_where_its_own_folder_says(vehicle):
    """One folder per tier — so "rebuild every rendered copy" is a directory
    somebody can point at, not a filter over a mixed one."""
    image = services.add_image(vehicle, a_photograph(), cover=True)

    assert "vehicles/thumbs/" in image.thumbnail.name.replace("\\", "/")
    assert "vehicles/previews/" in image.preview.name.replace("\\", "/")


def test_a_smaller_photograph_is_not_blown_up(vehicle, media_root):
    """A copy larger than its source is bytes bought for nothing."""
    image = services.add_image(vehicle, a_photograph(size=(320, 240)), cover=True)

    with Image.open(media_root / image.preview.name) as preview:
        assert (preview.width, preview.height) == (320, 240)


# ---------------------------------------------------------------------------
# HR-12 — the 13 GB already on disk
# ---------------------------------------------------------------------------


def test_the_rebuild_command_fills_a_tier_that_predates_it(vehicle, media_root):
    """The incident's own population: photographs uploaded before the tier.

    Simulated by clearing the field the way a migration from v1 leaves it —
    original on disk, rendered copy never made.
    """
    image = services.add_image(vehicle, a_photograph(), cover=True)
    VehicleImage.objects.filter(pk=image.pk).update(preview="")

    call_command("rebuild_image_tiers")

    image.refresh_from_db()
    assert image.preview, "بقيت الصورة القديمة بلا معاينة"
    with Image.open(media_root / image.preview.name) as preview:
        assert preview.width <= TIERS[1].box[0]


def test_running_the_rebuild_twice_renders_nothing_the_second_time(vehicle):
    """It is a command somebody runs again after it was interrupted."""
    image = services.add_image(vehicle, a_photograph(), cover=True)
    VehicleImage.objects.filter(pk=image.pk).update(preview="")
    call_command("rebuild_image_tiers")
    image.refresh_from_db()
    was = image.preview.name

    call_command("rebuild_image_tiers")

    image.refresh_from_db()
    assert image.preview.name == was, "أعاد التوليد فوق نسخةٍ قائمة"


def test_a_missing_original_is_reported_and_the_rest_still_render(
    vehicle, media_root, capsys
):
    """After a v1 migration some rows name files that are not there.

    A command that raises on the first one leaves the other forty thousand
    unrendered — which is the same page, still frozen.
    """
    orphan = services.add_image(vehicle, a_photograph("gone.png"), cover=True)
    healthy = services.add_image(vehicle, a_photograph("here.png"), position=1)
    VehicleImage.objects.filter(pk__in=[orphan.pk, healthy.pk]).update(preview="")
    (media_root / orphan.image.name).unlink()

    call_command("rebuild_image_tiers")

    orphan.refresh_from_db()
    healthy.refresh_from_db()
    assert not orphan.preview
    assert healthy.preview, "أوقف صفٌّ تالف بقيّة الصور"
    assert "الأصل غير موجود" in capsys.readouterr().err
