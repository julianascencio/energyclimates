"""Build warning-free Sphinx docs and stage the existing atlas under /atlas/."""

import argparse
import shutil
import subprocess
import sys
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default="docs/_build/html")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    output = Path(args.output).resolve()
    if output == root or root.is_relative_to(output):
        parser.error("Output must not be the repository or an ancestor")
    # Prevent overwriting any source directory when staging the atlas.
    if output.is_relative_to(root) and not output.is_relative_to(root / "docs/_build"):
        parser.error("Repository-local output must be below docs/_build")
    subprocess.run(
        [
            sys.executable,
            "-m",
            "sphinx",
            "-W",
            "--keep-going",
            "-b",
            "html",
            str(root / "docs"),
            str(output),
        ],
        cwd=root,
        check=True,
    )
    atlas = output / "atlas"
    if atlas.exists():
        shutil.rmtree(atlas)
    shutil.copytree(root / "atlas", atlas, ignore=shutil.ignore_patterns("*.zip", "*.bin"))
    subprocess.run(
        [sys.executable, "-m", "energyclimates", "prepare-website", "--dist", str(atlas)],
        cwd=root,
        check=True,
    )
    subprocess.run(
        [sys.executable, str(root / "scripts/check_site.py"), str(output)], cwd=root, check=True
    )
    print(f"Documentation and atlas ready: {output / 'index.html'}")


if __name__ == "__main__":
    main()
