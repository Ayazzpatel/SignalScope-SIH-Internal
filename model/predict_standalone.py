"""SignalScope Standalone-M (locally-trained timm ConvNeXt-Tiny) inference module.

Architecture: timm convnext_tiny → avg pool → LayerNorm → Dropout(0.25) → Linear(768, 1)
Checkpoint key: model_state
Preprocessing: Resize(224, 224) → Normalize(ImageNet stats)  [albumentations val transforms]
Output: single logit  — sigmoid → prob_ai
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

import cv2
import numpy as np
import torch
from torch import nn
from PIL import Image

logger = logging.getLogger("signalscope.ml_standalone")

MODEL_VERSION = "standalone-m-convnext-tiny"

DEFAULT_CHECKPOINT_PATH = (
    Path(__file__).resolve().parent.parent
    / "app"
    / "backend"
    / "signalscope"
    / "ML"
    / "model"
    / "Standalone_M"
    / "best_model.pt"
)

IMAGE_SIZE = 224
_MEAN = np.array([0.485, 0.456, 0.406], dtype=np.float32)
_STD  = np.array([0.229, 0.224, 0.225], dtype=np.float32)


def _pil_to_tensor(image: Image.Image, size: int) -> torch.Tensor:
    """Replicate albumentations val transforms: Resize → Normalize → ToTensor."""
    rgb = np.array(image.convert("RGB"))
    # Resize to (size, size) using cv2 (same as albumentations default INTER_LINEAR)
    rgb = cv2.resize(rgb, (size, size), interpolation=cv2.INTER_LINEAR).astype(np.float32) / 255.0
    rgb = (rgb - _MEAN) / _STD
    tensor = torch.from_numpy(rgb.transpose(2, 0, 1)).unsqueeze(0)  # (1, 3, H, W)
    return tensor


class _SignalScopeDetector(nn.Module):
    """Mirrors signalscope/model.py from the Local_Training package."""
    def __init__(self):
        super().__init__()
        import timm
        self.backbone = timm.create_model(
            "convnext_tiny",
            pretrained=False,
            num_classes=0,
            global_pool="avg",
        )
        features = self.backbone.num_features
        self.head = nn.Sequential(
            nn.LayerNorm(features),
            nn.Dropout(0.25),
            nn.Linear(features, 1),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.head(self.backbone(x)).squeeze(1)


class ModelContainer:
    def __init__(self, model: nn.Module, device: torch.device, image_size: int):
        self.model = model
        self.device = device
        self.image_size = image_size


def load_model(device: str = "cpu") -> ModelContainer:
    """Load Standalone-M weights once at server startup."""
    model_path_str = os.environ.get("SIGNALSCOPE_STANDALONE_MODEL_PATH")
    checkpoint_path = Path(model_path_str) if model_path_str else DEFAULT_CHECKPOINT_PATH

    if not checkpoint_path.exists():
        raise FileNotFoundError(
            f"Standalone-M checkpoint not found at: {checkpoint_path}. "
            "Set SIGNALSCOPE_STANDALONE_MODEL_PATH in your environment."
        )

    target_device = torch.device(device)
    if device == "cuda" and not torch.cuda.is_available():
        logger.warning("CUDA not available, falling back to CPU")
        target_device = torch.device("cpu")

    logger.info("Loading Standalone-M model from %s on %s...", checkpoint_path, target_device)

    checkpoint = torch.load(checkpoint_path, map_location=target_device, weights_only=False)
    image_size = int(checkpoint.get("image_size", IMAGE_SIZE))

    model = _SignalScopeDetector()
    state_dict = checkpoint.get("model_state", checkpoint)
    model.load_state_dict(state_dict, strict=True)
    model.to(target_device)
    model.eval()

    logger.info("Standalone-M loaded (image_size=%s, val_auc=%s)", image_size,
                checkpoint.get("metrics", {}).get("val", {}).get("roc_auc", "?"))
    return ModelContainer(model=model, device=target_device, image_size=image_size)


@torch.inference_mode()
def predict(container: ModelContainer, image: Image.Image) -> dict[str, Any]:
    """Run inference on one PIL image. Returns dict matching dual-analysis contract."""
    tensor = _pil_to_tensor(image, container.image_size).to(container.device)

    use_cuda = container.device.type == "cuda"
    with torch.autocast(device_type="cuda", enabled=use_cuda):
        logit = container.model(tensor)

    logit_val = float(logit.item() if logit.numel() == 1 else logit[0].item())
    prob_ai = float(torch.sigmoid(torch.tensor(logit_val)).item())
    prob_ai = max(0.0, min(1.0, prob_ai))
    real_probability = round(1.0 - prob_ai, 4)
    ai_probability = round(prob_ai, 4)

    label = "AI-generated" if ai_probability >= 0.5 else "Real"
    confidence = max(ai_probability, real_probability)

    logger.info(
        "Standalone-M Inference - logit: %.4f, prob_ai: %.4f",
        logit_val, ai_probability
    )

    return {
        "label": label,
        "ai_probability": ai_probability,
        "real_probability": real_probability,
        "confidence": confidence,
        "model_version": MODEL_VERSION,
    }
