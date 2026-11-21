"""Plotly chart functions and shared styling (BUILD_GUIDE 10.0).

Every builder takes the raw processed DataFrame, drops suppressed rows itself
(nothing suppressed reaches a trace or hover text), fades flagged rows with a
dagger, computes a finding-style title from the data, and returns (fig, caption).
"""
from __future__ import annotations

import math

import numpy as np
import pandas as pd
import plotly.graph_objects as go

BLUE = "#0072B2"   # Under 65
GREY = "#9E9E9E"   # 65+
ACCENT = "#D55E00"  # highlights only (age-65 line)
INK = "#333333"
LIGHT_BLUE = "#56B4E9"
DARK_GREY = "#616161"
FADE = 0.4
DAGGER = "†"
CI_NOTE = "Error bars are 95% CIs"
DAGGER_NOTE = f"{DAGGER} interpret with caution (n < 60 or RSE > 30%)"
SUPP_NOTE = "cells with n < 30 or < 5 events are suppressed and not shown"

FAMILIES = {
    "Cancer SAQ (CSAQ)": ["any_csaq_strain", "worry_bills", "fam_stability_worry", "borrowed_debt"],
    "Family finances (FW, ESAQ, bills, OOP)": ["any_fw_strain", "debt_collector", "missed_payment", "late_rent",
                                               "late_util", "prob_pay_bills", "sacrificed_basics", "high_oop_burden"],
    "Access to care": ["delay_or_forgo_care_cost", "delay_or_forgo_rx_cost"],
}


def family_of(measure: str) -> str:
    for fam, ms in FAMILIES.items():
        if measure in ms:
            return fam
    return "Other"


def layout(fig: go.Figure, title: str, height: int = 460, **kw) -> go.Figure:
    nlines = title.count("<br>") + 1
    top = 70 + 24 * nlines
    fig.update_layout(template="simple_white", font=dict(size=14, color=INK),
                      
                      height=height + 26 * (nlines - 1), margin=dict(l=10, r=30, t=top, b=50),
                      legend=dict(orientation="h", yanchor="bottom", y=1.01, x=0, xanchor="left"),
                      hoverlabel=dict(font_size=13), **kw)
    fig.add_annotation(text=title, name="chart_title", x=0, xref="paper", xanchor="left", xshift=-(fig.layout.margin.l or 0) + 4,
                       y=1, yref="paper", yanchor="bottom", showarrow=False, align="left", font=dict(size=17, color=INK))
    return fix_title(fig)


def fix_title(fig: go.Figure) -> go.Figure:
    """Place the title just above the legend row (call again after changing height/margins)."""
    H = fig.layout.height or 450
    m = fig.layout.margin
    ph = max(100, H - (m.t or 0) - (m.b or 0))
    legend = any(t.showlegend is not False and t.name for t in fig.data) and fig.layout.showlegend is not False
    y = 1 + (40 if legend else 10) / ph
    fig.update_annotations(selector=dict(name="chart_title"), y=y)
    return fig


def _wrap(s: str, width: int = 80) -> str:
    words, lines, cur = str(s).split(), [], ""
    for w in words:
        if len(cur) + len(w) + 1 > width and cur:
            lines.append(cur)
            cur = w
        else:
            cur = f"{cur} {w}".strip()
    lines.append(cur)
    return "<br>".join(lines)


def caption(df: pd.DataFrame | None, source: str | None = None, weight: str | None = None,
            ci: bool = True, extra: str | None = None) -> str:
    srcs = source or (", ".join(sorted(df["source"].dropna().astype(str).unique())) if df is not None and "source" in df.columns and len(df) else "")
    if weight is None and df is not None and "weight_var" in df.columns:
        weight = ", ".join(sorted(df["weight_var"].dropna().astype(str).unique()))
    parts = [srcs or None, (f"{weight} weight" + ("s" if "," in weight else "")) if weight else None, extra]
    return " · ".join(p for p in parts if p)


def _vis(df: pd.DataFrame | None) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame()
    d = df.copy()
    if "suppressed" in d.columns:
        d = d[~d["suppressed"].astype(bool)]
    if "pct" in d.columns:
        d = d[d["pct"].notna()]
    if "flagged" not in d.columns:
        d["flagged"] = False
    d["flagged"] = d["flagged"].fillna(False).astype(bool)
    return d


def _err(d: pd.DataFrame, col="pct"):
    lo = (d[col] - d["ci_lo"]).clip(lower=0) if "ci_lo" in d else None
    hi = (d["ci_hi"] - d[col]).clip(lower=0) if "ci_hi" in d else None
    return lo, hi


