"""
Soiling risk screening from surface dust
========================================

Input: NASA MERRA-2 GMI monthly surface dust, January–December 2019, sampled
at 2° latitude × 2.5° longitude on model land cells. This is a replay simulation,
not aerosol observations; every fourth native centre is retained, not averaged.

Method: concentration × assumed deposition velocity (0.001 m/s) × cos(30°).
The right map converts that dry mass flux to g/m²/day. Annual means are weighted
by month length and require all twelve months. No rain, cleaning, resuspension
or optical transmission model is applied.

Analysis: use this as a dust-deposition screening scenario. Higher modeled dust
increases potential deposition under the same assumptions. It is not a measured
soiling ratio, annual accumulation or PV energy loss. Single-year and coarse
sampling limits are recorded with the exported results.

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
study = run_environment(features, "soiling")
frames = [study.indicators, study.indicators]
result_tables = {"soiling": study.indicators}
map_context = study.manifest
map_grid = features.attrs["grid"].copy()
map_grid.update(
    display="equirectangular", interpolation="none", grey_background="No supplied value"
)
fig, axes = plt.subplots(2, 1, figsize=(12, 10), layout="constrained")
fig.get_layout_engine().set(h_pad=0.14, hspace=0.08)
panels = [
    ("mean_dust_ug_m3", "Day-weighted surface dust", "µg/m³", "YlOrBr"),
    ("dry_deposition_g_m2_day", "Dry dust deposition scenario", "g/m²/day", "magma"),
]
for index, (ax, frame, (column, title, unit, palette)) in enumerate(zip(axes, frames, panels)):
    settings = {"ax": ax, "title": title, "cmap": palette}
    settings.update(vmin=0, vmax=100 if index == 0 else 0.008)
    image = plot_rectilinear_map(
        frame, column, latitude=map_grid["latitude"], longitude=map_grid["longitude"], **settings
    )
    fig.colorbar(image, ax=ax, label=unit, shrink=0.75, pad=0.02, extend="max")
fig.suptitle(
    "Soiling risk screening from surface dust\nNASA MERRA-2 GMI · 2019 · sampled model land cells",
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
