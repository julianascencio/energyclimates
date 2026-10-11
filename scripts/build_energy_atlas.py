"""Reproduce the new experimental profiles from the same CRU/ERA5 providers.

Fetch the existing 1996–2022 monthly files first, or reuse work/energy-monthly.npz.
No GPCC data are necessary for the new solar/storage screening profiles.
"""

from pathlib import Path
import sys, json, calendar, shutil
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from kgpv.pipeline import normals, LAT, LON
from kgpv.engine.features import ClimateCube, extract_features
from kgpv.engine.rules import classify_features, class_labels, load_rules
from kgpv.engine.ml import train_clusters, save_model
from kgpv.export import write_layer

root = Path(__file__).resolve().parents[1]
raw = root / "raw"
work = root / "work"
dist = root / "atlas"
work.mkdir(exist_ok=True)
cache = work / "energy-monthly.npz"
provenance = work / "energy-inputs.json"
if cache.exists():
    with np.load(cache) as z:
        t = z["temperature"]
        h = z["ghi"]
    sources = json.loads(provenance.read_text())
else:
    t, ts = normals(sorted(raw.glob("cru_ts4.10.*.tmp.dat.nc.gz")), "temperature", 1996, 2022)
    print("Temperature normals complete", flush=True)
    h, hs = normals(sorted(raw.glob("e5.moda*ssrd*.nc")), "irradiation", 1996, 2022)
    np.savez_compressed(cache, temperature=t.astype("float32"), ghi=h.astype("float32"))
    sources = {"temperature": ts, "ghi": hs}
    provenance.write_text(json.dumps(sources, indent=2))
    print("Irradiation normals complete", flush=True)
# Canonical float32 monthly inputs make cached and fresh runs identical.
t = t.astype("float32")
h = h.astype("float32")
lat, lon = np.meshgrid(LAT, LON, indexing="ij")
valid = np.isfinite(t).all(0) & np.isfinite(h).all(0)
indices = np.flatnonzero(valid.ravel())
days = np.array(
    [np.mean([calendar.monthrange(y, m)[1] for y in range(1996, 2023)]) for m in range(1, 13)]
)
cube = ClimateCube(
    np.array([f"{a:.2f},{b:.2f}" for a, b in zip(lat.ravel()[indices], lon.ravel()[indices])]),
    lat.ravel()[indices],
    lon.ravel()[indices],
    {"temperature": t.reshape(12, -1)[:, indices], "ghi": h.reshape(12, -1)[:, indices]},
    days,
    "1996–2022",
    {"source": "CRU TS 4.10 + ERA5 / NCAR"},
)
f = extract_features(cube)
# Annual values should agree with the existing published atlas wherever both are valid.
for column, file in [
    ("ghi_annual_kwh_m2", "ghi-1996-2022"),
    ("temperature_mean_c", "temperature-1996-2022"),
]:
    old = np.fromfile(dist / f"data/{file}.bin", dtype="<f4")[indices]
    ok = np.isfinite(old)
    np.testing.assert_allclose(f[column].to_numpy()[ok], old[ok], rtol=2e-6, atol=2e-4)
examples = root / "examples"
examples.mkdir(exist_ok=True)
f.to_parquet(examples / "global-climate-features.parquet", index=False)
(
    f.attrs
    and (examples / "global-climate-features.metadata.json").write_text(
        json.dumps(f.attrs, indent=2)
    )
)
# Real monthly examples, sampled at the closest actual grid centre. Preserve that centre.
places = [
    ("Tenerife", 28.35, -16.55),
    ("Atacama", -23.5, -69.5),
    ("Ljubljana", 46.05, 14.5),
    ("Helsinki", 60.2, 25),
    ("Singapore", 1.35, 103.8),
    ("Phoenix", 33.45, -112.1),
]
rows = []
for name, y, x in places:
    j = int(
        np.argmin((cube.latitude - y) ** 2 + ((cube.longitude - x) * np.cos(np.deg2rad(y))) ** 2)
    )
    for m in range(12):
        rows.append(
            {
                "location_id": name,
                "latitude": cube.latitude[j],
                "longitude": cube.longitude[j],
                "month": m + 1,
                "temperature_c": cube.values["temperature"][m, j],
                "ghi_kwh_m2": cube.values["ghi"][m, j],
            }
        )
pd.DataFrame(rows).to_csv(examples / "monthly-climate.csv", index=False, float_format="%.6f")
config = {
    "format": "csv",
    "frequency": "climatology",
    "period": "1996–2022",
    "month_days": days.tolist(),
    "coordinates": {
        "id": "location_id",
        "latitude": "latitude",
        "longitude": "longitude",
        "month": "month",
    },
    "variables": {
        "temperature": {"column": "temperature_c", "unit": "C"},
        "ghi": {"column": "ghi_kwh_m2", "unit": "kWh/m2/month"},
    },
}
(examples / "monthly-mapping.json").write_text(json.dumps(config, indent=2))
models = dist / "models"
models.mkdir(exist_ok=True)
rules = load_rules()
shutil.copy(root / "kgpv/engine/rules-v1.json", models / "rules-v1.json")
palette = [
    "#00000000",
    "#92b9d3",
    "#a6cec5",
    "#e4a07d",
    "#5c96c0",
    "#52af9c",
    "#e88552",
    "#397ca8",
    "#319375",
    "#d65a38",
    "#21557b",
    "#237553",
    "#a63731",
]
layers = []
model_reports = {}
scheme_map = {}
rules_results = {}
source = "/models/rules-v1.json"