def _hover(d: pd.DataFrame, name_col: str, group_col: str | None, show_n: bool) -> list[str]:
    out = []
    for _, r in d.iterrows():
        s = f"<b>{r[name_col]}</b>"
        if group_col:
            s += f"<br>{r[group_col]}"
        s += f"<br>{r['pct']:.1f}%"
        if pd.notna(r.get("ci_lo")) and pd.notna(r.get("ci_hi")):
            s += f" (95% CI {r['ci_lo']:.1f}–{r['ci_hi']:.1f})"
        if show_n and pd.notna(r.get("n_unweighted")) and r.get("n_unweighted", 0) >= 5:
            s += f"<br>unweighted n = {int(r['n_unweighted'])}"
        if r.get("flagged"):
            s += f"<br>{DAGGER} interpret with caution"
        out.append(s)
    return out


def _is_u65(g: str) -> bool:
    g = str(g).lower()
    return ("under" in g or "<65" in g or "18-64" in g or "u65" in g) and "65+" not in g.split(":")[0]


def age_color(g: str) -> str:
    return BLUE if _is_u65(g) else GREY


def _likely_phrase(u: float, o: float) -> str:
    if o > 0 and u / o >= 1.95:
        return f"{u / o:.1f}× as likely"
    if u > o:
        return "more likely"
    if u < o:
        return "less likely"
    return "as likely"


# ---------------------------------------------------------------- hero
def hero_dumbbell(est: pd.DataFrame | None, tests: pd.DataFrame | None = None,
                  families: list[str] | None = None, show_n: bool = False):
    d = _vis(est)
    if d.empty or "chart_id" not in d:
        return None, ""
    d = d[d["chart_id"] == "age_gap"].copy()
    if families:
        d = d[d["measure"].map(family_of).isin(families)]
    if d.empty:
        return None, ""
    d["is_u65"] = d["group"].map(_is_u65)
    rows = []
    for m, g in d.groupby("measure", sort=False):
        u = g[g.is_u65]
        o = g[~g.is_u65]
        rec = dict(measure=m, label=g["measure_label"].iloc[0], u=u.iloc[0] if len(u) else None,
                   o=o.iloc[0] if len(o) else None)
        gap = np.nan
        if rec["u"] is not None and rec["o"] is not None:
            gap = rec["u"]["pct"] - rec["o"]["pct"]
            if tests is not None and not tests.empty and "diff_pp" in tests:
                t = tests[tests["measure"] == m]
                if len(t) and pd.notna(t["diff_pp"].iloc[0]):
                    gap = float(t["diff_pp"].iloc[0])
        rec["gap"] = gap
        rec["flag"] = any(x is not None and bool(x["flagged"]) for x in (rec["u"], rec["o"]))
        rows.append(rec)
    rows.sort(key=lambda r: (-math.inf if pd.isna(r["gap"]) else r["gap"]))  # largest gap on top
    ylab = [_wrap(r["label"] + (f" {DAGGER}" if r["flag"] else ""), 38) for r in rows]

    fig = go.Figure()
    lx, ly = [], []
    for r, yl in zip(rows, ylab):
        if r["u"] is not None and r["o"] is not None:
            lx += [r["o"]["pct"], r["u"]["pct"], None]
            ly += [yl, yl, None]
    fig.add_trace(go.Scatter(x=lx, y=ly, mode="lines", line=dict(color="#CFCFCF", width=4),
                             hoverinfo="skip", showlegend=False))
    for key, name, color in (("o", "65+", GREY), ("u", "Under 65", BLUE)):
        legend_done = False
        for faded in (False, True):
            pts = [(r[key], yl) for r, yl in zip(rows, ylab) if r[key] is not None and bool(r[key]["flagged"]) == faded]
            if not pts:
                continue
            pd_ = pd.DataFrame([p[0] for p in pts])
            pd_["ylab"] = [p[1] for p in pts]
            lo, hi = _err(pd_)
            fig.add_trace(go.Scatter(
                x=pd_["pct"], y=pd_["ylab"], mode="markers", name=name, legendgroup=name,
                showlegend=not legend_done,
                marker=dict(color=color, size=15, opacity=FADE if faded else 1, line=dict(color="white", width=1)),
                error_x=dict(type="data", symmetric=False, array=hi, arrayminus=lo, color=color,
                             thickness=1.5, width=4),
                hovertext=_hover(pd_, "measure_label", "group", show_n), hoverinfo="text"))
            legend_done = True
    for r, yl in zip(rows, ylab):
        if pd.notna(r["gap"]):
            fig.add_annotation(x=1.0, xref="paper", xanchor="left", y=yl, text=f"<b>{r['gap']:+.0f} pp</b>",
                               showarrow=False, font=dict(color=BLUE if r["gap"] > 0 else DARK_GREY, size=13))
    # title
    paired = [r for r in rows if pd.notna(r["gap"])]
    title = "Financial strain among breast cancer survivors, by age"
    if paired:
        lead = next((r for r in paired if r["measure"] == "any_csaq_strain"), max(paired, key=lambda r: r["gap"]))
        u, o = lead["u"]["pct"], lead["o"]["pct"]
        nhigher = sum(r["gap"] > 0 for r in paired)
        title = (f"Survivors under 65 were {_likely_phrase(u, o)} to report {lead['label'].lower()} "
                 f"({u:.0f}% vs {o:.0f}%)<br><sup>Under-65 estimate higher on {nhigher} of {len(paired)} measures · "
                 f"gap in percentage points at right</sup>")
    layout(fig, title, height=max(380, 70 + 48 * len(rows)))
    fig.update_layout(margin=dict(r=80))
    fig.update_xaxes(title="Weighted % of survivors", range=[0, _xmax(d)], ticksuffix="%")
    fig.update_yaxes(title=None, categoryorder="array", categoryarray=ylab)
    cap = caption(d)
    return fig, cap


