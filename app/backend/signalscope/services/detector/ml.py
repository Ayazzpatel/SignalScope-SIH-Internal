"""Adapter around the ML team's `model/predict.py` (see docs/ml-contract.md)."""

import importlib
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

from PIL import Image
from pydantic import ValidationError

from .base import Detector
from .types import Detection


class ContractError(RuntimeError):
    """The ML module does not honour docs/ml-contract.md."""


class MLDetector(Detector):
    name = "ml"

    def __init__(self, module: str, root: Path, device: str = "cpu") -> None:
        self._module_name = module
        self._root = root
        self._device = device
        self._module: ModuleType | None = None
        self._model: Any = None
        self._version = "unloaded"

    def load(self) -> None:
        if str(self._root) not in sys.path:
            sys.path.insert(0, str(self._root))
        try:
            module = importlib.import_module(self._module_name)
        except ImportError as exc:
            raise ContractError(
                f"Cannot import ML module '{self._module_name}' from {self._root}. "
                "Set DETECTOR=mock until model/predict.py exists."
            ) from exc

        for fn in ("load_model", "predict"):
            if not callable(getattr(module, fn, None)):
                raise ContractError(f"'{self._module_name}' must define a callable `{fn}()`")

        self._module = module
        self._model = module.load_model(device=self._device)
        if hasattr(module, "MODEL_VERSION"):
            self._version = str(module.MODEL_VERSION)

    @property
    def model_version(self) -> str:
        return self._version

    @property
    def is_ready(self) -> bool:
        return self._module is not None

    def predict(self, image: Image.Image) -> Detection:
        if self._module is None:
            raise RuntimeError("MLDetector.predict() called before load()")

        raw = self._module.predict(self._model, image)
        if not isinstance(raw, dict):
            raise ContractError(f"predict() must return a dict, got {type(raw).__name__}")
        try:
            detection = Detection.model_validate(raw)
        except ValidationError as exc:
            raise ContractError(f"predict() output violates the ML contract:\n{exc}") from exc

        self._version = detection.model_version
        return detection
