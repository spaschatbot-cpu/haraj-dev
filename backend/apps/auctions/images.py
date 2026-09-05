"""Rendered copies of a photograph, written to disk once at upload time. HR-12.

A list of fifty cars must never fetch fifty full-size photographs. That was
the real bottleneck in v1 — not the number of requests, which everyone kept
optimising, but 50 × 3 MB of JPEG travelling to a phone on mobile data. The
incident is 13 GB of originals served as-is, and the page froze.

**Two rendered tiers, not one.** ``PHASE_04`` §2-1 asks for both by name: "a
light copy for the list cards (Thumbnail) and a medium-resolution copy for the
preview, and the original is not loaded in full except on zoom". One tier is
not the rule half-done, it is a different rule: a card thumbnail enlarged to
fill a detail screen is a blurred picture of a car somebody is deciding to
spend eighty thousand riyals on, so without the middle tier the detail screen
goes back to the original and the incident comes back with it — on the screen
where a customer lingers longest.

The tiers are a **table**, and generation walks it. A third tier is a row here
and nothing else: a size written twice is two sizes waiting to disagree
(Article 4-5).

Generation happens on upload and only on upload: resizing on read means the
first visitor after every deploy pays for it, and a cache that can be cleared
is a cache that will be. What already exists on disk is filled in by
``manage.py rebuild_image_tiers``, not by a request.

The source this reads has already been through `apps.core.uploads`, so it is a
picture we encoded ourselves — this module never sees an uploader's bytes and
never picks a stored name (T912). It hands back content; the caller stores it
through the field, whose `upload_to` mints the name.
"""

from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO

from django.core.files.base import ContentFile
from PIL import Image

#: What every rendered copy is encoded as, whatever the original was.
RENDERED_SUFFIX = ".jpg"

#: Kept under the old name because `test_images.py` and any other caller that
#: only ever wanted the card size should not have to learn the table to ask
#: for it. Derived, so the two cannot drift.
THUMBNAIL_SUFFIX = RENDERED_SUFFIX


@dataclass(frozen=True)
class Tier:
    """One rendered size: the field it is stored in, its box, its quality."""

    #: The `ImageField` on `VehicleImage` that holds it. Named here rather than
    #: passed in, so "which sizes exist" and "where each is stored" is one
    #: answer in one place.
    field: str
    box: tuple[int, int]
    quality: int
    #: Why this size and not another. Read by nobody and needed by everybody
    #: who later wonders whether 400 was measured or guessed.
    purpose: str


TIERS: tuple[Tier, ...] = (
    Tier(
        field="thumbnail",
        box=(400, 300),
        quality=80,
        purpose="بطاقة في قائمة، على جوالٍ كبير بكثافة ٢× — ولا أوسع",
    ),
    Tier(
        field="preview",
        box=(1280, 960),
        quality=82,
        purpose="شاشة تفاصيل المركبة — تكفي الشاشة الكاملة ولا تُحمّل الأصل",
    ),
)

#: Wide enough for a card on a large phone at 2× density, and no wider.
THUMBNAIL_SIZE = TIERS[0].box
THUMBNAIL_QUALITY = TIERS[0].quality

PREVIEW_SIZE = TIERS[1].box


def render(source, tier: Tier) -> ContentFile:
    """Return ``source`` resized to ``tier`` as content ready to be stored.

    Everything is re-encoded as JPEG: the source may be a 12 MB PNG straight
    off a camera, and a "thumbnail" that inherits that encoding is not one.

    `Image.thumbnail` only ever shrinks — a photograph already smaller than the
    box is re-encoded at that size and not blown up, which is what we want: an
    upscaled copy is bytes bought for nothing.
    """
    source.open()
    try:
        with Image.open(source) as picture:
            picture = picture.convert("RGB")
            picture.thumbnail(tier.box)
            buffer = BytesIO()
            picture.save(buffer, format="JPEG", quality=tier.quality, optimize=True)
    finally:
        # `open()` without a matching `close()` was already here before HR-12
        # and cost nothing while one photograph was rendered per request. It
        # costs a great deal in `rebuild_image_tiers`, which walks every row:
        # forty thousand file handles held open, and on Windows the original
        # cannot even be deleted afterwards. Caught by the orphan test, which
        # deletes one.
        source.close()

    return ContentFile(buffer.getvalue())


def build_thumbnail(source) -> ContentFile:
    """The card-sized copy. Kept as a name because most callers want only it."""
    return render(source, TIERS[0])


def build_preview(source) -> ContentFile:
    """The detail-screen copy — the tier whose absence sends a screen to the
    original, which is the incident."""
    return render(source, TIERS[1])
