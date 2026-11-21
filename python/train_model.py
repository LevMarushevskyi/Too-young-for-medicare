"""Train the medical-bill hardship risk model on NHIS 2021-2024 (BUILD_GUIDE 8.3, 8.5, 8.6).

Run from repo root: .venv/bin/python python/train_model.py
Inputs : data/interim/nhis_breast.csv (R/04_nhis_clean.R)
Outputs: models/risk_model.joblib, models/logit_explain.json, models/model_card.json,
         data/processed/ml_metrics.csv, ml_calibration.csv, ml_importance.csv,
         ml_age_group_avg.csv
Note: nhis_cv rows in ml_metrics.csv: value = mean over 5 folds, ci_lo/ci_hi = mean -/+ 1 SD
across folds (NOT a 95% CI). Fairness rows use pooled out-of-fold predictions; ci blank.
"""
from __future__ import annotations

import json
import os
import sys
import warnings
from datetime import date

import joblib
import numpy as np
import pandas as pd
import sklearn
from sklearn.calibration import CalibratedClassifierCV
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.impute import SimpleImputer
from sklearn.inspection import permutation_importance
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import brier_score_loss, roc_auc_score
from sklearn.model_selection import StratifiedKFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, OrdinalEncoder, StandardScaler
import statsmodels.api as sm

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import harmonize as H  # noqa: E402

sklearn.set_config(enable_metadata_routing=True)
warnings.filterwarnings("ignore", category=FutureWarning)
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
P = lambda *a: os.path.join(ROOT, *a)  # noqa: E731
SEED = 42


def make_m1():
    pre = ColumnTransformer([
        ("num", Pipeline([("imp", SimpleImputer(strategy="median")),
                          ("sc", StandardScaler().set_fit_request(sample_weight=True))]), H.NUMERIC),
        ("bin", SimpleImputer(strategy="most_frequent"), H.BINARY),
        ("cat", Pipeline([("imp", SimpleImputer(strategy="most_frequent")),
                          ("oh", OneHotEncoder(categories=[H.CATEGORIES[c] for c in H.CATEGORICAL],
                                               handle_unknown="ignore"))]), H.CATEGORICAL),
    ], verbose_feature_names_out=False)
    lr = LogisticRegression(C=1.0, max_iter=2000).set_fit_request(sample_weight=True)
    return Pipeline([("pre", pre), ("lr", lr)])


def make_m2():
    pre = ColumnTransformer([
        ("num", "passthrough", H.NUMERIC + H.BINARY),
        ("cat", Pipeline([("imp", SimpleImputer(strategy="most_frequent")),
                          ("ord", OrdinalEncoder(categories=[H.CATEGORIES[c] for c in H.CATEGORICAL],
                                                 handle_unknown="use_encoded_value", unknown_value=-1))]),
         H.CATEGORICAL),
    ], verbose_feature_names_out=False)
    n_num = len(H.NUMERIC + H.BINARY)
    cat_mask = [False] * n_num + [True] * len(H.CATEGORICAL)
    hgb = HistGradientBoostingClassifier(max_depth=3, learning_rate=0.05, max_iter=300,
                                         early_stopping=True, categorical_features=cat_mask,
                                         random_state=SEED).set_fit_request(sample_weight=True)
    return Pipeline([("pre", pre), ("hgb", hgb)])


def calibrated(base):
    return CalibratedClassifierCV(base, method="sigmoid", cv=5).set_fit_request(sample_weight=True)


def cal_int_slope(y, p, w):
    """Weighted calibration intercept (offset logit p) and slope (y ~ logit p)."""
    p = np.clip(p, 1e-6, 1 - 1e-6)
    lp = np.log(p / (1 - p))
    wn = w / w.mean()
    slope = sm.GLM(y, sm.add_constant(lp), family=sm.families.Binomial(), var_weights=wn).fit().params[1]
    inter = sm.GLM(y, np.ones_like(lp), family=sm.families.Binomial(), offset=lp,
                   var_weights=wn).fit().params[0]
    return float(inter), float(slope)


def wquantile(x, w, qs):
    o = np.argsort(x)
    cw = np.cumsum(w[o]) / w.sum()
    return [float(x[o][np.searchsorted(cw, q)]) for q in qs]


