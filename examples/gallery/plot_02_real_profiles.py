"""
Classify six real climate grid cells
============================================

Use the repository's CRU/ERA5 monthly sample for 1996–2022. These are grid-cell
climatologies, not station observations. Profiles are experimental screening
labels. The sample has no precipitation, so this example does not run KGPV.
"""

from pathlib import Path

import matplotlib.pyplot as plt

from energyclimates.analysis import run_classification

# Gallery/notebooks run without __file__; direct scripts can run from any directory.
start = Path(__file__).resolve().parent if "__file__" in globals() else Path.cwd()
root = next(p for p in (start, *start.parents) if (p / "examples/monthly-climate.csv").is_file())
study = run_classification(
    root / "examples/monthly-climate.csv", root / "examples/monthly-mapping.json"
)
print(study.classifications[["location_id", "technology", "zone_name"]].to_string(index=False))
f = study.features
fig, ax = plt.subplots(figsize=(8, 4), layout="constrained")
ax.barh(f.location_id, f.ghi_annual_kwh_m2, color="#15616d")
ax.set_xlabel("Annual GHI (kWh/m²/year)")
ax.set_title("Six CRU/ERA5 cells · 1996–2022")
plt.show()
