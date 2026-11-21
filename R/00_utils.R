# 00_utils.R -- shared helpers for the MEPS / NHIS R pipeline
# Sourced by R/01-05. Run all scripts from the repo root.

suppressPackageStartupMessages({
  library(survey)
  library(haven)
})

options(survey.lonely.psu = "adjust", survey.adjust.domain.lonely = TRUE)  # as in team script

MEPS_RESERVED <- c(-1, -7, -8, -9, -15)

# Reserved MEPS codes -> NA (returns plain numeric, labels dropped)
recode_reserved <- function(x, reserved = MEPS_RESERVED) {
  x <- as.numeric(zap_labels(x))
  x[x %in% reserved] <- NA
  x
}

# 1 = YES -> 1, 2 = NO -> 0, anything else -> NA
yes_no <- function(x) {
  x <- recode_reserved(x)
  ifelse(x == 1, 1, ifelse(x == 2, 0, NA_real_))
}

# "any of" with NA only when every input is NA
any_of_na <- function(...) {
  m <- cbind(...)
  out <- as.numeric(rowSums(m == 1, na.rm = TRUE) > 0)
  out[rowSums(!is.na(m)) == 0] <- NA
  out
}

# Small-cell rule (BUILD_GUIDE 5.4).
# Suppress: unweighted denominator < 30, or numerator < 5. We also suppress when
# the complement (n - events) < 5, because a printed % with its n would reveal a
# cell of fewer than 5 respondents ("never show a cell < 5").
# Flag: n < 60 or RSE > 30%.
small_cell <- function(n, events, rse) {
  suppressed <- n < 30 | events < 5 | (n - events) < 5
  flagged <- !suppressed & (n < 60 | (!is.na(rse) & rse > 0.30))
  list(suppressed = suppressed, flagged = flagged)
}

# Weighted proportion of a 0/1 variable in a (sub)design, with logit CI.
# Returns pct and CIs on the 0-100 scale; rse = SE(p)/p.
prop_ci <- function(design, var) {
  f <- reformulate(var)
  y <- design$variables[[var]]
  n <- sum(!is.na(y)); ev <- sum(y == 1, na.rm = TRUE)
  if (n == 0) return(data.frame(pct = NA, ci_lo = NA, ci_hi = NA, n_unweighted = 0,
                                n_events = 0, rse = NA))
  m <- svymean(f, design, na.rm = TRUE)
  p <- as.numeric(coef(m)); se <- as.numeric(SE(m))
  lo <- hi <- NA_real_
  if (ev > 0 && ev < n) {
    ci <- tryCatch(confint(svyciprop(f, design, method = "logit", df = degf(design))),
                   error = function(e) c(NA, NA))
    lo <- ci[1]; hi <- ci[2]
  }
  data.frame(pct = 100 * p, ci_lo = 100 * lo, ci_hi = 100 * hi,
             n_unweighted = n, n_events = ev, rse = ifelse(p > 0, se / p, NA))
}

# Proportions of `var` within each level of `group`, small-cell rule applied.
prop_by <- function(design, var, group) {
  d0 <- subset(design, !is.na(design$variables[[var]]) & !is.na(design$variables[[group]]))
  lv <- design$variables[[group]]
  lv <- if (is.factor(lv)) levels(droplevels(d0$variables[[group]])) else sort(unique(na.omit(lv)))
  out <- do.call(rbind, lapply(lv, function(g) {
    dg <- d0[as.character(d0$variables[[group]]) == g, ]
    r <- prop_ci(dg, var); r$group <- g; r
  }))
  sc <- small_cell(out$n_unweighted, out$n_events, out$rse)
  out$suppressed <- sc$suppressed; out$flagged <- sc$flagged
  out[out$suppressed, c("pct", "ci_lo", "ci_hi", "rse")] <- NA
  out
}

# Full-file design for one weight, then domain subset (never filter before svydesign)
meps_design <- function(full, wt) {
  svydesign(ids = ~VARPSU, strata = ~VARSTR, weights = reformulate(wt),
            data = full, nest = TRUE)
}
