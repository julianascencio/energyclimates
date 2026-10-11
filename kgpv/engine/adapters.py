"""Explicit column/variable and unit mapping for CSV, Parquet, NetCDF, Zarr, GeoTIFF.

A provider may use any names. It must supply the variables required by the chosen
scheme. No units, time semantics or missing observations are guessed.
"""

import calendar
import hashlib
import json
from pathlib import Path
import numpy as np
import pandas as pd
from .features import ClimateCube, DAYS

FIELDS = {"temperature", "ghi", "precipitation", "relative_humidity", "wind_speed"}
SUM_FIELDS = {"ghi", "precipitation"}


def convert(a, field, unit, hours):
    """Convert to C, interval kWh/m², interval mm, %, or m/s.

    hours is the interval duration; ERA5 monthly mean daily J/m² must explicitly
    use J/m2/day, not J/m2. Arithmetic also supports lazy xarray objects.
    """
    u = unit.strip().lower().replace("²", "2").replace("°", "").replace(" ", "")
    if field == "temperature":
        if u in ["c", "degc", "celsius"]:
            return a
        if u in ["k", "kelvin"]:
            return a - 273.15
        if u in ["f", "degf", "fahrenheit"]:
            return (a - 32) * 5 / 9
    elif field == "ghi":
        if u in ["kwh/m2", "kwh/m2/interval", "kwh/m2/month"]:
            return a
        if u == "wh/m2":
            return a / 1000
        if u in ["j/m2", "j/m2/interval"]:
            return a / 3_600_000
        if u == "w/m2":
            return a * hours / 1000
        if u == "kwh/m2/day":
            return a * hours / 24
        if u == "j/m2/day":
            return a * hours / 24 / 3_600_000
    elif field == "precipitation":
        if u in ["mm", "mm/month", "kg/m2"]:
            return a
        if u == "m":
            return a * 1000
        if u == "mm/day":
            return a * hours / 24
        if u == "mm/hour":
            return a * hours
        if u == "kg/m2/s":
            return a * hours * 3600
    elif field == "relative_humidity":
        if u in ["%", "percent"]:
            return a
        if u in ["fraction", "1"]:
            return a * 100
    elif field == "wind_speed":
        if u in ["m/s", "ms-1"]:
            return a
        if u == "km/h":
            return a / 3.6
    raise ValueError(f"Unsupported unit {unit!r} for {field}; specify its meaning in the mapping")


def physical_mask(a, field):
    if field == "temperature":
        return (a >= -100) & (a <= 70)
    if field == "relative_humidity":
        return (a >= 0) & (a <= 100)
    return a >= 0


def configuration(config):
    if isinstance(config, (str, Path)):
        config = json.loads(Path(config).read_text())
    if not isinstance(config, dict) or not config.get("variables"):
        raise ValueError("A mapping with variables and units is required")
    if config.get("frequency") not in ["climatology", "monthly", "daily", "hourly"]:
        raise ValueError("frequency must be climatology, monthly, daily or hourly")
    for key, spec in config["variables"].items():
        if key not in FIELDS:
            raise ValueError(f"Unknown canonical variable: {key}")
        if not spec.get("unit"):
            raise ValueError(f"An explicit unit is required for {key}")
    return config


def source_metadata(path, config):
    p = Path(path)
    # Large source files are hashed in bounded blocks.
    sha = None
    if p.is_dir():
        entries = [source_metadata(child, {}) for child in sorted(p.rglob("*")) if child.is_file()]
        manifest = [
            {"path": str(child.relative_to(p)), "sha256": entry["sha256"]}
            for child, entry in zip([x for x in sorted(p.rglob("*")) if x.is_file()], entries)
        ]
        return {
            "source_file": p.name,
            "files": manifest,
            "sha256": hashlib.sha256(json.dumps(manifest, sort_keys=True).encode()).hexdigest(),
            "mapping": config,
        }
    if p.is_file():
        d = hashlib.sha256()
        with p.open("rb") as f:
            for b in iter(lambda: f.read(4 * 1024 * 1024), b""):
                d.update(b)
        sha = d.hexdigest()
    return {
        "source_file": p.name,
        "sha256": sha,
        "mapping": config,
        "missing_policy": "Every required month and observation must exist; no infilling",
        "period_note": config.get("period", ""),
    }