def _xmax(d: pd.DataFrame) -> float:
    m = pd.to_numeric(d.get("ci_hi", d["pct"]), errors="coerce").max()
    m = d["pct"].max() if pd.isna(m) else max(m, d["pct"].max())
    return float(min(100, max(10, math.ceil((m + 5) / 10) * 10)))


# ---------------------------------------------------------------- NHIS age curve
def age_curve(curve: pd.DataFrame | None, measure: str | None = None, show_n: bool = False,
              gap: pd.DataFrame | None = None):
    if curve is None or curve.empty:
        return None, ""
    c = curve.copy()
    if measure is None:
        measure = "prob_pay_bills" if "prob_pay_bills" in set(c["measure"]) else c["measure"].iloc[0]
    c = c[c["measure"] == measure]
    label = c["measure_label"].iloc[0] if len(c) else measure
    bands = c[c["age_mid"].notna()].sort_values("age_mid").copy()
    pooled = c[c["age_mid"].isna()]
    sup = bands["suppressed"].astype(bool) if "suppressed" in bands else pd.Series(False, index=bands.index)
    for col in ("pct", "ci_lo", "ci_hi"):
        bands.loc[sup, col] = np.nan
    if "flagged" not in bands:
        bands["flagged"] = False
    bands["flagged"] = bands["flagged"].fillna(False).astype(bool)
    vis = bands[bands["pct"].notna()]
    fig = go.Figure()
    for seg, color in ((bands["age_mid"] < 65, BLUE), (bands["age_mid"] >= 65, GREY)):
        b = bands[seg]
        fig.add_trace(go.Scatter(x=list(b["age_mid"]) + list(b["age_mid"])[::-1],
                                 y=list(b["ci_hi"]) + list(b["ci_lo"])[::-1], fill="toself", mode="lines",
                                 fillcolor=color, opacity=0.18, line=dict(width=0), hoverinfo="skip",
                                 showlegend=False))
    fig.add_trace(go.Scatter(x=bands["age_mid"], y=bands["pct"], mode="lines", line=dict(color=DARK_GREY, width=2),
                             connectgaps=False, hoverinfo="skip", showlegend=False))
    for faded in (False, True):
        v = vis[vis["flagged"] == faded]
        if v.empty:
            continue
        txt = []
        for _, r in v.iterrows():
            s = f"<b>Ages {r['age_band']}</b><br>{r['pct']:.1f}% (95% CI {r['ci_lo']:.1f}–{r['ci_hi']:.1f})"
            if show_n and r.get("n_unweighted", 0) >= 5:
                s += f"<br>unweighted n = {int(r['n_unweighted'])}"
            if faded:
                s += f"<br>{DAGGER} interpret with caution"
            txt.append(s)
        fig.add_trace(go.Scatter(x=v["age_mid"], y=v["pct"], mode="markers", showlegend=False,
                                 marker=dict(size=11, color=[BLUE if a < 65 else GREY for a in v["age_mid"]],
                                             opacity=FADE if faded else 1, line=dict(color="white", width=1)),
                                 hovertext=txt, hoverinfo="text"))
    fig.add_vline(x=65, line=dict(color=ACCENT, dash="dash", width=2))
    fig.add_annotation(x=65, y=1, yref="paper", text="Medicare eligibility (65)", showarrow=False,
                       xanchor="left", xshift=6, font=dict(color=ACCENT))
    title = f"{label} by age"
    pn = pooled_nhis(curve, measure, gap)
    if pn:
        u, o = pn[0], pn[1]
        lead = "Lower after Medicare age" if o < u else "No drop after Medicare age"
        title = f"{lead}: {label[0].lower() + label[1:]} — {u:.0f}% under 65 vs {o:.0f}% at 65+"
    elif len(vis):
        u = vis[vis.age_mid < 65]["pct"].mean()
        o = vis[vis.age_mid >= 65]["pct"].mean()
        if pd.notna(u) and pd.notna(o):
            title = f"{label}: band average {u:.0f}% under 65 vs {o:.0f}% at 65+"
    layout(fig, _wrap(title, 90), height=440)
    ymax = _xmax(vis) if len(vis) else 100
    fig.update_yaxes(title="Weighted %", range=[0, ymax], ticksuffix="%")
    fig.update_xaxes(title="Age band (points at weighted mean age)",
                     tickvals=list(vis["age_mid"]), ticktext=list(vis["age_band"]))
    src = c["source"].iloc[0] if "source" in c and len(c) else "NHIS 2021–2024"
    return fig, caption(None, source=src, weight="pooled WTFA_A / 4",
                        extra="shaded band = 95% CI; ages top-coded at 85")


