# 04_nhis_clean.R -- pool NHIS Sample Adult 2021-2024, build breast cancer cohort
#
# Pooling follows docs/reference/nhis2024_srvydesc.pdf, "Scenario 1: Concatenating
# 2024 and 2023 (pooling) ... to increase sample size" (p. 48-49): keep the same
# variables from each year, rbind the files, include SRVY_YR, divide the sample
# weight by the number of years pooled (here WTFA_A / 4), and use the standard
# variance estimation variables PSTRAT and PPSU unchanged ("Analysts interested in
# pooling three or more years of data can follow the same steps"). 2021-2024 share
# the 2016+ NHIS sample design, so PSTRAT/PPSU are used as-is with nest = TRUE.
#
# The design is declared on ALL sample adults (05 script); the breast cohort is a
# subset taken AFTER svydesign(). This script writes:
#   data/interim/nhis_all_adults.rds   (all adults, needed columns; for 05)
#   data/interim/nhis_breast.csv       (cohort, person-level; for python/)
#   data/processed/nhis_cohort_counts.csv
# Feature definitions live in python/harmonize.py (single source of truth); this
# script passes raw columns (reserved codes -> NA) plus the three outcomes.

suppressPackageStartupMessages(library(survey))
options(survey.lonely.psu = "adjust")

root <- Sys.getenv("PROJECT_ROOT", unset = ".")
raw_dir <- file.path(root, "data/raw/nhis")
dir.create(file.path(root, "data/interim"), showWarnings = FALSE, recursive = TRUE)
dir.create(file.path(root, "data/processed"), showWarnings = FALSE, recursive = TRUE)

wanted <- c("SRVY_YR", "WTFA_A", "PSTRAT", "PPSU", "CANEV_A", "BREASCAN_A",
            "BREASAGETC_A", "AGEP_A", "SEX_A", "HISPALLP_A", "REGION", "URBRRL",
            "POVRATTC_A", "RATCAT_A", "PRIVATE_A", "MEDICAID_A", "MEDICARE_A",
            "NOTCOV_A", "PRHDHP1_A", "EMPWRKLSW1_A", "PAYBLL12M_A", "PAYNOBLLNW_A",
            "PAYWORRY_A", "MEDDL12M_A", "MEDNG12M_A", "RXSK12M_A", "RXDL12M_A",
            "RXDG12M_A", "PHSTAT_A", "MARSTAT_A", "EDUCP_A")

years <- 2021:2024
read_year <- function(y) {
  yy <- substr(y, 3, 4)
  zf <- file.path(raw_dir, sprintf("adult%scsv.zip", yy))
  con <- unz(zf, sprintf("adult%s.csv", yy))
  hdr <- toupper(scan(unz(zf, sprintf("adult%s.csv", yy)), what = "", sep = ",",
                      nlines = 1, quiet = TRUE))
  keep <- ifelse(hdr %in% wanted, NA, "NULL")   # NA = read, "NULL" = skip
  d <- read.csv(con, colClasses = keep, header = TRUE)
  names(d) <- toupper(names(d))
  message(sprintf("NHIS %d: %d sample adults; missing vars: %s", y, nrow(d),
                  paste(setdiff(wanted, names(d)), collapse = ", ")))
  d
}
lst <- lapply(years, read_year)
common <- Reduce(intersect, lapply(lst, names))
dropped <- setdiff(wanted, common)
if (length(dropped)) message("Dropped (not present in all 4 years): ",
                             paste(dropped, collapse = ", "))
all_adults <- do.call(rbind, lapply(lst, function(d) d[, common]))
rm(lst)

# --- reserved codes -> NA (checked against the 2024 codebook entries) ---------
na_codes <- function(x, codes) { x[x %in% codes] <- NA; x }
one_digit_789 <- c("CANEV_A", "BREASCAN_A", "SEX_A", "PRIVATE_A", "MEDICAID_A",
                   "MEDICARE_A", "NOTCOV_A", "PRHDHP1_A", "EMPWRKLSW1_A",
                   "PAYBLL12M_A", "PAYNOBLLNW_A", "PAYWORRY_A", "MEDDL12M_A",
                   "MEDNG12M_A", "RXSK12M_A", "RXDL12M_A", "RXDG12M_A", "PHSTAT_A")
for (v in intersect(one_digit_789, names(all_adults)))
  all_adults[[v]] <- na_codes(all_adults[[v]], c(7, 8, 9))
