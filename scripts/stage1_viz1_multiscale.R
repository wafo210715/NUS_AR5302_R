#!/usr/bin/env Rscript
# =============================================================================
# Stage 1 Viz 1 (Multi-Scale): Tesco Store Coverage Choropleth
#   at LSOA, MSOA, Ward, and Borough scales
#
# Shows how spatial patterns in Tesco store accessibility change
# with geographic resolution.
#
# Requires:
#   output/lsoa_with_data.gpkg       (LSOA level - from Stage 0)
#   output/msoa_coverage.gpkg        (MSOA level - dissolved from LSOA)
#   output/ward_coverage.gpkg        (Ward level  - dissolved from LSOA)
#   output/borough_coverage.gpkg     (Borough level - dissolved from LSOA)
# =============================================================================

cat(paste0("=", strrep("=", 59)), "\n")
cat("Stage 1 Viz 1: Multi-Scale Coverage Choropleth\n")
cat(paste0("=", strrep("=", 59)), "\n\n")

# ── 0. Install missing packages ────────────────────────────────────────
required_packages <- c("sf", "ggplot2", "dplyr", "patchwork", "scales",
                       "RColorBrewer", "gridExtra")

for (pkg in required_packages) {
  if (!requireNamespace(pkg, quietly = TRUE)) {
    cat("Installing package:", pkg, "\n")
    install.packages(pkg, repos = "https://cloud.r-project.org", quiet = TRUE)
  }
}

suppressPackageStartupMessages({
  library(sf)
  sf_use_s2(FALSE)  # Disable S2 spherical geometry — causes rendering artifacts with projected data
  library(ggplot2)
  library(dplyr)
  library(patchwork)
  library(scales)
  library(RColorBrewer)
  library(gridExtra)
})

# ── 1. Load all geographic levels ─────────────────────────────────────
cat("Loading data ...\n")

lsoa  <- st_read("output/lsoa_with_data.gpkg",   quiet = TRUE) %>%
  st_make_valid() %>%
  filter(!is.na(PC1), !is.na(total_coverage), total_coverage >= 0) %>%
  mutate(n_units = n())

msoa  <- st_read("output/msoa_coverage.gpkg",     quiet = TRUE) %>%
  st_make_valid() %>%
  filter(!is.na(total_coverage))

ward  <- st_read("output/ward_coverage.gpkg",     quiet = TRUE) %>%
  st_make_valid() %>%
  filter(!is.na(total_coverage))

bor   <- st_read("output/borough_coverage.gpkg",  quiet = TRUE) %>%
  st_make_valid() %>%
  filter(!is.na(total_coverage))

# Ensure all in BNG
lsoa <- st_transform(lsoa, crs = 27700)
msoa <- st_transform(msoa, crs = 27700)
ward <- st_transform(ward, crs = 27700)
bor  <- st_transform(bor,  crs = 27700)

cat(sprintf("  LSOA:    %d units\n", nrow(lsoa)))
cat(sprintf("  MSOA:    %d units\n", nrow(msoa)))
cat(sprintf("  Ward:    %d units\n", nrow(ward)))
cat(sprintf("  Borough: %d units\n", nrow(bor)))

# ── 2. Create choropleth function ─────────────────────────────────────
make_choropleth <- function(gdf, title, subtitle, n_label = NULL) {

  # Use consistent colour scale across all maps
  p <- ggplot(gdf) +
    geom_sf(aes(fill = total_coverage), color = NA, linewidth = 0) +
    scale_fill_gradient2(
      low = "#2166AC", mid = "#F7F7F7", high = "#B2182B",
      midpoint = 50,
      name = "Total Coverage\n(% area)",
      limits = c(0, 100),
      breaks = seq(0, 100, by = 20),
      labels = percent_format(scale = 1, suffix = "%")
    ) +
    labs(
      title = title,
      subtitle = subtitle,
      caption = "15-min walking isochrone coverage | British National Grid"
    ) +
    theme_minimal(base_size = 9) +
    theme(
      legend.position = "none",  # single shared legend below
      plot.title = element_text(face = "bold", size = 11),
      plot.subtitle = element_text(size = 8, color = "grey40"),
      plot.caption = element_text(size = 6, color = "grey50"),
      panel.grid = element_line(color = "grey90"),
      axis.text = element_blank(),
      axis.ticks = element_blank(),
      plot.margin = margin(2, 2, 2, 2, unit = "pt")
    ) +
    coord_sf(crs = "EPSG:27700", datum = NA, expand = FALSE)

  # Add boundary lines at appropriate thickness
  if (nrow(gdf) <= 40) {
    # Borough: thin white boundary
    p <- p + geom_sf(color = "white", linewidth = 0.3, fill = NA)
  } else if (nrow(gdf) <= 700) {
    # MSOA/Ward: very thin boundary
    p <- p + geom_sf(color = "grey70", linewidth = 0.05, fill = NA)
  }

  return(p)
}

# ── 3. Create four panels ─────────────────────────────────────────────
cat("\nCreating choropleths ...\n")

