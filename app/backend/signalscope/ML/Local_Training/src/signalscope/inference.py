from __future__ import annotations

from pathlib import Path

import torch
from PIL import Image

from signalscope.dataset import tensor_from_pil
from signalscope.evidence import basic_evidence
from signalscope.model import build_model


def load_checkpoint(checkpoint_path: str | Path, device: torch.device):
    checkpoint = torch.load(checkpoint_path, map_location=device)
    model = build_model(pretrained=False)
    model.load_state_dict(checkpoint["model_state"])
    model.to(device)
    model.eval()
    image_size = int(checkpoint.get("image_size", 224))
    return model, image_size, checkpoint


@torch.inference_mode()
def predict_image(model, image: Image.Image, image_size: int, device: torch.device) -> dict:
    tensor = tensor_from_pil(image, image_size).to(device)
    logit = model(tensor)
    prob_ai = float(torch.sigmoid(logit).item())
    label = "AI-generated" if prob_ai >= 0.5 else "Real"
    confidence = prob_ai if prob_ai >= 0.5 else 1.0 - prob_ai
    return {
        "label": label,
        "ai_probability": prob_ai,
        "real_probability": 1.0 - prob_ai,
        "confidence": confidence,
    }


def predict_path(checkpoint_path: str | Path, image_path: str | Path, device: torch.device) -> dict:
    model, image_size, _ = load_checkpoint(checkpoint_path, device)
    image = Image.open(image_path).convert("RGB")
    prediction = predict_image(model, image, image_size, device)
    prediction["evidence"] = basic_evidence(str(image_path), image)
    return prediction

