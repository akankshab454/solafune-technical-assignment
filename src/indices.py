"""Visible-only spectral indices (no NIR/SWIR available)."""
from __future__ import annotations

import numpy as np

_EPS = 1e-6


def _bgr(refl):
    return refl[:, :, 0], refl[:, :, 1], refl[:, :, 2]


def vari(refl):
    """Visible Atmospherically Resistant Index, a vegetation proxy."""
    b, g, r = _bgr(refl)
    return (g - r) / (g + r - b + _EPS)


def brightness(refl):
    """RMS visible brightness, a bare-ground/stockpile proxy."""
    b, g, r = _bgr(refl)
    return np.sqrt((r**2 + g**2 + b**2) / 3.0)
