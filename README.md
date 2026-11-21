# 2nd Place Winner 🥈 at the 2026 BioKind Analytics Datathon (MEPS Health Care Track)
# Try out the project here: https://ctr-alt-elite-5rx2fh3smk5bxvbd2c8sgv.streamlit.app/

# Too Young for Medicare

**Financial hardship among breast cancer survivors under 65**
2026 Public Health Datathon (Biokind × UBSA), Healthcare Access track · Team Ctr-Alt-Elite

## Thesis

Breast cancer survivors under 65 are not yet eligible for Medicare, and they carry much more financial hardship than survivors 65 and older. Lower income makes it worse. We see the gap in the **MEPS 2024 Full Year Consolidated file (HC-256)**, and we check it against a larger CDC survey (NHIS 2021–2024). Published research suggests Medicare eligibility at 65 is part of the cause.

## Audience

- Cancer center leadership and oncology financial navigators.
- Employers and benefits teams who insure working-age patients.

## Call to action

**Screen every breast cancer patient under 65 for financial hardship at diagnosis.** Use a short risk screen like the tool in this app, and route high-risk patients to financial navigation before the bills arrive.

## Key findings

> All values come from `data/processed/` (MEPS 2024 HC-256 unless marked NHIS), survey-weighted, with 95% CIs. † = interpret with caution (unweighted n < 60 or RSE > 30%).

- **Any cancer-related financial strain (CSAQ, CSAQW24F):** 52.8% (32.4–72.3)† of survivors under 65 vs 19.1% (12.7–27.6) of survivors 65+ (difference +33.7 pp, 95% CI 14.8 to 52.6; Wald p on the difference = 0.0007, Rao-Scott p = 0.0003). Unweighted n = 59 under 65, 205 aged 65+.
- **Worried about paying medical bills:** 42.4% (22.9–64.6)† under 65 vs 18.4% (12.1–27.1) 65+ (difference +24.0 pp, 95% CI 4.1 to 43.8; Wald p = 0.019, Rao-Scott p = 0.009). The under-65 estimate is higher on 12 of 13 paired strain measures; out-of-pocket costs ≥ 10% of family income are the exception (12.2% vs 12.2%), and the gaps for cost-related prescription delay (4.3% vs 3.7%) and sacrificed basic spending (13.0% vs 9.9%) are small and not significant. Two further gaps are **borderline, not significant** by the test that matches their CI: problems paying medical bills (PROBPY42, PERWT24F) 13.0% vs 4.9% (+8.1 pp, 95% CI −0.8 to 17.1; Wald p = 0.074; Rao-Scott p = 0.029) and cost-related delayed or forgone care 8.5% vs 3.2% (+5.3 pp, 95% CI −1.0 to 11.7; Wald p = 0.10; Rao-Scott p = 0.030). `meps_age_gap_tests.csv` carries both p-values; `p_wald` comes from the same test as the CI.
- **After adjusting for treatment status and income (Model B):** adjusted OR for under 65 = 3.78 (95% CI 1.58–9.01; p = 0.003), n = 260 CSAQ respondents (64 worried). Lower vs high income: aOR 3.01 (1.19–7.63).
- **Income:** bill worry is 38.4% in the lower-income group (<200% FPL) vs 24.2% in the high-income group (400%+); the middle group (200–399%) is 18.2%†, so the income pattern is not monotonic. Out-of-pocket burden ≥ 10% of income is 30.5% (lower) vs 3.5%† (high).
- **Replication in NHIS 2021–2024 (n = 2,899 survivors; 2,892 with the outcome):** problems paying medical bills, 17.9% (15.1–21.1) under 65 vs 7.6% (6.3–9.2) 65+. Worried about paying bills if sick (very/somewhat): 48.4% vs 28.7%. Delayed or skipped care due to cost: 10.2% vs 3.1%.
- **Risk tool:** trained on NHIS, cross-validated AUC 0.739 (fold SD ±0.04), Brier 0.093, calibration slope 1.01. **External validation on MEPS 2024:** AUC 0.793 (bootstrap 95% CI 0.699–0.871), Brier 0.067, n = 368 with 29 events; mean predicted risk 9.8% vs 7.5% observed (the model over-predicts slightly in MEPS). Subgroup audit: AUC is lower for NH Black survivors (0.63) and the model under-predicts for them (16.2% predicted vs 19.7% observed).
- **Changes from the team's original numbers (see `data/processed/meps_team_reproduction.csv`):** the team's survey-weighted analysis already used the correct CSAQ weight (CSAQW24F) on a full-file design. Re-running their method reproduces their Model A (age per 10 years aOR 0.54, 95% CI 0.36–0.81; lower vs high income 2.98, 1.15–7.72; n = 260), bill worry by income (38.4 / 18.2 / 24.2%), and CSAQ prescription delay by bill worry (11.8% vs 1.9%) to the decimal. The weight fix matters for the team's earlier **unweighted** treatment-group bar charts (built from raw `table()` counts) and the preliminary age split, which we replace with weighted estimates. Using PERWT24F instead of CSAQW24F would shift results slightly (age aOR 0.52; worry 36.8 / 17.7 / 22.9%). Our cohort also drops 18 rows of the team's extract that were included by ICD-10 C50 code but reported no breast cancer diagnosis (see Cohort note). The guide's cost-related prescription item (DLAYPM42/AFRDPM42) gives 8.5%† vs 2.1%† by bill worry.

