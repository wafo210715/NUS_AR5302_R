#!/usr/bin/env Rscript
# =============================================================================
# Stage 1: Supply-Side Spatial Analysis
#
# Research Question: Does spatial heterogeneity exist in Tesco store
#   accessibility across London's LSOAs, and is it independent of
#   area-level deprivation?
#
# Visualizations:
#   1. Choropleth map of total Tesco store coverage (%)
#   2. LISA cluster map for total_coverage
#   3. Scatter plot: total_coverage vs IMD score (with LOESS curve)
#
# Requires: output/lsoa_with_data.gpkg (from python/00_stage0_preprocess.py)
# =============================================================================

cat(paste0("=", strrep("=", 59)), "\n")
cat("Stage 1: Supply-Side Spatial Analysis\n")
cat(paste0("=", strrep("=", 59)), "\n\n")

# ── 0. Install missing packages ────────────────────────────────────────
required_packages <- c("sf", "spdep", "ggplot2", "dplyr", "patchwork",
                       "RColorBrewer", "scales", "gridExtra", "viridis")

for (pkg in required_packages) {
  if (!requireNamespace(pkg, quietly = TRUE)) {
    cat("Installing package:", pkg, "\n")
    install.packages(pkg, repos = "https://cloud.r-project.org", quiet = TRUE)
  }
}

suppressPackageStartupMessages({
  library(sf)
  library(spdep)
  library(ggplot2)
  library(dplyr)
  library(patchwork)
  library(RColorBrewer)
  library(scales)
  library(gridExtra)
})

# ── 1. Load data ──────────────────────────────────────────────────────
cat("Loading data ...\n")

gpkg_path <- "output/lsoa_with_data.gpkg"
if (!file.exists(gpkg_path)) {
  stop("GeoPackage not found. Run python/00_stage0_preprocess.py first.\n",
       "  Expected: ", gpkg_path)
}

lsoa <- st_read(gpkg_path, quiet = TRUE) %>%
  st_make_valid()

# Filter to London LSOAs (those with PCA data, i.e. in the Tesco dataset)
lsoa <- lsoa %>%
  filter(!is.na(PC1)) %>%
  filter(!is.na(total_coverage)) %>%
  filter(total_coverage >= 0)

cat(sprintf("  %d London LSOAs loaded\n", nrow(lsoa)))
cat(sprintf("  Coverage range: %.1f%% - %.1f%%\n",
            min(lsoa$total_coverage, na.rm = TRUE),
            max(lsoa$total_coverage, na.rm = TRUE)))

# ── 2. Moran's I Analysis ─────────────────────────────────────────────
cat("\n--- Moran's I Analysis ---\n")

# Build spatial weights (Queen contiguity)
nb <- poly2nb(lsoa, queen = TRUE, snap = 0.01)
lw <- nb2listw(nb, style = "W", zero.policy = TRUE)

# Global Moran's I for total_coverage
moran_total <- moran.test(lsoa$total_coverage, lw, zero.policy = TRUE)
cat(sprintf("\n  Total Coverage - Moran's I:\n"))
print(moran_total)

# Also test each store type
cat("\n  Store-type Moran's I:\n")
for (col in c("express_coverage", "superstore_coverage", "extra_coverage")) {
  if (col %in% names(lsoa)) {
    mi <- moran.test(lsoa[[col]], lw, zero.policy = TRUE)
    cat(sprintf("    %s: I = %.4f, p = %.4e\n",
                col, mi$estimate[1], mi$p.value))
  }
}

# ── 3. LISA (Local Moran's I) ────────────────────────────────────────
cat("\n--- LISA Analysis ---\n")

lisa_total <- localmoran(lsoa$total_coverage, lw, zero.policy = TRUE)
lisa_df <- as.data.frame(lisa_total)
names(lisa_df) <- c("Ii", "E.Ii", "Var.Ii", "Z.Ii", "Pr")

# Classify quadrants
z <- lsoa$total_coverage
z_lag <- lag.listw(lw, z, zero.policy = TRUE)

