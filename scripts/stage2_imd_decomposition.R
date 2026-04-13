#!/usr/bin/env Rscript
# =============================================================================
# Stage 2: IMD Sub-Domain Decomposition (Beydoun-Inspired)
#
# Research Question: Which dimensions of deprivation are most strongly
#   associated with food purchasing behaviour in London?
#
# Methods:
#   - Model A (OLS): PC1/PC2 ~ IMD total score
#   - Model B (OLS): PC1/PC2 ~ 7 IMD sub-domains
#   - LASSO: Variable selection on 7 sub-domains
#
# Visualizations:
#   1. OLS coefficient comparison (Model A vs Model B) for PC1 & PC2
#   2. LASSO regularization path (coefficient shrinkage)
#   3. Variable importance ranking (OLS vs LASSO)
#
# Requires: output/imd_subdomains.csv, output/pca_scores.csv
#   (from python/00_stage0_preprocess.py)
# =============================================================================

cat(strrep("=", 60), "\n")
cat("Stage 2: IMD Sub-Domain Decomposition\n")
cat(strrep("=", 60), "\n\n")

# ── 0. Install missing packages ────────────────────────────────────────
required_packages <- c("glmnet", "ggplot2", "dplyr", "tidyr", "broom",
                       "patchwork", "scales", "forcats")

for (pkg in required_packages) {
  if (!requireNamespace(pkg, quietly = TRUE)) {
    cat("Installing package:", pkg, "\n")
    install.packages(pkg, repos = "https://cloud.r-project.org", quiet = TRUE)
  }
}

suppressPackageStartupMessages({
  library(glmnet)
  library(ggplot2)
  library(dplyr)
  library(tidyr)
  library(broom)
  library(patchwork)
  library(scales)
  library(forcats)
})

# ── 1. Load data ──────────────────────────────────────────────────────
cat("Loading data ...\n")

imd <- read.csv("output/imd_subdomains.csv")
pca <- read.csv("output/pca_scores.csv")

# Merge
df <- pca %>%
  inner_join(imd, by = "lsoa_code") %>%
  filter(!is.na(PC1), !is.na(PC2))

# Define domain column names (may vary slightly)
domain_names <- c("income", "employment", "education", "health",
                  "crime", "barriers", "living_environment")

# Check which domains exist
available_domains <- domain_names[domain_names %in% names(df)]
cat(sprintf("  %d LSOAs with complete data\n", nrow(df)))
cat(sprintf("  Available domains: %s\n",
            paste(available_domains, collapse = ", ")))

# Standardize all variables for fair comparison
for (var in c("PC1", "PC2", "imd_score", available_domains)) {
  if (var %in% names(df)) {
    df[[paste0(var, "_z")]] <- scale(df[[var]])
  }
}

# ── 2. Model A: OLS with IMD total ────────────────────────────────────
cat("\n--- Model A: OLS with IMD Total Score ---\n")

model_a_pc1 <- lm(PC1_z ~ imd_score_z, data = df)
model_a_pc2 <- lm(PC2_z ~ imd_score_z, data = df)

cat(sprintf("  PC1 ~ IMD total: R² = %.4f, adj R² = %.4f\n",
            summary(model_a_pc1)$r.squared, summary(model_a_pc1)$adj.r.squared))
cat(sprintf("  PC2 ~ IMD total: R² = %.4f, adj R² = %.4f\n",
            summary(model_a_pc2)$r.squared, summary(model_a_pc2)$adj.r.squared))

tidy_a_pc1 <- tidy(model_a_pc1)
tidy_a_pc2 <- tidy(model_a_pc2)

# ── 3. Model B: OLS with 7 IMD sub-domains ───────────────────────────
cat("\n--- Model B: OLS with IMD Sub-Domains ---\n")

# Build formula
formula_b <- as.formula(
  paste("PC1_z ~", paste(available_domains, collapse = " + "))
)
model_b_pc1 <- lm(formula_b, data = df)

formula_b2 <- as.formula(
  paste("PC2_z ~", paste(available_domains, collapse = " + "))
)
model_b_pc2 <- lm(formula_b2, data = df)

cat(sprintf("  PC1 ~ sub-domains: R² = %.4f, adj R² = %.4f\n",
            summary(model_b_pc1)$r.squared, summary(model_b_pc1)$adj.r.squared))
cat(sprintf("  PC2 ~ sub-domains: R² = %.4f, adj R² = %.4f\n",
            summary(model_b_pc2)$r.squared, summary(model_b_pc2)$adj.r.squared))

tidy_b_pc1 <- tidy(model_b_pc1)
tidy_b_pc2 <- tidy(model_b_pc2)

