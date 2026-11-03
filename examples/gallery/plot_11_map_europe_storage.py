"""
Map European solar seasonality and battery climate context
==========================================================

Recompute BESS climate profiles for a European bounding rectangle, which also
includes parts of North Africa and western Asia. Pair these with weakest-month
daily GHI to inspect ambient thermal context and solar seasonality separately.

BESS rules use coldest and warmest monthly mean air temperatures. They do not
measure extreme events, cell temperature, cooling load, battery safety or lifetime.
The weakest solar month is computed per cell; it is not a fixed calendar month.
The original 0.5° CRU/ERA5 cells cover 1996–2022. See :doc:`/map-examples` for export.
"""

import json
from pathlib import Path

import matplotlib.pyplot as plt

from energyclimates.analysis.maps import plot_category_map, plot_grid_map
from energyclimates.methods import class_labels, classify_features, load_rules
from kgpv.engine.results import read_features

start = Path(__file__).resolve().parent if "__file__" in globals() else Path.cwd()
root = next(
    p for p in (start, *start.parents) if (p / "examples/global-climate-features.parquet").is_file()
)
input_files = [
    root / "examples/global-climate-features.parquet",
    root / "examples/global-climate-features.metadata.json",
    root / "kgpv/engine/rules-v1.json",
    root / "atlas/data/catalog.json",
]
features = read_features(input_files[0])
bounds = (-15, 40, 30, 72)
region = features[
    features.longitude.between(bounds[0], bounds[1])
    & features.latitude.between(bounds[2], bounds[3])
].copy()
rules = load_rules(input_files[2])
profiles = classify_features(region, "bess", rules)
layer = next(
    x for x in json.loads(input_files[3].read_text())["layers"] if x["id"] == "energy-bess"
)
fig, axes = plt.subplots(1, 2, figsize=(15, 7), layout="constrained")
image = plot_grid_map(
    region,
    "ghi_daily_weakest_month",
    ax=axes[0],
    bounds=bounds,
    title="Daily GHI in the weakest month",
    cmap="viridis",
    vmin=0,
    vmax=5,
)
fig.colorbar(image, ax=axes[0], label="kWh/m²/day", orientation="horizontal", shrink=0.85)
plot_category_map(
    profiles,
    labels=class_labels("bess", rules),
    colors=layer["colors"],
    ax=axes[1],
    bounds=bounds,
    title="Experimental BESS thermal profiles",
)
fig.suptitle(
    "Europe and neighbouring cells\nCRU TS 4.10 + ERA5 · 1996–2022 · 0.5° cells", fontsize=15
)
result_tables = {"europe_features": region, "europe_bess": profiles}
map_context = {
    "method": "Regional features and experimental BESS rules",
    "rules": rules,
    "bounds_west_east_south_north": bounds,
    "selection": "Bounding rectangle, not country polygons",
}
print(
    f"{len(region):,} regional cells; cold threshold {rules['bess_cold_month_c']} °C, "
    f"hot threshold {rules['bess_hot_month_c']} °C (monthly means)."
)
print(profiles.zone_name.value_counts().to_string())
plt.show()
