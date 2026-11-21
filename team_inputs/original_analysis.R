# ============================================================
# Breast Cancer Analysis
# Dataset: meps_data/h256.dta
# ============================================================


# ------------------------------------------------------------
# Step 1: Define the variables and import the data
# ------------------------------------------------------------

bc_needed <- c(
  "DUPERSID",
  "AGE24X",
  "SEX",
  "RACETHX",
  "REGION24",
  "POVCAT24",
  "INSCOV24",
  "CABREAST",
  "CSAQELIG",
  "CTRTMT42",
  "CFNDBT42",
  "CFNUNB42",
  "CFNPMT42",
  "CFNSPD42",
  "CDLPRS42",
  "CDLTRT42",
  "CDLFUP42",
  "PROBPY42",
  "DLAYPM42",
  "TOTSLF24",
  "PERWT24F",
  "CSAQW24F",
  "VARSTR",
  "VARPSU"
)

# Confirm the number of selected variables
length(bc_needed)

# Import the selected variables
bc_data <- haven::read_dta(
  "meps_data/h256.dta",
  col_select = tidyselect::all_of(bc_needed)
)

# Standardize column names
names(bc_data) <- toupper(names(bc_data))

# Confirm the dataset dimensions
dim(bc_data)


# ------------------------------------------------------------
# Step 2: Inspect the breast-cancer diagnosis variable
# ------------------------------------------------------------

# Variable description
attr(bc_data$CABREAST, "label")

# Response codes and their labels
attr(bc_data$CABREAST, "labels")

# Counts for each stored code, including missing values
table(bc_data$CABREAST, useNA = "ifany")


# ------------------------------------------------------------
# Step 3: Create the breast-cancer subset
# ------------------------------------------------------------

# Keep records coded 1 (YES) for breast cancer diagnosis
bc_breast <- bc_data[
  which(bc_data$CABREAST == 1),
]

# Confirm the subset dimensions
dim(bc_breast)

# Confirm all selected records have CABREAST = 1
table(bc_breast$CABREAST, useNA = "ifany")


# ------------------------------------------------------------
# Step 4: Inspect questionnaire eligibility and treatment
# ------------------------------------------------------------

for (v in c("CSAQELIG", "CTRTMT42")) {
  cat("\n--------------------------------\n")
  cat("Variable:", v, "\n")
  
  cat("\nDescription:\n")
  print(attr(bc_breast[[v]], "label"))
  
  cat("\nResponse codes and labels:\n")
  print(attr(bc_breast[[v]], "labels"))
  
  cat("\nCounts in the breast-cancer subset:\n")
  print(table(bc_breast[[v]], useNA = "ifany"))
}

# ------------------------------------------------------------
# Step 5: Compare CSAQ eligibility with current cancer treatment
# ------------------------------------------------------------

with(
  bc_breast,
  table(
    CSAQELIG,
    CTRTMT42,
    useNA = "ifany"
  )
)

# ------------------------------------------------------------
# Step 6: Prepare the first relationship for inspection
# Current cancer treatment versus medical-bill worry
# ------------------------------------------------------------

# Create a separate subset of respondents with CSAQ data
# Keep bc_breast unchanged
bc_csaq <- bc_breast[
  which(bc_breast$CSAQELIG == 1),
]

# Confirm the subset size
nrow(bc_csaq)

# Inspect the medical-bill worry variable
attr(bc_csaq$CFNPMT42, "label")

attr(bc_csaq$CFNPMT42, "labels")

table(
  bc_csaq$CFNPMT42,
  useNA = "ifany"
)

# Inspect worry responses within each treatment category
with(
  bc_csaq,
  table(
    Treatment = CTRTMT42,
    Medical_bill_worry = CFNPMT42,
    useNA = "ifany"
  )
)

# ------------------------------------------------------------
# Step 7: Medical-bill worry by current cancer treatment
# Unweighted exploratory analysis
# ------------------------------------------------------------

# Keep valid YES/NO responses for this comparison only
bc_worry_treatment <- bc_csaq[
  which(
    bc_csaq$CTRTMT42 %in% c(1, 2) &
      bc_csaq$CFNPMT42 %in% c(1, 2)
  ),
]

# Create explicitly labeled categories
bc_worry_treatment$treatment_group <- factor(
  bc_worry_treatment$CTRTMT42,
  levels = c(1, 2),
  labels = c("Currently treated", "Not currently treated")
)

bc_worry_treatment$bill_worry <- factor(
  bc_worry_treatment$CFNPMT42,
  levels = c(1, 2),
  labels = c("Yes", "No")
)

# Counts: rows are treatment groups; columns are worry responses
worry_counts <- with(
  bc_worry_treatment,
  table(treatment_group, bill_worry)
)

# Summarize the percentage reporting worry in each group
worry_summary <- data.frame(
  Treatment = rownames(worry_counts),
  Worried = as.integer(worry_counts[, "Yes"]),
  Total = as.integer(rowSums(worry_counts)),
  row.names = NULL
)

worry_summary$Percent_worried <- (
  100 * worry_summary$Worried / worry_summary$Total
)

print(worry_summary, row.names = FALSE)

# Draw the graph
bar_positions <- barplot(
  height = worry_summary$Percent_worried,
  names.arg = c("Currently\ntreated", "Not currently\ntreated"),
  col = c("#0072B2", "#999999"),
  ylim = c(0, 100),
  ylab = "Respondents reporting medical-bill worry (%)",
  main = "Medical-bill worry by current cancer treatment",
  sub = "Breast-cancer diagnosis subset; unweighted, valid responses only",
  border = NA,
  las = 1,
  cex.names = 0.9,
  cex.sub = 0.8
)

text(
  x = bar_positions,
  y = worry_summary$Percent_worried + 5,
  labels = sprintf(
    "%.1f%%\n(%d/%d)",
    worry_summary$Percent_worried,
    worry_summary$Worried,
    worry_summary$Total
  ),
  cex = 0.9
)

# ------------------------------------------------------------
# Step 8: Inspect borrowing/debt by current cancer treatment
# ------------------------------------------------------------

# Confirm the description and response labels
attr(bc_csaq$CFNDBT42, "label")

attr(bc_csaq$CFNDBT42, "labels")

# Count all responses in the CSAQ subset
table(
  bc_csaq$CFNDBT42,
  useNA = "ifany"
)

# Compare debt responses across treatment categories
with(
  bc_csaq,
  table(
    Treatment = CTRTMT42,
    Borrowing_or_debt = CFNDBT42,
    useNA = "ifany"
  )
)

# ------------------------------------------------------------
# Step 9: Borrowing/debt by current cancer treatment
# Unweighted exploratory analysis
# ------------------------------------------------------------

# Keep valid YES/NO responses for this comparison only
bc_debt_treatment <- bc_csaq[
  which(
    bc_csaq$CTRTMT42 %in% c(1, 2) &
      bc_csaq$CFNDBT42 %in% c(1, 2)
  ),
]

# Create labeled categories
bc_debt_treatment$treatment_group <- factor(
  bc_debt_treatment$CTRTMT42,
  levels = c(1, 2),
  labels = c("Currently treated", "Not currently treated")
)

bc_debt_treatment$borrowing_debt <- factor(
  bc_debt_treatment$CFNDBT42,
  levels = c(1, 2),
  labels = c("Yes", "No")
)

# Count responses within each treatment group
debt_counts <- with(
  bc_debt_treatment,
  table(treatment_group, borrowing_debt)
)