def table_cube(frame, config):
    c = configuration(config)
    coords = c.get("coordinates", {})
    f = frame.copy()
    get = lambda k, default: coords.get(k, default)
    lat, lon = get("latitude", "latitude"), get("longitude", "longitude")
    for key in [lat, lon]:
        if key not in f:
            raise ValueError(f"Missing coordinate column: {key}")
        f[key] = pd.to_numeric(f[key], errors="raise")
    if not np.isfinite(f[[lat, lon]].to_numpy(float)).all():
        raise ValueError("Coordinates cannot be missing")
    if (f[lat].abs() > 90).any() or (f[lon].abs() > 360).any():
        raise ValueError("Coordinates outside supported geographic ranges")
    f[lon] = (f[lon] + 180) % 360 - 180
    idcol = get("id", "location_id")
    if idcol not in f:
        f[idcol] = f[lat].astype(str) + "," + f[lon].astype(str)
    if f[idcol].isna().any():
        raise ValueError("Location ID is missing")
    f[idcol] = f[idcol].astype(str)
    if f.groupby(idcol)[[lat, lon]].nunique().gt(1).any().any():
        raise ValueError("One location ID has multiple coordinates; use unique fixed-location IDs")
    frequency = c["frequency"]
    clim = frequency == "climatology"
    if clim:
        monthcol = get("month", "month")
        if monthcol not in f:
            raise ValueError("A month column (1–12) is required")
        months = pd.to_numeric(f[monthcol], errors="raise")
        if not months.between(1, 12).all() or not (months == months.astype(int)).all():
            raise ValueError("Months must be integers 1–12")
        f["_month"] = months.astype(int)
        f["_year"] = 2001
        days = np.asarray(c.get("month_days", DAYS), float)
        if days.shape != (12,) or (days <= 0).any():
            raise ValueError("month_days must contain 12 positive values")
        f["_hours"] = days[f._month - 1] * 24
        years = [2001]
        if f.duplicated([idcol, "_month"]).any():
            raise ValueError("Duplicate location/month; use frequency monthly for multiple years")
    else:
        timecol = get("time", "time")
        if timecol not in f:
            raise ValueError("A time column is required")
        # UTC is the documented default; non-UTC naive inputs need an explicit timezone.
        times = pd.to_datetime(f[timecol], errors="raise", format="mixed")
        if times.dt.tz is None:
            times = times.dt.tz_localize(
                c.get("timezone", "UTC"), ambiguous="raise", nonexistent="raise"
            )
        times = times.dt.tz_convert("UTC")
        f["_time"] = times
        if frequency == "hourly" and ((times.dt.minute != 0) | (times.dt.second != 0)).any():
            raise ValueError("Hourly timestamps must lie on whole UTC hours")
        if frequency == "daily" and ((times.dt.hour != 0) | (times.dt.minute != 0)).any():
            raise ValueError("Daily timestamps must be at midnight UTC")
        f["_year"] = times.dt.year
        f["_month"] = times.dt.month
        start = int(c.get("start_year", f._year.min()))
        end = int(c.get("end_year", f._year.max()))
        if start > end:
            raise ValueError("start_year must not exceed end_year")
        years = list(range(start, end + 1))
        f = f[f._year.between(start, end)].copy()
        if f.empty:
            raise ValueError("No observations in the requested period")
        duplicate = [idcol, "_year", "_month"] if frequency == "monthly" else [idcol, "_time"]
        if f.duplicated(duplicate).any():
            raise ValueError("Duplicate observation intervals")
        f["_hours"] = (
            f._time.dt.days_in_month * 24
            if frequency == "monthly"
            else (24 if frequency == "daily" else 1)
        )
        days = np.array(
            [np.mean([calendar.monthrange(y, m)[1] for y in years]) for m in range(1, 13)]
        )
    locations = f.groupby(idcol, sort=True)[[lat, lon]].first()
    ids = locations.index.to_numpy(str)
    n = len(ids)
    values = {}
    group = [idcol, "_year", "_month"]
    for field, spec in c["variables"].items():
        name = spec.get("column", spec.get("name", field))
        if name not in f:
            raise ValueError(f"Missing variable column: {name}")
        numeric = pd.to_numeric(f[name], errors="raise").to_numpy(float)
        for sentinel in spec.get("missing_values", []):
            numeric[numeric == sentinel] = np.nan
        a = np.asarray(convert(numeric, field, spec["unit"], f._hours.to_numpy()), float)
        if np.isinf(a).any():
            raise ValueError(f"Infinite {field} values")
        if spec.get("clip_min") is not None:
            a = np.maximum(a, float(spec["clip_min"]))
        if (np.isfinite(a) & ~physical_mask(a, field)).any():
            raise ValueError(f"Out-of-range {field}; check units or declare source missing_values")
        temp = f[group].copy()
        temp["_v"] = a
        grouped = temp.groupby(group)._v
        aggregate = grouped.sum(min_count=1) if field in SUM_FIELDS else grouped.mean()
        count = grouped.count()
        idx = aggregate.index
        expected = (
            np.ones(len(idx))
            if frequency in ["monthly", "climatology"]
            else np.array(
                [
                    calendar.monthrange(int(y), int(m))[1] * (24 if frequency == "hourly" else 1)
                    for _, y, m in idx
                ]
            )
        )
        aggregate[count.to_numpy() != expected] = np.nan
        normals = aggregate.groupby(level=[0, 2]).mean()
        normal_count = aggregate.groupby(level=[0, 2]).count()
        normals[normal_count != len(years)] = np.nan
        wide = normals.unstack(level=1).reindex(index=ids, columns=range(1, 13))
        values[field] = wide.to_numpy(float).T
    period = c.get("period") or ("User-supplied climatology" if clim else f"{years[0]}–{years[-1]}")
    return ClimateCube(
        ids,
        locations[lat].to_numpy(),
        locations[lon].to_numpy(),
        values,
        days,
        period,
        {
            "mapping": c,
            "input_rows": len(frame),
            "calendar": "declared month_days" if clim else "Gregorian",
            "month_days": days.tolist(),
        },
    )


