# 01_meps_clean.R -- MEPS HC-256 (2024 Full Year Consolidated): recodes + cohort flag
# Input : data/raw/meps/h256dta.zip (unzipped to data/interim/h256.dta if needed)
# Output: data/interim/meps_full.rds   (ALL persons, raw + derived vars; used for design)
#         data/interim/meps_full.csv   (same, CSV)
#         data/interim/meps_breast.csv (breast cohort only, for python/evaluate_external.py)
#         data/interim/meps_clean_log.txt
source("R/00_utils.R")

dir.create("data/interim", showWarnings = FALSE, recursive = TRUE)
dta <- "data/interim/h256.dta"
if (!file.exists(dta)) unzip("data/raw/meps/h256dta.zip", exdir = "data/interim")
if (!file.exists(dta)) {
  f <- list.files("data/interim", pattern = "\\.dta$", full.names = TRUE, ignore.case = TRUE)
  dta <- f[grepl("h256", basename(f), ignore.case = TRUE)][1]
}

keep <- c("DUPERSID", "VARSTR", "VARPSU", "PERWT24F", "CSAQW24F", "ESAQWT24F",
  "AGE24X", "SEX", "RACETHX", "REGION24", "CANCERDX", "CABREAST", "CSAQELIG",
  "POVCAT24", "POVLEV24", "FAMINC24", "TOTSLF24", "TOTEXP24",
  "INSCOV24", "PRVEV24", "MCDEV24", "MCREV24", "UNINS24",
  "CTRTMT42", "CFNPMT42", "CFNSTB42", "CFNDBT42", "CFNUNB42", "CFNSPD42", "CDLPRS42",
  "FWDEBT42", "FWCRED42", "FWRENT42", "FWUTIL42", "FWUNEXP42", "PROBPY42",
  "ACCELI42", "DLAYCA42", "AFRDCA42", "DLAYPM42", "AFRDPM42", "EQSBAS53",
  "EMPST53", "RTHLTH53", "MARRY24X", "HIDEG")
raw <- read_dta(dta, col_select = tidyselect::any_of(keep))
missing_vars <- setdiff(keep, names(raw))
d <- as.data.frame(zap_labels(raw))   # raw columns kept as numeric codes

log <- c(sprintf("MEPS HC-256 rows: %d", nrow(d)),
         sprintf("Missing requested vars: %s", paste(missing_vars, collapse = ", ")))

age <- recode_reserved(d$AGE24X)
d$breast  <- !is.na(d$CABREAST) & d$CABREAST == 1 & !is.na(age) & age >= 18
d$age_grp <- ifelse(is.na(age), NA, ifelse(age < 65, "Under 65", "65+"))
d$age10   <- age / 10

pc <- recode_reserved(d$POVCAT24)
d$inc3 <- ifelse(pc %in% 1:3, "Lower (<200% FPL)",
          ifelse(pc == 4, "Middle (200-399%)", ifelse(pc == 5, "High (400%+)", NA)))

prv <- recode_reserved(d$PRVEV24); mcd <- recode_reserved(d$MCDEV24)
mcr <- recode_reserved(d$MCREV24); uni <- recode_reserved(d$UNINS24)
d$ins_cat <- with(d, ifelse(is.na(age), NA,
  ifelse(age < 65,
    ifelse(prv %in% 1, "U65: Any private",
    ifelse(uni %in% 1, "U65: Uninsured",
    ifelse(mcd %in% 1 | mcr %in% 1, "U65: Public only", NA))),
    ifelse(mcr %in% 1 & prv %in% 1, "65+: Medicare + private",
    ifelse(mcr %in% 1 & mcd %in% 1, "65+: Medicare + Medicaid",
    ifelse(mcr %in% 1, "65+: Medicare only",
    ifelse(prv %in% 1, "65+: Private, no Medicare", "65+: Other/none")))))))
# Collapsed for Model C: any private vs no private (uninsured n is 1 in the cohort)
d$ins_private <- ifelse(is.na(prv), NA, ifelse(prv == 1, "Any private", "No private coverage"))

