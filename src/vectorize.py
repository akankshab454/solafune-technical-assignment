"""Part 3a: binary change raster -> attributed polygons."""
from __future__ import annotations

import geopandas as gpd
import numpy as np
from rasterio import features
from scipy import ndimage
from shapely.geometry import shape
from shapely.ops import unary_union

from . import config
from .change_detection import ChangeResult
from .io_raster import RasterStack

COLUMNS = ["date_before", "date_after", "method",
           "area_m2", "change_strength", "confidence", "geometry"]


def _strength(result: ChangeResult):
    for key in ("magnitude", "mad_magnitude"):
        if key in result.extra:
            return result.extra[key]
    return result.change_map


def polygonize(result: ChangeResult, ref: RasterStack,
               date_before=config.DATE_BEFORE, date_after=config.DATE_AFTER,
               min_area_m2=config.MIN_POLYGON_AREA_M2) -> gpd.GeoDataFrame:
    """Vectorize connected change regions with per-region area/strength/confidence."""
    binary = result.binary.astype(np.uint8)
    labels, n = ndimage.label(binary)
    if n == 0:
        return gpd.GeoDataFrame(columns=COLUMNS, geometry="geometry", crs=ref.crs)

    idx = np.arange(1, n + 1)
    conf = ndimage.mean(result.change_map, labels, idx)
    strength = ndimage.mean(_strength(result), labels, idx)

    geoms: dict[int, list] = {}
    for geom, val in features.shapes(labels.astype(np.int32), mask=binary.astype(bool),
                                     transform=ref.transform):
        geoms.setdefault(int(val), []).append(shape(geom))

    gdf = gpd.GeoDataFrame(
        [{"date_before": date_before, "date_after": date_after, "method": result.name,
          "change_strength": float(strength[lab - 1]), "confidence": float(conf[lab - 1]),
          "geometry": g[0] if len(g) == 1 else unary_union(g)}
         for lab, g in geoms.items()],
        crs=ref.crs)

    gdf["area_m2"] = gdf.to_crs(gdf.estimate_utm_crs()).area
    gdf = gdf[gdf["area_m2"] >= min_area_m2].reset_index(drop=True)
    return gdf[COLUMNS]


def to_wgs84(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    return gdf.to_crs(epsg=4326)
