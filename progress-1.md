# Project Progress — Session 1

**Date:** 2026-03-29

---

## Research Question

How do area-level deprivation (and its sub-domains), supply-side factors, and socio-demographic characteristics explain spatial variation in food purchasing patterns across London, using Tesco Clubcard data?

Full research plan: [`ar5302-research-plan.md`](ar5302-research-plan.md)

---

## Data Pipeline

### Stage 0: Preprocessing (`python/00_stage0_preprocess.py`)

Downloads and prepares all data for R analysis.

**Steps:**
1. Download IMD 2015 File 5 sub-domain scores from Gov.uk
2. PCA on Tesco grocery purchasing data (13 food categories → PC1 = "Convenience", PC2 = "Variety")
3. 15-min walking isochrones for 577 Tesco stores via osmnx + multi-source Dijkstra
4. Area-based coverage metrics (isochrone polygon ∩ LSOA polygon) for Express / Superstore / Extra
5. Merge into single GeoPackage

**Outputs:**

| File | Description | Rows |
|------|-------------|------|
| `output/lsoa_with_data.gpkg` | All data merged (LSOA geometries + coverage + IMD + PCA) | 32,844 |
| `output/imd_subdomains.csv` | IMD total + 7 sub-domain scores per LSOA | 32,844 |
| `output/pca_scores.csv` | PC1, PC2 per LSOA | 4,834 |
| `output/coverage_metrics.csv` | Coverage % per LSOA | 32,844 |

**Fixes applied:**
- IMD File 5 download URL updated (old URL returned 404)
- Sheet name changed from first sheet ("Notes") to second sheet ("ID2015 Scores")
- London LSOAs filtered by `PC1 not NA` (4,833 London LSOAs out of 32,844 England/Wales)

### Data Export (`python/01_export_data.py`)

Exports all data to CSV + ESRI shapefile format for Rmd import.

**Outputs:**

| CSV (`output/csv/`) | Rows | Shapefile (`output/shp/`) | Features |
|---|---|---|---|
| `poi_tesco_stores.csv` | 577 | — | — |
| `coverage_lsoa.csv` | 4,833 | `lsoa_boundaries/` | 4,833 |
| `coverage_msoa.csv` | 951 | `msoa_boundaries/` | 951 |
| `coverage_ward.csv` | 630 | `ward_boundaries/` | 630 |
| `coverage_borough.csv` | 33 | `borough_boundaries/` | 33 |
| `imd_subdomains.csv` | 4,833 | — | — |
| `pca_scores.csv` | 4,833 | — | — |

**Shapefile column name note:** ESRI shapefiles truncate to 10 chars. Coverage columns renamed: `express_cov`, `super_cov`, `extra_cov`, `total_cov`, `overlap_ix`, `uniq_types`. Borough columns: `bor_code`, `bor_name`. The Rmd uses CSV for attributes (full names) and shapefile for geometry only.

### Geographic Lookup

Built LSOA → MSOA → Ward → Borough hierarchy via spatial joins:

| File | Description | Rows |
|------|-------------|------|
| `data/raw/lsoa_msoa_lookup.csv` | LSOA → MSOA | 4,833 |
| `data/raw/lsoa_full_lookup.csv` | LSOA → Ward → MSOA → Borough + name | 4,833 |

MSOA boundaries downloaded from ONS ArcGIS FeatureServer. Ward boundaries downloaded and paginated (7,707 total). Centroid-based spatial joins with nearest-neighbor fallback for 167 unmatched LSOAs.

---

## Analysis Results

### Stage 1: Supply-Side Spatial Analysis (`scripts/stage1_supply_side.R`)

| Metric | Result |
|--------|--------|
| Moran's I (total_coverage) | **0.484** (p < 0.001) |
| Moran's I (superstore) | 0.916 |
| Moran's I (extra) | 0.911 |
| Correlation with IMD | r = 0.038 (p = 0.008) |
| OLS R² (coverage ~ IMD) | **0.0015** |

