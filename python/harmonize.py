"""Harmonized features for the risk model (BUILD_GUIDE 8.2). SINGLE SOURCE OF TRUTH.

Used by train_model.py (NHIS), evaluate_external.py (MEPS 2024) and the app
(feature row from user inputs). Category labels below are identical across all
three. Race/ethnicity is NOT a model feature (fairness audit only).

Code sources checked:
- NHIS 2024 adult codebook: PRIVATE_A/MEDICAID_A/MEDICARE_A 1,2 = yes, 3 = no;
  NOTCOV_A 1 = not covered, 2 = covered; REGION 1 NE 2 MW 3 S 4 W;
  EMPWRKLSW1_A 1 yes 2 no; PHSTAT_A 1-5 (4 fair, 5 poor);
  MARSTAT_A 1-3 married (spouse present / not present / unknown), 4 widowed,
  5 divorced, 6 separated, 7 never married, 8 living with partner, 9 unknown;
  EDUCP_A 08 bachelor's, 09 master's, 10 professional/doctoral (97-99 reserved);
  POVRATTC_A family poverty ratio 0-11 (top-coded at 11) -> x100 = % FPL.
- MEPS HC-256: POVLEV24 is family income as % of poverty line; MARRY24X 1 married;
  HIDEG 4 bachelor's 5 master's 6 doctorate (7 "other degree" -> not college);
  EMPST53 1 employed at RD 5/3; RTHLTH53 4 fair 5 poor; PRVEV24/MCDEV24/MCREV24/
  UNINS24 1 = yes (ever in 2024 / uninsured all year); REGION24 1-4.
Reserved negatives (-1,-7,-8,-9,-15) in MEPS and 7/8/9, 97/98/99 in NHIS -> NA.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

FEATURES = ["age", "under65", "fpl_band", "insurance", "region", "employed",
            "health_fair_poor", "married", "college"]
NUMERIC = ["age"]
BINARY = ["under65", "employed", "health_fair_poor", "married", "college"]
CATEGORICAL = ["fpl_band", "insurance", "region"]

FPL_BANDS = ["<100%", "100-199%", "200-399%", "400%+"]
INSURANCE_U65 = ["private_u65", "public_u65", "uninsured_u65"]
INSURANCE_65 = ["medicare_plus_private", "medicare_only_or_public"]
INSURANCE = INSURANCE_U65 + INSURANCE_65
REGIONS = ["NE", "MW", "S", "W"]
CATEGORIES = {"fpl_band": FPL_BANDS, "insurance": INSURANCE, "region": REGIONS}

FEATURE_LABELS = {
    "age": "Age", "under65": "Under 65", "fpl_band": "Family income (% of poverty line)",
    "insurance": "Health insurance", "region": "Census region", "employed": "Currently employed",
    "health_fair_poor": "Self-rated health fair/poor", "married": "Married",
    "college": "Bachelor's degree or higher",
}
LEVEL_LABELS = {
    "<100%": "income below the poverty line", "100-199%": "income 100-199% of poverty",
    "200-399%": "income 200-399% of poverty", "400%+": "income 400%+ of poverty",
    "private_u65": "private insurance (under 65)", "public_u65": "Medicaid/other public coverage (under 65)",
    "uninsured_u65": "no health insurance (under 65)",
    "medicare_plus_private": "Medicare plus private/supplemental coverage (65+)",
    "medicare_only_or_public": "Medicare only or other public coverage (65+)",
    "NE": "living in the Northeast", "MW": "living in the Midwest", "S": "living in the South",
    "W": "living in the West",
}
INSURANCE_PLAIN = {  # for app selectboxes
    "private_u65": "Private (employer or marketplace)",
    "public_u65": "Medicaid or other public",
    "uninsured_u65": "Uninsured",
    "medicare_plus_private": "Medicare + private/Medigap/retiree plan",
    "medicare_only_or_public": "Medicare only (or Medicare + Medicaid)",
}

# 2024 HHS poverty guidelines, 48 contiguous states + DC (ASPE, Jan 2024):
# $15,060 for 1 person + $5,380 per additional person. Alaska and Hawaii have
# higher guidelines and are NOT handled here.
FPL_2024_BASE = 15060
FPL_2024_PER_PERSON = 5380


def poverty_guideline_2024(household_size: int) -> float:
    n = max(int(household_size), 1)
    return FPL_2024_BASE + FPL_2024_PER_PERSON * (n - 1)


def fpl_band_from_pct(pct):
    """% of poverty (e.g. 150 = 150%) -> band label; vectorized; NaN stays NaN."""
    p = pd.to_numeric(pd.Series(pct), errors="coerce")
    out = pd.Series(np.nan, index=p.index, dtype=object)
    out[p < 100] = "<100%"
    out[(p >= 100) & (p < 200)] = "100-199%"
    out[(p >= 200) & (p < 400)] = "200-399%"
    out[p >= 400] = "400%+"
    return out


def fpl_band_from_income(income: float, household_size: int) -> str:
    pct = 100.0 * float(income) / poverty_guideline_2024(household_size)
    return fpl_band_from_pct([pct]).iloc[0]


def _yn(x, yes=(1,), no=(2,)):
    x = pd.to_numeric(x, errors="coerce")
    return pd.Series(np.where(x.isin(yes), 1.0, np.where(x.isin(no), 0.0, np.nan)), index=x.index)


def _insurance(age, private, public, medicare, uninsured):
    """All inputs 0/1/NaN Series. Under 65: uninsured > private > public.
    65+: any private (with or without Medicare) -> medicare_plus_private; else
    medicare_only_or_public (includes the very few uninsured 65+)."""
    out = pd.Series(np.nan, index=age.index, dtype=object)
    u65 = age < 65
    known = ~(private.isna() & public.isna() & medicare.isna() & uninsured.isna())
    out[u65 & known] = "public_u65"
    out[u65 & (private == 1)] = "private_u65"
    out[u65 & (uninsured == 1)] = "uninsured_u65"
    out[~u65 & known & age.notna()] = "medicare_only_or_public"
    out[~u65 & age.notna() & (private == 1)] = "medicare_plus_private"
    return out


def nhis_features(df: pd.DataFrame) -> pd.DataFrame:
    """NHIS raw columns (reserved codes may or may not already be NA) -> features."""
    age = pd.to_numeric(df["AGEP_A"], errors="coerce")
    age = age.where(age < 97).clip(upper=85)
    priv = _yn(df["PRIVATE_A"], yes=(1, 2), no=(3,))
    mcaid = _yn(df["MEDICAID_A"], yes=(1, 2), no=(3,))
    mcare = _yn(df["MEDICARE_A"], yes=(1, 2), no=(3,))
    unins = _yn(df["NOTCOV_A"], yes=(1,), no=(2,))
    public = pd.Series(np.where((mcaid == 1) | (mcare == 1), 1.0,
                                np.where(mcaid.isna() & mcare.isna(), np.nan, 0.0)), index=df.index)
    educ = pd.to_numeric(df["EDUCP_A"], errors="coerce")
    out = pd.DataFrame(index=df.index)
    out["age"] = age
    out["under65"] = np.where(age.isna(), np.nan, (age < 65).astype(float))
    out["fpl_band"] = fpl_band_from_pct(pd.to_numeric(df["POVRATTC_A"], errors="coerce") * 100).values
    out["insurance"] = _insurance(age, priv, public, mcare, unins)
    out["region"] = pd.to_numeric(df["REGION"], errors="coerce").map(dict(zip([1, 2, 3, 4], REGIONS)))
    out["employed"] = _yn(df["EMPWRKLSW1_A"])
    out["health_fair_poor"] = _yn(df["PHSTAT_A"], yes=(4, 5), no=(1, 2, 3))
    out["married"] = _yn(df["MARSTAT_A"], yes=(1, 2, 3), no=(4, 5, 6, 7, 8))
    out["college"] = pd.Series(np.where(educ.isin([8, 9, 10]), 1.0,
                                        np.where(educ.between(0, 7), 0.0, np.nan)), index=df.index)
    return out[FEATURES]


def nhis_race_eth(df: pd.DataFrame) -> pd.Series:
    m = {1: "Hispanic", 2: "NH White", 3: "NH Black", 4: "NH Asian", 5: "NH other/multiple",
         6: "NH other/multiple", 7: "NH other/multiple"}
    return pd.to_numeric(df["HISPALLP_A"], errors="coerce").map(m)


MEPS_COLS = ["DUPERSID", "CABREAST", "AGE24X", "POVLEV24", "PRVEV24", "MCDEV24", "MCREV24",
             "UNINS24", "REGION24", "EMPST53", "RTHLTH53", "MARRY24X", "HIDEG", "PROBPY42",
             "PERWT24F", "VARSTR", "VARPSU", "RACETHX", "SEX"]


def load_meps_h256(path_dta=None, path_zip=None) -> pd.DataFrame:
    """Read the needed MEPS h256 columns with pyreadstat (no dependency on Lane A)."""
    import os, tempfile, zipfile
    import pyreadstat
    if path_dta and os.path.exists(path_dta):
        df, _ = pyreadstat.read_dta(path_dta, usecols=MEPS_COLS)
        return df
    with zipfile.ZipFile(path_zip) as z, tempfile.TemporaryDirectory() as td:
        name = [n for n in z.namelist() if n.lower().endswith(".dta")][0]
        z.extract(name, td)
        df, _ = pyreadstat.read_dta(os.path.join(td, name), usecols=MEPS_COLS)
    return df


def _meps_na(x):
    x = pd.to_numeric(x, errors="coerce")
    return x.where(x >= 0)


def meps_features(df: pd.DataFrame) -> pd.DataFrame:
    age = _meps_na(df["AGE24X"]).clip(upper=85)
    priv = _yn(df["PRVEV24"])
    mcaid = _yn(df["MCDEV24"])
    mcare = _yn(df["MCREV24"])
    unins = _yn(df["UNINS24"])
    public = pd.Series(np.where((mcaid == 1) | (mcare == 1), 1.0,
                                np.where(mcaid.isna() & mcare.isna(), np.nan, 0.0)), index=df.index)
    emp = _meps_na(df["EMPST53"])
    hlth = _meps_na(df["RTHLTH53"])
    mar = _meps_na(df["MARRY24X"])
    deg = _meps_na(df["HIDEG"])
    out = pd.DataFrame(index=df.index)
    out["age"] = age
    out["under65"] = np.where(age.isna(), np.nan, (age < 65).astype(float))
    # POVLEV24 negatives are real (negative family income, h256cb), not reserved codes -> "<100%"
    out["fpl_band"] = fpl_band_from_pct(pd.to_numeric(df["POVLEV24"], errors="coerce")).values
    out["insurance"] = _insurance(age, priv, public, mcare, unins)
    out["region"] = _meps_na(df["REGION24"]).map(dict(zip([1, 2, 3, 4], REGIONS)))
    out["employed"] = np.where(emp.isna(), np.nan, (emp == 1).astype(float))
    out["health_fair_poor"] = np.where(hlth.isna(), np.nan, hlth.isin([4, 5]).astype(float))
    out["married"] = np.where(mar.isna() | (mar == 6), np.nan, (mar == 1).astype(float))
    out["college"] = np.where(deg.isna() | (deg == 8), np.nan, deg.isin([4, 5, 6]).astype(float))
    return out[FEATURES]


def meps_race_eth(df: pd.DataFrame) -> pd.Series:
    m = {1: "Hispanic", 2: "NH White", 3: "NH Black", 4: "NH Asian", 5: "NH other/multiple"}
    return pd.to_numeric(df["RACETHX"], errors="coerce").map(m)


def insurance_options(age: float) -> list[str]:
    """Valid insurance categories for an age (app selectbox)."""
    return INSURANCE_U65 if age < 65 else INSURANCE_65


def build_feature_row(age, insurance, region, employed, health_fair_poor, married, college,
                      fpl_band=None, income=None, household_size=None) -> pd.DataFrame:
    """One-row DataFrame from app inputs. Give fpl_band directly, or income + household_size
    (2024 HHS guidelines, contiguous US). Booleans may be bool or 0/1."""
    age = float(min(max(age, 18), 85))
    if fpl_band is None:
        if income is None or household_size is None:
            raise ValueError("give fpl_band or income + household_size")
        fpl_band = fpl_band_from_income(income, household_size)
    if fpl_band not in FPL_BANDS:
        raise ValueError(f"fpl_band must be one of {FPL_BANDS}")
    if insurance not in insurance_options(age):
        raise ValueError(f"insurance {insurance!r} not valid for age {age}: {insurance_options(age)}")
    if region not in REGIONS:
        raise ValueError(f"region must be one of {REGIONS}")
    row = {"age": age, "under65": float(age < 65), "fpl_band": fpl_band, "insurance": insurance,
           "region": region, "employed": float(bool(employed)),
           "health_fair_poor": float(bool(health_fair_poor)), "married": float(bool(married)),
           "college": float(bool(college))}
    return pd.DataFrame([row])[FEATURES]


def explain_contributions(row: pd.DataFrame, explain: dict, top: int = 3) -> list[dict]:
    """'What drives this estimate': coefficient x (value - training weighted mean), summed
    per feature, on the log-odds scale of the UNCALIBRATED logistic model. `explain` is
    models/logit_explain.json. Returns the top-|contribution| features with plain text."""
    r = row.iloc[0]
    res = []
    for feat, spec in explain["features"].items():
        if spec["type"] == "numeric":
            c = spec["coef_per_unit"] * (float(r[feat]) - spec["mean"])
            desc = f"age {int(round(float(r[feat])))}"
        elif spec["type"] == "binary":
            v = float(r[feat])
            c = spec["coef"] * (v - spec["mean"])
            desc = ("" if v == 1 else "not ") + FEATURE_LABELS[feat].lower()
            if feat == "under65":
                desc = "under 65" if v == 1 else "65 or older"
        else:
            c = sum(lv["coef"] * ((1.0 if r[feat] == name else 0.0) - lv["mean"])
                    for name, lv in spec["levels"].items())
            desc = LEVEL_LABELS.get(r[feat], str(r[feat]))
        res.append({"feature": feat, "feature_label": FEATURE_LABELS[feat], "contribution": c,
                    "direction": "raises" if c > 0 else "lowers", "text": desc})
    res.sort(key=lambda d: -abs(d["contribution"]))
    return res[:top]
