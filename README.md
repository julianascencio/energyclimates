# EnergyClimates

<p align="center">
  <a href="https://asvaconsulting.com"><img src="https://asvaconsulting.com/wp-content/uploads/2022/05/ASVA-1-1-scaled.jpg" alt="ASVA Consulting" width="280"></a>
</p>
<p align="center">
  <strong>Created by ASVA Consulting</strong><br>
  <a href="https://asvaconsulting.com">asvaconsulting.com</a> ·
  <a href="mailto:contacto@asvaconsulting.com">contacto@asvaconsulting.com</a>
</p>

**Understand the climate behind your energy system.**

Open-source Python tools to classify, compare and map climates for solar PV,
PV + battery systems and standalone battery storage. EnergyClimates connects
explicit climate inputs, reusable scientific methods and reproducible analyses.
Published methods retain their references; new profiles and ML models are
clearly identified as experimental.

[Documentation](https://julianascencio.github.io/energyclimates/) ·
[Example gallery](https://julianascencio.github.io/energyclimates/auto_examples/index.html) ·
[API reference](https://julianascencio.github.io/energyclimates/api.html) ·
[Interactive atlas](https://julianascencio.github.io/energyclimates/atlas/index.html) ·
[Release setup](docs/releasing.md)

Documentation uses **Sphinx + the PyData theme**, following
[OrbitalPV](https://julianascencio.github.io/orbital-pv/) and
[Energy Data Insights](https://julianascencio.github.io/energy-data-insights/).
The Pages workflow publishes after merge to `main`; first-time repository Pages
setup may be required. Links above are the deployment destinations.

## Input → methods → analysis

| Layer | Python namespace | Responsibility |
| --- | --- | --- |
| Input | `energyclimates.inputs` | Explicit variable/unit/calendar mappings, local file adapters, provider retrieval and provenance |
| Methods | `energyclimates.methods` | Climate features, KGPV/PVCZ and experimental PV, hybrid, BESS and ML methods |
| Analysis | `energyclimates.analysis` | Reproducible studies, tables, maps and manifests |

One distribution installs all three layers. The existing engine is reused;
`energyclimates` root imports, `energyclimates.ml`, `energyclimates.pvcz`, `kgpv`
and the `energyclimates`, `pvclimate`, `kgpv` commands remain compatible.
See the [architecture guide](docs/architecture.md).

## Install

Python **3.11–3.13** are covered by CI. Install from the repository:

```bash
python -m pip install "energyclimates @ git+https://github.com/julianascencio/energyclimates.git"
```

The new API is available on the redesign branch until its PR is merged. Wheels
and source distributions are built and checked by CI. Install a downloaded wheel:

```bash
python -m pip install ./energyclimates-0.2.0-py3-none-any.whl
```

After the first PyPI release is published, the index command is
`python -m pip install energyclimates`. **A configured release workflow is not an
already published PyPI release.** See [release instructions](docs/releasing.md)
for the one-time trusted-publisher setup.

Optional extras: `.[examples]` adds plotting; `.[docs]` adds the documentation
stack; `.[dev]` adds tests and distribution checks. For development:

```bash
git clone https://github.com/julianascencio/energyclimates.git
cd energyclimates
python -m pip install -e '.[dev,docs]'
```

## Quickstart from an installed wheel

No checkout, credentials or downloads are needed. These four climate profiles
use **synthetic data**, not measured climatologies.

```python
from energyclimates.inputs import example_climate
from energyclimates.analysis import run_classification

study = run_classification(example_climate())
print(study.classifications[["location_id", "technology", "zone_name", "status"]])
study.write("results/synthetic-study")
```

The default produces 12 rows: four locations × three experimental profiles.
Select `technology="pv"`, `"hybrid"`, `"bess"` or the separate published
`"kgpv"` method. Computation returns a `ClassificationStudy`; writing exports
CSV, metadata JSON, GeoJSON and GeoTIFFs for complete regular geographic grids.

Use the layers separately when integrating another application:

```python
from energyclimates.inputs import load_dataset
from energyclimates.methods import extract_features, classify_features

cube = load_dataset("my-weather.csv", "my-mapping.json")
features = extract_features(cube)
profiles = classify_features(features, technology="hybrid")
```

The [input guide](docs/inputs.md) defines units and data contracts;
[methods](docs/methods.md) separates published and experimental algorithms;
[analysis](docs/analysis.md) defines outputs and provenance.

## What works today

| Capability | Status |
| --- | --- |
| KGPV: six temperature/precipitation groups, four irradiation bands and 12 merged zones | Implemented; fixed published method and explicit boundaries |
| Todd Karin's PVCZ v0.2 | 18 published map layers, checksum-verified importer, classification and subdaily stressor utilities |
| Plain-language PV, PV + battery and battery-only profiles | Implemented, **experimental** |
| ML training, portable JSON models and prediction | Implemented, **experimental**; geographic holdout diagnostics |
| CSV, Parquet, NetCDF, Zarr and monthly GeoTIFF inputs | Implemented; explicit variable/unit mappings |
| Interactive atlas | 49 layers, comparison overlays, location inspection and browser-local monthly CSV classification |
| Wind-specific or other energy technology classifications | Future scope; not implemented |
| Published Delft and Purdue PVZones ML maps | Referenced; geographic assignments are not included |

## Run real-data and ML examples

From a repository checkout:

```bash
energyclimates classify examples/monthly-climate.csv \
  --mapping examples/monthly-mapping.json --output results/sample
python examples/quickstart.py
```

The sample contains monthly temperature and GHI from six real CRU/ERA5 grid cells
for **1996–2022**. They are not station observations. It has no precipitation,
so it cannot run KGPV without additional input.

For your own data:

```bash
energyclimates classify my-weather.nc --mapping configs/netcdf-monthly.json --technology kgpv
energyclimates classify my-weather.csv --mapping my-mapping.json --technology hybrid
```

The repository also includes 67,420 global climate-feature rows and fitted models:

```bash
energyclimates train examples/global-climate-features.parquet \
  --technology pv --clusters 8 --seed 42 --area-weighted --output my-pv-model.json
energyclimates predict examples/monthly-climate.csv \
  --mapping examples/monthly-mapping.json --model my-pv-model.json --output predictions
```

Use area weighting for a regular geographic grid, not automatically for stations.
Models retain geographic holdout diagnostics and explicit seeds. These are
independent experiments, not reproductions of the published Delft/PVZones maps.
`energyclimates evaluate-target` supports spatial cross-validation against a
separate measured or consistently simulated target; no real operational outcome
has yet validated the new classifications.

The [gallery](examples/gallery/) includes input inspection, real-cell profiles,
KGPV, missing-data behavior, ML prediction and a complete study export.

## Documentation and atlas

```bash
python scripts/build_docs.py
python -m http.server 8000 --directory docs/_build/html
```

Open `http://localhost:8000` for documentation and `/atlas/` for the atlas.
The build runs the gallery, treats Sphinx warnings as errors and rebuilds browser
assets from the bundled native GeoTIFFs. It does not download fresh climate data.
To run only the standalone atlas:

```bash
energyclimates prepare-website --dist atlas
python -m http.server 8000 --directory atlas
```

The basemap needs internet access; bundled scientific layers and browser CSV
processing work locally. The Python wheel contains code and rules, while the
atlas and large example datasets remain in the repository/source distribution.

## Scientific evidence and limits

New profile layers use CRU TS 4.10 and ECMWF ERA5/NCAR for **1996–2022**.
The temperature/precipitation refresh covers **1996–2025**; a full KGPV refresh
through 2025 still requires newer ERA5 inputs via configured CDS access.
The common 27-year period is not a 30-year climate normal.

Temperature and seasonality boundaries for the new profiles are provisional.
Monthly air temperature is not module or battery-cell temperature and omits daily
extremes. Climate profiles do not determine PV yield, storage size, battery safety,
lifetime, cooling load or financial return. Missing data remain unclassified.

The original 2019 KGPV deposit has a suspected zone-label ordering mismatch.
Original labels are retained with a warning and are not used to claim climate-zone
changes. See the [atlas reference](docs/ATLAS_REFERENCE.md),
[validation record](docs/validation.md) and [roadmap](docs/ROADMAP.md).

## AI-assisted development

Code, documentation, examples and tests are developed with AI assistance under
developer direction, using specifically identified literature and datasets.
Scientific assumptions, published methods and experimental choices must remain
traceable to their sources. Validation is evolving and errors may remain; check
assumptions and results for your intended use. Passing software tests does not
establish independent scientific or energy-performance validation.

## Quality and releases

```bash
python -m pytest
node tests/test_map_math.cjs
python -m build
python -m twine check dist/*
python scripts/check_distribution.py dist
python scripts/build_docs.py
```

CI checks Python 3.11, 3.12 and 3.13, existing browser parity, distributions and
installed-wheel imports/resources/commands from outside the checkout. The
release workflow checks the version against a published GitHub release tag,
then uses PyPI Trusted Publishing. See [contributing](CONTRIBUTING.md),
[changes](CHANGELOG.md) and [release setup](docs/releasing.md).

## Citation, licence and contact

Cite the software revision and the scientific methods and providers actually used.
[CITATION.cff](CITATION.cff) supplies software citation metadata. Key references:
[KGPV (2019)](https://doi.org/10.1016/j.solener.2019.08.072),
[PVCZ](https://github.com/toddkarin/pvcz),
[Delft ML classification](https://doi.org/10.1016/j.renene.2025.123685) and
[PVZones](https://doi.org/10.1016/j.apenergy.2025.126192).
See the [reference catalogue](docs/references.md) for their relationship to the code.

Original software and documentation: **MIT**. Data, derived databases, model assets
and third-party software retain their separate terms in
[DATA_LICENSES.md](DATA_LICENSES.md), [LICENSE](LICENSE) and [NOTICE](NOTICE).

Created and maintained by **ASVA Consulting** · [asvaconsulting.com](https://asvaconsulting.com) ·
[contacto@asvaconsulting.com](mailto:contacto@asvaconsulting.com).
