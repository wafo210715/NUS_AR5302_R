#!/usr/bin/env python3
"""
Stage 0: Data Preprocessing for Stage 1 & Stage 2 Analysis

Usage:
    python python/00_stage0_preprocess.py

This script prepares all data needed for the R analysis scripts:
1. Downloads IMD 2015 sub-domain scores (File 5) from Gov.uk
2. Computes PCA scores (PC1, PC2) from Tesco grocery purchasing data
3. Generates 15-min walking isochrones and supply-side coverage metrics

Outputs (saved to output/):
    - imd_subdomains.csv : IMD total + 7 sub-domain scores per LSOA
    - pca_scores.csv     : PC1, PC2 scores per LSOA
    - coverage_metrics.csv: Supply-side coverage metrics per LSOA
    - lsoa_with_data.gpkg : LSOA boundaries merged with all attributes (for R spatial analysis)
"""

import os
import sys
import time
import requests
import numpy as np
import pandas as pd
import geopandas as gpd
from pathlib import Path
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA

# ── Paths ──────────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).parent.parent
DATA_RAW     = PROJECT_ROOT / "data" / "raw"
DATA_TESCO   = PROJECT_ROOT / "tesco-data" / "7796666"
OUTPUT_DIR   = PROJECT_ROOT / "output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

LSOA_SHP = DATA_RAW / "LSOA_2011" / "LSOA_2011_EW_BGC_V3.shp"
TESCO_CSV = DATA_RAW / "tesco_osm_london.csv"
IMD_FILE1 = DATA_RAW / "IMD_2015_File_1_Index.xlsx"
IMD_FILE5_URL = (
    "https://assets.publishing.service.gov.uk/media/5a818571e5274a2e87dbe132/"
    "File_5_ID_2015_Scores_for_the_Indices_of_Deprivation.xlsx"
)
IMD_FILE5 = DATA_RAW / "IMD_2015_File_5_Scores.xlsx"

# Food categories used in PCA (Broadbridge et al. 2025)
FOOD_CATEGORIES = [
    "f_beer", "f_dairy", "f_eggs", "f_fats_oils", "f_fish", "f_fruit_veg",
    "f_grains", "f_meat_red", "f_poultry", "f_readymade", "f_soft_drinks",
    "f_sweets", "f_wine",
]

# Walking distance cutoff: 15 min * ~5 km/h = 1250 m
WALKING_CUTOFF_M = 1250


