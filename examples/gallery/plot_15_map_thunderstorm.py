"""
Thunderstorm risk screening from reported events
================================================

Input: NOAA NCEI Storm Events details, all five annual archives for 2020–2024.
Only valid event BEGIN coordinates and local dates are used. Reports of
Thunderstorm Wind and Lightning are kept separate in the two maps.

Method: bin reports into 1° geographic cells; count distinct local dates per
cell and divide by five calendar years. Multiple reports on the same date count
once. The exported tables also retain event counts. Empty cells remain absent.

Analysis: the maps show the contiguous-U.S. viewing rectangle, while result
tables retain all supplied U.S. reports. These are significant/damaging event
reports, not all thunderstorms, lightning flash density or annual probability.
Reporting varies with population and observing practices; grey cells do not
establish zero risk. Use local lightning/climatology data for design decisions.

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
study = run_environment(
    features, "thunderstorm", start_year=2020, end_year=2024, event_types=["Thunderstorm Wind"]
)
lightning = run_environment(
    features, "thunderstorm", start_year=2020, end_year=2024, event_types=["Lightning"]
)
frames = [study.indicators, lightning.indicators]
result_tables = {"wind": frames[0], "lightning": frames[1]}
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
        "Thunderstorm wind report days",
        "distinct local dates/year",
        "YlOrRd",
    ),
    ("reported_days_per_year", "Lightning report days", "distinct local dates/year", "YlOrRd"),
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
    "Thunderstorm risk screening from reported events\nNOAA NCEI Storm Events · 2020–2024 · U.S. reports in 1° bins",
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
