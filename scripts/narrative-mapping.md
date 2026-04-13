# Narrative Mapping Report

## Overview
This document maps narrative text from the academic paper draft (`ar5302-report-draft.md`) to the corresponding sections in the Rmd file (`stage1_supply_side.Rmd`). The mapping follows the three-stage structure of the analysis:

- **Stage 1**: Supply-Side Spatial Analysis (sections 1-14 in Rmd)
- **Stage 2**: IMD Sub-Domain Decomposition (sections 1-11 in Rmd) 
- **Stage 3**: Multi-Factor Prediction XGBoost+SHAP (sections 1-8 in Rmd)

## Introduction
**Corresponding paragraph**: Lines 1-15 (Introduction section)

### Narrative mapping:
**Before Rmd**: 
"The conventional food desert paradigm assumes that limited access to affordable, nutritious food explains poor dietary outcomes. However, this supply-side view neglects the complex interplay between geography, deprivation, and actual purchasing behavior. Our research addresses this gap by examining how area-level deprivation and its sub-domains—when compared to supply-side accessibility metrics and socio-demographic factors—explain spatial variation in food purchasing patterns across London."

**After Rmd**:
"This analysis reveals that the relationship between deprivation and food purchasing is far more nuanced than conventional food desert narratives suggest. While physical store accessibility is an important consideration, it explains far less about dietary behaviors than who lives in an area—the socio-demographic composition and structural dimensions of deprivation."

---

## Stage 1: Supply-Side Spatial Analysis

### 1. Import POI Data (Section 1)
**Before Rmd**: 
"Understanding Tesco's spatial footprint requires accurate store location data. We began by importing point-of-interest data for all Tesco stores across London, classified into three types: Express (convenience format), Superstore (medium-large), and Extra (hypermarket). This geospatial foundation enables precise measurement of accessibility across London's neighborhoods."

### 2. Generate 1250m Walking Buffers (Section 2)
**Before Rmd**: 
"A 15-minute walking distance (approximately 1.25 km at 5 km/h) represents a reasonable threshold for foot-based food access in urban environments. For each store, we generated circular buffers representing this accessible area, then unioned buffers by store type to create continuous service areas—avoiding boundary artifacts that plague raster-based approaches."

### 3. Visualize Buffers Over London (Section 3)
**Before Rmd**: 
"Visual inspection reveals clear spatial patterns: Express stores form a dense network across central and inner London, while Superstores and Extra stores cluster in suburban areas and transportation hubs. This distribution reflects strategic positioning based on population density, land availability, and local demographics."

### 5. Coverage Computation Function (Section 5)
**Before Rmd**: 
"To quantify accessibility objectively, we developed a polygon-based coverage calculation that intersects unioned buffer areas with administrative boundaries. This approach normalizes for geographic unit size—larger boroughs don't receive artificially inflated coverage scores. Coverage percentage equals the area of intersection divided by total boundary area, multiplied by 100."

### 6. Compute Coverage at All 4 Scales (Section 6)
**Before Rmd**: 
"Accessibility patterns vary dramatically across geographic scales. At LSOA level (neighborhood scale), Tesco coverage approaches uniformity due to dense Express networks. At borough level (city-wide), patterns reflect broader urban structure. The MSOA (Middle Super Output Area) scale—approximately 7,200 residents per unit—emerges as optimal, balancing spatial resolution with meaningful differentiation across London."

### 7. Verify & Summarize Coverage (Section 7)
**Before Rmd**: 
"Quality assurance checks confirmed complete coverage calculations across all scales. Summary statistics reveal that total Tesco coverage averages 68% across London MSOAs, with wide variation from near-uniform inner-city coverage to sparse outer suburban areas. This variation provides the spatial heterogeneity needed for meaningful analysis."

### 8. Multi-Scale Comparison (Section 8)
**Before Rmd**: 
"The multi-scale panel visually demonstrates how coverage patterns change with aggregation level. LSOA coverage appears uniform due to small geographic size, while borough coverage shows coarse differentiation. MSOA coverage reveals the most meaningful spatial variation, confirming our methodological choice for subsequent analysis."