Context (see references): the median age at breast cancer diagnosis is 63 (ACS), so about half of cases are diagnosed before Medicare age. At 65, Medicare coverage among cancer survivors jumps from 8.3% to 98.2%, and worry about paying medical bills falls by 7.7 percentage points (Kwon et al. 2025).

## Repository layout

```
├── README.md
├── LICENSE                      # MIT for code; data stay under their own terms
├── requirements.txt             # Python deps (app + ML)
├── r-packages.txt               # R deps
├── Makefile                     # make data / estimates / model / figures / app / all
├── data/
│   ├── raw/                     # downloaded zips (gitignored)
│   ├── interim/                 # cleaned person-level files (gitignored)
│   └── processed/               # small aggregate CSVs the app reads (committed)
├── R/
│   ├── 00_utils.R               # recode helpers, suppression rule, CI helper
│   ├── 01_meps_clean.R          # MEPS cohort + recodes
│   ├── 02_meps_estimates.R      # weighted estimates -> data/processed/meps_*.csv
│   ├── 03_meps_models.R         # svyglm models -> data/processed/meps_model_or.csv
│   ├── 04_nhis_clean.R          # pooled NHIS 2021–2024 cohort
│   └── 05_nhis_estimates.R      # NHIS age curve -> data/processed/nhis_age_curve.csv
├── python/
│   ├── harmonize.py             # shared NHIS/MEPS feature definitions
│   ├── train_model.py           # trains on NHIS -> models/, data/processed/ml_*.csv
│   └── evaluate_external.py     # external validation on MEPS 2024
├── models/                      # risk_model.joblib, model_card.json
├── app/
│   ├── Home.py
│   ├── pages/                   # 1_Findings, 2_Risk_Tool, 3_Methods_and_Sources
│   ├── components/              # Plotly chart helpers, figure export
│   └── content/context_stats.yaml  # published statistics + citation keys
├── team_inputs/                 # team's original extract, R script, and chart write-up
└── docs/
    ├── reference/               # codebooks and documentation PDFs
    └── citation_check.md        # verification log for every cited number
```

## Getting the data

All files are free, public-use, and de-identified, and no login is needed. Save each file at the path shown, relative to the repo root.

**MEPS 2024 (AHRQ)**, primary analysis. Source page: https://meps.ahrq.gov/mepsweb/data_stats/download_data_files_detail.jsp?cboPufNumber=HC-256

