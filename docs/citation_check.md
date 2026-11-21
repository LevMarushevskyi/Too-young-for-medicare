# Citation and statistics check

Checked November 21, 2026. Bibliographic metadata comes from Crossref (`api.crossref.org/works/<doi>`) and abstracts or full text from Europe PMC / PMC. Status meanings:

- **Verified**: matches the source.
- **Corrected**: the source says something different. The proposed fix is listed here, and `app/content/context_stats.yaml` has **not** been edited.
- **Could not verify**: the source wasn't reachable or doesn't contain the claim.

## Summary of proposed corrections (lead decides)

| Item | Currently in `context_stats.yaml` | Live source today | Proposal |
|---|---|---|---|
| `seer_prevalence` | 4,091,181 women living with female breast cancer in 2022 | SEER Stat Facts now reports **4,238,585 in 2023** | Either update to the 2023 figure, or keep 2022 and add "(SEER, 2025 release)". The old figure was correct for the earlier release. |
| `seer_new_cases` | 316,950 new cases in 2025 | SEER Stat Facts now reports **321,910 estimated new cases in 2026** | Same choice as above. 316,950 was SEER's 2025 estimate. |
| `banegas2018` | "$198,400 ... vs $116,800" | Figures appear in Li 2024 as a citation of Banegas. The Banegas abstract says costs are in **2015 US dollars**. | Optionally add "(2015 dollars)". Cite as "Banegas 2018, as reported in Li 2024". |

All other numbers check out as written.

## Literature

| Key | Status | Notes | Source |
|---|---|---|---|
| yabroff2016 | **Verified** | J Clin Oncol 2016;34(3):259–267, doi:10.1200/JCO.2015.62.0468. Full author list: Yabroff KR, Dowling EC, Guy GP Jr, Banegas MP, Davidoff A, Han X, Virgo KS, McNeel TS, Chawla N, Blanch-Hartigan D, Kent EE, Li C, Rodriguez JL, de Moor JS, Zheng Z, Jemal A, Ekwueme DU. The abstract confirms material hardship of 28.4% vs 13.8% and psychological hardship of 31.9% vs 14.7% (ages 18–64 vs 65+). Note: the data source is the **2011 MEPS Experiences with Cancer** supplement, not NHIS. | https://doi.org/10.1200/JCO.2015.62.0468 ; PMID 26644532 |
| yabroff2022 | **Verified** | J Natl Cancer Inst 2022;114(6):863–870, doi:10.1093/jnci/djac044. Authors: Yabroff KR, Han X, Song W, Zhao J, Nogueira L, Pollack CE, Jemal A, Zheng Z. The title supports "hardship associated with mortality". | https://doi.org/10.1093/jnci/djac044 |
| kwon2025 | **Verified** | J Cancer Surviv 2025;19(4):1431–1441 (published online March 2024), doi:10.1007/s11764-024-01562-x. Authors as listed. The abstract confirms Medicare coverage of 8.3% at 64 vs 98.2% at 65, worry about paying medical bills −7.7 pp (95% CI −12.0, −3.2), and delayed/skipped care due to cost −5.7 pp (−8.1, −3.3). The data are NHIS 2006–2018, ages 50–80, regression discontinuity. The study also found problems paying bills of −3.2 pp. | https://doi.org/10.1007/s11764-024-01562-x ; PMID 38520599 |
| politi2021 | **Verified** | Oncologist 2021;26(1):e142–e152 (published online October 2020), doi:10.1002/onco.13544. The author list matches. The full text confirms that patients 65+ scored 2.58 points lower in financial toxicity than those under 65 (95% CI −3.41, −1.74). | https://doi.org/10.1002/onco.13544 ; PMC7794185 |
| banegas2018 | **Verified (bibliographic) / secondary for numbers** | J Natl Compr Canc Netw 2018;16(4):402–410, doi:10.6004/jnccn.2017.7065. Authors: Banegas MP, Yabroff KR, O'Keeffe-Rosetti MC, Ritzwoller DP, Fishman PA, Salloum RG, Lafata JE, Hornbrook MC. The primary cost table could not be opened (PMC returned a CAPTCHA). The figures $198,400 (<65) and $116,800 (65+) over 5 years are confirmed verbatim in Li 2024, which cites Banegas. The costs are in 2015 USD according to the Banegas abstract. | https://doi.org/10.6004/jnccn.2017.7065 ; PMID 29632060 |
| li2024 | **Verified** | JNCI Cancer Spectr 2024;8(2):pkae007, doi:10.1093/jncics/pkae007. Authors: Li L, Zhang D, Li Y, Jain M, Lin X, Hu R, Liu J, Thapa J, Mu L, Chen Z, Liu B, Pagán JA. It contains the Banegas sentence quoted above. | https://doi.org/10.1093/jncics/pkae007 ; PMC10903972 |

