import base64
import io

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from signalscope.core.config import get_settings
from signalscope.main import create_app

URL = "/api/v1/analyze"


def post(client, data: bytes, filename: str = "img.jpg", content_type: str = "image/jpeg"):
    return client.post(URL, files={"file": (filename, data, content_type)})


def test_analyze_returns_full_result(client, encode):
    response = post(client, encode("JPEG"))

    assert response.status_code == 200
    body = response.json()
    assert body["detector"] == "mock"
    assert body["verdict"]["band"] in {"likely_real", "uncertain", "likely_ai"}
    assert 0 <= body["verdict"]["prob_ai"] <= 1
    assert body["verdict"]["headline"] and body["verdict"]["summary"]
    assert body["image"] == {
        "width": 128,
        "height": 96,
        "format": "JPEG",
        "size_bytes": body["image"]["size_bytes"],
        "sha256": body["image"]["sha256"],
    }
    assert body["disclaimer"]
    assert body["timings"]["total_ms"] >= body["timings"]["inference_ms"] >= 0
    assert response.headers["X-Request-ID"] == body["request_id"]


def test_heatmap_is_png_overlay_with_image_aspect_ratio(client, encode):
    body = post(client, encode("JPEG", size=(300, 150))).json()

    header, data = body["explanation"]["heatmap_png"].split(",", 1)
    assert header == "data:image/png;base64"
    overlay = Image.open(io.BytesIO(base64.b64decode(data)))
    assert overlay.mode == "RGBA"
    assert overlay.size == (300, 150)


def test_same_image_gives_same_result(client, encode):
    data = encode("PNG")
    first = post(client, data, "a.png", "image/png").json()
    second = post(client, data, "a.png", "image/png").json()

    assert first["verdict"] == second["verdict"]
    assert first["image"]["sha256"] == second["image"]["sha256"]


@pytest.mark.parametrize(("fmt", "mode"), [("PNG", "RGBA"), ("WEBP", "RGB")])
def test_accepts_png_with_alpha_and_webp(client, encode, fmt, mode):
    response = post(client, encode(fmt, mode=mode), f"x.{fmt.lower()}", f"image/{fmt.lower()}")

    assert response.status_code == 200
    assert response.json()["image"]["format"] == fmt


def test_uses_real_format_not_extension(client, encode):
    response = post(client, encode("PNG"), "looks_like.jpg", "image/jpeg")

    assert response.status_code == 200
    assert response.json()["image"]["format"] == "PNG"


def test_request_id_is_echoed(client, encode):
    response = client.post(
        URL, files={"file": ("a.jpg", encode(), "image/jpeg")}, headers={"X-Request-ID": "trace-123"}
    )

    assert response.headers["X-Request-ID"] == "trace-123"
    assert response.json()["request_id"] == "trace-123"


@pytest.mark.parametrize(
    ("data", "status", "code"),
    [
        (b"", 400, "empty_file"),
        (b"definitely not an image", 415, "unsupported_format"),
        (b"GIF89a" + b"\x00" * 64, 415, "unsupported_format"),
    ],
)
def test_rejects_bad_files_with_error_envelope(client, data, status, code):
    response = post(client, data)

    assert response.status_code == status
    error = response.json()["error"]
    assert error["code"] == code
    assert error["message"]
    assert error["request_id"] == response.headers["X-Request-ID"]


def test_rejects_gif(client):
    buffer = io.BytesIO()
    Image.new("RGB", (10, 10)).save(buffer, "GIF")

    response = post(client, buffer.getvalue(), "a.gif", "image/gif")

    assert response.status_code == 415


def test_rejects_truncated_image(client, encode):
    data = encode("JPEG", size=(256, 256))

    response = post(client, data[: len(data) // 2])

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "corrupt_image"


def test_missing_file_field(client):
    response = client.post(URL, data={"other": "x"})

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "invalid_request"


@pytest.fixture
def strict_client(monkeypatch) -> TestClient:
    monkeypatch.setenv("MAX_UPLOAD_MB", "1")
    monkeypatch.setenv("MAX_IMAGE_PIXELS", "10000")
    get_settings.cache_clear()
    with TestClient(create_app()) as test_client:
        yield test_client


def test_rejects_file_over_size_limit(strict_client):
    response = post(strict_client, b"\xff" * (2 * 1024 * 1024))

    assert response.status_code == 413
    assert response.json()["error"]["code"] == "file_too_large"


def test_rejects_too_many_pixels(strict_client, encode):
    response = post(strict_client, encode("PNG", size=(200, 100)), "big.png", "image/png")

    assert response.status_code == 413
    assert response.json()["error"]["code"] == "image_too_large"


def test_analyze_with_signalscope_ml_detector(monkeypatch, encode):
    monkeypatch.setenv("DETECTOR", "ml")
    monkeypatch.setenv("ML_MODULE", "model.predict")
    monkeypatch.setenv("ML_DEVICE", "cpu")
    get_settings.cache_clear()

    with TestClient(create_app()) as ml_client:
        response = post(ml_client, encode("JPEG", size=(256, 256)))
        assert response.status_code == 200
        body = response.json()
        assert body["detector"] == "ml"
        assert body["model_version"] == "convnext-tiny-e1"
        assert body["label"] in {"AI-generated", "Real"}
        assert "ai_probability" in body
        assert "real_probability" in body
        assert "confidence" in body
        assert "evidence" in body
        assert body["evidence"]["image_size"] == "256x256"
        assert "sharpness_laplacian_var" in body["evidence"]
        assert "high_frequency_noise_std" in body["evidence"]
        assert "exif_present" in body["evidence"]