def netcdf_cube(path, c):
    import xarray as xr

    coord = c.get("coordinates", {})
    tn = coord.get("time", "time")
    yn = coord.get("latitude", "lat")
    xn = coord.get("longitude", "lon")
    ds = (
        xr.open_zarr(path, chunks="auto")
        if c.get("format") == "zarr"
        else xr.open_dataset(path, chunks={tn: c.get("time_chunk", 120)})
    )
    try:
        if c.get("select"):
            ds = ds.sel(c["select"])
        for key in [yn, xn]:
            if ds[key].ndim != 1:
                raise ValueError(
                    "NetCDF needs 1D geographic latitude/longitude axes; reproject curvilinear grids first"
                )
        ds = (
            ds.assign_coords({xn: (ds[xn] + 180) % 360 - 180})
            .sortby(xn)
            .sortby(yn, ascending=False)
        )
        if len(np.unique(ds[xn])) != len(ds[xn]):
            raise ValueError("Duplicate longitude after wrapping; remove cyclic endpoint")
        lat, lon = np.meshgrid(ds[yn].values, ds[xn].values, indexing="ij")
        values = {}
        frequency = c["frequency"]
        clim = frequency == "climatology"
        if clim:
            monthkey = coord.get("month", "month")
            if monthkey != tn:
                ds = ds.rename({monthkey: tn})
            months = ds[tn].values
            if len(np.unique(months)) != len(months) or not np.isin(months, np.arange(1, 13)).all():
                raise ValueError("Climatology axis must use unique months 1–12")
            ds = ds.reindex({tn: np.arange(1, 13)})
            days = np.asarray(c.get("month_days", DAYS), float)
            hours = xr.DataArray(days * 24, dims=[tn], coords={tn: ds[tn]})
            nyears = 1
            period = c.get("period", "User-supplied climatology")
        else:
            if tn != "time":
                ds = ds.rename({tn: "time"})
                tn = "time"
            if not ds.indexes[tn].is_unique:
                raise ValueError("Duplicate NetCDF timestamps")
            ds = ds.sortby(tn)
            start = int(c.get("start_year", ds[tn].dt.year.min()))
            end = int(c.get("end_year", ds[tn].dt.year.max()))
            if start > end:
                raise ValueError("Invalid year range")
            ds = ds.sel({tn: slice(str(start), str(end))})
            if ds.sizes[tn] == 0:
                raise ValueError("No observations in the requested period")
            months = ds[tn].dt.month.values
            years = ds[tn].dt.year.values
            if frequency == "monthly" and len(set(zip(years, months))) != len(months):
                raise ValueError("Duplicate NetCDF calendar month")
            if frequency == "hourly" and ((ds[tn].dt.minute != 0) | (ds[tn].dt.second != 0)).any():
                raise ValueError("Hourly data must be aligned to whole hours")
            if frequency == "daily" and ((ds[tn].dt.hour != 0) | (ds[tn].dt.minute != 0)).any():
                raise ValueError("Daily data must be midnight-labelled")
            hours = (
                ds[tn].dt.days_in_month * 24
                if frequency == "monthly"
                else (24 if frequency == "daily" else 1)
            )
            nyears = end - start + 1
            period = c.get("period", f"{start}–{end}")
            cal = ds[tn].dt.calendar
            monthly_index = xr.date_range(
                f"{start}-01-01",
                f"{end + 1}-01-01",
                freq="MS",
                inclusive="left",
                calendar=cal,
                use_cftime=(cal not in ["standard", "gregorian", "proleptic_gregorian"]),
            )
            month_axis = xr.DataArray(monthly_index, dims=["time"], coords={"time": monthly_index})
            days = month_axis.dt.days_in_month.groupby("time.month").mean().values
        for field, spec in c["variables"].items():
            v = ds[spec.get("name", field)]
            if set(v.dims) != {tn, yn, xn}:
                raise ValueError(
                    f"{field}: select extra dimensions; expected time, latitude, longitude"
                )
            for sentinel in spec.get("missing_values", []):
                v = v.where(v != sentinel)
            v = convert(v, field, spec["unit"], hours)
            if spec.get("clip_min") is not None:
                v = v.clip(min=float(spec["clip_min"]))
            v = v.where(physical_mask(v, field))
            if clim:
                normal = v.rename({tn: "month"}) if tn != "month" else v
            else:
                resampler = v.resample(time="MS")
                count = resampler.count()
                monthly = (
                    resampler.sum(skipna=False)
                    if field in SUM_FIELDS
                    else resampler.mean(skipna=False)
                )
                expected = (
                    1
                    if frequency == "monthly"
                    else monthly.time.dt.days_in_month * (24 if frequency == "hourly" else 1)
                )
                monthly = monthly.where(count == expected).reindex(time=monthly_index)
                normal = (
                    monthly.groupby("time.month").mean(skipna=False).reindex(month=np.arange(1, 13))
                )
            values[field] = normal.transpose("month", yn, xn).compute().values.reshape(12, -1)
        ids = np.array([f"{a:.8f},{b:.8f}" for a, b in zip(lat.ravel(), lon.ravel())])
        return ClimateCube(
            ids,
            lat.ravel(),
            lon.ravel(),
            values,
            days,
            period,
            {"grid_shape": lat.shape, "mapping": c, "calendar": "declared" if clim else cal},
        )
    finally:
        ds.close()


