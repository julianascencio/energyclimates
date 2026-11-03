"""Explicitly download public inputs and build compact offline environmental snapshots.

Run from an installed checkout. Selected inputs are cached under raw/environment.
Provider revisions may change: inspect resulting metadata and diffs before use.
Gallery/docs builds never invoke this script.
"""

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import requests
import xarray as xr

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from energyclimates.inputs.environment import storm_events

GMI = "https://opendap.nccs.nasa.gov/dods/merra2_gmi/"
NOAA = "https://www.ncei.noaa.gov/pub/data/swdi/stormevents/csvfiles/"
SNOW = (
    "https://downloads.psl.noaa.gov/Datasets/ncep.reanalysis.derived/"
    "surface_gauss/weasd.sfc.mon.1981-2010.ltm.nc"
)
LAND = "https://downloads.psl.noaa.gov/Datasets/ncep.reanalysis/surface_gauss/land.sfc.gauss.nc"
STORM_FILES = [
    "StormEvents_details-ftp_v1.0_d2020_c20260323.csv.gz",
    "StormEvents_details-ftp_v1.0_d2021_c20260323.csv.gz",
    "StormEvents_details-ftp_v1.0_d2022_c20260625.csv.gz",
    "StormEvents_details-ftp_v1.0_d2023_c20260323.csv.gz",
    "StormEvents_details-ftp_v1.0_d2024_c20260728.csv.gz",
]


