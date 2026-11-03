# Soiling: dust deposition potential

{doc}`Run this map <auto_examples/plot_13_map_soiling>`

| Example | Input | Output |
| --- | --- | --- |
| {doc}`Soiling <auto_examples/plot_13_map_soiling>` | NASA MERRA-2 GMI modeled monthly surface dust, 2019; sampled land cells | Day-weighted dust concentration and an explicit dry-deposition scenario, g/m²/day |

## Method and interpretation

For each monthly concentration $C$ in µg/m³, deposition velocity $v$ in m/s and
panel tilt $\theta$ measured from horizontal, the illustrative dry mass flux is

$$F = C\,v\,\cos(\theta)\,86400/10^6 \quad [\mathrm{g\,m^{-2}\,day^{-1}}].$$

The defaults are **v = 0.001 m/s** and **tilt = 30°**. They are explicit scenario
assumptions, not locally calibrated constants or a published universal soiling
model. Annual means use month-length weights; the gallery uses the actual 2019
month lengths. Changing velocity scales the output linearly.

This omits rain washing, scheduled cleaning, resuspension, adhesion, particle-size
distribution, sea salt, soot and pollen. It does not turn deposition into optical
losses, annual retained mass or PV energy loss. Actual soiling-loss analysis needs
site-specific particulate and rainfall time series, cleaning records, module
geometry and a validated loss model. MERRA-2 **GMI** is a replay simulation;
unlike MERRA-2 itself, its aerosol optical depth is not constrained by observations.

## Run and export

The bundled snapshot runs offline from a repository checkout.

```bash
python -m pip install -e '.[examples]'
python examples/gallery/plot_13_map_soiling.py
```

```python
from energyclimates.analysis.environment import run_environment

study = run_environment("examples/environment/gmi-2019.parquet", "soiling")
study.write("results/soiling")
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
