# Global thunderstorm screening with lightning

{doc}`Run the global map <auto_examples/plot_15_map_thunderstorm>`

The gallery now covers the whole world using **WGLC lightning stroke density**
from 2012–2021. It replaces the U.S.-only report-count figure with a global
climatology. The two panels show annualized strokes/km² and peak monthly
strokes/km²/day. A square-root colour scale reveals low densities without
changing the exported numbers; real zeros are included.

## Inputs and method

The pinned [WGLC 2022 release](https://doi.org/10.5281/zenodo.6007052) supplies
monthly daily-density climatology fields on a global 0.5° grid for 2012–2021,
as stated in the NetCDF title and the 2022 paper. The catalogue description
still references the older time series; it is not the climatology period.
Four native cells are averaged into each 1° cell with spherical-area weights
proportional to cos(latitude). All twelve months and all four spatial cells
are required; missing values remain missing. The original monthly densities
are retained in the bundled input for alternative seasonal analyses.

`lightning_screen` then calculates:

- Annualized density = sum of monthly daily densities × month lengths in a
  **365-day climatological year**, in strokes/km²/year.
- Peak monthly daily density = maximum of the twelve monthly means, in
  strokes/km²/day.

This is lightning activity, **not thunderstorm counts, flash counts, damaging
wind reports, ground-strike probability or PV loss**. WWLLN detection efficiency
varies geographically and temporally, despite correction, and weak strokes
may be missed. These are historical screening data, not a current forecast.

## Run and export

```bash
python examples/gallery/plot_15_map_thunderstorm.py
```

```python
from energyclimates.analysis.environment import run_environment

study = run_environment("examples/environment/global-lightning-2012-2021.parquet", "global_lightning")
study.write("results/global-lightning")
```

The snapshot runs offline. See [input contracts and downloads](environment-maps.md).
The U.S. NOAA snapshot and `kind="thunderstorm"` API remain available for reported
wind/lightning studies; their coverage has not been relabelled as global.

## Attribution and rebuild

- Kaplan, J. O. and Lau, K. H.-K. (2021),
  [The WGLC global gridded lightning climatology and time series](https://doi.org/10.5194/essd-13-3219-2021).
- Kaplan and Lau (2022),
  [WGLC, 2022 update](https://doi.org/10.5194/essd-14-5665-2022).
- WGLC / WWLLN, 2022 release, doi:10.5281/zenodo.6007052.
  Follow the provider LICENSE's **CC BY-SA 4.0** terms. The derived snapshot,
  numerical results and map figures are distributed under
  [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/); retain attribution
  and identify these temporal/spatial aggregations as modifications. Software
  remains MIT-licensed.

```bash
python scripts/build_global_lightning_input.py
```

This optional command downloads about 26 MB. Gallery builds never download data.
Exact source URL, SHA-256, processing, units and licence accompany the snapshot.
