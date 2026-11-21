# 02_meps_estimates.R -- survey-weighted MEPS 2024 estimates (BUILD_GUIDE 5.3)
# Input : data/interim/meps_full.rds (from 01_meps_clean.R)
# Output: data/processed/meps_estimates.csv, meps_age_gap_tests.csv,
#         meps_unexpected_expense.csv, meps_cohort_counts.csv
#
# chart_id values in meps_estimates.csv:
#   overall        every strain measure, whole breast cohort (group = "All")
#   age_gap        every strain measure x age_grp (hero chart)
#   income         worry_bills, any_fw_strain, prob_pay_bills, high_oop_burden x inc3
#   insurance_age  worry_bills, prob_pay_bills x ins_cat (age-specific insurance groups)
#   treatment      team's four CSAQ measures x treated (now weighted)
#   behavior_link  delay_or_forgo_rx_cost, delay_or_forgo_care_cost (and the team's CSAQ
#                  csaq_delay_rx) x worry_bills
# Weights: CSAQ items -> CSAQW24F, ESAQ items -> ESAQWT24F, else PERWT24F. When the
# grouping variable is a CSAQ item (treated, worry_bills) the CSAQ weight is used.
source("R/00_utils.R")
dir.create("data/processed", showWarnings = FALSE, recursive = TRUE)
d <- readRDS("data/interim/meps_full.rds")

d$age_grp <- factor(d$age_grp, levels = c("Under 65", "65+"))
d$inc3 <- factor(d$inc3, levels = c("Lower (<200% FPL)", "Middle (200-399%)", "High (400%+)"))
d$treated_grp <- factor(ifelse(is.na(d$treated), NA,
  ifelse(d$treated == 1, "Currently treated", "Not currently treated")),
  levels = c("Currently treated", "Not currently treated"))
d$worry_grp <- factor(ifelse(is.na(d$worry_bills), NA,
  ifelse(d$worry_bills == 1, "Bill worry", "No bill worry")),
  levels = c("Bill worry", "No bill worry"))
d$all <- "All"

measures <- data.frame(rbind(
  c("worry_bills",              "Worried about paying medical bills",            "CSAQW24F", "CSAQ"),
  c("fam_stability_worry",      "Worried about family financial stability",      "CSAQW24F", "CSAQ"),
  c("borrowed_debt",            "Borrowed money or went into debt (cancer)",     "CSAQW24F", "CSAQ"),
  c("any_csaq_strain",          "Any cancer-related financial strain",           "CSAQW24F", "CSAQ"),
  c("debt_collector",           "Contacted by a debt collector",                 "PERWT24F", "FW"),
  c("missed_payment",           "Missed a loan or credit card payment",          "PERWT24F", "FW"),
  c("late_rent",                "Late or unable to pay rent/mortgage",           "PERWT24F", "FW"),
  c("late_util",                "Unable to pay utility bills",                   "PERWT24F", "FW"),
  c("any_fw_strain",            "Any household financial hardship",              "PERWT24F", "FW"),
  c("prob_pay_bills",           "Family had problems paying medical bills",      "PERWT24F", "PROB"),
  c("delay_or_forgo_care_cost", "Delayed or went without care due to cost",      "PERWT24F", "ACC"),
  c("delay_or_forgo_rx_cost",   "Delayed or went without prescriptions due to cost", "PERWT24F", "ACC"),
  c("sacrificed_basics",        "Sacrificed basic spending (ESAQ)",              "ESAQWT24F", "ESAQ"),
  c("high_oop_burden",          "Out-of-pocket costs >= 10% of family income",   "PERWT24F", "OOP"),
  c("unable_cover_bills",       "Unable to cover medical bills (cancer)",        "CSAQW24F", "CSAQ"),
  c("csaq_sacrificed",          "Sacrificed basic spending (cancer, CSAQ)",      "CSAQW24F", "CSAQ"),
  c("csaq_delay_rx",            "Delayed or forgone prescriptions (cancer, CSAQ)", "CSAQW24F", "CSAQ")
), stringsAsFactors = FALSE)
names(measures) <- c("measure", "label", "wt", "inst")
strain14 <- measures$measure[1:14]
univ_note <- c(CSAQ = "Adults with breast cancer, CSAQ respondents",
               FW   = "Adults with breast cancer (family food/financial items)",
               PROB = "Adults with breast cancer (family-level item)",
               ACC  = "Adults with breast cancer eligible for access supplement (ACCELI42==1)",
               ESAQ = "Adults with breast cancer, ESAQ respondents",
               OOP  = "Adults with breast cancer, family income > 0")