def pooled_nhis(curve: pd.DataFrame | None, measure="prob_pay_bills", gap: pd.DataFrame | None = None):
    """(under65 pct, 65+ pct, label) from nhis_age_gap.csv, or pooled rows (age_mid blank) in the curve."""
    if gap is not None and not gap.empty and "group" in gap:
        c = gap[gap["measure"] == measure].rename(columns={"group": "age_band"})
    elif curve is not None and not curve.empty:
        c = curve[(curve["measure"] == measure) & curve["age_mid"].isna()]
    else:
        return None
    c = c[c["pct"].notna()]
    c = c[~c["suppressed"].astype(bool)] if "suppressed" in c else c
    u = c[c["age_band"].map(_is_u65)]
    o = c[~c["age_band"].map(_is_u65)]
    if len(u) and len(o):
        return float(u["pct"].iloc[0]), float(o["pct"].iloc[0]), str(c["measure_label"].iloc[0])
    return None


# ---------------------------------------------------------------- forest
def _is_age_term(t: str, lab: str) -> bool:
    s = f"{t} {lab}".lower()
    return "age" in s or "65" in s


def forest(or_df: pd.DataFrame | None, model: str):
    if or_df is None or or_df.empty:
        return None, ""
    d = or_df[or_df["model"].astype(str) == str(model)].copy()
    sens = None
    if "lonely_psu_method" in d and d["lonely_psu_method"].nunique() > 1:
        prim = "adjust" if (d["lonely_psu_method"] == "adjust").any() else d["lonely_psu_method"].iloc[0]
        sens = ", ".join(x for x in d["lonely_psu_method"].dropna().unique() if x != prim)
        d = d[d["lonely_psu_method"] == prim]
    model = str(model).replace("Model", "").strip()
    d = d[~d["term"].astype(str).str.contains("ntercept", na=False)]
    d = d[d["or"].notna() & (d["or"] > 0)]
    if d.empty:
        return None, ""
    d["term_label"] = d["term_label"].fillna(d["term"])
    d = d.iloc[::-1]
    colors = [BLUE if _is_age_term(t, l) else DARK_GREY for t, l in zip(d["term"], d["term_label"])]
    txt = [f"<b>{l}</b><br>aOR {o:.2f} (95% CI {lo:.2f}–{hi:.2f})" + (f"<br>p = {p:.3f}" if pd.notna(p) else "")
           for l, o, lo, hi, p in zip(d["term_label"], d["or"], d["ci_lo"], d["ci_hi"], d.get("p_value", [np.nan] * len(d)))]
    fig = go.Figure(go.Scatter(
        x=d["or"], y=d["term_label"], mode="markers", marker=dict(color=colors, size=13, symbol="square"),
        error_x=dict(type="data", symmetric=False, array=d["ci_hi"] - d["or"], arrayminus=d["or"] - d["ci_lo"],
                     color=DARK_GREY, thickness=1.5), hovertext=txt, hoverinfo="text", showlegend=False))
    age = d[[_is_age_term(t, l) for t, l in zip(d["term"], d["term_label"])]]
    n = int(d["n"].iloc[0]) if "n" in d and pd.notna(d["n"].iloc[0]) else None
    title = "Adjusted odds ratios"
    if len(age):
        a = age.iloc[0]
        title = (f"{a['term_label']}: adjusted odds ratio {a['or']:.2f} "
                 f"(95% CI {a['ci_lo']:.2f}–{a['ci_hi']:.2f})")
    lo = max(0.02, float(d["ci_lo"].min()) * 0.8)
    hi = float(d["ci_hi"].max()) * 1.25
    layout(fig, _wrap(title, 90), height=max(320, 90 + 55 * len(d)))
    ticks = [t for t in (0.1, 0.25, 0.5, 1, 2, 4, 8, 16, 32) if lo <= t <= hi]
    fig.update_xaxes(type="log", title="Adjusted odds ratio (log scale)", range=[math.log10(lo), math.log10(hi)],
                     tickvals=ticks, ticktext=[f"{t:g}" for t in ticks], minor=dict(showgrid=False, ticks=""))
    fig.update_yaxes(title=None)
    # Reference line at OR = 1 as a trace (a vline shape did not render on the log axis)
    fig.add_trace(go.Scatter(x=[1, 1], y=[d["term_label"].iloc[0], d["term_label"].iloc[-1]], mode="lines",
                             line=dict(color=INK, dash="dot", width=1), hoverinfo="skip", showlegend=False))
    extra = "survey-weighted logistic regression" + (f", n = {n}" if n else "")
    return fig, " · ".join(["MEPS 2024", "CSAQW24F weight", extra,
                            "dotted line = no difference (OR = 1)"])


