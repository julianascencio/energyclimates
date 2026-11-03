"""
Map global solar resource and air temperature
=============================================

Reconstruct the bundled 0.5° grid from 67,420 CRU TS 4.10 / ERA5 feature rows.
These are 1996–2022 climatologies, not station measurements or a PV-yield map.
GHI is horizontal irradiation; the temperature is monthly-GHI-weighted ambient
air temperature, not module temperature. The grey background has no supplied
value. Cells are drawn at their original size without interpolation or downloads.

Run from an installed repository checkout, or use the batch commands in
:doc:`/map-examples` to save PNG, SVG, CSV and provenance files.
"""

from pathlib import Path

import matplotlib.pyplot as plt

from energyclimates.analysis.maps import plot_grid_map
from kgpv.engine.results import read_features

start = Path(__file__).resolve().parent if "__file__" in globals() else Path.cwd()
root = next(
    p for p in (start, *start.parents) if (p / "examples/global-climate-features.parquet").is_file()
)
input_files = [
    root / "examples/global-climate-features.parquet",
    root / "examples/global-climate-features.metadata.json",
]
features = read_features(input_files[0])
columns = ["ghi_annual_kwh_m2", "solar_weighted_temperature_c"]
fig, axes = plt.subplots(2, 1, figsize=(12, 10), layout="constrained")
fig.get_layout_engine().set(h_pad=0.14, hspace=0.08)
settings = [
    (columns[0], "Annual horizontal irradiation", "inferno", 500, 2800, "kWh/m²/year"),
    (columns[1], "Solar-weighted ambient temperature", "coolwarm", -25, 35, "°C"),
]
for ax, (column, title, cmap, vmin, vmax, unit) in zip(axes, settings):
    image = plot_grid_map(features, column, ax=ax, title=title, cmap=cmap, vmin=vmin, vmax=vmax)
    fig.colorbar(image, ax=ax, label=unit, shrink=0.75, pad=0.02)
fig.suptitle("Global solar climate\nCRU TS 4.10 + ERA5 · 1996–2022 · 0.5° cells", fontsize=15)
result_tables = {"resource": features[["location_id", "latitude", "longitude", *columns]]}
map_context = {"method": "Existing annual and solar-weighted monthly climate features"}
print(f"Mapped {len(features):,} cells; grey means no supplied value.")
print(features[columns].agg(["min", "median", "max"]).round(2).to_string())
plt.show()