# ═══════════════════════════════════════════════════════════════════════
# STEP 1: Download and parse IMD sub-domain scores
# ═══════════════════════════════════════════════════════════════════════
def step1_download_imd():
    print("\n" + "=" * 60)
    print("STEP 1: IMD 2015 Sub-Domain Scores")
    print("=" * 60)

    # Download File 5 if not present
    if not IMD_FILE5.exists():
        print(f"  Downloading IMD File 5 ...")
        try:
            resp = requests.get(IMD_FILE5_URL, timeout=120)
            resp.raise_for_status()
            IMD_FILE5.write_bytes(resp.content)
            print(f"  Saved: {IMD_FILE5}")
        except Exception as e:
            print(f"  ERROR downloading IMD File 5: {e}")
            print("  Please download manually from Gov.uk and place at:")
            print(f"    {IMD_FILE5}")
            sys.exit(1)
    else:
        print(f"  IMD File 5 already exists: {IMD_FILE5}")

    # Parse File 5
    print("  Parsing IMD sub-domain scores ...")
    xls = pd.ExcelFile(IMD_FILE5)
    print(f"  Sheets: {xls.sheet_names}")

    # Read the data sheet (skip "Notes" sheet if present)
    data_sheets = [s for s in xls.sheet_names if s.lower() != "notes"]
    sheet_name = data_sheets[0] if data_sheets else xls.sheet_names[1]
    df = pd.read_excel(IMD_FILE5, sheet_name=sheet_name)
    print(f"  Columns ({len(df.columns)}):")
    for c in df.columns:
        print(f"    - {c}")
    print(f"  Rows: {len(df)}")

    # Identify LSOA code column
    lsoa_col = None
    for c in df.columns:
        if "LSOA code" in c or "lsoa code" in c.lower():
            lsoa_col = c
            break
    if lsoa_col is None:
        print("  ERROR: Could not find LSOA code column")
        print("  Available columns:", list(df.columns))
        sys.exit(1)

    # Identify domain score columns
    # The 7 IMD domains: Income, Employment, Education, Health, Crime, Barriers, Living Environment
    domain_keywords = {
        "income": "Income",
        "employment": "Employment",
        "education": "Education",
        "health": "Health",
        "crime": "Crime",
        "barriers": "Barriers",
        "living_environment": "Living Environment",
    }

    # Also look for IMD total score
    imd_total_col = None
    for c in df.columns:
        if "IMD Score" in c or ("Index of Multiple Deprivation" in c and "Score" in c):
            imd_total_col = c
            break

    # Find score columns for each domain
    domain_cols = {}
    for key, keyword in domain_keywords.items():
        for c in df.columns:
            if keyword in c and ("Score" in c or "score" in c):
                # Prefer the domain score (not rank or decile)
                if "Rank" not in c and "Decile" not in c and "Quartile" not in c:
                    domain_cols[key] = c
                    break

    print(f"\n  Identified columns:")
    print(f"    LSOA code: {lsoa_col}")
    print(f"    IMD total: {imd_total_col}")
    for key, col in domain_cols.items():
        print(f"    {key}: {col}")

    # Build output DataFrame
    result = pd.DataFrame()
    result["lsoa_code"] = df[lsoa_col]

    if imd_total_col:
        result["imd_score"] = pd.to_numeric(df[imd_total_col], errors="coerce")
    else:
        # Try to get IMD score from File 1
        if IMD_FILE1.exists():
            imd1 = pd.read_excel(IMD_FILE1, sheet_name="IMD 2015")
            for c in imd1.columns:
                if "IMD" in c and "Score" in c:
                    result["imd_score"] = pd.to_numeric(imd1[c], errors="coerce")
                    break

    for key, col in domain_cols.items():
        result[key] = pd.to_numeric(df[col], errors="coerce")

    # Drop rows with all missing domain scores
    domain_keys = list(domain_cols.keys())
    result = result.dropna(subset=domain_keys, how="all")

    print(f"\n  Final IMD data: {len(result)} LSOAs")
    print(f"  Domains available: {[k for k in domain_keys if result[k].notna().sum() > 0]}")

    # Save
    out_path = OUTPUT_DIR / "imd_subdomains.csv"
    result.to_csv(out_path, index=False)
    print(f"  Saved: {out_path}")
    return result


# ═══════════════════════════════════════════════════════════════════════
# STEP 2: Compute PCA scores from grocery data
# ═══════════════════════════════════════════════════════════════════════
def step2_compute_pca():
    print("\n" + "=" * 60)
    print("STEP 2: PCA on Grocery Purchasing Data")
    print("=" * 60)

    # Load grocery data
    grocery_path = DATA_TESCO / "year_lsoa_grocery.csv"
    grocery = pd.read_csv(grocery_path)
    print(f"  Loaded {len(grocery)} LSOAs from grocery data")

    # Filter to food categories that exist
    available = [c for c in FOOD_CATEGORIES if c in grocery.columns]
    print(f"  Using {len(available)} food categories: {available}")

    X = grocery[available].fillna(0)

    # Standardize
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    # PCA
    pca = PCA()
    pc_scores = pca.fit_transform(X_scaled)
    var_exp = pca.explained_variance_ratio_ * 100

    print(f"\n  Variance explained:")
    for i in range(min(5, len(var_exp))):
        print(f"    PC{i+1}: {var_exp[i]:.1f}%")
    print(f"    PC1+PC2: {var_exp[0]+var_exp[1]:.1f}%")

    # Interpret PC1
    loadings = pd.DataFrame(
        pca.components_[:2].T,
        columns=["PC1", "PC2"],
        index=available,
    )
    print(f"\n  PC1 loadings (top 5 positive):")
    print(loadings["PC1"].sort_values(ascending=False).head(5).to_string())
    print(f"  PC1 loadings (top 5 negative):")
    print(loadings["PC1"].sort_values(ascending=True).head(5).to_string())

    # Save PCA scores
    pc_df = pd.DataFrame({
        "lsoa_code": grocery["area_id"],
        "PC1": pc_scores[:, 0],
        "PC2": pc_scores[:, 1],
    })

    # Save loadings
    loadings.to_csv(OUTPUT_DIR / "pca_loadings.csv")

    out_path = OUTPUT_DIR / "pca_scores.csv"
    pc_df.to_csv(out_path, index=False)
    print(f"\n  Saved: {out_path}")
    return pc_df, loadings, var_exp