### 9. MSOA Coverage Maps (Section 9)
**Before Rmd**: 
"Mapping coverage by store type reveals distinct service patterns. Express coverage dominates central London and transport corridors, Superstore coverage follows suburban development patterns, and Extra coverage concentrates in outlying areas. This spatial differentiation forms the basis for our typological analysis of service areas."

### 10. K-Means Clustering — Service Typologies (Section 10)
**Before Rmd**: 
"Beyond raw coverage metrics, we applied K-means clustering to identify distinct service-area typologies. The silhouette method confirmed four optimal clusters representing different combinations of Express, Superstore, and Extra accessibility—from dense urban service areas to underserved peripheral neighborhoods."

### 11. Spatial Autocorrelation — Moran's I (Section 11)
**Before Rmd**: 
"Spatial autocorrelation analysis (Moran's I) confirms that Tesco coverage exhibits significant clustering across all metrics. The strongest clustering appears in Express coverage (I = 0.58, p < 0.001), reflecting deliberate network design. LISA analysis reveals that spatial heterogeneity stems from concentrations of larger stores rather than absence of service, as even peripheral areas maintain baseline Express coverage."

### 13. Test Independence from Deprivation (Section 13)
**Before Rmd**: 
"A critical question is whether accessibility patterns align with deprivation. Correlation analysis reveals only weak associations between coverage metrics and IMD scores (r = 0.03 to 0.21). However, categorical analysis reveals a striking inversion: the best-served areas (Full Service clusters) are most deprived, while underserved areas have lower deprivation scores—challenging conventional food desert narratives and suggesting Tesco's large-format stores concentrate in dense, deprived areas where demand is highest."

### 14. Save Outputs (Section 14)
**Before Rmd**: 
"This comprehensive spatial analysis establishes that Tesco accessibility exhibits meaningful spatial heterogeneity across London, but this pattern shows only weak association with deprivation. The service typology clusters provide discrete categories for deeper investigation of how accessibility intersects with socioeconomic factors."

---

## Stage 2: IMD Sub-Domain Decomposition

### 1. Load Packages & Data (Section 1)
**Before Rmd**: 
"The second stage examines how deprivation dimensions relate to food purchasing behavior, replicating Beydoun et al.'s (2026) methodology but applying it to actual purchasing data rather than supply-side metrics. We operationalized this using Tesco Grocery 1.0 data aggregated to MSOA level, paired with IMD sub-domain scores and population weights."

### 2. PCA on Food Categories (Section 2)
**Before Rmd**: 
"Principal Component Analysis on 13 food category proportions revealed two dominant dimensions: PC1 (35.4% variance) captures a 'Convenience' axis distinguishing processed-heavy from fresh-oriented purchasing baskets, while PC2 (13.2% variance) captures a 'Hedonic' dimension centered on alcohol expenditure. Together, these components explain 48.6% of total variance in food purchasing composition."

### 2b. PCA Biplot (Section 2b)
**Before Rmd**: 
"The biplot visualization confirms the interpretability of our components. PC1 clearly separates processed foods (positive loadings) from fresh produce and meats (negative loadings), while PC2 distinguishes alcohol categories from staples. This dimensional reduction allows us to model complex purchasing patterns through two theoretically meaningful outcomes."

### 3. Aggregate to MSOA (Section 3)
**Before Rmd**: 
"LSOA-level data was aggregated to MSOA using population-weighted means, preserving representational accuracy while reducing computational complexity. This transition from neighborhood to neighborhood-group level matches the scale used in the supply-side analysis, enabling cross-stage integration."

### 4. Standardize (Section 4)
**Before Rmd**: 
"All continuous variables were standardized to z-scores to ensure comparability across different measurement scales and units. This allows direct comparison of coefficient magnitudes across regression models and facilitates interpretation of effect sizes."

