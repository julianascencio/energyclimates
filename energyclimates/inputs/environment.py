"""Local environmental inputs with explicit units and source metadata.

Use ``scripts/build_environment_inputs.py`` for the optional public downloads.
Imports and gallery execution never contact a provider.
"""

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd


def read_environment(path):
    """Read a Parquet snapshot and verify its adjacent ``.metadata.json`` hash.

    Returns a DataFrame with provenance in ``attrs``. Coordinates are WGS84
    degrees. Monthly array columns are January–December, with NaN for missing.
    Event snapshots retain individual reports, dates and original event IDs.
    """
    path = Path(path)
    metadata = json.loads(path.with_suffix(".metadata.json").read_text())
    actual = hashlib.sha256(path.read_bytes()).hexdigest()
    if metadata["sha256"] != actual:
        raise ValueError("Environmental input checksum does not match metadata")
    frame = pd.read_parquet(path)
    validate_coordinates(frame)
    frame.attrs = metadata
    return frame


def validate_coordinates(frame):
    """Reject missing or out-of-range geographic coordinates; do not relocate them."""
    for column, lower, upper in [("latitude", -90, 90), ("longitude", -180, 180)]:
        values = frame[column].to_numpy(dtype=float)
        if not np.isfinite(values).all() or not ((values >= lower) & (values <= upper)).all():
            raise ValueError(f"{column} must contain finite geographic coordinates")
