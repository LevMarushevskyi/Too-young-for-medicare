"""Findings: survey-weighted visualizations (BUILD_GUIDE 10.2)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import streamlit as st  # noqa: E402

from components import charts as C  # noqa: E402
from components import data as D  # noqa: E402
from components.common import page_setup, show_chart  # noqa: E402

page_setup("Findings")

est = D.load("meps_estimates.csv")
tests = D.load("meps_age_gap_tests.csv")
or_df = D.load("meps_model_or.csv")
ue = D.load("meps_unexpected_expense.csv")
curve = D.load("nhis_age_curve.csv")
nhis_gap = D.load("nhis_age_gap.csv")
ctx = D.context_stats()

# ---- sidebar
with st.sidebar:
    st.header("Filters")
    st.markdown("**Measures in the gap chart**")
    fams = [f for f in C.FAMILIES if st.checkbox(f, value=True, key=f"fam_{f}")]
    show_n = st.toggle("Show unweighted n in hover text", value=False)
    st.divider()
    st.subheader("Download processed data")
    for f in D.processed_files():
        b = D.safe_download_bytes(f)
        if b is not None:
            st.download_button(f, b, file_name=f, mime="text/csv", key=f"dl_{f}", width="stretch")
    st.caption("Aggregate estimates only; small cells are blank.")

st.title("Findings")
st.markdown("Survey-weighted estimates for adults with a breast cancer history in MEPS 2024, "
            "replicated in NHIS 2021–2024.")
st.caption("Error bars are 95% confidence intervals. † = interpret with caution (n < 60 or relative SE > 30%). "
           "Estimates from fewer than 30 respondents or 5 events are hidden.")

# 1. hero
st.header("1. The under-65 gap")
fig, cap = C.hero_dumbbell(est, tests, families=fams or None, show_n=show_n)
show_chart(fig, cap)
foot = []
pn = C.pooled_nhis(curve, "prob_pay_bills", nhis_gap)
if pn:
    foot.append(f"Replicated in NHIS 2021–2024: {pn[2].split(',')[0].lower()}, {pn[0]:.0f}% under 65 vs {pn[1]:.0f}% at 65+.")
if "yabroff2016" in ctx:
    foot.append("Earlier national data show the same pattern: " + ctx["yabroff2016"]["text"][0].lower()
                + ctx["yabroff2016"]["text"][1:] + " (Yabroff et al., 2016)")
if foot:
    st.caption(" ".join(foot))

# 2. NHIS age curve
st.header("2. Replication: the drop at 65")
measures = []
if curve is not None and not curve.empty:
    measures = list(dict.fromkeys(curve["measure"]))
col_a, col_b = st.columns([3, 1])
with col_a:
    if measures:
        labels = dict(zip(curve["measure"], curve["measure_label"]))
        m = st.selectbox("Measure", measures, format_func=lambda x: labels.get(x, x),
                         index=measures.index("prob_pay_bills") if "prob_pay_bills" in measures else 0)
        fig, cap = C.age_curve(curve, m, show_n=show_n, gap=nhis_gap)
        show_chart(fig, cap)
    else:
        st.info("NHIS age curve not available yet (data/processed/nhis_age_curve.csv).")
with col_b:
    if "kwon2025" in ctx:
        with st.container(border=True):
            st.markdown("**Published evidence (Kwon et al., 2025)**")
            st.write(ctx["kwon2025"]["text"])

# 3. forest
st.header("3. After adjusting for income and treatment")
if or_df is not None and not or_df.empty:
    models = list(dict.fromkeys(or_df["model"].astype(str)))
    default = models.index("B") if "B" in models else 0
    default = next((i for i, m_ in enumerate(models) if m_.replace("Model", "").strip() == "B"), 0)
    desc = {"A": "Age per 10 years", "B": "Under 65 vs 65+", "C": "Under 65 vs 65+, plus insurance"}
    mdl = st.radio("Model", models, index=default, horizontal=True,
                   format_func=lambda x: desc.get(x.replace("Model", "").strip(), x))
    fig, cap = C.forest(or_df, mdl)
    show_chart(fig, cap)
else:
    st.info("Model results not available yet (data/processed/meps_model_or.csv).")

# 4. income
st.header("4. Income")
fig, cap = C.income_bars(est, show_n=show_n)
show_chart(fig, cap)

# 5. unexpected expense
st.header("5. Covering an unexpected expense")
ue_by = st.radio("Compare by", ["Income", "Age group"], horizontal=True, key="ue_by")
fig, cap = C.unexpected_expense(ue, by="age" if ue_by == "Age group" else "income")
show_chart(fig, cap)

# 6. money -> missed care
st.header("6. Money worries and missed care")
fig, cap = C.care_by_worry(est, show_n=show_n)
show_chart(fig, cap)

# insurance (optional chart)
ins_id = next((c for c in ("insurance_age", "insurance") if est is not None and c in set(est["chart_id"])), None)
if ins_id:
    with st.expander("Insurance type and age"):
        ims = list(dict.fromkeys(est[est["chart_id"] == ins_id]["measure"]))
        lab = dict(zip(est["measure"], est["measure_label"]))
        im = st.selectbox("Measure", ims, format_func=lambda x: lab.get(x, x), key="ins_m")
        fig, cap = C.insurance_bars(est, im, show_n=show_n)
        show_chart(fig, cap, missing="All cells for this measure are suppressed.")

# 7. treatment
with st.expander("Current cancer treatment"):
    fig, cap = C.treatment_bars(est, show_n=show_n)
    show_chart(fig, cap)

# 8. context cards
st.header("Context from published research")
SRC = {"seer_statfacts": "NCI SEER", "acs_howcommon": "American Cancer Society", "banegas2018": "Banegas et al., 2018",
       "yabroff2022": "Yabroff et al., 2022", "cms_partd_2026": "CMS, 2026"}
keys = [("seer_prevalence", "Living with breast cancer"), ("banegas2018", "Cost of treatment"),
        ("yabroff2022", "Hardship and survival"), ("cms_partd", "Medicare drug cap")]
keys = [(k, t) for k, t in keys if k in ctx]
cols = st.columns(len(keys)) if keys else []
for col, (k, t) in zip(cols, keys):
    with col, st.container(border=True):
        st.markdown(f"**{t}**")
        st.write(ctx[k]["text"])
        st.caption(SRC.get(ctx[k]["cite"], ctx[k]["cite"]))
