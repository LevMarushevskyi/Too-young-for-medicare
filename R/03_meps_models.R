# 03_meps_models.R -- survey-weighted logistic models of medical-bill worry (BUILD_GUIDE 5.5)
# Output: data/processed/meps_model_or.csv
#         data/processed/meps_team_reproduction.csv
# Model A: worry_bills ~ treated + age10 + inc3          (reproduces team model)
# Model B: worry_bills ~ treated + age_grp + inc3        (headline: aOR Under 65 vs 65+)
# Model C: Model B + ins_private (any private vs none; the 3-level collapse is not
#          estimable because only 1 cohort member is uninsured all year)
# All use CSAQW24F, design declared on the full file, then subset to breast & CSAQW24F>0
# & complete cases. Primary lonely.psu = "adjust" + survey.adjust.domain.lonely = TRUE
# (conservative, as in team script). Sensitivity rows: "average" (domain adj. still on)
# and "adjust_nodomain" (domain adj. off, the AHRQ/NHIS-style setting).
source("R/00_utils.R")
dir.create("data/processed", showWarnings = FALSE, recursive = TRUE)
d <- readRDS("data/interim/meps_full.rds")

d$age_grp <- factor(d$age_grp, levels = c("65+", "Under 65"))
d$inc3 <- factor(d$inc3, levels = c("High (400%+)", "Middle (200-399%)", "Lower (<200% FPL)"))
d$ins_private <- factor(d$ins_private, levels = c("Any private", "No private coverage"))

term_labels <- c(
  treated = "Currently treated vs not",
  age10 = "Age (per 10 years)",
  "age_grpUnder 65" = "Under 65 vs 65+",
  "inc3Middle (200-399%)" = "Middle vs high income",
  "inc3Lower (<200% FPL)" = "Lower vs high income",
  "ins_privateNo private coverage" = "No private coverage vs any private")

forms <- list(
  A = worry_bills ~ treated + age10 + inc3,
  B = worry_bills ~ treated + age_grp + inc3,
  C = worry_bills ~ treated + age_grp + inc3 + ins_private)

fit_or <- function(design, f, model, method) {
  # method "adjust_nodomain": lonely.psu = "adjust" with survey.adjust.domain.lonely = FALSE
  # (tests the conservative domain adjustment set globally in 00_utils.R)
  old <- if (method == "adjust_nodomain") options(survey.lonely.psu = "adjust", survey.adjust.domain.lonely = FALSE)
         else options(survey.lonely.psu = method)
  on.exit(options(old))
  vars <- all.vars(f)
  ok <- Reduce(`&`, lapply(vars, function(v) !is.na(design$variables[[v]])))
  ds <- subset(design, ok)
  m <- svyglm(f, design = ds, family = quasibinomial())
  ci <- confint(m, method = "Wald", ddf = m$df.residual)
  ct <- coef(summary(m))
  out <- data.frame(model = model, term = names(coef(m)), or = exp(coef(m)),
    ci_lo = exp(ci[, 1]), ci_hi = exp(ci[, 2]), p_value = ct[, ncol(ct)],
    n = nrow(ds$variables), n_events = sum(ds$variables$worry_bills == 1),
    lonely_psu_method = method, row.names = NULL)
  out <- out[out$term != "(Intercept)", ]
  out$term_label <- unname(term_labels[out$term])
  out
}

full <- meps_design(d, "CSAQW24F")
csaq <- subset(full, breast & CSAQW24F > 0)
res <- do.call(rbind, c(
  lapply(names(forms), function(k) fit_or(csaq, forms[[k]], paste("Model", k), "adjust")),
  lapply(names(forms), function(k) fit_or(csaq, forms[[k]], paste("Model", k), "average")),
  lapply(names(forms), function(k) fit_or(csaq, forms[[k]], paste("Model", k), "adjust_nodomain"))))
