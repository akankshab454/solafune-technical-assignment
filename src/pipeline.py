"""End-to-end: load -> change detection -> vectorize -> store -> visualize.

    python -m src.pipeline [--methods ...] [--no-postgis] [--no-figures]
"""
from __future__ import annotations

import argparse

import geopandas as gpd
import pandas as pd

from . import (change_detection as cd, config, db, indices, io_raster as io,
               preprocess, vectorize, visualize)


def run(methods=tuple(cd.METHODS), prefer_postgis=True, make_figures=True):
    config.PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    before, after = io.load_date_stack(config.DATE_BEFORE), io.load_date_stack(config.DATE_AFTER)
    io.verify_consistency(before, after)
    print(io.summary(before)); print(io.summary(after))
    io.write_stack(before, config.PROCESSED_DIR / f"sentinel2_{config.DATE_BEFORE}_stack.tif")
    io.write_stack(after, config.PROCESSED_DIR / f"sentinel2_{config.DATE_AFTER}_stack.tif")

    mask = before.valid_mask & after.valid_mask
    b_refl, a_refl = preprocess.to_reflectance(before.data), preprocess.to_reflectance(after.data)
    a_norm = preprocess.relative_normalize(b_refl, a_refl, mask)

    io.write_single_band(indices.vari(a_refl) - indices.vari(b_refl), before,
                         config.PROCESSED_DIR / "vari_diff.tif")
    io.write_single_band(indices.brightness(a_refl) - indices.brightness(b_refl), before,
                         config.PROCESSED_DIR / "brightness_diff.tif")

    inputs = {"cva_magnitude": (b_refl, a_norm), "ir_mad": (b_refl, a_refl)}
    results = []
    for name in methods:
        res = cd.METHODS[name](*inputs[name], mask)
        print(f"[cd] {res.name:14s} thr={res.threshold:.4f} change={100 * res.binary[mask].mean():.2f}%")
        io.write_single_band(res.change_map, before,
                             config.PROCESSED_DIR / f"change_map_{res.name}.tif", nodata=0)
        io.write_single_band(res.binary, before,
                             config.PROCESSED_DIR / f"change_binary_{res.name}.tif", "uint8", 0)
        results.append(res)

    gdfs = [vectorize.polygonize(r, before) for r in results]
    for r, g in zip(results, gdfs):
        print(f"[vec] {r.name:14s} {len(g):4d} polygons, {g['area_m2'].sum() / 1e4:7.1f} ha")
    combined = gpd.GeoDataFrame(pd.concat(gdfs, ignore_index=True), crs=gdfs[0].crs)
    print("[db]", db.store(vectorize.to_wgs84(combined), prefer_postgis=prefer_postgis))

    if make_figures:
        for res in results:
            print("[viz]", visualize.static_panels(before, after, res))
        cmp_path = visualize.comparison_map(before, after, results)
        if cmp_path:
            print("[viz]", cmp_path)
        ir = next((g for r, g in zip(results, gdfs) if r.name == "ir_mad"), gdfs[-1])
        print("[viz]", visualize.folium_map(vectorize.to_wgs84(ir)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--methods", nargs="+", default=list(cd.METHODS), choices=list(cd.METHODS))
    ap.add_argument("--no-postgis", action="store_true")
    ap.add_argument("--no-figures", action="store_true")
    a = ap.parse_args()
    run(tuple(a.methods), prefer_postgis=not a.no_postgis, make_figures=not a.no_figures)


if __name__ == "__main__":
    main()
