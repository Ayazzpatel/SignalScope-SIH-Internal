"""Quick local inference: test with AI images in the current directory."""
import os
import sys
import logging

logging.basicConfig(level=logging.INFO, format="%(name)s - %(levelname)s - %(message)s")
sys.path.insert(0, 'd:/CST_Study_Documents/4_YEAR/SIH/SignalScope-SIH-Internal')

os.environ["SIGNALSCOPE_MODEL_PATH"] = (
    "D:\\CST_Study_Documents\\4_YEAR\\SIH\\SignalScope-SIH-Internal"
    "\\app\\backend\\signalscope\\ML\\model\\signalscope_E1\\E1_convnext_tiny_best.pt"
)

from model.predict import load_model, predict
from PIL import Image
import glob

def test_image(container, path: str):
    img = Image.open(path).convert("RGB")
    result = predict(container, img)
    status = "✓" if result['label'] == 'AI-generated' else "✗"
    print(f"  {status} {os.path.basename(path)[:40]}: {result['label']} (AI={result['ai_probability']:.3f})")
    return result

def main():
    print("Loading model...")
    container = load_model('cpu')
    print("Model loaded!\n")

    # Find images in current directory and common download locations
    search_paths = [
        "*.jpg", "*.jpeg", "*.png", "*.webp",
        "D:/Downloads/*.jpg", "D:/Downloads/*.jpeg", "D:/Downloads/*.png",
        os.path.join(os.path.expanduser("~"), "Downloads", "*.jpg"),
        os.path.join(os.path.expanduser("~"), "Downloads", "*.jpeg"),
        os.path.join(os.path.expanduser("~"), "Downloads", "*.png"),
        os.path.join(os.path.expanduser("~"), "Desktop", "*.jpg"),
        os.path.join(os.path.expanduser("~"), "Desktop", "*.jpeg"),
        os.path.join(os.path.expanduser("~"), "Desktop", "*.png"),
    ]
    
    all_images = []
    for pattern in search_paths:
        all_images.extend(glob.glob(pattern))
    
    if not all_images:
        print("No images found. Please place some test images in the current directory.")
        print("Alternatively, you can pass paths directly.")
        return
    
    print(f"Found {len(all_images)} images to test:\n")
    ai_count = 0
    real_count = 0
    for path in all_images[:20]:  # limit to 20
        try:
            r = test_image(container, path)
            if r['label'] == 'AI-generated':
                ai_count += 1
            else:
                real_count += 1
        except Exception as e:
            print(f"  ERROR: {os.path.basename(path)}: {e}")
    
    print(f"\nSummary: {ai_count} AI-generated, {real_count} Real")
    print("(Note: check if your 'AI images' were flagged correctly above)")

if __name__ == "__main__":
    main()