# Calculate group-specific percentages
debt_summary <- data.frame(
  Treatment = rownames(debt_counts),
  Reported_debt = as.integer(debt_counts[, "Yes"]),
  Total = as.integer(rowSums(debt_counts)),
  row.names = NULL
)

debt_summary$Percent_reporting_debt <- (
  100 * debt_summary$Reported_debt / debt_summary$Total
)

print(debt_summary, row.names = FALSE)

# Plot using the same 0–100% scale as the worry graph
bar_positions <- barplot(
  height = debt_summary$Percent_reporting_debt,
  names.arg = c("Currently\ntreated", "Not currently\ntreated"),
  col = c("#0072B2", "#999999"),
  ylim = c(0, 100),
  ylab = "Respondents reporting borrowing or debt (%)",
  main = "Borrowing or debt by current cancer treatment",
  sub = "Breast-cancer diagnosis subset; unweighted, valid responses only",
  border = NA,
  las = 1,
  cex.names = 0.9,
  cex.sub = 0.8
)

text(
  x = bar_positions,
  y = debt_summary$Percent_reporting_debt + 5,
  labels = sprintf(
    "%.1f%%\n(%d/%d)",
    debt_summary$Percent_reporting_debt,
    debt_summary$Reported_debt,
    debt_summary$Total
  ),
  cex = 0.9
)

# ------------------------------------------------------------
# Step 10: Inspect inability to cover medical bills
# ------------------------------------------------------------

# Variable description
print(attr(bc_csaq$CFNUNB42, "label"))

# Response codes and labels
print(attr(bc_csaq$CFNUNB42, "labels"))

# Overall response counts
print(
  table(
    bc_csaq$CFNUNB42,
    useNA = "ifany"
  )
)

# Responses by current cancer-treatment status
print(
  with(
    bc_csaq,
    table(
      Treatment = CTRTMT42,
      Unable_to_cover_bills = CFNUNB42,
      useNA = "ifany"
    )
  )
)


# ------------------------------------------------------------
# Step 11: Inability to cover medical bills by treatment status
# Unweighted exploratory analysis
# ------------------------------------------------------------

# Keep valid YES/NO responses for this comparison only
bc_unable_treatment <- bc_csaq[
  which(
    bc_csaq$CTRTMT42 %in% c(1, 2) &
      bc_csaq$CFNUNB42 %in% c(1, 2)
  ),
]

# Create labeled categories
bc_unable_treatment$treatment_group <- factor(
  bc_unable_treatment$CTRTMT42,
  levels = c(1, 2),
  labels = c("Currently treated", "Not currently treated")
)

# ------------------------------------------------------------
# Step 12: Inspect CFNSPD42 by current cancer-treatment status
# ------------------------------------------------------------

cat("\n--- VARIABLE DESCRIPTION ---\n")
print(attr(bc_csaq$CFNSPD42, "label"))

cat("\n--- RESPONSE CODES AND LABELS ---\n")
print(attr(bc_csaq$CFNSPD42, "labels"))

cat("\n--- RESPONSES BY TREATMENT STATUS ---\n")
print(
  with(
    bc_csaq,
    table(
      Treatment = CTRTMT42,
      CFNSPD42,
      useNA = "ifany"
    )
  )
)

bc_unable_treatment$unable_to_cover_bills <- factor(
  bc_unable_treatment$CFNUNB42,
  levels = c(1, 2),
  labels = c("Yes", "No")
)

# Count responses within each treatment group
unable_counts <- with(
  bc_unable_treatment,
  table(treatment_group, unable_to_cover_bills)
)

# Calculate group-specific percentages
unable_summary <- data.frame(
  Treatment = rownames(unable_counts),
  Reported_unable = as.integer(unable_counts[, "Yes"]),
  Total = as.integer(rowSums(unable_counts)),
  row.names = NULL
)

unable_summary$Percent_unable <- (
  100 * unable_summary$Reported_unable / unable_summary$Total
)

print(unable_summary, row.names = FALSE)

# Plot using the same 0–100% scale as the earlier graphs
bar_positions <- barplot(
  height = unable_summary$Percent_unable,
  names.arg = c("Currently\ntreated", "Not currently\ntreated"),
  col = c("#0072B2", "#999999"),
  ylim = c(0, 100),
  ylab = "Respondents unable to cover medical bills (%)",
  main = "Inability to cover medical bills by cancer treatment",
  sub = "Breast-cancer diagnosis subset; unweighted, valid responses only",
  border = NA,
  las = 1,
  cex.names = 0.9,
  cex.sub = 0.8
)

text(
  x = bar_positions,
  y = unable_summary$Percent_unable + 5,
  labels = sprintf(
    "%.1f%%\n(%d/%d)",
    unable_summary$Percent_unable,
    unable_summary$Reported_unable,
    unable_summary$Total
  ),
  cex = 0.9
)

# ------------------------------------------------------------
# Step 13: Sacrificed basic spending by cancer-treatment status
# Unweighted exploratory analysis
# ------------------------------------------------------------

# Keep valid YES/NO responses for this comparison only
bc_spending_treatment <- bc_csaq[
  which(
    bc_csaq$CTRTMT42 %in% c(1, 2) &
      bc_csaq$CFNSPD42 %in% c(1, 2)
  ),
]

# Create labeled categories
bc_spending_treatment$treatment_group <- factor(
  bc_spending_treatment$CTRTMT42,
  levels = c(1, 2),
  labels = c("Currently treated", "Not currently treated")
)

bc_spending_treatment$sacrificed_basic_spending <- factor(
  bc_spending_treatment$CFNSPD42,
  levels = c(1, 2),
  labels = c("Yes", "No")
)

# Count responses within each treatment group
spending_counts <- with(
  bc_spending_treatment,
  table(treatment_group, sacrificed_basic_spending)
)

# Calculate group-specific percentages
spending_summary <- data.frame(
  Treatment = rownames(spending_counts),
  Reported_sacrifice = as.integer(spending_counts[, "Yes"]),
  Total = as.integer(rowSums(spending_counts)),
  row.names = NULL
)

spending_summary$Percent_sacrificed <- (
  100 * spending_summary$Reported_sacrifice /
    spending_summary$Total
)

print(spending_summary, row.names = FALSE)

# Plot using the same 0–100% scale as the earlier graphs
bar_positions <- barplot(
  height = spending_summary$Percent_sacrificed,
  names.arg = c("Currently\ntreated", "Not currently\ntreated"),
  col = c("#0072B2", "#999999"),
  ylim = c(0, 100),
  ylab = "Respondents reporting sacrificed basic spending (%)",
  main = "Sacrificed basic spending by cancer treatment",
  sub = "Breast-cancer diagnosis subset; unweighted, valid responses only",
  border = NA,
  las = 1,
  cex.names = 0.9,
  cex.sub = 0.8
)

text(
  x = bar_positions,
  y = spending_summary$Percent_sacrificed + 5,
  labels = sprintf(
    "%.1f%%\n(%d/%d)",
    spending_summary$Percent_sacrificed,
    spending_summary$Reported_sacrifice,
    spending_summary$Total
  ),
  cex = 0.9
)


# ------------------------------------------------------------
# Step 14: Survey analysis setup
# ------------------------------------------------------------

# Run once if needed:
# install.packages("survey")

library(survey)

stopifnot(exists("bc_data"))

dir.create("results", showWarnings = FALSE)

# Flag singleton-PSU problems rather than silently applying a fix
options(survey.lonely.psu = "fail")


# ------------------------------------------------------------
# Step 15: Audit and prepare analysis variables
# ------------------------------------------------------------

