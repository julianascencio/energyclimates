"""Inspect both distributions and exercise only the installed wheel outside Git."""

import argparse
import os
import subprocess
import sys
import tarfile
import tempfile
import zipfile
from pathlib import Path

SMOKE = r"""
from pathlib import Path
from importlib.metadata import distribution
import json
import energyclimates
from energyclimates import load_dataset, extract_features, classify_features
from energyclimates.inputs import example_climate
from energyclimates.methods import load_rules
from energyclimates.analysis import run_classification
from energyclimates.analysis.environment import run_environment
from energyclimates.methods.ml import predict_clusters
import energyclimates.ml
import energyclimates.pvcz
import kgpv
assert Path(energyclimates.__file__).resolve().is_relative_to(Path('installed').resolve())
assert Path(kgpv.__file__).resolve().is_relative_to(Path('installed').resolve())
assert distribution('energyclimates').version == energyclimates.__version__
assert load_rules()['version']
study = run_classification(example_climate())
assert len(study.classifications) == 12
study.write('results')
manifest = json.loads(Path('results/manifest.json').read_text())
assert manifest['input']['metadata']['synthetic'] is True
assert len(run_classification(example_climate(), technology='kgpv').classifications) == 4
import pandas as pd
dust = pd.DataFrame({'latitude': [50.0], 'longitude': [10.0],
                     'dust_ug_m3_months': [[100.0] * 12]})
environment = run_environment(dust, 'soiling', tilt_degrees=0)
assert abs(environment.indicators.dry_deposition_g_m2_day.iloc[0] - 0.00864) < 1e-12
environment.write('environment-results')
assert json.loads(Path('environment-results/manifest.json').read_text())['kind'] == 'soiling'
for name in ('energyclimates', 'pvclimate', 'kgpv'):
    entry = next(e for e in distribution('energyclimates').entry_points if e.name == name)
    import sys
    sys.argv = [name, '--help']
    try:
        entry.load()()
    except SystemExit as exc:
        assert exc.code == 0
print('Installed wheel API, resources, version and CLI checks passed.')
"""


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", nargs="?", default="dist")
    args = parser.parse_args()
    dist = Path(args.directory).resolve()
    wheels = list(dist.glob("energyclimates-*.whl"))
    sources = list(dist.glob("energyclimates-*.tar.gz"))
    if len(wheels) != 1 or len(sources) != 1:
        parser.error("Expected exactly one energyclimates wheel and one sdist in a clean directory")
    with zipfile.ZipFile(wheels[0]) as archive:
        names = archive.namelist()
        for required in (
            "energyclimates/inputs/__init__.py",
            "energyclimates/methods/__init__.py",
            "energyclimates/analysis/__init__.py",
            "energyclimates/inputs/environment.py",
            "energyclimates/methods/environment.py",
            "energyclimates/analysis/environment.py",
            "kgpv/engine/rules-v1.json",
        ):
            assert required in names, required
        assert not any(n.startswith(("atlas/", "tests/", "examples/")) for n in names)
        for notice in ("LICENSE", "NOTICE", "DATA_LICENSES.md"):
            assert any(n.endswith("/licenses/" + notice) for n in names), notice
    with tarfile.open(sources[0]) as archive:
        names = {n.split("/", 1)[-1] for n in archive.getnames()}
        for required in (
            "pyproject.toml",
            "docs/conf.py",
            "examples/environment/gmi-2019.parquet",
            "examples/environment/gmi-2019.metadata.json",
            "examples/environment/snow-1981-2010.parquet",
            "examples/environment/snow-1981-2010.metadata.json",
            "examples/environment/storm-reports-2020-2024.parquet",
            "examples/environment/storm-reports-2020-2024.metadata.json",
            "scripts/build_environment_inputs.py",
            "scripts/check_distribution.py",
            "tests/test_public_workflow.py",
            "examples/monthly-climate.csv",
            "atlas/energy-core.mjs",
            "kgpv/engine/rules-v1.json",
        ):
            assert required in names, required
    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp) / "installed"
        subprocess.run(
            [
                sys.executable,
                "-m",
                "pip",
                "install",
                "--no-deps",
                "--no-compile",
                "--target",
                str(target),
                str(wheels[0]),
            ],
            check=True,
        )
        env = dict(os.environ, PYTHONPATH=str(target))
        subprocess.run([sys.executable, "-c", SMOKE], cwd=tmp, env=env, check=True)
        subprocess.run(
            [sys.executable, "-m", "energyclimates", "--help"], cwd=tmp, env=env, check=True
        )


if __name__ == "__main__":
    main()