# ---------------------------------------------------------------- grouped bars
def _grouped_bars(d: pd.DataFrame, x_col: str, color_col: str, colors: dict, show_n: bool,
                  horizontal: bool = False, x_order=None):
    fig = go.Figure()
    keys = list(dict.fromkeys(d[color_col]))
    for k in keys:
        g = d[d[color_col] == k]
        if x_order is not None:
            g = g.set_index(x_col).reindex([x for x in x_order if x in set(g[x_col])]).reset_index()
        lo, hi = _err(g)
        xs = [str(x) for x in g[x_col]]
        txt = [f"{p:.0f}%{(' ' + DAGGER) if f else ''}" for p, f in zip(g["pct"], g["flagged"])]
        common = dict(name=str(k), marker=dict(color=colors.get(k, DARK_GREY),
                                               opacity=[FADE if f else 1 for f in g["flagged"]]),
                      text=txt, textposition="outside", cliponaxis=False,
                      hovertext=_hover(g, "measure_label", "group", show_n), hoverinfo="text")
        if horizontal:
            fig.add_trace(go.Bar(y=xs, x=g["pct"], orientation="h",
                                 error_x=dict(type="data", symmetric=False, array=hi, arrayminus=lo, color=INK, thickness=1.2),
                                 **common))
        else:
            fig.add_trace(go.Bar(x=xs, y=g["pct"],
                                 error_y=dict(type="data", symmetric=False, array=hi, arrayminus=lo, color=INK, thickness=1.2),
                                 **common))
    fig.update_layout(barmode="group", bargap=0.25)
    return fig


def _two(d, measure, g_hi, g_lo):
    a = d[(d["measure"] == measure) & (d["group"] == g_hi)]
    b = d[(d["measure"] == measure) & (d["group"] == g_lo)]
    if len(a) and len(b):
        return float(a["pct"].iloc[0]), float(b["pct"].iloc[0]), a["measure_label"].iloc[0]
    return None


def income_bars(est: pd.DataFrame | None, show_n: bool = False):
    d = _vis(est)
    if d.empty:
        return None, ""
    d = d[(d["chart_id"] == "income") & d["measure"].isin(["worry_bills", "any_fw_strain"])]
    if d.empty:
        return None, ""
    order = list(dict.fromkeys(est[est["chart_id"] == "income"]["group"]))
    labels = dict(zip(d["measure"], d["measure_label"]))
    d = d.assign(mlabel=d["measure"].map(labels))
    colors = {labels.get("worry_bills"): BLUE, labels.get("any_fw_strain"): LIGHT_BLUE}
    fig = _grouped_bars(d, "group", "mlabel", colors, show_n, x_order=order)
    title = "Financial strain by family income"
    lo_g = next((g for g in order if g.lower().startswith("low")), order[0] if order else None)
    hi_g = next((g for g in order if g.lower().startswith("high")), order[-1] if order else None)
    t = _two(d, "worry_bills", lo_g, hi_g) if lo_g and hi_g else None
    if t:
        verb = "more often" if t[0] > t[1] else "no more often"
        title = f"Lower-income survivors worried about medical bills {verb} than high-income survivors ({t[0]:.0f}% vs {t[1]:.0f}%)"
    layout(fig, _wrap(title, 90))
    fig.update_yaxes(title="Weighted %", range=[0, _xmax(d)], ticksuffix="%")
    fig.update_xaxes(title="Family income (% of federal poverty level)")
    return fig, caption(d)