### 4b. Spatial Visualization of PCA Scores (Section 4b)
**Before Rmd**: 
"Spatial mapping reveals clear geographic patterns in purchasing behavior. PC1 (Convenience) shows higher scores in central and east London, reflecting areas with greater reliance on processed foods. PC2 (Hedonic) patterns are less spatially structured but show concentration in specific neighborhoods. These spatial distributions provide context for interpreting regression results."

### 5. Model A — OLS (IMD Total Score) (Section 5)
**Before Rmd**: 
"The baseline model used standardized IMD total score to predict purchasing patterns. Results confirm IMD's limitations: it explains virtually none of the variation in convenience-oriented purchasing (R² = 0.014), though it performs better for hedonic purchasing (R² = 0.322). This asymmetry suggests that aggregate deprivation scores mask important sub-domain heterogeneity."

### 6. Model B — OLS (7 IMD Sub-Domains) (Section 6)
**Before Rmd**: 
"Decomposing IMD into constituent sub-domains dramatically improves explanatory power. For PC1, the sub-domain model achieves adj. R² = 0.459—a 32-fold increase over the composite score. This demonstrates that IMD total actively conceals opposing directional effects across domains. Income deprivation emerges as the strongest predictor for convenience purchasing (β = +5.454), while employment deprivation dominates hedonic purchasing (β = +14.036)."

### 7. Model Comparison (Section 7)
**Before Rmd**: 
"The comparison starkly illustrates why composite indices fail. IMD total's weak performance (R² = 0.014 for PC1) stems from cancellation effects where income and employment deprivation pull in opposite directions. Sub-domain decomposition not only improves prediction but reveals which deprivation dimensions actually matter—and how they operate differently across purchasing dimensions."

### 8. LASSO Variable Selection (Section 8)
**Before Rmd**: 
"LASSO regression confirms that all seven sub-domains retain predictive power under regularization, with coefficients consistent in sign and relative magnitude with OLS estimates. This indicates that even weaker predictors carry genuine signal, and the solution is not an artefact of multicollinearity."

### 9. Visualization — OLS Coefficient Comparison (Section 9)
**Before Rmd**: 
"The coefficient comparison plot visually demonstrates how sub-domain decomposition reshapes our understanding. While IMD total shows negligible effects, individual domains reveal significant directional effects—particularly income and employment deprivation, which operate in opposing directions across the two purchasing dimensions."

### 10. Visualization — LASSO Regularization Path (Section 10)
**Before Rmd**: 
"The regularization paths confirm model stability. As penalty increases, coefficients shrink toward zero but maintain relative ordering, with income and employment deprivation remaining dominant predictors throughout. This robustness supports our interpretation of their substantive importance."

### 11. Visualization — Variable Importance Ranking (Section 11)
**Before Rmd**: 
"Importance rankings reveal consistent patterns across methods: income deprivation dominates PC1 prediction, employment deprivation dominates PC2, and education skills and living environment show significant effects. This pattern establishes baseline expectations for the multi-factor analysis in Stage 3."

---

## Stage 3: Multi-Factor Prediction

### 1. Load Packages & Socio-Demographic Data (Section 1)
**Before Rmd**: 
"The final stage integrates all three variable groups—supply-side metrics from Stage 1, IMD sub-domains from Stage 2, and socio-demographic controls—to test which factors retain predictive power when competing directly. Socio-demographic data (% BAME, car ownership) was sourced from the LSOA Atlas and aggregated to MSOA level using population weights."

### 2. Build Feature Matrix (Section 2)
**Before Rmd**: 
"We constructed a comprehensive feature matrix including 15 variables: 7 IMD sub-domains, 6 supply-side coverage metrics, and 2 socio-demographic controls. High collinearity between cluster dummies and raw coverage metrics led us to drop categorical variables, preserving the continuous coverage metrics for analysis."

### 3. XGBoost with Cross-Validation (Section 3)
**Before Rmd**: 
"XGBoost with 5-fold cross-validation was used to model non-linear relationships beyond the scope of linear models. The ensemble approach achieved significantly improved performance: R² = 0.586 for PC1 and 0.749 for PC2—representing substantial gains over linear baselines and capturing complex interactions between predictors."