def checksum(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def download(url, path):
    if not path.exists():
        temporary = path.with_suffix(path.suffix + ".part")
        with requests.get(url, stream=True, timeout=(15, 120)) as response:
            response.raise_for_status()
            with temporary.open("wb") as output:
                for block in response.iter_content(1024 * 1024):
                    output.write(block)
        temporary.replace(path)
    return {"url": url, "sha256": checksum(path), "bytes": path.stat().st_size}


def ascii_grid(text, variable):
    """Read one bounded GDS ASCII response, validating every row and coordinate."""
    match = re.search(rf"(?m)^{re.escape(variable)}, \[(\d+)\]\[(\d+)\]\[(\d+)\]\n", text)
    if match is None:
        raise ValueError(f"Missing GDS grid {variable}")
    nt, ny, nx = map(int, match.groups())
    section = text[match.end() :].split("\ntime,", 1)[0]
    grid = np.full((nt, ny, nx), np.nan)
    seen = set()
    for t, y, values in re.findall(r"(?m)^\[(\d+)\]\[(\d+)\], (.+)$", section):
        key = int(t), int(y)
        row = np.fromstring(values, sep=",")
        if key in seen or key[0] >= nt or key[1] >= ny or row.size != nx:
            raise ValueError("Invalid GDS row")
        seen.add(key)
        grid[key] = row
    if len(seen) != nt * ny:
        raise ValueError("Incomplete GDS grid")
    axes = {}
    for name, size in [("time", nt), ("lat", ny), ("lon", nx)]:
        coordinate = re.search(rf"(?m)^{name}, \[{size}\]\n([^\n]+)", text[match.end() :])
        if coordinate is None:
            raise ValueError(f"Missing GDS {name}")
        axes[name] = np.fromstring(coordinate[1], sep=",")
        if axes[name].size != size or not np.isfinite(axes[name]).all():
            raise ValueError("Invalid GDS coordinates")
    grid[abs(grid) >= 1e14] = np.nan
    return grid, axes


def monthly_table(lat, lon, **variables):
    yy, xx = np.meshgrid(lat, lon, indexing="ij")
    frame = pd.DataFrame({"latitude": yy.ravel(), "longitude": xx.ravel()})
    for name, values in variables.items():
        frame[name] = list(values.reshape(12, -1).T)
    return frame


def save(folder, name, frame, metadata):
    path = folder / f"{name}.parquet"
    frame.attrs = {}
    frame.to_parquet(path, index=False)
    metadata.update(
        schema="energyclimates-environment-input-v1", sha256=checksum(path), rows=len(frame)
    )
    path.with_suffix(".metadata.json").write_text(json.dumps(metadata, indent=2, allow_nan=False))
    print(f"{name}: {len(frame):,} rows, {path.stat().st_size:,} bytes", flush=True)


def build_gmi(cache, output):
    """Build the gmi snapshot from cached or downloaded provider files."""
    sources = []
    grids = {}
    reference_axes = None
    for name, dataset, variables in [
        ("dust", "tavgM_2d_aer_Nx", ["dusmass"]),
        ("lai", "tavgM_2d_lnd_Nx", ["lai", "grn"]),
    ]:
        query = ",".join(v + "[468:479][2:4:358][2:4:574]" for v in variables)
        path = cache / f"gmi-{name}.ascii"
        sources.append(download(GMI + dataset + ".ascii?" + query, path))
        meta = cache / (dataset + ".das")
        sources.append(download(GMI + dataset + ".das", meta))
        declarations = meta.read_text()
        expected = {"dusmass": "kg m-3", "lai": "1", "grn": "1"}
        for variable in variables:
            pattern = rf"\b{variable} \{{\s+String units \"{expected[variable]}\";"
            if re.search(pattern, declarations) is None:
                raise ValueError(f"Unexpected units for {variable}")
        text = path.read_text()
        for variable in variables:
            values, axes = ascii_grid(text, variable)
            if reference_axes is not None and any(
                not np.array_equal(axes[key], reference_axes[key]) for key in axes
            ):
                raise ValueError("GMI variables have mismatched axes")
            reference_axes = axes
            grids[variable] = values
        dates = xr.coding.times.decode_cf_datetime(
            axes["time"], "days since 0001-01-01", use_cftime=True
        )
        if [(d.year, d.month) for d in dates] != [(2019, m) for m in range(1, 13)]:
            raise ValueError("GMI selection is not January–December 2019")
    frame = monthly_table(
        axes["lat"], axes["lon"], dust_ug_m3_months=grids["dusmass"] * 1e9, lai_months=grids["lai"]
    )
    land = np.isfinite(grids["lai"]).any(axis=0).ravel()
    save(
        output,
        "gmi-2019",
        frame.loc[land].reset_index(drop=True),
        {
            "provider": "NASA GSFC / NCCS MERRA-2 GMI replay simulation",
            "period": "2019",
            "sources": sources,
            "reference": "https://acd-ext.gsfc.nasa.gov/Projects/GEOSCCM/MERRA2GMI/",
            "units": {"dust_ug_m3_months": "µg/m³", "lai_months": "m² leaf/m² ground"},
            "grid": {
                "crs": "EPSG:4326",
                "latitude": axes["lat"].tolist(),
                "longitude": axes["lon"].tolist(),
                "native_spacing_degrees": [0.5, 0.625],
                "sample_spacing_degrees": [2.0, 2.5],
            },
            "processing": "Jan–Dec; every fourth native centre (not block averages); kg/m³ × 1e9; "
            "retain cells with any valid model LAI; preserve monthly missing values.",
            "limitations": "Single model year; aerosols are not constrained by observed AOD in GMI. "
            "Sampling may omit local extremes; no measured soiling or land-cover class.",
        },
    )


def build_snow(cache, output):
    """Build the snow snapshot from cached or downloaded provider files."""
    path = cache / "snow-1981-2010.nc"
    source = download(SNOW, path)
    land_path = cache / "land.sfc.gauss.nc"
    land_source = download(LAND, land_path)
    with xr.open_dataset(land_path, decode_times=False) as land_ds:
        land_mask = land_ds.land.values[0] == 1
        land_lat, land_lon = land_ds.lat.values, land_ds.lon.values
    with xr.open_dataset(path, decode_times=False) as ds:
        if not (np.array_equal(ds.lat, land_lat) and np.array_equal(ds.lon, land_lon)):
            raise ValueError("NCEP land mask and snow grid do not align")
        if ds.weasd.attrs["units"] != "kg/m^2" or ds.weasd.shape != (12, 94, 192):
            raise ValueError("Unexpected NCEP snow contract")
        snow = ds.weasd.values.copy()
        snow[ds.valid_yr_count.values < 30] = np.nan
        lon = (ds.lon.values.astype(float) + 180) % 360 - 180
        lat = ds.lat.values.astype(float)
    save(
        output,
        "snow-1981-2010",
        monthly_table(lat, lon, swe_mm_months=snow).loc[land_mask.ravel()].reset_index(drop=True),
        {
            "provider": "NOAA PSL NCEP/NCAR Reanalysis 1",
            "period": "1981–2010 climatology",
            "sources": [source, land_source],
            "units": {"swe_mm_months": "mm water equivalent"},
            "grid": {
                "crs": "EPSG:4326",
                "latitude": sorted(lat.tolist()),
                "longitude": sorted(lon.tolist()),
                "native_grid": "94 × 192 Gaussian",
            },
            "processing": "1 kg/m² SWE = 1 mm water; retain only months with all 30 years; "
            "wrap longitude without resampling; retain NCEP static land-mask cells only.",
            "limitations": "Coarse modeled ground SWE. Ice sheets may have very large values; "
            "ocean/sea-ice cells excluded by the native static land mask. "
            "No module snow, daily cover or PV loss.",
        },
    )


def build_storms(cache, output):
    """Build the storms snapshot from cached or downloaded provider files."""
    frames, sources = [], []
    for name in STORM_FILES:
        path = cache / name
        sources.append(download(NOAA + name, path))
        frames.append(
            pd.read_csv(
                path,
                usecols=[
                    "EVENT_ID",
                    "EVENT_TYPE",
                    "BEGIN_YEARMONTH",
                    "BEGIN_DAY",
                    "BEGIN_LAT",
                    "BEGIN_LON",
                    "MAGNITUDE",
                ],
            )
        )
    events = storm_events(pd.concat(frames, ignore_index=True))
    filtering = events.attrs.copy()
    save(
        output,
        "storm-reports-2020-2024",
        events,
        {
            "provider": "NOAA NCEI Storm Events details",
            "period": "2020–2024 inclusive",
            "sources": sources,
            "filtering": filtering,
            "units": {"hail_diameter_mm": "mm", "date": "local event calendar date"},
            "grid": {"crs": "EPSG:4326", "input_geometry": "event BEGIN point"},
            "processing": "Select Hail, Thunderstorm Wind, Lightning; inches × 25.4; "
            "discard invalid dates/coordinates and 0,0 sentinels; unique event IDs.",
            "limitations": "U.S. report inventory, not uniform observation coverage. No report does "
            "not mean no hazard. Bias toward populated areas and significant events.",
        },
    )


BUILDERS = {"gmi": build_gmi, "snow": build_snow, "storms": build_storms}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache", type=Path, default=ROOT / "raw/environment")
    parser.add_argument("--output", type=Path, default=ROOT / "examples/environment")
    parser.add_argument(
        "--dataset",
        choices=["all", *BUILDERS],
        default="all",
        help="Refresh one source independently, or all available sources",
    )
    args = parser.parse_args()
    args.cache.mkdir(parents=True, exist_ok=True)
    args.output.mkdir(parents=True, exist_ok=True)
    selected = BUILDERS if args.dataset == "all" else [args.dataset]
    for name in selected:
        BUILDERS[name](args.cache, args.output)


if __name__ == "__main__":
    main()