p_lsoa <- make_choropleth(
  lsoa,
  title = "LSOA Level",
  subtitle = sprintf("n = %d | Mean: %.1f%% | SD: %.1f%%",
                     nrow(lsoa), mean(lsoa$total_coverage, na.rm = TRUE),
                     sd(lsoa$total_coverage, na.rm = TRUE))
)

p_msoa <- make_choropleth(
  msoa,
  title = "MSOA Level",
  subtitle = sprintf("n = %d | Mean: %.1f%% | SD: %.1f%%",
                     nrow(msoa), mean(msoa$total_coverage, na.rm = TRUE),
                     sd(msoa$total_coverage, na.rm = TRUE))
)

p_ward <- make_choropleth(
  ward,
  title = "Ward Level",
  subtitle = sprintf("n = %d | Mean: %.1f%% | SD: %.1f%%",
                     nrow(ward), mean(ward$total_coverage, na.rm = TRUE),
                     sd(ward$total_coverage, na.rm = TRUE))
)

p_bor <- make_choropleth(
  bor,
  title = "London Borough Level",
  subtitle = sprintf("n = %d | Mean: %.1f%% | SD: %.1f%%",
                     nrow(bor), mean(bor$total_coverage, na.rm = TRUE),
                     sd(bor$total_coverage, na.rm = TRUE))
)

# ── 4. Combine panels ────────────────────────────────────────────────
cat("Combining panels ...\n")

# Give one panel a legend, hide from others
p_msoa_leg <- p_msoa +
  theme(legend.position = "right",
        legend.key.width = unit(1.5, "cm"))

final <- (p_lsoa + p_msoa_leg) / (p_ward + p_bor) +
  plot_layout(heights = c(1, 1)) +
  plot_annotation(
    title = "Tesco Store Accessibility Across London: Multi-Scale Comparison",
    subtitle = "15-minute walking isochrone coverage (% of area covered by at least one Tesco store)",
    caption = "LSOA = Lower Super Output Area (~1,500 residents) | MSOA = Middle SOA (~7,200) | Ward = Electoral Ward | Borough = London Borough (~250,000)",
    theme = theme(
      plot.title = element_text(face = "bold", size = 14),
      plot.subtitle = element_text(size = 10, color = "grey40"),
      plot.caption = element_text(size = 7, color = "grey50", hjust = 0.5),
      plot.margin = margin(5, 5, 5, 5, unit = "pt")
    )
  )

# Save combined
ggsave("output/stage1_viz1_multiscale_coverage.png", final,
       width = 16, height = 14, dpi = 200, bg = "white")
cat("  Saved: output/stage1_viz1_multiscale_coverage.png\n")

# ── 5. Also save individual panels for flexibility ────────────────────
ggsave("output/stage1_viz1_lsoa_coverage.png", p_lsoa +
         theme(legend.position = "right",
               legend.key.width = unit(1.5, "cm")),
       width = 10, height = 9, dpi = 200, bg = "white")
ggsave("output/stage1_viz1_msoa_coverage.png", p_msoa +
         theme(legend.position = "right",
               legend.key.width = unit(1.5, "cm")),
       width = 10, height = 9, dpi = 200, bg = "white")
ggsave("output/stage1_viz1_ward_coverage.png", p_ward +
         theme(legend.position = "right",
               legend.key.width = unit(1.5, "cm")),
       width = 10, height = 9, dpi = 200, bg = "white")
ggsave("output/stage1_viz1_borough_coverage.png", p_bor +
         theme(legend.position = "right",
               legend.key.width = unit(1.5, "cm")),
       width = 10, height = 9, dpi = 200, bg = "white")
cat("  Saved individual panels to output/\n")

# ── Summary ───────────────────────────────────────────────────────────
cat(paste0("\n", strrep("=", 60)), "\n")
cat("MULTI-SCALE VISUALIZATION COMPLETE\n")
cat(strrep("=", 60), "\n")
cat(sprintf("  LSOA:    n=%4d, mean=%.1f%%, SD=%.1f%%\n",
            nrow(lsoa), mean(lsoa$total_coverage, na.rm=TRUE),
            sd(lsoa$total_coverage, na.rm=TRUE)))
cat(sprintf("  MSOA:    n=%4d, mean=%.1f%%, SD=%.1f%%\n",
            nrow(msoa), mean(msoa$total_coverage, na.rm=TRUE),
            sd(msoa$total_coverage, na.rm=TRUE)))
cat(sprintf("  Ward:    n=%4d, mean=%.1f%%, SD=%.1f%%\n",
            nrow(ward), mean(ward$total_coverage, na.rm=TRUE),
            sd(ward$total_coverage, na.rm=TRUE)))
cat(sprintf("  Borough: n=%4d, mean=%.1f%%, SD=%.1f%%\n",
            nrow(bor), mean(bor$total_coverage, na.rm=TRUE),
            sd(bor$total_coverage, na.rm=TRUE)))
cat("\n  Visualizations saved to output/:\n")
cat("    stage1_viz1_multiscale_coverage.png  (combined 2x2)\n")
cat("    stage1_viz1_lsoa_coverage.png        (individual)\n")
cat("    stage1_viz1_msoa_coverage.png        (individual)\n")
cat("    stage1_viz1_ward_coverage.png        (individual)\n")
cat("    stage1_viz1_borough_coverage.png     (individual)\n")
