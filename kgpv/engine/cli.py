"""Friendly command line for mapped weather, transparent rules and portable ML."""

import argparse
import json
from pathlib import Path
import pandas as pd
import numpy as np
from .adapters import load_dataset
from .features import extract_features
from .rules import classify_features, classify_kgpv, load_rules
from .ml import train_clusters, predict_clusters, save_model, load_model, evaluate_target


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


def prepare_website(folder):
    """Rebuild redundant browser assets from the native rasters in the download."""
    import rasterio
    from ..export import write_layer

    dist = Path(folder)
    catalog = json.loads((dist / "data/catalog.json").read_text())
    for layer in catalog["layers"]:
        with rasterio.open(dist / layer["download"].lstrip("/")) as src:
            a = src.read(1)
            transform = src.transform
        write_layer(
            dist,
            layer["id"],
            layer["title"],
            a,
            layer["group"],
            layer["period"],
            layer["units"],
            layer["description"],
            layer["source"],
            labels=layer.get("labels"),
            colors=layer.get("colors"),
            limits=(layer["min"], layer["max"]),
            warning=layer.get("warning"),
            transform=transform,
        )
    print(
        f"Rebuilt {len(catalog['layers'])} browser layers. Run: python -m http.server 8000 --directory {dist}"
    )


def parser():
    p = argparse.ArgumentParser(
        prog="energyclimates",
        description="Turn weather data into plain-language PV, PV + battery and battery climate profiles.",
    )
    sub = p.add_subparsers(dest="command", required=True)
    for action in ["classify", "predict"]:
        s = sub.add_parser(action)
        s.add_argument("input")
        s.add_argument("--mapping", help="JSON field/unit mapping (required for weather data)")
        s.add_argument(
            "--features", action="store_true", help="Input is already an extracted feature table"
        )
        s.add_argument("--output", default="results")
        if action == "classify":
            s.add_argument(
                "--technology", choices=["all", "pv", "hybrid", "bess", "kgpv"], default="all"
            )
            s.add_argument("--rules", help="Optional versioned rule JSON")
        else:
            s.add_argument("--model", required=True)
    s = sub.add_parser("train")
    s.add_argument("input")
    s.add_argument("--technology", choices=["pv", "hybrid", "bess"], default="pv")
    s.add_argument("--clusters", type=int)
    s.add_argument("--seed", type=int, default=42)
    s.add_argument(
        "--area-weighted",
        action="store_true",
        help="Only for a regular latitude/longitude grid, not station samples",
    )
    s.add_argument("--output", default="model.json")
    s.add_argument("--period")
    s.add_argument("--rules")
    s.add_argument("--feature-columns", nargs="+")
    s = sub.add_parser("evaluate-target")
    s.add_argument("input")
    s.add_argument("--target", required=True)
    s.add_argument("--technology", choices=["pv", "hybrid", "bess"], default="pv")
    s.add_argument("--seed", type=int, default=42)
    s.add_argument("--output", default="target-evaluation.json")
    s = sub.add_parser("add-layer")
    s.add_argument("input")
    s.add_argument("--dist", default="atlas")
    s.add_argument("--id", required=True)
    s.add_argument("--title", required=True)
    s.add_argument("--source", required=True)
    s.add_argument("--period")
    s = sub.add_parser("prepare-website")
    s.add_argument("--dist", default="atlas")
    return p


def main(argv=None):
    p = parser()
    a = p.parse_args(argv)
    try:
        if a.command == "prepare-website":
            prepare_website(a.dist)
            return
        if a.command == "add-layer":
            from .publish import add_layer

            add_layer(a.input, a.dist, a.id, a.title, a.source, a.period)
            return
        if a.command in ["classify", "predict"]:
            cube = None
            if a.features:
                f = read_features(a.input)
            else:
                if not a.mapping:
                    raise ValueError(
                        "Use --mapping your-mapping.json to declare columns, units and time frequency"
                    )
                cube = load_dataset(a.input, a.mapping)
                f = extract_features(cube)
            if a.command == "classify":
                rules = load_rules(a.rules)
                techs = ["pv", "hybrid", "bess"] if a.technology == "all" else [a.technology]
                if "kgpv" in techs and cube is None:
                    raise ValueError(
                        "KGPV requires monthly temperature, rain and irradiation; supply weather data with --mapping"
                    )
                result = pd.concat(
                    [
                        classify_kgpv(cube) if t == "kgpv" else classify_features(f, t, rules)
                        for t in techs
                    ],
                    ignore_index=True,
                )
                metadata = {
                    "operation": "classification",
                    "rules": rules,
                    "input": f.attrs,
                    "limitations": "Experimental ambient-climate profiles; not battery sizing, lifetime, safety or investment recommendations.",
                }
            else:
                model = load_model(a.model)
                result = predict_clusters(f, model)
                metadata = {
                    "operation": "ML prediction",
                    "model_version": model["model_version"],
                    "model_training_sha256": model["training_sha256"],
                    "input": f.attrs,
                    "note": "Distance separation is not a probability. Models are independent of published PVZones and Delft classifications.",
                }
            export_results(a.output, f, result, metadata)
        elif a.command == "train":
            f = read_features(a.input)
            if a.period:
                f.attrs["period"] = a.period
            model, prediction = train_clusters(
                f,
                a.technology,
                a.clusters or (4 if a.technology == "bess" else 8),
                a.seed,
                a.area_weighted,
                a.feature_columns,
                load_rules(a.rules),
            )
            out = Path(a.output)
            out.parent.mkdir(parents=True, exist_ok=True)
            save_model(model, out)
            prediction.to_csv(out.with_suffix(".predictions.csv"), index=False)
            print(
                f"Saved {model['clusters']} experimental groups to {out.resolve()}. Geographic holdout diagnostics are included in the model JSON."
            )
        else:
            report = evaluate_target(read_features(a.input), a.target, a.technology, a.seed)
            write_json(a.output, report)
            print(f"Saved spatial cross-validation results to {a.output}")
    except (ValueError, KeyError, FileNotFoundError, ImportError) as e:
        p.exit(2, f"Cannot complete: {e}\n")


if __name__ == "__main__":
    main()
