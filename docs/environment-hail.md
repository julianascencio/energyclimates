# Global hail: modeled activity in 2015

{doc}`Run this map <auto_examples/plot_16_map_hail>`

The map now covers the world using **Prein and Holland's PANGAEA V2** environmental
proxy for large hail **>2.5 cm**. It uses every daily field in **2015 only**.
It is not a 1979–2015 climatology; those are the full archive's dates.

## Input → method → analysis

The pinned source has 365 daily fields on 256 native Gaussian latitudes and
512 longitudes (approximately 0.7° spacing). Preserve those axes, sort longitudes,
and sum in float64 without interpolation. Every day must be valid at each cell;
missing data propagate and real zeros remain zero.

For daily probabilities $p_d$, the first panel is $S=\sum_d p_d$ and the second
is $S/365$. The sum is a modeled expected-day indicator by linearity of expectation;
it can exceed one and does not require independent days. Neither panel is the
probability of at least one hail event during a year. Do not calculate a return
period from these indicators.

**Units trap:** the NetCDF `HailProb.units` attribute says `%`, but the
[Version 2 dataset description](https://doi.org/10.1594/PANGAEA.893160) explicitly
defines the stored values as fractions from zero to one. The builder validates
that range and does **not** divide by 100. Display normalization changes only
colours; exported values retain their original scale.

Global grid coverage does not imply uniform observational validation. These are
modeled environmental conditions, not observed hail days, hailstone sizes or
PV damage. One year cannot establish a climate normal, trend, insurance pricing
or engineering design loads. The two panels are alternative units of the same
indicator, not independent evidence. Grey indicates missing values.

## Run and export

```bash
python -m pip install -e '.[examples]'
python examples/gallery/plot_16_map_hail.py
```

```python
from energyclimates.analysis.environment import run_environment

study = run_environment("examples/environment/global-hail-2015.parquet", "global_hail")
study.write("results/global-hail")
```

The checksum-verified offline snapshot includes 131,072 cells. Its metadata
records the exact source hash, period, native axes, units, licence and processing.
Batch downloads include figures, CSVs and the method manifest.

## Sources, attribution and optional rebuild

- Prein, A. F. and Holland, G. (2018),
  [Daily large hail probability on a global scale, Version 2](https://doi.org/10.1594/PANGAEA.893160).
- [Global estimates of damaging hail hazard](https://doi.org/10.1016/j.wace.2018.10.004),
  *Weather and Climate Extremes*, 22, 10–23.
- Derived snapshot and data products: [CC BY 3.0](https://creativecommons.org/licenses/by/3.0/).

```bash
python scripts/build_global_hail_input.py --source raw/global-hail/2015.nc
```

This optional command downloads one approximately 460 MB file; allow at least
1 GB free cache space. It checks the source SHA-256, all dates, native axes and
probability range, then processes daily chunks. Tests and gallery builds never
download it. Source changes require explicit review of the pinned checksum.

## Existing U.S. report API

`run_environment("examples/environment/storm-reports-2020-2024.parquet", "hail",
start_year=2020, end_year=2024)` remains available. It counts distinct report dates
for reported diameters ≥25.4 mm and retains maximum reported size. That dataset
has reporting/population bias and a different threshold from the global model.
Unreported cells remain absent, not zero hazard. See {doc}`environment-maps`.
