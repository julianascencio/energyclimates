# KGPV Atlas

Reproducible Python calculation software and a static map explorer for
Köppen–Geiger–Photovoltaic climate classification.

## Start with simple PV and battery profiles

The updated atlas has **49 layers**, including experimental plain-language PV,
PV + battery and battery-only profiles, three independent ML maps, KGPV and
Todd Karin's published PVCZ layers.

```bash
python -m pip install -e .
pvclimate classify examples/monthly-climate.csv --mapping examples/monthly-mapping.json
```

Use data from any provider with sufficient variables and explicit unit mappings:
CSV, Parquet, NetCDF, Zarr or monthly GeoTIFF. Python supports hourly, daily,
monthly and climatological inputs. The browser calculator supports monthly CSV.
It processes files locally and can apply the same rules or trained ML models.

```bash
pvclimate train examples/global-climate-features.parquet --technology pv --clusters 8 --area-weighted --output my-model.json
pvclimate predict examples/monthly-climate.csv --mapping examples/monthly-mapping.json --model my-model.json
```

[The full guide](docs/ENGINE_GUIDE.md) covers field mappings, rules, Python APIs,
training, evaluation and adding your own calculated layer to the website.
The download includes 67,420 real feature rows and three trained JSON models.
New profiles describe climate exposure; they have not been validated as estimates
of PV yield, battery size, battery life, safety or financial value.

## Delivered runs

| Output | Period | Inputs | Status |
|---|---|---|---|
| 12-zone KGPV, 24 raw zones, irradiation zones and climate inputs | 1996–2022 | CRU TS 4.10; GPCC Monthly v2025; ECMWF ERA5 distributed by NSF NCAR | Calculated |
| Temperature, precipitation, TP zones | 1996–2025 | CRU TS 4.10; GPCC Monthly v2025 | Calculated |
| Full latest-common-year KGPV | 1996–2025 | Same datasets, with ERA5 2023–2025 from CDS | Not calculated: CDS access required |
| Original classification and nine continuous PV/climate fields | 1990–2016, published 2019 | Mendeley DOI 10.17632/z3byd8jyfn.1 | Displayed unchanged; label-quality issue |

The current common irradiation period has **27 complete years**, not a WMO
30-year standard normal. The intended 1996–2025 refresh has 30 complete years.
No synthetic meteorology, interpolated years, or invented future maps are used.

## Run

