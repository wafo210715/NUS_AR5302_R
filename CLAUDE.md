# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

NUS AR5302 course project analyzing spatial patterns in food purchasing behavior. The main research question examines how Tesco store characteristics versus area deprivation (IMD) explain spatial variation in food purchasing patterns across London.

## Commands

### Python Analysis
```bash
# Run data acquisition (downloads IMD data, Tesco POI from OSM, London boundaries)
python python/01_acquire_data.py

# Run main analysis (PCA, regression, visualizations)
python python/02_analysis.py
```

### R
Open R scripts in RStudio or run via command line:
```bash
Rscript <script.R>
```

## Dependencies

### Python
- requests, pandas, numpy, matplotlib, seaborn
- scikit-learn, statsmodels, scipy
- openpyxl (for Excel files)

### R
- tidyverse, ggplot2, lubridate
- rmarkdown, tinytex

## Project Structure

```
├── python/
│   ├── 01_acquire_data.py   # Downloads IMD, OSM Tesco data, London boundaries
│   └── 02_analysis.py       # PCA, regression analysis, visualizations
├── data/
│   ├── raw/                  # Downloaded external datasets
│   └── *.csv                 # Singapore datasets (HDB, hawker centres)
├── tesco-data/
│   └── 7796666/              # Tesco grocery data by LSOA/MSOA/ward/borough
└── output/                   # Generated visualizations and reports
```

## Data Sources

- **Tesco grocery data**: `tesco-data/7796666/year_lsoa_grocery.csv` - annual grocery purchasing patterns at LSOA level
- **IMD 2015**: Index of Multiple Deprivation from UK Government
- **Tesco POI**: Queried from OpenStreetMap Overpass API
- **London boundaries**: GIS boundary files from London Datastore

## Analysis Workflow

1. **Acquire data** (`01_acquire_data.py`): Downloads external datasets
2. **Spatial processing**: Assigns Tesco stores to LSOAs using KD-tree nearest neighbor
3. **PCA**: Extracts dietary patterns from food category proportions (PC1="Convenience", PC2="Variety")
4. **Regression**: Compares store metrics vs IMD in explaining dietary patterns
5. **Visualization**: Generates 5 core visualizations to `output/`

## R / sf Gotchas

1. **`sf_use_s2(FALSE)`** — Required when working with projected data (EPSG:27700). S2 spherical geometry mode (default in sf ≥ 1.0) causes grey rendering artifacts.

2. **Never use `coord_sf()` when data is already projected** — `coord_sf(crs = "EPSG:27700")` on data already in EPSG:27700 triggers an internal reprojection that produces grey patches. Just omit it.

3. **`scale_fill_gradient(limits = ...)` censors out-of-bounds values to grey** — `st_intersection` can produce overlap areas microscopically larger than the boundary area due to floating point precision, giving coverage >100%. The default `oob = scales::censor` turns these into `NA` for rendering (grey). Fix: either remove `limits` entirely, or add `oob = scales::squish`.

4. **`st_intersection` drops non-intersecting rows** — Units with 0% coverage won't appear in the result. Always use `left_join` + `replace_na(0)` to fill them back in.

5. **`st_area()` returns units** — In projected CRS (EPSG:27700), it returns `units[m²]`. Wrap in `as.numeric()` for arithmetic.

6. **Shapefile 10-char column limit** — Always rename long columns before writing shapefiles (e.g. `express_coverage` → `expr_cov`).

7. **`geom_errorbarh()` deprecated** — Use `geom_errorbar()` with `orientation = "y"` in ggplot2 ≥ 4.0.

8. **`poly2nb()` topology warnings** — London boundaries have disconnected components. Use `zero.policy = TRUE`.
