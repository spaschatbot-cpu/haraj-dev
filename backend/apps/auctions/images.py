"""Thumbnails, written to disk once at upload time.

A list of fifty cars must never fetch fifty full-size photographs. That was
the real bottleneck in v1 — not the number of requests, which everyone kept
optimising, but 50 × 3 MB of JPEG travelling to a phone on mobile data.

Generation happens on upload and only on upload: resizing on read means the
first visitor after every deploy pays for it, and a cache that can be cleared
is a cache that will be.

The source this reads has already been through `apps.core.uploads`, so it is a
picture we encoded ourselves — this module never sees an uploader's bytes and
never picks a stored name (T912). It hands back content; the caller stores it
through the field, whose `upload_to` mints the name.
"""

from __future__ import annotations

from io import BytesIO

from django.core.files.base import ContentFile
from PIL import Image

#: Wide enough for a card on a large phone at 2× density, and no wider.
THUMBNAIL_SIZE = (400, 300)
THUMBNAIL_QUALITY = 80

#: What a thumbnail is always encoded as, whatever the original was.
THUMBNAIL_SUFFIX = ".jpg"


def build_thumbnail(source) -> ContentFile:
    """Return a thumbnail of ``source`` as content ready to be stored.

    Everything is re-encoded as JPEG: the source may be a 12 MB PNG straight
    off a camera, and a "thumbnail" that inherits that encoding is not one.
    """
    source.open()
    with Image.open(source) as picture:
        picture = picture.convert("RGB")
        picture.thumbnail(THUMBNAIL_SIZE)
        buffer = BytesIO()
        picture.save(buffer, format="JPEG", quality=THUMBNAIL_QUALITY, optimize=True)

    return ContentFile(buffer.getvalue())
