"""Deterministic fake detector so the app can be built before the real model exists.

The same image always yields the same result (seeded from its pixels), which keeps demos,
tests and the "seen before" feature stable. Results are clearly versioned as `mock-*`.
"""

import hashlib
import time

import numpy as np
from PIL import Image

from .base import Detector
from .types import Attribution, Cue, CueType, Detection, GeneratorFamily

HEATMAP_SIZE = 64

_CUE_TEXT: dict[CueType, str] = {
    CueType.FREQUENCY_ARTIFACT: "Periodic high-frequency pattern often left by generator upsampling.",
    CueType.TEXTURE_INCONSISTENCY: "Surface texture is unusually smooth or repetitive in this area.",
    CueType.LIGHTING_INCONSISTENCY: "Shading here does not match the apparent light direction.",
    CueType.GEOMETRY_ERROR: "Object edges bend in a physically implausible way.",
    CueType.WARPED_TEXT: "Lettering in this region appears malformed.",
    CueType.NOISE_RESIDUAL: "Camera sensor-noise pattern is weak or inconsistent here.",
}


class MockDetector(Detector):
    name = "mock"

    def __init__(self, latency_ms: int = 0) -> None:
        self._latency_ms = latency_ms
        self._ready = False

    def load(self) -> None:
        self._ready = True

    @property
    def model_version(self) -> str:
        return "mock-0.1"

    @property
    def is_ready(self) -> bool:
        return self._ready

    def predict(self, image: Image.Image) -> Detection:
        if self._latency_ms:
            time.sleep(self._latency_ms / 1000)

        rng = np.random.default_rng(_seed_from_image(image))
        prob_ai = float(rng.beta(0.8, 0.8))

        n_regions = int(rng.integers(1, 4)) if prob_ai >= 0.35 else int(rng.integers(0, 2))
        centers = rng.uniform(0.15, 0.85, size=(n_regions, 2))
        radii = rng.uniform(0.06, 0.18, size=n_regions)

        catalog = list(_CUE_TEXT)
        cue_types = [catalog[i] for i in rng.choice(len(catalog), size=n_regions, replace=False)]
        cues = [
            Cue(
                type=cue_type,
                description=_CUE_TEXT[cue_type],
                region=_bbox(cx, cy, r),
                strength=round(float(np.clip(prob_ai * rng.uniform(0.7, 1.0), 0, 1)), 3),
            )
            for (cx, cy), r, cue_type in zip(centers, radii, cue_types, strict=True)
        ]

        attribution = None
        if prob_ai >= 0.5:
            family = GeneratorFamily.DIFFUSION if rng.random() < 0.75 else GeneratorFamily.GAN
            attribution = Attribution(family=family, confidence=round(float(rng.uniform(0.4, 0.9)), 3))

        return Detection(
            prob_ai=round(prob_ai, 4),
            model_version=self.model_version,
            heatmap=_heatmap(centers, radii),
            cues=cues,
            attribution=attribution,
        )


def _seed_from_image(image: Image.Image) -> int:
    thumb = image.convert("RGB").resize((32, 32))
    return int.from_bytes(hashlib.sha256(thumb.tobytes()).digest()[:8], "big")


def _bbox(cx: float, cy: float, r: float) -> tuple[float, float, float, float]:
    x, y = max(cx - r, 0.0), max(cy - r, 0.0)
    w, h = min(2 * r, 1.0 - x), min(2 * r, 1.0 - y)
    return (round(x, 4), round(y, 4), round(w, 4), round(h, 4))


def _heatmap(centers: np.ndarray, radii: np.ndarray) -> np.ndarray:
    grid = np.linspace(0.0, 1.0, HEATMAP_SIZE, dtype=np.float32)
    xx, yy = np.meshgrid(grid, grid)
    heat = np.zeros((HEATMAP_SIZE, HEATMAP_SIZE), dtype=np.float32)
    for (cx, cy), r in zip(centers, radii, strict=True):
        heat += np.exp(-((xx - cx) ** 2 + (yy - cy) ** 2) / (2 * (r / 1.5) ** 2))
    peak = heat.max()
    return heat / peak if peak > 0 else heat
