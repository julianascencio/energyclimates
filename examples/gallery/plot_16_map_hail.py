"""
Hail risk screening from reported size and frequency
====================================================

Input: NOAA NCEI Storm Events Hail reports, 2020–2024, with unique event IDs,
BEGIN coordinates, local dates and reported diameter. Inches convert to mm
using exactly 25.4; missing size is not treated as zero.

Method: select reported diameter ≥ 25.4 mm, group into 1° cells, count distinct
local report dates per five-year period and retain the maximum reported size.
The maps display a contiguous-U.S. rectangle; exports retain all qualifying
U.S. reports. Cells without qualifying reports remain absent.

Analysis: frequent report days and large reported sizes identify locations for
further investigation. Population/reporting bias and the short record prevent
return-period, exceedance-probability or module-damage claims. A single maximum
is not a design hailstone size. Grey is not evidence of safety.

See :doc:`/environment-maps` for input contracts, equations, source URLs and
refresh instructions. Run this script offline from an installed checkout; the
batch runner exports figures, tables, assumptions and input checksums.
"""

from pathlib import Path

import matplotlib.pyplot as plt

from energyclimates.analysis.environment import run_environment
from energyclimates.analysis.maps import plot_grid_map
from energyclimates.inputs.environment import read_environment

start = Path(__file__).resolve().parent if "__file__" in globals() else Path.cwd()
root = next(p for p in (start, *start.parents) if (p / "examples/environment").is_dir())
input_files = [
    root / "examples/environment/storm-reports-2020-2024.parquet",
    root / "examples/environment/storm-reports-2020-2024.metadata.json",
]
features = read_environment(input_files[0])
study = run_environment(features, "hail", start_year=2020, end_year=2024)
frames = [study.indicators, study.indicators]
result_tables = {"hail": study.indicators}
map_context = study.manifest
map_grid = features.attrs["grid"].copy()
map_grid.update(
    display="equirectangular", interpolation="none", grey_background="No supplied value"
)
fig, axes = plt.subplots(2, 1, figsize=(12, 10), layout="constrained")
fig.get_layout_engine().set(h_pad=0.14, hspace=0.08)
panels = [
    (
        "reported_days_per_year",
        "Hail ≥ 25.4 mm: report days",
        "distinct local dates/year",
        "YlOrRd",
    ),
    ("maximum_reported_hail_mm", "Largest reported hail diameter", "mm", "magma"),
]
for index, (ax, frame, (column, title, unit, palette)) in enumerate(zip(axes, frames, panels)):
    settings = {"ax": ax, "title": title, "cmap": palette}
    image = plot_grid_map(frame, column, resolution=1, bounds=(-125, -66, 24, 50), **settings)
    map_grid.update(
        resolution_degrees=1,
        view_bounds=[-125, -66, 24, 50],
        grey_background="No qualifying report; not zero hazard",
    )
    fig.colorbar(image, ax=ax, label=unit, shrink=0.75, pad=0.02, extend="neither")
fig.suptitle(
    "Hail risk screening from reported size and frequency\nNOAA NCEI Storm Events · 2020–2024 · reported hail ≥ 25.4 mm",
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
