from __future__ import annotations

import argparse
import json

from signalscope.inference import predict_path
from signalscope.utils import get_device, setup_logging


def main():
    parser = argparse.ArgumentParser(description="Run SignalScope inference on one image.")
    parser.add_argument("--checkpoint", required=True)
    parser.add_argument("--image", required=True)
    args = parser.parse_args()

    setup_logging()
    result = predict_path(args.checkpoint, args.image, get_device())
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()

