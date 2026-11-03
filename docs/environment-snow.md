# Snow: modeled ground exposure

{doc}`Run this map <auto_examples/plot_14_map_snow>`

| Example | Input | Output |
| --- | --- | --- |
| {doc}`Snow <auto_examples/plot_14_map_snow>` | NOAA NCEP/NCAR Reanalysis 1 ground snow-water equivalent, 1981–2010 | Months with monthly-mean SWE ≥1 mm, mean and peak monthly SWE |

## Method and interpretation

`mean_swe_mm` is a day-weighted mean; `peak_month_swe_mm` is the maximum of the
monthly means. `months_mean_swe_above_threshold` counts monthly means **≥1 mm**,
with a configurable positive threshold. A month above that threshold is not a
count of snow-covered days. One kg/m² of SWE equals one mm liquid-water equivalent,
not one mm physical snow depth.

The 94×192 Gaussian source grid is drawn with its native latitude coordinates,
using midpoint display edges, without inventing a regular 0.5° grid. Only source
months with all 30 contributing years are retained. A representative non-leap
year weights the monthly climatology. The native static land mask excludes ocean and sea-ice cells; large ice-sheet values are retained and the peak panel uses a log scale.
Terrain, module snow cover, sliding, heating, tilt and energy loss are outside
this method.

## Run and export

The bundled snapshot runs offline from a repository checkout.

```bash
python -m pip install -e '.[examples]'
python examples/gallery/plot_14_map_snow.py
```

```python
from energyclimates.analysis.environment import run_environment

study = run_environment("examples/environment/snow-1981-2010.parquet", "snow")
study.write("results/snow")
```

The export retains numerical indicators, units, assumptions and source checksums.
See [input contracts and batch downloads](environment-maps.md) for shared APIs.

## Sources and optional refresh

- [NOAA PSL NCEP/NCAR derived data catalog](https://psl.noaa.gov/thredds/catalog/Datasets/ncep.reanalysis.derived/surface_gauss/catalog.html):
  `weasd.sfc.mon.1981-2010.ltm.nc` with the matching NCEP static land mask.

```bash
python scripts/build_environment_inputs.py --dataset snow
```

Refresh is explicit; tests and gallery builds never download provider data.
