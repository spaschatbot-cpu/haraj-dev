"""T912 — what the upload path refuses, and what it does to what it accepts.

The acceptance criterion is one line — *رفع ملف تنفيذي بامتداد صورة مرفوض* —
and it is the first test here. The rest are the other three halves of the same
incident: the name, the bomb, and the polyglot that passes every header check
ever written because it really is a valid image *and* really is a script.
"""

from __future__ import annotations

import zlib
from io import BytesIO

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image

from apps.core import uploads
from apps.core.uploads import UploadRejected

#: A PHP web shell. The exact thing that lived in v1's photographs directory.
WEBSHELL = b"<?php system($_GET['c']); ?>"


def a_photograph(name="car.png", size=(60, 40), fmt="PNG") -> SimpleUploadedFile:
    buffer = BytesIO()
    Image.new("RGB", size, (120, 140, 160)).save(buffer, format=fmt)
    return SimpleUploadedFile(name, buffer.getvalue(), content_type="image/png")


def test_an_executable_wearing_an_image_extension_is_refused():
    """The acceptance criterion. Name, extension and content type all lie."""
    disguised = SimpleUploadedFile("car.png", WEBSHELL, content_type="image/png")

    with pytest.raises(UploadRejected) as refusal:
        uploads.sanitise_image(disguised)

    assert "ليس صورة" in refusal.value.user_message


def test_a_real_image_with_a_payload_glued_on_loses_the_payload():
    """A polyglot passes every header check there is — because it is an image.

    Concatenating a script after the image data leaves a file that Pillow opens
    happily and that a misconfigured web server executes happily. Nothing about
    the *header* is wrong, so nothing that only reads headers can refuse it.
    Re-encoding is what removes it, and this is the test that says so.
    """
    original = a_photograph().read()
    polyglot = SimpleUploadedFile(
        "car.png", original + WEBSHELL, content_type="image/png"
    )

    sanitised = uploads.sanitise_image(polyglot)

    assert WEBSHELL not in sanitised.content.read()


def test_an_svg_is_refused_however_it_is_named():
    """SVG is a document with script in it, not a photograph."""
    svg = b'<svg xmlns="http://www.w3.org/2000/svg"><script>alert(1)</script></svg>'

    with pytest.raises(UploadRejected):
        uploads.sanitise_image(
            SimpleUploadedFile("car.jpg", svg, content_type="image/jpeg")
        )


def test_a_file_over_the_size_ceiling_is_refused(settings):
    settings.UPLOAD_MAX_BYTES = 128

    with pytest.raises(UploadRejected) as refusal:
        uploads.sanitise_image(a_photograph(size=(400, 400)))

    assert "حجم الملف" in refusal.value.user_message


def test_a_decompression_bomb_is_refused_before_it_is_decoded(settings):
    """A tiny file that claims enormous dimensions.

    The header says 40,000 × 40,000; the pixels are one compressed run of
    zeroes. A byte limit lets this through — it is a few kilobytes — and the
    memory is spent the instant anything decodes it. So the refusal has to come
    off the header, and the size ceiling is deliberately left generous here to
    prove that it is the *dimension* check doing the work.
    """
    settings.UPLOAD_MAX_BYTES = 10 * 1024 * 1024

    bomb = SimpleUploadedFile("car.png", _png_declaring(40_000, 40_000))

    with pytest.raises(UploadRejected) as refusal:
        uploads.sanitise_image(bomb)

    assert "أبعاد" in refusal.value.user_message


def test_a_generated_name_carries_nothing_the_uploader_wrote():
    traversal = "../../../etc/cron.d/x.png"

    name = uploads.vehicle_image_path(None, traversal)

    assert ".." not in name
    assert "etc" not in name
    assert name.startswith("vehicles/")
    assert name.endswith(".png")


def test_two_uploads_of_the_same_name_get_two_names():
    """Otherwise one customer's photograph overwrites another's."""
    first = uploads.vehicle_image_path(None, "car.jpg")
    second = uploads.vehicle_image_path(None, "car.jpg")

    assert first != second


def test_a_name_that_did_not_come_through_the_gate_is_not_an_image_name():
    """`.bin` is deliberate: a stored file that skipped sanitising looks wrong."""
    assert uploads.vehicle_image_path(None, "shell.php").endswith(".bin")


def test_an_empty_file_is_refused():
    with pytest.raises(UploadRejected):
        uploads.sanitise_image(SimpleUploadedFile("car.png", b""))


def _png_declaring(width: int, height: int) -> bytes:
    """A structurally valid PNG whose IHDR claims ``width`` × ``height``.

    Hand-built rather than produced by Pillow, because Pillow would have to
    allocate the very buffer this file exists to avoid allocating.
    """

    def chunk(kind: bytes, body: bytes) -> bytes:
        return (
            len(body).to_bytes(4, "big")
            + kind
            + body
            + zlib.crc32(kind + body).to_bytes(4, "big")
        )

    ihdr = width.to_bytes(4, "big") + height.to_bytes(4, "big") + bytes([8, 0, 0, 0, 0])
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", ihdr)
        + chunk(b"IDAT", zlib.compress(b"\x00" * 1024))
        + chunk(b"IEND", b"")
    )