res <- res[, c("model", "term", "term_label", "or", "ci_lo", "ci_hi", "p_value", "n", "n_events", "lonely_psu_method")]
res[, c("or", "ci_lo", "ci_hi")] <- round(res[, c("or", "ci_lo", "ci_hi")], 3)
res$p_value <- signif(res$p_value, 3)
write.csv(res, "data/processed/meps_model_or.csv", row.names = FALSE)
print(res, row.names = FALSE)

# ---------------- Team reproduction ----------------
# team_inputs/original_analysis.R: design on all 19,140 records with CSAQW24F, subset
# CSAQW24F > 0 & CABREAST == 1, lonely.psu = "adjust" with survey.adjust.domain.lonely = TRUE,
# model worry ~ treatment_group + age10 + income_group (POVCAT 1-3 / 4 / 5, ref High),
# Wald CI with ddf = df.residual. Worry-by-income and Rx delay (CDLPRS42, the CSAQ
# cancer-related item) by worry use the same design and svyciprop(method = "logit").
team_way <- function(wt) {
  old <- options(survey.lonely.psu = "adjust", survey.adjust.domain.lonely = TRUE); on.exit(options(old))
  dd <- d; dd$cab <- dd$CABREAST %in% 1
  des <- subset(meps_design(dd, wt), cab & dd[[wt]] > 0)
  mA <- fit_or(des, forms$A, "team", "adjust")
  inc <- prop_by(des, "worry_bills", "inc3")
  des2 <- update(des, wg = ifelse(is.na(worry_bills), NA, ifelse(worry_bills == 1, "Bill worry", "No bill worry")))
  rx <- prop_by(des2, "csaq_delay_rx", "wg")
  rxp <- prop_by(update(des2, prx = ifelse(ACCELI42 %in% 1, delay_or_forgo_rx_cost, NA)), "prx", "wg")
  g <- function(x, lab) round(x[x$group == lab, "pct"], 1)
  a <- function(term) with(mA[mA$term == term, ], sprintf("%.2f (%.2f-%.2f)", or, ci_lo, ci_hi))
  data.frame(
    quantity = c("aOR age per 10 years", "aOR lower vs high income", "aOR currently treated",
                 "Model n", "Worry %: lower income", "Worry %: middle income", "Worry %: high income",
                 "CSAQ Rx delay (CDLPRS42) %: bill worry", "CSAQ Rx delay (CDLPRS42) %: no bill worry",
                 "Rx delay/forgo for cost (DLAYPM42|AFRDPM42) %: bill worry",
                 "Rx delay/forgo for cost (DLAYPM42|AFRDPM42) %: no bill worry"),
    our_value = c(a("age10"), a("inc3Lower (<200% FPL)"), a("treated"), as.character(mA$n[1]),
                  g(inc, "Lower (<200% FPL)"), g(inc, "Middle (200-399%)"), g(inc, "High (400%+)"),
                  g(rx, "Bill worry"), g(rx, "No bill worry"), g(rxp, "Bill worry"), g(rxp, "No bill worry")),
    weight_used = wt)
}
team_vals <- c("0.54 (0.36-0.81)", "2.98 (1.15-7.73)", "1.50 (0.54-4.20)", "260",
               "38.4", "18.2", "24.2", "11.8", "1.9", "11.8", "1.9")
rep <- rbind(cbind(team_way("CSAQW24F"), team_value = team_vals),
             cbind(team_way("PERWT24F"), team_value = team_vals))
rep$note <- ifelse(rep$weight_used == "CSAQW24F",
  "Team method re-run: CSAQW24F, full-file design, CABREAST==1, adjust + adjust.domain.lonely=TRUE",
  "Same quantity with PERWT24F (wrong weight for CSAQ items), for comparison only")
rep$note[grepl("DLAYPM42", rep$quantity)] <- paste(rep$note[grepl("DLAYPM42", rep$quantity)],
  "; team figure used CDLPRS42, this row is the BUILD_GUIDE behavior_link item (ACCELI42==1)")
rep <- rep[, c("quantity", "team_value", "our_value", "weight_used", "note")]
write.csv(rep, "data/processed/meps_team_reproduction.csv", row.names = FALSE)
print(rep[, 1:4], row.names = FALSE)
