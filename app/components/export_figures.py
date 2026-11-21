"""Render key app charts to PNG for the slides team.

    .venv/bin/python app/components/export_figures.py            # real data -> docs/screenshots/
    TYFM_DATA_DIR=app/dev/mock_processed TYFM_MODELS_DIR=app/dev/mock_models \
        .venv/bin/python app/components/export_figures.py --out app/dev/mock_screenshots

Uses kaleido (needs a local Chrome/Chromium). Charts whose inputs are missing are skipped.
"""
from __future__ import annotations

import argparse
import sys
import warnings
from pathlib import Path

APP = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(APP))
warnings.filterwarnings("ignore")

import logging  # noqa: E402

logging.getLogger("streamlit").setLevel(logging.ERROR)

from components import charts as C  # noqa: E402
from components import data as D  # noqa: E402
from components import features as F  # noqa: E402
from components import risk as R  # noqa: E402

EXAMPLE = dict(age=50, insurance="private_u65", fpl_band=F.FPL_BANDS[1], region="S", employed=True,
               health_fair_poor=False, married=True, college=False)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(D.REPO / "docs" / "screenshots"))
    ap.add_argument("--scale", type=float, default=2.0)
    a = ap.parse_args()
    out = Path(a.out)
    if not out.is_absolute():
        out = D.REPO / out
    out.mkdir(parents=True, exist_ok=True)

    est, tests = D.load("meps_estimates.csv"), D.load("meps_age_gap_tests.csv")
    curve, gap = D.load("nhis_age_curve.csv"), D.load("nhis_age_gap.csv")
    or_df, ue = D.load("meps_model_or.csv"), D.load("meps_unexpected_expense.csv")
    figs = {}
    figs["01_hero_dumbbell"] = C.hero_dumbbell(est, tests)
    figs["02_nhis_age_curve"] = C.age_curve(curve, None, gap=gap)
    if or_df is not None and len(or_df):
        models = list(dict.fromkeys(or_df["model"].astype(str)))
        mB = next((m for m in models if m.replace("Model", "").strip() == "B"), models[0])
        figs["03_forest_model_B"] = C.forest(or_df, mB)
        mA = next((m for m in models if m.replace("Model", "").strip() == "A"), None)
        if mA:
            figs["03b_forest_model_A"] = C.forest(or_df, mA)
    figs["04_income_bars"] = C.income_bars(est)
    figs["05_unexpected_expense"] = C.unexpected_expense(ue)
    figs["06_missed_care_by_worry"] = C.care_by_worry(est)

    model, err = D.risk_model()
    if model is not None:
        row = F.make_row(**EXAMPLE)
        p = R.predict(model, row)
        alt = dict(EXAMPLE, age=65, insurance="medicare_plus_private" if "medicare_plus_private" in F.INS_65 else F.INS_65[0])
        p_alt = R.predict(model, F.make_row(**alt))
        ag = D.load("ml_age_group_avg.csv")
        avg = None
        if ag is not None and len(ag):
            h = ag[ag["age_group"].astype(str).map(C._is_u65)]
            avg = float(h["mean_pred"].iloc[0]) if len(h) else None
        fig = C.risk_compare(p, avg, "Under 65", p_alt, "Same person at 65, Medicare + private")
        fig.add_annotation(x=0, y=-0.32, xref="paper", yref="paper", showarrow=False, xanchor="left",
                           text=("Example: age 50, private insurance, income 100-199% FPL, South, employed, "
                                 "married, good health, no degree · demo, not a clinical tool"),
                           font=dict(size=12, color=C.DARK_GREY))
        fig.update_layout(margin=dict(b=90))
        figs["07_risk_tool_example"] = (fig, "")
        print(f"risk example: p={p:.3f}, at 65 w/ Medicare+private p={p_alt:.3f}, avg u65={avg}")
    else:
        print("skip risk tool example:", err)

    for name, (fig, cap) in figs.items():
        if fig is None:
            print("skip", name, "(no data)")
            continue
        fig.update_layout(width=1200, height=max(fig.layout.height or 500, 450))
        if cap:
            fig.add_annotation(x=0, y=0, yshift=-80, xref="paper", yref="paper", showarrow=False, xanchor="left",
                               yanchor="top", text=C._wrap(cap, 140), font=dict(size=11, color=C.DARK_GREY),
                               align="left")
            fig.update_layout(margin=dict(b=170))
        C.fix_title(fig)
        path = out / f"{name}.png"
        fig.write_image(str(path), scale=a.scale)
        print("wrote", path)


if __name__ == "__main__":
    main()