| File | Link | Save as |
|---|---|---|
| HC-256 2024 Full Year Consolidated (Stata) | https://meps.ahrq.gov/mepsweb/data_files/pufs/h256/h256dta.zip | `data/raw/meps/h256dta.zip` |
| HC-256 documentation | https://meps.ahrq.gov/mepsweb/data_stats/download_data/pufs/h256/h256doc.pdf | `docs/reference/h256doc.pdf` |
| HC-256 codebook | https://meps.ahrq.gov/mepsweb/data_stats/download_data/pufs/h256/h256cb.pdf | `docs/reference/h256cb.pdf` |
| (optional) HC-255 2024 Medical Conditions (Stata) | https://meps.ahrq.gov/mepsweb/data_files/pufs/h255/h255dta.zip | `data/raw/meps/h255dta.zip` |
| (optional) HC-255 codebook | https://meps.ahrq.gov/mepsweb/data_stats/download_data/pufs/h255/h255cb.pdf | `docs/reference/h255cb.pdf` |

**NHIS 2021–2024 Sample Adult (CDC/NCHS)**, used for the age curve and ML training. 2019–2020 are excluded on purpose because those years need special weight adjustments.

| File | Link | Save as |
|---|---|---|
| NHIS 2024 Sample Adult (CSV) | https://ftp.cdc.gov/pub/Health_Statistics/NCHS/Datasets/NHIS/2024/adult24csv.zip | `data/raw/nhis/adult24csv.zip` |
| NHIS 2023 Sample Adult (CSV) | https://ftp.cdc.gov/pub/Health_Statistics/NCHS/Datasets/NHIS/2023/adult23csv.zip | `data/raw/nhis/adult23csv.zip` |
| NHIS 2022 Sample Adult (CSV) | https://ftp.cdc.gov/pub/Health_Statistics/NCHS/Datasets/NHIS/2022/adult22csv.zip | `data/raw/nhis/adult22csv.zip` |
| NHIS 2021 Sample Adult (CSV) | https://ftp.cdc.gov/pub/Health_Statistics/NCHS/Datasets/NHIS/2021/adult21csv.zip | `data/raw/nhis/adult21csv.zip` |
| NHIS 2024 Sample Adult codebook | https://ftp.cdc.gov/pub/Health_Statistics/NCHS/Dataset_Documentation/NHIS/2024/adult-codebook.pdf | `docs/reference/nhis2024_adult-codebook.pdf` |
| NHIS 2024 Survey Description | https://ftp.cdc.gov/pub/Health_Statistics/NCHS/Dataset_Documentation/NHIS/2024/srvydesc-508.pdf | `docs/reference/nhis2024_srvydesc.pdf` |
| NHIS 2024 variable summary | https://ftp.cdc.gov/pub/Health_Statistics/NCHS/Dataset_Documentation/NHIS/2024/adult-summary.pdf | `docs/reference/nhis2024_adult-summary.pdf` |
| NHIS 2021–2023 codebooks | same URL as the 2024 codebook, with `2024` replaced by `2021`, `2022`, `2023` | `docs/reference/nhis20XX_adult-codebook.pdf` |

If a CDC FTP link fails, download from that year's documentation page, for example https://www.cdc.gov/nchs/nhis/documentation/2024-nhis.html.

**Not committed:** the reference PDFs in `docs/reference/` (about 50 MB in total). Download them from the links above.

## How to run

Requirements: R ≥ 4.3 with the packages in `r-packages.txt`, and Python 3.11.

```bash
# Python environment
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
# R packages
Rscript -e 'install.packages(c("survey","haven","dplyr","readr","tidyr","purrr","jsonlite"))'

make data        # checks that the raw zips are in data/raw/
make estimates   # Rscript R/01..05: MEPS + NHIS survey-weighted estimates
make model       # trains the risk model on NHIS, validates externally on MEPS
make figures     # exports static figures for the slides
make all         # data + estimates + model + figures
make app         # streamlit run app/Home.py
```

The app reads only `data/processed/` and `models/`, which are committed, so `streamlit run app/Home.py` works without the raw data. To deploy, use Streamlit Community Cloud with main file `app/Home.py`.

## Methods summary

**Design.** Every estimate declares the complex survey design on the **full** file and subsets afterward. We never filter rows before `svydesign()`.

