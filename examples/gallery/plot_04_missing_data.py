"""
Keep missing evidence visible
=====================================

Remove one GHI month. PV and hybrid profiles for that location become unclassified,
while the battery profile remains available from its complete temperature data.
No interpolation or infilling occurs.
"""

import matplotlib.pyplot as plt
import numpy as np

from energyclimates.analysis import run_classification
from energyclimates.inputs import example_climate

cube = example_climate()
cube.values["ghi"][3, 0] = np.nan
study = run_classification(cube)
print(
    study.classifications[["location_id", "technology", "status", "reason"]].to_string(index=False)
)
status = study.classifications.assign(classified=lambda x: x.zone_id > 0).pivot(
    index="location_id", columns="technology", values="classified"
)
fig, ax = plt.subplots(figsize=(6, 3), layout="constrained")
ax.imshow(status.to_numpy(int), vmin=0, vmax=1, cmap="BrBG")
ax.set_xticks(range(len(status.columns)), status.columns)
ax.set_yticks(range(len(status.index)), status.index)
for i in range(len(status.index)):
    for j in range(len(status.columns)):
        ax.text(
            j,
            i,
            "available" if status.iloc[i, j] else "missing",
            ha="center",
            va="center",
            color="white",
        )
ax.set_title("Synthetic example · missing GHI stays missing")
plt.show()
