"""
Map global ML climate groups and assignment separation
======================================================

Run the bundled experimental PV model on all 67,420 global feature rows. This
recreates assignments from the portable JSON model without retraining or network
requests. The map includes the training domain; it is not a held-out evaluation.

Assignment separation is (second-nearest distance minus nearest distance) divided
by second-nearest distance in standardized feature space. It is not a probability,
confidence interval or evidence of better energy performance. Both separation and
the model's atypical-condition status are retained in the exported CSV. Missing
data remain unclassified. See :doc:`/map-examples` for result downloads and export.
"""

import json
from pathlib import Path

import matplotlib.pyplot as plt

from energyclimates.analysis.maps import plot_category_map, plot_grid_map
from energyclimates.methods.ml import load_model, predict_clusters
from kgpv.engine.results import read_features

start = Path(__file__).resolve().parent if "__file__" in globals() else Path.cwd()
root = next(
    p for p in (start, *start.parents) if (p / "examples/global-climate-features.parquet").is_file()
)
input_files = [
    root / "examples/global-climate-features.parquet",
    root / "examples/global-climate-features.metadata.json",
    root / "atlas/models/pv.json",
    root / "atlas/data/catalog.json",
]
features = read_features(input_files[0])
model = load_model(input_files[2])
prediction = predict_clusters(features, model)
layer = next(
    x for x in json.loads(input_files[3].read_text())["layers"] if x["id"] == "energy-ml-pv"
)
fig, axes = plt.subplots(2, 1, figsize=(15, 10), layout="constrained")
fig.get_layout_engine().set(h_pad=0.14, hspace=0.08)
plot_category_map(
    prediction,
    labels=["No data", *model["names"]],
    colors=layer["colors"],
    ax=axes[0],
    title="Experimental PV climate groups",
)
image = plot_grid_map(
    prediction,
    "assignment_separation",
    ax=axes[1],
    title="Assignment separation (not confidence)",
    cmap="cividis",
    vmin=0,
    vmax=1,
)
fig.colorbar(image, ax=axes[1], label="Standardized-distance separation", shrink=0.7, pad=0.02)
fig.suptitle("Global ML climate grouping\nCRU TS 4.10 + ERA5 · 1996–2022 · 0.5° cells", fontsize=15)
result_tables = {"pv_ml_predictions": prediction}
map_context = {
    "method": "Existing experimental PV clustering model",
    "model_version": model["model_version"],
    "training_domain_included": True,
}
print(f"Model: {model['model_version']}; {len(prediction):,} predictions")
print(prediction.status.value_counts().to_string())
print(prediction.assignment_separation.agg(["min", "median", "max"]).round(3).to_string())
plt.show()
