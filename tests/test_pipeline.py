"""Unit tests for the change-analysis pipeline (synthetic data, no I/O)."""
import numpy as np
import pytest
from rasterio.transform import Affine

from src import change_detection as cd, indices, io_raster, preprocess, vectorize


def _stack(data, crs="EPSG:32735"):
    h, w = data.shape[:2]
    return io_raster.RasterStack(
        date="t", data=data.astype(np.float32),
        valid_mask=np.ones((h, w), bool), crs=crs,
        transform=Affine(10, 0, 370000, 0, -10, 8650000), profile={})


def test_verify_consistency_raises_on_shape_mismatch():
    a = _stack(np.zeros((10, 10, 3)))
    b = _stack(np.zeros((10, 12, 3)))
    with pytest.raises(ValueError):
        io_raster.verify_consistency(a, b)


def test_to_reflectance_scales_by_10000():
    assert preprocess.to_reflectance(np.array([10000.0])) == pytest.approx(1.0)


def test_indices_vari_and_brightness():
    refl = np.array([[[0.1, 0.3, 0.2]]], np.float32)   # B, G, R
    assert indices.vari(refl)[0, 0] == pytest.approx((0.3 - 0.2) / (0.3 + 0.2 - 0.1), rel=1e-3)
    assert indices.brightness(refl)[0, 0] == pytest.approx(np.sqrt((0.2**2 + 0.3**2 + 0.1**2) / 3))


def test_binarize_std_threshold():
    cmap = np.zeros((100, 100), np.float32)
    cmap[:10] = 1.0                                     # 10% "change"
    mask = np.ones_like(cmap, bool)
    binary, thr = cd.binarize(cmap, mask, strategy="std", k=2.0)
    assert thr == pytest.approx(cmap.mean() + 2 * cmap.std(), rel=1e-5)
    assert binary.dtype == np.uint8 and binary.sum() > 0


def test_cva_magnitude_flags_changed_region():
    before = np.full((50, 50, 3), 0.2, np.float32)
    after = before.copy()
    after[20:30, 20:30] += 0.4                          # bright block changed
    mask = np.ones((50, 50), bool)
    res = cd.cva_magnitude(before, after, mask)
    assert res.change_map[25, 25] > res.change_map[0, 0]
    assert res.binary[25, 25] == 1


def test_ir_mad_returns_valid_result():
    rng = np.random.default_rng(0)
    before = rng.random((30, 30, 3)).astype(np.float32)
    after = before + rng.normal(0, 0.01, before.shape).astype(np.float32)
    after[10:20, 10:20] += 0.5
    res = cd.ir_mad(before, after, np.ones((30, 30), bool))
    assert res.change_map.shape == (30, 30)
    assert 0.0 <= res.change_map.min() and res.change_map.max() <= 1.0
    assert res.binary.dtype == np.uint8


def test_polygonize_area_and_columns():
    binary = np.zeros((50, 50), np.uint8)
    binary[10:20, 10:20] = 1                            # 10x10 px @ 10 m -> 10000 m2
    res = cd.ChangeResult("cva_magnitude", binary.astype(np.float32), binary, 0.5,
                          {"magnitude": binary.astype(np.float32)})
    gdf = vectorize.polygonize(res, _stack(np.zeros((50, 50, 3))), min_area_m2=1000)
    assert len(gdf) == 1
    assert gdf["area_m2"].iloc[0] == pytest.approx(10000, abs=1)
    assert list(gdf.columns) == vectorize.COLUMNS