Python 3.11 or later. Allow about 2 GB of disk and 2 GB of RAM for input
archives, extraction and processing; four parallel downloads are used.

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e .
# Recreate the delivered common-period run (public, no credentials):
kgpv fetch --start 1996 --end 2022
kgpv calculate --start 1996 --end 2022
# Recreate the temperature/precipitation-only refresh:
kgpv calculate --start 1996 --end 2025 --climate-only
kgpv publish-layers
# Rebuild browser assets from included native GeoTIFFs after unzipping:
pvclimate prepare-website --dist atlas
# Serve the website locally:
python -m http.server 8000 --directory atlas
```

On Windows activate with `.venv\Scripts\activate`.
The download includes website source and all native GeoTIFFs; run
`pvclimate prepare-website` to recreate redundant browser image/value assets.
Raw input archives are needed only to recalculate climate features.

## PVCZ overlays and machine-learning classifications

The explorer includes a second-layer selector, swipe comparison, independent
transparency, both native-cell readings, GeoTIFFs and a location CSV containing
all layers. KGPV uses a 0.5° grid; PVCZ uses its original 0.25° grid.

[PVCZ by Todd Karin, C. Birk Jones and Anubhav Jain](https://github.com/toddkarin/pvcz)
is a degradation-oriented classification. The 18 imported layers cover its
combined temperature/humidity zones, component zones, KG reference, principal
thermal, humidity, radiation and wind stressors. The product uses GLDAS from
2010–2018. This is an import of v0.2, **not a recent GLDAS recalculation**.

```bash
python -m kgpv.external
# Include the 20 other published equivalent-temperature activation-energy fields:
python -m kgpv.external --all-activation-energies
```

The importer pins commit `aa89fab8d1d66f46f4ea8575e2452aa75a927535` and checks
SHA-256 digests. It reads CSV and numeric NPZ arrays with `allow_pickle=False`.
The CSV rounds coordinates to three significant digits, producing 52,975
duplicate coordinate pairs. Its 230,742 rows are validated against the author's
original coordinate arrays and `keepers` mask before rasterization. Do not
resample or deduplicate these rounded coordinates. All categorical IDs become
source ID + 1 to reserve zero; raster no-data is NaN. ASCE −5 values are missing;
zero denotes special wind regions and is retained only in the categorical map.
ASCE data are historical, U.S.-limited and are not current design guidance.
Additional activation-energy fields are optional; duplicate metadata fields and
the questionable `specific_humidity_rms` column are not mapped. See the import
provenance for the exact decisions. All colours are atlas palettes.

Two KGPV-citing ML classifications are documented under **Data & method**:

- [Triana de las Heras, Isabella & Vogt, Renewable Energy 256 (2026), 123685](https://doi.org/10.1016/j.renene.2025.123685):
  online June 2025; supervised feature selection and k-means, seven features,
  21 clusters, 1991–2021 climate on a 0.5° grid. It uses KGPV simulated c-Si
  yield as its performance reference. The paper states that geographic class
  assignments are in the supplement, but that supplement could not be retrieved
  here. No published raster or substitute clustering has been ingested.
- [Jahangir & Alam, Applied Energy (2025), 126192](https://doi.org/10.1016/j.apenergy.2025.126192):
  its [open preprint](https://arxiv.org/abs/2407.18284) cites KGPV as reference 17
  and describes seven PVZones using GHI, temperature and clearness index. No
  georeferenced downloadable zone dataset was located in this search.

Search checked 2026-09-13. Paper availability is distinct from raster availability.
To import either published ML map faithfully, obtain the authors' geographic
zone assignments and label key. No labels have been digitized from paper figures.

`atlas/data/external-catalog.json` preserves the imported layers when
`kgpv publish-layers` regenerates KGPV outputs. Re-running the PVCZ importer is
idempotent. Its default 18 layers are included in the software download.

## Complete the 2025 KGPV update

Create a [Copernicus CDS account](https://cds.climate.copernicus.eu/how-to-api),
accept the dataset licence and configure the standard `.cdsapirc` file locally.
Do not put tokens in the repository or upload them to the website. The software
uses `cdsapi.Client()` and the user's existing CDS configuration.

```bash
kgpv fetch --start 1996 --end 2025
kgpv calculate --start 1996 --end 2025
kgpv publish-layers
```

`fetch` resumes cached inputs. Years through 2022 use the public NCAR
distribution of ECMWF ERA5; later years use CDS. Both are the same ECMWF
reanalysis, not different solar-resource models. CDS retrieval was not tested
against an authenticated account in this delivery. Incompatible NetCDF shapes
or units cause explicit errors instead of guessed conversions.

After regenerating `atlas/`, publish that directory with the same Site identity.
Calculations run in Python on a local machine/server; this hosted website serves
finished artifacts. It does not run long Python jobs inside the browser.

## Scientific choices

- Temperature–precipitation classification: published Figure A1, including
  polar-first precedence, −3°C temperate/cold boundary and hemisphere-aware
  summer precipitation. Threshold precipitation is 20*Tann plus 0, 140 or
  280 mm, with two-thirds seasonal rainfall cutoffs following Kottek.
- `Tann` is the unweighted mean of 12 climatological monthly temperature means.
- Irradiation boundaries are fixed at 1,130, 1,560 and 2,070 kWh/m²/year.
  Exact boundaries remain in the lower irradiation class, explicitly documented
  here because the source figure does not specify equality.
- Class merging follows the paper's Table 4. No new population ranking or new
  percentile boundaries are calculated. Keeping these fixed supports comparison.
- CRU and GPCC use their native 0.5° cell-centred grid. ERA5 values are sampled
  at coincident cell centres of its 0.25° grid. This is point sampling, not a
  conservative area-average, and differs from regridding to the original CSV's
  integer/half-degree coordinate centres. No apparent fine detail is invented.
- GPCC `precip` is used, not `precip_infill`. Every calendar month in the selected
  period must exist, and every cell needs all years for each month. No gap filling.
- ERA5 `moda` SSRD is a monthly mean of **daily accumulated energy**. Multiply
  by actual days in the month (including leap years), then divide by 3,600,000
  to obtain monthly kWh/m². Sum the 12 climatological months for annual GHI.
- New outputs are research calculations, not independently validated.
  Differences from 2019 combine climate period changes, source revisions,
  ERA-Interim → ERA5 and grid alignment changes; do not attribute them solely
  to climate change.
- Categorical exports use no-data, nearest-neighbour rendering and no smoothing.
  Colour-scale limits for continuous layers are 2nd–98th percentiles; numerical
  inspection and GeoTIFFs retain values outside that display range.

## Original data issue

The SHA-256-verified Mendeley file contains 55,418 points, spanning 55°S–70°N.
At 55°S, 68°W the deposited label is AK, while annual GHI is 945.969 kWh/m² and
mean ambient temperature is 5.045°C. A class-label ordering mismatch is
suspected. Labels and numbers are displayed as deposited; no automatic label
inversion or baseline change map has been applied. See
`atlas/downloads/data-quality.json`. Confirm this with the original author before
using the baseline classes scientifically. The dataset header's `Tamb_avg`
description conflicts with its variable name; the UI interprets it as air
temperature and retains the separate `Tmod_avg` and `Tmod_max` columns.

The original annual yield, PR, capacity factor, module temperatures, effective
irradiation and optimal tilt are **original model outputs**, not newly simulated
PV performance. The new software calculates the classification and its climate
inputs. IPSL future projections are catalogued but not ingested.

## Output files and validation

- `work/monthly-START-END.npz`: full-precision monthly climatologies.
- `work/layers-START-END.npz`: arrays for derived layers.
- `work/run-START-END.json`: period, method and input SHA-256 digests.
- `atlas/data/*.tif`: geographic GeoTIFF rasters; `*.bin`: float32 cell values.
- `atlas/data/*.png`: nearest-neighbour Web Mercator map previews.
- `atlas/data/catalog.json`: extensible browser layer catalogue.

```bash
python -m unittest discover -s tests -v
node --check atlas/app.js
```

Tests cover climate ordering, dryness and temperature thresholds, hemispheres,
all 24 class merges, no-data, duplicate/missing months and ERA5 leap-month units.
See `docs/validation.md` for the actual delivered checks and remaining limits.
Browser interaction testing and WebMCP runtime validation were not available
within the permitted workflow for this delivery.

## Attribution and licences

- [Method, Ascencio-Vásquez, Brecl & Topič (2019)](https://doi.org/10.1016/j.solener.2019.08.072).
- [Original data, CC BY 4.0](https://data.mendeley.com/datasets/z3byd8jyfn/1).
- [CRU TS 4.10](https://crudata.uea.ac.uk/cru/data/hrg/cru_ts_4.10/): Climatic
  Research Unit, University of East Anglia; ODbL and Database Contents License,
  attribution and share-alike. Derived CRU-containing databases are shared on
  those terms. Cite Harris et al. (2020), doi:10.1038/s41597-020-0453-3.
- [GPCC Monthly v2025](https://opendata.dwd.de/climate_environment/GPCC/html/gpcc_precipitation_analysis_monthly_v2025_doi_download.html):
  GPCC/DWD, doi:10.5676/DWD_GPCC/MONTHLY_V2025_050. Retain attribution and provider terms.
- [ECMWF ERA5, NCAR distribution](https://doi.org/10.5065/P8GT-0R61): CC BY 4.0.
  Contains modified Copernicus Climate Change Service information. Neither the
  European Commission nor ECMWF is responsible for its use.
- [ERA5 monthly means, CDS](https://cds.climate.copernicus.eu/datasets/reanalysis-era5-single-levels-monthly-means).
- [ECMWF accumulated-variable conversion](https://confluence.ecmwf.int/pages/viewpage.action?pageId=197702790).
- Leaflet 1.9.4: BSD-2-Clause; OpenStreetMap basemap: ODbL and tile-provider terms.

Raw climate files are not committed. Their provider releases, retrieval scripts
and SHA-256 manifests make the computation traceable. Scientific software and
data licences are distinct; retain all upstream notices when redistributing.
