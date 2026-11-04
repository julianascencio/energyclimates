"""
Global thunderstorm screening with lightning
================================================

Input: WGLC detection-efficiency-corrected lightning stroke density, 2012–2021,
from the World Wide Lightning Location Network. The provider’s twelve monthly climatological daily means are used. Native
0.5° cells are averaged by spherical area into 1° global cells.

Method: multiply the twelve monthly daily densities by the lengths of a
365-day climatological year and sum. The second panel retains the highest
monthly daily density. All twelve months and spatial cells must be valid.

Analysis: these maps cover the world, including oceans. Strokes are electrical
discharges, not flashes or storm days. Detection efficiency varies across
regions and years; weak strokes can be missed. This lightning indicator does
not estimate damaging wind, annual storm probability or PV loss. Source zeros
remain zero; missing cells remain grey. The former U.S. report-count method
remains available as ``run_environment(..., "thunderstorm", ...)``.

Derived data and figures: CC BY-SA 4.0. Attribute Kaplan and Lau (2021, 2022),
WWLLN and WGLC (2022 release). See :doc:`/environment-thunderstorm` for citations,
exact inputs, processing and the optional rebuild command. This example runs
offline; the batch download includes numerical results and provenance.
"""

from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.colors import PowerNorm

from energyclimates.analysis.environment import run_environment
from energyclimates.analysis.maps import plot_grid_map
from energyclimates.inputs.environment import read_environment

start = Path(__file__).resolve().parent if "__file__" in globals() else Path.cwd()
root = next(p for p in (start, *start.parents) if (p / "examples/environment").is_dir())
input_files = [
    root / "examples/environment/global-lightning-2012-2021.parquet",
    root / "examples/environment/global-lightning-2012-2021.metadata.json",
]
features = read_environment(input_files[0])
study = run_environment(features, "global_lightning")
result_tables = {"lightning": study.indicators}
map_context = study.manifest
map_grid = features.attrs["grid"].copy()
map_grid.update(display="equirectangular", interpolation="none", view_bounds=[-180, 180, -90, 90])
fig, axes = plt.subplots(2, 1, figsize=(12, 13), layout="constrained")
panels = [
    ("annualized_strokes_km2", "Annualized lightning stroke density", "strokes/km²/year"),
    (
        "peak_month_strokes_km2_day",
        "Peak monthly daily lightning stroke density",
        "strokes/km²/day",
    ),
]
for ax, (column, title, unit) in zip(axes, panels):
    values = study.indicators[column]
    image = plot_grid_map(
        study.indicators,
        column,
        resolution=1,
        bounds=(-180, 180, -90, 90),
        ax=ax,
        title=title,
        cmap="YlOrRd",
        norm=PowerNorm(gamma=0.5, vmin=0, vmax=values.max()),
    )
    fig.colorbar(image, ax=ax, label=unit + " · square-root colour scale", shrink=0.7, pad=0.02)
fig.suptitle(
    "Global thunderstorm screening with lightning\nWGLC / WWLLN · 2012–2021 · 1° area means",
    fontsize=14,
)
fig.supxlabel("Kaplan & Lau / WGLC · CC BY-SA 4.0 · strokes ≠ flashes or storm days", fontsize=9)
print(f"Global cells: {len(study.indicators):,}")
print(
    study.indicators.drop(columns=["latitude", "longitude"]).agg(["min", "median", "max"]).round(4)
)
print("Limitations:", study.manifest["limitations"])
plt.show()
