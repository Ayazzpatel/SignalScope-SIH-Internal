"""Secondary detectors that run beside the primary one and contribute only an AI probability.

Each is a module under `model/` exposing `load_model(device)`, `predict(model, image) -> dict` with an
`ai_probability` key in [0, 1], and optionally `MODEL_VERSION`.
"""

import importlib
import logging
import sys
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from PIL import Image

from signalscope.core.config import Settings

logger = logging.getLogger("signalscope")

# key -> module. Order is the order the models appear in API responses.
AUX_MODULES = {
    "standalone_m": "model.predict_standalone",
    "e2": "model.predict_e2",
}


@dataclass
class AuxModel:
    key: str
    module: str
    container: Any = None
    predict_fn: Callable[[Any, Image.Image], dict[str, Any]] | None = None
    version: str = "unavailable"
    load_error: str | None = None

    @property
    def is_ready(self) -> bool:
        return self.predict_fn is not None

    def load(self, device: str) -> None:
        try:
            module = importlib.import_module(self.module)
            self.container = module.load_model(device)
            self.predict_fn = module.predict
            self.version = str(getattr(module, "MODEL_VERSION", self.module))
        except Exception as exc:  # noqa: BLE001 — a secondary model must never block startup
            self.load_error = f"{type(exc).__name__}: {exc}"
            logger.warning("Secondary model '%s' failed to load and will be skipped: %s", self.key, exc)
        else:
            logger.info("Secondary model '%s' ready (version %s)", self.key, self.version)

    def ai_probability(self, image: Image.Image) -> tuple[float, str]:
        """Return (P(AI), model_version). Raises if the model fails or returns a malformed result."""
        if self.predict_fn is None:
            raise RuntimeError(f"Secondary model '{self.key}' is not loaded")
        raw = self.predict_fn(self.container, image)
        prob = float(raw["ai_probability"])
        if not 0.0 <= prob <= 1.0:  # also rejects NaN
            raise ValueError(f"ai_probability must be within [0, 1], got {prob}")
        return prob, str(raw.get("model_version", self.version))


def load_aux_models(settings: Settings) -> list[AuxModel]:
    if str(settings.ml_root) not in sys.path:
        sys.path.insert(0, str(settings.ml_root))
    models = [AuxModel(key=key, module=module) for key, module in AUX_MODULES.items()]
    for model in models:
        model.load(settings.ml_device)
    return models
