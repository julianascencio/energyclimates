"""
Predict with an existing experimental ML model
======================================================

Apply the repository's portable PV model to the six real sample grid cells.
These independent experimental clusters do not reproduce published Delft or
PVZones geographic assignments. Distance separation is not a probability or
energy-performance validation.
"""

from pathlib import Path

import matplotlib.pyplot as plt

from energyclimates.inputs import load_dataset
from energyclimates.methods import extract_features
from energyclimates.methods.ml import load_model, predict_clusters

# Gallery/notebooks run without __file__; direct scripts can run from any directory.
start = Path(__file__).resolve().parent if "__file__" in globals() else Path.cwd()
root = next(p for p in (start, *start.parents) if (p / "examples/monthly-climate.csv").is_file())
features = extract_features(
    load_dataset(root / "examples/monthly-climate.csv", root / "examples/monthly-mapping.json")
)
model = load_model(root / "atlas/models/pv.json")
prediction = predict_clusters(features, model)
print(prediction[["location_id", "zone_name", "status"]].to_string(index=False))
fig, ax = plt.subplots(figsize=(8, 4), layout="constrained")
for zone in prediction.zone_id.unique():
    mask = prediction.zone_id == zone
    ax.scatter(
        features.loc[mask, "ghi_annual_kwh_m2"],
        features.loc[mask, "solar_weighted_temperature_c"],
        label=f"Cluster {zone}",
        s=65,
    )
ax.set_xlabel("Annual GHI (kWh/m²/year)")
ax.set_ylabel("GHI-weighted air temperature (°C)")
ax.set_title("Experimental PV clusters · six CRU/ERA5 cells")
ax.legend()
plt.show()
