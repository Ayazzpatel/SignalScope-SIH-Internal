"""Module D — provenance & metadata evidence.

Metadata is shown *alongside* the model verdict, never as a replacement: it is trivially stripped or forged.
Absence of metadata is not evidence of anything and is reported neutrally.
"""

import io
import logging
import re
from typing import Any

from PIL import ExifTags, Image

from signalscope.schemas.analysis import (
    C2PAInfo,
    ExifInfo,
    Provenance,
    ProvenanceSignal,
    SignalDirection,
    SignalSource,
)

logger = logging.getLogger("signalscope")

# IPTC Digital Source Type terms that declare generative-AI involvement.
_AI_SOURCE_TYPES = {
    "trainedAlgorithmicMedia": "fully AI-generated",
    "compositeWithTrainedAlgorithmicMedia": "partly AI-generated (composite)",
    "algorithmicMedia": "algorithmically generated (not a camera capture)",
}
_CAMERA_SOURCE_TYPE = "digitalCapture"

# Substrings of Software / generator names that point to generative tools.
_AI_TOOL_PATTERNS = re.compile(
    r"stable[\s-]?diffusion|midjourney|dall[\s·-]?e|firefly|novelai|comfyui|automatic1111|invokeai|"
    r"imagen|gemini|flux|leonardo|ideogram|dreamstudio|nightcafe|openai",
    re.IGNORECASE,
)
# PNG text chunks written by popular local generation UIs.
_GENERATOR_TEXT_KEYS = {
    "parameters": "Stable Diffusion WebUI (Automatic1111 / Forge)",
    "prompt": "ComfyUI",
    "workflow": "ComfyUI",
    "invokeai_metadata": "InvokeAI",
    "sd-metadata": "InvokeAI",
    "dream": "InvokeAI",
}

_EXIF_IFD = 0x8769
_GPS_IFD = 0x8825
_TAGS = {name: tag for tag, name in ExifTags.TAGS.items()}


def extract_provenance(raw: bytes, source: Image.Image, mime_type: str) -> Provenance:
    signals: list[ProvenanceSignal] = []

    exif = _read_exif(source)
    signals += _exif_signals(exif)
    signals += _text_chunk_signals(source)
    signals += _xmp_signals(source)

    c2pa = _read_c2pa(raw, mime_type)
    signals += _c2pa_signals(c2pa)

    if not signals:
        signals.append(
            ProvenanceSignal(
                source=SignalSource.NONE,
                direction=SignalDirection.NEUTRAL,
                message="No provenance metadata found. This is common — most platforms strip metadata "
                "on upload — so it says nothing about whether the image is real or AI-generated.",
            )
        )

    return Provenance(exif=exif, c2pa=c2pa, signals=_dedupe(signals))


# --------------------------------------------------------------------------- EXIF


def _read_exif(image: Image.Image) -> ExifInfo:
    try:
        exif = image.getexif()
    except Exception:  # malformed EXIF must never break analysis
        return ExifInfo(present=False)
    if not exif:
        return ExifInfo(present=False)

    sub = exif.get_ifd(_EXIF_IFD)

    def text(value: Any) -> str | None:
        if value is None:
            return None
        if isinstance(value, bytes):
            value = value.decode("utf-8", "ignore")
        cleaned = str(value).strip("\x00 ").strip()
        return cleaned[:200] or None

    return ExifInfo(
        present=True,
        camera_make=text(exif.get(_TAGS["Make"])),
        camera_model=text(exif.get(_TAGS["Model"])),
        software=text(exif.get(_TAGS["Software"])),
        captured_at=text(sub.get(_TAGS["DateTimeOriginal"]) or exif.get(_TAGS["DateTime"])),
        lens_model=text(sub.get(_TAGS["LensModel"])),
        # Only report that location data exists — never return coordinates.
        has_gps=bool(exif.get_ifd(_GPS_IFD)),
    )


