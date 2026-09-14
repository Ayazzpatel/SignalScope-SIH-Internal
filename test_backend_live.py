"""Quick HTTP test: upload a tiny solid-color image to the running backend and print the response."""
import io
import sys
import httpx
from PIL import Image
import numpy as np

def make_test_png(color: tuple) -> bytes:
    img = Image.fromarray(np.full((64, 64, 3), color, dtype=np.uint8))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()

def main():
    base_url = "http://127.0.0.1:8000"
    
    print("Testing backend health...")
    r = httpx.get(f"{base_url}/api/v1/health", timeout=5)
    print("Health:", r.json())
    
    print("\nUploading test image (solid blue - not a real photo)...")
    blue_png = make_test_png((100, 149, 237))  # cornflower blue
    
    # Try without auth first (might get 401)
    r = httpx.post(
        f"{base_url}/api/v1/analyze",
        files={"file": ("test.png", blue_png, "image/png")},
        timeout=60,
    )
    print("Status:", r.status_code)
    try:
        data = r.json()
        print("label:", data.get("label"))
        print("ai_probability:", data.get("ai_probability"))
        print("real_probability:", data.get("real_probability"))
        print("confidence:", data.get("confidence"))
        print("model_version:", data.get("model_version"))
        print("Full response keys:", list(data.keys()))
    except Exception:
        print("Response text:", r.text[:500])

if __name__ == "__main__":
    main()