lisa_df$quad <- NA_character_
lisa_df$quad[z_lag >= median(z, na.rm = TRUE) & z >= median(z, na.rm = TRUE)] <- "HH"
lisa_df$quad[z_lag >= median(z, na.rm = TRUE) & z <  median(z, na.rm = TRUE)] <- "LH"
lisa_df$quad[z_lag <  median(z, na.rm = TRUE) & z <  median(z, na.rm = TRUE)] <- "LL"
lisa_df$quad[z_lag <  median(z, na.rm = TRUE) & z >= median(z, na.rm = TRUE)] <- "HL"

# Mark significance at p < 0.05
lisa_df$quad[lisa_df$Pr > 0.05] <- "Not Significant"

lsoa$lisa_quad <- lisa_df$quad
lsoa$lisa_Ii   <- lisa_df$Ii

cat(sprintf("  LISA clusters:\n"))
print(table(lsoa$lisa_quad))

# ── 4. Test independence from IMD ─────────────────────────────────────
cat("\n--- Independence from IMD ---\n")

valid <- lsoa %>% filter(!is.na(total_coverage) & !is.na(imd_score))

cor_test <- cor.test(valid$total_coverage, valid$imd_score)
cat(sprintf("  Correlation (total_coverage vs IMD): r = %.4f, p = %.4e\n",
            cor_test$estimate, cor_test$p.value))

# Simple linear regression
lm_fit <- lm(total_coverage ~ imd_score, data = valid)
cat(sprintf("  OLS R²: %.4f\n", summary(lm_fit)$r.squared))

# ── 5. VISUALIZATIONS ─────────────────────────────────────────────────
cat("\n--- Creating Visualizations ---\n")

# Color palettes
lisa_colors <- c(
  "HH" = "#E31A1C",   # red   — high-high (hot spot)
  "LH" = "#FD8D3C",   # orange — low-high (outlier)
  "LL" = "#3182BD",   # blue  — low-low (cold spot)
  "HL" = "#C6DBEF",   # light blue — high-low (outlier)
  "Not Significant" = "#F0F0F0"
)

# ── Visualization 1: Choropleth of total coverage ──────────────────────
cat("  Creating Viz 1: Choropleth of total coverage ...\n")

p1 <- ggplot(lsoa) +
  geom_sf(aes(fill = total_coverage), color = NA, linewidth = 0) +
  scale_fill_gradient2(
    low = "#FEE0D2", mid = "#FCBBA1", high = "#CB181D",
    midpoint = median(lsoa$total_coverage, na.rm = TRUE),
    name = "Total Coverage\n(% of LSOA area)",
    limits = c(0, 100),
    breaks = seq(0, 100, by = 20),
    labels = percent_format(scale = 1, suffix = "%")
  ) +
  labs(
    title = "Tesco Store Accessibility Across London",
    subtitle = "15-minute walking isochrone coverage (% of LSOA area covered by any Tesco store)",
    caption = "Data: Tesco Grocery 1.0 (CDRC), OSM"
  ) +
  theme_minimal(base_size = 11) +
  theme(
    legend.position = "bottom",
    legend.key.width = unit(2, "cm"),
    plot.title = element_text(face = "bold", size = 13),
    plot.subtitle = element_text(size = 10, color = "grey40"),
    plot.caption = element_text(size = 8, color = "grey50"),
    panel.grid = element_line(color = "grey90"),
    axis.text = element_blank(),
    axis.ticks = element_blank()
  ) +
  coord_sf(crs = "EPSG:27700", datum = NA)

ggsave("output/stage1_viz1_coverage_choropleth.png", p1,
       width = 10, height = 9, dpi = 200, bg = "white")
cat("    Saved: output/stage1_viz1_coverage_choropleth.png\n")

# ── Visualization 2: LISA Cluster Map ─────────────────────────────────
cat("  Creating Viz 2: LISA cluster map ...\n")