- MEPS: `svydesign(ids = ~VARPSU, strata = ~VARSTR, weights = ~<weight>, nest = TRUE)`, then `subset(design, breast & <weight> > 0)`.
- NHIS: four years are pooled with `wt_pool = WTFA_A / 4`, using design `ids = ~PPSU, strata = ~PSTRAT, nest = TRUE`.
- `options(survey.lonely.psu = "adjust")` is used throughout. MEPS scripts also set `survey.adjust.domain.lonely = TRUE`, as in the team script. This is a conservative domain adjustment that widens MEPS CIs; it is not standard AHRQ practice and the NHIS scripts do not use it. Point estimates do not change.

**Weights.** Each MEPS instrument has its own weight:

| Variables | Weight |
|---|---|
| Cancer SAQ items (CTRTMT42, CFN*, CDL*, CEF*, CFCARE42, CBCK42) | `CSAQW24F` |
| Experiences SAQ items (EQ*, including EQSBAS53) | `ESAQWT24F` |
| Everything else (FW financial-wellbeing items, PROBPY42, access to care, expenditures) | `PERWT24F` (HC-256 has no separate FW weight) |
| NHIS (all items) | `WTFA_A / 4` |

**Cohorts.**
- MEPS: adults (AGE24X ≥ 18) with `CABREAST == 1`, which gives 377 persons, 99 of them under 65 (370 with PERWT24F > 0: 95 under 65; 271 CSAQ respondents with CSAQW24F > 0: 60 under 65; 320 ESAQ respondents: 80 under 65).
- NHIS: adults with `BREASCAN_A == 1`, 2021–2024 pooled; n = 2,899 (831 under 65, 2,068 aged 65+; 36 men are included). Pooled weight WTFA_A/4, design PSTRAT/PPSU.

**Small-cell rule.** We compute the unweighted n behind every estimate.
- **Suppress** an estimate if its unweighted denominator is n < 30 or its numerator count is < 5.
- **Flag** it (†, interpret with caution) if n < 60 or the relative standard error is > 30%.
- No cell with fewer than 5 respondents appears in any chart, table, tooltip, or download.

**Models.** Survey-weighted logistic regression (`svyglm`, quasibinomial) of medical-bill worry:
- Model A reproduces the team's model: treatment + age per 10 years + income.
- Model B replaces age with under 65 vs 65+ (headline).
- Model C adds any private coverage vs none (only one cohort member was uninsured all year): under-65 aOR 4.34 (1.56–12.06).
- Lonely-PSU sensitivity (`meps_model_or.csv`, column `lonely_psu_method`). The ORs are identical in every run. Model B under-65 95% CI: 1.58–9.01 in the primary run (`adjust` plus domain adjustment), 1.57–9.08 with `"average"` (domain adjustment still on, so this run varies only the lonely-PSU method), and 1.75–8.16 with the domain adjustment off (`adjust_nodomain`, the AHRQ/NHIS-style setting).

**Risk tool and external validation.**
- Training: a calibrated L2 logistic regression is trained on NHIS 2021–2024 survivors to predict *problems paying medical bills in the past 12 months*, using only features both surveys share (age, income as % FPL, insurance, region, employment, self-rated health, marital status, education).
- Fairness: race/ethnicity is used only for a fairness audit, never as an input.
- External validation: the model is scored on a **different national survey**, the MEPS 2024 breast cancer cohort, with outcome PROBPY42 and weights PERWT24F. We report AUC (bootstrap CI), Brier score, and calibration (10 bins for NHIS; 5 bins of about 74 for MEPS because there are only 29 events. Observed rates are blank for bins with fewer than 5 events, which leaves 3 of the 5 MEPS bins blank, and the `flagged` column marks bins with n < 60).
- Known harmonization limit: the 65+ insurance split is not like-for-like. *Medicare + private* is 49.2% of 65+ survivors in NHIS training but 35.0% in the MEPS external set (unweighted). MEPS PRVEV24 means ever-private during 2024, while NHIS is coverage at interview, and Medigap/Medicare Advantage may be classified differently.
- Intended use: an education and screening demo only. It is not for clinical or financial decisions.

## Cohort note

The cohort is defined by **`CABREAST == 1`**, the self-reported breast cancer diagnosis in the HC-256 cancer section. The team's original extract (`team_inputs/breast_analysis.csv`, 404 rows; person-level, so kept out of the public repo) also included persons flagged by an ICD-10 C50 condition code (`breast_c50_current == 1`). In 18 of those rows, CANCERDX == 2 or CABREAST == 2, which means the person did not report a breast cancer diagnosis. These rows are not in our cohort, so some counts differ from the team's original charts.

