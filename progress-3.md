# Project Progress — Session 3

**Date:** 2026-03-31

---

## What Changed

Added Stage 3 (Multi-Factor Prediction with XGBoost + SHAP) and a PCA biplot visualization to `stage1_supply_side.Rmd`. All three stages now live in a single Rmd.

---

## PCA Biplot (appended to Stage 2)

Added `s2-pca-biplot` chunk between `s2-pca` and `s2-merge`:

- **Style:** Fig 5 from reference paper — LSOA-level PCA scores as blue dots with food category loading arrows (red, auto-scaled)
- **Auto-scaling:** `arrow_scale` computed as `min(range(scores) / range(loadings)) * 0.8` to fit arrows within the score axis
- **Label positioning:** `hjust`/`vjust` flip based on arrow direction so labels don't overlap arrows
- **Data level:** LSOA (4,833 points) — shows full spatial granularity before MSOA aggregation

---

## Stage 3: Multi-Factor Prediction (XGBoost + SHAP)

All code appended to `scripts/stage1_supply_side.Rmd` after Stage 2.

### Data Sources

| Source | File | Variables | Aggregation |
|--------|------|-----------|-------------|
| Stage 2 | `msoa_df` | PC1_z, PC2_z, 7 IMD sub-domains (raw) | Already MSOA-level |
| Stage 1 | `msoa_cov` | 6 supply-side metrics + cluster (4 levels) | Already MSOA-level |
| New | `data/raw/lsoa-atlas/london_lsoa_bame_car.csv` | pct_bame, pct_car_ownership | LSOA → MSOA (pop-weighted) |

### Architecture

```
msoa_df (Stage 2)          msoa_cov (Stage 1)         socio_msoa (new)
  PC1_z, PC2_z              express/superstore/extra    pct_bame
  7 IMD sub-domains         total_coverage, overlap     pct_car_ownership
       |                        |                         |
       +---- inner_join --------+----- inner_join --------+
                                     |
                              feature_df (n ≈ 951)
                                     |
                              collinearity check
                          (cluster dummies vs coverage)
                                     |
                              xgb.DMatrix → xgb.cv → xgb.train
                                     |
                              SHAP values → visualizations
```

### Feature Matrix (18 features)

| Group | Features | Count |
|-------|----------|-------|
| Deprivation | income, employment, education, health, crime, barriers, living_environment | 7 |
| Supply-side | express_coverage, superstore_coverage, extra_coverage, total_coverage, overlap_index, unique_types | 6 |
| Cluster | cluster_2, cluster_3, cluster_4 (one-hot, cluster_1 = reference) | 3 |
| Socio-demographics | pct_bame, pct_car_ownership | 2 |

### Rmd Chunk Structure

| # | Chunk | Purpose |
|---|-------|---------|
| 1 | `s3-packages` | Install/load `xgboost` |
| 2 | `s3-load-socio` | Load BAME/car ownership, aggregate to MSOA (pop-weighted) |
| 3 | `s3-build-features` | Merge all data sources, one-hot encode clusters, `complete.cases()` filter |
| 4 | `s3-collinearity` | Check cluster dummies vs coverage metrics (drop dummies if \|r\| > 0.9) |
| 5 | `s3-prepare-matrix` | Define feature columns, build raw matrix + targets |
| 6 | `s3-xgb-pc1` | `xgb.cv()` 5-fold for PC1, report best iteration / CV R² |
| 7 | `s3-xgb-pc2` | `xgb.cv()` 5-fold for PC2 |
| 8 | `s3-performance` | R² comparison table: OLS vs LASSO vs XGBoost |
| 9 | `s3-shap-values` | Train final models, compute SHAP via `predcontrib = TRUE`, global importance |
| 10 | `s3-viz1-shap` | SHAP summary (boxplot + jitter, colored by feature value) |
| 11 | `s3-viz2-dependence` | SHAP dependence plots for top-5 features (2 × 5 grid) |
| 12 | `s3-viz3-importance` | Feature importance comparison: OLS vs LASSO vs XGBoost |

### Bug Fixes & Gotchas

1. **`xgb.DMatrix` doesn't survive between knitr chunks:** External C++ pointer gets invalidated between chunk evaluations. Fix: create `xgb.DMatrix` in the same chunk as `xgb.cv()` / `xgb.train()`.

2. **Segfault in `xgb.train()` after `xgb.cv()`:** `xgb.cv()` can corrupt the DMatrix object. Fix: recreate DMatrix before `xgb.train()`, set `nthread = 1`.

3. **`cv_object$best_iteration` returns NULL in newer xgboost:** API changed. Fix: compute directly from evaluation log: `which.min(cv_object$evaluation_log$test_rmse_mean)`.

4. **`print_every_n` deprecated:** Removed from `xgb.cv()` call — parameter no longer exists in current xgboost version.

5. **Duplicate factor levels in importance comparison:** `factor(label, levels = label[order(...)])` fails when the same label appears 3 times (OLS/LASSO/XGBoost). Fix: use `fct_reorder(label, importance, .fun = max, .desc = TRUE)`.

6. **LASSO R² computation used wrong X matrix:** Stage 3 overwrote `X_mat` with 18 features, but LASSO needs only 7 IMD sub-domains. Fix: extract `X_imd <- as.matrix(feature_df[, domain_names])` for LASSO predictions.

### Key Design Decisions

- **Raw (unstandardized) features for XGBoost:** Tree-based models are scale-invariant; standardization unnecessary
- **Z-scored targets (PC1_z, PC2_z):** For fair R² comparison with OLS/LASSO from Stage 2
- **Manual SHAP via `predcontrib = TRUE`:** No dependency on `SHAPforxgboost`; full control over ggplot2 styling
- **`nthread = 1`:** Prevents segfaults and threading issues in knitr environment
- **SHAP summary uses boxplot + jitter** instead of true beeswarm (which would require `ggbeeswarm` package)

---

## Files Modified/Created

| File | Action |
|------|--------|
| `scripts/stage1_supply_side.Rmd` | **Modified** — added PCA biplot chunk + full Stage 3 (10 chunks) |

---

## What's Next

### Visualization & Reporting — Not started

Per `ar5302-research-plan.md`:
1. Compile all figures and tables
2. Write up results
3. Review against academic positioning (Broadbridge + Beydoun bridge)
