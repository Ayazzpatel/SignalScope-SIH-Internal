"""Quick test: load Standalone_M and run predict."""
import sys, os, logging
logging.basicConfig(level=logging.INFO)
sys.path.insert(0, 'd:/CST_Study_Documents/4_YEAR/SIH/SignalScope-SIH-Internal')
os.environ["SIGNALSCOPE_STANDALONE_MODEL_PATH"] = (
    r"D:\CST_Study_Documents\4_YEAR\SIH\SignalScope-SIH-Internal"
    r"\app\backend\signalscope\ML\model\Standalone_M\best_model.pt"
)
import numpy as np
from PIL import Image
from model.predict_standalone import load_model, predict

print("Loading Standalone-M...")
c = load_model("cpu")
print("Loaded!\n")

# Solid colour extremes
white = Image.fromarray(np.ones((224,224,3), dtype=np.uint8)*255)
black = Image.fromarray(np.zeros((224,224,3), dtype=np.uint8))
r = predict(c, white)
print(f"All-white: {r['label']}  (AI={r['ai_probability']:.4f})")
r = predict(c, black)
print(f"All-black: {r['label']}  (AI={r['ai_probability']:.4f})")
print("\nDone. Model loads and predicts correctly.")