analysis_vars <- c(
  "CTRTMT42",
  "CFNPMT42", "CFNDBT42", "CFNUNB42", "CFNSPD42",
  "CDLPRS42", "CDLTRT42", "CDLFUP42",
  "AGE24X", "POVCAT24", "INSCOV24", "TOTSLF24"
)

# Save descriptions and value labels for review
capture.output(
  for (v in analysis_vars) {
    cat("\nVARIABLE:", v, "\n")
    print(attr(bc_data[[v]], "label"))
    print(attr(bc_data[[v]], "labels"))
    print(table(bc_data[[v]], useNA = "ifany"))
  },
  file = "results/variable_audit.txt"
)

# Inspect the relationship between eligibility and positive weight
with(
  bc_data,
  print(table(
    CSAQELIG,
    Positive_CSAQ_weight = CSAQW24F > 0,
    useNA = "ifany"
  ))
)

# Keep original imported data unchanged
analysis_data <- as.data.frame(bc_data)

# Convert YES/NO coding to numeric 1/0
yes_no <- function(x) {
  x <- as.numeric(x)
  ifelse(x == 1, 1,
         ifelse(x == 2, 0, NA_real_))
}

variable_map <- c(
  treated = "CTRTMT42",
  worry = "CFNPMT42",
  debt = "CFNDBT42",
  unable = "CFNUNB42",
  sacrifice = "CFNSPD42",
  delay_rx = "CDLPRS42",
  delay_treatment = "CDLTRT42",
  delay_followup = "CDLFUP42"
)

for (new_name in names(variable_map)) {
  analysis_data[[new_name]] <-
    yes_no(analysis_data[[variable_map[[new_name]]]])
}

analysis_data$breast_dx <-
  !is.na(analysis_data$CABREAST) &
  analysis_data$CABREAST == 1

# Preserve valid categorical values and their original labels
clean_factor <- function(x) {
  x[!is.na(x) & x < 0] <- NA
  haven::as_factor(x, levels = "both")
}

analysis_data$income <- clean_factor(analysis_data$POVCAT24)
analysis_data$insurance <- clean_factor(analysis_data$INSCOV24)

analysis_data$age <- ifelse(
  analysis_data$AGE24X >= 0,
  as.numeric(analysis_data$AGE24X),
  NA_real_
)

analysis_data$age10 <- analysis_data$age / 10

analysis_data$oop <- ifelse(
  analysis_data$TOTSLF24 >= 0,
  as.numeric(analysis_data$TOTSLF24),
  NA_real_
)

analysis_data$treatment_group <- factor(
  analysis_data$treated,
  levels = c(0, 1),
  labels = c("Not currently treated", "Currently treated")
)

analysis_data$worry_group <- factor(
  analysis_data$worry,
  levels = c(0, 1),
  labels = c("No bill worry", "Bill worry")
)

analysis_data$unable_group <- factor(
  analysis_data$unable,
  levels = c(0, 1),
  labels = c("No inability reported", "Unable to cover bills")
)

# ------------------------------------------------------------
# Step 16: Corrected survey design
# Preserve the full sample structure before domain restriction
# ------------------------------------------------------------

options(
  survey.lonely.psu = "fail",
  survey.adjust.domain.lonely = FALSE
)

# Verify the full analysis data are available
stopifnot(
  nrow(analysis_data) == nrow(bc_data),
  !anyNA(analysis_data$VARSTR),
  !anyNA(analysis_data$VARPSU),
  !anyNA(analysis_data$CSAQW24F),
  all(analysis_data$CSAQW24F >= 0)
)

# Define the design using ALL imported records.
# Retain zero questionnaire weights; do not replace them with 1.
design_csaq_full <- survey::svydesign(
  ids = ~VARPSU,
  strata = ~VARSTR,
  weights = ~CSAQW24F,
  nest = TRUE,
  data = analysis_data
)

# Restrict the DESIGN, not the underlying data frame
design_csaq <- subset(
  design_csaq_full,
  CSAQW24F > 0
)

design_bc <- subset(
  design_csaq,
  breast_dx
)

# Verify the analysis population
cat(
  "\nPositive-weight breast-cancer records:",
  nrow(design_bc$variables),
  "\nDesign degrees of freedom:",
  survey::degf(design_bc),
  "\n"
)

print(table(
  design_bc$variables$treatment_group,
  useNA = "ifany"
))


# ------------------------------------------------------------
# Step 17: Reusable weighted summaries and plots
# ------------------------------------------------------------

weighted_binary <- function(design, outcome, group) {
  
  group_values <- design$variables[[group]]
  
  groups <- if (is.factor(group_values)) {
    levels(droplevels(group_values))
  } else {
    sort(unique(group_values[!is.na(group_values)]))
  }
  
  results <- lapply(groups, function(g) {
    
    keep <- !is.na(group_values) &
      as.character(group_values) == as.character(g) &
      !is.na(design$variables[[outcome]])
    
    d <- design[keep, ]
    y <- d$variables[[outcome]]
    
    if (length(y) == 0) return(NULL)
    
    # Boundary groups need special handling; don't report
    # a misleading zero-width confidence interval.
    if (length(unique(y)) < 2) {
      estimate <- as.numeric(coef(
        svymean(reformulate(outcome), d)
      ))[1]
      
      lower <- upper <- NA_real_
      note <- "All responses identical; CI not estimated"
      
    } else {
      fit <- svyciprop(
        reformulate(outcome),
        design = d,
        method = "logit",
        df = degf(d)
      )
      
      estimate <- as.numeric(coef(fit))[1]
      ci <- as.numeric(confint(fit))
      
      lower <- ci[1]
      upper <- ci[2]
      note <- ""
    }
    
    data.frame(
      outcome = outcome,
      group = as.character(g),
      n = length(y),
      yes_n = sum(y == 1),
      percent = 100 * estimate,
      lower = 100 * lower,
      upper = 100 * upper,
      note = note
    )
  })
  
  do.call(rbind, results)
}

plot_weighted <- function(tab, title) {
  
  positions <- barplot(
    tab$percent,
    names.arg = tab$group,
    ylim = c(0, 100),
    col = rep(c("#999999", "#0072B2"), length.out = nrow(tab)),
    border = NA,
    ylab = "Weighted percentage reporting outcome",
    main = title,
    sub = "95% confidence intervals; n denotes unweighted valid responses",
    cex.names = 0.75,
    cex.main = 0.9,
    cex.sub = 0.7,
    las = 1
  )
  
  ok <- is.finite(tab$lower) & is.finite(tab$upper)
  
  if (any(ok)) {
    arrows(
      positions[ok], tab$lower[ok],
      positions[ok], tab$upper[ok],
      angle = 90, code = 3, length = 0.05
    )
  }
  
  text(
    positions,
    pmin(ifelse(ok, tab$upper, tab$percent) + 5, 97),
    labels = sprintf("%.1f%%\nn=%d", tab$percent, tab$n),
    cex = 0.75
  )
}

burden_titles <- c(
  worry = "Medical-bill worry",
  debt = "Borrowing or debt",
  unable = "Unable to cover medical bills",
  sacrifice = "Sacrificed basic spending"
)
stopifnot(
  !anyNA(csaq_population$VARSTR),
  !anyNA(csaq_population$VARPSU),
  !anyDuplicated(csaq_population$DUPERSID)
)

design_csaq <- svydesign(
  ids = ~VARPSU,
  strata = ~VARSTR,
  weights = ~CSAQW24F,
  nest = TRUE,
  data = csaq_population
)

design_bc <- subset(design_csaq, breast_dx)

