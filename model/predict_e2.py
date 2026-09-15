"""SignalScope E2 ("modern" GenImage) inference module — a secondary detector for the combined verdict.

Architecture: torchvision convnext_tiny, classifier[2] → Linear(768, 1)  (same network as E1, retrained)
Checkpoint:   model_state_dict + metadata: architecture, image_size, label_map {'real': 0, 'ai': 1}
Preprocessing: RGB → Resize(256) → CenterCrop(224) → ToTensor() → ImageNet normalisation
Output: single logit — sigmoid → P(AI-generated)
"""

from __future__ import annotations

import logging
from typing import Any

from PIL import Image

from model._checkpoints import resolve_checkpoint
from model.predict import (
    ModelContainer,
    ai_probability,
    build_convnext_tiny,
    make_transforms,
    read_checkpoint,
    select_device,
)

logger = logging.getLogger("signalscope.ml_e2")

MODEL_VERSION = "convnext-tiny-e2-modern"

CHECKPOINT = "signalscope_E2_modern/last_model.pt"
EXPECTED_ARCHITECTURE = "torchvision.convnext_tiny"


def load_model(device: str = "cpu") -> ModelContainer:
    """Load E2 weights once at server startup. Override the path with SIGNALSCOPE_E2_MODEL_PATH."""
    checkpoint_path = resolve_checkpoint(CHECKPOINT, "SIGNALSCOPE_E2_MODEL_PATH")
    target_device = select_device(device)
    logger.info("Loading E2 model from %s on %s...", checkpoint_path, target_device)

    checkpoint = read_checkpoint(checkpoint_path, target_device)

    architecture = checkpoint.get("architecture", EXPECTED_ARCHITECTURE)
    if architecture != EXPECTED_ARCHITECTURE:
        raise ValueError(f"E2 checkpoint architecture is '{architecture}', expected '{EXPECTED_ARCHITECTURE}'")
    label_map = checkpoint.get("label_map", {"real": 0, "ai": 1})
    if label_map.get("ai") != 1:
        raise ValueError(f"E2 checkpoint must label AI images as 1, got label_map={label_map}")

    image_size = int(checkpoint.get("image_size", 224))
    model = build_convnext_tiny(checkpoint["model_state_dict"], target_device)

    logger.info(
        "E2 loaded (epoch=%s, image_size=%s, val_auc=%s)",
        checkpoint.get("epoch", "?"),
        image_size,
        checkpoint.get("metrics", {}).get("val_auc", "?"),
    )
    return ModelContainer(model=model, device=target_device, transform=make_transforms(image_size))


def predict(container: ModelContainer, image: Image.Image) -> dict[str, Any]:
    """Run inference on one PIL image. Returns the secondary-model result shape."""
    logit, prob_ai = ai_probability(container, image)
    ai_prob = round(prob_ai, 4)
    real_prob = round(1.0 - prob_ai, 4)

    logger.info("E2 Inference - logit: %.4f, prob_ai: %.4f", logit, ai_prob)

    return {
        "label": "AI-generated" if ai_prob >= 0.5 else "Real",
        "ai_probability": ai_prob,
        "real_probability": real_prob,
        "confidence": max(ai_prob, real_prob),
        "model_version": MODEL_VERSION,
    }
