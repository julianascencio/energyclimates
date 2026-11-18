"""Verify optional installs and native RustGIS round trips against the atlas rasters."""

import hashlib
import json
import shutil
import sys
from pathlib import Path

import pytest
import rasterio

from energyclimates.analysis.rustgis import open_rustgis_atlas
from energyclimates.cli import main

ATLAS = Path(__file__).resolve().parents[1] / "atlas"


def test_missing_optional_dependency(monkeypatch):
    monkeypatch.setitem(sys.modules, "rustgis", None)
    with pytest.raises(ImportError, match=r"Python 3\.12.*rustgis extra"):
        open_rustgis_atlas(ATLAS)


def test_portable_cli_project(tmp_path):
    rustgis = pytest.importorskip("rustgis")
    # Copy only the scientific inputs, then remove them before reopening the project.
    data = tmp_path / "atlas/data"
    data.mkdir(parents=True)
    for name in ("catalog.json", "ghi-1996-2022.tif", "energy-pv.tif"):
        shutil.copy(ATLAS / "data" / name, data / name)
    project = tmp_path / "results" / "solar.rgis"
    main(
        [
            "rustgis",
            "ghi-1996-2022",
            "energy-pv",
            "--atlas",
            str(data.parent),
            "--output",
            str(project),
        ]
    )
    shutil.rmtree(data.parent)
    session = rustgis.Session(project=project)
    assert session.layer_names() == ["ghi-1996-2022", "energy-pv"]
    info = session.info()
    assert [layer["visible"] for layer in info["layers"]] == [True, False]
    assert [layer["renderer"] for layer in info["layers"]] == ["Stretch", "Unique Values"]
    assert {t["name"]: t["rows"] for t in info["tables"]} == {"Atlas layers": 2, "Class codes": 12}
    # The project carries both the source identity and the class descriptions.
    saved = project.read_text(encoding="utf-8")
    assert hashlib.sha256((ATLAS / "data/energy-pv.tif").read_bytes()).hexdigest() in saved
    assert "1996–2022" in saved
    assert "Low sun · cool" in saved

    lon, lat = -70.33, -27.37
    for layer in session.layer_names():
        session["ghi-1996-2022"].visible = layer == "ghi-1996-2022"
        session["energy-pv"].visible = layer == "energy-pv"
        with rasterio.open(ATLAS / "data" / f"{layer}.tif") as src:
            expected = next(src.sample([(lon, lat)]))[0]
            raster = session.run("raster.info", layer=layer)
            assert raster["cellSize"] == list(src.res)
            assert raster["crs"] == src.crs.to_string()
        hit = session.run("identify", lon=lon, lat=lat)
        assert hit["layer"] == layer
        # RustGIS Identify formats the continuous irradiation value to whole kWh/m²/year.
        assert float(hit["attributes"]["Band 1"]) == pytest.approx(expected, abs=0.5)
        assert session.run("identify", lon=0, lat=0) is None  # ocean / missing
    assert session.to_png(width=320, height=240).startswith(b"\x89PNG\r\n\x1a\n")


def test_default_and_invalid_ids():
    pytest.importorskip("rustgis")
    catalog = json.loads((ATLAS / "data/catalog.json").read_text(encoding="utf-8"))
    assert open_rustgis_atlas(ATLAS).layer_names() == [catalog["default"]]
    with pytest.raises(ValueError, match="Unknown atlas layer"):
        open_rustgis_atlas(ATLAS, "missing")
    with pytest.raises(ValueError, match="only once"):
        open_rustgis_atlas(ATLAS, "energy-pv", "energy-pv")


def test_identify_uses_original_half_cell_offset():
    pytest.importorskip("rustgis")
    key = "original-Tamb_avg"
    session = open_rustgis_atlas(ATLAS, key)
    # This point falls in a different row on a world-aligned 0.5° grid.
    lon, lat = -99.99, 45.01
    with rasterio.open(ATLAS / "data" / f"{key}.tif") as src:
        row, col = src.index(lon, lat)
        value = next(src.sample([(lon, lat)]))[0]
    hit = session.run("identify", lon=lon, lat=lat)["attributes"]
    assert hit["Pixel"] == f"{col}, {row}"
    assert float(hit["Band 1"]) == pytest.approx(value, abs=0.005)
