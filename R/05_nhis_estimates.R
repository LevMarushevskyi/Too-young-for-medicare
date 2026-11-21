# 05_nhis_estimates.R -- NHIS 2021-2024 pooled age curve + under-65 vs 65+ gap
# Design declared on ALL sample adults, then subset to the breast cohort.
# Small-cell rule (BUILD_GUIDE 5.4): suppress if unweighted denominator n < 30 or
# numerator count < 5 (pct/ci blank, suppressed = TRUE); flag if n < 60 or RSE > 30%.
# CIs: svyciprop(method = "logit"). age_mid = weighted mean age within the band.

suppressPackageStartupMessages(library(survey))
options(survey.lonely.psu = "adjust")
root <- Sys.getenv("PROJECT_ROOT", unset = ".")

all_adults <- readRDS(file.path(root, "data/interim/nhis_all_adults.rds"))
brks <- c(18, 40, 45, 50, 55, 60, 65, 70, 75, 80, Inf)
labs <- c("18-39", "40-44", "45-49", "50-54", "55-59", "60-64", "65-69", "70-74",
          "75-79", "80-85")
all_adults$age_band <- cut(all_adults$AGEP_A, brks, labs, right = FALSE)
all_adults$age_grp <- ifelse(all_adults$under65 == 1, "Under 65", "65+")

des <- svydesign(ids = ~PPSU, strata = ~PSTRAT, weights = ~wt_pool, nest = TRUE,
                 data = all_adults)
des_b <- subset(des, in_cohort)

measures <- c(prob_pay_bills = "Problems paying medical bills, past 12 months",
              worry_bills_very_or_somewhat = "Very or somewhat worried about paying medical bills if sick",
              cost_delay_any = "Delayed or did not get medical care due to cost, past 12 months")

est_one <- function(d, m) {
  dd <- subset(d, !is.na(get(m)))
  n <- nrow(dd$variables); k <- sum(dd$variables[[m]] == 1)
  out <- list(pct = NA, ci_lo = NA, ci_hi = NA, n = n, k = k, sup = TRUE, flag = TRUE)
  if (n < 30 || k < 5) return(out)
  f <- as.formula(paste0("~I(", m, " == 1)"))
  p <- svyciprop(f, dd, method = "logit")
  ci <- as.numeric(confint(p)); se <- as.numeric(SE(p)); pv <- as.numeric(p)
  rse <- if (pv > 0) se / pv else Inf
  list(pct = round(100 * pv, 1), ci_lo = round(100 * ci[1], 1),
       ci_hi = round(100 * ci[2], 1), n = n, k = k, sup = FALSE,
       flag = (n < 60) || (rse > 0.30))
}

rows <- list()
for (m in names(measures)) for (b in labs) {
  d <- subset(des_b, age_band == b)
  e <- est_one(d, m)
  mid <- if (nrow(d$variables) > 0) round(as.numeric(svymean(~AGEP_A, d)), 1) else NA
  rows[[length(rows) + 1]] <- data.frame(
    source = "NHIS 2021-2024", measure = m, measure_label = measures[[m]],
    age_band = b, age_mid = mid, pct = e$pct, ci_lo = e$ci_lo, ci_hi = e$ci_hi,
    n_unweighted = e$n, suppressed = e$sup, flagged = e$flag)
}
curve <- do.call(rbind, rows)
write.csv(curve, file.path(root, "data/processed/nhis_age_curve.csv"), row.names = FALSE,
          na = "")

gap <- list()
for (m in names(measures)) for (g in c("Under 65", "65+")) {
  e <- est_one(subset(des_b, age_grp == g), m)
  gap[[length(gap) + 1]] <- data.frame(
    measure = m, measure_label = measures[[m]], group = g, pct = e$pct,
    ci_lo = e$ci_lo, ci_hi = e$ci_hi, n_unweighted = e$n, suppressed = e$sup,
    flagged = e$flag)
}
gap <- do.call(rbind, gap)
write.csv(gap, file.path(root, "data/processed/nhis_age_gap.csv"), row.names = FALSE,
          na = "")
print(curve[, c("measure", "age_band", "pct", "ci_lo", "ci_hi", "n_unweighted",
                "suppressed", "flagged")])
print(gap)