p2 <- ggplot(lsoa) +
  geom_sf(aes(fill = lisa_quad), color = "white", linewidth = 0.05) +
  scale_fill_manual(
    values = lisa_colors,
    name = "LISA Cluster\n(p < 0.05)",
    drop = FALSE,
    labels = c(
      "HH" = "High-High\n(Hot Spot)",
      "LH" = "Low-High\n(Spatial Outlier)",
      "LL" = "Low-Low\n(Cold Spot)",
      "HL" = "High-Low\n(Spatial Outlier)",
      "Not Significant" = "Not Significant"
    )
  ) +
  labs(
    title = "LISA Cluster Map: Tesco Store Coverage",
    subtitle = sprintf("Moran's I = %.3f (p < 0.001)", moran_total$estimate[1]),
    caption = "Queen contiguity weights; significance at p < 0.05"
  ) +
  theme_minimal(base_size = 11) +
  theme(
    legend.position = "bottom",
    legend.key.width = unit(1.5, "cm"),
    plot.title = element_text(face = "bold", size = 13),
    plot.subtitle = element_text(size = 10, color = "grey40"),
    plot.caption = element_text(size = 8, color = "grey50"),
    panel.grid = element_line(color = "grey90"),
    axis.text = element_blank(),
    axis.ticks = element_blank()
  ) +
  coord_sf(crs = "EPSG:27700", datum = NA)

ggsave("output/stage1_viz2_lisa_cluster.png", p2,
       width = 10, height = 9, dpi = 200, bg = "white")
cat("    Saved: output/stage1_viz2_lisa_cluster.png\n")

# ── Visualization 3: Scatter: Coverage vs IMD with LOESS ──────────────
cat("  Creating Viz 3: Scatter: coverage vs IMD with LOESS ...\n")

plot_df <- lsoa %>%
  filter(!is.na(total_coverage), !is.na(imd_score)) %>%
  mutate(
    # IMD decile (1 = most deprived)
    imd_decile = ntile(imd_score, 10)
  )

p3 <- ggplot(plot_df, aes(x = imd_score, y = total_coverage)) +
  geom_point(aes(color = imd_decile), alpha = 0.3, size = 1.2, shape = 16) +
  geom_smooth(method = "loess", se = TRUE, color = "#E31A1C",
              linewidth = 1, fill = "#FEE0D2", alpha = 0.6,
              span = 0.75) +
  geom_smooth(method = "lm", se = FALSE, color = "#3182BD",
              linewidth = 0.8, linetype = "dashed") +
  scale_color_viridis_c(
    option = "plasma",
    name = "IMD Decile\n(1=most deprived)",
    direction = -1,
    breaks = 1:10
  ) +
  labs(
    title = "Tesco Store Coverage vs. Area Deprivation",
    subtitle = sprintf("Pearson r = %.3f, p = %.1e | OLS R² = %.3f",
                       cor_test$estimate, cor_test$p.value,
                       summary(lm_fit)$r.squared),
    x = "IMD Score (higher = more deprived)",
    y = "Total Store Coverage (%)",
    caption = "Red line: LOESS fit | Blue dashed: OLS fit | Points coloured by IMD decile"
  ) +
  theme_minimal(base_size = 11) +
  theme(
    legend.position = "right",
    plot.title = element_text(face = "bold", size = 13),
    plot.subtitle = element_text(size = 10, color = "grey40"),
    plot.caption = element_text(size = 8, color = "grey50"),
    panel.grid.minor = element_blank()
  ) +
  ylim(0, 100)

ggsave("output/stage1_viz3_coverage_vs_imd.png", p3,
       width = 11, height = 7, dpi = 200, bg = "white")
cat("    Saved: output/stage1_viz3_coverage_vs_imd.png\n")

# ── Summary ───────────────────────────────────────────────────────────
cat(paste0("\n", strrep("=", 60)), "\n")
cat("STAGE 1 COMPLETE\n")
cat(strrep("=", 60), "\n")
cat(sprintf("  Moran's I (total_coverage): %.4f (p = %.2e)\n",
            moran_total$estimate[1], moran_total$p.value))
cat(sprintf("  Correlation with IMD: r = %.4f (p = %.2e)\n",
            cor_test$estimate, cor_test$p.value))
cat(sprintf("  OLS R² (coverage ~ IMD): %.4f\n",
            summary(lm_fit)$r.squared))
cat("\n  Visualizations saved to output/:\n")
cat("    1. stage1_viz1_coverage_choropleth.png\n")
cat("    2. stage1_viz2_lisa_cluster.png\n")
cat("    3. stage1_viz3_coverage_vs_imd.png\n")
