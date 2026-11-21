"""Risk tool (BUILD_GUIDE 10.3). Education and screening demo only."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd  # noqa: E402
import streamlit as st  # noqa: E402

from components import charts as C  # noqa: E402
from components import data as D  # noqa: E402
from components import features as F  # noqa: E402
from components import risk as R  # noqa: E402
from components.common import page_setup, show_chart  # noqa: E402

page_setup("Risk Tool")
card = D.model_card() or {}
st.title("Financial hardship risk screen")
st.warning("**Education and screening demo only.** Not for clinical or financial decisions.", icon="⚠️")
st.markdown(f"Estimates the chance that a person with a breast cancer history reports "
            f"**{card.get('outcome', 'problems paying medical bills in the past 12 months').lower()}**. "
            "Trained on NHIS 2021–2024 and tested on MEPS 2024.")

model, err = D.risk_model()
if model is None:
    st.warning(err + " Run `make model` to build it.")

# ---- inputs
age = st.slider("Age", 18, 85, 50)
with st.form("inputs"):
    c1, c2 = st.columns(2)
    with c1:
        ins_opts = F.insurance_options(age)
        insurance = st.selectbox("Insurance" + (" (under 65)" if age < 65 else " (65+, Medicare)"), ins_opts,
                                 format_func=F.label)
        mode = st.radio("Household income", ["Enter income and household size", "Choose a band"], horizontal=True)
        income = st.number_input("Annual household income ($)", 0, 2_000_000, 40_000, step=1_000)
        hh = st.number_input("Household size", 1, 12, 2)
        band_direct = st.selectbox("Income band", F.FPL_BANDS, index=2, format_func=F.label)
    with c2:
        region = st.selectbox("Region", F.REGIONS, format_func=F.label)
        employed = st.checkbox("Currently employed", value=True)
        hfp = st.checkbox("Self-rated health is fair or poor")
        married = st.checkbox("Married", value=True)
        college = st.checkbox("College degree (bachelor's or higher)")
        whatif = st.toggle("What if: same person at 65 with Medicare + private coverage", value=True)
    submitted = st.form_submit_button("Estimate risk", type="primary")

if mode.startswith("Enter"):
    pct = F.fpl_pct(income, hh)
    fpl_band = F.fpl_band_from_pct(pct)
    st.caption(f"Income is {pct:.0f}% of the 2024 HHS poverty guideline for a household of {hh} "
               f"(${F.FPL_2024_BASE + F.FPL_2024_PER_PERSON * (hh - 1):,}; 48 contiguous states and DC) "
               f"→ band: {F.label(fpl_band)}.")
else:
    fpl_band = band_direct

row = F.make_row(age, insurance, fpl_band, region, employed, hfp, married, college)


def _avg_for_age(under65: bool):
    ag = D.load("ml_age_group_avg.csv")  # ML lane: age_group,mean_pred,obs_rate,n_unweighted (NHIS)
    if ag is not None and len(ag) and "age_group" in ag:
        hit = ag[ag["age_group"].astype(str).map(C._is_u65) == under65]
        if len(hit) and pd.notna(hit["mean_pred"].iloc[0]):
            return float(hit["mean_pred"].iloc[0])
    mt = D.load("ml_metrics.csv")
    if mt is None or mt.empty:
        return None
    d = mt[(mt["dataset"] == "nhis_cv") & mt["metric"].isin(["prevalence_pred", "prevalence_obs"])].copy()
    sg = d["subgroup"].fillna("").astype(str).str.lower()

    def is_u(s):
        return ("under" in s or "<65" in s or "u65" in s or "18-64" in s or "under65=1" in s) and "not" not in s

    def is_o(s):
        return ("65+" in s or "65 and" in s or "65plus" in s or "over" in s or ">=65" in s) and not is_u(s)

    d = d[sg.map(is_u if under65 else is_o)]
    for m in ("prevalence_pred", "prevalence_obs"):
        v = d[d["metric"] == m]["value"]
        if len(v) and pd.notna(v.iloc[0]):
            return float(v.iloc[0])
    return None


def _tier(p):
    t = card.get("risk_tiers") or {}
    lo, mo = t.get("low_max"), t.get("moderate_max")
    if lo is None or mo is None:
        return None, None
    if p <= lo:
        return "Low", "#2E7D32"
    if p <= mo:
        return "Moderate", "#E69F00"
    return "High", C.ACCENT


if model is not None:
    try:
        p = R.predict(model, row)
    except Exception as e:  # noqa: BLE001
        st.error(f"The model could not score this input ({type(e).__name__}: {e}).")
        p = None
    if p is not None:
        p_alt = None
        alt_row = None
        if whatif:
            alt_ins = "medicare_plus_private" if "medicare_plus_private" in F.INS_65 else F.INS_65[0]
            alt_row = F.make_row(65, alt_ins, fpl_band, region, employed, hfp, married, college)
            try:
                p_alt = R.predict(model, alt_row)
            except Exception:  # noqa: BLE001
                p_alt = None
        st.divider()
        o1, o2 = st.columns([1, 2])
        with o1:
            st.metric("Estimated risk", f"{p * 100:.0f}%")
            tier, color = _tier(p)
            if tier:
                st.markdown(f"<span style='background:{color};color:white;padding:4px 12px;border-radius:12px;"
                            f"font-weight:600'>{tier} risk</span>", unsafe_allow_html=True)
                st.caption("Tiers split the training population into thirds by predicted risk.")
            if p_alt is not None:
                st.metric("Same person at 65, Medicare + private", f"{p_alt * 100:.0f}%",
                          delta=f"{(p_alt - p) * 100:+.0f} points", delta_color="inverse")
        with o2:
            agl = "Under 65" if age < 65 else "65+"
            st.plotly_chart(C.risk_compare(p, _avg_for_age(age < 65), agl, p_alt, "Same person at 65, Medicare + private"),
                            width="stretch", config={"displaylogo": False})

        st.subheader("What drives this estimate")
        contribs = R.contributions(D.logit_explain(), row)
        if contribs:
            st.markdown("Compared with an average survivor in the training data:")
            for f_, c_ in contribs[:3]:
                st.markdown("- " + R.plain_words(f_, c_, row))
            st.plotly_chart(C.contributions_bar([(F.label(f_), c_) for f_, c_ in contribs[:6]]),
                            width="stretch", config={"displaylogo": False})
            st.caption("Each bar shows how far this answer moves the estimate from an average survivor "
                       "(log-odds scale). Associations, not causes.")
        else:
            st.info("Factor explanations are not available (models/logit_explain.json missing).")

        st.subheader("Next steps")
        st.markdown("- Ask your cancer center whether it has a **financial navigator** or financial counselor.\n"
                    "- Check your **employer benefits** (HR or benefits office) for coverage details, "
                    "employee assistance programs and leave options.\n"
                    "- Ask your care team before skipping or delaying care or prescriptions because of cost.")

# ---- performance
with st.expander("Model performance"):
    mt = D.load("ml_metrics.csv")
    met = card.get("metrics") or {}
    k1, k2, k3, k4 = st.columns(4)

    def _m(ds, name, fallback):
        r = D.metric(mt, ds, name)
        if r is not None and pd.notna(r.get("value")):
            return r
        return {"value": fallback} if fallback is not None else None

    for col, ds, name, lab, fb in ((k1, "nhis_cv", "auc", "NHIS CV AUC", met.get("nhis_cv_auc")),
                                   (k2, "nhis_cv", "brier", "NHIS CV Brier", met.get("nhis_cv_brier")),
                                   (k3, "meps_external", "auc", "MEPS external AUC", met.get("meps_auc")),
                                   (k4, "meps_external", "brier", "MEPS external Brier", met.get("meps_brier"))):
        r = _m(ds, name, fb)
        with col:
            if r is None:
                st.metric(lab, "pending")
            else:
                ci = ""
                if pd.notna(r.get("ci_lo", None)) and pd.notna(r.get("ci_hi", None)) and r.get("ci_lo") is not None:
                    ci = (f"fold range ±1 SD {r['ci_lo']:.2f}–{r['ci_hi']:.2f}" if ds == "nhis_cv"
                          else f"bootstrap 95% CI {r['ci_lo']:.2f}–{r['ci_hi']:.2f}")
                st.metric(lab, f"{float(r['value']):.3f}", delta=ci or None, delta_color="off")
    ev = card.get("external_events")
    st.caption(f"Calibrated logistic regression · trained on NHIS (n = {card.get('train_n', 'n/a')}) · "
               f"tested on MEPS 2024 (n = {card.get('external_n', 'n/a')}" + (f", {ev} events" if ev else "") + "). "
               "With few MEPS events the external CI is wide, so the two AUCs are not meaningfully different.")
    fig, cap = C.calibration(D.load("ml_calibration.csv"))
    show_chart(fig, cap, missing="Calibration table not available yet (ml_calibration.csv).")
    if mt is not None and "subgroup" in mt.columns:
        sub = mt[mt["subgroup"].fillna("").astype(str).str.strip() != ""]
        if len(sub):
            st.markdown("**Subgroup performance** (groups with n < 50 or fewer than 5 events are hidden)")
            sub = sub.copy()
            if "model" in sub and sub["model"].nunique() > 1:
                mn = sub["model"].astype(str).str.lower()
                sub = sub[mn.str.contains("calibrated") & ~mn.str.contains("uncalibrated")] if (mn.str.contains("calibrated") & ~mn.str.contains("uncalibrated")).any() else sub
            sub["value"] = pd.to_numeric(sub["value"], errors="coerce")
            tbl = sub.pivot_table(index=["dataset", "subgroup"], columns="metric", values="value",
                                  aggfunc="first", dropna=False)
            st.dataframe(tbl.round(3), width="stretch")
    fig, cap = C.importance(D.load("ml_importance.csv"))
    show_chart(fig, cap, missing="Feature importance not available yet (ml_importance.csv).")
