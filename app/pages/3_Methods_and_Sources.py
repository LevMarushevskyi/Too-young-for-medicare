"""Methods and sources (BUILD_GUIDE 10.4)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd  # noqa: E402
import streamlit as st  # noqa: E402

from components import data as D  # noqa: E402
from components.common import page_setup  # noqa: E402

page_setup("Methods")
st.title("Methods and sources")

st.header("Data sources")
st.dataframe(pd.DataFrame([
    {"Source": "MEPS HC-256 (AHRQ)", "Years": "2024", "Role": "Primary: all findings charts, regression, external validation of the risk model",
     "Link": "https://meps.ahrq.gov/mepsweb/data_stats/download_data_files_detail.jsp?cboPufNumber=HC-256"},
    {"Source": "NHIS Sample Adult (CDC/NCHS)", "Years": "2021–2024 pooled", "Role": "Supplement: age curve; ML training data",
     "Link": "https://www.cdc.gov/nchs/nhis/documentation/2024-nhis.html"},
    {"Source": "Published literature, SEER, ACS, CMS", "Years": "n/a", "Role": "Context (cited below)",
     "Link": None},
]), hide_index=True, width="stretch",
    column_config={"Link": st.column_config.LinkColumn("Link")})

st.header("Survey design and weights")
st.markdown(
    "- **Design first, then subset.** Each estimate declares the design on the full MEPS file "
    "(`svydesign(ids = ~VARPSU, strata = ~VARSTR, weights = ~<weight>, nest = TRUE)`), then subsets to the cohort; "
    "`survey.lonely.psu = \"adjust\"`.\n"
    "- **Conservative domain adjustment.** MEPS estimates also set `survey.adjust.domain.lonely = TRUE` (as in the "
    "team's script). It widens CIs but does not move point estimates; with it off, the Model B under-65 CI is "
    "1.75–8.16 instead of 1.58–9.01.\n"
    "- **Age-gap tests.** `p_value` is the Rao-Scott chi-square; `p_wald` tests the difference and matches the CI shown. "
    "Problems paying bills (p_wald 0.074) and cost-related delayed care (0.10) are borderline, not significant.")
st.dataframe(pd.DataFrame([
    {"Items": "Cancer SAQ (CTRTMT42, CFN*, CDL*, CEF*, CFCARE42, CBCK42)", "Weight": "CSAQW24F"},
    {"Items": "Experiences with care SAQ (EQ*, incl. EQSBAS53)", "Weight": "ESAQWT24F"},
    {"Items": "Everything else (FW items, PROBPY42, access to care, expenditures)",
     "Weight": "PERWT24F (HC-256 has no separate financial-wellbeing weight)"},
]), hide_index=True, width="stretch")
st.markdown("NHIS: four years stacked, pooled weight `WTFA_A / 4`, design `ids = ~PPSU, strata = ~PSTRAT`, "
            "cohort subset after declaring the design.")

st.header("Small-cell rule")
st.markdown("- **Hidden** everywhere (charts, tooltips, downloads) if the unweighted denominator is under 30 "
            "or fewer than 5 respondents had the outcome.\n"
            "- **Flagged** (faded, marked †) if n < 60 or the relative standard error is over 30%.")

st.header("Cohorts")
card = D.model_card() or {}
st.markdown(
    "- **MEPS 2024:** adults (AGE24X ≥ 18) with CABREAST = 1 (ever told they had breast cancer), "
    "rather than the team's original `breast_c50_current` flag.\n"
    "- **NHIS 2021–2024:** adults with BREASCAN_A = 1 (ever told breast cancer), four years pooled. "
    f"ML training n = {card.get('train_n', 'pending')}"
    + (f" ({card.get('train_events')} with problems paying bills)" if card.get("train_events") else "") + "."
)
mc = D.safe_df("meps_cohort_counts.csv")
if mc is not None and len(mc):
    st.markdown("**MEPS cohort counts**")
    st.dataframe(mc, hide_index=True, width="stretch")
nc = D.safe_df("nhis_cohort_counts.csv")
if nc is not None and len(nc):
    st.markdown("**NHIS cohort counts by year**")
    st.dataframe(nc, hide_index=True, width="stretch")
tr = D.safe_df("meps_team_reproduction.csv")
if tr is not None and len(tr):
    with st.expander("Reproducing the team's original numbers"):
        st.dataframe(tr, hide_index=True, width="stretch")

st.header("Risk model")
if card:
    st.markdown(f"**{card.get('name', '')}**  \n"
                f"Outcome: {card.get('outcome', '')}  \n"
                f"Training data: {card.get('train_data', '')}  \n"
                f"External test: {card.get('external_data', '')} (n = {card.get('external_n', 'n/a')})  \n"
                f"Model: {card.get('model', '')}  \n"
                f"Features: {', '.join(card.get('features', []))}")
    met = card.get("metrics") or {}
    if met:
        st.dataframe(pd.DataFrame([{"metric": k, "value": str(v)} for k, v in met.items()]), hide_index=True)
    st.caption("Education and screening demo only; not for clinical or financial decisions.")
else:
    st.info("Model card not available yet (models/model_card.json).")
st.markdown("**Survey differences.**\n"
            "- MEPS insurance is “ever during 2024”; NHIS is coverage at interview. *Medicare + private* is 49.2% of 65+ "
            "survivors in NHIS but 35.0% in MEPS (unweighted).\n"
            "- Years since diagnosis and high-deductible plan exist only in NHIS, so they are left out of the model.\n"
            "- Race/ethnicity is not a model input; it is used only to check performance by subgroup.")

st.header("Limitations")
st.markdown("- Cross-sectional data: associations, not causation.\n"
            "- Self-reported outcomes.\n"
            "- Small MEPS samples (cancer questionnaire n ≈ 260), so confidence intervals are wide.\n"
            "- Age is entangled with insurance and employment.\n"
            "- MEPS and NHIS differ in item wording, reference periods and outcome level (person vs family).")

st.header("References")
ctx = D.context_stats()
REFS = {
    "meps_hc256": "Agency for Healthcare Research and Quality. *Medical Expenditure Panel Survey HC-256: 2024 Full Year Consolidated Data File.* Rockville, MD: AHRQ; August 2026. https://meps.ahrq.gov/mepsweb/data_stats/download_data_files_detail.jsp?cboPufNumber=HC-256",
    "nhis_2021_2024": "National Center for Health Statistics. *National Health Interview Survey, 2021, 2022, 2023, and 2024. Sample Adult public-use data files and documentation.* Hyattsville, MD: NCHS, CDC. https://www.cdc.gov/nchs/nhis/documentation/2024-nhis.html",
    "meps_github": "AHRQ. *MEPS programming examples and quick reference guides* (GitHub: HHS-AHRQ/MEPS).",
    "seer_statfacts": "National Cancer Institute, SEER Program. *Cancer Stat Facts: Female Breast Cancer.* https://seer.cancer.gov/statfacts/html/breast.html. Accessed November 21, 2026.",
    "acs_howcommon": "American Cancer Society. *How Common Is Breast Cancer?* https://www.cancer.org/cancer/types/breast-cancer/about/how-common-is-breast-cancer.html. Accessed November 21, 2026.",
    "yabroff2016": "Yabroff KR, Dowling EC, Guy GP Jr, et al. Financial hardship associated with cancer in the United States: findings from a population-based sample of adult cancer survivors. *J Clin Oncol.* 2016;34(3):259–267. doi:10.1200/JCO.2015.62.0468",
    "yabroff2022": "Yabroff KR, et al. Association of medical financial hardship and mortality among cancer survivors in the United States. *J Natl Cancer Inst.* 2022;114(6):863–870. doi:10.1093/jnci/djac044",
    "kwon2025": "Kwon Y, Roberts ET, Degenholtz HB, Jacobs BL, Sabik LM. Association of Medicare eligibility with access to and affordability of care among older cancer survivors. *J Cancer Surviv.* 2025;19(4):1431–1441. doi:10.1007/s11764-024-01562-x",
    "politi2021": "Politi MC, Yen RW, Elwyn G, et al. Women who are young, non-White, and with lower socioeconomic status report higher financial toxicity up to 1 year after breast cancer surgery. *Oncologist.* 2021;26(1):e142–e152. doi:10.1002/onco.13544",
    "banegas2018": "Banegas MP, Yabroff KR, O'Keeffe-Rosetti MC, et al. Medical care costs associated with cancer in integrated delivery systems. *J Natl Compr Canc Netw.* 2018;16(4):402–410. doi:10.6004/jnccn.2017.7065",
    "li2024": "Li L, Zhang D, Li Y, et al. Medical financial hardship between young adult cancer survivors and matched individuals without cancer in the United States. *JNCI Cancer Spectr.* 2024;8(2):pkae007. doi:10.1093/jncics/pkae007",
    "cms_partd_2026": "Centers for Medicare & Medicaid Services. *Final CY 2026 Part D Redesign Program Instructions* (fact sheet). https://www.cms.gov/newsroom/fact-sheets/final-cy-2026-part-d-redesign-program-instructions",
    "hhs_fpl_2024": "Office of the Assistant Secretary for Planning and Evaluation, HHS. *2024 Poverty Guidelines* (risk-tool income bands). https://aspe.hhs.gov/topics/poverty-economic-mobility/poverty-guidelines",
}
st.markdown("\n".join(f"{i}. {v}" for i, v in enumerate(REFS.values(), 1)))
st.markdown("**Software:** R `survey` (Lumley); R Core Team, *R*; scikit-learn (Pedregosa et al., JMLR 2011;12:2825–2830); "
            "Streamlit; Plotly.")

st.header("Data use")
st.markdown("All data are public-use and de-identified. Following the MEPS and NHIS data use agreements, we made no "
            "attempt to identify individuals and hide small cells. The analyses and conclusions are the authors' own "
            "and are not endorsed by AHRQ, NCHS, or CDC.")
