"""Public layer compatibility and provenance across the applied workflow."""

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
import rasterio

import energyclimates
from energyclimates.analysis import run_classification
from energyclimates.inputs import example_climate, load_dataset
from energyclimates.methods import classify_features, extract_features
from energyclimates.methods.ml import predict_clusters
from energyclimates.ml import predict_clusters as legacy_predict


def test_public_layers_preserve_function_identity():
    assert energyclimates.load_dataset is load_dataset
    assert energyclimates.extract_features is extract_features
    assert energyclimates.classify_features is classify_features
    assert predict_clusters is legacy_predict


def test_sample_is_independent_and_keeps_missing_data(tmp_path):
    cube = example_climate()
    cube.values["ghi"][0, 0] = np.nan
    assert np.isfinite(example_climate().values["ghi"]).all()
    study = run_classification(cube)
    rows = study.classifications.query("location_id == 'mild'").set_index("technology")
    assert rows.loc["pv", "zone_id"] == 0
    assert rows.loc["hybrid", "zone_id"] == 0
    assert rows.loc["bess", "zone_id"] > 0
    study.write(tmp_path)
    manifest = json.loads((tmp_path / "manifest.json").read_text())
    assert manifest["input"]["metadata"]["synthetic"] is True
    assert manifest["package_version"] == energyclimates.__version__
    assert len(pd.read_csv(tmp_path / "classification.csv")) == 12
    assert len(json.loads((tmp_path / "classification.geojson").read_text())["features"]) == 12
    assert not list(tmp_path.glob("*.tif"))


def test_regular_grid_exports_and_published_method(tmp_path):
    cube = example_climate()
    cube.latitude[:] = [10, 10, 20, 20]
    cube.longitude[:] = [0, 10, 0, 10]
    study = run_classification(cube, technology="kgpv")
    study.write(tmp_path)
    with rasterio.open(tmp_path / "kgpv.tif") as grid:
        assert grid.shape == (2, 2)
        assert grid.crs.to_epsg() == 4326
        assert grid.nodata == 0
        expected = study.classifications.pivot(
            index="latitude", columns="longitude", values="zone_id"
        )
        np.testing.assert_array_equal(grid.read(1), expected.loc[[20, 10], [0, 10]].to_numpy())
    assert "rules" not in study.manifest["method"]
    assert study.manifest["method"]["name"] == "KGPV"


def test_file_input_preserves_source_hash():
    root = Path(__file__).resolve().parents[1]
    study = run_classification(
        root / "examples/monthly-climate.csv", root / "examples/monthly-mapping.json"
    )
    assert len(study.classifications) == 18
    assert len(study.manifest["input"]["metadata"]["sha256"]) == 64
    assert "synthetic" not in study.manifest["input"]["metadata"]


@pytest.mark.parametrize("technology", ["wind", "", "ALL"])
def test_invalid_technology(technology):
    with pytest.raises(ValueError, match="technology"):
        run_classification(example_climate(), technology=technology)


def test_explicit_mapping_contract():
    with pytest.raises(ValueError, match="mapping"):
        run_classification("weather.csv")
    with pytest.raises(ValueError, match="mapping"):
        run_classification(example_climate(), {})
