"""External validation on the MEPS 2024 breast cancer cohort (BUILD_GUIDE 8.4).

Run from repo root after train_model.py: .venv/bin/python python/evaluate_external.py
Cohort: CABREAST == 1, AGE24X >= 18, PROBPY42 in {1,2}, PERWT24F > 0. Outcome PROBPY42 == 1.
All metrics weighted by PERWT24F. AUC 95% CI = percentile bootstrap (1,000 person resamples;
simple, not design-based). Appends meps_external rows to ml_metrics.csv / ml_calibration.csv
(replacing any previous meps_external rows) and updates models/model_card.json.
"""
from __future__ import annotations

import json
import os
import sys

import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import brier_score_loss, roc_auc_score

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import harmonize as H  # noqa: E402
from train_model import P, cal_int_slope, calib_table  # noqa: E402

MEPS_CAL_BINS = 5  # n=368 / 29 events: 10 bins left 7 of 10 suppressed and the rest n=37

B = 1000


def main():
    dta = P("data/interim/h256.dta")
    raw = H.load_meps_h256(path_dta=dta, path_zip=P("data/raw/meps/h256dta.zip"))
    d = raw[(raw.CABREAST == 1) & (raw.AGE24X >= 18) & raw.PROBPY42.isin([1, 2]) & (raw.PERWT24F > 0)]
    d = d.reset_index(drop=True)
    X = H.meps_features(d)
    y = (d.PROBPY42 == 1).astype(int).values
    w = d.PERWT24F.values.astype(float)
    model = joblib.load(P("models/risk_model.joblib"))
    p = model.predict_proba(X)[:, 1]
    print(f"MEPS external n={len(y)}, events={y.sum()}, missing features: {X.isna().sum().to_dict()}")

    auc = roc_auc_score(y, p, sample_weight=w)
    brier = brier_score_loss(y, p, sample_weight=w)
    ci_int, slope = cal_int_slope(y, p, w)
    obs, pred = np.average(y, weights=w), np.average(p, weights=w)
    rng = np.random.default_rng(42)
    boots = {"auc": [], "brier": [], "cal_intercept": [], "cal_slope": []}
    n = len(y)
    for _ in range(B):
        i = rng.integers(0, n, n)
        if y[i].min() == y[i].max():
            continue
        boots["auc"].append(roc_auc_score(y[i], p[i], sample_weight=w[i]))
        boots["brier"].append(brier_score_loss(y[i], p[i], sample_weight=w[i]))
        a, s = cal_int_slope(y[i], p[i], w[i])
        boots["cal_intercept"].append(a)
        boots["cal_slope"].append(s)
    ci = {k: np.percentile(v, [2.5, 97.5]) for k, v in boots.items()}

    name = "calibrated_logistic_l2"
    card_path = P("models/model_card.json")
    card = json.load(open(card_path))
    if "boosting" in card["model"]:
        name = "calibrated_hist_gb"
    rows = [dict(metric="auc", value=auc, ci_lo=ci["auc"][0], ci_hi=ci["auc"][1]),
            dict(metric="brier", value=brier, ci_lo=ci["brier"][0], ci_hi=ci["brier"][1]),
            dict(metric="cal_intercept", value=ci_int, ci_lo=ci["cal_intercept"][0], ci_hi=ci["cal_intercept"][1]),
            dict(metric="cal_slope", value=slope, ci_lo=ci["cal_slope"][0], ci_hi=ci["cal_slope"][1]),
            dict(metric="prevalence_obs", value=obs, ci_lo=None, ci_hi=None),
            dict(metric="prevalence_pred", value=pred, ci_lo=None, ci_hi=None)]
    # subgroup by age group (suppress n<50 or events<5)
    for lab, m in (("Under 65", X.under65 == 1), ("65+", X.under65 == 0)):
        m = m.values
        k = int(y[m].sum())
        sg = f"age_group={lab}"
        if m.sum() < 50 or k < 5:
            rows += [dict(metric=mt, value=None, ci_lo=None, ci_hi=None,
                          subgroup=sg + " (suppressed: n<50 or events<5)")
                     for mt in ("auc", "prevalence_obs", "prevalence_pred")]
            continue
        rows += [dict(metric="auc", value=roc_auc_score(y[m], p[m], sample_weight=w[m]), subgroup=sg),
                 dict(metric="prevalence_obs", value=np.average(y[m], weights=w[m]), subgroup=sg),
                 dict(metric="prevalence_pred", value=np.average(p[m], weights=w[m]), subgroup=sg)]
    ext = pd.DataFrame(rows)
    ext.insert(0, "model", name)
    ext.insert(0, "dataset", "meps_external")
    ext["subgroup"] = ext.get("subgroup", pd.Series(dtype=object)).fillna("")
    for c in ("value", "ci_lo", "ci_hi"):
        ext[c] = pd.to_numeric(ext[c]).astype(float).round(4)
    met = pd.read_csv(P("data/processed/ml_metrics.csv"), keep_default_na=False, na_values=[""])
    met = met[met.dataset != "meps_external"]
    met = pd.concat([met, ext[met.columns]], ignore_index=True)
    met["subgroup"] = met["subgroup"].fillna("")
    met.to_csv(P("data/processed/ml_metrics.csv"), index=False)

    cal = pd.read_csv(P("data/processed/ml_calibration.csv"))
    cal = cal[cal.dataset != "meps_external"]
    cal = pd.concat([cal, calib_table(y, p, w, "meps_external", nbins=MEPS_CAL_BINS)], ignore_index=True)
    cal.to_csv(P("data/processed/ml_calibration.csv"), index=False)

    sh = 100 * (X.loc[X.under65 == 0, "insurance"] == "medicare_plus_private").mean()
    card["limitations"] = [
        (l.replace(" (unweighted);", f" (unweighted) vs {sh:.1f}% in the MEPS external set;", 1)
         if l.startswith("65+ insurance split") and "MEPS external set" not in l else l)
        for l in card["limitations"]]
    card["external_n"] = int(n)
    card["external_events"] = int(y.sum())
    card["metrics"].update({"meps_auc": round(auc, 4),
                            "meps_auc_ci": [round(float(ci["auc"][0]), 4), round(float(ci["auc"][1]), 4)],
                            "meps_brier": round(brier, 4), "meps_cal_intercept": round(ci_int, 4),
                            "meps_cal_slope": round(slope, 4), "meps_prevalence_obs": round(float(obs), 4),
                            "meps_prevalence_pred": round(float(pred), 4),
                            "meps_auc_ci_method": f"percentile bootstrap, {len(boots['auc'])} person resamples, weighted AUC"})
    json.dump(card, open(card_path, "w"), indent=2)
    print(ext.to_string())
    print(calib_table(y, p, w, "meps_external", nbins=MEPS_CAL_BINS).to_string())


if __name__ == "__main__":
    main()