### 4. Model Performance Comparison (Section 4)
**Before Rmd**: 
"Performance comparisons validate our multi-stage approach. The XGBoost model improves upon the sub-domain baseline by +0.123 in PC1 R² and +0.227 in PC2 R², demonstrating that socio-demographic and supply-side factors contribute uniquely to purchasing behavior beyond deprivation alone."

### 5. SHAP Analysis (Section 5)
**Before Rmd**: 
"SHAP analysis reveals a dramatic reshuffling of feature importance. For PC1 (Convenience), education deprivation (mean |SHAP| = 0.311) and living environment deprivation (0.279) emerge as top predictors, while income deprivation—the apparent dominant factor in isolation—drops out of the top five entirely. For PC2 (Variety), % BAME dominates overwhelmingly (0.574), validating Broadbridge et al.'s finding about ethnic composition's role."

### 6. Visualization — SHAP Summary Plot (Section 6)
**Before Rmd**: 
"The SHAP beeswarm plot visually confirms the reshuffling. Supply-side metrics rank consistently low across both dimensions, reinforcing the central argument that physical accessibility explains less about purchasing behavior than who lives in an area. Education deprivation and % BAME emerge as the strongest predictors in the integrated model."

### 7. Visualization — SHAP Dependence Plots (Section 7)
**Before Rmd**: 
"Depence plots reveal non-linear patterns not captured by linear models. Education deprivation shows a clear threshold effect on convenience purchasing, while % BAME exhibits complex non-linear relationships with hedonic purchasing—patterns that the XGBoost+SHAP approach captures effectively."

### 8. Visualization — Feature Importance Comparison (Section 8)
**Before Rmd**: 
"The importance comparison across methods (OLS, LASSO, XGBoost+SHAP) shows how model choice affects interpretation. Linear methods emphasize different dimensions than the non-linear ensemble, but consistently show that supply-side metrics rank lowest across all approaches—confirming that supply-side interventions alone may be insufficient to improve dietary outcomes."

---

## Conclusion
**Corresponding paragraph**: Lines 108-111 (Conclusion section)

### Narrative mapping:
**Before Rmd**: 
"This study demonstrates that the relationship between deprivation and food purchasing is far more nuanced than composite indices suggest. IMD total explains virtually none of the variation in convenience-oriented purchasing, yet its sub-domains collectively explain nearly half—revealing that opposing directional effects across deprivation dimensions cancel in the aggregate score. When socio-demographic factors compete alongside deprivation in a non-linear model, the picture shifts again: income deprivation— the apparent dominant predictor in isolation—drops out entirely, replaced by education deprivation, living environment, and ethnic composition as the key drivers. Supply-side Tesco accessibility consistently ranks as the weakest predictor group for both purchasing dimensions, reinforcing that physical proximity to food retailers explains far less than who lives in an area."

**After Rmd**: 
"Together, these findings challenge the conventional food desert paradigm: improving food purchasing outcomes may depend less on opening new stores and more on addressing structural socio-demographic inequalities. The multi-stage approach reveals how linear models can mask important relationships, and how non-linear machine learning methods can uncover complex patterns that remain hidden in simpler analyses. This complexity suggests that dietary interventions must be tailored to specific deprivation dimensions rather than relying on blanket supply-side solutions."

---

## Word Count Summary
- Total narrative text recommended: ~1,250 words
- Text distributed across: 8 sections (Introduction + 7 analysis sections)
- Average per section: ~156 words (ranging from 50-250 words per section)
- Focus areas: 
  - Emphasizing methodological innovations (multi-scale analysis, SHAP integration)
  - Highlighting counterintuitive findings (accessibility-deprivation inversion)
  - Connecting across stages to show progressive insight
  - Contextualizing results within existing literature (Broadbridge, Beydoun)
  - Practical implications for food policy and intervention design
