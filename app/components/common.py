"""Small shared helpers for pages."""
from __future__ import annotations

import pandas as pd
import streamlit as st

from components import charts as C
from components import data as D


def page_setup(title: str):
    st.set_page_config(page_title=f"{title} · Too Young for Medicare", layout="wide")
    D.mock_banner()


def show_chart(fig, cap: str, missing: str = "Not available yet: the processed CSV for this chart has not been produced."):
    if fig is None:
        st.info(missing)
        return
    st.plotly_chart(fig, width="stretch", config={"displaylogo": False})
    if cap:
        st.caption(cap)


def age_gap_pair(est: pd.DataFrame | None, measure: str):
    """(under65 row, 65+ row) for a measure in the age_gap chart, visible rows only, else None."""
    d = D.visible(est)
    if d.empty:
        return None
    d = d[(d["chart_id"] == "age_gap") & (d["measure"] == measure)]
    u = d[d["group"].map(C._is_u65)]
    o = d[~d["group"].map(C._is_u65)]
    if len(u) and len(o):
        return u.iloc[0], o.iloc[0]
    return None


def model_age_term(or_df: pd.DataFrame | None, model: str = "B"):
    if or_df is None or or_df.empty:
        return None
    d = or_df[or_df["model"].astype(str).str.upper().str.replace("MODEL", "").str.strip() == model.upper()]
    d = d[~d["term"].astype(str).str.contains("ntercept", na=False)]
    m = d[[C._is_age_term(t, str(l)) for t, l in zip(d["term"], d["term_label"])]]
    return m.iloc[0] if len(m) else None


def external_auc():
    mt = D.load("ml_metrics.csv")
    r = D.metric(mt, "meps_external", "auc")
    if r is not None and pd.notna(r.get("value")):
        return float(r["value"]), r.get("ci_lo"), r.get("ci_hi")
    card = D.model_card() or {}
    v = (card.get("metrics") or {}).get("meps_auc")
    if v is not None:
        ci = (card.get("metrics") or {}).get("meps_auc_ci") or [None, None]
        return float(v), ci[0], ci[1]
    return None
