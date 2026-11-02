"""Reproducible studies that connect inputs, methods and saved evidence."""

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from energyclimates import __version__
from energyclimates.inputs import ClimateCube, load_dataset
from energyclimates.methods import classify_features, classify_kgpv, extract_features, load_rules
from kgpv.engine.results import export_results

__all__ = ["ClassificationStudy", "run_classification"]


@dataclass
class ClassificationStudy:
    """A feature table, classifications and the provenance for one study.

    ``classifications`` has one row per location and selected technology.
    Zone ID zero denotes insufficient data and is retained in all exports.
    """

    features: pd.DataFrame
    classifications: pd.DataFrame
    manifest: dict

    def write(self, output: str | Path) -> Path:
        """Write CSV, metadata JSON, GeoJSON and eligible regular-grid GeoTIFFs.

        Use a dedicated folder per study. Matching files are replaced; unrelated
        files are left untouched. Provider files and atlas assets are not copied.
        """
        folder = Path(output)
        export_results(folder, self.features, self.classifications, self.manifest)
        return folder


def run_classification(
    source: ClimateCube | str | Path,
    mapping: dict | str | Path | None = None,
    *,
    technology: str = "all",
) -> ClassificationStudy:
    """Classify a local dataset or an already normalized climate cube.

    Parameters
    ----------
    source : ClimateCube or path
        Normalized monthly values or a local file supported by the adapters.
    mapping : dict or path, optional
        Required for file inputs; declares variables, units and time semantics.
        Must be omitted for an existing cube.
    technology : str
        ``all`` runs the experimental PV, hybrid and BESS profiles. ``kgpv``
        selects the separate published method; ``pv``, ``hybrid`` or ``bess``
        selects a single experimental profile.

    Returns
    -------
    ClassificationStudy
        Tables and provenance. No files are written until ``write`` is called.
    """
    if technology not in {"all", "pv", "hybrid", "bess", "kgpv"}:
        raise ValueError("technology must be all, pv, hybrid, bess or kgpv")
    if isinstance(source, ClimateCube):
        if mapping is not None:
            raise ValueError("mapping must be omitted for a ClimateCube")
        cube = source
    else:
        if mapping is None:
            raise ValueError("A mapping with explicit variables, units and frequency is required")
        cube = load_dataset(source, mapping)
    features = extract_features(cube)
    technologies = ["pv", "hybrid", "bess"] if technology == "all" else [technology]
    rules = load_rules()
    classifications = pd.concat(
        [
            classify_kgpv(cube) if item == "kgpv" else classify_features(features, item, rules)
            for item in technologies
        ],
        ignore_index=True,
    )
    manifest = {
        "schema_version": "classification-study-v1",
        "package_version": __version__,
        "operation": "classification",
        "technologies": technologies,
        "input": features.attrs,
        "method": (
            {"name": "KGPV", "reference": "https://doi.org/10.1016/j.solener.2019.08.072"}
            if technology == "kgpv"
            else {"name": "Experimental energy climate profiles", "rules": rules}
        ),
        "limitations": (
            "Climate screening only; not a prediction of yield, storage size, "
            "battery safety, lifetime, cooling load or financial return."
        ),
    }
    return ClassificationStudy(features, classifications, manifest)
