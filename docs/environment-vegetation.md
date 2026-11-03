# Vegetation: model leaf area

{doc}`Run this map <auto_examples/plot_17_map_vegetation>`

| Example | Input | Output |
| --- | --- | --- |
| {doc}`Vegetation <auto_examples/plot_17_map_vegetation>` | NASA MERRA-2 GMI model monthly leaf-area index, 2019 | Day-weighted mean LAI and seasonal range, m² leaf/m² ground |

## Method and interpretation

Compute the month-length-weighted annual mean LAI and the difference between
maximum and minimum monthly LAI. The 2019 NASA GMI snapshot selects every fourth
native latitude/longitude centre, yielding **2°×2.5° sample spacing** from a
0.5°×0.625° model. These are samples, not block means. At least one valid LAI
month establishes the example's model-land mask; incomplete series retain
missing output indicators. Complete source axes are supplied to plotting so
missing cells cannot stretch their neighbours.

LAI is not NDVI, land-cover class, biomass, canopy height or tree-clearance
information. Local shade analysis needs height, geometry and finer observations.
A single modeled year cannot establish current vegetation conditions or trends.

## Run and export

The bundled snapshot runs offline from a repository checkout.

```bash
python -m pip install -e '.[examples]'
python examples/gallery/plot_17_map_vegetation.py
```

```python
from energyclimates.analysis.environment import run_environment

study = run_environment("examples/environment/gmi-2019.parquet", "vegetation")
study.write("results/vegetation")
```

The export retains numerical indicators, units, assumptions and source checksums.
See [input contracts and batch downloads](environment-maps.md) for shared APIs.

## Sources and optional refresh

- [NASA MERRA-2 GMI project and model description](https://acd-ext.gsfc.nasa.gov/Projects/GEOSCCM/MERRA2GMI/)
  and [NCCS public OPeNDAP collections](https://opendap.nccs.nasa.gov/dods/merra2_gmi).
  Inputs use `dusmass` from `tavgM_2d_aer_Nx` and `lai` from `tavgM_2d_lnd_Nx`.

```bash
python scripts/build_environment_inputs.py --dataset gmi
```

Refresh is explicit; tests and gallery builds never download provider data.
