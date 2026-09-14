from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ExifTags


def basic_evidence(image_path: str | None, pil_image: Image.Image | None = None) -> dict:
    if pil_image is None:
        if image_path is None:
            raise ValueError("image_path or pil_image is required")
        pil_image = Image.open(image_path).convert("RGB")

    image = np.array(pil_image.convert("RGB"))
    gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
    lap_var = float(cv2.Laplacian(gray, cv2.CV_64F).var())
    noise = gray.astype(np.float32) - cv2.GaussianBlur(gray, (5, 5), 0).astype(np.float32)
    noise_std = float(noise.std())
    channels = image.reshape(-1, 3).astype(np.float32)
    channel_std = channels.std(axis=0).round(3).tolist()

    exif_summary = {}
    try:
        exif = pil_image.getexif()
        tag_lookup = {ExifTags.TAGS.get(k, k): v for k, v in exif.items()}
        for key in ["Make", "Model", "Software", "DateTime", "LensModel"]:
            if key in tag_lookup:
                exif_summary[key] = str(tag_lookup[key])
    except Exception:
        exif_summary = {}

    return {
        "filename": Path(image_path).name if image_path else "uploaded_image",
        "width": int(pil_image.width),
        "height": int(pil_image.height),
        "sharpness_laplacian_var": round(lap_var, 3),
        "high_frequency_noise_std": round(noise_std, 3),
        "rgb_channel_std": channel_std,
        "exif": exif_summary,
    }

