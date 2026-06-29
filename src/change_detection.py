"""Part 2: change detection - CVA baseline and IR-MAD."""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy import linalg, stats
from skimage.filters import threshold_otsu

from . import config


@dataclass
class ChangeResult:
    name: str
    change_map: np.ndarray    # (H, W) float32 in [0, 1]
    binary: np.ndarray        # (H, W) uint8
    threshold: float
    extra: dict


def _norm01(values, mask):
    """Scale to [0, 1] over valid pixels using 2/98 percentiles."""
    out = np.zeros_like(values, dtype=np.float32)
    v = values[mask]
    if v.size:
        lo, hi = np.percentile(v, [2, 98])
        if hi > lo:
            out[mask] = np.clip((values[mask] - lo) / (hi - lo), 0, 1)
    return out


def binarize(change_map, mask, strategy=config.THRESHOLD_STRATEGY,
             k=config.THRESHOLD_K, pct=config.THRESHOLD_PERCENTILE):
    """Threshold a change map. 'std' (mean+k*std) suits unimodal histograms."""
    v = change_map[mask]
    if v.size == 0 or v.max() == v.min():
        return np.zeros_like(change_map, np.uint8), float("nan")
    thr = {"std": v.mean() + k * v.std(),
           "otsu": lambda: threshold_otsu(v),
           "percentile": np.percentile(v, pct)}[strategy]
    thr = float(thr() if callable(thr) else thr)
    return (mask & (change_map > thr)).astype(np.uint8), thr


def cva_magnitude(before, after, mask) -> ChangeResult:
    """Euclidean norm of the band-difference vector (provided baseline)."""
    mag = np.linalg.norm(after - before, axis=2)
    cmap = _norm01(mag, mask)
    binary, thr = binarize(cmap, mask)
    return ChangeResult("cva_magnitude", cmap, binary, thr, {"magnitude": mag})


def ir_mad(before, after, mask, max_iter=config.IRMAD_MAX_ITER, tol=config.IRMAD_TOL) -> ChangeResult:
    """Iteratively Reweighted MAD (Nielsen 2007); robust to radiometric drift."""
    h, w, p = before.shape
    m = mask.reshape(-1)
    X, Y = before.reshape(-1, p)[m].astype(np.float64), after.reshape(-1, p)[m].astype(np.float64)
    weights = np.ones(X.shape[0])
    rho_prev, rho, Z, eps = np.zeros(p), np.zeros(p), None, 1e-9

    for _ in range(max_iter):
        sw = weights.sum()
        Xc = X - (weights[:, None] * X).sum(0) / sw
        Yc = Y - (weights[:, None] * Y).sum(0) / sw
        Sxx = (Xc * weights[:, None]).T @ Xc / sw + eps * np.eye(p)
        Syy = (Yc * weights[:, None]).T @ Yc / sw + eps * np.eye(p)
        Sxy = (Xc * weights[:, None]).T @ Yc / sw

        rho2, a = linalg.eigh(Sxy @ linalg.solve(Syy, Sxy.T), Sxx)
        order = np.argsort(rho2)[::-1]
        rho, a = np.sqrt(np.clip(rho2[order], 0, 1)), a[:, order]
        b = linalg.solve(Syy, Sxy.T @ a)
        for i in range(p):
            b[:, i] /= np.sqrt(max(b[:, i] @ Syy @ b[:, i], eps))
            if a[:, i] @ Sxy @ b[:, i] < 0:
                b[:, i] = -b[:, i]

        M = Xc @ a - Yc @ b
        Z = (M**2 / np.clip(2 * (1 - rho), eps, None)).sum(1)
        weights = 1.0 - stats.chi2.cdf(Z, df=p)
        if np.max(np.abs(rho - rho_prev)) < tol:
            break
        rho_prev = rho.copy()

    mad_mag = np.zeros(h * w, np.float32)
    mad_mag[m] = np.sqrt(Z)
    mad_mag = mad_mag.reshape(h, w)
    cmap = _norm01(mad_mag, mask)
    binary, thr = binarize(cmap, mask)
    return ChangeResult("ir_mad", cmap, binary, thr,
                        {"mad_magnitude": mad_mag, "canonical_correlations": rho})


METHODS = {"cva_magnitude": cva_magnitude, "ir_mad": ir_mad}
