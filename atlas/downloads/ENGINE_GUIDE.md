# EnergyClimates user guide

The software answers: **what climate will this energy system experience?**
It provides three experimental profiles, the published KGPV method, and tools to
train or apply your own ML climate groups. Plain names are primary; numeric IDs
are only used for rasters and reproducible lookup tables.

## Start in two commands

Unzip the software, open a terminal in `energyclimates`, and install Python 3.11+:

```bash
python -m pip install -e .
energyclimates classify examples/monthly-climate.csv --mapping examples/monthly-mapping.json
```

This classifies six real CRU/ERA5 grid cells near example locations. The cells
are not station measurements. All three system profiles are calculated by
default. Use `--technology pv`, `hybrid` or `bess` for just one.

Outputs in `results/`:

- `classification.csv`: names, technical IDs, status and reasons for missing data.
- `features.csv`: the climate signals behind the names, with a metadata sidecar.
- `classification.geojson`: points you can open in GIS software.
- `pv.tif`, `hybrid.tif`, `bess.tif`: also produced for a complete regular grid.
- `manifest.json`: explicit mappings, input checksums, period and rule definitions.

For a full reference classification, add monthly precipitation to your mapping:

```bash
energyclimates classify my-weather.nc --mapping configs/netcdf-monthly.json --technology kgpv
```

KGPV follows the original six temperature/precipitation groups, four irradiation
bands and fixed 24-to-12 merge table. This is not an implementation of all 30
standard Köppen–Geiger subtypes.

## Bring data from any provider

“Any provider” means you can map arbitrary column or variable names. It does
**not** mean a dataset can classify variables it does not contain. You must
supply units, time semantics, coordinates and the required climate fields.

| Profile | Required inputs | Name describes |
|---|---|---|
| PV | 12 monthly mean air temperatures + monthly GHI energy | Sunlight level and sunlight-weighted air temperature |
| PV + battery | Same | Solar seasonality and ambient thermal exposure |
| Battery only | 12 monthly mean air temperatures | Coldest and warmest monthly temperature exposure |
| Published KGPV | Temperature + precipitation totals + GHI | Original climate/irradiation classification |

Optional humidity and wind inputs are extracted as features and can be selected
for custom ML experiments. They do not silently alter the default rule profiles.

| Format | Supported organization |
|---|---|
| CSV / Parquet | One interval per fixed location; declared coordinate and field names |
| NetCDF / Zarr | CF time; 1D latitude and longitude axes; select extra dimensions explicitly |
| GeoTIFF | One file per variable; 12 bands ordered January–December; CRS required |

CSV, Parquet, NetCDF and Zarr accept hourly, daily or monthly time series, or an
already calculated 12-month climatology. Monthly means across multiple years
must be declared as `climatology`; dated monthly observations use `monthly`.
Latitude and longitude must be geographic degrees (longitude −180…180 or 0…360).
Generic adapters load local files; download data using the provider's own tools.
The existing `kgpv fetch` command handles the atlas's CRU/GPCC/ERA5 sources.

For large gridded time series, NetCDF/Zarr uses Dask to reduce the time dimension
before loading the 12 monthly outputs. The final grid must fit in memory.
CSV/Parquet are read in memory. GeoTIFFs are processed one band at a time, with
a default 10-million-cell source/destination guard. Crop large inputs first;
explicitly adjust `max_cells` only when sufficient memory is available.
Curvilinear grids need an external reprojection. Unstructured point tables are
supported, but are exported as points rather than interpolated into a raster.

### A monthly CSV mapping

```json
{
  "format": "csv",
  "frequency": "climatology",
  "period": "1991–2020",
  "month_days": [31,28.2666666667,31,30,31,30,31,31,30,31,30,31],
  "coordinates": {
    "id": "site", "latitude": "lat", "longitude": "lon", "month": "month"
  },
  "variables": {
    "temperature": {"column": "air_temperature", "unit": "C"},
    "ghi": {"column": "solar_energy", "unit": "kWh/m2/month"}
  }
}
```

Change the names to your file's actual headers. For timestamped data, use
`frequency: hourly`, `daily` or `monthly`, and `coordinates.time: timestamp`.
You may set `start_year` and `end_year`; otherwise the complete calendar-year
span of the input is required. UTC is the default for tabular times. An explicit
timezone can localize naive hourly timestamps before UTC conversion. Daily
observations must be labelled at midnight UTC and hourly data on whole hours.
Interval values are assumed to belong to the labelled interval; cumulative
running counters must be differenced upstream. TMY timestamps must be normalized
to one consistent representative year or converted to monthly climatology first.

### Units you must distinguish

- Air temperature: `C`, `K`, `F`.
- GHI interval energy: `kWh/m2`, `Wh/m2`, `J/m2`.
- GHI mean flux: `W/m2`, multiplied by the actual interval duration.
- Mean daily GHI energy: `kWh/m2/day` or `J/m2/day`.
- Precipitation: `mm`, `m`, `mm/day`, `mm/hour`, `kg/m2/s`.
- Relative humidity: `%` or `fraction`; wind: `m/s` or `km/h`.

