from __future__ import annotations

import argparse
import logging
from pathlib import Path

import pandas as pd


MANIFESTS = ["train.csv", "normal_val.csv", "unseen_wukong.csv"]


def setup_logging():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s", datefmt="%H:%M:%S")


def portable_tail(raw_path: str) -> Path:
    path = Path(str(raw_path))
    parts = path.parts
    for idx, part in enumerate(parts):
        if part.lower().startswith("genimage"):
            return Path(*parts[idx:])
    return Path(path.name)


def resolve(raw_path: str, dataset_root: Path) -> Path:
    path = Path(str(raw_path))
    if path.is_absolute() and path.exists():
        return path
    if not path.is_absolute():
        candidate = dataset_root / path
        if candidate.exists():
            return candidate
    return dataset_root / portable_tail(raw_path)


def rewrite_manifest(input_csv: Path, output_csv: Path, dataset_root: Path) -> None:
    df = pd.read_csv(input_csv)
    if "path" not in df.columns or "label" not in df.columns:
        raise ValueError(f"{input_csv} must contain columns: path,label")
    df = df.copy()
    df["path"] = df["path"].map(lambda p: str(portable_tail(p)).replace("\\", "/"))
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_csv, index=False)
    logging.info("Rewrote %s -> %s using portable paths under %s", input_csv, output_csv, dataset_root)


def validate_manifest(input_csv: Path, dataset_root: Path) -> None:
    df = pd.read_csv(input_csv)
    if "path" not in df.columns or "label" not in df.columns:
        raise ValueError(f"{input_csv} must contain columns: path,label")
    missing = []
    for raw_path in df["path"].tolist():
        if not resolve(raw_path, dataset_root).exists():
            missing.append(str(resolve(raw_path, dataset_root)))
    if missing:
        preview = "\n".join(missing[:20])
        raise FileNotFoundError(f"{input_csv}: missing {len(missing)} files. First missing paths:\n{preview}")
    logging.info("Validated %s rows in %s", len(df), input_csv)


def main():
    parser = argparse.ArgumentParser(description="Rewrite or validate SignalScope manifests on a new machine.")
    parser.add_argument("--dataset-root", required=True, help="Root folder containing GenImage image folders.")
    parser.add_argument("--input-dir", required=True, help="Folder containing train.csv, normal_val.csv, unseen_wukong.csv.")
    parser.add_argument("--output-dir", required=True, help="Folder for rewritten manifests. Can equal input-dir for validate.")
    parser.add_argument("--mode", choices=["rewrite", "validate"], required=True)
    args = parser.parse_args()

    setup_logging()
    dataset_root = Path(args.dataset_root)
    input_dir = Path(args.input_dir)
    output_dir = Path(args.output_dir)

    if not dataset_root.exists():
        raise FileNotFoundError(f"Dataset root does not exist: {dataset_root}")

    for name in MANIFESTS:
        input_csv = input_dir / name
        if not input_csv.exists():
            raise FileNotFoundError(f"Required manifest not found: {input_csv}")
        if args.mode == "rewrite":
            rewrite_manifest(input_csv, output_dir / name, dataset_root)
        else:
            validate_manifest(input_csv, dataset_root)

    logging.info("Manifest preparation complete.")


if __name__ == "__main__":
    main()