def geotiff_cube(path, c):
    import rasterio
    from rasterio.warp import calculate_default_transform, reproject, Resampling

    if c["frequency"] != "climatology":
        raise ValueError("GeoTIFF adapter expects 12 bands ordered January–December")
    base = Path(path)
    values = {}
    reference = None
    if base.is_file() and len(c["variables"]) > 1:
        raise ValueError(
            "For multiple variables provide a directory and one 12-band file per variable"
        )
    days = np.asarray(c.get("month_days", DAYS), float)
    for field, spec in c["variables"].items():
        source = base / spec["file"] if base.is_dir() else base
        with rasterio.open(source) as ds:
            if ds.count != 12 or ds.crs is None:
                raise ValueError("Each GeoTIFF needs a CRS and exactly 12 monthly bands")
            if reference is None:
                if (
                    ds.crs.to_epsg() == 4326
                    and ds.transform.b == 0
                    and ds.transform.d == 0
                    and "resolution" not in c
                ):
                    transform, width, height = ds.transform, ds.width, ds.height
                else:
                    transform, width, height = calculate_default_transform(
                        ds.crs,
                        "EPSG:4326",
                        ds.width,
                        ds.height,
                        *ds.bounds,
                        **({"resolution": c["resolution"]} if "resolution" in c else {}),
                    )
                if transform.a <= 0 or transform.e >= 0:
                    raise ValueError("Expected north-up grid")
                if max(width * height, ds.width * ds.height) > c.get("max_cells", 10_000_000):
                    raise ValueError(
                        "Raster too large for the selected memory budget; crop/reduce resolution or explicitly increase max_cells"
                    )
                reference = (transform, width, height)
            transform, width, height = reference
            aligned = (
                ds.crs.to_epsg() == 4326
                and ds.transform == transform
                and ds.width == width
                and ds.height == height
            )
            method = c.get("resampling", "nearest")
            if method not in ["nearest", "bilinear"]:
                raise ValueError("Resampling must be nearest or bilinear")
            a = np.full((12, height, width), np.nan, dtype="float32")
            for band in range(12):
                raw = ds.read(band + 1, masked=True).astype("float32").filled(np.nan)
                for sentinel in spec.get("missing_values", []):
                    raw[raw == sentinel] = np.nan
                converted = convert(raw, field, spec["unit"], days[band] * 24)
                if spec.get("clip_min") is not None:
                    converted = np.maximum(converted, float(spec["clip_min"]))
                converted = np.where(physical_mask(converted, field), converted, np.nan)
                if aligned:
                    a[band] = converted
                else:
                    reproject(
                        converted,
                        a[band],
                        src_transform=ds.transform,
                        src_crs=ds.crs,
                        src_nodata=np.nan,
                        dst_transform=transform,
                        dst_crs="EPSG:4326",
                        dst_nodata=np.nan,
                        resampling=getattr(Resampling, method),
                    )
            values[field] = a.reshape(12, -1)
    transform, width, height = reference
    yy, xx = np.meshgrid(
        transform.f + (np.arange(height) + 0.5) * transform.e,
        transform.c + (np.arange(width) + 0.5) * transform.a,
        indexing="ij",
    )
    xx = (xx + 180) % 360 - 180
    ids = np.array([f"{a:.8f},{b:.8f}" for a, b in zip(yy.ravel(), xx.ravel())])
    return ClimateCube(
        ids,
        yy.ravel(),
        xx.ravel(),
        values,
        days,
        c.get("period", "User-supplied climatology"),
        {"mapping": c, "grid_shape": [height, width], "resampling": c.get("resampling", "nearest")},
    )


