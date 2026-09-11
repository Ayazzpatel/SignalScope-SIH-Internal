from signalscope.core.config import Settings

from .base import Detector
from .ml import ContractError, MLDetector
from .mock import MockDetector
from .types import Attribution, Cue, CueType, Detection, GeneratorFamily

__all__ = [
    "Attribution",
    "ContractError",
    "Cue",
    "CueType",
    "Detection",
    "Detector",
    "GeneratorFamily",
    "MLDetector",
    "MockDetector",
    "build_detector",
]


def build_detector(settings: Settings) -> Detector:
    if settings.detector == "ml":
        return MLDetector(module=settings.ml_module, root=settings.ml_root, device=settings.ml_device)
    return MockDetector(latency_ms=settings.mock_latency_ms)