# Inspect design and analysis sample
print(summary(design_csaq))

cat(
  "\nPositive-weight breast-cancer records:",
  nrow(design_bc$variables),
  "\nDesign degrees of freedom:",
  degf(design_bc),
  "\n"
)

print(table(
  design_bc$variables$treatment_group,
  useNA = "ifany"
))

# ------------------------------------------------------------
# Step 18: Weighted treatment comparisons with 95% CIs
# Primary exploratory variance method: adjust
# ------------------------------------------------------------

options(
  survey.lonely.psu = "adjust",
  survey.adjust.domain.lonely = TRUE
)

dir.create("results", showWarnings = FALSE)

# Save the completed worry sensitivity check
write.csv(
  worry_sensitivity,
  "results/worry_variance_sensitivity.csv",
  row.names = FALSE
)

# Calculate all four comparisons
treatment_results <- do.call(
  rbind,
  lapply(names(burden_titles), function(outcome) {
    weighted_binary(
      design_bc,
      outcome,
      "treatment_group"
    )
  })
)

print(treatment_results, row.names = FALSE)

# Save the estimates
write.csv(
  treatment_results,
  "results/weighted_treatment_comparisons.csv",
  row.names = FALSE
)

# Save the four graphs in one PDF
pdf(
  "results/weighted_treatment_comparisons.pdf",
  width = 10,
  height = 8
)

par(
  mfrow = c(2, 2),
  mar = c(5, 4, 4, 1)
)

for (outcome in names(burden_titles)) {
  plot_weighted(
    treatment_results[
      treatment_results$outcome == outcome,
    ],
    paste(
      burden_titles[[outcome]],
      "by treatment status"
    )
  )
}

dev.off()


# ------------------------------------------------------------
# Step 19A: Verify care-delay variables and analysis counts
# ------------------------------------------------------------

# Inspect original descriptions and response labels
for (v in c("CDLPRS42", "CDLTRT42", "CDLFUP42")) {
  
  cat("\n----------------------------------------\n")
  cat("VARIABLE:", v, "\n")
  
  cat("\nDESCRIPTION:\n")
  print(attr(bc_data[[v]], "label"))
  
  cat("\nRESPONSE LABELS:\n")
  print(attr(bc_data[[v]], "labels"))
}

# Inspect unweighted counts within the weighted analysis domain
# Recoded values: 0 = NO, 1 = YES, NA = unavailable

cat("\n----------------------------------------\n")
cat("BILL WORRY versus DELAYED/FORGONE PRESCRIPTIONS\n")

with(
  design_bc$variables,
  print(table(
    Bill_worry = worry,
    Prescription_delay = delay_rx,
    useNA = "ifany"
  ))
)

cat("\n----------------------------------------\n")
cat("UNABLE TO COVER BILLS versus DELAYED/FORGONE TREATMENT\n")

with(
  design_bc$variables,
  print(table(
    Unable_to_cover_bills = unable,
    Treatment_delay = delay_treatment,
    useNA = "ifany"
  ))
)

cat("\n----------------------------------------\n")
cat("UNABLE TO COVER BILLS versus DELAYED/FORGONE FOLLOW-UP\n")

with(
  design_bc$variables,
  print(table(
    Unable_to_cover_bills = unable,
    Followup_delay = delay_followup,
    useNA = "ifany"
  ))
)


# ------------------------------------------------------------
# Step 19B: Follow-up delay by inability to cover medical bills
# ------------------------------------------------------------

# Display the original description
print(attr(bc_data$CDLFUP42, "label"))

# Retain the documented exploratory variance settings
options(
  survey.lonely.psu = "adjust",
  survey.adjust.domain.lonely = TRUE
)

# Calculate weighted percentages and 95% confidence intervals
followup_results <- weighted_binary(
  design = design_bc,
  outcome = "delay_followup",
  group = "unable_group"
)

print(followup_results, row.names = FALSE)

# Save the results
write.csv(
  followup_results,
  "results/followup_delay_by_bill_difficulty.csv",
  row.names = FALSE
)

# ------------------------------------------------------------
# Step 19C: Inspect prescription and treatment-delay comparisons
# ------------------------------------------------------------

# Print descriptions and coding together
for (v in c("CDLPRS42", "CDLTRT42")) {
  cat("\n----------------------------------------\n")
  cat("VARIABLE:", v, "\n")
  
  print(list(
    description = attr(bc_data[[v]], "label"),
    response_labels = attr(bc_data[[v]], "labels")
  ))
}

cat("\nBILL WORRY versus PRESCRIPTION DELAY\n")

with(
  design_bc$variables,
  print(table(
    Bill_worry = worry,
    Prescription_delay = delay_rx,
    useNA = "ifany"
  ))
)

cat("\nUNABLE TO COVER BILLS versus TREATMENT DELAY\n")

with(
  design_bc$variables,
  print(table(
    Unable_to_cover_bills = unable,
    Treatment_delay = delay_treatment,
    useNA = "ifany"
  ))
)


# ------------------------------------------------------------
# Step 19D: Remaining care-delay checks
# ------------------------------------------------------------

print(list(
  prescription_description =
    attr(bc_data$CDLPRS42, "label"),
  
  prescription_labels =
    attr(bc_data$CDLPRS42, "labels"),
  
  treatment_description =
    attr(bc_data$CDLTRT42, "label"),
  
  treatment_labels =
    attr(bc_data$CDLTRT42, "labels"),
  
  prescription_counts = with(
    design_bc$variables,
    table(
      Bill_worry = worry,
      Prescription_delay = delay_rx,
      useNA = "ifany"
    )
  )
))


# ------------------------------------------------------------
# Step 19E: Weighted economic-burden and care-delay summaries
# ------------------------------------------------------------

options(
  survey.lonely.psu = "adjust",
  survey.adjust.domain.lonely = TRUE
)

# 1. Prescription delay by medical-bill worry
rx_results <- weighted_binary(
  design = design_bc,
  outcome = "delay_rx",
  group = "worry_group"
)

# 2. Treatment delay by inability to cover bills
treatment_delay_results <- weighted_binary(
  design = design_bc,
  outcome = "delay_treatment",
  group = "unable_group"
)

# 3. Follow-up delay by inability to cover bills
followup_results <- weighted_binary(
  design = design_bc,
  outcome = "delay_followup",
  group = "unable_group"
)

# Combine and save
care_results <- rbind(
  rx_results,
  treatment_delay_results,
  followup_results
)

write.csv(
  care_results,
  "results/burden_and_care_delays.csv",
  row.names = FALSE
)

# Compact display
care_display <- data.frame(
  Outcome = care_results$outcome,
  Group = care_results$group,
  Yes_n = care_results$yes_n,
  Valid_n = care_results$n,
  Weighted_percent = round(care_results$percent, 1),
  CI_95 = sprintf(
    "%.1f to %.1f",
    care_results$lower,
    care_results$upper
  )
)

print(
  care_display,
  row.names = FALSE,
  right = FALSE
)

# ------------------------------------------------------------
# Step 19F: Prescription-delay visualization
# ------------------------------------------------------------

plot_weighted(
  rx_results,
  "Delayed/forgone prescriptions by medical-bill worry"
)

# Save a copy
pdf(
  "results/prescription_delay_by_bill_worry.pdf",
  width = 8,
  height = 6
)

plot_weighted(
  rx_results,
  "Delayed/forgone prescriptions by medical-bill worry"
)

dev.off()

# ------------------------------------------------------------
# Step 20A: Inspect income and insurance before comparisons
# ------------------------------------------------------------

