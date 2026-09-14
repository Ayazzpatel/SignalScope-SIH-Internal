from __future__ import annotations

import argparse
import logging
import random
from pathlib import Path

import pandas as pd


IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}

TRAIN_GENERATORS = {
    "adm": ["genimage-adm", "GenImage-ADM"],
    "biggan": ["genimage-biggan", "GenImage-BigGAN"],
    "glide": ["genimage-glide", "GenImage-glide"],
    "midjourney": ["genimage-midjourney", "GenImage-Midjourney-Part-1", "Midjourney"],
    "stable_diffusion_v1_4": ["genimage-stable-diffusion-v1-4", "GenImage-stable-diffusion-v1-4"],
    "vqdm": ["genimage-vqdm", "GenImage-VQDM"],
}

TEST_GENERATORS = {
    "wukong": ["genimage-wukong", "GenImage-wukong"],
}

REAL_HINTS = {"real", "nature", "human", "0_real", "0"}
AI_HINTS = {"ai", "fake", "synthetic", "generated", "1_fake", "1"}


def setup_logging() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s", datefmt="%H:%M:%S")


def find_generator_dir(dataset_root: Path, aliases: list[str]) -> Path:
    for alias in aliases:
        candidate = dataset_root / alias
        if candidate.exists():
            return candidate
    lowered = {p.name.lower(): p for p in dataset_root.iterdir() if p.is_dir()}
    for alias in aliases:
        if alias.lower() in lowered:
            return lowered[alias.lower()]
    raise FileNotFoundError(f"Could not find folder for aliases: {aliases}")


def infer_label(path: Path) -> int | None:
    lower_parts = [p.lower() for p in path.parts]
    for part in reversed(lower_parts):
        tokens = set(part.replace("-", "_").split("_"))
        if part in AI_HINTS or tokens.intersection(AI_HINTS):
            return 1
        if part in REAL_HINTS or tokens.intersection(REAL_HINTS):
            return 0
    return None


def collect_rows(generator_name: str, generator_dir: Path, dataset_root: Path) -> list[dict]:
    rows = []
    skipped = 0
    for path in generator_dir.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in IMAGE_EXTS:
            continue
        label = infer_label(path.relative_to(generator_dir))
        if label is None:
            skipped += 1
            continue
        rows.append(
            {
                "path": path.relative_to(dataset_root).as_posix(),
                "label": label,
                "generator": generator_name,
            }
        )
    if skipped:
        logging.warning("%s: skipped %s images because no real/AI folder label was recognized", generator_name, skipped)
    logging.info("%s: collected %s labeled images", generator_name, len(rows))
    return rows


def stratified_split(rows: list[dict], val_ratio: float, seed: int) -> tuple[list[dict], list[dict]]:
    rng = random.Random(seed)
    buckets: dict[tuple[str, int], list[dict]] = {}
    for row in rows:
        buckets.setdefault((row["generator"], int(row["label"])), []).append(row)

    train_rows, val_rows = [], []
    for bucket in buckets.values():
        rng.shuffle(bucket)
        val_count = max(1, int(len(bucket) * val_ratio)) if len(bucket) > 1 else 0
        val_rows.extend(bucket[:val_count])
        train_rows.extend(bucket[val_count:])

    rng.shuffle(train_rows)
    rng.shuffle(val_rows)
    return train_rows, val_rows


def save_manifest(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(path, index=False)
    logging.info("Wrote %s rows to %s", len(rows), path)


def main() -> None:
    parser = argparse.ArgumentParser(description="Build portable SignalScope manifests from local GenImage folders.")
    parser.add_argument("--dataset-root", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--val-ratio", type=float, default=0.15)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    setup_logging()
    dataset_root = Path(args.dataset_root)
    output_dir = Path(args.output_dir)
    if not dataset_root.exists():
        raise FileNotFoundError(f"Dataset root does not exist: {dataset_root}")

    train_pool = []
    for name, aliases in TRAIN_GENERATORS.items():
        train_pool.extend(collect_rows(name, find_generator_dir(dataset_root, aliases), dataset_root))

    unseen_rows = []
    for name, aliases in TEST_GENERATORS.items():
        unseen_rows.extend(collect_rows(name, find_generator_dir(dataset_root, aliases), dataset_root))

    train_rows, val_rows = stratified_split(train_pool, args.val_ratio, args.seed)
    save_manifest(output_dir / "train.csv", train_rows)
    save_manifest(output_dir / "normal_val.csv", val_rows)
    save_manifest(output_dir / "unseen_wukong.csv", unseen_rows)

    logging.info("Done. Wukong was held out from training and validation.")


if __name__ == "__main__":
    main()
