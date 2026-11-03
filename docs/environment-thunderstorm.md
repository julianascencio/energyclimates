# Thunderstorms: reported wind and lightning exposure

{doc}`Run this map <auto_examples/plot_15_map_thunderstorm>`

| Example | Input | Output |
| --- | --- | --- |
| {doc}`Thunderstorms <auto_examples/plot_15_map_thunderstorm>` | NOAA NCEI U.S. Thunderstorm Wind and Lightning reports, 2020–2024 | Distinct local report dates/year in 1° bins; separate wind and lightning maps |

## Method and interpretation

The method uses the event's **BEGIN** point and local calendar date, bins the
point into an explicitly declared grid and counts unique dates. Multiple events
on the same day in one cell count as one report day. Divide by the declared
inclusive record length, **five years**, including years without a matching
report. Event counts remain available separately.

Thunderstorm wind and lightning are analyzed separately.
NOAA Storm Events is a U.S. inventory of significant/damaging weather reports,
with population, observation and reporting biases. It is not a worldwide storm
climatology. The maps display the contiguous-U.S. rectangle; the CSVs retain
qualifying reports elsewhere in the U.S. **Unreported cells stay absent** and
are not evidence of zero hazard. No annual probability, return period, lightning
flash density, hail kinetic energy or PV damage is inferred. Records cover only
2020–2024 and should not be treated as a long-term climate normal.

## Run and export

The bundled snapshot runs offline from a repository checkout.

```bash
python -m pip install -e '.[examples]'
python examples/gallery/plot_15_map_thunderstorm.py
```

```python
from energyclimates.analysis.environment import run_environment

study = run_environment("examples/environment/storm-reports-2020-2024.parquet", "thunderstorm", start_year=2020, end_year=2024)
study.write("results/thunderstorm")
```

The export retains numerical indicators, units, assumptions and source checksums.
See [input contracts and batch downloads](environment-maps.md) for shared APIs.

## Sources and optional refresh

- [NOAA Storm Events bulk archive](https://www.ncei.noaa.gov/pub/data/swdi/stormevents/csvfiles/)
  and [field definitions](https://www.ncei.noaa.gov/pub/data/swdi/stormevents/csvfiles/Storm-Data-Bulk-csv-Format.pdf).
  Exact annual revision filenames are pinned in the builder and metadata.

```bash
python scripts/build_environment_inputs.py --dataset storms
```

Refresh is explicit; tests and gallery builds never download provider data.
