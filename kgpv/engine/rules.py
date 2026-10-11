"""Versioned, interpretable screening profiles; these are not engineering limits."""

import json
from pathlib import Path
import numpy as np
from .features import extract_features
from ..classify import tp_classify, irradiation_classify, combine, ZONE_LABELS

RULE_FILE = Path(__file__).with_name("rules-v1.json")
TECH_FEATURES = {
    "pv": ["ghi_annual_kwh_m2", "solar_weighted_temperature_c", "weak_month_ratio"],
    "hybrid": [
        "ghi_annual_kwh_m2",
        "weak_month_ratio",
        "temperature_coldest_month_c",
        "temperature_warmest_month_c",
    ],
    "bess": ["temperature_coldest_month_c", "temperature_warmest_month_c"],
}
KG_SIMPLE = [
    "No data",
    "Tropical · very sunny",
    "Tropical · sunny",
    "Desert · very sunny",
    "Desert · sunny",
    "Steppe · very sunny",
    "Steppe · sunny",
    "Temperate · sunny",
    "Temperate · moderate sun",
    "Temperate · low sun",
    "Cold · moderate sun",
    "Cold · low sun",
    "Polar · low sun",
]


def load_rules(path=None):
    r = json.loads(Path(path or RULE_FILE).read_text())
    for key, length in [
        ("solar_thresholds_kwh_m2_year", 3),
        ("pv_temperature_thresholds_c", 2),
        ("weak_month_ratio_thresholds", 2),
    ]:
        a = np.asarray(r[key], float)
        if len(a) != length or not np.isfinite(a).all() or (np.diff(a) <= 0).any():
            raise ValueError(f"Invalid rule thresholds: {key}")
    if not 0 < r["weak_month_ratio_thresholds"][0] < r["weak_month_ratio_thresholds"][1] <= 1:
        raise ValueError("Seasonality ratios must be within (0, 1]")
    if not r["bess_cold_month_c"] < r["bess_hot_month_c"]:
        raise ValueError("Cold threshold must be below hot threshold")
    if r["solar_thresholds_kwh_m2_year"][0] <= 0:
        raise ValueError("Solar thresholds must be positive")
    for key, n in [
        ("solar_names", 4),
        ("pv_temperature_names", 3),
        ("season_names", 3),
        ("bess_names", 4),
    ]:
        if len(r[key]) != n or not all(isinstance(x, str) and x for x in r[key]):
            raise ValueError(f"Invalid labels: {key}")
    return r


def class_labels(technology, rules=None):
    r = rules or load_rules()
    if technology == "pv":
        return ["No data"] + [
            f"{s} · {t}" for s in r["solar_names"] for t in r["pv_temperature_names"]
        ]
    if technology == "hybrid":
        return ["No data"] + [
            f"{s} · {t.lower()}" for s in r["season_names"] for t in r["bess_names"]
        ]
    if technology == "bess":
        return ["No data"] + r["bess_names"]
    if technology == "kgpv":
        return KG_SIMPLE
    raise ValueError("Technology must be pv, hybrid, bess or kgpv")


def classify_features(features, technology="pv", rules=None):
    r = rules or load_rules()
    if technology not in TECH_FEATURES:
        raise ValueError("Use pv, hybrid or bess")
    f = features
    required = TECH_FEATURES[technology]
    for key in required:
        if key not in f:
            raise ValueError(f"Missing required feature: {key}")
    ok = np.isfinite(f[required].to_numpy(float)).all(1)
    col = lambda name: f[name].to_numpy(float) if name in f else np.full(len(f), np.nan)
    sun = np.searchsorted(r["solar_thresholds_kwh_m2_year"], col("ghi_annual_kwh_m2"), side="left")
    t = col("solar_weighted_temperature_c")
    lo, hi = r["pv_temperature_thresholds_c"]
    heat = np.where(t < lo, 0, np.where(t > hi, 2, 1))
    cold = col("temperature_coldest_month_c") < r["bess_cold_month_c"]
    hot = col("temperature_warmest_month_c") > r["bess_hot_month_c"]
    thermal = cold.astype(int) + 2 * hot.astype(int)
    seasonal = np.searchsorted(
        r["weak_month_ratio_thresholds"], col("weak_month_ratio"), side="right"
    )
    if technology == "pv":
        code = sun * 3 + heat + 1
    elif technology == "hybrid":
        code = seasonal * 4 + thermal + 1
    else:
        code = thermal + 1
    code = np.where(ok, code, 0).astype(int)
    labels = class_labels(technology, r)
    result = f[[c for c in ["location_id", "latitude", "longitude"] if c in f]].copy()
    result["technology"] = technology
    result["zone_id"] = code
    result["zone_name"] = [labels[c] for c in code]
    result["status"] = np.where(ok, "Experimental profile", "Insufficient data")
    result["reason"] = [
        "; ".join(k for k in required if not np.isfinite(float(f.iloc[i][k]))) if not v else ""
        for i, v in enumerate(ok)
    ]
    result["seasonality"] = [
        r["season_names"][int(x)] if np.isfinite(y) else "Not available"
        for x, y in zip(seasonal, col("weak_month_ratio"))
    ]
    result["thermal_context"] = [
        r["bess_names"][int(x)] if np.isfinite(a) and np.isfinite(b) else "Not available"
        for x, a, b in zip(
            thermal, col("temperature_coldest_month_c"), col("temperature_warmest_month_c")
        )
    ]
    result["scheme_version"] = r["version"]
    result.attrs.update(f.attrs)
    return result


