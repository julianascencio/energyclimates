"""Friendly command line for mapped weather, transparent rules and portable ML."""

import argparse
import json
from pathlib import Path
import pandas as pd
from .adapters import load_dataset
from .features import extract_features
from .rules import classify_features, classify_kgpv, load_rules
from .ml import train_clusters, predict_clusters, save_model, load_model, evaluate_target


from .results import export_results, read_features, write_json


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
