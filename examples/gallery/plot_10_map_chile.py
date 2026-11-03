"""
Inspect Chile and neighbouring climate cells
============================================

Crop the same global snapshot to a Chile-centred rectangle. The rectangle also
contains neighbouring countries; it is not a Chile-only selection or national
statistic. Original 0.5° cells remain visible, with no invented local detail.

Compare annual solar resource against weak-month availability. The marked
Atacama point is the actual grid-cell centre in the repository's six-location
monthly sample, not an asserted weather-station position. The CSV export keeps
every selected cell and its coordinates. See :doc:`/map-examples` for export.
"""

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

from energyclimates.analysis.maps import plot_grid_map
from kgpv.engine.results import read_features

start = Path(__file__).resolve().parent if "__file__" in globals() else Path.cwd()
root = next(
    p for p in (start, *start.parents) if (p / "examples/global-climate-features.parquet").is_file()
)
input_files = [
    root / "examples/global-climate-features.parquet",
    root / "examples/global-climate-features.metadata.json",
    root / "examples/monthly-climate.csv",
]
features = read_features(input_files[0])
bounds = (-80, -63, -57, -16)
region = features[
    features.longitude.between(bounds[0], bounds[1])
    & features.latitude.between(bounds[2], bounds[3])
].copy()
sample = pd.read_csv(input_files[2]).query("location_id == 'Atacama'").iloc[0]
fig, axes = plt.subplots(1, 2, figsize=(10, 11), layout="constrained")
columns = ["ghi_annual_kwh_m2", "weak_month_ratio"]
for ax, column, title, unit, low, high, cmap in zip(
    axes,
    columns,
    ["Annual horizontal irradiation", "Weak-month solar availability"],
    ["kWh/m²/year", "Weak-month / annual daily GHI"],
    [500, 0],
    [2800, 1],
    ["inferno", "viridis"],
):
    image = plot_grid_map(
        region, column, ax=ax, bounds=bounds, title=title, vmin=low, vmax=high, cmap=cmap
    )
    fig.colorbar(image, ax=ax, label=unit, orientation="horizontal", shrink=0.9, pad=0.04)
    ax.plot(sample.longitude, sample.latitude, "o", color="white", markeredgecolor="#152f45")
    ax.annotate(
        "Atacama\nsample cell",
        (sample.longitude, sample.latitude),
        xytext=(-72, -20),
        fontsize=9,
        color="#142b40",
        bbox={"facecolor": "white", "alpha": 0.9, "edgecolor": "none"},
        arrowprops={"arrowstyle": "-", "color": "#142b40"},
    )
fig.suptitle(
    "Chile and neighbouring cells\nCRU TS 4.10 + ERA5 · 1996–2022 · original 0.5° grid", fontsize=15
)
result_tables = {"chile_region": region[["location_id", "latitude", "longitude", *columns]]}
map_context = {
    "method": "Regional feature crop",
    "bounds_west_east_south_north": bounds,
    "selection": "Bounding rectangle, not a country polygon",
}
print(f"Selected {len(region):,} cells in west/east/south/north bounds {bounds}.")
print(region[columns].agg(["min", "median", "max"]).round(3).to_string())
plt.show()
