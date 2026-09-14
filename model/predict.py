"""SignalScope AI-image detection model inference module.

Honours the ML contract (docs/ml-contract.md) with ConvNeXt-Tiny binary classifier:
- Input size: 224 x 224
- Output: single logit
- Label: 0 = Real, 1 = AI-generated
- Preprocessing: RGB -> Resize(256) -> CenterCrop(224) -> ToTensor() -> ImageNet Normalization
- Lightweight evidence: image size, Laplacian variance, high-frequency noise std, EXIF presence.
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
from torchvision import models, transforms
from PIL import Image

logger = logging.getLogger("signalscope.ml")

MODEL_VERSION = "convnext-tiny-e1"

DEFAULT_CHECKPOINT_PATH = (
    Path(__file__).resolve().parent.parent
    / "app"
    / "backend"
    / "signalscope"
    / "ML"
    / "model"
    / "signalscope_E1"
    / "E1_convnext_tiny_best.pt"
)

# Standard validation preprocessing
INFERENCE_TRANSFORMS = transforms.Compose(
    [
        transforms.Resize(256),
        transforms.CenterCrop(224),
        transforms.ToTensor(),
        transforms.Normalize(
            mean=[0.485, 0.456, 0.406],
            std=[0.229, 0.224, 0.225],
        ),
    ]
)


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
    def __init__(self, model: nn.Module, device: torch.device):
        self.model = model
        self.device = device


def load_model(device: str = "cpu") -> ModelContainer:
    """Load ConvNeXt-Tiny weights once. Called a single time at server startup.

    Supports configurable path via SIGNALSCOPE_MODEL_PATH or MODEL_PATH.
    """
    model_path_str = os.environ.get("SIGNALSCOPE_MODEL_PATH") or os.environ.get("MODEL_PATH")
    if model_path_str:
        checkpoint_path = Path(model_path_str)
    else:
        checkpoint_path = DEFAULT_CHECKPOINT_PATH

    if not checkpoint_path.exists():
        raise FileNotFoundError(
            f"SignalScope model checkpoint not found at: {checkpoint_path}. "
            "Set SIGNALSCOPE_MODEL_PATH in your environment or backend .env file."
        )

    # Use CUDA if available and requested, otherwise CPU
    if device == "cuda" and not torch.cuda.is_available():
        logger.warning("CUDA requested but not available; falling back to CPU")
        target_device = torch.device("cpu")
    else:
        target_device = torch.device(device)

    logger.info("Loading ConvNeXt-Tiny model from %s on %s...", checkpoint_path, target_device)

    # Build ConvNeXt-Tiny architecture and replace classifier head with single-output linear layer
    model = models.convnext_tiny(weights=None)
    in_features = model.classifier[2].in_features
    model.classifier[2] = nn.Linear(in_features, 1)

    # Load checkpoint supporting both model_state_dict and model_state keys
    # Use weights_only=False to allow numpy scalar globals saved in PyTorch checkpoints
    checkpoint = torch.load(checkpoint_path, map_location=target_device, weights_only=False)

    if isinstance(checkpoint, dict):
        if "model_state_dict" in checkpoint:
            state_dict = checkpoint["model_state_dict"]
        elif "model_state" in checkpoint:
            state_dict = checkpoint["model_state"]
        else:
            state_dict = checkpoint
    else:
        state_dict = checkpoint

    model.load_state_dict(state_dict)
    model.to(target_device)
    model.eval()

    logger.info("SignalScope ConvNeXt-Tiny model successfully loaded and ready.")
    return ModelContainer(model=model, device=target_device)


@torch.inference_mode()
def predict(container: ModelContainer, image: Image.Image) -> dict[str, Any]:
    """Run inference on ONE image.

    image: PIL image, converted to RGB.
    Returns a dict matching both the ML contract and the required response shape.
    """
    model = container.model
    device = container.device

    rgb_image = image.convert("RGB")
    tensor = INFERENCE_TRANSFORMS(rgb_image).unsqueeze(0).to(device)

    use_cuda = device.type == "cuda"
    with torch.autocast(device_type="cuda", enabled=use_cuda):
        logit = model(tensor)

    # Output logit -> sigmoid probability
    if logit.dim() > 1:
        logit = logit.squeeze()
    logit_val = float(logit.item() if logit.numel() == 1 else logit[0].item())

    prob_ai = float(torch.sigmoid(torch.tensor(logit_val)).item())
    prob_ai = max(0.0, min(1.0, prob_ai))
    real_probability = round(1.0 - prob_ai, 4)
    ai_probability = round(prob_ai, 4)

    logger.info(f"Model Inference - Raw logit: {logit_val:.4f}, Prob AI: {ai_probability:.4f}, Prob Real: {real_probability:.4f}")

    # Predicted label: if ai_probability >= 0.5, label is AI-generated, otherwise Real
    label = "AI-generated" if ai_probability >= 0.5 else "Real"
    confidence = max(ai_probability, real_probability)

    # Lightweight forensic evidence
    evidence = compute_evidence(image)

    return {
        # Required by ML contract
        "prob_ai": ai_probability,
        "model_version": MODEL_VERSION,
        "heatmap": None,
        "cues": [],
        "attribution": None,
        # Required response fields
        "label": label,
        "ai_probability": ai_probability,
        "real_probability": real_probability,
        "confidence": confidence,
        "evidence": evidence,
    }
