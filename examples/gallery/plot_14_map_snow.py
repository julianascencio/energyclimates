"""
Snow risk screening from ground snow water
==========================================

Input: NOAA PSL NCEP/NCAR Reanalysis 1 monthly ground snow-water equivalent,
1981–2010. The original 94 × 192 Gaussian grid is retained; 1 kg/m² equals 1 mm
water equivalent. All thirty years must contribute to each retained month.

Method: count monthly means at or above 1 mm SWE and retain the maximum monthly
mean. These are months with elevated MEAN snow water, not snow-cover days,
snowfall totals or physical snow depth. Twelve valid months are required.

Analysis: identify persistent versus seasonal modeled ground-snow exposure.
Ice-sheet values can be very large; the peak map uses a logarithmic colour scale.
The native static land mask excludes oceans and sea ice. Local terrain, snow on modules, tilt, sliding,
heating and PV losses require a separate site-level snow model.

See :doc:`/environment-maps` for input contracts, equations, source URLs and
refresh instructions. Run this script offline from an installed checkout; the
batch runner exports figures, tables, assumptions and input checksums.
"""

from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.colors import LogNorm

from energyclimates.analysis.environment import run_environment
from energyclimates.analysis.maps import plot_rectilinear_map
from energyclimates.inputs.environment import read_environment

start = Path(__file__).resolve().parent if "__file__" in globals() else Path.cwd()
root = next(p for p in (start, *start.parents) if (p / "examples/environment").is_dir())
input_files = [
    root / "examples/environment/snow-1981-2010.parquet",
    root / "examples/environment/snow-1981-2010.metadata.json",
]
features = read_environment(input_files[0])
study = run_environment(features, "snow")
frames = [study.indicators, study.indicators]
result_tables = {"snow": study.indicators}
map_context = study.manifest
map_grid = features.attrs["grid"].copy()
map_grid.update(
    display="equirectangular",
    interpolation="none",
    grey_background="No supplied value; log snow panel also masks zero",
)
fig, axes = plt.subplots(2, 1, figsize=(12, 10), layout="constrained")
fig.get_layout_engine().set(h_pad=0.14, hspace=0.08)
panels = [
    ("months_mean_swe_above_threshold", "Months with mean SWE ≥ 1 mm", "months (0–12)", "Blues"),
    (
        "peak_month_swe_mm",
        "Peak monthly-mean ground SWE",
        "mm water equivalent (log scale)",
        "viridis",
    ),
]
for index, (ax, frame, (column, title, unit, palette)) in enumerate(zip(axes, frames, panels)):
    settings = {"ax": ax, "title": title, "cmap": palette}
    if index == 0:
        settings.update(vmin=0, vmax=12)
    else:
        settings.update(norm=LogNorm(vmin=1, vmax=1000))
    image = plot_rectilinear_map(
        frame, column, latitude=map_grid["latitude"], longitude=map_grid["longitude"], **settings
    )
    fig.colorbar(
        image, ax=ax, label=unit, shrink=0.75, pad=0.02, extend="neither" if index == 0 else "both"
    )
fig.suptitle(
    "Snow risk screening from ground snow water\nNOAA NCEP/NCAR Reanalysis 1 · 1981–2010 · native Gaussian grid",
    fontsize=14,
)
for name, table in result_tables.items():
    print(f"{name}: {len(table):,} output rows")
    print(
        table.select_dtypes(include="number")
        .drop(columns=["latitude", "longitude"])
        .agg(["min", "median", "max"])
        .round(4)
        .to_string()
    )
print("Limitations:", study.manifest["limitations"])
plt.show()
