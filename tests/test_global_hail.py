"""Scientific contracts for the global single-year hail map."""

import importlib.util
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from energyclimates.analysis.environment import run_environment
from energyclimates.inputs.environment import read_environment
from energyclimates.methods.hail import hail_probability_screen

ROOT = Path(__file__).resolve().parents[1]


def test_hail_sum_is_not_annual_probability():
    frame = pd.DataFrame(
        {
            "latitude": [0, 1, 2],
            "longitude": [0, 1, 2],
            "sum_daily_hail_probability": [36.5, 0, np.nan],
        }
    )
    study = run_environment(frame, "global_hail")
    np.testing.assert_allclose(study.indicators.modeled_hail_day_equivalents, [36.5, 0, np.nan])
    np.testing.assert_allclose(study.indicators.mean_daily_hail_probability, [0.1, 0, np.nan])
    assert study.manifest["output_units"]["mean_daily_hail_probability"] == "fraction"
    for value in [-1, 366, np.inf]:
        frame.loc[0, "sum_daily_hail_probability"] = value
        with pytest.raises(ValueError, match="physical range"):
            hail_probability_screen(frame)
    with pytest.raises(ValueError, match="days"):
        hail_probability_screen(frame, n_days=0)


def test_daily_fraction_reduction_and_missing_days():
    sys.path.insert(0, str(ROOT / "scripts"))
    try:
        spec = importlib.util.spec_from_file_location(
            "build_global_hail_input", ROOT / "scripts/build_global_hail_input.py"
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        values = np.array([[[0.5, 0, np.nan]], [[0.5, 0, 0.2]]])
        np.testing.assert_allclose(module.sum_daily_probabilities(values), [[1, 0, np.nan]])
        for value in [-0.01, 1.01, np.inf]:
            with pytest.raises(ValueError, match="fractions"):
                module.sum_daily_probabilities(np.array([[[value]]]))
    finally:
        sys.path.pop(0)


def test_snapshot_global_coverage_and_provenance():
    frame = read_environment(ROOT / "examples/environment/global-hail-2015.parquet")
    assert len(frame) == 256 * 512
    assert frame.attrs["period"] == "2015-01-01/2015-12-31"
    assert frame.latitude.min() < -89 and frame.latitude.max() > 89
    assert frame.longitude.min() < -179 and frame.longitude.max() > 179
    assert not frame.duplicated(["latitude", "longitude"]).any()
    for south, north, west, east in [
        (-35, 5, -80, -35),
        (-35, 35, -15, 45),
        (-40, -10, 110, 155),
        (5, 50, 65, 145),
    ]:
        region = frame.query("@south < latitude < @north and @west < longitude < @east")
        assert region.sum_daily_hail_probability.max() > 0
    study = run_environment(frame, "global_hail")
    assert study.indicators.modeled_hail_day_equivalents.max() == pytest.approx(28.89250442257041)
    assert (study.indicators.modeled_hail_day_equivalents == 0).any()
    assert len(frame.attrs["sources"][0]["sha256"]) == 64