def load_dataset(path, config):
    c = configuration(config)
    fmt = c.get("format", Path(path).suffix.lstrip(".").lower())
    if fmt in ["csv", "csv.gz", "gz"]:
        cube = table_cube(pd.read_csv(path, skiprows=c.get("skiprows", 0)), c)
    elif fmt in ["parquet", "pq"]:
        cube = table_cube(pd.read_parquet(path), c)
    elif fmt in ["nc", "netcdf", "zarr"]:
        cube = netcdf_cube(path, {**c, "format": fmt})
    elif fmt in ["tif", "tiff", "geotiff"]:
        cube = geotiff_cube(path, c)
    else:
        raise ValueError("Supported formats: CSV, Parquet, NetCDF, Zarr, 12-band GeoTIFF")
    if fmt in ["tif", "tiff", "geotiff"] and Path(path).is_dir():
        files = [
            {
                "path": spec["file"],
                "sha256": source_metadata(Path(path) / spec["file"], {})["sha256"],
            }
            for spec in c["variables"].values()
        ]
        cube.metadata.update(
            {
                "source_file": Path(path).name,
                "files": files,
                "sha256": hashlib.sha256(json.dumps(files, sort_keys=True).encode()).hexdigest(),
                "mapping": c,
            }
        )
    else:
        cube.metadata.update(source_metadata(path, c))
    return cube