designs <- list()
for (w in c("PERWT24F", "CSAQW24F", "ESAQWT24F")) {
  full <- meps_design(d, w)
  designs[[w]] <- subset(full, breast & full$variables[[w]] > 0)
}

est_rows <- function(chart_id, measure, group_var, wt = NULL) {
  m <- measures[measures$measure == measure, ]
  if (is.null(wt)) wt <- m$wt
  r <- prop_by(designs[[wt]], measure, group_var)
  data.frame(source = "MEPS 2024", chart_id = chart_id, measure = measure,
    measure_label = m$label, group_var = group_var, group = r$group,
    pct = round(r$pct, 1), ci_lo = round(r$ci_lo, 1), ci_hi = round(r$ci_hi, 1),
    n_unweighted = r$n_unweighted, n_events = r$n_events, rse = round(r$rse, 3),
    suppressed = r$suppressed, flagged = r$flagged, weight_var = wt,
    universe_note = if (wt == "CSAQW24F") univ_note[["CSAQ"]] else univ_note[[m$inst]])
}

est <- list()
for (m in measures$measure) est[[length(est) + 1]] <- est_rows("overall", m, "all")
for (m in strain14) est[[length(est) + 1]] <- est_rows("age_gap", m, "age_grp")
for (m in c("worry_bills", "any_fw_strain", "prob_pay_bills", "high_oop_burden"))
  est[[length(est) + 1]] <- est_rows("income", m, "inc3")
for (m in c("worry_bills", "prob_pay_bills"))
  est[[length(est) + 1]] <- est_rows("insurance_age", m, "ins_cat")
for (m in c("worry_bills", "borrowed_debt", "unable_cover_bills", "csaq_sacrificed"))
  est[[length(est) + 1]] <- est_rows("treatment", m, "treated_grp")
for (m in c("delay_or_forgo_rx_cost", "delay_or_forgo_care_cost", "csaq_delay_rx"))
  est[[length(est) + 1]] <- est_rows("behavior_link", m, "worry_grp", wt = "CSAQW24F")
est <- do.call(rbind, est)
# Cells that would reveal small counts are blanked (suppressed rows keep only n)
# If any group of a chart/measure is suppressed, blank n_events for its sibling groups too,
# otherwise overall events minus the shown siblings' events recovers the suppressed count.
key <- paste(est$chart_id, est$measure)
est$n_events[key %in% key[est$suppressed]] <- NA
est$n_events[est$suppressed] <- NA
# A denominator of 1-4 is itself a small cell (5.4: never show cells <5)
est$n_unweighted[est$suppressed & est$n_unweighted < 5] <- NA
write.csv(est, "data/processed/meps_estimates.csv", row.names = FALSE, na = "")

# ---- Age gap tests: Rao-Scott chi-square + Under65 - 65+ difference (pp) ----
tests <- do.call(rbind, lapply(strain14, function(m) {
  wt <- measures$wt[measures$measure == m]
  ds <- subset(designs[[wt]], !is.na(designs[[wt]]$variables[[m]]) & !is.na(age_grp))
  ds <- update(ds, yf = factor(ds$variables[[m]], levels = c(0, 1)))
  p <- tryCatch(svychisq(~yf + age_grp, ds)$p.value, error = function(e) NA)
  by <- svyby(reformulate(m), ~age_grp, ds, svymean, na.rm = TRUE, covmat = TRUE)
  ct <- svycontrast(by, c("Under 65" = 1, "65+" = -1))
  est_d <- as.numeric(coef(ct)); se <- as.numeric(SE(ct)); df <- degf(ds)
  sup <- any(est$suppressed[est$chart_id == "age_gap" & est$measure == m])
  out <- data.frame(measure = m, diff_pp = round(100 * est_d, 1),
    diff_lo = round(100 * (est_d - qt(.975, df) * se), 1),
    diff_hi = round(100 * (est_d + qt(.975, df) * se), 1),
    p_value = signif(as.numeric(p), 3),
    test = sprintf("p_value: Rao-Scott F (svychisq); diff/CI and p_wald: Under 65 - 65+ via svycontrast, t df=%d; weight %s", df, wt),
    p_wald = signif(2 * pt(-abs(est_d / se), df), 3))
  if (sup) { out[, c("diff_pp", "diff_lo", "diff_hi", "p_wald")] <- NA
             out$test <- paste(out$test, "; diff blanked: a group cell is suppressed") }
  out
}))
write.csv(tests, "data/processed/meps_age_gap_tests.csv", row.names = FALSE, na = "")