## Limitations

- The data are cross-sectional, so these are associations, not causation.
- Outcomes are self-reported.
- The MEPS Cancer SAQ sample is small (n ≈ 260–300 survivors with a positive CSAQ weight), so CIs are wide and some cells are suppressed or flagged.
- Age is confounded with insurance and employment, so the under-65 gap is not purely a "Medicare effect". Kwon et al. (2025) provide the quasi-experimental evidence.
- The surveys differ in item wording and reference periods:
  - Insurance: MEPS measures insurance "ever during 2024", while NHIS measures coverage at interview.
  - Bill problems: MEPS PROBPY42 is family-level.
- NHIS does not release the urban–rural variable (URBRRL) in 2024, so it was dropped from the pooled file.

## Data sources and references

### Data
- **[meps_hc256]** Agency for Healthcare Research and Quality. *Medical Expenditure Panel Survey HC-256: 2024 Full Year Consolidated Data File.* Rockville, MD: AHRQ; August 2026. https://meps.ahrq.gov/mepsweb/data_stats/download_data_files_detail.jsp?cboPufNumber=HC-256
- **[meps_hc255]** Agency for Healthcare Research and Quality. *Medical Expenditure Panel Survey HC-255: 2024 Medical Conditions.* Rockville, MD: AHRQ; August 2026. https://meps.ahrq.gov/mepsweb/data_stats/download_data_files_detail.jsp?cboPufNumber=HC-255
- **[nhis_2021_2024]** National Center for Health Statistics. *National Health Interview Survey, 2021, 2022, 2023, and 2024. Sample Adult public-use data files and documentation.* Hyattsville, MD: NCHS, Centers for Disease Control and Prevention. Data years were released in mid-2022, 2023, 2024, and 2025; the Sample Adult codebooks are dated 25 July 2022 (2021), 05 June 2023 (2022), 24 June 2024 (2023), and 18 June 2025 (2024). https://www.cdc.gov/nchs/nhis/documentation/2024-nhis.html (and the 2021–2023 pages).
- **[meps_github]** AHRQ. *MEPS programming examples and quick reference guides* (GitHub: HHS-AHRQ/MEPS). https://github.com/HHS-AHRQ/MEPS. Used for variable references.

