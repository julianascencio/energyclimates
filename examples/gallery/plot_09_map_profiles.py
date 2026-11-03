"""
Recompute global PV, hybrid and BESS profile maps
=================================================

Apply the existing versioned rules to every bundled global feature row. This
example recomputes the classifications instead of displaying cached map images.
Colours and names are taken from the existing atlas catalogue, so the gallery
and interactive atlas use the same category identity.

All three classifications are experimental climate screening. They do not
predict yield, storage size, battery lifetime or economic performance. ID 0 is
unclassified; missing cells stay grey. The three output CSVs include the rule
version, category name, status and reasons. See :doc:`/map-examples` for export.
"""

import json
from pathlib import Path

import matplotlib.pyplot as plt

from energyclimates.analysis.maps import plot_category_map
from energyclimates.methods import class_labels, classify_features, load_rules
from kgpv.engine.results import read_features

start = Path(__file__).resolve().parent if "__file__" in globals() else Path.cwd()
root = next(
    p for p in (start, *start.parents) if (p / "examples/global-climate-features.parquet").is_file()
)
input_files = [
    root / "examples/global-climate-features.parquet",
    root / "examples/global-climate-features.metadata.json",
    root / "kgpv/engine/rules-v1.json",
    root / "atlas/data/catalog.json",
]
features = read_features(input_files[0])
rules = load_rules(input_files[2])
layers = {layer["id"]: layer for layer in json.loads(input_files[3].read_text())["layers"]}
fig, axes = plt.subplots(3, 1, figsize=(15, 13), layout="constrained")
fig.get_layout_engine().set(h_pad=0.14, hspace=0.08)
result_tables = {}
for ax, technology, title in zip(
    axes, ["pv", "hybrid", "bess"], ["Solar PV", "PV + battery", "Battery storage"]
):
    profiles = classify_features(features, technology, rules)
    result_tables[technology] = profiles
    plot_category_map(
        profiles,
        labels=class_labels(technology, rules),
        colors=layers[f"energy-{technology}"]["colors"],
        ax=ax,
        title=title,
    )
    print(f"{title}: {len(profiles):,} cells, {(profiles.zone_id == 0).sum():,} unclassified")
    print(profiles.zone_name.value_counts().to_string())
fig.suptitle(
    "Experimental energy climate profiles\nCRU TS 4.10 + ERA5 · 1996–2022 · 0.5° cells", fontsize=15
)
map_context = {"method": "Experimental rules", "rules": rules}
plt.show()