**Key finding:** Supply-side coverage is highly spatially clustered but nearly independent of deprivation. Tesco's 15-min walking isochrones cover ~99% of London LSOAs.

**Visualizations:** `output/stage1_viz1_coverage_choropleth.png`, `output/stage1_viz2_lisa_cluster.png`, `output/stage1_viz3_coverage_vs_imd.png`

### Stage 2: IMD Sub-Domain Decomposition (`scripts/stage2_imd_decomposition.R`)

| Model | PC1 R² | PC2 R² |
|--------|--------|--------|
| A: IMD total score | 0.002 | 0.221 |
| B: 7 sub-domains | **0.325** | **0.344** |

**Key findings:**
- Sub-domain decomposition improves PC1 R² by **0.322** — total IMD score masks all predictive power
- **Income** is the strongest LASSO predictor for both PC1 (|β| = 2.70) and PC2 (|β| = 6.17)
- For PC2, **Employment** is second strongest (|β| = 5.94), consistent with Beydoun et al. (2026)
- All 7 domains survive LASSO regularization

**Visualizations:** `output/stage2_viz1_ols_coefficients.png`, `output/stage2_viz2_lasso_path.png`, `output/stage2_viz3_variable_importance.png`

### Multi-Scale Coverage Visualization (`scripts/stage1_multiscale.Rmd`)

Block-by-block Rmd importing CSV + shapefile, producing choropleths at 4 scales with POI dots overlaid. Knits to `output/stage1_multiscale.html`.

Coverage distribution across scales:

| Scale | n | Mean | SD | Min | Below 100% |
|-------|---|------|----|-----|-----------|
| LSOA | 4,833 | 99.7% | 4.5% | 0.0% | 52 |
| MSOA | 951 | 99.4% | 5.2% | 13.1% | 44 |
| Ward | 630 | 99.3% | 5.2% | 21.8% | 37 |
| Borough | 33 | 98.6% | 3.7% | 83.1% | 9 |

---

## Technical Notes

### R Gotchas Encountered

1. **`sf_use_s2(FALSE)`** — Required when working with projected data (EPSG:27700). S2 spherical geometry mode (default in sf ≥ 1.0) causes grey rendering artifacts.

2. **Never use `coord_sf()` when data is already projected** — `coord_sf(crs = "EPSG:27700")` on data already in EPSG:27700 triggers an internal reprojection that produces grey patches. Just omit it.

3. **`%+%` operator** — Not available without `stringr`/`scales`. Use `paste0()` instead.

4. **Shapefile 10-char column limit** — Always rename long columns before writing shapefiles.

5. **`geom_errorbarh()` deprecated** — Use `geom_errorbar()` with `orientation = "y"` in ggplot2 ≥ 4.0.

6. **`get_legend()`** — Requires `cowplot` package. Use patchwork layout with one panel having a legend instead.

### Python Notes

- IMD File 5 correct URL: `https://assets.publishing.service.gov.uk/media/5a818571e5274a2e87dbe132/File_5_ID_2015_Scores_for_the_Indices_of_Deprivation.xlsx`
- Isochrone computation: `nx.multi_source_dijkstra_path_length` with cutoff=1250m per store type (3 Dijkstra runs instead of 577)
- ArcGIS GeoJSON uses `attributes` + `geometry.rings` (not `properties` + `geometry.coordinates`); needs conversion and `set_crs(allow_override=TRUE)`

---

## What's Next

### Stage 3: Multi-Factor Prediction (XGBoost + SHAP) — Not started

Per `ar5302-research-plan.md`:
1. Assemble full feature matrix (7 IMD sub-domains + 5-6 supply-side + 2-3 demographics)
2. XGBoost with 5-fold CV for PC1 and PC2
3. SHAP analysis (global importance, summary plots, dependence plots for top-5)
4. Feature importance comparison: XGBoost vs LASSO vs OLS
