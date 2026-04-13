# AR5302 Assignment 2 — Research Plan (Revised)

**Date:** 2026-03-29
**Status:** Brainstorming complete, ready for implementation

---

## Research Questions

### Primary RQ

> To what extent do area-level deprivation (and its sub-domains), supply-side factors, and socio-demographic characteristics explain spatial variation in food purchasing patterns across London?

### Sub-RQ 1: Supply-Side Spatial Heterogeneity

> Does spatial heterogeneity exist in Tesco store accessibility across London, and is it independent of area-level deprivation?

**Why this matters:** Broadbridge found that walking distance to the nearest store has almost no effect on purchasing patterns. But their measure was crude — "distance to nearest Tesco." Our approach captures store *type diversity* and *service coverage*. A key methodological consideration is the choice of spatial unit: LSOAs are too small (15-min walking buffers cause near-complete coverage in dense areas, washing out heterogeneity), while boroughs are too coarse. We empirically compare LSOA, MSOA, Ward, and Borough scales to select the most informative unit for analysis.

### Sub-RQ 2: IMD Sub-Domain Decomposition (Beydoun-Inspired)

> Which dimensions of deprivation (if any) are most strongly associated with food purchasing behaviour in London, and does this differ from Beydoun et al. (2026)'s finding that employment deprivation is the strongest predictor of food *desert risk*?

**Why this matters:** This adapts Beydoun's approach (LASSO for variable selection on IMD sub-domains) but substitutes their DV (EFDI — supply-side accessibility) with our DV (PC scores — demand-side purchasing). We use standard LASSO rather than Adaptive LASSO because our feature set is small (7 sub-domains), and omit Mixed-Effects since London boroughs have far less inter-regional variation than Beydoun's England/Scotland/Wales split. If the same deprivation domain predicts both, it suggests a unified structural driver. If different domains emerge, it reveals a disconnect between supply and demand.

### Sub-RQ 3: Multi-Factor Competition

> When supply-side factors, deprivation sub-domains, and socio-demographic characteristics compete in a single model, which factors retain the strongest predictive power for food purchasing behaviour?

**Why this matters:** Stage 2 establishes clean bivariate relationships. Stage 3 tests whether these relationships survive in a realistic "noisy" multivariate setting, and reveals non-linear patterns that linear methods miss.

---

## Experimental Design

### Stage 0: Data Preparation

**Inputs:**
- Tesco Grocery 1.0 (POI + purchase data, already have)
- IMD 2015 (7 sub-domains at LSOA level, open-source from Gov.uk)
- LSOA boundaries (shapefile, already have)
- Additional socio-demographics: ethnicity (% BAME from Census), housing price (from ONS/LSOA Atlas)

**Outputs:**
- `MSOA_features.parquet` — one row per MSOA with all merged features

### Stage 1: Supply-Side Spatial Analysis

**Goal:** Characterize the spatial distribution of Tesco store service quality across London.

**Method:**