# ---- Confidence covering an unexpected expense (FWUNEXP42) x inc3 (+ All) ----
lab4 <- c("1" = "Not at all confident", "2" = "Not too confident",
          "3" = "Somewhat confident", "4" = "Very confident")
dp <- designs[["PERWT24F"]]
ue <- list()
for (gv in c("all", "inc3", "age_grp")) for (k in 1:4) {
  nm <- paste0("unexp_", k)
  dp$variables[[nm]] <- ifelse(is.na(dp$variables$fw_unexp), NA, as.numeric(dp$variables$fw_unexp == k))
  r <- prop_by(dp, nm, gv)
  ue[[length(ue) + 1]] <- data.frame(group = r$group, response_level = k,
    response_label = lab4[[as.character(k)]], pct = round(r$pct, 1),
    ci_lo = round(r$ci_lo, 1), ci_hi = round(r$ci_hi, 1),
    n_unweighted = r$n_unweighted, suppressed = r$suppressed, n_ev = r$n_events)
}
ue <- do.call(rbind, ue)
# Complementary suppression: the 4 levels sum to 100%, so a lone suppressed level (or a
# set of suppressed levels whose combined count is < 5) can be recovered by subtraction.
# Suppress the next-smallest level until the suppressed set holds >= 5 persons.
for (g in unique(ue$group)) {
  i <- which(ue$group == g)
  repeat {
    s <- ue$suppressed[i]
    if (!any(s) || all(s) || sum(ue$n_ev[i][s]) >= 5) break
    cand <- i[!s]; j <- cand[which.min(ue$n_ev[cand])]
    ue$suppressed[j] <- TRUE
  }
}
ue[ue$suppressed, c("pct", "ci_lo", "ci_hi")] <- NA
ue$n_ev <- NULL
ue <- ue[order(match(ue$group, c("All", levels(d$inc3), levels(d$age_grp))), ue$response_level), ]
write.csv(ue, "data/processed/meps_unexpected_expense.csv", row.names = FALSE, na = "")

# ---- Cohort counts for every universe used ----
cc <- function(name, wt, cond) {
  b <- d[d$breast & d[[wt]] > 0 & cond(d), ]
  data.frame(cohort = name, n_unweighted = nrow(b), weighted_n = round(sum(b[[wt]])), weight_var = wt)
}
T <- function(x) rep(TRUE, nrow(x))
counts <- rbind(
  data.frame(cohort = "MEPS 2024 full file (design base)", n_unweighted = nrow(d),
             weighted_n = round(sum(d$PERWT24F)), weight_var = "PERWT24F"),
  cc("Breast cancer adults, PERWT24F>0", "PERWT24F", T),
  cc("Breast cancer adults under 65, PERWT24F>0", "PERWT24F", function(x) x$age_grp %in% "Under 65"),
  cc("Breast cancer adults 65+, PERWT24F>0", "PERWT24F", function(x) x$age_grp %in% "65+"),
  cc("Breast cancer adults, CSAQ respondents (CSAQW24F>0)", "CSAQW24F", T),
  cc("Breast cancer adults under 65, CSAQW24F>0", "CSAQW24F", function(x) x$age_grp %in% "Under 65"),
  cc("Breast cancer adults 65+, CSAQW24F>0", "CSAQW24F", function(x) x$age_grp %in% "65+"),
  cc("CSAQ respondents with valid worry_bills", "CSAQW24F", function(x) !is.na(x$worry_bills)),
  cc("Breast cancer adults, ESAQ respondents (ESAQWT24F>0)", "ESAQWT24F", T),
  cc("Breast cancer adults under 65, ESAQWT24F>0", "ESAQWT24F", function(x) x$age_grp %in% "Under 65"),
  cc("Breast cancer adults 65+, ESAQWT24F>0", "ESAQWT24F", function(x) x$age_grp %in% "65+"),
  cc("Access supplement eligible (ACCELI42==1), PERWT24F>0", "PERWT24F", function(x) x$ACCELI42 %in% 1),
  cc("Family income > 0 (OOP burden), PERWT24F>0", "PERWT24F", function(x) !is.na(x$oop_share))
)
write.csv(counts, "data/processed/meps_cohort_counts.csv", row.names = FALSE)

cat("Wrote", nrow(est), "estimate rows;", sum(est$suppressed), "suppressed;", sum(est$flagged), "flagged\n")
print(est[est$chart_id == "age_gap", c("measure", "group", "pct", "ci_lo", "ci_hi", "n_unweighted", "suppressed", "flagged", "weight_var")], row.names = FALSE)
print(tests[, 1:5], row.names = FALSE)