# ═══════════════════════════════════════════════════════════════════════
# STEP 3: Compute supply-side coverage metrics using walking isochrones
# ═══════════════════════════════════════════════════════════════════════
def step3_compute_coverage():
    print("\n" + "=" * 60)
    print("STEP 3: Supply-Side Coverage Metrics (15-min Walking Isochrones)")
    print("=" * 60)

    import networkx as nx
    try:
        import osmnx as ox
    except ImportError:
        print("  osmnx not available, using Euclidean buffer fallback")
        return _compute_coverage_buffer()

    # Load Tesco stores
    stores = pd.read_csv(TESCO_CSV)
    print(f"  Loaded {len(stores)} Tesco stores")
    print(f"  Store type distribution:\n{stores['store_type'].value_counts().to_string()}")

    # Group Metro with Express (both are small-format convenience stores)
    stores["store_type_grouped"] = stores["store_type"].replace({"Metro": "Express", "Unknown": "Express"})
    print(f"\n  Grouped store types:\n{stores['store_type_grouped'].value_counts().to_string()}")

    # Load LSOA boundaries (projected to BNG)
    print(f"\n  Loading LSOA boundaries from {LSOA_SHP} ...")
    lsoa_gdf = gpd.read_file(LSOA_SHP)
    print(f"  CRS: {lsoa_gdf.crs}")

    # Filter to London LSOAs (codes starting with E01)
    lsoa_gdf = lsoa_gdf[lsoa_gdf["LSOA11CD"].str.startswith("E01")].copy()
    print(f"  London LSOAs: {len(lsoa_gdf)}")

    # Project to British National Grid (EPSG:27700)
    if lsoa_gdf.crs is None or lsoa_gdf.crs.to_epsg() != 27700:
        lsoa_gdf = lsoa_gdf.to_crs("EPSG:27700")
    print(f"  Projected to EPSG:27700")

    # Download London pedestrian street network
    print(f"\n  Downloading London pedestrian network via osmnx ...")
    print(f"  (This may take a few minutes on first run)")
    t0 = time.time()
    try:
        G = ox.graph_from_place("Greater London, England", network_type="walk")
    except Exception:
        # Fallback: use bounding box
        bounds = lsoa_gdf.total_bounds  # [minx, miny, maxx, maxy] in BNG
        # Convert to lat/lon for osmnx
        from shapely.geometry import Point
        corners = [Point(bounds[0], bounds[1]), Point(bounds[2], bounds[3])]
        corners_gdf = gpd.GeoDataFrame(geometry=corners, crs="EPSG:27700")
        corners_gdf = corners_gdf.to_crs("EPSG:4326")
        bbox = (
            corners_gdf.geometry.y.min() - 0.05,
            corners_gdf.geometry.x.min() - 0.05,
            corners_gdf.geometry.y.max() + 0.05,
            corners_gdf.geometry.x.max() + 0.05,
        )
        G = ox.graph_from_bbox(bbox=bbox, network_type="walk")

    # Project graph to BNG
    G = ox.project_graph(G, to_crs="EPSG:27700")
    nodes_gdf = ox.graph_to_gdfs(G, edges=False)
    print(f"  Network downloaded in {time.time()-t0:.0f}s")
    print(f"  Nodes: {len(nodes_gdf)}, Edges: {G.number_of_edges()}")

    # Project store coordinates to BNG
    store_gdf = gpd.GeoDataFrame(
        stores,
        geometry=gpd.points_from_xy(stores["lon"], stores["lat"]),
        crs="EPSG:4326",
    )
    store_gdf = store_gdf.to_crs("EPSG:27700")

    # Compute isochrones for each store type using multi-source Dijkstra
    coverage_polygons = {}
    store_types = ["Express", "Superstore", "Extra"]

    for stype in store_types:
        type_stores = store_gdf[store_gdf["store_type_grouped"] == stype]
        if len(type_stores) == 0:
            print(f"\n  {stype}: No stores found, skipping")
            continue

        print(f"\n  Computing {stype} isochrone ({len(type_stores)} stores) ...")
        t0 = time.time()

        # Find nearest network nodes for all stores of this type
        source_nodes = ox.distance.nearest_nodes(
            G,
            X=type_stores.geometry.x.values,
            Y=type_stores.geometry.y.values,
        )

        # Multi-source Dijkstra: shortest distance from ANY store to all nodes
        distances = nx.multi_source_dijkstra_path_length(
            G, set(source_nodes), cutoff=WALKING_CUTOFF_M, weight="length"
        )

        # Get covered nodes
        covered_ids = list(distances.keys())
        print(f"    Covered nodes: {len(covered_ids)}")

        # Create isochrone polygon from covered nodes
        covered_nodes = nodes_gdf.loc[nodes_gdf.index.isin(covered_ids)]
        if len(covered_nodes) >= 3:
            union_pts = covered_nodes.geometry.union_all()
            iso_poly = union_pts.convex_hull
            coverage_polygons[stype] = iso_poly
        elif len(covered_nodes) > 0:
            coverage_polygons[stype] = covered_nodes.geometry.union_all().buffer(200)
        else:
            coverage_polygons[stype] = None

        print(f"    Done in {time.time()-t0:.1f}s")

    # Compute union of all coverage polygons
    valid_polys = [p for p in coverage_polygons.values() if p is not None]
    if valid_polys:
        all_coverage = gpd.GeoSeries(valid_polys).union_all()
    else:
        all_coverage = None

    # Compute coverage metrics per LSOA
    print(f"\n  Computing coverage metrics per LSOA ...")
    results = []
    for _, lsoa in lsoa_gdf.iterrows():
        lsoa_area = lsoa.geometry.area
        if lsoa_area == 0:
            continue
        row = {"lsoa_code": lsoa["LSOA11CD"]}

        covered_types = 0
        for stype in store_types:
            if stype in coverage_polygons and coverage_polygons[stype] is not None:
                try:
                    inter = lsoa.geometry.intersection(coverage_polygons[stype])
                    pct = inter.area / lsoa_area * 100
                except Exception:
                    pct = 0.0
            else:
                pct = 0.0
            row[f"{stype.lower()}_coverage"] = round(pct, 2)
            if pct > 0:
                covered_types += 1

        # Total coverage = area covered by ANY store type (union)
        if all_coverage is not None:
            try:
                total_inter = lsoa.geometry.intersection(all_coverage)
                row["total_coverage"] = round(total_inter.area / lsoa_area * 100, 2)
            except Exception:
                row["total_coverage"] = 0.0
        else:
            row["total_coverage"] = 0.0

        # Overlap index
        sum_individual = sum(row.get(f"{s.lower()}_coverage", 0) for s in store_types)
        row["overlap_index"] = round(sum_individual - row["total_coverage"], 2)

        # Unique types
        row["unique_types"] = covered_types

        results.append(row)

    coverage_df = pd.DataFrame(results)
    print(f"  Coverage metrics computed for {len(coverage_df)} LSOAs")

    # Save
    out_path = OUTPUT_DIR / "coverage_metrics.csv"
    coverage_df.to_csv(out_path, index=False)
    print(f"  Saved: {out_path}")

    return coverage_df, lsoa_gdf


