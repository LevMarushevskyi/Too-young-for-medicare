"""Write MOCK processed CSVs (BUILD_GUIDE section 6 schemas) for app development.

MOCK DATA ONLY. Numbers are invented to exercise the app (including suppressed
and flagged rows). Never copy these into data/processed/.

    .venv/bin/python app/dev/make_mock_data.py
    TYFM_DATA_DIR=app/dev/mock_processed TYFM_MODELS_DIR=app/dev/mock_models \
        .venv/bin/streamlit run app/Home.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
OUT = HERE / "mock_processed"
MOUT = HERE / "mock_models"
rng = np.random.default_rng(7)

EST_COLS = ["source", "chart_id", "measure", "measure_label", "group_var", "group", "pct",
            "ci_lo", "ci_hi", "n_unweighted", "n_events", "rse", "suppressed", "flagged",
            "weight_var", "universe_note"]

MEASURES = {
    # measure: (label, weight, universe, under65 pct, 65+ pct)
    "any_csaq_strain": ("Any cancer-related financial strain", "CSAQW24F", "CSAQ respondents", 52, 19),
    "worry_bills": ("Worried about paying medical bills", "CSAQW24F", "CSAQ respondents", 42, 18),
    "fam_stability_worry": ("Worried about family financial stability", "CSAQW24F", "CSAQ respondents", 35, 12),
    "borrowed_debt": ("Borrowed money or went into debt", "CSAQW24F", "CSAQ respondents", 15, 2),
    "debt_collector": ("Contacted by a debt collector", "PERWT24F", "All adults", 14, 4),
    "missed_payment": ("Missed a credit card or loan payment", "PERWT24F", "All adults", 12, 3),
    "late_rent": ("Late on rent or mortgage", "PERWT24F", "All adults", 9, 2),
    "late_util": ("Late on utility bills", "PERWT24F", "All adults", 13, 4),
    "any_fw_strain": ("Any family financial-wellbeing strain", "PERWT24F", "All adults", 27, 8),
    "prob_pay_bills": ("Family had problems paying medical bills", "PERWT24F", "All adults", 22, 9),
    "delay_or_forgo_care_cost": ("Delayed or skipped care due to cost", "PERWT24F", "Access supplement eligible", 11, 5),
    "delay_or_forgo_rx_cost": ("Delayed or skipped prescriptions due to cost", "PERWT24F", "Access supplement eligible", 8, 3),
    "sacrificed_basics": ("Sacrificed basics to pay for care", "ESAQWT24F", "ESAQ respondents", 10, 4),
    "high_oop_burden": ("Out-of-pocket costs >= 10% of family income", "PERWT24F", "All adults", 12, 15),
}


def est_row(chart_id, measure, label, group_var, group, p, n, weight, universe):
    events = int(round(n * p / 100))
    se = np.sqrt(max(p * (100 - p), 1) / max(n, 1)) * 1.4
    rse = se / p if p > 0 else np.nan
    suppressed = n < 30 or events < 5
    flagged = (not suppressed) and (n < 60 or rse > 0.30)
    lo, hi = max(0.0, p - 1.96 * se), min(100.0, p + 1.96 * se)
    return dict(source="MEPS 2024", chart_id=chart_id, measure=measure, measure_label=label,
                group_var=group_var, group=group,
                pct=np.nan if suppressed else round(p, 1), ci_lo=np.nan if suppressed else round(lo, 1),
                ci_hi=np.nan if suppressed else round(hi, 1), n_unweighted=n, n_events=events,
                rse=np.nan if suppressed else round(rse, 3), suppressed=suppressed, flagged=flagged,
                weight_var=weight, universe_note=f"Adults with breast cancer, {universe} (MOCK)")


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    rows, tests = [], []
    for m, (lab, w, uni, pu, po) in MEASURES.items():
        nu = 70 if w == "CSAQW24F" else 95
        no = 190 if w == "CSAQW24F" else 260
        if m == "late_rent":
            nu = 55  # -> flagged under 65
        rows.append(est_row("age_gap", m, lab, "age_grp", "Under 65", pu, nu, w, uni))
        rows.append(est_row("age_gap", m, lab, "age_grp", "65+", po, no, w, uni))
        d = pu - po
        tests.append(dict(measure=m, diff_pp=d, diff_lo=d - 12, diff_hi=d + 12,
                          p_value=0.001 if abs(d) > 12 else 0.2, test="svychisq (Rao-Scott F)"))
    inc = [("Lower (<200% FPL)", 1.4, 110), ("Middle (200-399%)", 0.8, 90), ("High (400%+)", 0.9, 120)]
    for m in ["worry_bills", "any_fw_strain", "prob_pay_bills", "high_oop_burden"]:
        lab, w, uni, pu, po = MEASURES[m]
        for g, mult, n in inc:
            rows.append(est_row("income", m, lab, "inc3", g, (pu + po) / 2 * mult, n, w, uni))
    ins = [("Under 65: any private", 60), ("Under 65: public only", 32), ("Under 65: uninsured", 7),
           ("65+: Medicare + private", 140), ("65+: Medicare only", 70), ("65+: Medicare + Medicaid", 40)]
    for m in ["worry_bills", "prob_pay_bills"]:
        lab, w, uni, pu, po = MEASURES[m]
        for g, n in ins:
            rows.append(est_row("insurance", m, lab, "ins_cat", g, pu if g.startswith("Under") else po, n, w, uni))
    for m in ["worry_bills", "fam_stability_worry", "borrowed_debt", "any_csaq_strain"]:
        lab, w, uni, pu, po = MEASURES[m]
        rows.append(est_row("treatment", m, lab, "treated", "Currently treated", pu * 0.9, 45, w, uni))
        rows.append(est_row("treatment", m, lab, "treated", "Not currently treated", po * 1.2, 215, w, uni))
    for m in ["delay_or_forgo_rx_cost", "delay_or_forgo_care_cost"]:
        lab, w, uni, pu, po = MEASURES[m]
        rows.append(est_row("care_by_worry", m, lab, "worry_bills", "Worried about bills", 11.8 if "rx" in m else 15, 75, w, uni))
        rows.append(est_row("care_by_worry", m, lab, "worry_bills", "Not worried", 1.9 if "rx" in m else 4, 180, w, uni))
    est = pd.DataFrame(rows)[EST_COLS]
    est.to_csv(OUT / "meps_estimates.csv", index=False)
    pd.DataFrame(tests).to_csv(OUT / "meps_age_gap_tests.csv", index=False)

    orr = []
    for model, agevar in [("A", [("age10", "Age (per 10 years)", 0.54, 0.36, 0.81)]),
                          ("B", [("age_grpUnder 65", "Under 65 (vs 65+)", 2.9, 1.4, 6.0)])]:
        terms = agevar + [("treatedTRUE", "Currently treated", 1.5, 0.54, 4.2),
                          ("inc3Lower (<200% FPL)", "Lower income (vs high)", 2.98, 1.15, 7.73),
                          ("inc3Middle (200-399%)", "Middle income (vs high)", 0.8, 0.3, 2.1)]
        for t, tl, o, lo, hi in terms:
            orr.append(dict(model=model, term=t, term_label=tl, **{"or": o}, ci_lo=lo, ci_hi=hi,
                            p_value=0.01, n=260, n_events=70, lonely_psu_method="adjust"))
    pd.DataFrame(orr).to_csv(OUT / "meps_model_or.csv", index=False)

    ue = []
    labels = {1: "Not at all confident", 2: "Not too confident", 3: "Somewhat confident", 4: "Very confident"}
    dists = {"Lower (<200% FPL)": [30, 25, 28, 17], "Middle (200-399%)": [12, 18, 35, 35], "High (400%+)": [3, 7, 25, 65]}
    for g, d in dists.items():
        for lvl, p in zip(range(1, 5), d):
            n = 110
            sup = lvl == 1 and g.startswith("High")
            ue.append(dict(group=g, response_level=lvl, response_label=labels[lvl],
                           pct=np.nan if sup else p, ci_lo=np.nan if sup else max(0, p - 8),
                           ci_hi=np.nan if sup else p + 8, n_unweighted=n, suppressed=sup))
    pd.DataFrame(ue).to_csv(OUT / "meps_unexpected_expense.csv", index=False)

    bands = [("18-39", 32), ("40-44", 42), ("45-49", 47), ("50-54", 52), ("55-59", 57), ("60-64", 62),
             ("65-69", 67), ("70-74", 72), ("75-79", 77), ("80-85", 82.5)]
    ac = []
    meas = {"prob_pay_bills": ("Problems paying medical bills", 20),
            "worry_bills_very_or_somewhat": ("Very or somewhat worried about medical bills", 45),
            "cost_delay_any": ("Delayed or skipped care due to cost", 12)}
    for m, (lab, base) in meas.items():
        for b, mid in bands:
            p = base * (1.0 if mid < 65 else 0.55) * (1 + (60 - mid) / 200)
            n = 25 if b == "18-39" else 150 + int(rng.integers(0, 200))
            sup = n < 30
            ac.append(dict(source="NHIS 2021-2024", measure=m, measure_label=lab, age_band=b, age_mid=mid,
                           pct=np.nan if sup else round(p, 1), ci_lo=np.nan if sup else round(p - 4, 1),
                           ci_hi=np.nan if sup else round(p + 4, 1), n_unweighted=n, suppressed=sup,
                           flagged=(not sup) and n < 60))
        ac.append(dict(source="NHIS 2021-2024", measure=m, measure_label=lab, age_band="Under 65", age_mid=np.nan,
                       pct=base, ci_lo=base - 3, ci_hi=base + 3, n_unweighted=1200, suppressed=False, flagged=False))
        ac.append(dict(source="NHIS 2021-2024", measure=m, measure_label=lab, age_band="65+", age_mid=np.nan,
                       pct=round(base * 0.5, 1), ci_lo=base * 0.5 - 2, ci_hi=base * 0.5 + 2, n_unweighted=1800,
                       suppressed=False, flagged=False))
    pd.DataFrame(ac).to_csv(OUT / "nhis_age_curve.csv", index=False)

    met = []
    for ds, auc in [("nhis_cv", 0.72), ("meps_external", 0.66)]:
        met += [dict(dataset=ds, model="M1", metric="auc", value=auc, ci_lo=auc - 0.05, ci_hi=auc + 0.05, subgroup=""),
                dict(dataset=ds, model="M1", metric="brier", value=0.15, ci_lo=np.nan, ci_hi=np.nan, subgroup=""),
                dict(dataset=ds, model="M1", metric="prevalence_obs", value=0.2, ci_lo=np.nan, ci_hi=np.nan, subgroup=""),
                dict(dataset=ds, model="M1", metric="prevalence_pred", value=0.21, ci_lo=np.nan, ci_hi=np.nan, subgroup="")]
    for sg, auc, pp in [("Under 65", 0.70, 0.27), ("65+", 0.68, 0.11), ("fpl <100", 0.66, 0.35)]:
        met += [dict(dataset="nhis_cv", model="M1", metric="auc", value=auc, ci_lo=np.nan, ci_hi=np.nan, subgroup=sg),
                dict(dataset="nhis_cv", model="M1", metric="prevalence_pred", value=pp, ci_lo=np.nan, ci_hi=np.nan, subgroup=sg),
                dict(dataset="nhis_cv", model="M1", metric="prevalence_obs", value=pp + 0.01, ci_lo=np.nan, ci_hi=np.nan, subgroup=sg)]
    pd.DataFrame(met).to_csv(OUT / "ml_metrics.csv", index=False)
    cal = []
    for ds in ["nhis_cv", "meps_external"]:
        for b in range(10):
            mp = 0.03 + b * 0.06
            cal.append(dict(dataset=ds, bin=b + 1, mean_pred=mp, obs_rate=max(0, mp + rng.normal(0, 0.03)), n=80))
    pd.DataFrame(cal).to_csv(OUT / "ml_calibration.csv", index=False)
    pd.DataFrame([
        dict(feature="insurance", feature_label="Insurance type", importance=0.04, importance_sd=0.005, method="permutation (AUC drop)"),
        dict(feature="fpl_band", feature_label="Income (% of poverty line)", importance=0.035, importance_sd=0.004, method="permutation (AUC drop)"),
        dict(feature="age", feature_label="Age", importance=0.03, importance_sd=0.004, method="permutation (AUC drop)"),
        dict(feature="health_fair_poor", feature_label="Fair/poor health", importance=0.02, importance_sd=0.003, method="permutation (AUC drop)"),
        dict(feature="region", feature_label="Region", importance=0.004, importance_sd=0.002, method="permutation (AUC drop)"),
    ]).to_csv(OUT / "ml_importance.csv", index=False)
    print("wrote mock CSVs to", OUT)
    make_mock_model()


def make_mock_model():
    """Tiny sklearn Pipeline on synthetic data, same input columns as the real one."""
    from sklearn.compose import ColumnTransformer
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import Pipeline
    from sklearn.preprocessing import OneHotEncoder
    import joblib

    sys.path.insert(0, str(HERE.parent))
    from components import features as F

    MOUT.mkdir(parents=True, exist_ok=True)
    n = 3000
    age = rng.integers(25, 86, n)
    df = pd.DataFrame({
        "age": age, "under65": (age < 65).astype(int),
        "fpl_band": rng.choice(F.FPL_BANDS, n),
        "insurance": [rng.choice(F.insurance_options(a)) for a in age],
        "region": rng.choice(F.REGIONS, n),
        "employed": rng.integers(0, 2, n), "health_fair_poor": rng.integers(0, 2, n),
        "married": rng.integers(0, 2, n), "college": rng.integers(0, 2, n),
    })
    lin = (-1.2 + 0.9 * df.under65 + 0.8 * (df.fpl_band == F.FPL_BANDS[0]) - 0.6 * (df.fpl_band == F.FPL_BANDS[-1])
           + 0.9 * (df.insurance == "uninsured_u65") + 0.7 * df.health_fair_poor - 0.02 * (df.age - 60))
    y = rng.random(n) < 1 / (1 + np.exp(-lin))
    cats = ["fpl_band", "insurance", "region"]
    nums = ["age", "under65", "employed", "health_fair_poor", "married", "college"]
    pre = ColumnTransformer([("cat", OneHotEncoder(handle_unknown="ignore", sparse_output=False), cats),
                             ("num", "passthrough", nums)])
    pipe = Pipeline([("pre", pre), ("clf", LogisticRegression(max_iter=2000))])
    pipe.fit(df[F.FEATURES], y)
    joblib.dump(pipe, MOUT / "risk_model.joblib")
    names = pipe.named_steps["pre"].get_feature_names_out()
    Xt = pipe.named_steps["pre"].transform(df[F.FEATURES])
    coefs = pipe.named_steps["clf"].coef_[0]
    explain = {"intercept": float(pipe.named_steps["clf"].intercept_[0]),
               "coefficients": {nm: float(c) for nm, c in zip(names, coefs)},
               "reference_values": {nm: float(v) for nm, v in zip(names, Xt.mean(axis=0))},
               "note": "MOCK. coefficient x (value - reference) on the logit scale"}
    (MOUT / "logit_explain.json").write_text(json.dumps(explain, indent=2))
    p = pipe.predict_proba(df[F.FEATURES])[:, 1]
    t1, t2 = np.quantile(p, [1 / 3, 2 / 3])
    card = {
        "name": "Breast cancer survivor medical-bill hardship risk (demo) [MOCK]",
        "outcome": "Problems paying medical bills, past 12 months",
        "train_data": "MOCK synthetic data", "train_n": n, "train_events": int(y.sum()),
        "external_data": "MOCK", "external_n": 300, "model": "L2 logistic regression (MOCK)",
        "features": F.FEATURES,
        "excluded_features_and_why": {"race_ethnicity": "used for fairness audit only"},
        "metrics": {"nhis_cv_auc": 0.72, "nhis_cv_brier": 0.15, "meps_auc": 0.66, "meps_auc_ci": [0.6, 0.71], "meps_brier": 0.16},
        "risk_tiers": {"low_max": float(t1), "moderate_max": float(t2)},
        "intended_use": "Education and screening demonstration for a student datathon. Not for clinical or financial decisions.",
        "limitations": ["cross-sectional survey data", "self-reported outcomes",
                        "insurance and outcome definitions differ slightly across surveys", "small MEPS test set"],
        "created": "2026-11-21",
    }
    (MOUT / "model_card.json").write_text(json.dumps(card, indent=2))
    print("wrote mock model to", MOUT)


if __name__ == "__main__":
    main()
