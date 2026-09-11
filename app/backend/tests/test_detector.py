import sys

import numpy as np
import pytest
from pydantic import ValidationError

from signalscope.services.detector import ContractError, Detection, MLDetector, MockDetector


@pytest.fixture
def mock_detector() -> MockDetector:
    detector = MockDetector()
    detector.load()
    return detector


def test_mock_is_deterministic(mock_detector, image):
    first, second = mock_detector.predict(image), mock_detector.predict(image)

    assert first.prob_ai == second.prob_ai
    assert first.cues == second.cues
    assert np.array_equal(first.heatmap, second.heatmap)


def test_mock_output_honours_contract(mock_detector, image):
    result = mock_detector.predict(image)

    assert 0.0 <= result.prob_ai <= 1.0
    assert result.heatmap.ndim == 2
    assert result.heatmap.min() >= 0.0 and result.heatmap.max() <= 1.0
    for cue in result.cues:
        x, y, w, h = cue.region
        assert x + w <= 1.0 + 1e-6 and y + h <= 1.0 + 1e-6


def test_contract_accepts_minimal_output():
    result = Detection.model_validate({"prob_ai": 0.5, "model_version": "v0"})

    assert result.heatmap is None and result.cues == [] and result.attribution is None


def test_contract_coerces_list_heatmap():
    result = Detection.model_validate({"prob_ai": 0.1, "model_version": "v0", "heatmap": [[0.0, 1.0]]})

    assert isinstance(result.heatmap, np.ndarray)


@pytest.mark.parametrize(
    "bad",
    [
        {"prob_ai": 1.2, "model_version": "v0"},
        {"prob_ai": 0.5, "model_version": ""},
        {"prob_ai": 0.5, "model_version": "v0", "heatmap": [0.1, 0.2]},
        {"prob_ai": 0.5, "model_version": "v0", "heatmap": [[2.0]]},
        {
            "prob_ai": 0.5,
            "model_version": "v0",
            "cues": [{"type": "made_up", "description": "x", "strength": 1}],
        },
    ],
)
def test_contract_rejects_bad_output(bad):
    with pytest.raises(ValidationError):
        Detection.model_validate(bad)


def test_ml_detector_uses_contract_module(tmp_path, image):
    pkg = tmp_path / "fake_model"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("")
    (pkg / "predict.py").write_text(
        "def load_model(device='cpu'):\n"
        "    return {'device': device}\n"
        "def predict(model, image):\n"
        "    return {'prob_ai': 0.9, 'model_version': 'fake-1', 'heatmap': [[0.0, 0.5], [0.5, 1.0]]}\n"
    )
    detector = MLDetector(module="fake_model.predict", root=tmp_path)
    try:
        detector.load()
        result = detector.predict(image)
    finally:
        sys.modules.pop("fake_model.predict", None)
        sys.modules.pop("fake_model", None)

    assert detector.is_ready
    assert result.prob_ai == 0.9
    assert detector.model_version == "fake-1"


def test_ml_detector_fails_clearly_when_module_missing(tmp_path):
    detector = MLDetector(module="does_not_exist.predict", root=tmp_path)

    with pytest.raises(ContractError, match="DETECTOR=mock"):
        detector.load()
