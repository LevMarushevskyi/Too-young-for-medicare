"""Too Young for Medicare: home page.  Run: streamlit run app/Home.py"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import pandas as pd  # noqa: E402
import streamlit as st  # noqa: E402

from components import data as D  # noqa: E402
from components.common import age_gap_pair, external_auc, model_age_term, page_setup  # noqa: E402

page_setup("Home")

st.title("Too Young for Medicare")
st.markdown(
    "#### Breast cancer survivors under 65, not yet eligible for Medicare, report far more financial "
    "hardship than survivors 65 and older."
)

est = D.load("meps_estimates.csv")
or_df = D.load("meps_model_or.csv")

c1, c2, c3 = st.columns(3)
pair = age_gap_pair(est, "any_csaq_strain") or age_gap_pair(est, "worry_bills")
with c1:
    if pair:
        u, o = pair
        st.metric(f"{u['measure_label']}: under 65 vs 65+", f"{u['pct']:.0f}% vs {o['pct']:.0f}%",
                  delta=f"{u['pct'] - o['pct']:+.0f} pp gap", delta_color="off")
        st.caption("MEPS 2024, survey-weighted")
    else:
        st.metric("Any financial strain: under 65 vs 65+", "pending")
with c2:
    t = model_age_term(or_df, "B")
    if t is not None:
        st.metric(f"Adjusted odds ratio: {t['term_label']}", f"{t['or']:.1f}",
                  delta=f"95% CI {t['ci_lo']:.1f}–{t['ci_hi']:.1f}", delta_color="off")
        st.caption("Odds of worrying about medical bills, adjusted for treatment and income")
    else:
        st.metric("Adjusted OR, under 65 (Model B)", "pending")
with c3:
    a = external_auc()
    if a:
        ci = f"95% CI {a[1]:.2f}–{a[2]:.2f}" if a[1] is not None and pd.notna(a[1]) and a[2] is not None and pd.notna(a[2]) else "point estimate"
        st.metric("Risk tool accuracy (AUC) on MEPS 2024", f"{a[0]:.2f}", delta=ci, delta_color="off")
        st.caption("Trained on a different survey (NHIS 2021–2024); 0.5 = coin flip, 1.0 = perfect")
    else:
        st.metric("Risk tool external AUC (MEPS 2024)", "pending")

ctx = D.context_stats()
lines = [ctx[k]["text"] for k in ("acs_median_age", "seer_new_cases") if k in ctx]
if lines:
    st.info(" ".join(lines) + "  \n*Sources: American Cancer Society; NCI SEER.*")

with st.container(border=True):
    st.subheader("Who this is for")
    st.markdown(
        "**Audience:** cancer center leadership and oncology financial navigators, plus employers and "
        "benefits teams who insure working-age patients.\n\n"
        "**Call to action:** screen every breast cancer patient under 65 for financial hardship at diagnosis, "
        "with a short screen like the one in this app, and route high-risk patients to financial "
        "navigation *before* the bills arrive."
    )

st.subheader("Explore")
l1, l2, l3 = st.columns(3)
with l1:
    st.page_link("pages/1_Findings.py", label="Findings: the under-65 gap", icon="📊")
with l2:
    st.page_link("pages/2_Risk_Tool.py", label="Risk tool", icon="🧮")
with l3:
    st.page_link("pages/3_Methods_and_Sources.py", label="Methods and sources", icon="📚")