```
1. For each Tesco store:
   - Geocode location (lat, lon) — already in POI data
   - Classify type: Express / Superstore / Extra

2. Generate 15-minute walking isochrone for each store:
   - Tool: OSRM (Open Source Routing Machine) via Python
   - Or use: networkx + OSM street network (osmnx)
   - Output: polygon per store

3. Scale exploration (decide analysis unit):
   - For each of 4 scales (LSOA, MSOA, Ward, Borough):
     a. Compute coverage metrics via polygon intersection:
        express_coverage% = area(unit ∩ express_buffers) / area(unit)
        superstore_coverage% = area(unit ∩ superstore_buffers) / area(unit)
        extra_coverage% = area(unit ∩ extra_buffers) / area(unit)
        total_coverage% = area(unit ∩ any_buffer) / area(unit)
     b. Visualize Tesco POI density + buffer coverage at each scale
     c. Assess: does this scale reveal meaningful spatial heterogeneity?
   - Expected finding: LSOA too small (near-complete coverage, no signal),
     Borough too coarse. MSOA likely optimal.
   - Document scale selection rationale (for Methods section + Figure 1)

4. Coverage computation at chosen scale (MSOA, pending empirical confirmation):
   - For each MSOA, compute via polygon intersection:
     express_coverage% = area(MSOA ∩ express_buffers) / area(MSOA)
     superstore_coverage% = area(MSOA ∩ superstore_buffers) / area(MSOA)
     extra_coverage% = area(MSOA ∩ extra_buffers) / area(MSOA)
     total_coverage% = area(MSOA ∩ any_buffer) / area(MSOA)
     overlap_index = (express% + superstore% + extra%) - total%
     unique_types = count of distinct store types covering this MSOA

5. Clustering:
   - Features per MSOA: [express%, superstore%, extra%]
   - Standardize, then K-Means (k=2-6, select by silhouette score)
   - Result: k=4, silhouette = 0.6+
   - Interpret clusters: e.g., "Express-dominant", "Superstore-dominant",
     "Mixed", "Underserved"
   - Map clusters on London choropleth

6. Spatial analysis:
   - Moran's I on each coverage metric (report as number in text, no map)
   - Choropleth maps for each metric

7. Test independence from deprivation (two complementary approaches):
   a. Continuous approach:
      - Aggregate IMD to MSOA (population-weighted mean of constituent LSOAs, using Tesco data's population field from ONS 2015 mid-year estimates)
      - Correlation: coverage metrics vs IMD score
      - Scatter: total_coverage% vs IMD (with loess curve)
      - Result: all correlations weak (r = 0.03–0.21), no clear linear relationship
   b. Categorical approach (cluster-based):
      - ANOVA / Kruskal-Wallis: do mean IMD scores differ across the 4 cluster types?
      - If significant: post-hoc pairwise test (e.g., Tukey HSD) to identify which pairs differ
      - This captures non-linear, type-level relationships that correlation misses
      - Expected: Underserved MSOAs may have higher IMD than Full Service, but Standard Urban vs Full Service may not differ
```

**Why no grid cell approach:** At LSOA scale, 15-min walking buffers produce near-complete coverage across London, washing out spatial heterogeneity. Grid cells within LSOA boundaries create boundary artifacts — edge cells may be majority-uncovered, producing misleading "no service" readings for units that are actually well-served. Direct polygon intersection at the MSOA scale avoids both problems.

**Deliverables:**
- Scale selection comparison figure (LSOA vs MSOA vs Ward vs Borough)
- Supply-side feature table (one row per MSOA)
- Cluster map + interpretation
- Moran's I results (text only, no map — no significant Low-Low coldspots)
- Independence test results: correlation table + ANOVA/Kruskal-Wallis + post-hoc test

**Key libraries:** `osmnx`, `geopandas`, `shapely`, `pysal`, `libpysal`, `scikit-learn` (KMeans)

### Stage 2: IMD Sub-Domain Decomposition (Linear Baseline)

**Goal:** Replicate Beydoun's methodology with purchasing data as DV.

**Note:** All Stage 2 models operate at MSOA level (n = 961). PC1 and PC2 are aggregated from LSOA to MSOA via population-weighted mean; IMD sub-domains are aggregated via population-weighted mean of constituent LSOAs.

**Method:**

```
1. Prepare IMD sub-domain data:
   - Download IMD 2015 sub-domain scores from Gov.uk (LSOA level)
   - Aggregate LSOA-level data to MSOA (population-weighted mean of constituent LSOAs)
   - Aggregate PC1, PC2 from LSOA to MSOA (population-weighted mean)
   - Merge → one row per MSOA with: PC1, PC2, IMD_total, 7 sub-domains
   - Z-score standardize all independent variables

2. OLS regression — Model A (IMD total), at MSOA level:
   PC1_msoa ~ IMD_total_msoa
   PC2_msoa ~ IMD_total_msoa

3. OLS regression — Model B (IMD sub-domains), at MSOA level:
   PC1_msoa ~ income + employment + education + health + crime + barriers + living_environment
   PC2_msoa ~ income + employment + education + health + crime + barriers + living_environment

4. Compare:
   - Model A vs Model B: does sub-domain decomposition improve R²?
   - PC1 vs PC2: which DV is better explained?
   - Our results vs Beydoun's: same strongest predictor?
   - Note: R² values will differ from Broadbridge (who used LSOA) due to ecological aggregation

5. LASSO (variable selection, inspired by Beydoun):
   - 7 sub-domains as features, PC1_msoa as DV
   - 7 sub-domains as features, PC2_msoa as DV
   - Standardize features, LassoCV with 5-fold CV
   - Report: which sub-domains survive regularization (coef ≠ 0)?
   - Note: Beydoun used Adaptive LASSO; we use standard LASSO because our variable set is small (7 sub-domains) and Adaptive LASSO offers negligible improvement with few features
```

