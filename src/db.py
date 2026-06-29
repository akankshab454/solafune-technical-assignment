"""Part 3b: store change features in PostGIS, with a GeoPackage fallback."""
from __future__ import annotations

import os

from dotenv import load_dotenv

from . import config

load_dotenv(config.ROOT / ".env")

TABLE = "change_features"
GPKG = config.PROCESSED_DIR / "change_features.gpkg"

SAMPLE_QUERIES = {
    "area_per_method":
        f"SELECT method, COUNT(*) n, ROUND(SUM(area_m2)::numeric,1) total_m2 "
        f"FROM {TABLE} GROUP BY method ORDER BY total_m2 DESC;",
    "largest_polygons":
        f"SELECT method, ROUND(area_m2::numeric,1) area_m2, ROUND(confidence::numeric,3) confidence "
        f"FROM {TABLE} ORDER BY area_m2 DESC LIMIT 5;",
}


def _url():
    e = os.environ
    return (f"postgresql+psycopg2://{e.get('POSTGRES_USER','solafune')}:"
            f"{e.get('POSTGRES_PASSWORD','solafune')}@{e.get('POSTGRES_HOST','localhost')}:"
            f"{e.get('POSTGRES_PORT','5432')}/{e.get('POSTGRES_DB','solafune')}")


def get_engine():
    from sqlalchemy import create_engine
    return create_engine(_url())


def _to_4326(gdf):
    return gdf if gdf.crs and gdf.crs.to_epsg() == 4326 else gdf.to_crs(epsg=4326)


def store(gdf, table=TABLE, prefer_postgis=True) -> str:
    """Try PostGIS (geometry(Polygon,4326)); fall back to a GeoPackage."""
    gdf = _to_4326(gdf).reset_index(drop=True)
    if "id" not in gdf.columns:
        gdf.insert(0, "id", range(1, len(gdf) + 1))
    if prefer_postgis:
        try:
            from sqlalchemy import text
            engine = get_engine()
            with engine.begin() as c:
                c.execute(text("CREATE EXTENSION IF NOT EXISTS postgis;"))
            gdf.to_postgis(table, engine, if_exists="replace", index=False)
            return f"PostGIS: wrote {len(gdf)} rows to '{table}'"
        except Exception as exc:
            print(f"[db] PostGIS unavailable ({type(exc).__name__}); using GeoPackage.")
    gdf.to_file(str(GPKG), layer=table, driver="GPKG")
    return f"GeoPackage: wrote {len(gdf)} rows to {GPKG}"


def run_sample_queries() -> str:
    from sqlalchemy import text
    with get_engine().connect() as c:
        return "\n\n".join(
            f"-- {name}\n" + "\n".join(str(tuple(r)) for r in c.execute(text(sql)))
            for name, sql in SAMPLE_QUERIES.items())
