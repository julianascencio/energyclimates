"""
Global modeled large-hail activity in 2015
============================================================

Input: Prein and Holland (2018), PANGAEA V2 daily large-hail probabilities for
2015 on the native 256 × 512 Gaussian/longitude grid. Hail means diameter
>2.5 cm. The V2 catalogue defines fractions from zero to one, overriding the
misleading percent attribute in the NetCDF file.

Method: sum all 365 daily probabilities. This is a modeled hail-day-equivalent
indicator, not the probability of hail occurring at least once during the year.
The second panel divides by 365 to show mean daily probability. No independent-
day assumption or spatial interpolation is used. Missing days propagate.

Analysis: this is ONE modeled year, not a climatology, observed event count,
return period, design hail size or PV damage estimate. Environmental-proxy
calibration and geographic biases limit site-level use. Source zeros stay zero;
missing values are grey. The original U.S. report method remains available as
``run_environment(..., "hail", start_year=2020, end_year=2024)``.

Derived data: CC BY 3.0, Prein and Holland (2018). Dataset:
https://doi.org/10.1594/PANGAEA.893160. Paper:
https://doi.org/10.1016/j.wace.2018.10.004.
See :doc:`/environment-hail` for reproducible inputs, units and limitations.
This example runs offline and exports numerical results with provenance.
"""

from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.colors import PowerNorm

from energyclimates.analysis.environment import run_environment
from energyclimates.analysis.maps import plot_rectilinear_map
from energyclimates.inputs.environment import read_environment

start = Path(__file__).resolve().parent if "__file__" in globals() else Path.cwd()
root = next(p for p in (start, *start.parents) if (p / "examples/environment").is_dir())
input_files = [
    root / "examples/environment/global-hail-2015.parquet",
    root / "examples/environment/global-hail-2015.metadata.json",
]
features = read_environment(input_files[0])
study = run_environment(features, "global_hail")
result_tables = {"hail": study.indicators}
map_context = study.manifest
map_grid = features.attrs["grid"].copy()
map_grid.update(display="equirectangular", interpolation="none", view_bounds=[-180, 180, -90, 90])
fig, axes = plt.subplots(2, 1, figsize=(12, 12), layout="constrained")
panels = [
    (
        "modeled_hail_day_equivalents",
        "Sum of daily large-hail probabilities",
        "modeled day equivalents",
    ),
    ("mean_daily_hail_probability", "Mean daily large-hail probability", "fraction (0–1)"),
]
for ax, (column, title, unit) in zip(axes, panels):
    image = plot_rectilinear_map(
        study.indicators,
        column,
        latitude=map_grid["latitude"],
        longitude=map_grid["longitude"],
        bounds=(-180, 180, -90, 90),
        ax=ax,
        title=title,
        cmap="YlOrRd",
        norm=PowerNorm(gamma=0.5, vmin=0, vmax=study.indicators[column].max()),
    )
    fig.colorbar(image, ax=ax, label=unit + " · square-root colour scale", shrink=0.7, pad=0.02)
fig.suptitle(
    "Global modeled large-hail activity · 2015 only\nPrein & Holland (2018), PANGAEA V2 · hail >2.5 cm",
    fontsize=14,
)
print(f"hail: {len(study.indicators):,} output rows")
print(
    study.indicators.drop(columns=["latitude", "longitude"])
    .agg(["min", "median", "max"])
    .to_string()
)
print("Limitations:", study.manifest["limitations"])
plt.show()