## Published statistics

| Key | Status | Notes | Source |
|---|---|---|---|
| seer_prevalence (4,091,181 in 2022) | **Corrected (outdated)** | The live page now reads: "In 2023, there were an estimated 4,238,585 women living with female breast cancer in the United States." Search-engine snapshots of the earlier release show 4,091,181 for 2022. | https://seer.cancer.gov/statfacts/html/breast.html |
| seer_new_cases (316,950 in 2025) | **Corrected (outdated)** | The live page now reads: "In 2026, it is estimated that there will be 321,910 new cases of female breast cancer." 316,950 was the 2025 estimate. SEER also lists a median age at diagnosis of 64 (SEER 21, 2019–2023). | https://seer.cancer.gov/statfacts/html/breast.html |
| acs_howcommon (median age 63) | **Verified** | "The median age at the time of breast cancer diagnosis is 63." ACS's 2026 estimate is about 321,910 new invasive cases. | https://www.cancer.org/cancer/types/breast-cancer/about/how-common-is-breast-cancer.html |
| cms_partd_2026 ($2,100) | **Verified** | The CY 2026 annual out-of-pocket threshold is $2,100. The fact sheet was released April 7, 2025. | https://www.cms.gov/newsroom/fact-sheets/final-cy-2026-part-d-redesign-program-instructions |
| hhs_fpl_2024 ($15,060 + $5,380) | **Verified** | 48 contiguous states + DC: $15,060 for 1 person, plus $5,380 for each additional person. Published in 89 FR 2961, January 17, 2024. The ASPE page returned HTTP 502, so the Federal Register text was used. | https://www.federalregister.gov/documents/2024/01/17/2024-00796/annual-update-of-the-hhs-poverty-guidelines |

## Data release dates

| Item | Status | Date | Source |
|---|---|---|---|
| MEPS HC-256 | **Verified** | August 2026. Title: "MEPS HC-256: 2024 Full Year Consolidated Data File" | https://meps.ahrq.gov/mepsweb/data_stats/download_data_files_detail.jsp?cboPufNumber=HC-256 |
| NHIS 2021 | **Verified (codebook)** | Codebook dated 25 July 2022. FTP `adult21csv.zip` timestamp 7/29/2022. | ftp.cdc.gov/pub/Health_Statistics/NCHS/Datasets/NHIS/2021/ |
| NHIS 2022 | **Verified (codebook)** | Codebook version 05 June 2023. FTP files dated 6/26/2023. | ftp.cdc.gov/pub/Health_Statistics/NCHS/Datasets/NHIS/2022/ |
| NHIS 2023 | **Verified (codebook)** | Codebook dated 24 June 2024. FTP `adult23.zip` 6/20/2024; CSV re-posted 7/17/2024. | ftp.cdc.gov/pub/Health_Statistics/NCHS/Datasets/NHIS/2023/ |
| NHIS 2024 | **Verified (codebook)** | Codebook version 18 June 2025. FTP files dated 6/30/2025. The documentation page itself shows no explicit release date. | https://www.cdc.gov/nchs/nhis/documentation/2024-nhis.html |

These dates come from the codebook cover pages and FTP timestamps. NCHS documentation pages don't state a single "release date", so the README uses "released mid-2022/2023/2024/2025, codebook dated ..." wording.