def grid(v):
    a = np.full(360 * 720, np.nan)
    a[indices] = v
    return a.reshape(360, 720)


for tech in ["pv", "hybrid", "bess"]:
    title = {
        "pv": "Solar PV · simple climate profiles",
        "hybrid": "PV + battery · simple climate profiles",
        "bess": "Battery storage · simple climate profiles",
    }[tech]
    out = classify_features(f, tech, rules)
    rules_results[tech] = out
    colors = (
        palette if tech != "bess" else ["#00000000", "#599d8f", "#5b91c8", "#e27f40", "#8b5da0"]
    )
    layer = write_layer(
        dist,
        "energy-" + tech,
        title,
        grid(out.zone_id),
        "Simple profiles · experimental",
        "1996–2022",
        "",
        rules["notes"][tech] if tech != "pv" else rules["notes"]["pv"],
        source,
        labels=class_labels(tech, rules),
        colors=colors,
        warning="Experimental climate screening. Monthly averages do not describe extremes, battery life, optimal storage size or financial performance.",
    )
    layer.update(
        {"technology": tech, "scheme": "rules", "scheme_version": rules["version"], "profile": True}
    )
    layers.append(layer)
    scheme_map[tech] = {"rules": layer["id"]}
    model, pred = train_clusters(
        f, tech, clusters=4 if tech == "bess" else 8, seed=42, area_weighted=True, rules=rules
    )
    save_model(model, models / f"{tech}.json")
    model_reports[tech] = model["diagnostics"]
    mllayer = write_layer(
        dist,
        "energy-ml-" + tech,
        {"pv": "Solar PV", "hybrid": "PV + battery", "bess": "Battery storage"}[tech]
        + " · ML climate groups",
        grid(pred.zone_id),
        "ML profiles · experimental",
        "1996–2022",
        "",
        "New atlas MiniBatchKMeans model, fitted to area-weighted CRU/ERA5 climate features. Groups are described using their physical centres.",
        f"/models/{tech}.json",
        labels=["No data"] + model["names"],
        colors=palette[: model["clusters"] + 1],
        warning="Experimental ML grouping. Spatial holdout diagnostics describe climate geometry; they do not prove better PV yield or battery performance.",
    )
    mllayer.update(
        {
            "technology": tech,
            "scheme": "ml",
            "model_version": model["model_version"],
            "profile": True,
        }
    )
    layers.append(mllayer)
    scheme_map[tech]["ml"] = mllayer["id"]
    print(f"{tech}: rule and ML layers complete; {len(f)} cells", flush=True)
feature_layers = {}
for key, title, unit in [
    ("solar_weighted_temperature_c", "Temperature during sunny months", "°C"),
    ("temperature_coldest_month_c", "Coldest monthly mean temperature", "°C"),
    ("temperature_warmest_month_c", "Warmest monthly mean temperature", "°C"),
    ("weak_month_ratio", "Weak-month solar availability", "fraction"),
    ("ghi_daily_weakest_month", "Daily irradiation in the weakest month", "kWh/m²/day"),
]:
    layer = write_layer(
        dist,
        "energy-feature-" + key,
        title,
        grid(f[key]),
        "Climate drivers · 1996–2022",
        "1996–2022",
        unit,
        "Derived from 12 complete CRU/ERA5 monthly climatological means. Weak-month ratio compares daily irradiation with the annual daily mean.",
        source,
    )
    layer["feature"] = key
    layers.append(layer)
    feature_layers[key] = layer["id"]
feature_layers.update(
    {"ghi_annual_kwh_m2": "ghi-1996-2022", "temperature_mean_c": "temperature-1996-2022"}
)
manifest = {
    "scheme_version": rules["version"],
    "status": "experimental",
    "period": "1996–2022",
    "cells": len(f),
    "month_days": days.tolist(),
    "features": list(f.columns),
    "sources": sources,
    "rules": rules,
    "ml_diagnostics": model_reports,
    "limits": [
        "Monthly mean climate only; no extreme-temperature or subdaily-variability claims",
        "27-year common period, not a 30-year WMO normal",
        "BESS climate profiles exclude chemistry, enclosure, dispatch, tariffs and grid constraints",
        "No independent operational target was used to validate performance superiority",
    ],
}
(dist / "data/energy-provenance.json").write_text(json.dumps(manifest, indent=2))
cat_path = dist / "data/catalog.json"
cat = json.loads(cat_path.read_text())
cat["layers"] = [l for l in cat["layers"] if not l["id"].startswith("energy-")]
cat["layers"] = layers + cat["layers"]
cat["default"] = "energy-pv"
cat["energy"] = {
    "schemes": scheme_map,
    "features": feature_layers,
    "rules": "/models/rules-v1.json",
    "provenance": "/data/energy-provenance.json",
    "version": rules["version"],
}
cat_path.write_text(json.dumps(cat, ensure_ascii=False, indent=2))
# Keep extensions when the historical KGPV exporter is re-run.
ext_path = dist / "data/external-catalog.json"
ext = json.loads(ext_path.read_text())
ext["layers"] = [l for l in ext["layers"] if not l["id"].startswith("energy-")] + layers
ext["energy"] = cat["energy"]
ext_path.write_text(json.dumps(ext, ensure_ascii=False, indent=2))
print(
    json.dumps(
        {"complete": True, "layers": len(cat["layers"]), "new_layers": len(layers), "cells": len(f)}
    ),
    flush=True,
)
