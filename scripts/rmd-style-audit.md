# RMD Style Audit - Stage 1 Supply Side Analysis

## 1. All ggplot2 Theme Calls

### Unique Theme Configurations:

#### A. `theme_minimal(base_size = 11)` (Lines 146, 499, 636, 690)
```r
theme_minimal(base_size = 11) +
theme(
  legend.position = "right",
  axis.text = element_blank(),
  axis.ticks = element_blank()
)
```
**Used in**: Buffer visualization, K-means map, IMD scatter, PCA correlation

#### B. `theme_minimal(base_size = 10)` (Lines 288, 300, 369, 431, 494, 846, 1095, 1140, 1484, 1507, 1648)
- **Lines 288-291**: Multi-panel map
  ```r
  theme_minimal(base_size = 10) +
  theme(
    plot.title = element_text(face = "bold"),
    axis.text = element_blank(), 
    axis.ticks = element_blank(),
    plot.margin = margin(2, 2, 2, 2, unit = "pt")
  )
  ```

- **Lines 369-378**: Single panel map (LSOA level)
  ```r
  theme_minimal(base_size = 10) +
  theme(
    legend.position = "none",
    plot.title = element_text(face = "bold", size = 12),
    plot.subtitle = element_text(size = 8, colour = "grey40")
  )
  ```

- **Lines 431-436**: MSOA panel
  ```r
  theme_minimal(base_size = 10) +
  theme(
    legend.position = "none",
    plot.title = element_text(face = "bold"),
    axis.text = element_blank(),
    axis.ticks = element_blank()
  )
  ```

- **Lines 846-852**: PCA biplot
  ```r
  theme_minimal(base_size = 10) +
  theme(
    plot.title = element_text(face = "bold", size = 12),
    plot.subtitle = element_text(size = 9, colour = "grey40")
  )
  ```

- **Lines 1095-1099**: OLS coefficient comparison
  ```r
  theme_minimal(base_size = 10) +
  theme(
    legend.position = "bottom",
    strip.text = element_text(face = "bold")
  )
  ```

- **Lines 1140-1144**: LASSO path
  ```r
  theme_minimal(base_size = 10) +
  theme(
    legend.position = "bottom",
    legend.text = element_text(size = 7),
    strip.text = element_text(face = "bold", size = 9),
    plot.title = element_text(face = "bold", size = 12)
  )
  ```

#### C. `theme_void(base_size = 11)` (Lines 920-926)
```r
theme_void(base_size = 11) +
theme(
  plot.title = element_text(face = "bold", size = 13, hjust = 0.5),
  plot.subtitle = element_text(colour = "grey40", size = 10, hjust = 0.5),
  legend.position = "bottom",
  legend.key.width = unit(1.5, "cm")
)
```
**Used in**: PCA spatial maps

#### D. `theme_minimal(base_size = 9)` (Lines 1503, 1557, 1648)
- **Lines 1503-1511**: SHAP summary plot
  ```r
  theme_minimal(base_size = 9) +
  theme(
    legend.position = "right",
    legend.key.width = unit(0.8, "cm")
  )
  ```

- **Lines 1557-1565**: SHAP dependence plots
  ```r
  theme_minimal(base_size = 9) +
  theme(
    strip.text = element_text(face = "bold", size = 8),
    plot.title = element_text(face = "bold", size = 13),
    plot.subtitle = element_text(size = 9, colour = "grey40")
  )
  ```

- **Lines 1648-1656**: Feature importance comparison
  ```r
  theme_minimal(base_size = 9) +
  theme(
    strip.text = element_text(face = "bold", size = 10),
    plot.title = element_text(face = "bold", size = 13),
    plot.subtitle = element_text(size = 9, colour = "grey40"),
    plot.caption = element_text(size = 7, colour = "grey50"),
    panel.grid.minor = element_blank(),
    panel.grid.major.y = element_blank()
  )
  ```

#### E. Plot Annotation Themes
- **Lines 309-310**: 
  ```r
  plot_annotation(title = "Shapefile & Area Check",
                  theme = theme(plot.title = element_text(face = "bold", size = 14)))
  ```
- **Lines 946-947**:
  ```r
  caption = "Analysis at MSOA scale. Borough boundaries overlaid in white.",
  theme = theme(plot.caption = element_text(colour = "grey50", hjust = 0.5))
  ```