d$treated             <- yes_no(d$CTRTMT42)
d$worry_bills         <- yes_no(d$CFNPMT42)
d$fam_stability_worry <- yes_no(d$CFNSTB42)
d$borrowed_debt       <- yes_no(d$CFNDBT42)
d$any_csaq_strain     <- any_of_na(d$worry_bills, d$fam_stability_worry, d$borrowed_debt)
d$unable_cover_bills  <- yes_no(d$CFNUNB42)   # team measure
d$csaq_sacrificed     <- yes_no(d$CFNSPD42)   # team measure
d$csaq_delay_rx       <- yes_no(d$CDLPRS42)   # team measure (cancer-related Rx delay)
d$debt_collector      <- yes_no(d$FWDEBT42)
d$missed_payment      <- yes_no(d$FWCRED42)
d$late_rent           <- yes_no(d$FWRENT42)
d$late_util           <- yes_no(d$FWUTIL42)
d$any_fw_strain       <- any_of_na(d$debt_collector, d$missed_payment, d$late_rent, d$late_util)
d$fw_unexp            <- recode_reserved(d$FWUNEXP42)  # 1 not at all ... 4 very confident
d$prob_pay_bills      <- yes_no(d$PROBPY42)
acc <- recode_reserved(d$ACCELI42) %in% 1
d$delay_or_forgo_care_cost <- ifelse(acc, any_of_na(yes_no(d$DLAYCA42), yes_no(d$AFRDCA42)), NA)
d$delay_or_forgo_rx_cost   <- ifelse(acc, any_of_na(yes_no(d$DLAYPM42), yes_no(d$AFRDPM42)), NA)
d$sacrificed_basics   <- yes_no(d$EQSBAS53)
fi <- recode_reserved(d$FAMINC24); oop <- recode_reserved(d$TOTSLF24)
d$oop_share       <- ifelse(!is.na(fi) & fi > 0, oop / fi, NA)
d$high_oop_burden <- ifelse(is.na(d$oop_share), NA, as.numeric(d$oop_share >= 0.10))

stopifnot(!anyNA(d$VARSTR), !anyNA(d$VARPSU), !anyDuplicated(d$DUPERSID))

b <- d[d$breast, ]
nab <- d$CABREAST %in% 1 & is.na(age)
log <- c(log,
  sprintf("CABREAST==1 total: %d; of these AGE24X reserved/NA (excluded): %d (CSAQW24F>0 %d, PERWT24F>0 %d)",
          sum(d$CABREAST %in% 1), sum(nab), sum(d$CSAQW24F[nab] > 0), sum(d$PERWT24F[nab] > 0)),
  sprintf("Breast cohort (CABREAST==1 & AGE24X>=18): %d (female %d; under 65 %d)",
          nrow(b), sum(b$SEX == 2), sum(b$age_grp == "Under 65")),
  sprintf("CSAQW24F>0: %d; ESAQWT24F>0: %d; PERWT24F>0: %d",
          sum(b$CSAQW24F > 0), sum(b$ESAQWT24F > 0), sum(b$PERWT24F > 0)))

# Team-extract discrepancy: rows flagged breast_c50_current==1 but CANCERDX==2 or CABREAST==2
tf <- "team_inputs/breast_analysis.csv"
if (file.exists(tf)) {
  t <- read.csv(tf)
  disc <- with(t, breast_c50_current == 1 & (CANCERDX == 2 | CABREAST == 2))
  log <- c(log,
    sprintf("Team extract rows: %d; breast_c50_current==1: %d; CABREAST==1: %d",
            nrow(t), sum(t$breast_c50_current == 1, na.rm = TRUE), sum(t$CABREAST == 1, na.rm = TRUE)),
    sprintf("Team rows with breast_c50_current==1 but CANCERDX==2 or CABREAST==2: %d (excluded; cohort uses CABREAST)",
            sum(disc, na.rm = TRUE)))
}

saveRDS(d, "data/interim/meps_full.rds")
write.csv(d, "data/interim/meps_full.csv", row.names = FALSE, na = "")
write.csv(b, "data/interim/meps_breast.csv", row.names = FALSE, na = "")
writeLines(log, "data/interim/meps_clean_log.txt")
cat(log, sep = "\n")