def care_by_worry(est: pd.DataFrame | None, show_n: bool = False):
    d = _vis(est)
    if d.empty:
        return None, ""
    ids = ("care_by_worry", "behavior_link")
    d = d[d["chart_id"].isin(ids)]
    if d.empty:
        return None, ""
    groups = list(dict.fromkeys(est[est["chart_id"].isin(ids)]["group"]))
    worried = next((g for g in groups if not str(g).lower().startswith("no")), groups[0])
    colors = {g: (BLUE if g == worried else GREY) for g in groups}
    fig = _grouped_bars(d, "measure_label", "group", colors, show_n)
    other = next((g for g in groups if g != worried), None)
    title = "Cost-related missed care, by worry about medical bills"
    t = None
    for m_ in ("csaq_delay_rx", "delay_or_forgo_rx_cost", "delay_or_forgo_care_cost"):
        t = _two(d, m_, worried, other) if other else None
        if t:
            break
    if t:
        title = (f"Survivors worried about bills more often reported {t[2][0].lower() + t[2][1:]}: "
                 f"{t[0]:.0f}% vs {t[1]:.0f}% among those not worried") if t[0] > t[1] else (
                 f"{t[2]}: {t[0]:.0f}% among survivors worried about bills vs {t[1]:.0f}% among those not worried")
    elif other:
        title += " (some cells suppressed: too few respondents)"
    layout(fig, _wrap(title, 90))
    fig.update_yaxes(title="Weighted %", range=[0, _xmax(d)], ticksuffix="%")
    fig.update_xaxes(title=None)
    return fig, caption(d)


def treatment_bars(est: pd.DataFrame | None, show_n: bool = False):
    d = _vis(est)
    if d.empty:
        return None, ""
    d = d[d["chart_id"] == "treatment"]
    if d.empty:
        return None, ""
    groups = list(dict.fromkeys(est[est["chart_id"] == "treatment"]["group"]))
    treated = next((g for g in groups if not str(g).lower().startswith("not")), groups[0])
    colors = {g: (BLUE if g == treated else GREY) for g in groups}
    fig = _grouped_bars(d, "measure_label", "group", colors, show_n)
    other = next((g for g in groups if g != treated), None)
    title = "Financial strain by current cancer treatment"
    t = _two(d, "worry_bills", treated, other) if other else None
    if t:
        title = f"Bill worry: {t[0]:.0f}% among those in treatment vs {t[1]:.0f}% not in treatment (weighted)"
    layout(fig, _wrap(title, 90))
    fig.update_yaxes(title="Weighted %", range=[0, _xmax(d)], ticksuffix="%")
    fig.update_xaxes(title=None)
    return fig, caption(d)


def insurance_bars(est: pd.DataFrame | None, measure: str = "worry_bills", show_n: bool = False):
    d = _vis(est)
    if d.empty:
        return None, ""
    ids = ("insurance", "insurance_age")
    allrows = est[est["chart_id"].isin(ids) & (est["measure"] == measure)]
    d = d[d["chart_id"].isin(ids) & (d["measure"] == measure)]
    if d.empty:
        return None, ""
    order = list(dict.fromkeys(allrows["group"]))[::-1]
    d = d.set_index("group").reindex([g for g in order if g in set(d["group"])]).reset_index()
    lo, hi = _err(d)
    ylab = [str(g) + (f" {DAGGER}" if f else "") for g, f in zip(d["group"], d["flagged"])]
    fig = go.Figure(go.Bar(y=ylab, x=d["pct"], orientation="h",
                           marker=dict(color=[age_color(g) for g in d["group"]],
                                       opacity=[FADE if f else 1 for f in d["flagged"]]),
                           error_x=dict(type="data", symmetric=False, array=hi, arrayminus=lo, color=INK),
                           text=[f"{p:.0f}%" for p in d["pct"]], textposition="outside", cliponaxis=False,
                           hovertext=_hover(d, "measure_label", "group", show_n), hoverinfo="text"))
    nsup = int(allrows["suppressed"].astype(bool).sum()) if "suppressed" in allrows else 0
    label = allrows["measure_label"].iloc[0]
    top = d.loc[d["pct"].idxmax()]
    title = f"{label}: highest in “{top['group']}” ({top['pct']:.0f}%)"
    layout(fig, _wrap(title, 90), height=max(320, 90 + 50 * len(d)))
    fig.update_xaxes(title="Weighted %", range=[0, _xmax(d)], ticksuffix="%")
    extra = (f"{nsup} insurance group{'s' if nsup > 1 else ''} hidden (too few respondents)") if nsup else None
    return fig, caption(d, extra=extra)


def _is_income_group(g: str) -> bool:
    g = str(g).lower()
    return "fpl" in g or "%" in g or g.startswith(("low", "middle", "high"))


