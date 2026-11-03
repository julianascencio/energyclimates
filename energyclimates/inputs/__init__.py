"""Input contracts, local-file adapters and explicit provider downloads.

Adapters normalize declared units and calendars into twelve monthly values.
Provider functions perform network I/O only when explicitly called.
"""

import numpy as np

from kgpv.engine.adapters import load_dataset, table_cube
from kgpv.engine.features import ClimateCube
from kgpv.sources import fetch_baseline, fetch_climate, fetch_era5_cds, fetch_era5_ncar

__all__ = [
    "ClimateCube",
    "example_climate",
    "fetch_baseline",
    "fetch_climate",
    "fetch_era5_cds",
    "fetch_era5_ncar",
    "load_dataset",
    "table_cube",
]


def example_climate() -> ClimateCube:
    """Return four deterministic synthetic locations, without files or network.

    Temperature is monthly mean air temperature in degrees Celsius; GHI is
    monthly energy in kWh/m²; precipitation is monthly total in millimetres.
    Coordinates are illustrative. These values are not measured climatologies.
    Each call returns independent arrays suitable for missing-data experiments.
    """
    season = np.cos(2 * np.pi * (np.arange(12) - 6) / 12)[:, None]
    return ClimateCube(
        ids=np.array(["mild", "cold", "hot", "seasonal"]),
        latitude=np.array([28.0, 60.0, 20.0, 45.0]),
        longitude=np.array([-16.0, 10.0, 30.0, 0.0]),
        values={
            "temperature": np.array([20.0, 5.0, 29.0, 14.0])
            + season * np.array([3.0, 16.0, 7.0, 14.0]),
            "ghi": np.array([170.0, 85.0, 200.0, 125.0])
            + season * np.array([25.0, 75.0, 30.0, 100.0]),
            "precipitation": np.broadcast_to([30.0, 60.0, 5.0, 70.0], (12, 4)).copy(),
        },
        period="Synthetic representative year (365 days)",
        metadata={"synthetic": True, "generator": "energyclimates.inputs.example_climate/v1"},
    )
