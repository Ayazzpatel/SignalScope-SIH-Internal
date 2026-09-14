"""Perceptual hashing (pHash) for "seen before" matching.

pHash survives resizing and re-compression: two visually identical images land within a few bits of each
other, while unrelated images differ in ~32 of 64 bits. Implemented with a DCT matrix in NumPy to avoid
pulling SciPy into the image.
"""

import numpy as np
from PIL import Image

_SIZE = 32
_LOW = 8
_MASK64 = (1 << 64) - 1

# Orthogonal DCT-II basis: row u, column x.
_u = np.arange(_SIZE)[:, None]
_x = np.arange(_SIZE)[None, :]
_DCT = np.cos(np.pi * (2 * _x + 1) * _u / (2 * _SIZE))


def perceptual_hash(image: Image.Image) -> int:
    """Return a 64-bit pHash as a *signed* int (fits a Postgres BIGINT)."""
    grey = np.asarray(image.convert("L").resize((_SIZE, _SIZE), Image.Resampling.LANCZOS), dtype=np.float64)
    low = (_DCT @ grey @ _DCT.T)[:_LOW, :_LOW].flatten()
    bits = low > np.median(low[1:])  # DC term excluded from the threshold
    value = 0
    for bit in bits:
        value = (value << 1) | int(bit)
    return value - (1 << 64) if value >= (1 << 63) else value


def hamming(a: int, b: int) -> int:
    return ((a ^ b) & _MASK64).bit_count()
