from __future__ import annotations

import logging
from pathlib import Path

import albumentations as A
import cv2
import numpy as np
import pandas as pd
import torch
from albumentations.pytorch import ToTensorV2
from torch.utils.data import Dataset


LABEL_MAP = {
    "0": 0,
    "1": 1,
    "real": 0,
    "human": 0,
    "natural": 0,
    "authentic": 0,
    "ai": 1,
    "fake": 1,
    "synthetic": 1,
    "generated": 1,
}


def normalize_label(value) -> int:
    key = str(value).strip().lower()
    if key not in LABEL_MAP:
        raise ValueError(f"Unsupported label value: {value!r}")
    return LABEL_MAP[key]


def resolve_image_path(raw_path: str, dataset_root: str | Path | None) -> Path:
    path = Path(str(raw_path))
    if path.is_absolute() and path.exists():
        return path

    if dataset_root is None:
        return path

    root = Path(dataset_root)
    if not path.is_absolute():
        return root / path

    parts = path.parts
    for idx, part in enumerate(parts):
        if part.lower().startswith("genimage"):
            return root.joinpath(*parts[idx:])

    return root / path.name


def load_manifest(csv_path: str | Path, dataset_root: str | Path | None = None) -> pd.DataFrame:
    df = pd.read_csv(csv_path)
    if "path" not in df.columns or "label" not in df.columns:
        raise ValueError(f"{csv_path} must contain columns: path,label")

    df = df[["path", "label"]].copy()
    df["label"] = df["label"].map(normalize_label)
    df["resolved_path"] = df["path"].map(lambda p: str(resolve_image_path(p, dataset_root)))
    return df


def verify_paths(df: pd.DataFrame, sample_limit: int | None = None) -> None:
    paths = df["resolved_path"].tolist()
    if sample_limit is not None:
        paths = paths[:sample_limit]
    missing = [p for p in paths if not Path(p).exists()]
    if missing:
        preview = "\n".join(missing[:10])
        raise FileNotFoundError(f"Missing {len(missing)} image files. First missing paths:\n{preview}")
    logging.info("Verified %s image paths", len(paths))


def make_transforms(image_size: int, train: bool) -> A.Compose:
    if train:
        return A.Compose(
            [
                A.RandomResizedCrop(image_size, image_size, scale=(0.75, 1.0), ratio=(0.9, 1.1), p=1.0),
                A.HorizontalFlip(p=0.5),
                A.OneOf(
                    [
                        A.ImageCompression(quality_lower=45, quality_upper=95, p=1.0),
                        A.GaussianBlur(blur_limit=(3, 5), p=1.0),
                    ],
                    p=0.45,
                ),
                A.ColorJitter(brightness=0.18, contrast=0.18, saturation=0.18, hue=0.04, p=0.45),
                A.Normalize(mean=(0.485, 0.456, 0.406), std=(0.229, 0.224, 0.225)),
                ToTensorV2(),
            ]
        )
    return A.Compose(
        [
            A.Resize(image_size, image_size),
            A.Normalize(mean=(0.485, 0.456, 0.406), std=(0.229, 0.224, 0.225)),
            ToTensorV2(),
        ]
    )


class SignalScopeDataset(Dataset):
    def __init__(self, manifest: pd.DataFrame, image_size: int, train: bool):
        self.df = manifest.reset_index(drop=True)
        self.transforms = make_transforms(image_size, train=train)

    def __len__(self) -> int:
        return len(self.df)

    def __getitem__(self, idx: int):
        row = self.df.iloc[idx]
        path = row["resolved_path"]
        image = cv2.imread(path, cv2.IMREAD_COLOR)
        if image is None:
            raise FileNotFoundError(f"Could not read image: {path}")
        image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        image = self.transforms(image=image)["image"]
        label = torch.tensor(float(row["label"]), dtype=torch.float32)
        return image, label, path


def tensor_from_pil(image, image_size: int) -> torch.Tensor:
    image = np.array(image.convert("RGB"))
    transformed = make_transforms(image_size, train=False)(image=image)["image"]
    return transformed.unsqueeze(0)

