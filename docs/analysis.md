# Analysis

```python
from energyclimates.analysis import run_classification
from energyclimates.inputs import example_climate

study = run_classification(example_climate(), technology="all")
study.write("results/study-001")
```

The returned `ClassificationStudy` contains `features`, `classifications` and
`manifest`. Computation and writing are separate, so applications can inspect
or plot the result without filesystem side effects. File inputs require a mapping;
passing a mapping for an already normalized cube is rejected.

| Saved output | Contract |
| --- | --- |
| `features.csv` | One row per input location, including missing feature values |
| `features.metadata.json` | Feature units, period and source metadata |
| `classification.csv` | One row per location and requested technology |
| `classification.geojson` | Geographic points; missing scalar properties become null |
| `manifest.json` | Package version, requested technologies, rules or method reference, input provenance and limits |
| `<technology>.tif` | Only for a complete regular geographic grid; EPSG:4326, ID 0 is nodata |

Use a fresh output directory for each study. Matching files are replaced; unrelated
files remain. The workflow does not interpolate stations into a raster or change
the hosted atlas. Existing CLI commands use the same table and map exporter.

A manifest retains input checksums for file adapters. An in-memory cube retains
its supplied metadata; it does not claim to be a frozen source-file snapshot.
The synthetic demo label is preserved in the manifest. No provider request is
made by `run_classification`.

For ML studies, use `energyclimates.methods.ml` and the existing `train`, `predict`
and `evaluate-target` commands. Inspect holdout diagnostics, missing-data counts,
source periods and assumptions before interpreting any map as useful energy evidence.

## Environmental maps

The [environmental workflows](environment-maps.md) cover soiling, snow,
thunderstorms, hail, vegetation and population, with runnable inputs, explicit
methods and exported analysis results. Use the corresponding
`energyclimates.analysis.environment` module.
