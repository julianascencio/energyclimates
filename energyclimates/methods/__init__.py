"""Reusable climate features and classifications, independent of file I/O.

Published KGPV/PVCZ methods and experimental PV/hybrid/BESS screening profiles
retain their existing implementations, units and missing-data conventions.
Machine-learning methods are available in :mod:`energyclimates.methods.ml`.
"""

from kgpv.engine.features import FEATURE_UNITS, extract_features
from kgpv.engine.rules import (
    class_labels,
    classify_features,
    classify_kgpv,
    classify_pvcz,
    load_rules,
    pvcz_stressors,
)

__all__ = [
    "FEATURE_UNITS",
    "class_labels",
    "classify_features",
    "classify_kgpv",
    "classify_pvcz",
    "extract_features",
    "load_rules",
    "pvcz_stressors",
]
