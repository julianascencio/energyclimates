# EnergyClimates

**Understand the climate behind your energy system.**

Open-source Python tools to classify, compare and map climates for solar PV,
PV + battery systems and standalone battery storage. Use ordinary names such as
**“Sunny · mild”**, **“Seasonal sun · cold winters”** and **“Hot summers”**.

The project includes established classification methods, experimental energy
profiles, machine-learning tools, dataset adapters and a locally runnable atlas.
The experimental methods are clearly labelled; published methods retain their
original scientific references.

## What works today

| Capability | Status |
|---|---|
| KGPV: six temperature/precipitation groups, four irradiation bands and 12 merged zones | Implemented; fixed published method with documented boundary conventions |
| Todd Karin's PVCZ v0.2 | 18 published map layers, checksum-verified importer, classification and subdaily stressor utilities |
| Plain-language PV, PV + battery and battery-only profiles | Implemented, **experimental** |
| ML training, portable JSON models and prediction | Implemented, **experimental**; geographic holdout diagnostics |
| CSV, Parquet, NetCDF, Zarr and monthly GeoTIFF input | Implemented with explicit variable/unit mappings |
| Interactive atlas | 49 layers, comparison overlays, location inspection and browser-local monthly CSV classification |
| Wind-specific or other energy technology classifications | Future scope; not implemented |
| Published Delft and Purdue PVZones ML maps | Referenced; their geographic assignments are not included |

New profile layers use CRU TS 4.10 and ECMWF ERA5/NCAR for **1996–2022**.
The temperature/precipitation refresh covers **1996–2025**. A full 2025 KGPV
refresh still requires newer ERA5 inputs through configured Copernicus CDS access.
The current 27-year common period is not a 30-year climate normal.

## Start here

Python 3.11 or later:

```bash
git clone https://github.com/julianascencio/energyclimates.git
cd energyclimates
python -m pip install -e .
energyclimates classify examples/monthly-climate.csv --mapping examples/monthly-mapping.json
```

The included CSV contains real monthly values from six CRU/ERA5 grid cells.
The command writes plain-language profiles for all three technologies, feature
tables, map points and a manifest into `results/`. Complete regular grids also
produce labelled GeoTIFFs.

You can also run `python -m energyclimates ...`. The earlier `pvclimate` and
`kgpv` commands remain available for compatibility and provider refreshes.
This project has not yet been published to PyPI; install from this repository.

## Use your own data

```bash
energyclimates classify my-weather.nc --mapping configs/netcdf-monthly.json --technology kgpv
energyclimates classify my-weather.csv --mapping my-mapping.json --technology hybrid
```

Data can come from any provider **if it contains the required variables**.
Supply field names, units, coordinates and time frequency in a JSON mapping.
Hourly, daily, monthly and climatological inputs are supported; a GeoTIFF input
uses 12 monthly bands. Missing observations remain missing.

Battery-only profiles need temperature. PV and hybrid profiles also need GHI.
Published KGPV additionally needs precipitation. See the
[dataset and API guide](docs/ENGINE_GUIDE.md) and ready-to-edit [mappings](configs/).

```python
from energyclimates import load_dataset, extract_features, classify_features

weather = load_dataset("examples/monthly-climate.csv", "examples/monthly-mapping.json")
features = extract_features(weather)
profiles = classify_features(features, technology="hybrid")
print(profiles[["location_id", "zone_name"]])
```

## Train or use an ML model

The repository includes 67,420 real global climate-feature rows and trained PV,
hybrid and BESS models. Model files are inspectable JSON, not executable pickle.

```bash
energyclimates train examples/global-climate-features.parquet --technology pv --clusters 8 --area-weighted --output my-pv-model.json
energyclimates predict examples/monthly-climate.csv --mapping examples/monthly-mapping.json --model my-pv-model.json --output predictions
```

Use area weighting for a regular geographic grid, not automatically for a sample
of stations. Evaluation holds out complete geographic blocks and fits the scaler
only on training blocks. Final models are refitted on all complete training data.
The chosen cluster counts are provisional. These models are independent atlas
experiments, not reproductions of published Delft or Purdue classifications.

For a separate measured or consistently simulated yield/cooling/degradation
outcome, `energyclimates evaluate-target` performs spatial cross-validation and
reports regression errors against a baseline. No real operational outcome has
yet validated the new classifications.

## Open the atlas locally

Native GeoTIFFs are included. Rebuild the redundant browser image/value assets:

```bash
energyclimates prepare-website --dist atlas
python -m http.server 8000 --directory atlas
```

Open `http://localhost:8000`. The atlas offers simple profiles first, with all
scientific layers and technical codes under advanced controls. Its CSV calculator
processes files in your browser. Python computations run on your own machine.
The basemap needs internet access; the bundled scientific layers do not.

Add your calculated grid to the layer selector:

```bash
energyclimates add-layer results/pv.tif --id my-pv --title "My PV profiles" --source https://example.org/my-data --dist atlas
```

Replace the example source URL with your actual dataset/provenance URL.

## Scientific limits

The new temperature and seasonality boundaries are provisional climate screening
choices. Monthly air temperature is not module or battery-cell temperature and
does not describe daily extremes. These profiles do not determine PV yield,
storage size, battery safety, lifetime, cooling load or financial return.

The original 2019 KGPV deposit has a suspected zone-label ordering mismatch.
Original labels are preserved with a warning; they are not used to claim climate
zone changes. Read the [atlas reference](docs/ATLAS_REFERENCE.md),
[validation record](docs/validation.md) and [roadmap](docs/ROADMAP.md).

## Development

```bash
python -m pip install -e '.[dev]'
python -m unittest discover -s tests -v
node tests/test_map_math.cjs
python -m build --outdir dist
```

Node.js is needed only for the browser/Python parity and map-math tests.
The Python runtime itself does not require Node. `energyclimates` is the public
API; `kgpv/` retains the existing implementation and compatibility interfaces.
See [CONTRIBUTING.md](CONTRIBUTING.md) for scientific and code contributions.

## Citation and licence

Cite the relevant scientific method and its data providers in addition to this
software. [CITATION.cff](CITATION.cff) supplies software citation metadata.
Key methods: [KGPV (2019)](https://doi.org/10.1016/j.solener.2019.08.072),
[PVCZ](https://github.com/toddkarin/pvcz),
[Delft ML classification](https://doi.org/10.1016/j.renene.2025.123685) and
[PVZones](https://doi.org/10.1016/j.apenergy.2025.126192).

Original software and documentation: **MIT**. Climate data, derived databases,
model assets and bundled third-party software retain their separate terms.
Read [DATA_LICENSES.md](DATA_LICENSES.md), [LICENSE](LICENSE) and [NOTICE](NOTICE).
