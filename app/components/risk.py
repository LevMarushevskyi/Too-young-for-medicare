"""Risk-tool helpers: prediction and per-person factor contributions."""
from __future__ import annotations

import math

import numpy as np
import pandas as pd

from components import features as F


def predict(model, row: pd.DataFrame) -> float:
    p = float(model.predict_proba(row)[:, 1][0])
    return min(1.0, max(0.0, p))


def _coef_items(explain: dict):
    """Yield (name, coef, ref) from a few plausible logit_explain.json layouts."""
    if not isinstance(explain, dict):
        return []
    coefs = explain.get("coefficients") or explain.get("coef") or explain.get("coefs")
    refs = (explain.get("reference_values") or explain.get("reference") or explain.get("means")
            or explain.get("centers") or {})
    items = []
    if isinstance(coefs, dict):
        for k, v in coefs.items():
            if isinstance(v, dict):
                items.append((k, v.get("coef", v.get("value")), v.get("ref", v.get("reference", refs.get(k) if isinstance(refs, dict) else None))))
            else:
                items.append((k, v, refs.get(k) if isinstance(refs, dict) else None))
    elif isinstance(coefs, list):
        for e in coefs:
            if isinstance(e, dict):
                nm = e.get("name") or e.get("term") or e.get("feature")
                items.append((nm, e.get("coef", e.get("value", e.get("estimate"))),
                              e.get("ref", e.get("reference", e.get("mean")))))
        if isinstance(refs, dict):
            items = [(n, c, r if r is not None else refs.get(n)) for n, c, r in items]
    elif isinstance(explain.get("features"), list):
        return _coef_items({"coefficients": explain["features"], "reference_values": refs})
    return [(n, c, r) for n, c, r in items if n is not None and c is not None]


def _value(name: str, row: dict):
    """Value of a (possibly one-hot / prefixed) design-matrix column for this person, plus its base feature."""
    base = name.split("__", 1)[1] if "__" in name else name
    for f in sorted(row, key=len, reverse=True):
        if base == f:
            try:
                return float(row[f]), f
            except (TypeError, ValueError):
                return None, f
        for sep in ("_", "=", "[", ":"):
            if base.startswith(f + sep):
                cat = base[len(f) + 1:].rstrip("]")
                v = row[f]
                if isinstance(v, (int, float, np.integer, np.floating)) and not isinstance(v, bool):
                    try:
                        return float(float(v) == float(cat)), f
                    except ValueError:
                        return None, f  # spline basis or similar: cannot evaluate here
                return float(str(v) == cat), f
    return None, None


def contributions(explain: dict | None, row: pd.DataFrame):
    """List of (feature, contribution in log-odds) sorted by |contribution|, or None if unavailable.

    Uses harmonize.explain_contributions (ML lane's reference implementation) when the JSON has
    its layout ({"features": {name: {type, coef|coef_per_unit|levels, mean}}}); else a generic parser.
    """
    if not explain:
        return None
    H = F._H
    if H is not None and hasattr(H, "explain_contributions") and isinstance(explain.get("features"), dict):
        try:
            res = H.explain_contributions(row, explain, top=len(explain["features"]))
            return [(d["feature"], float(d["contribution"])) for d in res]
        except Exception:  # noqa: BLE001
            pass
    r = row.iloc[0].to_dict()
    agg: dict[str, float] = {}
    for name, coef, ref in _coef_items(explain):
        if "intercept" in str(name).lower():
            continue
        v, f = _value(str(name), r)
        if v is None or f is None:
            continue
        try:
            c = float(coef) * (v - (float(ref) if ref is not None else 0.0))
        except (TypeError, ValueError):
            continue
        if math.isfinite(c):
            agg[f] = agg.get(f, 0.0) + c
    if not agg:
        return None
    return sorted(agg.items(), key=lambda kv: -abs(kv[1]))


def plain_words(feature: str, contrib: float, row: pd.DataFrame) -> str:
    v = row.iloc[0][feature]
    yesno = {
        "employed": ("being currently employed", "not being currently employed"),
        "health_fair_poor": ("fair or poor self-rated health", "good-or-better self-rated health"),
        "married": ("being married", "not being married"),
        "college": ("having a college degree", "not having a college degree"),
        "under65": ("being under 65", "being 65 or older"),
    }
    if feature in yesno:
        desc = yesno[feature][0] if int(float(v)) == 1 else yesno[feature][1]
    elif feature == "age":
        desc = f"age {int(float(v))}"
    else:
        lv = getattr(F._H, "LEVEL_LABELS", {}) if F._H is not None else {}
        desc = lv.get(str(v)) or f"{F.label(feature).lower()}: {F.label(str(v))}"
    direction = "raises" if contrib > 0 else "lowers"
    return f"**{desc[0].upper() + desc[1:]}** {direction} the estimate."