cat("\n--- INCOME DESCRIPTION AND LABELS ---\n")

print(list(
  description = attr(bc_data$POVCAT24, "label"),
  response_labels = attr(bc_data$POVCAT24, "labels")
))

cat("\n--- INSURANCE DESCRIPTION AND LABELS ---\n")

print(list(
  description = attr(bc_data$INSCOV24, "label"),
  response_labels = attr(bc_data$INSCOV24, "labels")
))

cat("\n--- INCOME GROUP COUNTS ---\n")

print(table(
  design_bc$variables$income,
  useNA = "ifany"
))

cat("\n--- INSURANCE GROUP COUNTS ---\n")

print(table(
  design_bc$variables$insurance,
  useNA = "ifany"
))

cat("\n--- BILL WORRY BY INCOME ---\n")

with(
  design_bc$variables,
  print(table(
    Income = income,
    Bill_worry = worry,
    useNA = "ifany"
  ))
)

cat("\n--- BILL WORRY BY INSURANCE ---\n")

with(
  design_bc$variables,
  print(table(
    Insurance = insurance,
    Bill_worry = worry,
    useNA = "ifany"
  ))
)


# ------------------------------------------------------------
# Step 20B: Medical-bill worry by insurance
# Comparison: any private versus public only
# ------------------------------------------------------------

options(
  survey.lonely.psu = "adjust",
  survey.adjust.domain.lonely = TRUE
)

# Restrict the survey design to the two supportable categories
design_insurance <- subset(
  design_bc,
  INSCOV24 %in% c(1, 2)
)

# Create a clearly labeled comparison variable
design_insurance <- update(
  design_insurance,
  insurance_comparison = factor(
    as.numeric(INSCOV24),
    levels = c(1, 2),
    labels = c("Any private", "Public only")
  )
)

# Weighted percentages and 95% confidence intervals
insurance_worry_results <- weighted_binary(
  design = design_insurance,
  outcome = "worry",
  group = "insurance_comparison"
)

print(
  insurance_worry_results,
  row.names = FALSE
)

# Save the results
write.csv(
  insurance_worry_results,
  "results/bill_worry_by_insurance.csv",
  row.names = FALSE
)

# Display the graph
plot_weighted(
  insurance_worry_results,
  "Medical-bill worry by insurance coverage"
)

# ------------------------------------------------------------
# Step 20D: Medical-bill worry by grouped family income
# ------------------------------------------------------------

options(
  survey.lonely.psu = "adjust",
  survey.adjust.domain.lonely = TRUE
)

# Keep valid original income categories
design_income <- subset(
  design_bc,
  POVCAT24 %in% 1:5
)

# Combine poor/negative, near-poor, and low income
design_income <- update(
  design_income,
  income_group = factor(
    ifelse(
      POVCAT24 %in% c(1, 2, 3), 1,
      ifelse(POVCAT24 == 4, 2, 3)
    ),
    levels = c(1, 2, 3),
    labels = c(
      "Lower income",
      "Middle income",
      "High income"
    )
  )
)

# Confirm unweighted counts
with(
  design_income$variables,
  print(table(
    Income_group = income_group,
    Bill_worry = worry,
    useNA = "ifany"
  ))
)

# Weighted percentages and 95% confidence intervals
income_worry_results <- weighted_binary(
  design = design_income,
  outcome = "worry",
  group = "income_group"
)

# Compact display
income_display <- data.frame(
  Income = income_worry_results$group,
  Yes_n = income_worry_results$yes_n,
  Valid_n = income_worry_results$n,
  Weighted_percent = round(
    income_worry_results$percent, 1
  ),
  CI_95 = sprintf(
    "%.1f to %.1f",
    income_worry_results$lower,
    income_worry_results$upper
  )
)

print(
  income_display,
  row.names = FALSE,
  right = FALSE
)

# Save the full estimates
write.csv(
  income_worry_results,
  "results/bill_worry_by_grouped_income.csv",
  row.names = FALSE
)

# Display the graph
plot_weighted(
  income_worry_results,
  "Medical-bill worry by family income"
)

# ------------------------------------------------------------
# Step 20E: Overall income–bill-worry association
# ------------------------------------------------------------

options(
  survey.lonely.psu = "adjust",
  survey.adjust.domain.lonely = TRUE
)

# Use respondents with valid income and bill-worry responses
design_income_worry <- subset(
  design_income,
  !is.na(worry) & !is.na(income_group)
)

# Confirm the analysis counts
with(
  design_income_worry$variables,
  print(table(
    Income = income_group,
    Bill_worry = worry
  ))
)

# Overall survey-adjusted association test
income_worry_test <- survey::svychisq(
  ~income_group + worry,
  design = design_income_worry,
  statistic = "F"
)

print(income_worry_test)

# Save the test output
capture.output(
  print(income_worry_test),
  file = "results/income_worry_association_test.txt"
)

# ------------------------------------------------------------
# Step 21A: Prepare a limited adjusted model
# Outcome: medical-bill worry
# Predictors: treatment status, age, grouped income
# ------------------------------------------------------------

# design_income contains the three-group income variable
# and all positive-weight breast-cancer records with valid income

design_model <- subset(
  design_income,
  !is.na(worry) &
    !is.na(treatment_group) &
    !is.na(age10) &
    !is.na(income_group)
)

# Use high income as the reference category
design_model <- update(
  design_model,
  income_group = relevel(
    income_group,
    ref = "High income"
  )
)

cat(
  "\nComplete-case model records:",
  nrow(design_model$variables),
  "\nDesign degrees of freedom:",
  survey::degf(design_model),
  "\n"
)

cat("\nBILL-WORRY COUNTS\n")
print(table(
  design_model$variables$worry
))

cat("\nWORRY BY TREATMENT STATUS\n")
with(
  design_model$variables,
  print(table(treatment_group, worry))
)

cat("\nWORRY BY GROUPED INCOME\n")
with(
  design_model$variables,
  print(table(income_group, worry))
)

cat("\nAGE SUMMARY\n")
print(summary(
  design_model$variables$age
))

print(list(
  model_sample_size = nrow(design_model$variables),
  
  design_degrees_of_freedom =
    survey::degf(design_model),
  
  worry_counts = table(
    design_model$variables$worry,
    useNA = "ifany"
  ),
  
  worry_by_treatment = with(
    design_model$variables,
    table(treatment_group, worry)
  ),
  
  worry_by_income = with(
    design_model$variables,
    table(income_group, worry)
  )
))

# ------------------------------------------------------------
# Step 21B: Adjusted model of medical-bill worry
# ------------------------------------------------------------

options(
  survey.lonely.psu = "adjust",
  survey.adjust.domain.lonely = TRUE
)

# Explicitly set the reference categories
design_model <- update(
  design_model,
  
  treatment_group = relevel(
    treatment_group,
    ref = "Not currently treated"
  ),
  
  income_group = relevel(
    income_group,
    ref = "High income"
  )
)

# Fit the limited model
model_worry <- survey::svyglm(
  worry ~ treatment_group + age10 + income_group,
  design = design_model,
  family = quasibinomial()
)

# Display model coefficients and diagnostics
print(summary(model_worry))

cat("\nModel converged:", model_worry$converged, "\n")

# ------------------------------------------------------------
# Step 21C: Adjusted odds ratios from the existing model
# ------------------------------------------------------------

model_ci <- confint(
  model_worry,
  method = "Wald",
  ddf = model_worry$df.residual
)

coefficient_table <- coef(summary(model_worry))