def _compute_coverage_buffer():
    """Fallback: use Euclidean buffers instead of network isochrones"""
    print("  Using Euclidean buffer approximation (1.2 km ≈ 15-min walk)")

    # Load data
    stores = pd.read_csv(TESCO_CSV)
    lsoa_gdf = gpd.read_file(LSOA_SHP)
    lsoa_gdf = lsoa_gdf[lsoa_gdf["LSOA11CD"].str.startswith("E01")].copy()
    lsoa_gdf = lsoa_gdf.to_crs("EPSG:27700")

    stores["store_type_grouped"] = stores["store_type"].replace(
        {"Metro": "Express", "Unknown": "Express"}
    )

    # Create store points in BNG
    store_gdf = gpd.GeoDataFrame(
        stores,
        geometry=gpd.points_from_xy(stores["lon"], stores["lat"]),
        crs="EPSG:4326",
    ).to_crs("EPSG:27700")

    # Create buffers per store type
    store_types = ["Express", "Superstore", "Extra"]
    coverage_polygons = {}

    for stype in store_types:
        type_stores = store_gdf[store_gdf["store_type_grouped"] == stype]
        if len(type_stores) == 0:
            continue
        coverage_polygons[stype] = type_stores.geometry.buffer(WALKING_CUTOFF_M).union_all()

    # Compute coverage per LSOA
    valid_polys = [p for p in coverage_polygons.values() if p is not None]
    all_coverage = gpd.GeoSeries(valid_polys).union_all() if valid_polys else None

    results = []
    for _, lsoa in lsoa_gdf.iterrows():
        lsoa_area = lsoa.geometry.area
        if lsoa_area == 0:
            continue
        row = {"lsoa_code": lsoa["LSOA11CD"]}
        covered_types = 0

        for stype in store_types:
            if stype in coverage_polygons:
                try:
                    inter = lsoa.geometry.intersection(coverage_polygons[stype])
                    pct = inter.area / lsoa_area * 100
                except Exception:
                    pct = 0.0
            else:
                pct = 0.0
            row[f"{stype.lower()}_coverage"] = round(pct, 2)
            if pct > 0:
                covered_types += 1

        if all_coverage is not None:
            try:
                total_inter = lsoa.geometry.intersection(all_coverage)
                row["total_coverage"] = round(total_inter.area / lsoa_area * 100, 2)
            except Exception:
                row["total_coverage"] = 0.0
        else:
            row["total_coverage"] = 0.0

        row["overlap_index"] = round(
            sum(row.get(f"{s.lower()}_coverage", 0) for s in store_types) - row["total_coverage"], 2
        )
        row["unique_types"] = covered_types
        results.append(row)

    coverage_df = pd.DataFrame(results)
    coverage_df.to_csv(OUTPUT_DIR / "coverage_metrics.csv", index=False)
    print(f"  Saved: {OUTPUT_DIR / 'coverage_metrics.csv'}")
    return coverage_df, lsoa_gdf


