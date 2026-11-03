"""Scientific contracts, missing-data behavior and report aggregation."""

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from energyclimates.analysis.environment import run_environment
from energyclimates.inputs.environment import read_environment
from energyclimates.methods.environment import (
    soiling_screen,
)


def monthly(column, values):
    return pd.DataFrame({"latitude": [10.0], "longitude": [20.0], column: [values]})


def test_soiling_dimensions_and_tilt():
    frame = monthly("dust_ug_m3_months", [100.0] * 12)
    flat = soiling_screen(frame, tilt_degrees=0, deposition_velocity_m_s=0.001)
    assert flat.dry_deposition_g_m2_day.iloc[0] == pytest.approx(0.00864)
    tilted = soiling_screen(frame, tilt_degrees=60)
    assert tilted.dry_deposition_g_m2_day.iloc[0] == pytest.approx(0.00432)
    assert soiling_screen(frame, tilt_degrees=90).dry_deposition_g_m2_day.iloc[0] < 1e-15
    with pytest.raises(ValueError, match="tilt"):
        soiling_screen(frame, tilt_degrees=-1)


@pytest.mark.parametrize(
    "function,column,output",
    [
        (soiling_screen, "dust_ug_m3_months", "dry_deposition_g_m2_day"),
    ],
)
def test_incomplete_monthly_series_do_not_become_valid_annual_indicators(function, column, output):
    result = function(monthly(column, [1] * 11 + [np.nan]))
    assert result.valid_months.iloc[0] == 11
    assert np.isnan(result[output].iloc[0])
    with pytest.raises(ValueError):
        function(monthly(column, [1] * 11))
    with pytest.raises(ValueError, match="physical range"):
        function(monthly(column, [-1] * 12))


def test_snapshot_hash_and_study_export(tmp_path):
    root = Path(__file__).resolve().parents[1]
    path = root / "examples/environment/gmi-2019.parquet"
    frame = read_environment(path)
    result = run_environment(frame, "soiling", tilt_degrees=60)
    result.write(tmp_path)
    manifest = json.loads((tmp_path / "manifest.json").read_text())
    assert manifest["parameters"]["tilt_degrees"] == 60
    assert manifest["parameters"]["deposition_velocity_m_s"] == 0.001
    assert manifest["input"]["sha256"] == frame.attrs["sha256"]
    altered = tmp_path / "bad.parquet"
    altered.write_bytes(path.read_bytes() + b"changed")
    altered.with_suffix(".metadata.json").write_text(path.with_suffix(".metadata.json").read_text())
    with pytest.raises(ValueError, match="checksum"):
        read_environment(altered)


def test_all_bundled_inputs_have_verified_provenance():
    root = Path(__file__).resolve().parents[1]
    for path in (root / "examples/environment").glob("*.parquet"):
        frame = read_environment(path)
        assert len(frame) == frame.attrs["rows"]
        assert frame.attrs["sources"]
        assert all(len(source["sha256"]) == 64 for source in frame.attrs["sources"])


def test_rectilinear_native_axes_preserve_missing_rows():
    pytest.importorskip("matplotlib")
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    from energyclimates.analysis.maps import plot_rectilinear_map

    frame = pd.DataFrame({"latitude": [-40, 70], "longitude": [-150, 150], "v": [1, 2]})
    image = plot_rectilinear_map(frame, "v", latitude=[-40, 0, 70], longitude=[-150, 0, 150])
    data = image.get_array()
    assert data.shape == (3, 3)
    assert data[0, 0] == 1 and data[2, 2] == 2
    assert data[1].mask.all()
    with pytest.raises(ValueError, match="supplied axes"):
        plot_rectilinear_map(
            frame.assign(latitude=[-39, 70]), "v", latitude=[-40, 0, 70], longitude=[-150, 0, 150]
        )
    plt.close("all")


def test_rectilinear_global_dateline_half_cell_is_visible_on_both_edges():
    pytest.importorskip("matplotlib")
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    from energyclimates.analysis.maps import plot_rectilinear_map

    frame = pd.DataFrame({"latitude": [0], "longitude": [-180], "v": [7]})
    image = plot_rectilinear_map(frame, "v", latitude=[-45, 0, 45], longitude=[-180, -90, 0, 90])
    values = image.get_array()
    assert values[1, 0] == values[1, -1] == 7
    assert values[1, 1:-1].mask.all()
    assert image.get_coordinates()[0, 0, 0] == -180
    assert image.get_coordinates()[0, -1, 0] == 180
    plt.close("all")
