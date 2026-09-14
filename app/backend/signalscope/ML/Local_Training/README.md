# SignalScope Final Model Package

SignalScope is a standalone AI-image detector package intended for handoff to another person. It does not depend on Kaggle notebooks, previous notebook cells, or hard-coded Kaggle paths.

The package trains a ConvNeXt-Tiny based binary detector on GenImage-derived manifests, validates on a normal validation split, tests on unseen Wukong, saves checkpoints, writes metrics, and launches a demo UI that reports AI probability, confidence, and basic image evidence.

## Required Input Files And Folders

You need these inputs on the target machine:

1. `train.csv`
2. `normal_val.csv`
3. `unseen_wukong.csv`
4. The image dataset folder containing the image files referenced by those CSVs.

Recommended GenImage downloads:

```text
GenImage-ADM
GenImage-BigGAN
GenImage-glide
GenImage-Midjourney-Part-1
GenImage-stable-diffusion-v1-4
GenImage-VQDM
GenImage-wukong
```

Final split strategy:

```text
Train/normal validation:
  ADM, BigGAN, GLIDE, Midjourney, Stable Diffusion v1.4, VQDM

Final unseen test:
  Wukong only
```

This is intentional. Wukong is held out so the final score measures generalization to a generator family not used for training.

Recommended layout:

```text
SignalScopeFinal/
  manifests/
    train.csv
    normal_val.csv
    unseen_wukong.csv
  data/
    genimage-adm/
    genimage-biggan/
    genimage-glide/
    genimage-midjourney/
    genimage-stable-diffusion-v1-4/
    genimage-vqdm/
    genimage-wukong/
```

The CSV manifests must contain:

```text
path,label
```

Accepted label formats:

```text
0 / 1
real / ai
human / synthetic
fake / real
```

If you do not already have manifests, build them from the local GenImage folders:

```bash
python scripts/build_genimage_manifests.py ^
  --dataset-root D:\Datasets\GenImage ^
  --output-dir manifests_prepared ^
  --val-ratio 0.15 ^
  --seed 42
```

The builder expects each generator folder to contain real and AI images in recognizable subfolders such as `nature/ai`, `nature/real`, `0_real`, `1_fake`, `real`, or `fake`. If a downloaded Kaggle folder uses a different structure, run the script once and it will report what it cannot recognize.

If your existing manifests still contain Kaggle paths such as `/kaggle/input/...`, use the preparation utility below to rewrite them.

## Setup

Create and activate a Python environment:

```bash
python -m venv .venv
.venv\Scripts\activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Install the correct PyTorch build for your GPU if needed. For NVIDIA GPUs, use the command recommended at:

```text
https://pytorch.org/get-started/locally/
```

## Prepare Or Validate Manifests

Rewrite old machine-specific paths into portable paths:

```bash
python scripts/prepare_manifests.py ^
  --dataset-root D:\Datasets\GenImage ^
  --input-dir manifests ^
  --output-dir manifests_prepared ^
  --mode rewrite
```

Validate that all manifest image paths exist:

```bash
python scripts/prepare_manifests.py ^
  --dataset-root D:\Datasets\GenImage ^
  --input-dir manifests_prepared ^
  --output-dir manifests_prepared ^
  --mode validate
```

The training script can also resolve portable relative paths using `--dataset-root`.

## Train Final Model

```bash
python src/train.py ^
  --dataset-root D:\Datasets\GenImage ^
  --train-csv manifests_prepared\train.csv ^
  --val-csv manifests_prepared\normal_val.csv ^
  --test-csv manifests_prepared\unseen_wukong.csv ^
  --output-dir results\final_run ^
  --epochs 8 ^
  --batch-size 16 ^
  --image-size 224 ^
  --lr 2e-4 ^
  --num-workers 4 ^
  --amp
```

Outputs:

```text
results/final_run/
  best_model.pt
  last_model.pt
  metrics.json
  predictions_val.csv
  predictions_test.csv
  confusion_matrix_test.png
```

## Launch Demo UI

```bash
python src/app.py ^
  --checkpoint results\final_run\best_model.pt ^
  --image-size 224
```

Then open the local URL printed in the terminal.

## Direct CLI Inference

```bash
python src/predict.py ^
  --checkpoint results\final_run\best_model.pt ^
  --image path\to\image.jpg
```

## Notes For The Recipient

- This is a binary detector: `0 = real`, `1 = AI`.
- Training uses 224px preprocessing.
- Training augmentation includes JPEG compression, blur, color changes, flips, and resize/crop.
- Loss is `BCEWithLogitsLoss`.
- AMP is supported through `--amp`.
- Metrics include ROC-AUC, Macro-F1, accuracy, precision, recall, FPR, and confusion matrix.
- The best checkpoint is selected by validation ROC-AUC.
- Unseen Wukong should be treated as the final generalization test split.