# ═══════════════════════════════════════════════════════════════════════
# STEP 4: Merge everything into a single GeoPackage for R
# ═══════════════════════════════════════════════════════════════════════
def step4_merge_outputs(coverage_df, lsoa_gdf):
    print("\n" + "=" * 60)
    print("STEP 4: Merging outputs for R")
    print("=" * 60)

    # Load IMD sub-domains
    imd = pd.read_csv(OUTPUT_DIR / "imd_subdomains.csv")

    # Load PCA scores
    pca = pd.read_csv(OUTPUT_DIR / "pca_scores.csv")

    # Start with LSOA boundaries
    gdf = lsoa_gdf[["LSOA11CD", "geometry"]].copy()
    gdf = gdf.rename(columns={"LSOA11CD": "lsoa_code"})

    # Merge coverage metrics
    gdf = gdf.merge(coverage_df, on="lsoa_code", how="left")

    # Merge IMD
    gdf = gdf.merge(imd, on="lsoa_code", how="left")

    # Merge PCA scores
    gdf = gdf.merge(pca, on="lsoa_code", how="left")

    print(f"  Final GeoDataFrame: {len(gdf)} LSOAs, {len(gdf.columns)} columns")
    print(f"  Columns: {list(gdf.columns)}")
    print(f"  CRS: {gdf.crs}")

    # Save as GeoPackage
    gpkg_path = OUTPUT_DIR / "lsoa_with_data.gpkg"
    gdf.to_file(gpkg_path, driver="GPKG")
    print(f"  Saved: {gpkg_path}")

    return gdf


# ═══════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════
def main():
    print("=" * 60)
    print("Stage 0: Data Preprocessing")
    print("=" * 60)

    # Step 1: IMD sub-domain scores
    imd_df = step1_download_imd()

    # Step 2: PCA scores
    pc_df, loadings, var_exp = step2_compute_pca()

    # Step 3: Coverage metrics
    coverage_df, lsoa_gdf = step3_compute_coverage()

    # Step 4: Merge everything
    merged_gdf = step4_merge_outputs(coverage_df, lsoa_gdf)

    print("\n" + "=" * 60)
    print("PREPROCESSING COMPLETE")
    print("=" * 60)
    print(f"\nOutputs saved to {OUTPUT_DIR}/:")
    print("  - imd_subdomains.csv")
    print("  - pca_scores.csv")
    print("  - pca_loadings.csv")
    print("  - coverage_metrics.csv")
    print("  - lsoa_with_data.gpkg")
    print("\nReady for R analysis (Stage 1 & Stage 2)")


if __name__ == "__main__":
    main()