def _exif_signals(exif: ExifInfo) -> list[ProvenanceSignal]:
    signals: list[ProvenanceSignal] = []
    if not exif.present:
        return signals

    if exif.software and _AI_TOOL_PATTERNS.search(exif.software):
        signals.append(
            ProvenanceSignal(
                source=SignalSource.EXIF,
                direction=SignalDirection.AI,
                message=f"EXIF 'Software' field names a generative tool: {exif.software}.",
            )
        )
    elif exif.software:
        signals.append(
            ProvenanceSignal(
                source=SignalSource.EXIF,
                direction=SignalDirection.NEUTRAL,
                message=f"Processed with {exif.software}. Editing software alone does not indicate AI.",
            )
        )

    if exif.camera_make or exif.camera_model:
        camera = " ".join(filter(None, [exif.camera_make, exif.camera_model]))
        signals.append(
            ProvenanceSignal(
                source=SignalSource.EXIF,
                direction=SignalDirection.REAL,
                message=f"EXIF names a capture device ({camera}). Weak evidence — EXIF is easy to copy or fake.",
            )
        )
    return signals


# --------------------------------------------------------------------------- PNG / WebP text chunks


def _text_chunk_signals(image: Image.Image) -> list[ProvenanceSignal]:
    signals: list[ProvenanceSignal] = []
    info = {str(k).lower(): v for k, v in image.info.items() if isinstance(v, str | bytes)}

    for key, tool in _GENERATOR_TEXT_KEYS.items():
        if key in info:
            signals.append(
                ProvenanceSignal(
                    source=SignalSource.EMBEDDED_TEXT,
                    direction=SignalDirection.AI,
                    message=f"Contains a '{key}' text block of the kind written by {tool}.",
                )
            )

    for key in ("software", "comment", "description", "author"):
        value = info.get(key)
        if isinstance(value, bytes):
            value = value.decode("utf-8", "ignore")
        if value and _AI_TOOL_PATTERNS.search(value[:2000]):
            match = _AI_TOOL_PATTERNS.search(value[:2000])
            signals.append(
                ProvenanceSignal(
                    source=SignalSource.EMBEDDED_TEXT,
                    direction=SignalDirection.AI,
                    message=f"Embedded '{key}' text mentions a generative tool ({match.group(0)}).",
                )
            )
    return signals


# --------------------------------------------------------------------------- XMP / IPTC


def _xmp_packet(image: Image.Image) -> bytes:
    # JPEG/WebP expose XMP as info["xmp"]; PNG as an iTXt chunk named "XML:com.adobe.xmp".
    for key in ("xmp", "XML:com.adobe.xmp"):
        value = image.info.get(key)
        if value:
            return value if isinstance(value, bytes) else str(value).encode("utf-8", "ignore")
    return b""


def _xmp_signals(image: Image.Image) -> list[ProvenanceSignal]:
    # IPTC DigitalSourceType lives in the XMP packet. Scanning only that packet (not the whole file)
    # avoids double-counting the same term inside a C2PA manifest. Cheap byte scan, no XML parse.
    raw = _xmp_packet(image)
    signals: list[ProvenanceSignal] = []
    if not raw:
        return signals
    for term, meaning in _AI_SOURCE_TYPES.items():
        if re.search(rb"digitalsourcetype/" + term.encode() + rb"\b", raw, re.IGNORECASE):
            signals.append(
                ProvenanceSignal(
                    source=SignalSource.XMP,
                    direction=SignalDirection.AI,
                    message=f"IPTC metadata declares the image as {meaning}.",
                )
            )
            break
    else:
        if re.search(rb"digitalsourcetype/" + _CAMERA_SOURCE_TYPE.encode() + rb"\b", raw, re.IGNORECASE):
            signals.append(
                ProvenanceSignal(
                    source=SignalSource.XMP,
                    direction=SignalDirection.REAL,
                    message="IPTC metadata declares a digital camera capture (unsigned, so it can be edited).",
                )
            )
    return signals


# --------------------------------------------------------------------------- C2PA / Content Credentials


