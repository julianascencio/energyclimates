# Scientific data, model assets and third-party notices

The root MIT licence covers original EnergyClimates software and documentation.
**It does not apply automatically to the data.** Preserve the following sources,
licences and attribution when redistributing data or derived products.

| Material | Source and terms |
|---|---|
| CRU TS 4.10 temperature; CRU-containing derived climate profiles, feature tables, example weather and model training assets | [CRU](https://crudata.uea.ac.uk/cru/data/hrg/cru_ts_4.10/), [CRU data terms](https://crudata.uea.ac.uk/cru/data/). ODbL / Database Contents License. Derived CRU-containing databases in this repository are made available on those terms. Cite Harris et al. (2020), doi:10.1038/s41597-020-0453-3. |
| ECMWF ERA5 distributed through NSF NCAR | [Dataset](https://doi.org/10.5065/P8GT-0R61), CC BY 4.0 and applicable Copernicus attribution. Contains modified Copernicus Climate Change Service information; neither the European Commission nor ECMWF is responsible for its use. |
| GPCC Monthly v2025 precipitation and derived KGPV inputs | [GPCC / DWD](https://opendata.dwd.de/climate_environment/GPCC/html/gpcc_precipitation_analysis_monthly_v2025_doi_download.html), doi:10.5676/DWD_GPCC/MONTHLY_V2025_050. Retain DWD/GPCC attribution and provider terms. |
| Original KGPV 2019 data and PV metrics | [Mendeley deposit](https://data.mendeley.com/datasets/z3byd8jyfn/1), CC BY 4.0. Authors: Julian Ascencio-Vasquez, Kristijan Brecl and Marko Topic. The original deposited zone labels have an unresolved quality warning; see the atlas reference. |
| Todd Karin's PVCZ v0.2 data | [Upstream repository](https://github.com/toddkarin/pvcz), MIT notice retained at `atlas/downloads/pvcz-LICENSE.txt`. GLDAS/NASA is the underlying climate source; retain upstream attribution. |
| Leaflet | BSD-2-Clause; retained at `atlas/vendor/leaflet-LICENSE.txt`. |
| OpenStreetMap basemap | ODbL; online tile use is subject to the [OSM tile policy](https://operations.osmfoundation.org/policies/tiles/). Tiles are not bundled. |

ODbL text: https://opendatacommons.org/licenses/odbl/1-0/
Database Contents License: https://opendatacommons.org/licenses/dbcl/1-0/
CC BY 4.0: https://creativecommons.org/licenses/by/4.0/

File-level sources, periods and checksums are recorded in `atlas/data/catalog.json`,
`atlas/data/energy-provenance.json`, `atlas/data/pvcz-provenance.json` and the
run manifests. The original upstream raw archives are downloaded separately.
The `atlas/models/*.json` files are experimental model assets derived from the
stated CRU/ERA5 training data; retain their rules, training fingerprints and this
notice when redistributing them.

The source data were retrieved for the September 2026 atlas release. URLs and
provider availability can change. Inclusion of research references does not
redistribute those papers or imply author endorsement of the new classifications.
