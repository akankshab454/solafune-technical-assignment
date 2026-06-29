"""DN->reflectance and relative radiometric normalization."""
from __future__ import annotations

import numpy as np

from . import config


def to_reflectance(dn):
    return dn.astype(np.float32) / config.REFLECTANCE_SCALE


def relative_normalize(before, after, valid, stable_pct=60.0):
    """Rescale `after` per band to `before` using the most stable pixels."""
    diff = np.abs(after - before).sum(axis=2)
    ok = valid & np.isfinite(diff)
    if not ok.any():
        return after
    stable = ok & (diff <= np.percentile(diff[ok], stable_pct))
    out = after.copy()
    for b in range(after.shape[2]):
        x, y = after[:, :, b][stable], before[:, :, b][stable]
        if x.size < 10 or x.std() == 0:
            continue
        slope = np.cov(x, y, bias=True)[0, 1] / x.var()
        out[:, :, b] = slope * after[:, :, b] + (y.mean() - slope * x.mean())
    return out
