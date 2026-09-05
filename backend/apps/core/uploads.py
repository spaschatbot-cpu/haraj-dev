"""The one door every uploaded file comes through. T912.

In v1 a webshell lived for months inside the photographs directory. Nothing
exotic got it there: the upload path trusted three things the uploader writes —
the file name, its extension, and its ``Content-Type`` header — and the web
server was willing to execute what it found. Each of those is answered here,
and none of the answers is a list of bad extensions.

**Content decides, never the name.** ``sanitise_image`` opens the bytes and
asks the decoder what they are. A PHP script called ``car.png`` announced as
``image/png`` has no image header, so it is refused before anything else about
it is considered.

**The name is ours, never theirs.** :func:`generated_name` throws the uploaded
name away and mints ``<uuid>.<ext>``, where the extension comes from the format
we *detected*. That closes path traversal (``../../public/x.png``), null-byte
and double-extension tricks, and the overwrite of somebody else's file, all at
once — not as three checks that each have to be remembered.

**The stored bytes are ours too.** The original is re-encoded rather than
written through. A file can be a valid image *and* a valid script at the same
time — append the payload after the image data and every header check in the
world still passes. Re-encoding keeps the picture and drops everything that was
not part of it, EXIF included. It costs one decode per upload, once, and it is
the only measure here that survives a misconfigured web server.

**Size is bounded twice, and the second bound is the one that matters.** A
6 KB PNG can declare 40,000 × 40,000 pixels and ask for 6 GB of memory the
moment anything decodes it. So the dimensions are read from the header and
refused *before* :meth:`PIL.Image.Image.load` is ever called — a byte limit
alone does not see this coming.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from io import BytesIO

from django.conf import settings
from django.core.files.base import ContentFile
from PIL import Image, UnidentifiedImageError

from apps.core.errors import DomainError


class UploadRejected(DomainError):
    """The file is not something this platform will store.

    A 409 like every other refusal: the caller can pick a different file, and
    the sentence tells them which property of this one was wrong.
    """

    code = "upload_rejected"
    default_message = "الملف غير مقبول."


#: What we are willing to store, and the extension each format is stored under.
#:
#: An allowlist of *decoded formats*, not of extensions: the key is what the
#: decoder said the bytes are. GIF and SVG are absent deliberately — SVG is a
#: document with script in it, and an animated GIF is not a photograph of a car.
ALLOWED_IMAGE_FORMATS: dict[str, str] = {
    "JPEG": ".jpg",
    "PNG": ".png",
    "WEBP": ".webp",
}


def max_bytes() -> int:
    return int(settings.UPLOAD_MAX_BYTES)


def max_pixels() -> int:
    return int(settings.UPLOAD_MAX_IMAGE_PIXELS)


def max_edge() -> int:
    return int(settings.UPLOAD_MAX_IMAGE_EDGE)


@dataclass(frozen=True)
class SanitisedImage:
    """A picture we minted ourselves, ready to be stored under a name we chose."""

    content: ContentFile
    image_format: str
    suffix: str
    width: int
    height: int


def generated_name(prefix: str, suffix: str) -> str:
    """``vehicles/2026/09/3f2a….jpg`` — nothing in it came from the uploader.

    The date folders exist so that a year's uploads can be archived or deleted
    as a unit; the uuid is what makes two customers uploading ``car.jpg`` at the
    same second two files rather than one.
    """
    today = datetime.now(UTC)
    return f"{prefix.strip('/')}/{today:%Y}/{today:%m}/{uuid.uuid4().hex}{suffix}"


def _too_big(limit: int) -> str:
    """The one Arabic sentence both size refusals use, in megabytes."""
    return f"حجم الملف أكبر من الحد المسموح ({limit // (1024 * 1024)} ميجابايت)."


def _read_bounded(uploaded) -> bytes:
    """The file's bytes, refusing anything over the ceiling without buffering it.

    ``uploaded.size`` is checked first because it is free, and then the read is
    bounded anyway: ``size`` is whatever the wrapper reported, and a stream that
    lies about it must not be able to spend our memory proving it.
    """
    declared = getattr(uploaded, "size", None)
    limit = max_bytes()
    if declared is not None and declared > limit:
        raise UploadRejected(
            f"upload of {declared} bytes over the {limit} ceiling",
            user_message=_too_big(limit),
            detail={"max_bytes": limit},
        )

    if hasattr(uploaded, "open"):
        uploaded.open()
    if hasattr(uploaded, "seek"):
        uploaded.seek(0)

    data = uploaded.read(limit + 1)
    if len(data) > limit:
        raise UploadRejected(
            f"upload longer than the {limit} byte ceiling",
            user_message=_too_big(limit),
            detail={"max_bytes": limit},
        )
    if not data:
        raise UploadRejected("empty upload", user_message="الملف فارغ.")
    return data


def sanitise_image(uploaded) -> SanitisedImage:
    """Decide from the bytes whether this is a picture, and hand back a new one.

    Everything the caller supplied about the file — its name, its extension,
    its declared content type — is ignored. What comes back is re-encoded from
    the decoded pixels, so no byte of the original body reaches storage.

    Raises :class:`UploadRejected`, in Arabic, for every refusal.
    """
    data = _read_bounded(uploaded)

    # Pillow's own bomb guard, aimed at our ceiling rather than at its default.
    # Set here rather than at import so a test may lower it; it is the backstop
    # for a decode that does not come through this module, while the explicit
    # check below is the one that produces an Arabic sentence.
    Image.MAX_IMAGE_PIXELS = max_pixels()

    try:
        # `Image.open` is lazy: it parses the header and stops. So `.format`
        # and `.size` are known here while nothing has been decoded yet, which
        # is the only moment a bomb can be refused cheaply.
        with Image.open(BytesIO(data)) as probe:
            image_format = (probe.format or "").upper()
            width, height = probe.size
    except UnidentifiedImageError as exc:
        raise UploadRejected(
            "uploaded bytes are not a recognised image",
            user_message="الملف ليس صورة. المسموح: JPG أو PNG أو WEBP.",
        ) from exc
    except Image.DecompressionBombError as exc:
        raise UploadRejected(
            f"decompression bomb refused: {exc}",
            user_message="أبعاد الصورة أكبر من المسموح.",
        ) from exc
    except Exception as exc:  # noqa: BLE001 — a broken header is data, not a crash
        raise UploadRejected(
            f"image header unreadable: {type(exc).__name__}: {exc}",
            user_message="تعذّرت قراءة الصورة.",
        ) from exc

    if image_format not in ALLOWED_IMAGE_FORMATS:
        raise UploadRejected(
            f"image format {image_format!r} is not allowed",
            user_message="نوع الصورة غير مسموح. المسموح: JPG أو PNG أو WEBP.",
            detail={"format": image_format},
        )

    # Both checks, and both before `load()`. The edge catches the long thin
    # image whose total pixel count looks reasonable; the area catches the
    # square one whose edges do.
    if width > max_edge() or height > max_edge() or width * height > max_pixels():
        raise UploadRejected(
            f"image {width}x{height} over the dimension ceiling",
            user_message=(
                f"أبعاد الصورة {width}×{height} أكبر من المسموح "
                f"({max_edge()} بكسل لكل ضلع)."
            ),
            detail={"width": width, "height": height, "max_edge": max_edge()},
        )

    try:
        with Image.open(BytesIO(data)) as picture:
            # Only now is anything decoded. JPEG has no alpha channel, so a
            # transparent source is flattened here rather than failing the save
            # with a message about colour modes. Every other mode is kept as it
            # arrived: converting a palette PNG to RGBA would multiply the size
            # of the very file we are trying to keep small.
            if image_format == "JPEG" and picture.mode not in ("RGB", "L"):
                picture = picture.convert("RGB")
            buffer = BytesIO()
            picture.save(buffer, format=image_format)
    except Image.DecompressionBombError as exc:
        raise UploadRejected(
            f"decompression bomb refused during decode: {exc}",
            user_message="أبعاد الصورة أكبر من المسموح.",
        ) from exc
    except Exception as exc:  # noqa: BLE001 — a truncated body is data too
        raise UploadRejected(
            f"image could not be re-encoded: {type(exc).__name__}: {exc}",
            user_message="تعذّرت قراءة الصورة.",
        ) from exc

    suffix = ALLOWED_IMAGE_FORMATS[image_format]
    return SanitisedImage(
        content=ContentFile(buffer.getvalue()),
        image_format=image_format,
        suffix=suffix,
        width=width,
        height=height,
    )


def vehicle_image_path(instance, filename: str) -> str:  # noqa: ARG001
    """``upload_to`` for a vehicle photograph.

    ``filename`` is accepted and discarded — Django insists on passing it, and
    discarding it *here* is the point: a callable that returns a name of our own
    is what makes the field incapable of writing an uploader-chosen path.
    `ops/checks/one_upload_gate.py` refuses any file field that does not use one
    of these.
    """
    return generated_name("vehicles", _suffix_of(filename))


def vehicle_thumbnail_path(instance, filename: str) -> str:  # noqa: ARG001
    """``upload_to`` for the thumbnail beside it. Same rule, its own folder."""
    return generated_name("vehicles/thumbs", _suffix_of(filename))


def vehicle_preview_path(instance, filename: str) -> str:  # noqa: ARG001
    """``upload_to`` for the detail-screen copy (HR-12). Same rule again.

    Its own folder rather than a suffix on the thumbnail's, for the reason the
    thumbnail has one: "delete every rendered copy and rebuild" is a directory
    somebody can point at, and a mixed directory is a `rm` nobody dares run.
    """
    return generated_name("vehicles/previews", _suffix_of(filename))


def _suffix_of(filename: str) -> str:
    """The extension **we** put on the name we generated, never the uploader's.

    Both callables above are handed the name that `sanitise_image` produced, so
    the suffix is already one of ours. Anything else falls back to `.bin`, which
    is deliberately not an image extension: a file that reached storage without
    passing through this module should look wrong on sight.
    """
    for suffix in ALLOWED_IMAGE_FORMATS.values():
        if filename.lower().endswith(suffix):
            return suffix
    return ".bin"


__all__ = [
    "ALLOWED_IMAGE_FORMATS",
    "SanitisedImage",
    "UploadRejected",
    "generated_name",
    "sanitise_image",
    "vehicle_image_path",
    "vehicle_preview_path",
    "vehicle_thumbnail_path",
]
