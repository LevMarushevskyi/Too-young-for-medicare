"""Cached loaders for processed CSVs, model artifacts and context stats.

Paths are computed from this file, so the app runs from any cwd and on
Streamlit Community Cloud. Dev overrides:
  TYFM_DATA_DIR   -> directory with the section-6 CSVs (default data/processed)
  TYFM_MODELS_DIR -> directory with risk_model.joblib etc. (default models)
"""
from __future__ import annotations

import json
import os
from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st
import yaml

REPO = Path(__file__).resolve().parents[2]
APP = REPO / "app"


def _dir(env: str, default: Path) -> Path:
    v = os.environ.get(env)
    if v:
        p = Path(v)
        return p if p.is_absolute() else (REPO / p)
    return default


DATA_DIR = _dir("TYFM_DATA_DIR", REPO / "data" / "processed")
MODELS_DIR = _dir("TYFM_MODELS_DIR", REPO / "models")
USING_MOCK = "mock" in str(DATA_DIR).lower()

_CORE = ["meps_estimates.csv", "meps_age_gap_tests.csv", "meps_model_or.csv",
         "meps_unexpected_expense.csv", "nhis_age_curve.csv", "ml_metrics.csv",
         "ml_calibration.csv", "ml_importance.csv"]


def processed_files() -> list[str]:
    """Core section-6 files first, then any other CSV the lanes wrote."""
    extra = sorted(p.name for p in DATA_DIR.glob("*.csv") if p.name not in _CORE) if DATA_DIR.exists() else []
    return [f for f in _CORE if (DATA_DIR / f).exists()] + extra


def _to_bool(s: pd.Series) -> pd.Series:
    if s.dtype == bool:
        return s
    return s.astype(str).str.strip().str.upper().isin(["TRUE", "T", "1", "YES"])


def _file_sig(path: Path):
    try:
        return path.stat().st_mtime
    except OSError:
        return None


@st.cache_data(show_spinner=False)
def _read_csv(path_str: str, _mtime) -> pd.DataFrame | None:
    p = Path(path_str)
    if not p.exists():
        return None
    df = pd.read_csv(p)
    for c in ("suppressed", "flagged"):
        if c in df.columns:
            df[c] = _to_bool(df[c])
    if "suppressed" in df.columns:
        # belt and braces: no value survives for a suppressed row
        for c in ("pct", "ci_lo", "ci_hi", "rse"):
            if c in df.columns:
                df.loc[df["suppressed"], c] = np.nan
    return df


def load(name: str) -> pd.DataFrame | None:
    """Return a processed CSV (or None if missing). Includes suppressed rows: use visible()."""
    p = DATA_DIR / name
    return _read_csv(str(p), _file_sig(p))


def visible(df: pd.DataFrame | None) -> pd.DataFrame:
    """Rows that may be shown: not suppressed and with a numeric pct."""
    if df is None or df.empty:
        return pd.DataFrame(columns=[] if df is None else df.columns)
    out = df
    if "suppressed" in out.columns:
        out = out[~out["suppressed"]]
    if "pct" in out.columns:
        out = out[out["pct"].notna()]
    if "flagged" not in out.columns:
        out = out.assign(flagged=False)
    return out.copy()


def safe_df(name: str) -> pd.DataFrame | None:
    """Copy of a processed CSV with every suppressed cell blanked (incl. counts) and every
    count column (n, n_*) blanked where 1 <= value < 5. Use for downloads and raw tables."""
    df = load(name)
    if df is None:
        return None
    df = df.copy()
    if "suppressed" in df.columns:
        blank = [c for c in ("pct", "ci_lo", "ci_hi", "rse", "n_events", "n_unweighted") if c in df.columns]
        df[blank] = df[blank].astype(object)
        df.loc[df["suppressed"], blank] = None
    for c in df.columns:
        if c == "n" or c.startswith("n_"):
            v = pd.to_numeric(df[c], errors="coerce")
            small = (v > 0) & (v < 5)
            if small.any():
                df[c] = [("<5" if sm else ("" if pd.isna(x) else (str(int(x)) if float(x).is_integer() else str(x))))
                         for x, sm in zip(v, small)]
    return df


def safe_download_bytes(name: str) -> bytes | None:
    df = safe_df(name)
    return None if df is None else df.to_csv(index=False).encode()


@st.cache_data(show_spinner=False)
def _read_json(path_str: str, _mtime):
    p = Path(path_str)
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text())
    except Exception:  # noqa: BLE001
        return None


def model_card() -> dict | None:
    p = MODELS_DIR / "model_card.json"
    return _read_json(str(p), _file_sig(p))


def logit_explain() -> dict | None:
    p = MODELS_DIR / "logit_explain.json"
    return _read_json(str(p), _file_sig(p))


@st.cache_resource(show_spinner=False)
def _load_model(path_str: str, _mtime):
    import joblib

    return joblib.load(path_str)


def risk_model():
    """(model, error_message). model is None if absent or unloadable."""
    p = MODELS_DIR / "risk_model.joblib"
    if not p.exists():
        return None, "Model not built yet: models/risk_model.joblib is missing."
    try:
        return _load_model(str(p), _file_sig(p)), None
    except Exception as e:  # noqa: BLE001
        return None, f"Model file exists but could not be loaded ({type(e).__name__}: {e})."


@st.cache_data(show_spinner=False)
def context_stats() -> dict:
    p = APP / "content" / "context_stats.yaml"
    try:
        items = yaml.safe_load(p.read_text()) or []
        return {d["key"]: d for d in items}
    except Exception:  # noqa: BLE001
        return {}


def mock_banner():
    if USING_MOCK:
        st.warning("DEVELOPMENT MODE: showing MOCK data (TYFM_DATA_DIR points to a mock directory). "
                   "These numbers are invented.", icon="⚠️")


def metric(df: pd.DataFrame | None, dataset: str, metric_name: str, subgroup: str | None = None):
    """Row (as dict) from ml_metrics.csv for an overall (blank subgroup) or named subgroup.

    When several models are listed, the deployed one (name containing "calibrated" but not
    "uncalibrated") is preferred."""
    if df is None or df.empty:
        return None
    d = df[(df["dataset"] == dataset) & (df["metric"] == metric_name)]
    if "model" in d.columns and d["model"].nunique() > 1:
        mn = d["model"].astype(str).str.lower()
        pref = d[mn.str.contains("calibrated") & ~mn.str.contains("uncalibrated")]
        d = pref if len(pref) else d
    sg = d["subgroup"].fillna("").astype(str).str.strip() if "subgroup" in d.columns else pd.Series("", index=d.index)
    if subgroup is None:
        d = d[sg.isin(["", "all", "overall", "All", "Overall", "nan"])]
    else:
        d = d[sg.str.lower() == subgroup.lower()]
    if d.empty:
        return None
    return d.iloc[0].to_dict()
