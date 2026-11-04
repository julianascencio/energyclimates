"""Explicitly rebuild the offline global lightning snapshot (about 26 MB download)."""

import argparse
from pathlib import Path

import numpy as np
import xarray as xr
from build_environment_inputs import download, monthly_table, save

URL = "https://zenodo.org/api/records/6007052/files/wglc_climatology_30m.nc/content"


def coarsen_density(values, latitude):
    """Area-weighted 2×2 mean on a regular geographic grid; require all cells.

    Spherical cell areas are proportional to cos(latitude) on this grid.
    Missing source cells invalidate the corresponding coarse cell.
    """
    values = np.asarray(values, dtype=float)
    latitude = np.asarray(latitude, dtype=float)
    if values.shape[-2:] != (len(latitude), 2 * len(latitude)) or len(latitude) % 2:
        raise ValueError("Expected an even, global 2:1 longitude/latitude grid")
    if np.isinf(values).any() or (values[np.isfinite(values)] < 0).any():
        raise ValueError("Invalid lightning density")
    weights = np.cos(np.deg2rad(latitude)).reshape(-1, 2)
    cells = values.reshape(*values.shape[:-2], len(latitude) // 2, 2, -1, 2)
    return (cells * weights[..., None, None]).sum(axis=(-1, -3)) / (
        2 * weights.sum(axis=1)[:, None]
    )


def build(cache, output):
    path = cache / "wglc_climatology_30m.nc"
    source = download(URL, path)
    if source["sha256"] != "b5f36f097b659025f4b5e483093e60b99d6d66286da8823778fffbff3ad0fc92":
        raise ValueError("Provider checksum changed; review the new revision")
    with xr.open_dataset(path) as dataset:
        if "2012-2021" not in dataset.attrs.get("title", ""):
            raise ValueError("Unexpected climatology period")
        if dataset.density.attrs.get("units") != "strokes km-2 d-1":
            raise ValueError("Unexpected provider density units")
        if dataset.sizes["time"] != 12:
            raise ValueError("Expected twelve climatological months")
        np.testing.assert_array_equal(dataset.time.dt.month.values, np.arange(1, 13))
        lat, lon = dataset.lat.values, dataset.lon.values
        np.testing.assert_allclose(lat, np.arange(-89.75, 90, 0.5))
        np.testing.assert_allclose(lon, np.arange(-179.75, 180, 0.5))
        months = coarsen_density(dataset.density.values, lat)
        frame = monthly_table(
            lat.reshape(-1, 2).mean(axis=1),
            lon.reshape(-1, 2).mean(axis=1),
            lightning_strokes_km2_day_months=months,
        )
    metadata = {
        "title": "WGLC global monthly lightning stroke density, 2012–2021",
        "period": "2012-01-01/2021-12-31",
        "sources": [source],
        "citation": "Kaplan and Lau (2021, 2022); WGLC 2022 release, doi:10.5281/zenodo.6007052",
        "license": "CC BY-SA 4.0, following the provider LICENSE; applies to this derived snapshot and its data products.",
        "license_url": "https://creativecommons.org/licenses/by-sa/4.0/",
        "units": {"lightning_strokes_km2_day_months": "strokes/km²/day, January–December"},
        "processing": "Provider monthly daily-density climatology for 2012–2021; 2×2 spherical-area-weighted means of native 0.5° cells to 1°; no interpolation.",
        "missing_data": "All twelve climatological months and all four spatial cells required; NaN stays missing; source zeros retained.",
        "limitations": "Detection-efficiency-corrected WWLLN strokes, not flashes, thunderstorm counts or wind reports. Detection varies geographically and through time; weak strokes can be missed.",
        "grid": {"type": "regular", "resolution_degrees": 1, "bounds": [-180, 180, -90, 90]},
    }
    save(output, "global-lightning-2012-2021", frame, metadata)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache", type=Path, default=Path("raw/global-lightning"))
    parser.add_argument("--output", type=Path, default=Path("examples/environment"))
    args = parser.parse_args()
    args.cache.mkdir(parents=True, exist_ok=True)
    args.output.mkdir(parents=True, exist_ok=True)
    build(args.cache, args.output)
