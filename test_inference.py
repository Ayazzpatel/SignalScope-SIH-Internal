"""End-to-end inference test: loads model and tests a real vs. AI-ish image."""
import os
import sys
import logging

# Set up logging so we can see the logit values
logging.basicConfig(level=logging.INFO, format="%(name)s - %(levelname)s - %(message)s")

sys.path.insert(0, 'd:/CST_Study_Documents/4_YEAR/SIH/SignalScope-SIH-Internal')

# Set model path
os.environ["SIGNALSCOPE_MODEL_PATH"] = (
    "D:\\CST_Study_Documents\\4_YEAR\\SIH\\SignalScope-SIH-Internal"
    "\\app\\backend\\signalscope\\ML\\model\\signalscope_E1\\E1_convnext_tiny_best.pt"
)

from model.predict import load_model, predict
from PIL import Image
import urllib.request
import io
import numpy as np

def test_image(container, img: Image.Image, label: str):
    result = predict(container, img)
    print(f"\n[{label}]")
    print(f"  Predicted: {result['label']}")
    print(f"  AI Probability:   {result['ai_probability']:.4f}")
    print(f"  Real Probability: {result['real_probability']:.4f}")
    print(f"  Confidence:       {result['confidence']:.4f}")
    return result

def main():
    print("Loading model...")
    container = load_model('cpu')
    print("Model loaded successfully!")

    # Test 1: Solid color images (extreme cases)
    print("\n=== EXTREME TEST: Solid color images ===")
    all_white = Image.fromarray(np.ones((224, 224, 3), dtype=np.uint8) * 255)
    test_image(container, all_white, "All White (no info)")
    
    all_black = Image.fromarray(np.zeros((224, 224, 3), dtype=np.uint8))
    test_image(container, all_black, "All Black (no info)")
    
    # Test 2: Download a known real photo
    print("\n=== REAL PHOTO TEST ===")
    try:
        url = "https://upload.wikimedia.org/wikipedia/commons/thumb/1/18/Dog_Breeds.jpg/320px-Dog_Breeds.jpg"
        with urllib.request.urlopen(url, timeout=10) as r:
            real_img = Image.open(io.BytesIO(r.read())).convert("RGB")
        test_image(container, real_img, "Real Photo (Wikipedia Dog)")
    except Exception as e:
        print(f"  Could not download real photo: {e}")

    print("\n=== DONE ===")
    print("If ALL predictions say 'Real' (prob_ai always ~0.0-0.1), the model may be predicting inversely or was not trained properly on this split.")
    print("If predictions vary, the model is working correctly.")

if __name__ == "__main__":
    main()
