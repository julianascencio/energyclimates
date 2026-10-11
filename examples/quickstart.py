"""Run from the repository root after: python -m pip install -e ."""
from pathlib import Path
from energyclimates import load_dataset, extract_features, classify_features
from energyclimates.ml import load_model, predict_clusters

root = Path(__file__).resolve().parents[1]
cube = load_dataset(root / "examples/monthly-climate.csv", root / "examples/monthly-mapping.json")
features = extract_features(cube)
for technology in ("pv", "hybrid", "bess"):
    print(f"\n{technology.upper()} · experimental profiles")
    print(classify_features(features, technology)[["location_id", "zone_name"]].to_string(index=False))
model = load_model(root / "atlas/models/pv.json")
print("\nPV · independent experimental ML groups")
print(predict_clusters(features, model)[["location_id", "zone_name", "status"]].to_string(index=False))
