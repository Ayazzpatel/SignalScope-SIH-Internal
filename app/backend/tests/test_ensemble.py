"""Combined verdict across the primary detector and the secondary models."""

import asyncio
import io
import re

import numpy as np
import pytest
from PIL import Image

from signalscope.core.config import get_settings
from signalscope.schemas.analysis import VerdictBand
from signalscope.services.analysis import AnalysisService
from signalscope.services.aux_models import AuxModel
from signalscope.services.detector import Detection, Detector
from signalscope.services.verdict import make_ensemble_verdict

URL = "/api/v1/analyze/ensemble"
THRESHOLD = 0.25


@pytest.mark.parametrize(
    ("probs", "band"),
    [
        ([0.0, 0.1, 0.2499], VerdictBand.LIKELY_REAL),
        ([0.25, 0.0, 0.0], VerdictBand.LIKELY_AI),  # the threshold itself counts as AI
        ([0.01, 0.02, 0.9], VerdictBand.LIKELY_AI),  # any single model is enough
        ([0.3], VerdictBand.LIKELY_AI),
    ],
)
def test_any_model_over_threshold_flags_ai(probs, band):
    verdict = make_ensemble_verdict(probs, THRESHOLD)

    assert verdict.band == band
    assert verdict.prob_ai == max(probs)


@pytest.mark.parametrize("probs", [[0.0], [0.24], [0.25], [0.99]])
def test_ensemble_wording_never_overclaims(probs):
    verdict = make_ensemble_verdict(probs, THRESHOLD)
    text = f"{verdict.headline} {verdict.summary}".lower()

    for banned in ("fake", "certain", "certainly", "definitely", "proof", "100%"):
        assert not re.search(rf"\b{re.escape(banned)}(?!\w)", text), banned


def test_ensemble_needs_a_probability():
    with pytest.raises(ValueError):
        make_ensemble_verdict([], THRESHOLD)


def test_ensemble_endpoint_with_mock_detector(client, encode):
    response = client.post(URL, files={"file": ("a.jpg", encode(), "image/jpeg")})

    assert response.status_code == 200
    body = response.json()
    assert body["final"]["band"] in {"likely_real", "likely_ai"}
    assert body["final"]["thresholds"] == {"likely_real_max": 0.25, "likely_ai_min": 0.25}
    # Secondary models only load with DETECTOR=ml, so the mock detector stands alone.
    assert [m["key"] for m in body["models"]] == ["e1"]
    assert body["analysis"]["detector"] == "mock"
    assert body["analysis"]["image"]["format"] == "JPEG"


def test_ensemble_endpoint_rejects_bad_files(client):
    response = client.post(URL, files={"file": ("a.jpg", b"not an image", "image/jpeg")})

    assert response.status_code == 415
    assert response.json()["error"]["code"] == "unsupported_format"


class _FixedDetector(Detector):
    name = "ml"

    def __init__(self, prob_ai: float) -> None:
        self._prob_ai = prob_ai

    def load(self) -> None: ...

    def predict(self, image: Image.Image) -> Detection:
        return Detection(prob_ai=self._prob_ai, model_version="fixed-e1")

    @property
    def model_version(self) -> str:
        return "fixed-e1"

    @property
    def is_ready(self) -> bool:
        return True


def _aux(key: str, prob: float | None) -> AuxModel:
    if prob is None:
        return AuxModel(key=key, module="n/a", load_error="ImportError: missing")

    def predict(_container, _image):
        return {"ai_probability": prob, "model_version": f"{key}-v1"}

    return AuxModel(key=key, module="n/a", predict_fn=predict, version=f"{key}-v1")


def _broken_aux(key: str) -> AuxModel:
    def predict(_container, _image):
        raise RuntimeError("boom")

    return AuxModel(key=key, module="n/a", predict_fn=predict, version=f"{key}-v1")


def _jpeg() -> bytes:
    pixels = np.random.default_rng(2).integers(0, 256, size=(64, 64, 3), dtype=np.uint8)
    buffer = io.BytesIO()
    Image.fromarray(pixels).save(buffer, "JPEG")
    return buffer.getvalue()


def _run(primary: float, *aux_models: AuxModel):
    service = AnalysisService(_FixedDetector(primary), get_settings(), aux_models)
    return asyncio.run(service.analyze_ensemble(_jpeg(), "req-1"))


def test_a_secondary_model_alone_can_flag_ai():
    result = _run(0.05, _aux("standalone_m", 0.1), _aux("e2", 0.3))

    assert result.final.band == VerdictBand.LIKELY_AI
    assert result.final.prob_ai == 0.3
    assert [m.key for m in result.models] == ["e1", "standalone_m", "e2"]
    assert result.analysis.ai_probability == 0.05


def test_all_models_low_is_likely_real():
    result = _run(0.05, _aux("standalone_m", 0.1), _aux("e2", 0.2))

    assert result.final.band == VerdictBand.LIKELY_REAL


def test_failed_secondary_models_are_reported_and_excluded():
    result = _run(0.05, _aux("standalone_m", None), _broken_aux("e2"))

    assert result.final.band == VerdictBand.LIKELY_REAL
    by_key = {m.key: m for m in result.models}
    assert by_key["standalone_m"].error == "Model is not loaded."
    assert by_key["e2"].error == "Inference failed."
    assert by_key["e2"].ai_probability is None
    assert "boom" not in (by_key["e2"].error or "")  # internals stay in the server log


def test_out_of_range_secondary_output_is_rejected():
    result = _run(0.05, _aux("e2", 1.5))

    assert result.models[1].error == "Inference failed."
    assert result.final.band == VerdictBand.LIKELY_REAL
