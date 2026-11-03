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


def storm_events(frame):
    """Normalize NOAA Storm Events details columns to report-level inputs.

    Select Hail, Thunderstorm Wind and Lightning. Missing coordinates/dates and
    zero/zero sentinel positions are excluded and counted in ``attrs``. NOAA hail
    magnitude is inches, converted to mm; wind magnitude is deliberately not
    interpreted as hail size. Duplicate event IDs are rejected, not double counted.
    Local event dates come from BEGIN_YEARMONTH and BEGIN_DAY (not UTC dates).
    """
    selected = frame[frame.EVENT_TYPE.isin(["Hail", "Thunderstorm Wind", "Lightning"])].copy()
    if selected.EVENT_ID.isna().any() or selected.EVENT_ID.duplicated().any():
        raise ValueError("Storm event IDs must be present and unique")
    date = pd.to_datetime(
        selected.BEGIN_YEARMONTH.astype(str) + selected.BEGIN_DAY.astype(str).str.zfill(2),
        format="%Y%m%d",
        errors="coerce",
    )
    lat = pd.to_numeric(selected.BEGIN_LAT, errors="coerce")
    lon = pd.to_numeric(selected.BEGIN_LON, errors="coerce")
    valid = lat.between(-90, 90) & lon.between(-180, 180) & date.notna()
    valid &= ~((lat == 0) & (lon == 0))
    magnitude = pd.to_numeric(selected.MAGNITUDE, errors="coerce")
    result = (
        pd.DataFrame(
            {
                "event_id": selected.EVENT_ID,
                "event_type": selected.EVENT_TYPE,
                "date": date.dt.strftime("%Y-%m-%d"),
                "latitude": lat,
                "longitude": lon,
                "hail_diameter_mm": magnitude.where(
                    selected.EVENT_TYPE.eq("Hail") & magnitude.gt(0)
                )
                * 25.4,
            }
        )
        .loc[valid]
        .reset_index(drop=True)
    )
    result.attrs = {
        "selected_reports": len(selected),
        "excluded_invalid_reports": int((~valid).sum()),
    }
    return result
