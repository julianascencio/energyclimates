"""
Map population density with explicit aggregation
================================================

Input: CIESIN / NASA SEDAC GPWv4.11 population density for 2020, distributed
by the Stanford Natural Capital Project mirror. Native density is people/km²,
consistent with census/register estimates; it is not a live population count.

Method: the bundled input is an arithmetic mean of valid native 30-arcsecond
densities within each 0.5° block. Source overviews are not used. Nodata remains
missing and real zero density stays zero. Plot both density and log10(1+density).

Analysis: the logarithmic view exposes low-density settlement patterns while
the linear view highlights dense regions. This preview is not a land-area-
weighted or count-conserving aggregate. Do not multiply by whole geographic
cell area or sum density to infer population totals. Local siting and demand
analysis need finer data and administrative/census validation.

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
    root / "examples/environment/population-2020.parquet",
    root / "examples/environment/population-2020.metadata.json",
]
features = read_environment(input_files[0])
study = run_environment(features, "population")
frames = [study.indicators, study.indicators]
result_tables = {"population": study.indicators}
map_context = study.manifest
map_grid = features.attrs["grid"].copy()
map_grid.update(
    display="equirectangular", interpolation="none", grey_background="No supplied value"
)
fig, axes = plt.subplots(2, 1, figsize=(12, 10), layout="constrained")
fig.get_layout_engine().set(h_pad=0.14, hspace=0.08)
panels = [
    ("population_density_km2", "Population density preview", "people/km²", "magma"),
    (
        "log10_population_density_plus_one",
        "Settlement density on a log scale",
        "log10(1 + people/km²)",
        "magma",
    ),
]
for index, (ax, frame, (column, title, unit, palette)) in enumerate(zip(axes, frames, panels)):
    settings = {"ax": ax, "title": title, "cmap": palette}
    settings.update(vmin=0, vmax=2000 if index == 0 else 4)
    image = plot_grid_map(frame, column, resolution=0.5, bounds=(-180, 180, -60, 85), **settings)
    fig.colorbar(image, ax=ax, label=unit, shrink=0.75, pad=0.02, extend="max")
fig.suptitle(
    "Map population density with explicit aggregation\nCIESIN / NASA SEDAC GPWv4.11 · 2020 estimate · 0.5° density preview",
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
