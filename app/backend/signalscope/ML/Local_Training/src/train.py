from __future__ import annotations

import argparse
import logging
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import torch
from torch import nn
from torch.utils.data import DataLoader
from tqdm import tqdm

from signalscope.dataset import SignalScopeDataset, load_manifest, verify_paths
from signalscope.metrics import compute_metrics
from signalscope.model import build_model
from signalscope.utils import get_device, save_json, seed_everything, setup_logging


def parse_args():
    parser = argparse.ArgumentParser(description="Train the final SignalScope detector.")
    parser.add_argument("--dataset-root", type=str, default=None)
    parser.add_argument("--train-csv", type=str, required=True)
    parser.add_argument("--val-csv", type=str, required=True)
    parser.add_argument("--test-csv", type=str, required=True)
    parser.add_argument("--output-dir", type=str, default="results/final_run")
    parser.add_argument("--epochs", type=int, default=8)
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument("--image-size", type=int, default=224)
    parser.add_argument("--lr", type=float, default=2e-4)
    parser.add_argument("--weight-decay", type=float, default=1e-4)
    parser.add_argument("--num-workers", type=int, default=4)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--amp", action="store_true")
    parser.add_argument("--verify-paths", action="store_true", default=True)
    return parser.parse_args()


def run_epoch(model, loader, criterion, optimizer, scaler, device, train: bool, amp: bool):
    model.train(train)
    losses, labels, probs, paths = [], [], [], []
    progress = tqdm(loader, desc="train" if train else "eval", leave=False)

    for images, targets, batch_paths in progress:
        images = images.to(device, non_blocking=True)
        targets = targets.to(device, non_blocking=True)

        with torch.set_grad_enabled(train):
            with torch.autocast(device_type=device.type, enabled=amp and device.type == "cuda"):
                logits = model(images)
                loss = criterion(logits, targets)

            if train:
                optimizer.zero_grad(set_to_none=True)
                scaler.scale(loss).backward()
                scaler.step(optimizer)
                scaler.update()

        batch_probs = torch.sigmoid(logits.detach()).cpu().numpy().tolist()
        losses.append(float(loss.detach().cpu()))
        labels.extend(targets.detach().cpu().numpy().astype(int).tolist())
        probs.extend(batch_probs)
        paths.extend(batch_paths)
        progress.set_postfix(loss=sum(losses) / len(losses))

    metrics = compute_metrics(labels, probs)
    metrics["loss"] = float(sum(losses) / max(1, len(losses)))
    return metrics, pd.DataFrame({"path": paths, "label": labels, "prob_ai": probs})


def save_checkpoint(path, model, optimizer, epoch, image_size, metrics):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    torch.save(
        {
            "model_state": model.state_dict(),
            "optimizer_state": optimizer.state_dict(),
            "epoch": epoch,
            "image_size": image_size,
            "metrics": metrics,
            "model_name": "convnext_tiny",
        },
        path,
    )


def save_confusion_matrix_png(metrics: dict, path: Path) -> None:
    cm = metrics["confusion_matrix"]
    matrix = [[cm["tn"], cm["fp"]], [cm["fn"], cm["tp"]]]
    fig, ax = plt.subplots(figsize=(4, 4))
    ax.imshow(matrix, cmap="Blues")
    ax.set_xticks([0, 1], labels=["Pred Real", "Pred AI"])
    ax.set_yticks([0, 1], labels=["True Real", "True AI"])
    for i in range(2):
        for j in range(2):
            ax.text(j, i, str(matrix[i][j]), ha="center", va="center", color="black")
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)


def main():
    args = parse_args()
    setup_logging()
    seed_everything(args.seed)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    logging.info("Loading manifests")
    train_df = load_manifest(args.train_csv, args.dataset_root)
    val_df = load_manifest(args.val_csv, args.dataset_root)
    test_df = load_manifest(args.test_csv, args.dataset_root)

    if args.verify_paths:
        verify_paths(train_df)
        verify_paths(val_df)
        verify_paths(test_df)

    device = get_device()
    logging.info("Using device: %s", device)

    train_loader = DataLoader(
        SignalScopeDataset(train_df, args.image_size, train=True),
        batch_size=args.batch_size,
        shuffle=True,
        num_workers=args.num_workers,
        pin_memory=device.type == "cuda",
    )
    val_loader = DataLoader(
        SignalScopeDataset(val_df, args.image_size, train=False),
        batch_size=args.batch_size,
        shuffle=False,
        num_workers=args.num_workers,
        pin_memory=device.type == "cuda",
    )
    test_loader = DataLoader(
        SignalScopeDataset(test_df, args.image_size, train=False),
        batch_size=args.batch_size,
        shuffle=False,
        num_workers=args.num_workers,
        pin_memory=device.type == "cuda",
    )

    model = build_model(pretrained=True).to(device)
    criterion = nn.BCEWithLogitsLoss()
    optimizer = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=args.weight_decay)
    scaler = torch.cuda.amp.GradScaler(enabled=args.amp and device.type == "cuda")

    history = []
    best_auc = -1.0
    for epoch in range(1, args.epochs + 1):
        logging.info("Epoch %s/%s", epoch, args.epochs)
        train_metrics, _ = run_epoch(model, train_loader, criterion, optimizer, scaler, device, True, args.amp)
        val_metrics, val_predictions = run_epoch(model, val_loader, criterion, optimizer, scaler, device, False, args.amp)
        logging.info(
            "epoch=%s train_loss=%.4f val_auc=%.4f val_f1=%.4f val_acc=%.4f",
            epoch,
            train_metrics["loss"],
            val_metrics["roc_auc"],
            val_metrics["macro_f1"],
            val_metrics["accuracy"],
        )

        row = {"epoch": epoch, "train": train_metrics, "val": val_metrics}
        history.append(row)
        save_checkpoint(output_dir / "last_model.pt", model, optimizer, epoch, args.image_size, row)

        current_auc = val_metrics["roc_auc"]
        if current_auc == current_auc and current_auc > best_auc:
            best_auc = current_auc
            save_checkpoint(output_dir / "best_model.pt", model, optimizer, epoch, args.image_size, row)
            val_predictions.to_csv(output_dir / "predictions_val.csv", index=False)
            logging.info("Saved new best checkpoint with val ROC-AUC %.4f", best_auc)

    logging.info("Evaluating best checkpoint on unseen Wukong test manifest")
    checkpoint = torch.load(output_dir / "best_model.pt", map_location=device)
    model.load_state_dict(checkpoint["model_state"])
    test_metrics, test_predictions = run_epoch(model, test_loader, criterion, optimizer, scaler, device, False, args.amp)
    test_predictions.to_csv(output_dir / "predictions_test.csv", index=False)
    save_confusion_matrix_png(test_metrics, output_dir / "confusion_matrix_test.png")

    save_json(
        output_dir / "metrics.json",
        {
            "config": vars(args),
            "best_val_roc_auc": best_auc,
            "history": history,
            "unseen_wukong_test": test_metrics,
        },
    )
    logging.info("Done. Best model: %s", output_dir / "best_model.pt")
    logging.info("Unseen Wukong metrics: %s", test_metrics)


if __name__ == "__main__":
    main()