**ERA5 monthly mean SSRD is mean daily accumulated energy:** map it as
`J/m2/day`, not `J/m2`. The adapter multiplies by that calendar month's days.
The example configuration is `configs/era5-monthly.json`; ERA5 cumulative hourly
products require appropriate deaccumulation before this generic adapter.

Each variable can declare `missing_values`, for example `[-9999]`. Missing
intervals invalidate the affected monthly mean; missing months or missing years
invalidate annual features that depend on them. No imputation is performed.
Tabular physical-range violations raise errors; gridded violations become missing
cells before aggregation. Small negative source radiation values can be clipped
only with an explicit `clip_min: 0`, recorded in the mapping.

For an already averaged climatology, supply average calendar month lengths for
its actual period. The default is a non-leap 365-day representative year. CF
NetCDF time supports its declared calendar, including 360-day calendars.

GeoTIFF configuration selects `nearest` (default) or `bilinear` resampling for
continuous monthly inputs. Classification rasters are always rendered using
nearest-neighbour sampling. No spatial interpolation fills temporal gaps.

## What the simple profiles mean

The complete, editable definition is `kgpv/engine/rules-v1.json`.

| Signal | Experimental definition |
|---|---|
| Low / moderate / sunny / very sunny | Annual GHI ≤1130 / ≤1560 / ≤2070 / >2070 kWh/m², retaining KGPV's bands |
| Cool / mild / hot for PV | GHI-weighted monthly ambient temperature <10 / 10–25 / >25°C |
| Strongly seasonal / seasonal / steady sun | Weak-month daily GHI divided by annual daily GHI mean: <0.35 / 0.35–<0.75 / ≥0.75 |
| Cold winters | Coldest monthly mean air temperature <5°C |
| Hot summers | Warmest monthly mean air temperature >30°C |
| Mild year-round | Neither thermal condition above, referring only to monthly averages |

PV combines four sun levels with three temperatures. Hybrid combines three
seasonality levels with four thermal contexts. Battery-only uses only the four
thermal contexts. The weak-month fraction is also supplied with PV output.
Zero annual sunlight cannot define sunlight-weighted temperature or the weak-month
ratio and therefore yields no PV/hybrid profile. Battery classification remains
possible if its temperature inputs are complete.

Temperature and seasonality cutoffs are provisional, not validated engineering
limits. Monthly averages miss daily heat/cold extremes and subdaily variability.
Ambient temperature is not module or battery-cell temperature. These are not
battery safety, chemistry selection, capacity, lifetime, cooling-load or revenue
recommendations. A small battery cannot bridge seasonal sunlight gaps simply
because a location is assigned a hybrid profile.

To make your own rules, copy the JSON, change thresholds/names, assign a new
version and pass `--rules my-rules.json`. Keep published KGPV separate. Custom
rules do not overwrite the hosted atlas automatically.

## Run machine learning

The download includes an actual feature table for 67,420 global land cells on a
0.5° grid, from CRU TS 4.10 and ECMWF ERA5/NCAR for 1996–2022. It contains no
fabricated weather or operational targets. It includes three trained models in
`atlas/models/`: PV (8 groups), hybrid (8), battery (4).

```bash
energyclimates train examples/global-climate-features.parquet --technology pv --clusters 8 --seed 42 --area-weighted --output my-pv-model.json
energyclimates predict examples/monthly-climate.csv --mapping examples/monthly-mapping.json --model my-pv-model.json --output predictions
# Or predict from a previously extracted feature table:
energyclimates predict results/features.csv --features --model atlas/models/bess.json
```

Use `--area-weighted` only for a regular latitude/longitude grid, where
cos(latitude) approximates cell area. Do not use it automatically for a sample
of weather stations. Missing feature rows are excluded explicitly from training.
Training requires enough diverse locations and at least five 10° geographic
blocks. Prediction can operate on one location.

Default predictors:

| Model | Predictors |
|---|---|
| PV | Annual GHI, sunlight-weighted air temperature, weak-month ratio |
| Hybrid | Annual GHI, weak-month ratio, coldest/warmest monthly means |
| Battery | Coldest/warmest monthly means |

Select alternative extracted climate columns with `--feature-columns ...`.
Coordinates, zone labels and outcome/yield variables are excluded from predictor
selection. Custom columns and their physical meaning remain your responsibility.

The model uses weighted standardization and MiniBatch K-means, seed 42 and ten
initializations. A geographic holdout contains 20% of **blocks**, not necessarily
20% of locations. Scaling and evaluation clustering see only training blocks.
Diagnostics include held-out feature distance, unweighted silhouette on up to
1,500 held-out cells and adjusted Rand stability across two other seeds. The
final model is refitted on all complete locations. The requested cluster count
is a provisional choice, not a proven optimum.

Saved models are inspectable JSON numeric arrays, never executable pickle or
joblib files. They contain features, scaler parameters, centres, plain names,
training fingerprints, package versions and diagnostics. Identical training
inputs/order, seed, configuration and software versions reproduce results.
The website reads the same model files and rule definitions as Python.

