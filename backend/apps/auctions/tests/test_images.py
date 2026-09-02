"""T408 — a thumbnail exists before the first visitor asks for one.

The acceptance criterion is about bytes, not requests: a page of fifty cars
must never reference a full-size photograph. So the test looks at what the
card hands out and at the size of what was written to disk, rather than at how
many queries happened — that is a different test, in `test_cards.py`.
"""

from __future__ import annotations

from io import BytesIO

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image

from apps.auctions import services
from apps.auctions.cards import card_queryset, vehicle_card
from apps.auctions.images import THUMBNAIL_SIZE
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
