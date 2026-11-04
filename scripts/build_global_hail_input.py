"""Rebuild the global 2015 hail snapshot from one pinned PANGAEA V2 file.

Explicit download: about 460 MB; allow 1 GB free cache space. Gallery is offline.
Daily chunks bound memory use. No multiyear climatology is claimed.
"""

import argparse
from pathlib import Path

import numpy as np
import pandas as pd
import xarray as xr
from build_environment_inputs import download, save

URL = (
    "https://hs.pangaea.de/model/Prein-Holland_2018/V2/2015_HailProbabilities_ERA-Interim_daily.nc"
)
SHA256 = "b80be54f3e3d5c912f53febfb5341337abc7cafd9a237c71322fea25bf0fbb08"


def sum_daily_probabilities(values):
    """Sum daily fractions without dropping NaNs or converting fractions to percent."""
    values = np.asarray(values, dtype=float)
    finite = values[np.isfinite(values)]
    if values.ndim != 3 or np.isinf(values).any() or ((finite < 0) | (finite > 1)).any():
        raise ValueError("Expected daily probability fractions in [0, 1]")
    return np.sum(values, axis=0)


def build(path, output):
    source = download(URL, path)
    if source["sha256"] != SHA256:
        raise ValueError("Provider checksum changed; review source revision")
    with xr.open_dataset(path) as dataset:
        np.testing.assert_array_equal(
            dataset.time.values.astype("datetime64[D]"),
            pd.date_range("2015-01-01", "2015-12-31").values.astype("datetime64[D]"),
        )
        lat = dataset.lat.values[:, 0].astype(float)
        lon = dataset.lon.values[0, :].astype(float)
        np.testing.assert_allclose(dataset.lat.values, np.broadcast_to(lat[:, None], (256, 512)))
        np.testing.assert_allclose(dataset.lon.values, np.broadcast_to(lon[None, :], (256, 512)))
        total = np.zeros((256, 512), dtype=float)
        for day in range(365):
            total += sum_daily_probabilities(dataset.HailProb.isel(time=slice(day, day + 1)).values)
    # Preserve native Gaussian latitudes and exact source longitude centres.
    order = np.argsort(lon)
    lon = lon[order]
    total = total[:, order]
    xx, yy = np.meshgrid(lon, lat)
    frame = pd.DataFrame(
        {
            "latitude": yy.ravel(),
            "longitude": xx.ravel(),
            "sum_daily_hail_probability": total.ravel(),
        }
    )
    metadata = {
        "title": "Global modeled large-hail daily probability sum, 2015",
        "period": "2015-01-01/2015-12-31",
        "sources": [source],
        "citation": "Prein and Holland (2018), PANGAEA V2, doi:10.1594/PANGAEA.893160; doi:10.1016/j.wace.2018.10.004",
        "license": "CC BY 3.0",
        "license_url": "https://creativecommons.org/licenses/by/3.0/",
        "units": {
            "sum_daily_hail_probability": "sum of daily probability fractions (day equivalents)"
        },
        "processing": "Sum all 365 daily HailProb fields in float64, retaining NaNs. Sort native longitudes; no resampling. V2 DOI defines values as 0..1 fractions despite NetCDF percent attribute; no division by 100.",
        "missing_data": "Every daily value required; NaN propagates; source zeros retained.",
        "limitations": "Single modeled year, not climatology or observations. Environmental proxy for hail >2.5 cm; not annual probability, return period, hail size or PV damage. Geographic calibration limits apply.",
        "grid": {
            "type": "rectilinear",
            "latitude": lat.tolist(),
            "longitude": lon.tolist(),
            "bounds": [-180, 180, -90, 90],
        },
    }
    output.mkdir(parents=True, exist_ok=True)
    save(output, "global-hail-2015", frame, metadata)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=Path("raw/global-hail/2015.nc"))
    parser.add_argument("--output", type=Path, default=Path("examples/environment"))
    args = parser.parse_args()
    args.source.parent.mkdir(parents=True, exist_ok=True)
    build(args.source, args.output)