### Published statistics and literature
- **[seer_statfacts]** National Cancer Institute, Surveillance, Epidemiology, and End Results Program. *Cancer Stat Facts: Female Breast Cancer.* https://seer.cancer.gov/statfacts/html/breast.html. Accessed November 21, 2026.
- **[acs_howcommon]** American Cancer Society. *How Common Is Breast Cancer?* https://www.cancer.org/cancer/types/breast-cancer/about/how-common-is-breast-cancer.html. Accessed November 21, 2026.
- **[yabroff2016]** Yabroff KR, Dowling EC, Guy GP Jr, Banegas MP, Davidoff A, Han X, Virgo KS, McNeel TS, Chawla N, Blanch-Hartigan D, Kent EE, Li C, Rodriguez JL, de Moor JS, Zheng Z, Jemal A, Ekwueme DU. Financial hardship associated with cancer in the United States: findings from a population-based sample of adult cancer survivors. *J Clin Oncol.* 2016;34(3):259–267. doi:10.1200/JCO.2015.62.0468
- **[yabroff2022]** Yabroff KR, Han X, Song W, Zhao J, Nogueira L, Pollack CE, Jemal A, Zheng Z. Association of medical financial hardship and mortality among cancer survivors in the United States. *J Natl Cancer Inst.* 2022;114(6):863–870. doi:10.1093/jnci/djac044
- **[kwon2025]** Kwon Y, Roberts ET, Degenholtz HB, Jacobs BL, Sabik LM. Association of Medicare eligibility with access to and affordability of care among older cancer survivors. *J Cancer Surviv.* 2025;19(4):1431–1441. doi:10.1007/s11764-024-01562-x
- **[politi2021]** Politi MC, Yen RW, Elwyn G, O'Malley AJ, Saunders CH, Schubbe D, Forcino R, Durand MA. Women who are young, non-White, and with lower socioeconomic status report higher financial toxicity up to 1 year after breast cancer surgery: a mixed-effects regression analysis. *Oncologist.* 2021;26(1):e142–e152. doi:10.1002/onco.13544
- **[banegas2018]** Banegas MP, Yabroff KR, O'Keeffe-Rosetti MC, Ritzwoller DP, Fishman PA, Salloum RG, Lafata JE, Hornbrook MC. Medical care costs associated with cancer in integrated delivery systems. *J Natl Compr Canc Netw.* 2018;16(4):402–410. doi:10.6004/jnccn.2017.7065
- **[li2024]** Li L, Zhang D, Li Y, Jain M, Lin X, Hu R, Liu J, Thapa J, Mu L, Chen Z, Liu B, Pagán JA. Medical financial hardship between young adult cancer survivors and matched individuals without cancer in the United States. *JNCI Cancer Spectr.* 2024;8(2):pkae007. doi:10.1093/jncics/pkae007. This is our secondary source for the Banegas 5-year cost figures.
- **[cms_partd_2026]** Centers for Medicare & Medicaid Services. *Final CY 2026 Part D Redesign Program Instructions* (fact sheet). April 7, 2025. https://www.cms.gov/newsroom/fact-sheets/final-cy-2026-part-d-redesign-program-instructions
- **[hhs_fpl_2024]** Office of the Assistant Secretary for Planning and Evaluation, HHS. *Poverty Guidelines* (2024: $15,060 for one person plus $5,380 per additional person, 48 contiguous states and DC; 89 FR 2961, January 17, 2024). https://aspe.hhs.gov/topics/poverty-economic-mobility/poverty-guidelines

Verification notes for every cited number are in [`docs/citation_check.md`](docs/citation_check.md).

### Software
- Lumley T. *survey: analysis of complex survey samples.* R package. https://cran.r-project.org/package=survey
- R Core Team. *R: A Language and Environment for Statistical Computing.* R Foundation for Statistical Computing. https://www.R-project.org/
- Pedregosa F, et al. Scikit-learn: Machine learning in Python. *J Mach Learn Res.* 2011;12:2825–2830.
- Streamlit. https://streamlit.io
- Plotly Technologies Inc. *Plotly Python Open Source Graphing Library.* https://plotly.com/python/
- IBM Plex Sans typeface (IBM Corp.), SIL Open Font License 1.1, self-hosted in `app/static/fonts/`.

## Data use

The project uses only public-use, de-identified data. We did not attempt to re-identify anyone, and small cells are suppressed (see Methods).

## Acknowledgment

"This project uses public-use data from the Agency for Healthcare Research and Quality's Medical Expenditure Panel Survey and the National Center for Health Statistics' National Health Interview Survey. The analyses and conclusions are the authors' own and are not endorsed by AHRQ, NCHS, or CDC. Built for the 2026 Public Health Datathon (Biokind × Undergraduate Biostatistics Student Association)."

## Run the app locally

The app reads only the small aggregate files that are committed (`data/processed/`, `models/`, `app/content/`). You do **not** need to download MEPS or NHIS, or install R, to run it.

1. **Clone the repo:**
   ```bash
   git clone https://github.com/LevMarushevskyi/Ctr-Alt-Elite.git
   cd Ctr-Alt-Elite
   ```
2. **Create a Python 3.11 environment and install the requirements.** scikit-learn is pinned to 1.9.1 because the saved model was built with it.
   ```bash
   python3.11 -m venv .venv
   source .venv/bin/activate          # Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   ```
3. **Start the app:**
   ```bash
   streamlit run app/Home.py          # or: make app
   ```
4. **Open it.** Go to http://localhost:8501 if a browser tab doesn't open on its own. Use the sidebar to switch between **Findings**, **Risk Tool**, and **Methods and Sources**. Stop the server with `Ctrl+C`.

To rebuild every number from the raw data, you need R 4.x and the raw files (see "Getting the data"). Then run `make all` before starting the app.
