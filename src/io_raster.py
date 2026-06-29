"""Part 1: load bands by path, verify consistency, stack channels-last."""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import rasterio

from . import config


@dataclass
class RasterStack:
    date: str
    data: np.ndarray          # (H, W, 3) float32, [Blue, Green, Red]
    valid_mask: np.ndarray    # (H, W) bool
    crs: object
    transform: object
    profile: dict

    @property
    def shape(self):
        return self.data.shape[:2]


def load_date_stack(date: str) -> RasterStack:
    """Load the three bands for one date; assert they share grid + CRS."""
    bands, masks, meta = [], [], []
    for fname in config.BAND_FILES:
        path = config.date_folder(date) / fname
        with rasterio.open(path) as src:
            arr = src.read(1, masked=True).astype(np.float32)
            meta.append((src.crs, src.transform, (src.height, src.width), src.profile))
        bands.append(arr.filled(0.0))
        masks.append(~np.ma.getmaskarray(arr) & (arr.filled(config.NODATA_VALUE) != config.NODATA_VALUE))

    crs, transform, shape, profile = meta[0]
    for fname, (c, t, s, _) in zip(config.BAND_FILES, meta):
        if (c, t, s) != (crs, transform, shape):
            raise ValueError(f"{date}/{fname}: CRS/transform/shape mismatch vs {config.BAND_FILES[0]}")

    return RasterStack(date, np.stack(bands, axis=-1), np.logical_and.reduce(masks),
                       crs, transform, profile)


def verify_consistency(*stacks: RasterStack) -> None:
    """Fail loudly if dates differ in CRS, transform or shape."""
    ref = stacks[0]
    for s in stacks[1:]:
        if (s.crs, s.transform, s.shape) != (ref.crs, ref.transform, ref.shape):
            raise ValueError(f"{s.date} inconsistent with {ref.date}")


def write_stack(stack: RasterStack, path) -> None:
    profile = {**stack.profile, "count": 3, "dtype": "float32", "nodata": config.NODATA_VALUE}
    out = np.where(stack.valid_mask[..., None], stack.data, config.NODATA_VALUE)
    with rasterio.open(str(path), "w", **profile) as dst:
        for i in range(3):
            dst.write(out[:, :, i].astype("float32"), i + 1)
            dst.set_band_description(i + 1, config.BAND_NAMES[i])


def write_single_band(array, reference: RasterStack, path, dtype="float32", nodata=None) -> None:
    profile = {**reference.profile, "count": 1, "dtype": dtype, "nodata": nodata,
               "crs": reference.crs, "transform": reference.transform}
    with rasterio.open(str(path), "w", **profile) as dst:
        dst.write(array.astype(dtype), 1)


def summary(stack: RasterStack) -> str:
    return (f"[{stack.date}] {stack.shape} {stack.crs} "
            f"valid={100 * stack.valid_mask.mean():.2f}%")