def calib_table(y, p, w, dataset, nbins=10):
    """Quantile bins of predicted risk (unweighted cut). Small-cell rule: obs_rate blank if
    bin n < 30 or events < 5 (mean_pred still shown); flagged = n < 60."""
    bins = pd.qcut(pd.Series(p).rank(method="first"), nbins, labels=False)
    rows = []
    for b in range(nbins):
        m = (bins == b).values
        n, k = int(m.sum()), int(y[m].sum())
        obs = np.average(y[m], weights=w[m]) if (n >= 30 and k >= 5) else np.nan
        rows.append({"dataset": dataset, "bin": b + 1,
                     "mean_pred": round(float(np.average(p[m], weights=w[m])), 4),
                     "obs_rate": None if np.isnan(obs) else round(float(obs), 4), "n": n,
                     "flagged": bool(n < 60)})  # 5.4 flag (dagger) for small bins
    return pd.DataFrame(rows)


def main():
    df = pd.read_csv(P("data/interim/nhis_breast.csv"))
    df = df[df["prob_pay_bills"].notna()].reset_index(drop=True)
    X = H.nhis_features(df)
    y = df["prob_pay_bills"].astype(int).values
    w = df["wt_pool"].values.astype(float)
    race = H.nhis_race_eth(df)
    miss = X.isna().mean()
    print(f"NHIS train n={len(y)}, events={y.sum()}, weighted prevalence={np.average(y, weights=w):.4f}")
    print("feature missingness:", miss.round(3).to_dict())
    if (miss > 0.05).any():
        print("WARNING: >5% missing in", list(miss[miss > 0.05].index), "- indicator not implemented")

    skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=SEED)
    folds = list(skf.split(X, y))
    res = {"M1": {"auc": [], "brier": []}, "M2": {"auc": [], "brier": []}}
    for tr, te in folds:
        for name, mk in (("M1", make_m1), ("M2", make_m2)):
            m = mk().fit(X.iloc[tr], y[tr], sample_weight=w[tr])
            p = m.predict_proba(X.iloc[te])[:, 1]
            res[name]["auc"].append(roc_auc_score(y[te], p, sample_weight=w[te]))
            res[name]["brier"].append(brier_score_loss(y[te], p, sample_weight=w[te]))
    for k, v in res.items():
        print(k, "AUC %.3f +- %.3f, Brier %.4f" % (np.mean(v["auc"]), np.std(v["auc"]), np.mean(v["brier"])))
    pick = "M2" if np.mean(res["M2"]["auc"]) - np.mean(res["M1"]["auc"]) >= 0.02 else "M1"
    make_pick = make_m1 if pick == "M1" else make_m2
    print("picked", pick)

    # out-of-fold predictions of the CALIBRATED chosen model
    oof = np.zeros(len(y))
    cal_rows = {"auc": [], "brier": [], "cal_intercept": [], "cal_slope": [],
                "prevalence_obs": [], "prevalence_pred": []}
    for tr, te in folds:
        m = calibrated(make_pick()).fit(X.iloc[tr], y[tr], sample_weight=w[tr])
        p = m.predict_proba(X.iloc[te])[:, 1]
        oof[te] = p
        ci, cs = cal_int_slope(y[te], p, w[te])
        cal_rows["auc"].append(roc_auc_score(y[te], p, sample_weight=w[te]))
        cal_rows["brier"].append(brier_score_loss(y[te], p, sample_weight=w[te]))
        cal_rows["cal_intercept"].append(ci)
        cal_rows["cal_slope"].append(cs)
        cal_rows["prevalence_obs"].append(np.average(y[te], weights=w[te]))
        cal_rows["prevalence_pred"].append(np.average(p, weights=w[te]))

    model_name = {"M1": "calibrated_logistic_l2", "M2": "calibrated_hist_gb"}[pick]
    metrics = []
    for name, lab in (("M1", "logistic_l2_uncalibrated"), ("M2", "hist_gb_uncalibrated")):
        for met in ("auc", "brier"):
            v = np.array(res[name][met])
            metrics.append(dict(dataset="nhis_cv", model=lab, metric=met, value=v.mean(),
                                ci_lo=v.mean() - v.std(), ci_hi=v.mean() + v.std(), subgroup=""))
    for met, v in cal_rows.items():
        v = np.array(v)
        metrics.append(dict(dataset="nhis_cv", model=model_name, metric=met, value=v.mean(),
                            ci_lo=v.mean() - v.std(), ci_hi=v.mean() + v.std(), subgroup=""))

    # fairness / subgroups (8.5) on pooled OOF predictions, suppress n < 50
    groups = {"age_group": np.where(X["under65"] == 1, "Under 65", "65+"),
              "fpl_band": X["fpl_band"].fillna("missing").values,
              "race_ethnicity": race.fillna("missing").values}
    for gname, g in groups.items():
        for lev in sorted(set(g)):
            m = g == lev
            n, k = int(m.sum()), int(y[m].sum())
            sg = f"{gname}={lev}"
            if n < 50 or k < 5:
                for met in ("auc", "prevalence_obs", "prevalence_pred"):
                    metrics.append(dict(dataset="nhis_cv", model=model_name, metric=met, value=None,
                                        ci_lo=None, ci_hi=None, subgroup=sg + " (suppressed: n<50 or events<5)"))
                continue
            auc = roc_auc_score(y[m], oof[m], sample_weight=w[m]) if 0 < k < n else None
            for met, val in (("auc", auc), ("prevalence_obs", np.average(y[m], weights=w[m])),
                             ("prevalence_pred", np.average(oof[m], weights=w[m]))):
                metrics.append(dict(dataset="nhis_cv", model=model_name, metric=met, value=val,
                                    ci_lo=None, ci_hi=None, subgroup=sg))
    met_df = pd.DataFrame(metrics)
    met_df[["value", "ci_lo", "ci_hi"]] = met_df[["value", "ci_lo", "ci_hi"]].astype(float).round(4)
    met_df.to_csv(P("data/processed/ml_metrics.csv"), index=False)
    calib_table(y, oof, w, "nhis_cv").to_csv(P("data/processed/ml_calibration.csv"), index=False)

    # final model on all NHIS data
    final_cal = calibrated(make_pick()).fit(X, y, sample_weight=w)
    final = Pipeline([("calibrated", final_cal)])
    os.makedirs(P("models"), exist_ok=True)
    joblib.dump(final, P("models/risk_model.joblib"))
    p_all = final.predict_proba(X)[:, 1]

    # tiers: weighted tertiles of predicted risk on NHIS
    t1, t2 = wquantile(p_all, w, [1 / 3, 2 / 3])

    # explanation json from the uncalibrated logistic refit on all data
    m1 = make_m1().fit(X, y, sample_weight=w)
    pre, lr = m1.named_steps["pre"], m1.named_steps["lr"]
    names = list(pre.get_feature_names_out())
    coefs = dict(zip(names, lr.coef_[0]))
    Z = pre.transform(X)
    Z = Z.toarray() if hasattr(Z, "toarray") else Z
    zmean = dict(zip(names, np.average(Z, axis=0, weights=w)))
    sc = pre.named_transformers_["num"].named_steps["sc"]
    feats = {"age": {"type": "numeric", "coef_per_unit": float(coefs["age"] / sc.scale_[0]),
                     "mean": float(np.average(X["age"], weights=w))}}
    for b in H.BINARY:
        feats[b] = {"type": "binary", "coef": float(coefs[b]), "mean": float(zmean[b])}
    for c in H.CATEGORICAL:
        feats[c] = {"type": "categorical",
                    "levels": {lev: {"coef": float(coefs[f"{c}_{lev}"]), "mean": float(zmean[f"{c}_{lev}"])}
                               for lev in H.CATEGORIES[c]}}
    explain = {"model": "uncalibrated L2 logistic (same features), log-odds scale",
               "intercept": float(lr.intercept_[0]),
               "how_to_use": "contribution = coef * (x - mean); categorical: sum over levels of "
                             "coef * (1[x==level] - mean). See harmonize.explain_contributions.",
               "features": feats}
    with open(P("models/logit_explain.json"), "w") as f:
        json.dump(explain, f, indent=2)

    # permutation importance (final model, in-sample NHIS, weighted AUC drop)
    pi = permutation_importance(final, X, y, scoring="roc_auc", n_repeats=10, random_state=SEED,
                                sample_weight=w)
    imp = pd.DataFrame({"feature": H.FEATURES, "feature_label": [H.FEATURE_LABELS[f] for f in H.FEATURES],
                        "importance": pi.importances_mean.round(4), "importance_sd": pi.importances_std.round(4),
                        "method": "permutation_auc_drop_nhis_insample_10rep"})
    imp.sort_values("importance", ascending=False).to_csv(P("data/processed/ml_importance.csv"), index=False)

    # app comparison bar: weighted mean predicted risk by age group (final model, NHIS)
    rows = []
    for lab, m in (("Under 65", X["under65"] == 1), ("65+", X["under65"] == 0)):
        m = m.values
        rows.append({"age_group": lab, "mean_pred": round(float(np.average(p_all[m], weights=w[m])), 4),
                     "obs_rate": round(float(np.average(y[m], weights=w[m])), 4), "n_unweighted": int(m.sum())})
    pd.DataFrame(rows).to_csv(P("data/processed/ml_age_group_avg.csv"), index=False)

    card = {
        "name": "Breast cancer survivor medical-bill hardship risk (demo)",
        "outcome": "Problems paying medical bills, past 12 months",
        "train_data": "NHIS Sample Adult 2021-2024, adults with breast cancer history",
        "train_n": int(len(y)), "train_events": int(y.sum()),
        "external_data": "MEPS HC-256 2024, adults with breast cancer (CABREAST=1)",
        "external_n": None,
        "model": {"M1": "Calibrated L2 logistic regression",
                  "M2": "Calibrated histogram gradient boosting"}[pick] + " (sigmoid, 5-fold CalibratedClassifierCV)",
        "model_selection": {"rule": "M1 unless M2 CV AUC >= M1 + 0.02",
                            "m1_cv_auc": round(float(np.mean(res["M1"]["auc"])), 4),
                            "m2_cv_auc": round(float(np.mean(res["M2"]["auc"])), 4), "picked": pick},
        "features": H.FEATURES,
        "excluded_features_and_why": {
            "race_ethnicity": "used for fairness audit only",
            "years_since_diagnosis": "NHIS-only; not available in MEPS, excluded from portable model",
            "high_deductible_plan": "NHIS-only; not available in MEPS, excluded from portable model",
            "urban_rural": "URBRRL not on the 2024 NHIS public file"},
        "metrics": {"nhis_cv_auc": round(float(np.mean(cal_rows["auc"])), 4),
                    "nhis_cv_auc_sd": round(float(np.std(cal_rows["auc"])), 4),
                    "nhis_cv_brier": round(float(np.mean(cal_rows["brier"])), 4),
                    "meps_auc": None, "meps_auc_ci": [None, None], "meps_brier": None},
        "risk_tiers": {"low_max": round(t1, 4), "moderate_max": round(t2, 4),
                       "method": "weighted tertiles of predicted risk, NHIS training data"},
        "intended_use": "Education and screening demonstration for a student datathon. Not for clinical or financial decisions.",
        "limitations": ["cross-sectional survey data", "self-reported outcomes",
                        "insurance and outcome definitions differ slightly across surveys",
                        "small MEPS test set",
                        "NHIS insurance is coverage at interview; MEPS is ever-covered in 2024",
                        "outcome refers to the respondent's family in both surveys",
                        "male survivors (n=%d) included in NHIS training" % int((df['SEX_A'] == 1).sum()),
                        "65+ insurance split is not like-for-like: medicare_plus_private is %.1f%% of 65+ in NHIS "
                        "training (unweighted)%s; MEPS PRVEV24 is ever-private in 2024 and Medigap/Medicare "
                        "Advantage may be classified differently" % (
                            100 * (X.loc[X.under65 == 0, 'insurance'] == 'medicare_plus_private').mean(), "")],
        "missing_data": "most-frequent (binary/categorical) or median (age) imputation inside the pipeline; "
                        "no feature >5% missing, so no missing indicators",
        "nhis_cv_ci_note": "ml_metrics nhis_cv ci_lo/ci_hi = mean -/+ 1 SD over 5 folds",
        "fpl_guidelines": "2024 HHS poverty guidelines, 48 contiguous states + DC: $15,060 + $5,380 per extra person; AK/HI not handled",
        "sklearn_version": sklearn.__version__,
        "created": str(date.today()),
    }
    with open(P("models/model_card.json"), "w") as f:
        json.dump(card, f, indent=2)

    # sanity check required by the lead
    a = H.build_feature_row(50, "uninsured_u65", "S", 0, 0, 0, 0, fpl_band="<100%")
    b = H.build_feature_row(70, "medicare_plus_private", "S", 0, 0, 0, 0, fpl_band="400%+")
    pa, pb = final.predict_proba(a)[0, 1], final.predict_proba(b)[0, 1]
    print(f"sanity: 50yo uninsured <100% FPL = {pa:.3f}; 70yo Medicare+private 400%+ = {pb:.3f}")
    assert pa > pb, "SANITY CHECK FAILED"
    print("top drivers (50yo):", H.explain_contributions(a, explain))
    print("tiers:", t1, t2)
    print(met_df[met_df.subgroup == ""].to_string())


if __name__ == "__main__":
    main()