def _read_c2pa(raw: bytes, mime_type: str) -> C2PAInfo:
    if b"c2pa" not in raw:  # JUMBF manifests always carry the 'c2pa' label — skip the SDK when absent
        return C2PAInfo(present=False, checked=True)
    try:
        import c2pa
    except ImportError:
        return C2PAInfo(present=False, checked=False, error="Content Credentials library not installed.")

    reader = None
    try:
        # Never fetch remote manifests: no outbound network calls triggered by user uploads.
        context = c2pa.Context(c2pa.Settings.from_dict({"verify": {"remote_manifest_fetch": False}}))
        reader = c2pa.Reader.try_create(mime_type, io.BytesIO(raw), context=context)
        if reader is None:
            return C2PAInfo(present=False, checked=True)
        return _parse_manifest(reader.get_active_manifest() or {}, reader.get_validation_state())
    except Exception as exc:
        logger.warning("C2PA read failed: %s", exc)
        return C2PAInfo(present=True, checked=False, error="Content Credentials found but could not be read.")
    finally:
        if reader is not None:
            reader.close()


def _parse_manifest(manifest: dict[str, Any], validation_state: str | None) -> C2PAInfo:
    generator = manifest.get("claim_generator")
    info_list = manifest.get("claim_generator_info") or []
    if not generator and info_list and isinstance(info_list[0], dict):
        first = info_list[0]
        generator = " ".join(filter(None, [first.get("name"), first.get("version")]))

    signature = manifest.get("signature_info") or {}
    source_types: list[str] = []
    actions: list[str] = []
    for assertion in manifest.get("assertions") or []:
        if not str(assertion.get("label", "")).startswith("c2pa.actions"):
            continue
        for action in (assertion.get("data") or {}).get("actions") or []:
            if action.get("action"):
                actions.append(str(action["action"]))
            if action.get("digitalSourceType"):
                source_types.append(str(action["digitalSourceType"]).rsplit("/", 1)[-1])

    return C2PAInfo(
        present=True,
        checked=True,
        validation_state=validation_state,
        claim_generator=generator,
        signer=signature.get("issuer") or signature.get("common_name"),
        signed_at=signature.get("time"),
        actions=sorted(set(actions)),
        digital_source_types=sorted(set(source_types)),
    )


def _c2pa_signals(info: C2PAInfo) -> list[ProvenanceSignal]:
    if not info.present:
        return []
    if not info.checked:
        return [
            ProvenanceSignal(
                source=SignalSource.C2PA, direction=SignalDirection.NEUTRAL, message=info.error or ""
            )
        ]

    signals: list[ProvenanceSignal] = []
    state = (info.validation_state or "").lower()
    if state == "invalid":
        signals.append(
            ProvenanceSignal(
                source=SignalSource.C2PA,
                direction=SignalDirection.NEUTRAL,
                message="Content Credentials are present but FAILED validation — the file may have been "
                "altered after signing. Treat its claims with caution.",
            )
        )
    else:
        by = f" signed by {info.signer}" if info.signer else ""
        signals.append(
            ProvenanceSignal(
                source=SignalSource.C2PA,
                direction=SignalDirection.NEUTRAL,
                message=f"Content Credentials found{by} (validation: {info.validation_state or 'unknown'}).",
            )
        )

    declared_ai = [t for t in info.digital_source_types if t in _AI_SOURCE_TYPES]
    if declared_ai:
        signals.append(
            ProvenanceSignal(
                source=SignalSource.C2PA,
                direction=SignalDirection.AI,
                message=f"Content Credentials declare the image as {_AI_SOURCE_TYPES[declared_ai[0]]}.",
            )
        )
    elif _CAMERA_SOURCE_TYPE in info.digital_source_types:
        signals.append(
            ProvenanceSignal(
                source=SignalSource.C2PA,
                direction=SignalDirection.REAL,
                message="Content Credentials declare a digital camera capture.",
            )
        )
    return signals


def _dedupe(signals: list[ProvenanceSignal]) -> list[ProvenanceSignal]:
    seen: set[str] = set()
    unique = []
    for signal in signals:
        if signal.message not in seen:
            seen.add(signal.message)
            unique.append(signal)
    return unique
