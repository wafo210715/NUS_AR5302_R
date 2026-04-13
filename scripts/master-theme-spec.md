# Master Visual Theme Specification

**Date**: 2026-03-31
**Decision log**: Based on color-palette-research.md, rmd-style-audit.md, narrative-mapping.md

---

## Design Decisions & Rationale

### Decision 1: Color Palette — Okabe-Ito + RdYlGn Sequential
**Why**: Nature-mandated colorblind-safe palette is the gold standard for academic publications. Okabe-Ito provides maximum distinguishability for categorical data. For sequential choropleth maps, we use a green sequential palette (RdYlGn reversed) instead of viridis to avoid the "too dark at extremes" issue and better differentiate coverage percentages.

**How to apply**: Define all colors at the top of the Rmd in a setup chunk. Never use hardcoded hex codes inline.

### Decision 2: Unified Base Theme — `theme_pub()`
**Why**: Audit found 5+ different theme configurations with drifting base_size (9/10/11), inconsistent margins, and repeated `element_blank()` calls. A single custom theme function eliminates all drift.

**How to apply**: Define `theme_pub()` in setup. All plots call `+ theme_pub()` instead of `+ theme_minimal() + theme(...)`.

### Decision 3: Consistent Figure Dimensions
**Why**: Audit found dimensions ranging from 8x6 to 16x14. Wide multi-panel plots need consistent aspect ratios.

**How to apply**:
- Full-width maps: 12 x 8 (4:3 ratio, fits well in knitted HTML/PDF)
- Wide panels (3-column): 14 x 5
- Wide panels (2-column): 12 x 5
- Standard single plots: 10 x 7
- Tall plots (boxplots, bar charts): 8 x 6

### Decision 4: Data Source Attribution
**Why**: Audit found zero data source credits. Assignment checklist requires "Did you attribute properly all the data?"

**How to apply**: Add a "Data Sources" note in the YAML and as captions on the first plot that uses each dataset.

### Decision 5: Cluster Labels — Human-Readable Names
**Why**: Current cluster map shows "1, 2, 3, 4" — meaningless without context. The report draft names them: Standard Urban, Superstore-dominant, Full Service, Underserved.

**How to apply**: Relabel cluster factors before plotting.

---

## Master Color Palette (Okabe-Ito, Nature-Recommended)

```r
# Categorical palette (up to 8 categories)
pal_categorical <- c(
  "#E69F00",  # Orange — primary accent
  "#56B4E9",  # Sky Blue — secondary accent
  "#009E73",  # Bluish Green
  "#F0E442",  # Yellow (use sparingly, poor contrast on white)
  "#CC79A7",  # Pink/Violet
  "#0077BB",  # Blue
  "#D55E00",  # Vermilion
  "#000000"   # Black
)

# Store type colors (3 categories — from categorical, picking best contrast)
pal_store_type <- c(
  "Express"    = "#0077BB",  # Blue
  "Superstore" = "#009E73",  # Green
  "Extra"      = "#D55E00"   # Vermilion/Orange-Red
)

# Model comparison colors (4 methods)
pal_model <- c(
  "OLS"      = "#CC79A7",  # Pink
  "LASSO"    = "#0077BB",  # Blue
  "XGBoost"  = "#009E73",  # Green
  "IMD Total" = "#E69F00"  # Orange
)

# Cluster colors (4 clusters — distinct, colorblind-safe)
pal_cluster <- c(
  "1: Standard Urban"  = "#56B4E9",  # Sky Blue
  "2: Superstore-dominant" = "#E69F00",  # Orange
  "3: Full Service"     = "#009E73",  # Green
  "4: Underserved"      = "#D55E00"   # Vermilion
)

# Sequential palette for choropleth maps (coverage %)
# Using viridis "plasma" — perceptually uniform, colorblind-safe, print-friendly
# Implemented via scale_fill_viridis_c(option = "plasma", begin = 0.1, end = 0.95)

# Diverging palette for z-scores (RdBu)
# Implemented via scale_fill_distiller(palette = "RdYlBu", direction = -1)

# SHAP gradient (blue-white-red)
shap_gradient <- c(low = "#2166AC", mid = "#F7F7F7", high = "#B2182B")

# Accent for LOESS/smooth lines
accent_line <- "#CC3311"
```

---

## Unified Base Theme: `theme_pub()`