model_results <- data.frame(
  Term = names(coef(model_worry)),
  Adjusted_OR = exp(coef(model_worry)),
  Lower_95 = exp(model_ci[, 1]),
  Upper_95 = exp(model_ci[, 2]),
  P_value = coefficient_table[, ncol(coefficient_table)],
  row.names = NULL
)

model_results <- subset(
  model_results,
  Term != "(Intercept)"
)

print(
  model_results,
  row.names = FALSE,
  digits = 4
)

write.csv(
  model_results,
  "results/adjusted_worry_model.csv",
  row.names = FALSE
)

# ------------------------------------------------------------
# Step 21D: Sensitivity to the single-PSU variance adjustment
# ------------------------------------------------------------

sensitivity_results <- local({
  
  old_options <- options(
    survey.lonely.psu = "average",
    survey.adjust.domain.lonely = TRUE
  )
  
  on.exit(options(old_options))
  
  model_worry_average <- survey::svyglm(
    worry ~ treatment_group + age10 + income_group,
    design = design_model,
    family = quasibinomial()
  )
  
  extract_results <- function(model, method) {
    
    ci <- confint(
      model,
      method = "Wald",
      ddf = model$df.residual
    )
    
    ct <- coef(summary(model))
    
    out <- data.frame(
      Method = method,
      Term = names(coef(model)),
      Adjusted_OR = exp(coef(model)),
      Lower_95 = exp(ci[, 1]),
      Upper_95 = exp(ci[, 2]),
      P_value = ct[, ncol(ct)],
      row.names = NULL
    )
    
    out[out$Term != "(Intercept)", ]
  }
  
  rbind(
    extract_results(model_worry, "adjust"),
    extract_results(model_worry_average, "average")
  )
})

print(
  sensitivity_results,
  row.names = FALSE,
  digits = 4
)

write.csv(
  sensitivity_results,
  "results/worry_model_sensitivity.csv",
  row.names = FALSE
)

# ------------------------------------------------------------
# Step 22: Forest plot of adjusted odds ratios
# ------------------------------------------------------------

# If needed, install once:
# install.packages("ggplot2")

library(ggplot2)

# Prepare plotting data
plot_data <- model_results

term_labels <- c(
  "treatment_groupCurrently treated" =
    "Currently treated vs not currently treated",
  "age10" =
    "Age (per 10-year increase)",
  "income_groupLower income" =
    "Lower income vs high income",
  "income_groupMiddle income" =
    "Middle income vs high income"
)

plot_data$Predictor <- factor(
  plot_data$Term,
  levels = rev(names(term_labels)),
  labels = rev(unname(term_labels))
)

plot_data$Estimate_label <- sprintf(
  "%.2f (%.2f–%.2f)",
  plot_data$Adjusted_OR,
  plot_data$Lower_95,
  plot_data$Upper_95
)

# Build plot
worry_forest_plot <- ggplot(
  plot_data,
  aes(x = Adjusted_OR, y = Predictor)
) +
  geom_vline(
    xintercept = 1,
    linetype = "dashed",
    color = "grey50"
  ) +
  geom_segment(
    aes(
      x = Lower_95,
      xend = Upper_95,
      yend = Predictor
    ),
    linewidth = 0.8,
    color = "#24557A"
  ) +
  geom_point(
    size = 3.2,
    color = "#24557A"
  ) +
  geom_text(
    aes(x = 10, label = Estimate_label),
    hjust = 0,
    size = 3.7
  ) +
  scale_x_log10(
    breaks = c(0.25, 0.5, 1, 2, 4, 8),
    labels = c("0.25", "0.5", "1", "2", "4", "8")
  ) +
  coord_cartesian(
    xlim = c(0.25, 30)
  ) +
  labs(
    title = "Factors associated with medical-bill worry",
    subtitle = paste(
      "Adjusted odds ratios and 95% confidence intervals",
      "| Analytic sample: n = 260"
    ),
    x = "Adjusted odds ratio (log scale)",
    y = NULL,
    caption = paste(
      "Each estimate is adjusted for the other predictors shown.",
      "Dashed line: odds ratio = 1.",
      "Primary analysis uses the 'adjust' single-PSU method;",
      "conclusions were unchanged using 'average'.",
      sep = "\n"
    )
  ) +
  theme_minimal(base_size = 12) +
  theme(
    panel.grid.major.y = element_blank(),
    panel.grid.minor = element_blank(),
    plot.title = element_text(face = "bold"),
    plot.subtitle = element_text(
      color = "grey35",
      margin = margin(b = 15)
    ),
    plot.caption = element_text(
      hjust = 0,
      size = 9,
      margin = margin(t = 15)
    ),
    axis.text.y = element_text(color = "black"),
    plot.margin = margin(15, 20, 15, 15)
  )

print(worry_forest_plot)

# Save figure
dir.create("results", showWarnings = FALSE)

ggsave(
  filename = "results/adjusted_worry_forest_plot.png",
  plot = worry_forest_plot,
  width = 11,
  height = 5.5,
  dpi = 300,
  bg = "white"
)

ggsave(
  filename = "results/adjusted_worry_forest_plot.pdf",
  plot = worry_forest_plot,
  width = 11,
  height = 5.5,
  bg = "white"
)


# ------------------------------------------------------------
# Step 23: Verify the design and analysis variables
# ------------------------------------------------------------

options(
  survey.lonely.psu = "adjust",
  survey.adjust.domain.lonely = TRUE
)

# Verify analysis_data contains all imported people
stopifnot(
  nrow(analysis_data) == nrow(bc_data),
  setequal(analysis_data$DUPERSID, bc_data$DUPERSID),
  !anyDuplicated(analysis_data$DUPERSID),
  !anyNA(analysis_data$VARSTR),
  !anyNA(analysis_data$VARPSU),
  !anyNA(analysis_data$CSAQW24F),
  all(analysis_data$CSAQW24F >= 0)
)

# Verify the breast-cancer domain
stopifnot(
  all(design_bc$variables$CABREAST == 1),
  all(design_bc$variables$CSAQW24F > 0)
)

# Check the existing burden indicators are numeric 0/1 or missing
burden_vars <- c("worry", "debt", "unable", "sacrifice")

stopifnot(
  all(burden_vars %in% names(design_bc$variables))
)

for (v in burden_vars) {
  x <- design_bc$variables[[v]]
  
  stopifnot(
    is.numeric(x) || is.logical(x),
    all(is.na(x) | x %in% c(0, 1))
  )
}

cat(
  "\nBreast-cancer domain records:",
  nrow(design_bc$variables),
  "\nDesign degrees of freedom:",
  survey::degf(design_bc),
  "\n"
)

print(table(
  design_bc$variables$treatment_group,
  useNA = "ifany"
))

# Check raw codes against recoded indicators
raw_burden <- c(
  worry = "CFNPMT42",
  debt = "CFNDBT42",
  unable = "CFNUNB42",
  sacrifice = "CFNSPD42"
)

for (v in names(raw_burden)) {
  cat("\nRaw-to-recoded check:", v, "\n")
  
  print(table(
    raw = design_bc$variables[[raw_burden[[v]]]],
    recoded = design_bc$variables[[v]],
    useNA = "ifany"
  ))
}


# ------------------------------------------------------------
# Step 24: Weighted financial-hardship summaries
# ------------------------------------------------------------

burden_titles <- c(
  worry = "Medical-bill worry",
  debt = "Borrowing money or debt",
  unable = "Unable to cover medical bills",
  sacrifice = "Sacrificed basic spending"
)