### Theme Inconsistencies:
1. **base_size varies**: 11, 10, 9 - not consistent across plots
2. **Plot title sizes**: 14, 13, 12, bold/not bold mixed
3. **Subtitle styles**: Some use `size`, some use `colour = "grey40"`, some missing
4. **Legend positions**: Mix of "right", "bottom", "none", and manual positioning
5. **Caption sizes**: Mixed usage - some use theme, some don't
6. **Margin units**: Some use `margin(2, 2, 2, 2, unit = "pt")`, some don't specify margins

## 2. All Color Scale Calls

### Manual Color Vectors:
- **Line 133**: `type_colors <- c("Express" = "#1f78b4", "Superstore" = "#33a02c", "Extra" = "#e31a1c")`
- **Lines 1083-1084**: OLS comparison
  ```r
  scale_fill_manual(values = c("A: IMD Total" = "#7570B3",
                               "B: Sub-domains" = "#D95F02"))
  ```
- **Lines 1195-1197**: LASSO path
  ```r
  scale_fill_manual(values = c(
    "OLS (PC1)" = "#7570B3", "OLS (PC2)" = "#E7298A",
    "LASSO (PC1)" = "#1B9E77", "LASSO (PC2)" = "#D95F02"
  ))
  ```
- **Lines 1492-1493**: SHAP gradient
  ```r
  scale_fill_gradient2(low = "#2166AC", mid = "#F7F7F7", high = "#B2182B")
  ```
- **Lines 1637-1638**: Final importance comparison
  ```r
  scale_fill_manual(values = c("OLS" = "#7570B3", "LASSO" = "#D95F02",
                                "XGBoost" = "#1B9E77"))
  ```

### Built-in Scales:
- **Line 298**: `scale_fill_viridis_c(na.value = "grey50")`
- **Lines 357-360**: Coverage gradient
  ```r
  scale_fill_gradient(
    low = "#FFFFCC", high = "#B2182B",
    breaks = seq(0, 100, by = 20)
  )
  ```
- **Lines 425-428**: Similar gradient
  ```r
  scale_fill_gradient(
    low = "#FFFFCC", high = "#B2182B"
  )
  ```
- **Line 494**: `scale_fill_brewer(palette = "Set2", name = "Cluster")`
- **Line 685**: `scale_fill_brewer(palette = "Set2", guide = "none")`
- **Lines 915-917**: PCA z-score scale
  ```r
  scale_fill_distiller(
    palette = "RdBu", direction = -1, name = "Z-Score"
  )
  ```
- **Line 1131**: `scale_colour_brewer(palette = "Set2", name = "Domain")`

### Color Inconsistencies:
1. **Multiple green shades**: `#2ca02c` (line 286), `#33a02c` (type_colors), `#1B9E77` (LASSO/XGBoost)
2. **Red palette**: `#e31a1c` (type_colors), `#B2182B` (gradients), `#CC3311` (arrows), `#2166AC` (SHAP low)
3. **Blue variations**: `#1f78b4` (type_colors), `#7570B3` (OLS), `#4477AA` (points)
4. **Color schemes**: Viridis, Set2, RdBu, custom gradients - no consistent palette strategy

## 3. All Figure Dimensions

### Plot Sizes:
- **12×9**: Line 132 - Buffer visualization (seems appropriate for map)
- **16×14**: Lines 283, 386 - Shapefile check and multiscale comparison (large for detail inspection)
- **16×6**: Line 420 - MSOA by type maps (wide for multiple panels)
- **8×6**: Lines 477, 623, 682 - K-means optimal, IMD scatter, boxplot (reasonable for smaller plots)
- **10×9**: Line 491 - Cluster map (good aspect ratio)
- **10×8**: Line 798 - PCA biplot (standard)
- **14×7**: Line 904 - PCA maps (wide for spatial visualization)
- **12×6**: Line 1036 - OLS visualization (wide)
- **11×6**: Lines 1088, 1153 - LASSO path and importance (consistent size)
- **14×10**: Line 1466 - SHAP summary (large for detail)
- **16×10**: Line 1519 - SHAP dependence (very wide)
- **13×9**: Line 1569 - Feature comparison (good size)

### Potential Mismatches:
1. **Line 420**: `16×6` for MSOA maps - might be too tall for the content
2. **Line 1519**: `16×10` for SHAP dependence - extremely wide aspect ratio
3. **Line 283**: `16×14` for shapefile check - very large dimensions for what appears to be boundary checks

