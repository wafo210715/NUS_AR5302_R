#!/usr/bin/env python3
"""
Export all project data to CSV + shapefile format for Rmd import.

Reads from existing GeoPackages and raw CSVs, writes to:
  output/csv/     — flat tables for data analysis
  output/shp/     — ESRI shapefiles for spatial visualisation (EPSG:27700)

Usage:
    python python/01_export_data.py
"""

import os
import shutil
from pathlib import Path

import pandas as pd
import geopandas as gpd

# ── paths ───────────────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parent.parent
DATA_RAW = ROOT / "data" / "raw"
OUTPUT = ROOT / "output"
CSV_DIR = OUTPUT / "csv"
SHP_DIR = OUTPUT / "shp"

CSV_DIR.mkdir(parents=True, exist_ok=True)
SHP_DIR.mkdir(parents=True, exist_ok=True)

# ── helper ──────────────────────────────────────────────────────────────
def write_shp(gdf: gpd.GeoDataFrame, name: str, out_dir: Path = SHP_DIR):
    """Write a GeoDataFrame to an ESRI shapefile, removing any previous export."""
    folder = out_dir / name
    if folder.exists():
        shutil.rmtree(folder)
    folder.mkdir(parents=True, exist_ok=True)
    # Shapefile column limit is 10 chars — shorten coverage names
    rename_map = {
        "express_coverage": "expr_cov",
        "superstore_coverage": "super_cov",
        "extra_coverage": "extra_cov",
        "total_coverage": "total_cov",
        "overlap_index": "overlap_ix",
        "unique_types": "uniq_types",
        "borough_code": "bor_code",
        "borough_name": "bor_name",
    }
    gdf = gdf.rename(columns=rename_map)
    gdf.to_file(str(folder / f"{name}.shp"), driver="ESRI Shapefile")
    print(f"  SHP  -> {folder}/")


def write_csv(df: pd.DataFrame, name: str, out_dir: Path = CSV_DIR):
    df.to_csv(out_dir / f"{name}.csv", index=False)
    print(f"  CSV  -> {out_dir / f'{name}.csv'}  ({len(df)} rows)")


# ═══════════════════════════════════════════════════════════════════════
# 1.  POI — Tesco store locations
# ═══════════════════════════════════════════════════════════════════════
print("\n[1/7] POI — Tesco store locations")
poi = pd.read_csv(DATA_RAW / "tesco_osm_london.csv")
# Keep only useful columns
poi_out = poi[["osm_id", "lat", "lon", "name", "store_type"]].copy()
write_csv(poi_out, "poi_tesco_stores")

# ═══════════════════════════════════════════════════════════════════════
# 2.  LSOA — coverage + boundaries (London only)
# ═══════════════════════════════════════════════════════════════════════
print("\n[2/7] LSOA — coverage metrics + boundaries")
lsoa_gpkg = gpd.read_file(OUTPUT / "lsoa_with_data.gpkg")
london = lsoa_gpkg[lsoa_gpkg["PC1"].notna()].copy().to_crs(epsg=27700)

cov_cols = ["express_coverage", "superstore_coverage", "extra_coverage",
            "total_coverage", "overlap_index", "unique_types"]
lsoa_cov = london[["lsoa_code"] + cov_cols].copy()
write_csv(lsoa_cov, "coverage_lsoa")
write_shp(london[["lsoa_code", "geometry"] + cov_cols], "lsoa_boundaries")

# ═══════════════════════════════════════════════════════════════════════
# 3.  MSOA — dissolved coverage + boundaries
# ═══════════════════════════════════════════════════════════════════════
print("\n[3/7] MSOA — coverage metrics + boundaries")
msoa = gpd.read_file(OUTPUT / "msoa_coverage.gpkg").to_crs(epsg=27700)
msoa_cov = msoa[["MSOA11CD"] + cov_cols].copy()
write_csv(msoa_cov, "coverage_msoa")
write_shp(msoa[["MSOA11CD", "geometry"] + cov_cols], "msoa_boundaries")

# ═══════════════════════════════════════════════════════════════════════
# 4.  Ward — dissolved coverage + boundaries
# ═══════════════════════════════════════════════════════════════════════
print("\n[4/7] Ward — coverage metrics + boundaries")
ward = gpd.read_file(OUTPUT / "ward_coverage.gpkg").to_crs(epsg=27700)
ward_cov = ward[["WD11CD"] + cov_cols].copy()
write_csv(ward_cov, "coverage_ward")
write_shp(ward[["WD11CD", "geometry"] + cov_cols], "ward_boundaries")

# ═══════════════════════════════════════════════════════════════════════
# 5.  Borough — dissolved coverage + boundaries
# ═══════════════════════════════════════════════════════════════════════
print("\n[5/7] Borough — coverage metrics + boundaries")
bor = gpd.read_file(OUTPUT / "borough_coverage.gpkg").to_crs(epsg=27700)
bor_cov = bor[["borough_code", "borough_name"] + cov_cols].copy()
write_csv(bor_cov, "coverage_borough")
write_shp(bor[["borough_code", "borough_name", "geometry"] + cov_cols],
          "borough_boundaries")

# ═══════════════════════════════════════════════════════════════════════
# 6.  IMD sub-domains (London LSOAs only)
# ═══════════════════════════════════════════════════════════════════════
print("\n[6/7] IMD sub-domains")
imd_cols = ["imd_score", "income", "employment", "education",
            "health", "crime", "barriers", "living_environment"]
imd_out = london[["lsoa_code"] + imd_cols].copy()
write_csv(imd_out, "imd_subdomains")

# ═══════════════════════════════════════════════════════════════════════
# 7.  PCA scores (London LSOAs only)
# ═══════════════════════════════════════════════════════════════════════
print("\n[7/7] PCA scores")
pca_out = london[["lsoa_code", "PC1", "PC2"]].copy()
write_csv(pca_out, "pca_scores")

# ── summary ─────────────────────────────────────────────────────────────
print("\n" + "=" * 50)
print("EXPORT COMPLETE")
print("=" * 50)
print(f"\n  CSVs  -> {CSV_DIR}/")
for f in sorted(CSV_DIR.glob("*.csv")):
    rows = sum(1 for _ in open(f)) - 1
    print(f"    {f.name:40s} {rows:>6,} rows")
print(f"\n  SHPs  -> {SHP_DIR}/")
for d in sorted(SHP_DIR.iterdir()):
    if d.is_dir():
        shp = d / f"{d.name}.shp"
        if shp.exists():
            g = gpd.read_file(str(shp))
            print(f"    {d.name:40s} {len(g):>6,} features  (EPSG:{g.crs.to_epsg()})")
