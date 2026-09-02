"""Thumbnails, written to disk once at upload time.

A list of fifty cars must never fetch fifty full-size photographs. That was
the real bottleneck in v1 — not the number of requests, which everyone kept
optimising, but 50 × 3 MB of JPEG travelling to a phone on mobile data.

Generation happens on upload and only on upload: resizing on read means the
first visitor after every deploy pays for it, and a cache that can be cleared
is a cache that will be.
"""

from __future__ import annotations

from io import BytesIO
from pathlib import PurePosixPath

from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from PIL import Image

#: Wide enough for a card on a large phone at 2× density, and no wider.
THUMBNAIL_SIZE = (400, 300)
THUMBNAIL_QUALITY = 80


def thumbnail_name(source_name: str) -> str:
    """`vehicles/2026/09/abc.png` → `vehicles/2026/09/thumbs/abc.jpg`.

    Kept beside the original rather than in a parallel tree so that deleting a
    year's uploads takes its thumbnails with it.
    """
    path = PurePosixPath(source_name)
    return str(path.parent / "thumbs" / f"{path.stem}.jpg")


def build_thumbnail(source) -> str:
    """Write a thumbnail for an uploaded image and return its storage name.

    Everything is re-encoded as JPEG: the source may be a 12 MB PNG straight
    off a camera, and a "thumbnail" that inherits that encoding is not one.
    """
    source.open()
    with Image.open(source) as picture:
        picture = picture.convert("RGB")
        picture.thumbnail(THUMBNAIL_SIZE)
        buffer = BytesIO()
        picture.save(buffer, format="JPEG", quality=THUMBNAIL_QUALITY, optimize=True)

    return default_storage.save(
        thumbnail_name(source.name), ContentFile(buffer.getvalue())
    )