```r
theme_pub <- function(base_size = 11, map_mode = FALSE) {
  ret <- theme_minimal(base_size = base_size) +
    theme(
      # Typography
      plot.title    = element_text(face = "bold", size = base_size + 2),
      plot.subtitle = element_text(size = base_size - 1, colour = "grey40"),
      plot.caption  = element_text(size = base_size - 3, colour = "grey50",
                                   hjust = 1, margin = margin(t = 4)),
      strip.text    = element_text(face = "bold", size = base_size),

      # Legend
      legend.position    = "bottom",
      legend.text        = element_text(size = base_size - 2),
      legend.title       = element_text(face = "bold", size = base_size - 1),
      legend.key.width   = unit(1.2, "cm"),
      legend.margin      = margin(4, 4, 4, 4),
      legend.box.margin  = margin(0, 0, 4, 0),

      # Grid
      panel.grid.minor = element_blank(),
      panel.grid.major = element_line(colour = "grey92", linewidth = 0.3),

      # Axes
      axis.title  = element_text(size = base_size),
      axis.text   = element_text(size = base_size - 1),

      # Margins
      plot.margin = margin(8, 8, 8, 8, unit = "pt")
    )

  if (map_mode) {
    ret <- ret + theme(
      axis.text  = element_blank(),
      axis.ticks = element_blank(),
      panel.grid = element_blank()
    )
  }

  ret
}
```

---

## Typography Rules

| Element | Font | Size | Style |
|---------|------|------|-------|
| Report title | System sans-serif | 18pt | Bold |
| Section headers (##) | System sans-serif | 14pt | Bold |
| Sub-headers (###) | System sans-serif | 12pt | Bold |
| Body text | System sans-serif | 11pt | Regular |
| Code | Monospace | 9pt | Regular |
| Plot title | System sans-serif | 13pt | Bold |
| Plot subtitle | System sans-serif | 10pt | Regular, grey40 |
| Plot caption | System sans-serif | 8pt | Regular, grey50 |
| Axis labels | System sans-serif | 10pt | Regular |
| Axis text | System sans-serif | 9pt | Regular |

---

## Figure Dimensions Reference

| Plot Type | Width | Height | Notes |
|-----------|-------|--------|-------|
| Full London map | 10 | 8 | Single panel, map mode |
| 2x2 multi-scale panel | 12 | 10 | Combined with patchwork |
| 3-column coverage strip | 14 | 5 | Express/Superstore/Extra |
| 2-column PCA maps | 12 | 6 | PC1 and PC2 side by side |
| Coefficient plot (faceted) | 12 | 6 | 2 DV facets |
| LASSO path (faceted) | 11 | 6 | 2 DV facets |
| Importance bar chart (faceted) | 12 | 7 | 4 method facets |
| SHAP beeswarm (faceted) | 14 | 8 | 2 DV facets |
| SHAP dependence (grid) | 14 | 10 | 5x2 grid |
| Boxplot / scatter | 8 | 6 | Standard |
| Silhouette plot | 8 | 5 | Diagnostic |
| Model comparison table | Full width | Auto | kable/modelsummary |

---

## YAML Output Configuration (for publication)

```yaml
output:
  html_document:
    toc: true
    toc_float: true
    code_folding: show
    fig_width: 10
    fig_height: 7
    theme: null          # Use our custom CSS
    highlight: tango     # Clean syntax highlighting
    df_print: paged
```

---

## Data Source Attribution Template

```
Data: Tesco Grocery 1.0 (Aiello et al., 2020) | Boundaries: ONS Open Geography
      | IMD 2015: Gov.uk | Socio-demographics: LSOA Atlas (2011 Census)
      | Road network: OpenStreetMap via OSRM
```

---

## Code Chunk Display Rules

| Chunk Type | echo | include | message | warning | comment |
|------------|------|---------|---------|---------|---------|
| Setup/packages | FALSE | FALSE | FALSE | FALSE | Hidden completely |
| Data loading | TRUE | TRUE | FALSE | FALSE | Code visible, no noise |
| Utility functions | TRUE | TRUE | FALSE | FALSE | Code visible |
| Diagnostic checks | TRUE | TRUE | FALSE | TRUE | Hide warnings for Moran's I etc |
| Plot generation | TRUE | TRUE | FALSE | FALSE | Code visible |
| Table output | TRUE | TRUE | FALSE | FALSE | Code visible |
| Save/export | TRUE | TRUE | FALSE | FALSE | Code visible |

**Key rule**: Assignment requires "code you wrote has to be visible" — so all analysis code stays visible. Only package loading gets hidden.