# ── 4. Model comparison ──────────────────────────────────────────────
cat("\n--- Model Comparison ---\n")
comparison <- data.frame(
  Model = c("A: IMD total", "B: Sub-domains"),
  PC1_R2 = c(
    summary(model_a_pc1)$r.squared,
    summary(model_b_pc1)$r.squared
  ),
  PC2_R2 = c(
    summary(model_a_pc2)$r.squared,
    summary(model_b_pc2)$r.squared
  ),
  PC1_AdjR2 = c(
    summary(model_a_pc1)$adj.r.squared,
    summary(model_b_pc1)$adj.r.squared
  ),
  PC2_AdjR2 = c(
    summary(model_a_pc2)$adj.r.squared,
    summary(model_b_pc2)$adj.r.squared
  )
)
print(comparison, row.names = FALSE)

improvement <- (summary(model_b_pc1)$adj.r.squared - summary(model_a_pc1)$adj.r.squared)
cat(sprintf("\n  Sub-domain decomposition improves PC1 adj. R² by %.4f\n", improvement))

# ── 5. LASSO Variable Selection ───────────────────────────────────────
cat("\n--- LASSO Variable Selection ---\n")

# Prepare feature matrix (X) and target vectors (y)
X_mat <- as.matrix(df[, available_domains])
y_pc1 <- df$PC1_z
y_pc2 <- df$PC2_z

# 5-fold CV for PC1
set.seed(42)
cv_pc1 <- cv.glmnet(X_mat, y_pc1, alpha = 1, nfolds = 5)
best_lambda_pc1 <- cv_pc1$lambda.min

lasso_pc1 <- glmnet(X_mat, y_pc1, alpha = 1, lambda = best_lambda_pc1)
lasso_coefs_pc1 <- as.numeric(coef(lasso_pc1))[-1]
names(lasso_coefs_pc1) <- available_domains

cat(sprintf("  PC1 LASSO (lambda.min = %.6f):\n", best_lambda_pc1))
for (i in seq_along(lasso_coefs_pc1)) {
  sig <- ifelse(abs(lasso_coefs_pc1[i]) > 1e-10, " *", "   (zero)")
  cat(sprintf("    %s: %.6f%s\n", names(lasso_coefs_pc1)[i],
              lasso_coefs_pc1[i], sig))
}

# 5-fold CV for PC2
set.seed(42)
cv_pc2 <- cv.glmnet(X_mat, y_pc2, alpha = 1, nfolds = 5)
best_lambda_pc2 <- cv_pc2$lambda.min

lasso_pc2 <- glmnet(X_mat, y_pc2, alpha = 1, lambda = best_lambda_pc2)
lasso_coefs_pc2 <- as.numeric(coef(lasso_pc2))[-1]
names(lasso_coefs_pc2) <- available_domains

cat(sprintf("\n  PC2 LASSO (lambda.min = %.6f):\n", best_lambda_pc2))
for (i in seq_along(lasso_coefs_pc2)) {
  sig <- ifelse(abs(lasso_coefs_pc2[i]) > 1e-10, " *", "   (zero)")
  cat(sprintf("    %s: %.6f%s\n", names(lasso_coefs_pc2)[i],
              lasso_coefs_pc2[i], sig))
}

# ── 6. VISUALIZATIONS ─────────────────────────────────────────────────
cat("\n--- Creating Visualizations ---\n")

# Pretty domain labels
domain_labels <- c(
  income = "Income",
  employment = "Employment",
  education = "Education",
  health = "Health",
  crime = "Crime",
  barriers = "Barriers to\nHousing",
  living_environment = "Living\nEnvironment"
)

# ── Visualization 1: OLS Coefficient Comparison ────────────────────────
cat("  Creating Viz 1: OLS coefficient comparison ...\n")

# Prepare data for plotting
coef_plot_data <- bind_rows(
  tidy_b_pc1 %>%
    filter(term != "(Intercept)") %>%
    mutate(DV = "PC1 (Convenience)", Model = "B: Sub-domains"),
  tidy_b_pc2 %>%
    filter(term != "(Intercept)") %>%
    mutate(DV = "PC2 (Variety)", Model = "B: Sub-domains"),
  tidy_a_pc1 %>%
    filter(term != "(Intercept)") %>%
    mutate(term = "IMD Total", DV = "PC1 (Convenience)", Model = "A: IMD Total"),
  tidy_a_pc2 %>%
    filter(term != "(Intercept)") %>%
    mutate(term = "IMD Total", DV = "PC2 (Variety)", Model = "A: IMD Total")
) %>%
  mutate(
    sig = case_when(
      p.value < 0.001 ~ "***",
      p.value < 0.01  ~ "**",
      p.value < 0.05  ~ "*",
      TRUE            ~ ""
    ),
    term = factor(term, levels = rev(c("IMD Total", available_domains)))
  )

