"""SignalScope AI-image detection model inference module.

Honours the ML contract (docs/ml-contract.md) with ConvNeXt-Tiny binary classifier:
- Input size: 224 x 224
- Output: single logit
- Label: 0 = Real, 1 = AI-generated
- Preprocessing: RGB -> Resize(256) -> CenterCrop(224) -> ToTensor() -> ImageNet Normalization
- Lightweight evidence: image size, Laplacian variance, high-frequency noise std, EXIF presence.

The loading / inference helpers are shared with model/predict_e2.py (same architecture, retrained).
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import cv2
import numpy as np
import torch
from torch import nn
from torchvision import models, transforms
from PIL import Image

from model._checkpoints import resolve_checkpoint

logger = logging.getLogger("signalscope.ml")

MODEL_VERSION = "convnext-tiny-e1"

CHECKPOINT = "signalscope_E1/E1_convnext_tiny_best.pt"


def make_transforms(image_size: int = 224) -> transforms.Compose:
    """Validation preprocessing used in training: Resize(256) -> CenterCrop(224) -> ImageNet normalisation."""
    return transforms.Compose(
        [
            transforms.Resize(round(image_size * 256 / 224)),
            transforms.CenterCrop(image_size),
            transforms.ToTensor(),
            transforms.Normalize(
                mean=[0.485, 0.456, 0.406],
                std=[0.229, 0.224, 0.225],
            ),
        ]
    )


# Standard validation preprocessing
INFERENCE_TRANSFORMS = make_transforms(224)


def compute_evidence(image: Image.Image) -> dict[str, Any]:
    """Compute lightweight image evidence without claiming to be a separate forensic model."""
    width, height = image.width, image.height
    image_size_str = f"{width}x{height}"

    rgb_np = np.array(image.convert("RGB"))
    gray = cv2.cvtColor(rgb_np, cv2.COLOR_RGB2GRAY)

    lap_var = float(cv2.Laplacian(gray, cv2.CV_64F).var())
    blur = cv2.GaussianBlur(gray, (5, 5), 0)
    noise = gray.astype(np.float32) - blur.astype(np.float32)
    noise_std = float(noise.std())

    exif_present = False
    try:
        exif = image.getexif()
        exif_present = bool(exif and len(exif) > 0)
    except Exception:
        exif_present = False

    return {
        "image_size": image_size_str,
        "sharpness_laplacian_var": round(lap_var, 2),
        "high_frequency_noise_std": round(noise_std, 2),
        "exif_present": exif_present,
    }


class ModelContainer:
    def __init__(self, model: nn.Module, device: torch.device, transform: transforms.Compose = INFERENCE_TRANSFORMS):
        self.model = model
        self.device = device
        self.transform = transform


def select_device(device: str) -> torch.device:
    """Use CUDA if available and requested, otherwise CPU."""
    if device == "cuda" and not torch.cuda.is_available():
        logger.warning("CUDA requested but not available; falling back to CPU")
        return torch.device("cpu")
    return torch.device(device)


def read_checkpoint(checkpoint_path: Path, device: torch.device) -> dict[str, Any]:
    # Use weights_only=False to allow numpy scalar globals saved in PyTorch checkpoints
    checkpoint = torch.load(checkpoint_path, map_location=device, weights_only=False)
    return checkpoint if isinstance(checkpoint, dict) else {"model_state_dict": checkpoint}


def build_convnext_tiny(state_dict: dict[str, Any], device: torch.device) -> nn.Module:
    """torchvision ConvNeXt-Tiny with the classifier head replaced by a single-logit linear layer."""
    model = models.convnext_tiny(weights=None)
    in_features = model.classifier[2].in_features
    model.classifier[2] = nn.Linear(in_features, 1)
    model.load_state_dict(state_dict)
    model.to(device)
    model.eval()
    return model


@torch.inference_mode()
def ai_probability(container: ModelContainer, image: Image.Image) -> tuple[float, float]:
    """Return (raw logit, sigmoid probability of AI-generated) for one image."""
    tensor = container.transform(image.convert("RGB")).unsqueeze(0).to(container.device)

    use_cuda = container.device.type == "cuda"
    with torch.autocast(device_type="cuda", enabled=use_cuda):
        logit = container.model(tensor)

    logit_val = float(logit.reshape(-1)[0].item())
    prob_ai = float(torch.sigmoid(torch.tensor(logit_val)).item())
    return logit_val, max(0.0, min(1.0, prob_ai))


def load_model(device: str = "cpu") -> ModelContainer:
    """Load ConvNeXt-Tiny weights once. Called a single time at server startup.

    Supports configurable path via SIGNALSCOPE_MODEL_PATH or MODEL_PATH.
    """
    checkpoint_path = resolve_checkpoint(CHECKPOINT, "SIGNALSCOPE_MODEL_PATH", "MODEL_PATH")
    target_device = select_device(device)

    logger.info("Loading ConvNeXt-Tiny model from %s on %s...", checkpoint_path, target_device)

    # Supports both model_state_dict and model_state keys
    checkpoint = read_checkpoint(checkpoint_path, target_device)
    state_dict = checkpoint.get("model_state_dict") or checkpoint.get("model_state") or checkpoint
    model = build_convnext_tiny(state_dict, target_device)

    logger.info("SignalScope ConvNeXt-Tiny model successfully loaded and ready.")
    return ModelContainer(model=model, device=target_device)


def predict(container: ModelContainer, image: Image.Image) -> dict[str, Any]:
    """Run inference on ONE image.

    image: PIL image, converted to RGB.
    Returns a dict matching both the ML contract and the required response shape.
    """
    logit_val, prob_ai = ai_probability(container, image)
    real_probability = round(1.0 - prob_ai, 4)
    ai_probability_ = round(prob_ai, 4)

    logger.info(f"Model Inference - Raw logit: {logit_val:.4f}, Prob AI: {ai_probability_:.4f}, Prob Real: {real_probability:.4f}")

    # Predicted label: if ai_probability >= 0.5, label is AI-generated, otherwise Real
    label = "AI-generated" if ai_probability_ >= 0.5 else "Real"
    confidence = max(ai_probability_, real_probability)

    # Lightweight forensic evidence
    evidence = compute_evidence(image)

    return {
        # Required by ML contract
        "prob_ai": ai_probability_,
        "model_version": MODEL_VERSION,
        "heatmap": None,
        "cues": [],
        "attribution": None,
        # Required response fields
        "label": label,
        "ai_probability": ai_probability_,
        "real_probability": real_probability,
        "confidence": confidence,
        "evidence": evidence,
    }
