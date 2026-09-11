import io

from PIL import Image
from PIL.PngImagePlugin import PngInfo

from signalscope.services.provenance import _parse_manifest, extract_provenance

AI_XMP = (
    b"<x:xmpmeta><rdf:Description Iptc4xmpExt:DigitalSourceType="
    b'"http://cv.iptc.org/newscodes/digitalsourcetype/trainedAlgorithmicMedia"/></x:xmpmeta>'
)


def _analyse(data: bytes, mime: str = "image/jpeg"):
    return extract_provenance(data, Image.open(io.BytesIO(data)), mime)


def _jpeg(**save_kwargs) -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (40, 30), "white").save(buffer, "JPEG", **save_kwargs)
    return buffer.getvalue()


def _directions(result) -> set[str]:
    return {s.direction for s in result.signals}


def test_no_metadata_is_reported_neutrally():
    result = _analyse(_jpeg())

    assert not result.exif.present
    assert not result.c2pa.present
    assert _directions(result) == {"neutral"}
    assert "says nothing" in result.signals[0].message


def test_camera_exif_is_weak_real_signal_and_gps_is_presence_only():
    exif = Image.Exif()
    exif[271], exif[272], exif[305] = "Canon", "EOS R5", "Adobe Lightroom"
    exif[0x8825] = {1: "N", 2: (12.0, 34.0, 56.0)}

    result = _analyse(_jpeg(exif=exif))

    assert result.exif.camera_make == "Canon" and result.exif.camera_model == "EOS R5"
    assert result.exif.has_gps is True
    assert "12" not in result.model_dump_json()  # coordinates never leak
    camera = next(s for s in result.signals if s.direction == "real")
    assert "easy to copy or fake" in camera.message


def test_ai_software_in_exif():
    exif = Image.Exif()
    exif[305] = "Adobe Firefly"

    result = _analyse(_jpeg(exif=exif))

    assert "ai" in _directions(result)


def test_png_generation_parameters_chunk():
    meta = PngInfo()
    meta.add_text("parameters", "a ceramic mug, Steps: 30, Sampler: Euler a")
    buffer = io.BytesIO()
    Image.new("RGB", (40, 30)).save(buffer, "PNG", pnginfo=meta)

    result = _analyse(buffer.getvalue(), "image/png")

    signal = next(s for s in result.signals if s.direction == "ai")
    assert signal.source == "embedded_text"
    assert "Automatic1111" in signal.message


def test_iptc_digital_source_type_in_xmp():
    result = _analyse(_jpeg(xmp=AI_XMP))

    signal = next(s for s in result.signals if s.source == "xmp")
    assert signal.direction == "ai"
    assert "fully AI-generated" in signal.message


def test_iptc_term_outside_xmp_packet_is_ignored():
    # e.g. the same URL inside a C2PA manifest must not also count as an XMP declaration
    data = _jpeg(comment=b"digitalsourcetype/trainedAlgorithmicMedia")

    result = _analyse(data)

    assert not any(s.source == "xmp" for s in result.signals)


def test_c2pa_manifest_parsing():
    manifest = {
        "claim_generator_info": [{"name": "Adobe Firefly", "version": "3.0"}],
        "signature_info": {"issuer": "Adobe Inc.", "time": "2026-09-01T10:00:00Z"},
        "assertions": [
            {
                "label": "c2pa.actions.v2",
                "data": {
                    "actions": [
                        {
                            "action": "c2pa.created",
                            "digitalSourceType": "http://cv.iptc.org/newscodes/digitalsourcetype/trainedAlgorithmicMedia",
                        }
                    ]
                },
            }
        ],
    }

    info = _parse_manifest(manifest, "Valid")

    assert info.claim_generator == "Adobe Firefly 3.0"
    assert info.signer == "Adobe Inc."
    assert info.actions == ["c2pa.created"]
    assert info.digital_source_types == ["trainedAlgorithmicMedia"]


def test_file_mentioning_c2pa_without_manifest_does_not_crash():
    data = _jpeg(xmp=b"<x:xmpmeta>c2pa</x:xmpmeta>")

    result = _analyse(data)

    assert result.signals  # handled gracefully either way