# Add a constant grouping variable for overall estimates
design_bc_plot <- update(
  design_bc,
  all_respondents = factor("All respondents")
)

# Overall financial-hardship profile
burden_overall <- do.call(
  rbind,
  lapply(names(burden_titles), function(v) {
    weighted_binary(
      design = design_bc_plot,
      outcome = v,
      group = "all_respondents"
    )
  })
)

# Financial hardship by current cancer treatment
burden_by_treatment <- do.call(
  rbind,
  lapply(names(burden_titles), function(v) {
    weighted_binary(
      design = design_bc_plot,
      outcome = v,
      group = "treatment_group"
    )
  })
)

# Add readable labels
add_burden_labels <- function(tab) {
  
  tab$indicator <- unname(
    burden_titles[as.character(tab$outcome)]
  )
  
  tab$indicator <- factor(
    tab$indicator,
    levels = rev(unname(burden_titles))
  )
  
  tab
}

burden_overall <- add_burden_labels(burden_overall)

burden_by_treatment <- add_burden_labels(
  burden_by_treatment
)

print(burden_overall, row.names = FALSE, digits = 4)

print(
  burden_by_treatment,
  row.names = FALSE,
  digits = 4
)

dir.create("results", showWarnings = FALSE)

write.csv(
  burden_overall,
  "results/breast_cancer_burden_overall.csv",
  row.names = FALSE
)

write.csv(
  burden_by_treatment,
  "results/breast_cancer_burden_by_treatment.csv",
  row.names = FALSE
)

# ------------------------------------------------------------
# Step 25: Overall financial-hardship profile
# ------------------------------------------------------------

library(ggplot2)

profile_data <- burden_overall

profile_data$display_label <- sprintf(
  "%.1f%% (n=%d)",
  profile_data$percent,
  profile_data$n
)

profile_data$label_x <- ifelse(
  is.finite(profile_data$upper),
  profile_data$upper,
  profile_data$percent
) + 2

profile_limit <- max(
  35,
  profile_data$label_x + 20,
  na.rm = TRUE
)

profile_limit <- min(100, profile_limit)

p_burden_profile <- ggplot(
  profile_data,
  aes(x = percent, y = indicator)
) +
  geom_segment(
    data = subset(
      profile_data,
      is.finite(lower) & is.finite(upper)
    ),
    aes(
      x = lower,
      xend = upper,
      yend = indicator
    ),
    linewidth = 0.8,
    color = "#24557A"
  ) +
  geom_point(
    size = 3.3,
    color = "#24557A"
  ) +
  geom_text(
    aes(
      x = label_x,
      label = display_label
    ),
    hjust = 0,
    size = 3.7
  ) +
  scale_x_continuous(
    labels = function(x) paste0(x, "%"),
    breaks = seq(0, 100, 10)
  ) +
  coord_cartesian(
    xlim = c(0, profile_limit),
    clip = "off"
  ) +
  labs(
    title = "Financial hardship among respondents with breast-cancer history",
    subtitle = "2024 MEPS | Survey-weighted estimates",
    x = "Percentage reporting each outcome",
    y = NULL,
    caption = paste(
      "Lines indicate 95% confidence intervals.",
      "n = unweighted valid responses for each outcome.",
      "Outcomes can overlap; percentages should not be added.",
      "No interval is shown when all valid responses are identical.",
      sep = "\n"
    )
  ) +
  theme_minimal(base_size = 12) +
  theme(
    panel.grid.major.y = element_blank(),
    panel.grid.minor = element_blank(),
    plot.title = element_text(face = "bold", size = 14),
    plot.caption = element_text(hjust = 0, size = 9),
    plot.margin = margin(15, 35, 15, 15)
  )

print(p_burden_profile)

ggsave(
  "results/breast_cancer_burden_profile.png",
  p_burden_profile,
  width = 12,
  height = 5.5,
  dpi = 300,
  bg = "white"
)

ggsave(
  "results/breast_cancer_burden_profile.pdf",
  p_burden_profile,
  width = 12,
  height = 5.5,
  bg = "white"
)

# ------------------------------------------------------------
# Step 26: Financial hardship by current cancer treatment
# ------------------------------------------------------------

treatment_plot_data <- burden_by_treatment

treatment_plot_data$group <- factor(
  treatment_plot_data$group,
  levels = c(
    "Not currently treated",
    "Currently treated"
  )
)

stopifnot(!anyNA(treatment_plot_data$group))

treatment_plot_data$display_label <- sprintf(
  "%.1f%% (n=%d)",
  treatment_plot_data$percent,
  treatment_plot_data$n
)

treatment_plot_data$label_x <- ifelse(
  is.finite(treatment_plot_data$upper),
  treatment_plot_data$upper,
  treatment_plot_data$percent
) + 2

treatment_limit <- min(
  100,
  max(
    40,
    treatment_plot_data$label_x + 20,
    na.rm = TRUE
  )
)

p_burden_treatment <- ggplot(
  treatment_plot_data,
  aes(
    x = percent,
    y = group,
    color = group
  )
) +
  geom_segment(
    data = subset(
      treatment_plot_data,
      is.finite(lower) & is.finite(upper)
    ),
    aes(
      x = lower,
      xend = upper,
      yend = group
    ),
    linewidth = 0.8
  ) +
  geom_point(size = 3) +
  geom_text(
    aes(
      x = label_x,
      label = display_label
    ),
    hjust = 0,
    size = 3.3,
    show.legend = FALSE
  ) +
  facet_wrap(
    ~indicator,
    ncol = 2
  ) +
  scale_color_manual(
    values = c(
      "Not currently treated" = "#666666",
      "Currently treated" = "#0072B2"
    )
  ) +
  scale_x_continuous(
    labels = function(x) paste0(x, "%"),
    breaks = seq(0, 100, 20)
  ) +
  coord_cartesian(
    xlim = c(0, treatment_limit),
    clip = "off"
  ) +
  labs(
    title = "Financial hardship by current cancer-treatment status",
    subtitle = "Respondents with breast-cancer history | 2024 MEPS",
    x = "Survey-weighted percentage",
    y = NULL,
    caption = paste(
      "Lines indicate 95% confidence intervals.",
      "n = unweighted valid responses within each group.",
      "Descriptive estimates; not adjusted for age or income.",
      "Current treatment refers to cancer treatment, not necessarily breast-cancer treatment.",
      sep = "\n"
    )
  ) +
  theme_minimal(base_size = 11) +
  theme(
    legend.position = "none",
    panel.grid.major.y = element_blank(),
    panel.grid.minor = element_blank(),
    strip.text = element_text(face = "bold"),
    plot.title = element_text(face = "bold", size = 14),
    plot.caption = element_text(hjust = 0, size = 9),
    plot.margin = margin(15, 30, 15, 15)
  )

print(p_burden_treatment)

ggsave(
  "results/breast_cancer_burden_by_treatment.png",
  p_burden_treatment,
  width = 13,
  height = 7,
  dpi = 300,
  bg = "white"
)

# ------------------------------------------------------------
# Step 27: Inspect delayed or forgone cancer care
# ------------------------------------------------------------

care_vars <- c(
  "CDLPRS42",
  "CDLTRT42",
  "CDLFUP42"
)

for (v in care_vars) {
  
  x <- design_bc$variables[[v]]
  
  cat("\n--------------------------------\n")
  cat("Variable:", v, "\n")
  
  cat("\nDescription:\n")
  print(attr(x, "label"))
  
  cat("\nResponse labels:\n")
  print(attr(x, "labels"))
  
  cat("\nUnweighted counts:\n")
  print(table(x, useNA = "ifany"))
}

