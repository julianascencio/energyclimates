"""
Export a reproducible study
===================================

Run all three experimental profiles, write a temporary study and inspect its
manifest. The synthetic source flag survives the complete input → method →
analysis workflow. Use a permanent output directory in your own application.
"""

import json
from pathlib import Path
from tempfile import TemporaryDirectory

import matplotlib.pyplot as plt

from energyclimates.analysis import run_classification
from energyclimates.inputs import example_climate

study = run_classification(example_climate())
with TemporaryDirectory() as folder:
    study.write(folder)
    manifest = json.loads((Path(folder) / "manifest.json").read_text())
    print(
        json.dumps(
            {
                "version": manifest["package_version"],
                "technologies": manifest["technologies"],
                "input": manifest["input"]["metadata"],
            },
            indent=2,
        )
    )
    print("Outputs:", sorted(p.name for p in Path(folder).iterdir()))
counts = study.classifications.groupby("technology").size()
fig, ax = plt.subplots(figsize=(6, 3), layout="constrained")
ax.bar(counts.index, counts.values, color="#15616d")
ax.set_ylabel("Classified synthetic locations")
ax.set_ylim(0, 5)
ax.set_title("One study · three experimental profiles")
plt.show()