def unexpected_expense(ue: pd.DataFrame | None, by: str = "income", show_n: bool = False):
    if ue is None or ue.empty:
        return None, ""
    if by == "age":
        ue = ue[ue["group"].astype(str).str.lower().map(lambda g: ("65" in g) and not _is_income_group(g))]
    else:
        ue = ue[ue["group"].map(_is_income_group)] if ue["group"].map(_is_income_group).any() else ue
    if ue.empty:
        return None, ""
    order = list(dict.fromkeys(ue["group"]))
    d = _vis(ue)
    if d.empty:
        return None, ""
    levels = sorted(d["response_level"].unique())
    palette = ["#08306B", "#2171B5", "#6BAED6", "#C6DBEF", "#EEEEEE"]
    fig = go.Figure()
    # Suppressed levels are shown as one grey "suppressed" block at the left so the shown
    # segments keep their true positions (complementary suppression in R guarantees the
    # combined suppressed block holds >= 5 persons). No value in text or hover.
    shown = d.groupby("group")["pct"].sum().reindex(order[::-1])
    gap = (100 - shown).clip(lower=0)
    gap = gap[(gap > 0.5) & gap.index.isin(ue.loc[ue["suppressed"].astype(bool), "group"])]
    if len(gap):
        fig.add_trace(go.Bar(y=list(gap.index), x=list(gap.values), orientation="h",
                             name="Suppressed (too few respondents)", marker_color="#EEEEEE",
                             marker_line=dict(color="#BDBDBD", width=1), hoverinfo="text",
                             hovertext=["Suppressed: too few respondents"] * len(gap)))
    for i, lvl in enumerate(levels):
        g = d[d["response_level"] == lvl].set_index("group").reindex(order[::-1]).dropna(subset=["pct"]).reset_index()
        lab = g["response_label"].iloc[0] if len(g) else str(lvl)
        txt = []
        for _, r in g.iterrows():
            s = f"<b>{r['group']}</b><br>{lab}: {r['pct']:.1f}%"
            if pd.notna(r.get("ci_lo")):
                s += f" (95% CI {r['ci_lo']:.1f}–{r['ci_hi']:.1f})"
            txt.append(s)
        fig.add_trace(go.Bar(y=g["group"], x=g["pct"], orientation="h", name=lab,
                             marker_color=palette[i % len(palette)], hovertext=txt, hoverinfo="text",
                             text=[f"{p:.0f}%" if p >= 6 else "" for p in g["pct"]], textposition="inside",
                             insidetextanchor="middle",
                             textfont=dict(color="white" if i < 2 else INK)))
    fig.update_layout(barmode="stack")
    title = f"Confidence covering an unexpected expense, by {'age group' if by == 'age' else 'income'}"
    low = [l for l in levels if l <= 2]
    if by == "age":
        lo_g = next((g for g in order if _is_u65(g)), order[0])
        hi_g = next((g for g in order if not _is_u65(g)), order[-1])
    else:
        lo_g = next((g for g in order if g.lower().startswith("low")), order[0])
        hi_g = next((g for g in order if g.lower().startswith("high")), order[-1])
    nm_lo, nm_hi = ("under-65", "65+") if by == "age" else ("lower-income", "high-income")
    a = d[(d["group"] == lo_g) & d["response_level"].isin(low)]
    b = d[(d["group"] == hi_g) & d["response_level"].isin(low)]
    sup_any = bool(ue["suppressed"].astype(bool).any())
    if len(a) == len(low) and len(b) == len(low) and low:
        title = (f"{a['pct'].sum():.0f}% of {nm_lo} survivors were not confident they could cover an unexpected "
                 f"expense vs {b['pct'].sum():.0f}% of {nm_hi} survivors")
    elif len(a) == len(low) and low:
        title = (f"{a['pct'].sum():.0f}% of {nm_lo} survivors were not confident they could cover an unexpected "
                 f"expense<br><sup>Not-confident categories suppressed for the {nm_hi} group (too few respondents)</sup>")
    head, _, sub = title.partition("<br>")
    layout(fig, _wrap(head, 90) + ("<br>" + sub if sub else ""), height=380)
    fig.update_xaxes(title="Weighted % (100% stacked)", range=[0, 100], ticksuffix="%")
    fig.update_yaxes(categoryorder="array", categoryarray=order[::-1])
    fig.update_layout(legend=dict(traceorder="normal"))
    sup_any = bool(ue["suppressed"].astype(bool).any())
    extra = "grey = categories combined because too few respondents to show separately" if sup_any else None
    return fig, caption(None, source="MEPS 2024", weight="PERWT24F", ci=False, extra=extra)