for (v in intersect(c("AGEP_A", "BREASAGETC_A", "EDUCP_A", "HISPALLP_A", "RATCAT_A"),
                    names(all_adults)))
  all_adults[[v]] <- na_codes(all_adults[[v]], c(97, 98, 99))
# MARSTAT_A: 7 = never married, 8 = living with partner are REAL codes; 9 = unknown
all_adults$MARSTAT_A <- na_codes(all_adults$MARSTAT_A, 9)
# REGION 1-4 has no reserved codes; POVRATTC_A is continuous 0-11 (top-coded 11).

# --- outcomes ----------------------------------------------------------------
yn <- function(x) ifelse(x == 1, 1L, ifelse(x == 2, 0L, NA_integer_))
all_adults$prob_pay_bills <- yn(all_adults$PAYBLL12M_A)
# PAYWORRY_A: 1 very worried, 2 somewhat worried, 3 not at all worried
all_adults$worry_bills_very_or_somewhat <-
  ifelse(all_adults$PAYWORRY_A %in% c(1, 2), 1L,
         ifelse(all_adults$PAYWORRY_A == 3, 0L, NA_integer_))
d1 <- all_adults$MEDDL12M_A; d2 <- all_adults$MEDNG12M_A
all_adults$cost_delay_any <- ifelse((!is.na(d1) & d1 == 1) | (!is.na(d2) & d2 == 1), 1L,
                                    ifelse(!is.na(d1) & !is.na(d2) & d1 == 2 & d2 == 2,
                                           0L, NA_integer_))
all_adults$wt_pool <- all_adults$WTFA_A / length(years)
all_adults$in_cohort <- !is.na(all_adults$BREASCAN_A) & all_adults$BREASCAN_A == 1 &
  !is.na(all_adults$AGEP_A) & all_adults$AGEP_A >= 18
all_adults$under65 <- as.integer(all_adults$AGEP_A < 65)
all_adults$years_since_dx <- pmax(all_adults$AGEP_A - all_adults$BREASAGETC_A, 0)

saveRDS(all_adults, file.path(root, "data/interim/nhis_all_adults.rds"))

# Design declared on the full file, then subset (used here only for the weighted
# cohort size; estimates are in 05_nhis_estimates.R).
des <- svydesign(ids = ~PPSU, strata = ~PSTRAT, weights = ~wt_pool, nest = TRUE,
                 data = all_adults)
des_b <- subset(des, in_cohort)

cohort <- all_adults[all_adults$in_cohort, ]
write.csv(cohort, file.path(root, "data/interim/nhis_breast.csv"), row.names = FALSE,
          na = "")

cnt <- function(d, label) data.frame(
  year = label,
  n_sample_adults = nrow(d),
  n_breast_18plus = sum(d$in_cohort),
  n_breast_female = sum(d$in_cohort & d$SEX_A %in% 2),
  n_breast_male = sum(d$in_cohort & d$SEX_A %in% 1),
  n_breast_under65 = sum(d$in_cohort & d$under65 %in% 1),
  n_breast_65plus = sum(d$in_cohort & d$under65 %in% 0),
  n_breast_outcome_nonmissing = sum(d$in_cohort & !is.na(d$prob_pay_bills)),
  n_breast_outcome_yes = sum(d$in_cohort & d$prob_pay_bills %in% 1)
)
counts <- do.call(rbind, c(lapply(years, function(y)
  cnt(all_adults[all_adults$SRVY_YR == y, ], as.character(y))),
  list(cnt(all_adults, "2021-2024 pooled"))))
counts$weighted_pop_pooled <- NA
counts$weighted_pop_pooled[nrow(counts)] <- round(sum(weights(des_b)))
counts$vars_dropped <- paste(dropped, collapse = ";")
print(counts)
# Small-cell rule (5.4): never publish a count of 1-4. Mask it as "<5" and blank its
# complement in the same row (female = 18plus - male would reveal it).
# If any single year has 1-4 men, blank the per-year sex split for every year: the
# pooled row minus the other years would otherwise reveal the small cell by subtraction.
yr_rows <- counts$year != "2021-2024 pooled"
if (any(yr_rows & counts$n_breast_male > 0 & counts$n_breast_male < 5)) {
  counts$n_breast_male[yr_rows] <- NA
  counts$n_breast_female[yr_rows] <- NA
}
write.csv(counts, file.path(root, "data/processed/nhis_cohort_counts.csv"),
          row.names = FALSE, na = "")
print(counts)
message(sprintf("Pooled NHIS breast cancer cohort (18+): n = %d", nrow(cohort)))
