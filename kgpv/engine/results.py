"""Shared feature reading and study exports for Python and CLI workflows."""

import json
from pathlib import Path

import numpy as np
import pandas as pd


def write_json(path, value):
    Path(path).write_text(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False))


def read_features(path):
    p = Path(path)
    f = pd.read_parquet(p) if p.suffix in [".parquet", ".pq"] else pd.read_csv(p)
    side = p.with_suffix(".metadata.json")
    if side.exists():
        f.attrs.update(json.loads(side.read_text()))
    return f


def export_results(folder, features, result, metadata):
    out = Path(folder)
    out.mkdir(parents=True, exist_ok=True)
    features.to_csv(out / "features.csv", index=False)
    result.to_csv(out / "classification.csv", index=False)
    write_json(out / "features.metadata.json", features.attrs)
    write_json(out / "manifest.json", metadata)
    # Points preserve station coordinates and work for irregular or regular grids.
    if {"latitude", "longitude"}.issubset(result):
        records = []
        for row in result.to_dict("records"):
            lat, lon = row.pop("latitude"), row.pop("longitude")
            properties = {k: (None if pd.isna(v) else v) for k, v in row.items()}
            records.append(
                {
                    "type": "Feature",
                    "geometry": {"type": "Point", "coordinates": [lon, lat]},
                    "properties": properties,
                }
            )
        write_json(
            out / "classification.geojson", {"type": "FeatureCollection", "features": records}
        )
    # Export a categorical GeoTIFF when every coordinate in a regular grid is present.
    if {"latitude", "longitude"}.issubset(features) and not features.duplicated(
        ["latitude", "longitude"]
    ).any():
        lat = np.sort(features.latitude.unique())[::-1]
        lon = np.sort(features.longitude.unique())
        regular = (
            len(lat) > 1
            and len(lon) > 1
            and len(lat) * len(lon) == len(features)
            and np.allclose(np.diff(lat), np.diff(lat)[0])
            and np.allclose(np.diff(lon), np.diff(lon)[0])
        )
        if regular:
            import rasterio
            from rasterio.transform import from_origin

            by = (
                result.groupby("technology") if "technology" in result else [("prediction", result)]
            )
            for tech, rows in by:
                grid = (
                    rows.pivot(index="latitude", columns="longitude", values="zone_id")
                    .reindex(index=lat, columns=lon)
                    .fillna(0)
                    .to_numpy("uint8")
                )
                dx = float(lon[1] - lon[0])
                dy = float(lat[0] - lat[1])
                with rasterio.open(
                    out / f"{tech}.tif",
                    "w",
                    driver="GTiff",
                    height=len(lat),
                    width=len(lon),
                    count=1,
                    dtype="uint8",
                    nodata=0,
                    crs="EPSG:4326",
                    transform=from_origin(lon[0] - dx / 2, lat[0] + dy / 2, dx, dy),
                    compress="deflate",
                ) as dst:
                    dst.write(grid, 1)
                    dst.update_tags(
                        period=features.attrs.get("period", "Not supplied"),
                        labels=json.dumps(
                            rows[["zone_id", "zone_name"]].drop_duplicates().to_dict("records")
                        ),
                    )
    print(f"Saved {len(result):,} profiles to {out.resolve()}; missing inputs remain unclassified.")
