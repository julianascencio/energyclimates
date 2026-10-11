"""Provider-independent climate classification for solar and storage."""

from .features import ClimateCube, extract_features
from .rules import classify_features, classify_kgpv, load_rules
from .adapters import load_dataset

__all__ = [
    "ClimateCube",
    "extract_features",
    "classify_features",
    "classify_kgpv",
    "load_rules",
    "load_dataset",
]