p1 <- ggplot(coef_plot_data, aes(x = estimate, y = term, fill = Model)) +
  geom_vline(xintercept = 0, colour = "grey50", linewidth = 0.4) +
  geom_errorbarh(
    aes(xmin = estimate - 1.96 * std.error,
        xmax = estimate + 1.96 * std.error),
    height = 0.2, linewidth = 0.3, position = position_dodge(0.6)
  ) +
  geom_point(shape = 21, size = 2.5, position = position_dodge(0.6)) +
  geom_text(
    aes(label = sig),
    position = position_dodge(0.6),
    vjust = -0.5, hjust = -0.3, size = 3, fontface = "bold"
  ) +
  facet_wrap(~ DV, scales = "free_x") +
  scale_fill_manual(values = c("A: IMD Total" = "#7570B3",
                                "B: Sub-domains" = "#D95F02"),
                    name = NULL) +
  labs(
    title = "OLS Regression Coefficients: IMD vs. Food Purchasing Patterns",
    subtitle = sprintf("Model A (IMD total): R²=%.3f / Model B (7 sub-domains): R²=%.3f",
                       summary(model_a_pc1)$r.squared,
                       summary(model_b_pc1)$r.squared),
    x = "Standardised Coefficient (± 95% CI)",
    y = NULL,
    caption = "DV = z-scored PC1/PC2 | *** p<0.001, ** p<0.01, * p<0.05"
  ) +
  theme_minimal(base_size = 10) +
  theme(
    legend.position = "bottom",
    strip.text = element_text(face = "bold"),
    plot.title = element_text(face = "bold", size = 12),
    plot.subtitle = element_text(size = 9, color = "grey40"),
    plot.caption = element_text(size = 7, color = "grey50"),
    panel.grid.minor = element_blank()
  )

ggsave("output/stage2_viz1_ols_coefficients.png", p1,
       width = 12, height = 6, dpi = 200, bg = "white")
cat("    Saved: output/stage2_viz1_ols_coefficients.png\n")

# ── Visualization 2: LASSO Regularization Path ────────────────────────
cat("  Creating Viz 2: LASSO regularization path ...\n")

# Get full LASSO paths
lasso_path_pc1 <- glmnet(X_mat, y_pc1, alpha = 1)
lasso_path_pc2 <- glmnet(X_mat, y_pc2, alpha = 1)

# Extract path data (coef matrix: rows=features+intercept, cols=lambda steps)
coef_pc1 <- as.matrix(coef(lasso_path_pc1))[-1, , drop = FALSE]  # 7 x nlambda
coef_pc2 <- as.matrix(coef(lasso_path_pc2))[-1, , drop = FALSE]

path_df <- bind_rows(
  data.frame(
    lambda = lasso_path_pc1$lambda,
    t(coef_pc1),
    DV = "PC1 (Convenience)",
    check.names = FALSE
  ),
  data.frame(
    lambda = lasso_path_pc2$lambda,
    t(coef_pc2),
    DV = "PC2 (Variety)",
    check.names = FALSE
  )
) %>%
  pivot_longer(
    cols = -c(lambda, DV),
    names_to = "domain",
    values_to = "coefficient"
  ) %>%
  mutate(domain = recode(domain, !!!domain_labels))

p2 <- ggplot(path_df, aes(x = log(lambda), y = coefficient, colour = domain)) +
  geom_line(linewidth = 0.8) +
  geom_hline(yintercept = 0, colour = "grey50", linewidth = 0.3) +
  # Mark optimal lambda
  geom_vline(xintercept = log(best_lambda_pc1), linetype = "dashed",
             colour = "grey60", linewidth = 0.5) +
  facet_wrap(~ DV) +
  scale_colour_brewer(palette = "Set2", name = "Domain") +
  labs(
    title = "LASSO Regularization Path",
    subtitle = sprintf("Optimal λ (PC1) = %.4f (dashed line)", best_lambda_pc1),
    x = "log(λ)",
    y = "Standardised Coefficient",
    caption = "5-fold cross-validation | Domains with coef = 0 are eliminated"
  ) +
  theme_minimal(base_size = 10) +
  theme(
    legend.position = "bottom",
    legend.text = element_text(size = 7),
    strip.text = element_text(face = "bold"),
    plot.title = element_text(face = "bold", size = 12),
    plot.subtitle = element_text(size = 9, color = "grey40"),
    plot.caption = element_text(size = 7, color = "grey50"),
    panel.grid.minor = element_blank()
  )

ggsave("output/stage2_viz2_lasso_path.png", p2,
       width = 11, height = 6, dpi = 200, bg = "white")
cat("    Saved: output/stage2_viz2_lasso_path.png\n")