# ---------------------------------------------------------------- ML
def calibration(cal: pd.DataFrame | None):
    if cal is None or cal.empty:
        return None, ""
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=[0, 1], y=[0, 1], mode="lines", line=dict(color=GREY, dash="dot"),
                             name="Perfect calibration", hoverinfo="skip"))
    names = {"nhis_cv": ("NHIS cross-validation", DARK_GREY), "meps_external": ("MEPS 2024 external", BLUE)}
    for ds, g in cal.groupby("dataset"):
        g = g[pd.to_numeric(g["n"], errors="coerce").fillna(0) >= 5] if "n" in g else g
        nm, col = names.get(ds, (ds, ACCENT))
        flg = (g["flagged"].astype(str).str.lower() == "true") if "flagged" in g else pd.Series(False, index=g.index)
        fig.add_trace(go.Scatter(x=g["mean_pred"], y=g["obs_rate"], mode="lines+markers", name=nm,
                                 line=dict(color=col),
                                 marker=dict(size=9, opacity=[FADE if f else 1 for f in flg]),
                                 text=[f" {DAGGER} n<60, interpret with caution" if f else "" for f in flg],
                                 hovertemplate="predicted %{x:.2f}<br>observed %{y:.2f}%{text}<extra>" + nm + "</extra>"))
    m = float(max(cal["mean_pred"].max(), cal["obs_rate"].max(), 0.1)) * 1.1
    layout(fig, "Calibration: predicted vs observed risk by bin of predicted risk", height=400)
    fig.update_xaxes(title="Mean predicted probability", range=[0, min(1, m)])
    fig.update_yaxes(title="Observed rate (weighted)", range=[0, min(1, m)])
    return fig, (f"NHIS: 10 bins; MEPS: 5 bins (fewer events) · survey-weighted · faded points {DAGGER} = bin n < 60")


def importance(imp: pd.DataFrame | None):
    if imp is None or imp.empty:
        return None, ""
    d = imp.sort_values("importance")
    lab = d["feature_label"].fillna(d["feature"]) if "feature_label" in d else d["feature"]
    fig = go.Figure(go.Bar(y=lab, x=d["importance"], orientation="h", marker_color=BLUE,
                           error_x=dict(type="data", array=d.get("importance_sd"), color=INK)))
    top = lab.iloc[-1]
    layout(fig, f"{top} contributes most to the model's predictions", height=max(300, 80 + 40 * len(d)))
    meth = d["method"].iloc[0] if "method" in d else "permutation importance"
    fig.update_xaxes(title=f"Importance ({meth})")
    nice = "Permutation importance: drop in AUC when a feature is shuffled" if "permutation" in str(meth) else meth
    return fig, f"{nice} · error bars = ±1 SD across repeats"


def risk_compare(p: float, avg: float | None, age_label: str, p_alt: float | None = None, alt_label: str = ""):
    ys, xs, cs = ["This person"], [p * 100], [BLUE if age_label.startswith("Under") else GREY]
    if p_alt is not None:
        ys.append(alt_label)
        xs.append(p_alt * 100)
        cs.append(GREY)
    if avg is not None:
        ys.append(f"Average, {age_label} (training data)")
        xs.append(avg * 100)
        cs.append("#BDBDBD")
    fig = go.Figure(go.Bar(y=ys[::-1], x=xs[::-1], orientation="h", marker_color=cs[::-1],
                           text=[f"{x:.0f}%" for x in xs[::-1]], textposition="outside", cliponaxis=False,
                           hovertemplate="%{y}: %{x:.1f}%<extra></extra>"))
    title = f"Estimated risk {p*100:.0f}%"
    if avg is not None:
        rel = "above" if p > avg else "below" if p < avg else "equal to"
        title += f", {rel} the {avg*100:.0f}% average for survivors {age_label.lower()}"
    if p_alt is not None:
        title += f"<br><sup>Same person at 65 with Medicare + private: {p_alt*100:.0f}%</sup>"
    layout(fig, title, height=260 + 30 * len(ys))
    fig.update_layout(margin=dict(t=95))
    fix_title(fig)
    fig.update_xaxes(title="Predicted probability of problems paying medical bills", range=[0, max(xs) * 1.25 + 5],
                     ticksuffix="%")
    return fig


def contributions_bar(contribs: list[tuple[str, float]]):
    d = contribs[::-1]
    fig = go.Figure(go.Bar(y=[a for a, _ in d], x=[b for _, b in d], orientation="h",
                           marker_color=[ACCENT if b > 0 else GREY for _, b in d],
                           hovertemplate="%{y}: %{x:+.2f} log-odds<extra></extra>"))
    layout(fig, "What pushes this estimate up (orange) or down (grey)", height=260)
    fig.update_xaxes(title="Contribution vs. an average survivor (log-odds)", zeroline=True)
    return fig
