"""Risk-tool feature definitions for the app.

python/harmonize.py is the single source of truth (BUILD_GUIDE 8.2). If it is
importable and exposes the constants below, they are used; otherwise the
fallback constants here (copied from BUILD_GUIDE 8.2) apply.
harmonize.py present as of 14:00 (FPL bands use "<100%" style labels); fallbacks kept for safety.
"""
from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
if str(REPO / "python") not in sys.path:
    sys.path.insert(0, str(REPO / "python"))

try:  # pragma: no cover - depends on other lane
    import harmonize as _H  # type: ignore
except Exception:  # noqa: BLE001
    _H = None

FEATURES = ["age", "under65", "fpl_band", "insurance", "region", "employed",
            "health_fair_poor", "married", "college"]
FPL_BANDS = ["<100", "100-199", "200-399", "400+"]
INS_U65 = ["private_u65", "public_u65", "uninsured_u65"]
INS_65 = ["medicare_plus_private", "medicare_only_or_public"]
REGIONS = ["NE", "MW", "S", "W"]


def _pick(*names, default):
    if _H is None:
        return default
    for n in names:
        v = getattr(_H, n, None)
        if v is not None:
            try:
                return list(v) if not isinstance(v, dict) else list(v.keys())
            except TypeError:
                pass
    return default


FEATURES = _pick("FEATURES", "FEATURE_COLUMNS", "MODEL_FEATURES", default=FEATURES)
FPL_BANDS = _pick("FPL_BANDS", "FPL_BAND_LEVELS", default=FPL_BANDS)
REGIONS = _pick("REGIONS", "REGION_LEVELS", default=REGIONS)
_ins_all = _pick("INSURANCE_LEVELS", "INSURANCE_CATS", "INSURANCE", default=INS_U65 + INS_65)
INS_U65 = [c for c in _ins_all if c.endswith("_u65")] or INS_U65
INS_65 = [c for c in _ins_all if not c.endswith("_u65")] or INS_65
HARMONIZE_LOADED = _H is not None

LABELS = {
    "private_u65": "Private / employer insurance",
    "public_u65": "Medicaid or other public only",
    "uninsured_u65": "Uninsured",
    "medicare_plus_private": "Medicare + private (Medigap / Advantage / employer)",
    "medicare_only_or_public": "Medicare only, or Medicare + Medicaid",
    "<100": "Under 100% of poverty line", "<100%": "Under 100% of poverty line",
    "100-199%": "100-199% of poverty line", "200-399%": "200-399% of poverty line",
    "400%+": "400% or more of poverty line",
    "100-199": "100-199% of poverty line",
    "200-399": "200-399% of poverty line",
    "400+": "400% or more of poverty line",
    "NE": "Northeast", "MW": "Midwest", "S": "South", "W": "West",
    "age": "Age", "under65": "Under 65", "fpl_band": "Household income",
    "insurance": "Insurance", "region": "Region", "employed": "Employment",
    "health_fair_poor": "Self-rated health", "married": "Marital status", "college": "Education",
}

# 2024 HHS poverty guidelines, 48 contiguous states + DC (ASPE). Alaska/Hawaii higher.
FPL_2024_BASE = 15060
FPL_2024_PER_PERSON = 5380


if _H is not None:
    LABELS.update(getattr(_H, "INSURANCE_PLAIN", {}) or {})
    LABELS.update({k: v for k, v in (getattr(_H, "FEATURE_LABELS", {}) or {}).items()})


def label(x: str) -> str:
    return LABELS.get(x, str(x).replace("_", " "))


def insurance_options(age: int) -> list[str]:
    return INS_U65 if age < 65 else INS_65


def fpl_pct(income: float, hh_size: int) -> float:
    g = FPL_2024_BASE + FPL_2024_PER_PERSON * (max(1, int(hh_size)) - 1)
    return 100.0 * float(income) / g


def fpl_band_from_pct(pct: float) -> str:
    if _H is not None:
        for fn in ("fpl_band_from_pct", "fpl_to_band", "fpl_band"):
            f = getattr(_H, fn, None)
            if callable(f):
                try:
                    v = f(pct)
                    if isinstance(v, str) and v in FPL_BANDS:
                        return v
                except Exception:  # noqa: BLE001
                    pass
    if pct < 100:
        return FPL_BANDS[0]
    if pct < 200:
        return FPL_BANDS[1]
    if pct < 400:
        return FPL_BANDS[2]
    return FPL_BANDS[3]


def make_row(age, insurance, fpl_band, region, employed, health_fair_poor, married, college):
    import pandas as pd

    if _H is not None and hasattr(_H, "build_feature_row"):
        return _H.build_feature_row(age=age, insurance=insurance, region=region, employed=employed,
                                    health_fair_poor=health_fair_poor, married=married, college=college,
                                    fpl_band=fpl_band)
    age = int(min(85, max(18, age)))
    row = dict(age=age, under65=int(age < 65), fpl_band=fpl_band, insurance=insurance, region=region,
               employed=int(bool(employed)), health_fair_poor=int(bool(health_fair_poor)),
               married=int(bool(married)), college=int(bool(college)))
    return pd.DataFrame([row])[[c for c in FEATURES if c in row] or list(row)]
