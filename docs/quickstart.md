# Quickstart

This runs from an installed wheel, in any directory, without downloads or credentials.
The four locations and all weather values are **synthetic**.

```python
from energyclimates.inputs import example_climate
from energyclimates.analysis import run_classification

study = run_classification(example_climate())
print(study.classifications[["location_id", "technology", "zone_name", "status"]])
study.write("results/synthetic-study")
```

The default produces 12 rows: four locations × three experimental profiles.
`technology="kgpv"` selects the separate published KGPV method, using the
synthetic monthly precipitation included in the example.

## Use the layers independently

```python
from energyclimates.inputs import example_climate
from energyclimates.methods import extract_features, classify_features

cube = example_climate()
features = extract_features(cube)
profiles = classify_features(features, technology="hybrid")
```

## Run the bundled real-data example from a checkout

```bash
energyclimates classify examples/monthly-climate.csv   --mapping examples/monthly-mapping.json --output results/sample
python examples/quickstart.py
```

These are six real CRU/ERA5 grid cells for 1996–2022, not station observations.
The sample has temperature and GHI but no precipitation; it cannot classify KGPV.
The original quickstart also reads a trained model from `atlas/models/`.

For your own local files:

```python
from energyclimates.analysis import run_classification

study = run_classification("my-weather.csv", "my-mapping.json", technology="pv")
study.write("results/my-study")
```

The [input guide](inputs.md) explains the required mapping. See the
[analysis guide](analysis.md) for outputs, provenance and missing-data handling.
