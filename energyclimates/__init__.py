"""Plain-language climate classifications for energy systems.

New PV, hybrid and BESS profiles are experimental. Published KGPV and PVCZ
methods retain their attribution and declared implementation conventions.
"""
from kgpv.engine import (
    ClimateCube,
    classify_features,
    classify_kgpv,
    extract_features,
    load_dataset,
    load_rules,
)

__version__ = "0.1.0"
__all__ = [
    "ClimateCube", "classify_features", "classify_kgpv", "extract_features",
    "load_dataset", "load_rules",
]