**Deliverables:**
- Regression tables (OLS + LASSO)
- Coefficient comparison plot (our results vs Beydoun's)
- Variable importance ranking from LASSO

**Key libraries:** `statsmodels`, `scikit-learn`

### Stage 3: Multi-Factor Prediction (XGBoost + SHAP)

**Goal:** Test relative importance of all factors in a non-linear, multivariate setting. Each variable group has an explicit theoretical source — no variables are introduced without justification.

**Note:** All features and targets at MSOA level (n = 961). PC1, PC2, and socio-demographics aggregated from LSOA via population-weighted mean; supply-side metrics and cluster assignments computed directly at MSOA level in Stage 1.

**Variable groups and theoretical justification:**

| Group | Variables | Theoretical source | Rationale |
|-------|-----------|-------------------|-----------|
| Deprivation | IMD 7 sub-domains | Beydoun et al. (2026) | Replicate their framework; test if same domains predict demand-side purchasing |
| Supply-side | coverage %, cluster dummies | Our Stage 1 | Counterintuitive coverage–deprivation finding; richer than Broadbridge's single walk time |
| Socio-demographics | % BAME, car ownership % | Broadbridge et al. (2025) | Both significant in their OLS (R² = 0.38); neither is captured by IMD |

**Variables NOT included and why:**
- ~~Median housing price~~ — not used in either reference paper; likely collinear with IMD income + living environment sub-domains
- ~~Population density~~ — not used in either reference paper; likely collinear with supply-side coverage metrics
- ~~Walk time~~ — subsumed by our multi-dimensional supply-side coverage metrics (Stage 1)
- ~~Household income~~ — already captured by IMD income sub-domain
- ~~Age~~ — Broadbridge found it significant but with the weakest effect (β = −0.21 vs income β = −0.73); can be added as sensitivity analysis if time permits
- ~~Education level~~ — Broadbridge explicitly excluded due to collinearity with income

**Method:**

```
1. Feature engineering:
   Features per MSOA:
   - IMD sub-domains (7): income, employment, education, health, crime, barriers, living_env
   - Supply-side (5-6): express%, superstore%, extra%, total%, overlap, unique_types
   - Supply-side cluster (one-hot encoded, 3 dummies from 4 clusters)
   - Socio-demographics (2): % BAME, car ownership %
   - Note: if cluster dummies and raw coverage % are highly collinear, drop one or the other

2. Target variables (MSOA-level, population-weighted aggregated from LSOA):
   - PC1 (Convenience: processed vs fresh)
   - PC2 (Variety: narrow vs diverse)

3. Model:
   - XGBoost regressor (xgboost.XGBRegressor)
   - 5-fold cross-validation
   - Hyperparameter tuning: max_depth, learning_rate, n_estimators, min_child_weight, subsample

4. SHAP analysis:
   - shap.TreeExplainer
   - Global feature importance (mean |SHAP|)
   - SHAP summary plot (direction of effect)
   - SHAP dependence plots for top-5 features

5. Comparison:
   - XGBoost R² vs OLS R² vs LASSO R²
   - XGBoost feature ranking vs LASSO feature ranking vs OLS coefficient magnitude
   - Does supply-side gain importance when competing with deprivation?
   - Does the strongest deprivation sub-domain remain the same as Stage 2?
```

**Deliverables:**
- Model performance comparison table
- SHAP summary plot
- SHAP dependence plots for top-5 features
- Feature importance ranking comparison (XGBoost vs LASSO vs OLS)

**Key libraries:** `xgboost`, `shap`, `scikit-learn`

---

## Data Requirements

| Data | Source | Format | Status |
|------|--------|--------|--------|
| Tesco Grocery 1.0 (POI) | CDRC | CSV | Already have |
| Tesco Grocery 1.0 (Purchases) | CDRC | CSV | Already have |
| PCA results (PC1, PC2 per LSOA) | Computed | CSV/parquet | Already have |
| IMD 2015 total score | Gov.uk | CSV | **Need to download** |
| IMD 2015 sub-domain scores (7 domains) | Gov.uk | CSV | **Need to download** |
| LSOA boundaries (2011) | ONS | Shapefile | Already have |
| MSOA boundaries (2011) | ONS | Shapefile | **Need to download** |
| Ward boundaries | London Datastore | Shapefile | **Need to download** |
| Borough boundaries | London Datastore | Shapefile | **Need to download** |
| LSOA Atlas (BAME %, car ownership %) | CDRC/LSOA Atlas | CSV | **Need to download** |
| OSM street network (London) | OpenStreetMap | PBF | **Need to download** |

---

## Implementation Order (for Claude Code)

### Phase 1: Data Acquisition
1. Download IMD 2015 sub-domain data from Gov.uk
2. Download LSOA Atlas data for % BAME and car ownership (Broadbridge's significant predictors)
3. Download MSOA, Ward, Borough boundaries
4. Aggregate all LSOA-level data to MSOA (population-weighted mean) → `MSOA_features.parquet`

### Phase 2: Stage 1 — Supply-Side Analysis
6. Build 15-min walking isochrones for all Tesco stores
7. Scale exploration: compute coverage at LSOA, MSOA, Ward, Borough → visualize → select scale
8. Compute coverage metrics at chosen scale via polygon intersection
9. K-Means clustering → interpret service typology
10. Moran's I + choropleth maps
11. Correlation: coverage metrics vs IMD
12. ANOVA/Kruskal-Wallis: IMD across cluster types + post-hoc

### Phase 3: Stage 2 — IMD Decomposition (all at MSOA level)
13. Aggregate PC1, PC2 from LSOA to MSOA (population-weighted mean)
14. OLS: IMD total → PC1, PC2
15. OLS: IMD sub-domains → PC1, PC2
16. LASSO: sub-domains → PC1, PC2
17. Comparison with Beydoun results

### Phase 4: Stage 3 — XGBoost + SHAP (all at MSOA level)
18. Assemble full feature matrix (IMD sub-domains + supply-side + cluster dummies + % BAME + car ownership)
19. XGBoost with CV for PC1 and PC2
20. SHAP analysis
21. Feature importance comparison across methods

### Phase 5: Visualization & Reporting
22. Compile all figures and tables
23. Write up results

---

## Limitations to Acknowledge

1. **Tesco-only data**: Only captures Clubcard users' purchases at Tesco. Channel substitution (Aldi, Lidl, Iceland, local shops) is invisible. Clubcard users may have higher store loyalty, which is a strength (less noise) but limits generalizability.

2. **Cross-sectional**: No causal inference. Only association.

3. **Compositional data**: PC scores from proportional food data violate orthogonality assumptions of PCA. Following Broadbridge, we primarily report PC1 results and treat PC2 as supplementary.

4. **Isochrone assumption**: 15-min walking isochrone assumes uniform walking speed and street network quality. Does not account for store opening hours, stock levels, or in-store experience. Does not differentiate between walking and driving modes — in peri-urban London, many shoppers may drive to larger stores.

5. **Temporal mismatch**: IMD 2015 vs Tesco data 2015 vs LSOA Atlas (2011 Census). Broadbridge used the same 2011 Census socio-demographics, so this is consistent with the literature.

6. **London-only**: Results may not generalize to other UK cities or rural areas.

---

## Academic Positioning

This study positions itself at the intersection of two recent contributions:
- **Broadbridge et al. (2025)**: Used Tesco data to identify food deserts, but only used IMD-independent variables (income, BAME, age from LSOA Atlas). Never tested IMD sub-domains.
- **Beydoun et al. (2026)**: Tested IMD sub-domains against food desert risk (EFDI), but used no real purchasing data.

**Our contribution:** We bridge these two approaches by testing IMD sub-domains against *actual purchasing behaviour* (not supply-side accessibility), and by adding supply-side spatial heterogeneity as a competing predictor alongside deprivation. The XGBoost + SHAP analysis goes beyond both studies by testing non-linear, multi-factor competition.
