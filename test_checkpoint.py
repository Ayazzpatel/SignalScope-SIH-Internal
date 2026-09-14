"""Quick check of the Standalone_M checkpoint keys."""
import torch

ckpt_path = r"D:\CST_Study_Documents\4_YEAR\SIH\SignalScope-SIH-Internal\app\backend\signalscope\ML\model\Standalone_M\best_model.pt"
ckpt = torch.load(ckpt_path, map_location="cpu", weights_only=False)
print("Type:", type(ckpt))
if isinstance(ckpt, dict):
    print("Keys:", list(ckpt.keys()))
    if "model_name" in ckpt:
        print("model_name:", ckpt["model_name"])
    if "image_size" in ckpt:
        print("image_size:", ckpt["image_size"])
    if "metrics" in ckpt:
        m = ckpt["metrics"]
        if isinstance(m, dict):
            val = m.get("val", {})
            print("best val roc_auc:", val.get("roc_auc") if isinstance(val, dict) else m.get("best_val_roc_auc"))
