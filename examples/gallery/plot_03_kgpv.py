"""
Apply the published KGPV method
=======================================

KGPV additionally needs monthly precipitation. Use synthetic inputs to demonstrate
the separate published-method API; this is not a map of observed climate zones.
"""

import matplotlib.pyplot as plt

from energyclimates.inputs import example_climate
from energyclimates.methods import classify_kgpv

cube = example_climate()
zones = classify_kgpv(cube)
print(zones[["location_id", "zone_name", "source_code", "status"]].to_string(index=False))
fig, ax = plt.subplots(figsize=(9, 3), layout="constrained")
ax.axis("off")
table = ax.table(
    cellText=zones[["location_id", "zone_name", "source_code"]].values,
    colLabels=["Synthetic site", "KGPV name", "Source code"],
    loc="center",
    colWidths=[0.2, 0.55, 0.2],
)
table.auto_set_font_size(False)
table.set_fontsize(10)
table.scale(1, 1.8)
ax.set_title("Published KGPV method · synthetic inputs")
plt.show()
