"""Part 4: static summary panels and an interactive folium map."""
from __future__ import annotations

import geopandas as gpd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import ListedColormap
from rasterio.plot import plotting_extent

from . import config
from .change_detection import ChangeResult
from .io_raster import RasterStack


def _rgb(stack: RasterStack):
    """Contrast-stretched RGB (2/98 percentiles) from the [B,G,R] stack."""
    rgb = stack.data[:, :, list(config.RGB_INDEX)]
    out = np.zeros_like(rgb, np.float32)
    for i in range(3):
        band = rgb[:, :, i]
        lo, hi = np.percentile(band[stack.valid_mask], [2, 98])
        if hi > lo:
            out[:, :, i] = np.clip((band - lo) / (hi - lo), 0, 1)
    out[~stack.valid_mask] = 0
    return out


def static_panels(before, after, result: ChangeResult, out_path=None):
    out_path = out_path or config.FIGURES_DIR / f"summary_{result.name}.png"
    config.FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    extent = plotting_extent(before.data[:, :, 0], before.transform)
    aoi = gpd.read_file(config.AOI_PATH).to_crs(before.crs)

    fig, axes = plt.subplots(2, 2, figsize=(13, 12))
    axes[0, 0].imshow(_rgb(before), extent=extent)
    axes[0, 0].set_title(f"RGB before - {config.DATE_BEFORE}")
    axes[0, 1].imshow(_rgb(after), extent=extent)
    axes[0, 1].set_title(f"RGB after - {config.DATE_AFTER}")

    im = axes[1, 0].imshow(np.where(before.valid_mask, result.change_map, np.nan),
                           extent=extent, cmap="magma", vmin=0, vmax=1)
    axes[1, 0].set_title(f"Change intensity ({result.name})")
    fig.colorbar(im, ax=axes[1, 0], fraction=0.046, pad=0.04)

    axes[1, 1].imshow(_rgb(after), extent=extent)
    axes[1, 1].imshow(np.ma.masked_where(result.binary == 0, result.binary), extent=extent,
                      cmap=ListedColormap(["#ff2d2d"]), alpha=0.6)
    axes[1, 1].set_title(f"Detected change (thr={result.threshold:.3f})")

    for ax in axes.ravel():
        aoi.boundary.plot(ax=ax, color="cyan", linewidth=1.5)
        ax.set_xlabel("Easting (m)"); ax.set_ylabel("Northing (m)")
    fig.suptitle(f"Sentinel-2 change detection - open-pit mine, Zambia ({result.name})", fontsize=15)
    fig.tight_layout()
    fig.savefig(out_path, dpi=130, bbox_inches="tight")
    plt.close(fig)
    return out_path


def comparison_map(before, after, results, out_path=None):
    """Agreement between CVA and IR-MAD: both / CVA-only / IR-MAD-only."""
    out_path = out_path or config.FIGURES_DIR / "method_comparison.png"
    by = {r.name: r for r in results}
    if "cva_magnitude" not in by or "ir_mad" not in by:
        return None
    cva, irmad = by["cva_magnitude"].binary, by["ir_mad"].binary
    agree = cva.astype(np.uint8) + 2 * irmad.astype(np.uint8)   # 1=CVA, 2=IR-MAD, 3=both
    extent = plotting_extent(before.data[:, :, 0], before.transform)
    aoi = gpd.read_file(config.AOI_PATH).to_crs(before.crs)

    fig, ax = plt.subplots(figsize=(11, 10))
    ax.imshow(_rgb(after), extent=extent)
    cmap = ListedColormap(["#ffd400", "#ff2d2d", "#39ff14"])  # CVA, IR-MAD, both
    ax.imshow(np.ma.masked_where(agree == 0, agree), extent=extent, cmap=cmap,
              vmin=1, vmax=3, alpha=0.7)
    aoi.boundary.plot(ax=ax, color="cyan", linewidth=1.5)
    handles = [plt.Rectangle((0, 0), 1, 1, color=c) for c in cmap.colors]
    ax.legend(handles, ["CVA only", "IR-MAD only", "Both agree"], loc="lower right")
    ax.set_title("Change-detection agreement: CVA vs IR-MAD")
    ax.set_xlabel("Easting (m)"); ax.set_ylabel("Northing (m)")
    fig.tight_layout()
    fig.savefig(out_path, dpi=130, bbox_inches="tight")
    plt.close(fig)
    return out_path


def folium_map(gdf_wgs84: gpd.GeoDataFrame, out_path=None):
    import folium
    out_path = out_path or config.FIGURES_DIR / "interactive_map.html"
    config.FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    aoi = gpd.read_file(config.AOI_PATH).to_crs(epsg=4326)
    minx, miny, maxx, maxy = aoi.total_bounds
    m = folium.Map(location=[(miny + maxy) / 2, (minx + maxx) / 2], zoom_start=12)
    folium.TileLayer("Esri.WorldImagery", name="Satellite", attr="Esri").add_to(m)
    folium.GeoJson(aoi, name="AOI", style_function=lambda _: {
        "color": "cyan", "fill": False, "weight": 2}).add_to(m)
    if len(gdf_wgs84):
        folium.GeoJson(gdf_wgs84, name="Detected change",
                       style_function=lambda _: {"color": "red", "fillColor": "red",
                                                 "weight": 1, "fillOpacity": 0.4},
                       tooltip=folium.GeoJsonTooltip(
                           fields=["method", "area_m2", "confidence"])).add_to(m)
    folium.LayerControl().add_to(m)
    m.save(str(out_path))
    return out_path
