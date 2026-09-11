# ML ↔ App Contract

This is the **only** agreement between the ML team (`/model`) and the application (`/app`).
As long as both sides honour it, either side can change internals freely.

- The app never imports anything from `/model` except the two functions below.
- The ML side never needs to know about HTTP, databases, users or the UI.

---

## 1. Module location

```
/model/predict.py
```

The app imports it as the Python module `model.predict` (repo root is on `sys.path`).
Override with the `ML_MODULE` env var if the path changes.

## 2. Functions

```python
from typing import Any
from PIL import Image

def load_model(device: str = "cpu") -> Any:
    """Load weights once. Called a single time at server startup.

    device: "cpu" or "cuda" (from the ML_DEVICE env var).
    Returns any object; the app passes it back to predict() unchanged.
    """

def predict(model: Any, image: Image.Image) -> dict:
    """Run inference on ONE image.

    image: PIL image, already decoded and converted to RGB by the app.
           Original resolution — the ML side does its own resize/normalise.
    Must be thread-safe for sequential calls (the app runs it in a worker thread).
    Returns a dict matching Section 3.
    """
```

## 3. Output schema

```python
{
    "prob_ai": 0.87,                  # REQUIRED float in [0, 1]. Calibrated P(AI-generated).
    "model_version": "clip-fusion-v1",# REQUIRED str. Changes whenever weights change.

    "heatmap": np.ndarray | None,     # OPTIONAL 2-D float array (H x W), values in [0, 1].
                                      # Any resolution — the app resizes it to the image.
                                      # 1.0 = region that most pushed the verdict.

    "cues": [                         # OPTIONAL list, may be empty.
        {
            "type": "frequency_artifact",   # one of the cue types in Section 4
            "description": "Periodic high-frequency pattern typical of upsampling layers.",
            "region": [0.10, 0.20, 0.30, 0.25],  # OPTIONAL [x, y, w, h], NORMALISED 0–1
                                                 # relative to image width/height. null = global cue.
            "strength": 0.72                # float in [0, 1]
        }
    ],

    "attribution": {                  # OPTIONAL (Module B). null if not supported.
        "family": "diffusion",        # "diffusion" | "gan" | "other"
        "confidence": 0.64            # float in [0, 1]
    }
}
```

### Rules

| Rule | Why |
|---|---|
| `prob_ai` must be **calibrated** (temperature scaling or similar). | The UI shows it as a likelihood. |
| The **app** turns `prob_ai` into a verdict band (`likely_real` / `uncertain` / `likely_ai`). | Presentation and thresholds live in one place. |
| ML team tells the app team the chosen operating threshold(s). | They are set via `BAND_LIKELY_REAL_MAX` / `BAND_LIKELY_AI_MIN`. |
| Cues must be **grounded in measured signals** — never invented text. | Judges score faithfulness (PDF §4.3). |
| No cue may reference a real person, identity or event. | Ethics rules (PDF §1). |
| `predict()` raises an exception on failure — never returns a fake result. | The app reports the error honestly. |

## 4. Cue types

Use one of these values for `cue.type` (ask the app team to add new ones — the UI maps each to an icon and plain-language label):

| `type` | Meaning |
|---|---|
| `frequency_artifact` | Periodic / spectral patterns from generator upsampling |
| `texture_inconsistency` | Implausibly smooth or repeated textures |
| `lighting_inconsistency` | Shadows / reflections disagree with light source |
| `geometry_error` | Physically impossible shapes, warped structures |
| `warped_text` | Garbled or malformed lettering |
| `anatomical_error` | Wrong number/shape of limbs, fingers (non-identifying) |
| `noise_residual` | Sensor-noise pattern missing or inconsistent |
| `other` | Anything else — describe it in `description` |

## 5. Minimal reference implementation

```python
# model/predict.py
import numpy as np

MODEL_VERSION = "dummy-v0"

def load_model(device="cpu"):
    return None

def predict(model, image):
    return {
        "prob_ai": 0.5,
        "model_version": MODEL_VERSION,
        "heatmap": np.zeros((16, 16), dtype=np.float32),
        "cues": [],
        "attribution": None,
    }
```

## 6. How the app switches over

```
DETECTOR=mock   # default — app uses its built-in MockDetector
DETECTOR=ml     # app calls model/predict.py via MLDetector
```

The app validates every `predict()` result against this schema; a mismatch fails loudly with a
clear error message, so contract drift is caught immediately.
