"""Render a detector heat-map (2-D float array in [0, 1]) as a transparent PNG overlay."""

import base64
import io

import numpy as np
from PIL import Image

# Low values fade out completely so only the regions that drove the verdict are tinted.
_ALPHA_FLOOR = 0.2
_MAX_ALPHA = 0.8

# Colour stops (value, RGB): yellow → orange → red.
_STOPS = np.array([0.0, 0.5, 1.0], dtype=np.float32)
_COLOURS = np.array([[253, 224, 71], [249, 115, 22], [220, 38, 38]], dtype=np.float32)


def render_heatmap_png(heatmap: np.ndarray, width: int, height: int, max_side: int) -> bytes:
    scale = min(1.0, max_side / max(width, height))
    out_w, out_h = max(1, round(width * scale)), max(1, round(height * scale))

    resized = np.asarray(
        Image.fromarray(heatmap.astype(np.float32)).resize((out_w, out_h), Image.Resampling.BILINEAR)
    )
    values = np.clip(resized, 0.0, 1.0)

    rgb = np.stack([np.interp(values, _STOPS, _COLOURS[:, c]) for c in range(3)], axis=-1)
    alpha = np.clip((values - _ALPHA_FLOOR) / (1 - _ALPHA_FLOOR), 0.0, 1.0) * _MAX_ALPHA
    rgba = np.concatenate([rgb, alpha[..., None] * 255], axis=-1).astype(np.uint8)

    buffer = io.BytesIO()
    Image.fromarray(rgba).save(buffer, format="PNG", optimize=True)
    return buffer.getvalue()


def png_data_url(png: bytes) -> str:
    return "data:image/png;base64," + base64.b64encode(png).decode("ascii")
