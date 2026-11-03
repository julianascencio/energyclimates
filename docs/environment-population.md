# Population: density preview

{doc}`Run this map <auto_examples/plot_18_map_population>`

| Example | Input | Output |
| --- | --- | --- |
| {doc}`Population <auto_examples/plot_18_map_population>` | CIESIN / NASA SEDAC GPWv4.11 2020 density via Stanford's mirror | 0.5° arithmetic density preview and log10(1+density), preserving real zeros |

## Method and interpretation

GPW density divides source population counts by source land area. The bundled
preview takes an **arithmetic mean of valid native densities** in each 60×60
pixel block (0.5°). It reads original raster pixels, not unknown precomputed
overviews. Zero remains zero; a block with no valid pixels stays missing.
The second panel uses `log10(1 + density)` so zero can be displayed.

This is deliberately a density-screening preview, **not a count-conserving or
land-area-weighted population aggregate**. Do not sum densities or multiply by
whole geographic cell area to obtain people; coastal and partial-land cells
make that incorrect. For totals, aggregate the original count and land-area
rasters consistently. The 2020 census-based estimate is not current population,
electricity consumption or a demand forecast.

## Run and export

The bundled snapshot runs offline from a repository checkout.

```bash
python -m pip install -e '.[examples]'
python examples/gallery/plot_18_map_population.py
```

```python
from energyclimates.analysis.environment import run_environment

study = run_environment("examples/environment/population-2020.parquet", "population")
study.write("results/population")
```

The export retains numerical indicators, units, assumptions and source checksums.
See [input contracts and batch downloads](environment-maps.md) for shared APIs.

## Sources and optional refresh

- [CIESIN GPWv4.11 population density DOI](https://doi.org/10.7927/H49C6VHW),
  [NASA dataset description](https://data.nasa.gov/dataset/gridded-population-of-the-world-version-4-gpwv4-population-density-revision-11)
  and [Stanford-distributed source GeoTIFF](https://data.naturalcapitalalliance.stanford.edu/download/global/ciesin-nasa-gpw-grdi/ciesen_nasa_gpw_v4_population_density_2020.tif).

```bash
python scripts/build_environment_inputs.py --dataset population
```

Refresh is explicit; tests and gallery builds never download provider data.
