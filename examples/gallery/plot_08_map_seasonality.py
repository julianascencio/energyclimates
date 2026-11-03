"""
Map the weakest solar month
===========================

Compare daily irradiation in the weakest climatological month with its ratio to
the annual daily mean. A ratio near one indicates relatively steady monthly sun;
a low ratio indicates stronger seasonality. Monthly totals were already divided
by their month lengths by the existing feature extractor. These features cannot
determine battery duration, hourly autonomy or worst-case weather.

The bundled CRU/ERA5 snapshot uses 1996–2022 and 0.5° cells. No interpolation,
provider requests or missing-value filling is performed. See :doc:`/map-examples`
for the commands that save all maps and their numeric results.
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
fig, axes = plt.subplots(2, 1, figsize=(12, 10), layout="constrained")
fig.get_layout_engine().set(h_pad=0.14, hspace=0.08)
columns = ["ghi_daily_weakest_month", "weak_month_ratio"]
for ax, column, title, unit, maximum in zip(
    axes,
    columns,
    ["Daily GHI in the weakest month", "Weak-month / annual daily GHI"],
    ["kWh/m²/day", "Fraction"],
    [7, 1],
):
    image = plot_grid_map(
        features, column, ax=ax, title=title, cmap="viridis", vmin=0, vmax=maximum
    )
    fig.colorbar(image, ax=ax, label=unit, shrink=0.75, pad=0.02)
fig.suptitle("Solar seasonality\nCRU TS 4.10 + ERA5 · 1996–2022 · 0.5° cells", fontsize=15)
result_tables = {"seasonality": features[["location_id", "latitude", "longitude", *columns]]}
map_context = {"method": "Weakest monthly daily GHI and its ratio to annual daily GHI"}
print(features[columns].agg(["min", "median", "max"]).round(3).to_string())
plt.show()
