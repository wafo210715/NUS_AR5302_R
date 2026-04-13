# Project Progress — Session 2

**Date:** 2026-03-29

---

## What Changed

Restructured Stage 1 to be fully Rmd-native. All coverage metrics are now computed from scratch in R using `sf` spatial operations, instead of importing pre-computed CSVs from Python preprocessing. The analysis scale was confirmed as MSOA.

---

## Stage 1: Supply-Side Spatial Analysis (`scripts/stage1_supply_side.Rmd`)

### Architecture

All analysis conducted block-by-block in a single Rmd. Data flow:

```
POI CSV (565 stores)          Boundary shapefiles (4 scales, independent)
  store_type, lon, lat        geometry only (EPSG:27700)
        |                            |
        v                            |
  poi_sf (sf POINT)                  |
        |                            |
        v                            |
  buffers_by_type (3 rows)           |
  Express/Superstore/Extra           |
        |                            |
        +---- st_intersection -------+--- for each scale independently
                                      |
                    +----------------+----------------+----------------+
                    |                |                |                |
                    v                v                v                v
             lsoa_cov (4,833)  msoa_cov (951)   ward_cov (630)   bor_cov (33)
```

Key design decisions:
- **Circular buffers** (`sf::st_buffer(dist = 1250)`) instead of network isochrones — simpler, R-native, adequate for dense urban London
- **Independent intersection per scale** — coverage = `area(intersection) / area(boundary) × 100`, not aggregated from LSOA. Properly normalizes for unit size.
- **Union buffers by store type** (3 polygons instead of 565) before intersection — critical for performance

### Rmd Chunk Structure

| # | Section | Key Operations |
|---|---------|---------------|
| 0 | Setup | `sf`, `dplyr`, `ggplot2`, `patchwork`, `scales`, `spdep`, `cluster`, `factoextra`. `sf_use_s2(FALSE)`. Auto-install missing packages. |
| 1 | Import POI | Read CSV, filter out "Unknown" (Tesco Mobile), convert to sf EPSG:27700 |
| 2 | Generate Buffers | 1250m circular buffers, union by store type (3 rows) |
| 3 | Visualize Buffers | Semi-transparent buffers + MSOA boundary background + POI dots |
| 4 | Load Boundaries | Shapefiles from `output/shp/` (geometry only, strip pre-computed columns) |
| 5 | Coverage Function | Reusable `compute_coverage(boundaries, buffers, buffer_all, id_col)` — called 4 times |
| 6 | Compute Coverage | LSOA (4,833), MSOA (951), Ward (630), Borough (33) |
| 7 | Checkpoints | NA check, out-of-bounds check, shapefile completeness, area_m2 check |
| 8 | Multi-Scale Panel | 2×2 choropleth: LSOA \| MSOA / Ward \| Borough |
| 9 | MSOA Coverage Maps | Coverage by store type (Express, Superstore, Extra) at MSOA scale |
| 10 | K-Means Clustering | k=4 (silhouette-optimal), cluster map + profile bar chart |
| 11 | Moran's I | Queen contiguity on MSOA, test 5 coverage metrics |
| 12 | LISA Cluster Map | Local Moran's I on `superstore_coverage` at MSOA |
| 13 | IMD Independence Test | Aggregate IMD to MSOA via lookup table, correlation + scatter with loess |
| 14 | Save | Export `coverage_msoa_rmd.csv` |

### Bug Fixes & Gotchas

1. **Grey areas in choropleth (root cause found):** `scale_fill_gradient(limits = c(0, 100))` with default `oob = scales::censor` turns values >100% (from floating point precision in `st_intersection`) into NA, rendered as grey. Fix: removed `limits` parameter entirely — coverage >100% is meaningful (overlap density).
   - Checkpoint 1 (NA check) passed because `100.0000001` is not `NA`
   - Checkpoint 2 (shapefile green fill) passed because geometry is complete
   - Checkpoint 2b (area_m2 fill) passed because all areas are valid
   - The out-of-bounds check revealed: 1,667 LSOAs had `total_coverage > 100`

2. **IMD join producing duplicate columns:** Running the `imd-aggregate` chunk multiple times in RStudio caused `left_join` to create `imd_score.x`, `imd_score.y` suffix columns. Fix: `select(-any_of(imd_cols))` before join to make the chunk idempotent.

3. **`scale()` on sf object fails:** `st_drop_geometry()` must be called before `scale()` — geometry column is not numeric.

4. **`Unknown` store types:** These are Tesco Mobile (not food stores). Filtered out instead of mapping to Express (565 stores remain: 487 Express, 47 Superstore, 31 Extra).

### Visualization Choices

- **Color gradient:** `scale_fill_gradient(low = "#FFFFCC", high = "#B2182B")` — sequential yellow-to-red. Replaced diverging blue-white-red which was poor for near-saturated coverage data.
- **MSOA background:** Added `geom_sf(data = msoa_geom, fill = NA, colour = "grey70")` under buffer visualization for geographic context.
- **No `coord_sf()`:** Data already in EPSG:27700; adding it causes grey patches.
- **No `limits` on gradient:** Coverage can exceed 100% due to overlapping buffers — this is meaningful information.

### Analysis Scale Selection

MSOA confirmed as optimal scale:
- LSOA: too fine-grained, near-complete coverage washes out heterogeneity
- Borough: too coarse, smooths everything
- MSOA: reveals meaningful spatial patterns in store type diversity

---

## Files Modified/Created

| File | Action |
|------|--------|
| `scripts/stage1_supply_side.Rmd` | **Created** — full Stage 1 Rmd (58 chunks) |
| `CLAUDE.md` | **Updated** — added R/sf gotchas section |

---

## What's Next

### Stage 2: IMD Sub-Domain Decomposition — Not started

Per `ar5302-research-plan.md`:
1. Prepare IMD sub-domain data at MSOA level (already done in Stage 1 §13)
2. OLS: PC1/PC2 ~ IMD total score
3. OLS: PC1/PC2 ~ 7 IMD sub-domains
4. LASSO variable selection
5. Compare with Beydoun et al. (2026) findings

### Stage 3: Multi-Factor Prediction (XGBoost + SHAP) — Not started