# ------------------------------------------------------------
# Step 28: Recode delayed or forgone care
# ------------------------------------------------------------

yes_no_01 <- function(x) {
  out <- rep(NA_real_, length(x))
  out[which(x == 1)] <- 1
  out[which(x == 2)] <- 0
  out
}

design_bc_care <- update(
  design_bc,
  delay_rx = yes_no_01(CDLPRS42),
  delay_treatment = yes_no_01(CDLTRT42),
  delay_followup = yes_no_01(CDLFUP42)
)

care_titles <- c(
  delay_rx = "Prescriptions",
  delay_treatment = "Treatment",
  delay_followup = "Follow-up care"
)

# Confirm recoded counts
for (v in names(care_titles)) {
  cat("\n", care_titles[[v]], "\n")
  print(table(
    design_bc_care$variables[[v]],
    useNA = "ifany"
  ))
}


# ------------------------------------------------------------
# Step 29: Overall weighted estimates of care disruption
# ------------------------------------------------------------

care_results <- do.call(
  rbind,
  lapply(names(care_titles), function(v) {
    
    keep <- !is.na(design_bc_care$variables[[v]])
    d <- design_bc_care[keep, ]
    y <- d$variables[[v]]
    
    fit <- survey::svyciprop(
      reformulate(v),
      design = d,
      method = "beta",
      level = 0.95
    )
    
    ci <- as.numeric(confint(fit))
    
    data.frame(
      outcome = v,
      indicator = unname(care_titles[[v]]),
      n = length(y),
      yes_n = sum(y == 1),
      missing_n = sum(!keep),
      percent = 100 * as.numeric(coef(fit))[1],
      lower = 100 * ci[1],
      upper = 100 * ci[2],
      row.names = NULL
    )
  })
)

print(
  care_results,
  row.names = FALSE,
  digits = 4
)

dir.create("results", showWarnings = FALSE)

write.csv(
  care_results,
  "results/breast_cancer_care_disruption.csv",
  row.names = FALSE
)


# ------------------------------------------------------------
# Step 30: Plot delayed or forgone care
# ------------------------------------------------------------

library(ggplot2)

care_plot_data <- care_results

care_plot_data$row_label <- sprintf(
  "%s\n%.1f%%; %d yes / %d valid responses",
  care_plot_data$indicator,
  care_plot_data$percent,
  care_plot_data$yes_n,
  care_plot_data$n
)

care_plot_data$row_label <- factor(
  care_plot_data$row_label,
  levels = rev(care_plot_data$row_label)
)

p_care_disruption <- ggplot(
  care_plot_data,
  aes(x = percent, y = row_label)
) +
  geom_segment(
    aes(
      x = lower,
      xend = upper,
      yend = row_label
    ),
    linewidth = 0.9,
    color = "#0072B2"
  ) +
  geom_point(
    size = 3.5,
    color = "#0072B2"
  ) +
  scale_x_continuous(
    limits = c(0, NA),
    labels = function(x) paste0(x, "%"),
    expand = expansion(mult = c(0, 0.12))
  ) +
  labs(
    title = "Reported delays or forgone care",
    subtitle = "Respondents with breast-cancer history | 2024 MEPS",
    x = "Survey-weighted percentage",
    y = NULL,
    caption = paste(
      "Lines show 95% confidence intervals using the Korn–Graubard beta method.",
      "Event counts and valid-response counts are unweighted.",
      "Nine responses are missing for each outcome.",
      "Outcomes can overlap; the same person may report more than one.",
      sep = "\n"
    )
  ) +
  theme_minimal(base_size = 12) +
  theme(
    panel.grid.major.y = element_blank(),
    panel.grid.minor = element_blank(),
    axis.text.y = element_text(
      color = "black",
      lineheight = 1.1
    ),
    plot.title = element_text(
      face = "bold",
      size = 15
    ),
    plot.caption = element_text(
      hjust = 0,
      size = 9,
      margin = margin(t = 12)
    ),
    plot.margin = margin(15, 20, 15, 15)
  )

print(p_care_disruption)

ggsave(
  "results/breast_cancer_care_disruption.png",
  plot = p_care_disruption,
  width = 11,
  height = 5.5,
  dpi = 300,
  bg = "white"
)

ggsave(
  "results/breast_cancer_care_disruption.pdf",
  plot = p_care_disruption,
  width = 11,
  height = 5.5,
  bg = "white"
)

#MOORE VISUALLIZATION

# ------------------------------------------------------------
# Presentation figure: Overall financial-hardship profile
# ------------------------------------------------------------

library(ggplot2)

burden_plot_data <- burden_overall

# Order rows from highest to lowest percentage
burden_plot_data <- burden_plot_data[
  order(burden_plot_data$percent, decreasing = TRUE),
]

burden_plot_data$indicator <- factor(
  as.character(burden_plot_data$indicator),
  levels = rev(as.character(burden_plot_data$indicator))
)

# Put exact estimates in a separate column to the right
burden_plot_data$estimate_label <- sprintf(
  "%.1f%% (%.1f–%.1f)",
  burden_plot_data$percent,
  burden_plot_data$lower,
  burden_plot_data$upper
)

p_burden_overall <- ggplot(
  burden_plot_data,
  aes(x = percent, y = indicator)
) +
  geom_segment(
    aes(
      x = lower,
      xend = upper,
      yend = indicator
    ),
    linewidth = 1,
    color = "#24557A"
  ) +
  geom_point(
    size = 3.8,
    color = "#24557A"
  ) +
  geom_text(
    aes(
      x = 39,
      label = estimate_label
    ),
    hjust = 0,
    size = 4,
    color = "black"
  ) +
  scale_x_continuous(
    breaks = seq(0, 35, 5),
    labels = function(x) paste0(x, "%"),
    expand = expansion(mult = c(0, 0))
  ) +
  coord_cartesian(
    xlim = c(0, 58)
  ) +
  labs(
    title = "About 1 in 4 reported medical-bill worry",
    subtitle = paste(
      "Financial hardship among respondents with",
      "breast-cancer history | 2024 MEPS"
    ),
    x = "Survey-weighted percentage",
    y = NULL,
    caption = paste(
      "Points show weighted percentages; lines show 95% confidence intervals.",
      "Numbers at right: percentage (95% CI).",
      "Valid responses: worry, 263; unable to cover bills, 263;",
      "sacrificed basic spending, 261; borrowing or debt, 262.",
      "Outcomes may overlap and should not be added together.",
      sep = "\n"
    )
  ) +
  theme_minimal(base_size = 13) +
  theme(
    panel.grid.major.y = element_blank(),
    panel.grid.minor = element_blank(),
    axis.text.y = element_text(color = "black"),
    plot.title = element_text(
      face = "bold",
      size = 18,
      margin = margin(b = 8)
    ),
    plot.subtitle = element_text(
      size = 11,
      color = "grey30",
      margin = margin(b = 16)
    ),
    plot.caption = element_text(
      hjust = 0,
      size = 9,
      margin = margin(t = 14)
    ),
    plot.margin = margin(18, 20, 15, 15)
  )

print(p_burden_overall)

dir.create("results", showWarnings = FALSE)

ggsave(
  "results/breast_cancer_burden_overall_presentation.png",
  plot = p_burden_overall,
  width = 12,
  height = 6,
  dpi = 300,
  bg = "white"
)

ggsave(
  "results/breast_cancer_burden_overall_presentation.pdf",
  plot = p_burden_overall,
  width = 12,
  height = 6,
  bg = "white"
)
