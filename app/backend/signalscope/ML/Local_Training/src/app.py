from __future__ import annotations

import argparse

import gradio as gr
import torch

from signalscope.evidence import basic_evidence
from signalscope.inference import load_checkpoint, predict_image
from signalscope.utils import get_device


def format_result(prediction: dict, evidence: dict) -> str:
    return (
        f"Prediction: {prediction['label']}\n"
        f"AI probability: {prediction['ai_probability']:.4f}\n"
        f"Real probability: {prediction['real_probability']:.4f}\n"
        f"Confidence: {prediction['confidence']:.4f}\n\n"
        "Basic evidence:\n"
        f"- Size: {evidence['width']} x {evidence['height']}\n"
        f"- Sharpness: {evidence['sharpness_laplacian_var']}\n"
        f"- High-frequency noise: {evidence['high_frequency_noise_std']}\n"
        f"- RGB variation: {evidence['rgb_channel_std']}\n"
        f"- EXIF: {evidence['exif'] or 'none detected'}"
    )


def main():
    parser = argparse.ArgumentParser(description="Launch the SignalScope demo UI.")
    parser.add_argument("--checkpoint", required=True)
    parser.add_argument("--image-size", type=int, default=None)
    parser.add_argument("--server-name", type=str, default="127.0.0.1")
    parser.add_argument("--server-port", type=int, default=7860)
    args = parser.parse_args()

    device = get_device()
    model, checkpoint_image_size, _ = load_checkpoint(args.checkpoint, device)
    image_size = args.image_size or checkpoint_image_size

    def analyze(image):
        if image is None:
            return "Upload an image first."
        with torch.inference_mode():
            prediction = predict_image(model, image, image_size, device)
        evidence = basic_evidence(None, image)
        return format_result(prediction, evidence)

    demo = gr.Interface(
        fn=analyze,
        inputs=gr.Image(type="pil", label="Image"),
        outputs=gr.Textbox(label="SignalScope result", lines=12),
        title="SignalScope AI Image Detector",
        allow_flagging="never",
    )
    demo.launch(server_name=args.server_name, server_port=args.server_port)


if __name__ == "__main__":
    main()
