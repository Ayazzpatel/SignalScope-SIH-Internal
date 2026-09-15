"""Locate model weights: env-var override → repo `model/model/` → `app/backend/signalscope/ML/model/`."""

from __future__ import annotations

import os
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
_SEARCH_DIRS = (
    _REPO_ROOT / "model" / "model",
    _REPO_ROOT / "app" / "backend" / "signalscope" / "ML" / "model",
)


def resolve_checkpoint(relative: str, *env_vars: str) -> Path:
    """Return the checkpoint path for `relative` (e.g. "signalscope_E1/E1_convnext_tiny_best.pt").

    An env var that is set always wins, and must point at an existing file.
    """
    for var in env_vars:
        value = os.environ.get(var)
        if value:
            path = Path(value)
            if not path.exists():
                raise FileNotFoundError(f"{var} points to a checkpoint that does not exist: {path}")
            return path

    candidates = [directory / relative for directory in _SEARCH_DIRS]
    for path in candidates:
        if path.exists():
            return path

    looked_in = ", ".join(str(path) for path in candidates)
    hint = f" or set {' / '.join(env_vars)}" if env_vars else ""
    raise FileNotFoundError(f"Checkpoint '{relative}' not found. Looked in: {looked_in}. Copy it there{hint}.")
