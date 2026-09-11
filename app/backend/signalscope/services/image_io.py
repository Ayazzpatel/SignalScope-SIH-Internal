"""Decode and validate uploaded images. Everything happens in memory — nothing touches disk."""

import hashlib
import io
import warnings
from dataclasses import dataclass

from PIL import Image, ImageOps, UnidentifiedImageError

from signalscope.core.errors import AppError

ALLOWED_FORMATS = {"JPEG": "image/jpeg", "PNG": "image/png", "WEBP": "image/webp"}


@dataclass(frozen=True)
class DecodedImage:
    raw: bytes  # original bytes, used for metadata / provenance
    source: Image.Image  # as decoded, before any transform (keeps EXIF / text chunks)
    rgb: Image.Image  # orientation-corrected RGB, what the detector sees
    format: str
    mime_type: str
    sha256: str

    @property
    def width(self) -> int:
        return self.rgb.width

    @property
    def height(self) -> int:
        return self.rgb.height


def decode_image(raw: bytes, max_pixels: int) -> DecodedImage:
    if not raw:
        raise AppError(400, "empty_file", "The uploaded file is empty.")

    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            source = Image.open(io.BytesIO(raw))
            fmt = source.format or ""
            if fmt not in ALLOWED_FORMATS:
                raise AppError(415, "unsupported_format", "Only JPEG, PNG and WebP images are supported.")
            # Check dimensions from the header before decoding any pixels.
            if source.width * source.height > max_pixels:
                raise AppError(
                    413,
                    "image_too_large",
                    f"Image is {source.width}x{source.height}; the limit is {max_pixels // 1_000_000} megapixels.",
                )
            source.load()
    except AppError:
        raise
    except UnidentifiedImageError as exc:
        raise AppError(415, "unsupported_format", "The file is not a recognised image.") from exc
    except (Image.DecompressionBombError, Image.DecompressionBombWarning) as exc:
        raise AppError(413, "image_too_large", "Image dimensions exceed the allowed limit.") from exc
    except (OSError, SyntaxError, ValueError) as exc:
        raise AppError(422, "corrupt_image", "The image could not be decoded — it may be truncated.") from exc

    return DecodedImage(
        raw=raw,
        source=source,
        rgb=_to_rgb(source),
        format=fmt,
        mime_type=ALLOWED_FORMATS[fmt],
        sha256=hashlib.sha256(raw).hexdigest(),
    )


def _to_rgb(image: Image.Image) -> Image.Image:
    """Apply EXIF orientation, take the first frame, and flatten transparency onto white."""
    if getattr(image, "is_animated", False):
        image.seek(0)
    oriented = ImageOps.exif_transpose(image) or image
    if oriented.mode in ("RGBA", "LA") or (oriented.mode == "P" and "transparency" in oriented.info):
        rgba = oriented.convert("RGBA")
        background = Image.new("RGB", rgba.size, (255, 255, 255))
        background.paste(rgba, mask=rgba.getchannel("A"))
        return background
    return oriented.convert("RGB")