## 4. Code Chunks That Could Be Hidden

### Potentially Hideable Chunks (if code folding allowed):

#### Setup Chunks:
- **Lines 14-41**: Package installation and loading (`setup` chunk)
  - Pure utility code
  - Not analysis-specific
  - Could have `include = FALSE`

#### Utility Functions:
- **Lines 284-291**: `plot_boundary` function definition
  - Helper function for repeated plotting pattern
  - Could be hidden with `echo = FALSE`

#### Data Path Chunk:
- **Lines 43-48**: Path definitions (`paths` chunk)
  - Infrastructure code
  - Could be hidden

#### K-Means Helper:
- **Lines 507-525**: Cluster composition analysis
  - Results interpretation code
  - Could be shown in text instead

### Current State:
All chunks have `echo = TRUE` due to assignment requirements, but the `setup` chunk has `include = FALSE` which is appropriate.

## 5. Current Annotation/Caption Style

### Title Patterns:
- Most follow: "Main Analysis Topic" (Line 495: "K-Means Service Typology Clusters (MSOA Level)")
- Some include methodology: "Method-specific" (Line 1037: "OLS Regression Coefficients: IMD vs. Food Purchasing Patterns")

### Subtitle Patterns:
- Usually explains the metric/variable being shown (Line 402: "15-minute walking buffer coverage (% of area covered by at least one Tesco store)")
- Sometimes includes technical details (Line 497: sprintf("k = %d | Features: Express, Superstore, Extra coverage", k_chosen))
- Some explain interpretation (Line 1551: "Each point = one MSOA | Red line = LOESS trend | Dashed = zero effect")

### Caption Patterns:
1. **Color explanations** (Line 144: "Blue = Express | Green = Superstore | Red = Extra")
2. **Scale descriptions** (Line 403: "LSOA (~1,500 residents) | MSOA (~7,200) | Ward (electoral division) | Borough (~250,000) | Black dots = Tesco stores")
3. **Statistical information** (Line 1093: "DV = z-scored PC1/PC2 | *** p<0.001, ** p<.01, * p<0.05")
4. **Method notes** (Line 1137: "5-fold cross-validation | Domains with coef = 0 are eliminated")
5. **Data source/analysis scale** (Line 946: "Analysis at MSOA scale. Borough boundaries overlaid in white.")

### Data Source Credits:
**No explicit data source credits found**. The document assumes readers know:
- Tesco store locations are treated as given
- Shapefiles are loaded from standard directories
- No mention of OS OpenData, ONS, or other data sources
- No license/copyright information for boundary data

## 6. Inconsistencies

### A. Naming Conventions:
1. **Variable naming**: Mixed `colours` vs `colors` (though mostly `colors` American spelling)
2. **Metric names**: Some abbreviated (`metric`), some full words (`total_coverage`)
3. **Factor levels**: Some use `factor()` explicitly, some rely on default coercion

### B. Theme Drift:
1. **Base size drift**: From 11 (early plots) → 10 (most plots) → 9 (later plots)
2. **Caption evolution**: Early captions are simple, later ones include more statistical notation
3. **Subtitle complexity**: Simple → increasingly detailed with technical terms

### C. Redundant Theme Elements:
1. **Legend positioning**: Multiple chunks override position separately instead of using a unified theme
2. **Axis styling**: `element_blank()` repeated many times - could use a base theme
3. **Plot margins**: Some use `margin()`, others rely on defaults

### D. Inconsistent Scale Applications:
1. **Gradients**: Two instances of identical `#FFFFCC` → `#B2182B` gradients could be unified
2. **Brewer palettes**: "Set2" used multiple times but with different purposes
3. **Manual vs automatic**: Some scales use manual colors, others use built-in palettes

### E. Code Style Inconsistencies:
1. **String interpolation**: Sometimes `sprintf()` sometimes direct strings
2. **Function calls**: Mix of `aes_string()` and `aes()` (mostly aes() which is good)
3. **tidyverse conventions**: Mostly consistent use of pipes and tidy verbs

### Recommendations:
1. Create a base theme object to standardize sizing, fonts, and margins
2. Define a color palette at the beginning for consistency
3. Unify gradient definitions into named objects
4. Add data source citations for reproducibility
5. Consider reducing figure dimensions for very wide plots (lines 420, 1519)
