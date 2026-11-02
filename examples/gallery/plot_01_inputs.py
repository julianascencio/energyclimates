"""
Inspect monthly climate inputs
======================================

Create the synthetic example available in an installed wheel. Inspect temperature
and irradiation separately before computing a classification. The coordinates
and weather values are illustrative, not measurements.
"""

import matplotlib.pyplot as plt
import numpy as np

from energyclimates.inputs import example_climate

cube = example_climate()
fig, axes = plt.subplots(1, 2, figsize=(10, 4), layout="constrained")
for i, name in enumerate(cube.ids):
    axes[0].plot(np.arange(1, 13), cube.values["temperature"][:, i], label=name)
    axes[1].plot(np.arange(1, 13), cube.values["ghi"][:, i], label=name)
for ax in axes:
    ax.set_xlabel("Month")
    ax.set_xticks([1, 4, 7, 10, 12])
    ax.grid(alpha=0.2)
axes[0].set_ylabel("Monthly mean air temperature (°C)")
axes[1].set_ylabel("Monthly GHI (kWh/m²)")
axes[1].legend()
fig.suptitle("Synthetic climate inputs")
plt.show()
