"""Execute map gallery studies offline and export figures, tables and provenance."""

import argparse
import hashlib
import json
import platform
import runpy
import sys
from contextlib import redirect_stdout
from importlib.metadata import version
from io import StringIO
from pathlib import Path
from unittest.mock import patch
from zipfile import ZIP_DEFLATED, ZipFile


def checksum(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("results/map-gallery"))
    parser.add_argument("--archive", type=Path, help="Optional combined ZIP of this run's outputs")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(root))

    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    from energyclimates import __version__

    output = args.output.resolve()
    if output == root or root.is_relative_to(output):
        parser.error("Output cannot be the repository or its ancestor")
    if output.is_relative_to(root) and not any(
        output.is_relative_to(root / allowed) for allowed in ("results", "docs/_generated")
    ):
        parser.error("Repository-local output must be below results/ or docs/_generated/")
    output.mkdir(parents=True, exist_ok=True)
    generated = []
    reports = []
    sources = [
        root / path
        for path in (
            "energyclimates/analysis/maps.py",
            "kgpv/engine/rules.py",
            "kgpv/engine/ml.py",
            "scripts/run_map_gallery.py",
            "energyclimates/inputs/environment.py",
            "energyclimates/methods/environment.py",
            "energyclimates/analysis/environment.py",
        )
    ]
    runtime = {name: version(name) for name in ("numpy", "pandas", "matplotlib", "pyarrow")}
    for example in sorted((root / "examples/gallery").glob("plot_*_map_*.py")):
        plt.close("all")
        log = StringIO()
        with redirect_stdout(log), patch.object(plt, "show"):
            namespace = runpy.run_path(str(example))
        figures = [plt.figure(number) for number in plt.get_fignums()]
        tables = namespace["result_tables"]
        if not figures or not tables or any(frame.empty for frame in tables.values()):
            raise RuntimeError(f"{example.name} did not produce figures and nonempty tables")
        folder = output / example.stem
        folder.mkdir(exist_ok=True)
        files = []
        for index, figure in enumerate(figures, start=1):
            for suffix in ("png", "svg"):
                path = folder / f"figure-{index}.{suffix}"
                figure.savefig(path, dpi=150, bbox_inches="tight", facecolor="white")
                files.append(path)
        table_metadata = {}
        for name, frame in tables.items():
            path = folder / f"{name}.csv"
            frame.to_csv(path, index=False, float_format="%.12g")
            files.append(path)
            table_metadata[name] = {
                "rows": len(frame),
                "columns": list(frame.columns),
                "metadata": frame.attrs,
            }
        script = folder / example.name
        script.write_text(example.read_text())
        stdout = folder / "results.txt"
        stdout.write_text(log.getvalue())
        files.extend([script, stdout])
        manifest = {
            "schema": "energyclimates-map-gallery-v1",
            "example": example.name,
            "package_version": __version__,
            "python": platform.python_version(),
            "dependencies": runtime,
            "context": namespace["map_context"],
            "input_metadata": namespace["features"].attrs,
            "grid": namespace.get(
                "map_grid",
                {
                    "crs": "EPSG:4326",
                    "resolution_degrees": 0.5,
                    "display": "equirectangular",
                    "interpolation": "none",
                    "grey_background": "No supplied value or unclassified cell",
                },
            ),
            "inputs_sha256": {
                str(p.relative_to(root)): checksum(p) for p in namespace["input_files"]
            },
            "code_sha256": {str(p.relative_to(root)): checksum(p) for p in [example, *sources]},
            "tables": table_metadata,
            "outputs_sha256": {p.name: checksum(p) for p in files},
            "limitations": namespace["map_context"].get(
                "limitations", "Screening, not yield, storage sizing or battery-life predictions."
            ),
        }
        manifest_path = folder / "manifest.json"
        manifest_path.write_text(
            json.dumps(manifest, indent=2, ensure_ascii=False, allow_nan=False)
        )
        files.append(manifest_path)
        generated.extend(files)
        reports.append(
            {
                "example": example.stem,
                "figures": len(figures),
                "tables": {name: len(frame) for name, frame in tables.items()},
            }
        )
        plt.close("all")
        print(f"{example.stem}: {len(figures)} figure(s), {len(tables)} table(s)")
    if not reports:
        raise RuntimeError("No map gallery examples found")
    for name in ("DATA_LICENSES.md", "LICENSE"):
        target = output / name
        target.write_text((root / name).read_text())
        generated.append(target)
    provenance = output / "source-provenance.json"
    provenance.write_text((root / "atlas/data/energy-provenance.json").read_text())
    generated.append(provenance)
    summary = output / "summary.json"
    summary.write_text(json.dumps(reports, indent=2))
    generated.append(summary)
    if args.archive:
        archive = args.archive.resolve()
        if archive in generated:
            parser.error("Archive cannot overwrite a generated result")
        archive.parent.mkdir(parents=True, exist_ok=True)
        # Include only files produced by this run, never stale or unrelated files.
        with ZipFile(archive, "w", compression=ZIP_DEFLATED) as bundle:
            for path in sorted(generated):
                bundle.write(path, path.relative_to(output))
        print(f"Results archive: {archive}")
    print(f"Completed {len(reports)} map examples in {output}")


if __name__ == "__main__":
    main()