Predictions provide the nearest group plus a distance-based separation measure.
**Separation is not confidence or a probability.** A flag identifies inputs
outside any training feature range or beyond the group's 95th-percentile
training distance. Approximately some training locations are flagged by design;
this is not a calibrated uncertainty model.

These models are independent atlas experiments. They do not reproduce the
published Delft or Purdue PVZones classifications. Their actual georeferenced
class assignments remain unavailable in this delivery. See the publication
links and availability notes in the website's Data & method tab.

### Test whether climate features predict a practical outcome

Supply a separate measured or consistently simulated outcome: PV specific yield,
battery cooling energy, or battery degradation, with matched periods, equipment
configuration, coordinates and documented provenance. Do not treat a climate
zone label as an independent target.

```bash
energyclimates evaluate-target climate-with-outcome.parquet --target measured_yield --technology pv --output evaluation.json
```

This runs random-forest regression with five geographically separated folds,
RMSE/MAE/R², a training-mean baseline and held-out permutation importance. It
assesses predictor relevance; it does not prove that the chosen clustering is
optimal. Equipment, operations and sampling can confound the result. No real
operational target has been evaluated in the delivered atlas; the automated
software test uses an explicitly synthetic fixture only.

## Use the Python API

```python
from energyclimates import load_dataset, extract_features, classify_features
from energyclimates.ml import train_clusters, predict_clusters, load_model

cube = load_dataset("my-weather.csv", "my-mapping.json")
features = extract_features(cube)
profiles = classify_features(features, technology="hybrid")
profiles.to_csv("my-profiles.csv", index=False)
model = load_model("atlas/models/hybrid.json")
groups = predict_clusters(features, model)
```

An adapter can also produce `ClimateCube(ids, latitude, longitude, values, days,
period, metadata)` directly. `values` is a dictionary of canonical variables,
each with shape `(12, number_of_locations)`; units are °C, monthly kWh/m²,
monthly mm, %, and m/s. NaN means missing. This is the extension point for a
new provider or file format. A pre-extracted feature CSV passed with `--features`
must follow the units and definitions in `kgpv/engine/features.py`.

For PVCZ experiments, `kgpv.engine.rules.pvcz_stressors` computes Arrhenius
equivalent module temperature and temperature velocity from regular hourly or
three-hourly module temperatures and specific humidity. `classify_pvcz` maps
those stressors to temperature/humidity bins. Monthly ambient means cannot
substitute for module temperatures. These utilities declare upper-bin equality;
they are not claimed to recreate every preprocessing step of Todd Karin's
GLDAS pipeline. The atlas's PVCZ rasters remain the checksum-verified published
v0.2 product. A physical module-temperature model additionally requires suitable
irradiance, mounting and wind inputs, such as the documented
[pvlib Faiman model](https://pvlib-python.readthedocs.io/en/stable/reference/generated/pvlib.temperature.faiman.html).

## Add your calculated layer to the website

The software download includes every native GeoTIFF. To reduce duplication, it
omits browser `.bin` and `.png` copies. Recreate them before serving locally:

```bash
energyclimates prepare-website --dist atlas
python -m http.server 8000 --directory atlas
```

For a complete regular square geographic grid, the classifier exports a GeoTIFF
with labels. Add it to your local atlas:

```bash
energyclimates add-layer results/pv.tif --id my-pv --title "My PV climate profiles" --source https://example.org/my-data --dist atlas
```

Use your actual data/provenance URL. This adds the layer to the advanced catalogue
and overlay selector. IDs are prefixed with `custom-`; repeating an ID replaces
that custom layer. This command writes local website files; republish them to
update a hosted site. Point-only or nonsquare grids require explicit preparation
before becoming atlas rasters. Local CSV results can always be downloaded as GIS
points without claiming interpolated map coverage.

To reproduce the new delivered global profiles after fetching original inputs:

```bash
kgpv fetch --start 1996 --end 2022
python scripts/build_energy_atlas.py
```

This retains the 1996–2022 profile period. For a different period, use the generic
adapters and explicit mapping, train the chosen model and add the resulting layer.
A new 1996–2025 full KGPV still requires ERA5 2023–2025 through configured CDS
access. The current common period is 27 years, not a 30-year standard normal.

## References and reuse

- [KGPV, Ascencio-Vásquez et al. (2019)](https://doi.org/10.1016/j.solener.2019.08.072).
- [Todd Karin's PVCZ](https://github.com/toddkarin/pvcz).
- [Delft ML classification](https://doi.org/10.1016/j.renene.2025.123685).
- [PVZones](https://doi.org/10.1016/j.apenergy.2025.126192).
- [Scikit-learn geographic/group validation tools](https://scikit-learn.org/stable/modules/cross_validation.html).
- [BLAST-Lite battery lifetime modelling](https://github.com/NatLabRockies/BLAST-Lite).

Retain provider attribution and data licences in README.md. CRU-derived data and
features are shared under the stated ODbL / Database Contents License terms.
Software, original deposited datasets and derived climate data have separate
licences; do not discard upstream notices when redistributing.
