"""
Map vegetation leaf area and seasonal variation
===============================================

Input: NASA MERRA-2 GMI monthly leaf-area index (LAI), January–December 2019,
on sampled model land cells. LAI is leaf area divided by ground area (m²/m²).
The 2° × 2.5° sample spacing is coarser than the native 0.5° × 0.625° model grid.

Method: calculate the day-weighted annual mean and maximum minus minimum of
twelve monthly LAI values. A missing month makes the annual indicators missing.
The maps use complete declared axes so gaps never stretch neighbouring cells.

Analysis: distinguish high model leaf area from strong seasonal variation.
This is model vegetation structure, not a measured NDVI map, land-cover class,
forest-height layer, biomass estimate or vegetation shading calculation. Use
local canopy/height and site geometry inputs for PV clearance analysis.

See :doc:`/environment-maps` for input contracts, equations, source URLs and
refresh instructions. Run this script offline from an installed checkout; the
batch runner exports figures, tables, assumptions and input checksums.
"""

from pathlib import Path

import matplotlib.pyplot as plt

from energyclimates.analysis.environment import run_environment
from energyclimates.analysis.maps import plot_rectilinear_map
from energyclimates.inputs.environment import read_environment

start = Path(__file__).resolve().parent if "__file__" in globals() else Path.cwd()
root = next(p for p in (start, *start.parents) if (p / "examples/environment").is_dir())
input_files = [
    root / "examples/environment/gmi-2019.parquet",
    root / "examples/environment/gmi-2019.metadata.json",
]
features = read_environment(input_files[0])
study = run_environment(features, "vegetation")
frames = [study.indicators, study.indicators]
result_tables = {"vegetation": study.indicators}
map_context = study.manifest
map_grid = features.attrs["grid"].copy()
map_grid.update(
    display="equirectangular", interpolation="none", grey_background="No supplied value"
)
fig, axes = plt.subplots(2, 1, figsize=(12, 10), layout="constrained")
fig.get_layout_engine().set(h_pad=0.14, hspace=0.08)
panels = [
    ("mean_lai", "Mean leaf-area index", "m² leaf/m² ground", "YlGn"),
    ("seasonal_lai_range", "Seasonal LAI range", "m² leaf/m² ground", "YlGn"),
]
for index, (ax, frame, (column, title, unit, palette)) in enumerate(zip(axes, frames, panels)):
    settings = {"ax": ax, "title": title, "cmap": palette}
    settings.update(vmin=0, vmax=6)
    image = plot_rectilinear_map(
        frame, column, latitude=map_grid["latitude"], longitude=map_grid["longitude"], **settings
    )
    fig.colorbar(image, ax=ax, label=unit, shrink=0.75, pad=0.02, extend="max")
fig.suptitle(
    "Map vegetation leaf area and seasonal variation\nNASA MERRA-2 GMI · 2019 · sampled model land cells",
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