# ── Visualization 3: Variable Importance Ranking ───────────────────────
cat("  Creating Viz 3: Variable importance ranking ...\n")

# OLS importance: absolute coefficient magnitude (Model B) with sign
ols_importance <- bind_rows(
  tidy_b_pc1 %>%
    filter(term != "(Intercept)") %>%
    mutate(Method = "OLS (PC1)", importance = abs(estimate),
           sign = ifelse(estimate > 0, "+", "-")) %>%
    select(term, Method, importance, sign),
  tidy_b_pc2 %>%
    filter(term != "(Intercept)") %>%
    mutate(Method = "OLS (PC2)", importance = abs(estimate),
           sign = ifelse(estimate > 0, "+", "-")) %>%
    select(term, Method, importance, sign)
)

# LASSO importance: absolute coefficient (non-zero only) with sign
lasso_importance <- bind_rows(
  data.frame(
    term = names(lasso_coefs_pc1),
    Method = "LASSO (PC1)",
    importance = abs(lasso_coefs_pc1),
    sign = ifelse(lasso_coefs_pc1 > 0, "+", "-")
  ),
  data.frame(
    term = names(lasso_coefs_pc2),
    Method = "LASSO (PC2)",
    importance = abs(lasso_coefs_pc2),
    sign = ifelse(lasso_coefs_pc2 > 0, "+", "-")
  )
)

# Combine
importance_df <- bind_rows(ols_importance, lasso_importance) %>%
  mutate(
    term = recode(term, !!!domain_labels),
    term = fct_reorder(term, importance, .fun = mean, .desc = TRUE),
    Method = factor(Method, levels = c("OLS (PC1)", "LASSO (PC1)",
                                        "OLS (PC2)", "LASSO (PC2)"))
  )

p3 <- ggplot(importance_df, aes(x = importance, y = term, fill = Method)) +
  geom_col(position = position_dodge(0.7), width = 0.6, alpha = 0.85) +
  geom_text(
    aes(label = sign),
    position = position_dodge(0.7),
    vjust = -0.5, hjust = 0.5,
    size = 2.5, fontface = "bold", colour = "grey30"
  ) +
  facet_wrap(~ Method, ncol = 2, scales = "free_x") +
  scale_fill_manual(values = c(
    "OLS (PC1)" = "#7570B3", "OLS (PC2)" = "#E7298A",
    "LASSO (PC1)" = "#1B9E77", "LASSO (PC2)" = "#D95F02"
  )) +
  guides(fill = "none") +
  labs(
    title = "Variable Importance Ranking: OLS vs. LASSO",
    subtitle = "Bar height = |standardised coefficient| | '+'/'-' = direction of association with DV",
    x = "|Standardised Coefficient|",
    y = NULL,
    caption = "LASSO: coefficients set to zero are eliminated by regularisation"
  ) +
  theme_minimal(base_size = 10) +
  theme(
    strip.text = element_text(face = "bold", size = 9),
    plot.title = element_text(face = "bold", size = 12),
    plot.subtitle = element_text(size = 9, color = "grey40"),
    plot.caption = element_text(size = 7, color = "grey50"),
    panel.grid.minor = element_blank(),
    panel.grid.major.y = element_blank()
  )

ggsave("output/stage2_viz3_variable_importance.png", p3,
       width = 11, height = 7, dpi = 200, bg = "white")
cat("    Saved: output/stage2_viz3_variable_importance.png\n")

# ── Summary ───────────────────────────────────────────────────────────
cat(paste0("\n", strrep("=", 60)), "\n")
cat("STAGE 2 COMPLETE\n")
cat(strrep("=", 60), "\n")

cat("\n  Key findings:\n")
cat(sprintf("    Model A (IMD total → PC1): R² = %.4f\n",
            summary(model_a_pc1)$r.squared))
cat(sprintf("    Model B (sub-domains → PC1): R² = %.4f\n",
            summary(model_b_pc1)$r.squared))

# Strongest predictor from LASSO
strongest_pc1 <- names(which.max(abs(lasso_coefs_pc1)))
cat(sprintf("    LASSO strongest predictor for PC1: %s (|β| = %.4f)\n",
            strongest_pc1, max(abs(lasso_coefs_pc1))))

surviving_pc1 <- names(lasso_coefs_pc1)[abs(lasso_coefs_pc1) > 1e-10]
cat(sprintf("    LASSO surviving domains for PC1: %s\n",
            paste(surviving_pc1, collapse = ", ")))

cat("\n  Visualizations saved to output/:\n")
cat("    1. stage2_viz1_ols_coefficients.png\n")
cat("    2. stage2_viz2_lasso_path.png\n")
cat("    3. stage2_viz3_variable_importance.png\n")
