"""Paths, dates and tunables."""
from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INPUT_DIR = Path(os.environ.get(
    "SOLAFUNE_INPUTS", ROOT.parent / "Technical Assignment_DS" / "Technical Assignment"))
AOI_PATH = INPUT_DIR / "aoi.geojson"
DATA_DIR = INPUT_DIR / "data"
PROCESSED_DIR = ROOT / "data" / "processed"
FIGURES_DIR = ROOT / "figures"
DOCS_DIR = ROOT / "docs"

DATE_BEFORE, DATE_AFTER = "20230812", "20230902"

# Bands are named identically per date; stored channels-last as [Blue, Green, Red].
BAND_FILES = ("B02.tif", "B03.tif", "B04.tif")
BAND_NAMES = ("Blue", "Green", "Red")
RGB_INDEX = (2, 1, 0)              # channels-last -> (R, G, B) for display

REFLECTANCE_SCALE = 10000.0       # Sentinel-2 L2A DN scaling
NODATA_VALUE = 0

THRESHOLD_STRATEGY = "std"        # "std" (mean+k*std) | "otsu" | "percentile"
THRESHOLD_K = 2.0
THRESHOLD_PERCENTILE = 95.0
MIN_POLYGON_AREA_M2 = 2000.0      # drop speckle < ~20 pixels
IRMAD_MAX_ITER = 15
IRMAD_TOL = 1e-2


def date_folder(date: str) -> Path:
    return DATA_DIR / f"sentinel2_{date}"