def classify_kgpv(cube):
    f = extract_features(cube)
    n = len(cube.ids)
    tp = tp_classify(
        cube.get("temperature").reshape(12, n, 1),
        cube.get("precipitation").reshape(12, n, 1),
        cube.latitude,
    ).ravel()
    zone, _ = combine(tp, irradiation_classify(f.ghi_annual_kwh_m2.to_numpy()))
    out = f[["location_id", "latitude", "longitude"]].copy()
    out["technology"] = "kgpv"
    out["zone_id"] = zone
    out["zone_name"] = [KG_SIMPLE[int(x)] for x in zone]
    out["source_code"] = [ZONE_LABELS[int(x)] for x in zone]
    out["status"] = np.where(zone > 0, "Published KGPV method", "Insufficient data")
    return out


def classify_pvcz(equivalent_module_temperature_c, specific_humidity_g_kg):
    """PVCZ temperature×humidity IDs, using explicit upper-bin equality.

    Requires actual equivalent MODULE temperature, not annual ambient temperature.
    Returns 1..50; 0 denotes no data. Subtract 1 for source-style numeric IDs.
    Exact published-data boundary handling is not assumed; this convention is explicit.
    """
    t, h = np.broadcast_arrays(
        np.asarray(equivalent_module_temperature_c, float),
        np.asarray(specific_humidity_g_kg, float),
    )
    ti = np.searchsorted([14, 19, 24, 29, 34, 39, 44, 49, 54], t, side="right")
    hi = np.searchsorted([3, 4.1, 5.9, 10.5], h, side="right")
    return np.where(np.isfinite(t) & np.isfinite(h) & (h >= 0), 1 + ti + 10 * hi, 0).astype("uint8")


def pvcz_stressors(
    module_temperature_c, specific_humidity_g_kg, interval_hours=1.0, activation_energy_ev=1.1
):
    """Time×location arrays on a regular interval; gaps invalidate that location.

    Supply hourly or 3-hourly module temperatures (measured or modelled with
    POA irradiance and a declared module-temperature model). Monthly means do
    not preserve Arrhenius exposure and must not be used here.
    """
    from scipy.special import logsumexp

    t, h = np.broadcast_arrays(
        np.asarray(module_temperature_c, float), np.asarray(specific_humidity_g_kg, float)
    )
    if t.ndim != 2 or len(t) < 2:
        raise ValueError("Expected time × location arrays with at least two samples")
    if not 0 < interval_hours <= 3 or not 0 < activation_energy_ev <= 5:
        raise ValueError("Expected <=3-hourly data and a positive activation energy")
    good = np.isfinite(t).all(0) & np.isfinite(h).all(0) & (t > -273.15).all(0) & (h >= 0).all(0)
    a = activation_energy_ev / 8.617333262145e-5
    with np.errstate(divide="ignore", invalid="ignore"):
        eq = -a / (logsumexp(-a / (t + 273.15), axis=0) - np.log(len(t))) - 273.15
    eq = np.where(good, eq, np.nan)
    humidity = np.where(good, h.mean(0), np.nan)
    return {
        "equivalent_module_temperature_c": eq,
        "specific_humidity_g_kg": humidity,
        "temperature_velocity_c_hour": np.where(
            good, np.abs(np.diff(t, axis=0)).mean(0) / interval_hours, np.nan
        ),
        "pvcz_zone_id": classify_pvcz(eq, humidity),
    }
