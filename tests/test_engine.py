"""Scientific contracts, adapter equivalence and independent-language parity."""

import json
import subprocess
import tempfile
import unittest
from pathlib import Path
import numpy as np
import pandas as pd
import xarray as xr
from kgpv.engine import (
    ClimateCube,
    extract_features,
    classify_features,
    classify_kgpv,
    load_rules,
    load_dataset,
)
from kgpv.engine.adapters import table_cube, convert
from kgpv.engine.rules import classify_pvcz, pvcz_stressors
from kgpv.engine.ml import train_clusters, predict_clusters, save_model, load_model, evaluate_target

ROOT = Path(__file__).resolve().parents[1]
BASE = {
    "format": "csv",
    "frequency": "climatology",
    "variables": {
        "temperature": {"column": "temperature_c", "unit": "C"},
        "ghi": {"column": "ghi_kwh_m2", "unit": "kWh/m2"},
    },
}


def monthly():
    return pd.DataFrame(
        {
            "location_id": ["a"] * 12,
            "latitude": [20] * 12,
            "longitude": [15] * 12,
            "month": range(1, 13),
            "temperature_c": np.arange(12) + 10.0,
            "ghi_kwh_m2": [100.0] * 12,
        }
    )


def frow(**changes):
    r = {
        "ghi_annual_kwh_m2": 1500.0,
        "solar_weighted_temperature_c": 20.0,
        "weak_month_ratio": 0.6,
        "temperature_coldest_month_c": 5.0,
        "temperature_warmest_month_c": 30.0,
    }
    r.update(changes)
    return r


class RulesTests(unittest.TestCase):
    def test_solar_temperature_season_thermal_boundaries(self):
        for h, sun in [
            (1130, 0),
            (1130.001, 1),
            (1560, 1),
            (1560.001, 2),
            (2070, 2),
            (2070.001, 3),
        ]:
            for t, heat in [(9.999, 0), (10, 1), (25, 1), (25.001, 2)]:
                r = classify_features(
                    pd.DataFrame([frow(ghi_annual_kwh_m2=h, solar_weighted_temperature_c=t)]), "pv"
                ).iloc[0]
                self.assertEqual(r.zone_id, sun * 3 + heat + 1)
        for ratio, season in [(0.34999, 0), (0.35, 1), (0.74999, 1), (0.75, 2)]:
            for lo, hi, thermal in [(5, 30, 0), (4.99, 30, 1), (5, 30.01, 2), (4.99, 30.01, 3)]:
                f = pd.DataFrame(
                    [
                        frow(
                            weak_month_ratio=ratio,
                            temperature_coldest_month_c=lo,
                            temperature_warmest_month_c=hi,
                        )
                    ]
                )
                self.assertEqual(
                    classify_features(f, "hybrid").zone_id[0], season * 4 + thermal + 1
                )
                self.assertEqual(classify_features(f, "bess").zone_id[0], thermal + 1)

    def test_missing_month_and_battery_solar_independence(self):
        df = monthly()
        df.loc[2, "ghi_kwh_m2"] = np.nan
        f = extract_features(table_cube(df, BASE))
        self.assertEqual(f.ghi_months[0], 11)
        self.assertEqual(classify_features(f, "pv").zone_id[0], 0)
        self.assertGreater(classify_features(f, "bess").zone_id[0], 0)
        df.ghi_kwh_m2 = 0
        f = extract_features(table_cube(df, BASE))
        self.assertEqual(f.ghi_annual_kwh_m2[0], 0)
        self.assertTrue(np.isnan(f.weak_month_ratio[0]))
        self.assertEqual(classify_features(f, "pv").zone_id[0], 0)
        df.loc[0, "temperature_c"] = np.nan
        self.assertEqual(
            classify_features(extract_features(table_cube(df, BASE)), "bess").zone_id[0], 0
        )

    def test_kgpv_and_pvcz_inputs(self):
        cube = ClimateCube(
            ["one", "missing"],
            [20, -20],
            [30, 30],
            {
                "temperature": np.full((12, 2), 25.0),
                "precipitation": np.full((12, 2), 200.0),
                "ghi": np.column_stack([np.full(12, 200.0), np.full(12, np.nan)]),
            },
        )
        self.assertEqual(classify_kgpv(cube).zone_id.tolist(), [1, 0])
        np.testing.assert_equal(classify_pvcz([13.99, 14, np.nan], [2, 3, 2]), [1, 12, 0])
        stress = pvcz_stressors(np.full((24, 1), 30.0), np.full((24, 1), 5.0))
        self.assertAlmostEqual(stress["equivalent_module_temperature_c"][0], 30)
        with self.assertRaises(ValueError):
            pvcz_stressors(np.full((12, 1), 30.0), np.full((12, 1), 5.0), interval_hours=720)


class AdapterTests(unittest.TestCase):
    def test_units(self):
        self.assertAlmostEqual(convert(273.15, "temperature", "K", 1), 0)
        self.assertAlmostEqual(convert(68, "temperature", "F", 1), 20)
        self.assertEqual(convert(3.6e6, "ghi", "J/m2/day", 29 * 24), 29)
        self.assertEqual(convert(100, "ghi", "W/m2", 24), 2.4)
        self.assertEqual(convert(0.01, "precipitation", "m", 24), 10)
        self.assertEqual(convert(0.5, "relative_humidity", "fraction", 1), 50)
        with self.assertRaises(ValueError):
            convert(10, "ghi", "unknown", 1)

    def test_daily_hourly_missing_duplicates(self):
        for freq, step in [("daily", "D"), ("hourly", "h")]:
            ts = pd.date_range("2020-01-01", "2021-01-01", freq=step, inclusive="left")
            df = pd.DataFrame(
                {
                    "time": ts,
                    "latitude": 0.0,
                    "longitude": 0.0,
                    "temperature_c": 20.0,
                    "ghi_kwh_m2": 100.0,
                }
            )
            c = {
                **BASE,
                "frequency": freq,
                "variables": {**BASE["variables"], "ghi": {"column": "ghi_kwh_m2", "unit": "W/m2"}},
            }
            cube = table_cube(df, c)
            f = extract_features(cube)
            self.assertAlmostEqual(f.ghi_annual_kwh_m2[0], 878.4)
            self.assertEqual(cube.days[1, 0], 29)
            missing = extract_features(table_cube(df.drop(index=35), c))
            self.assertTrue(np.isnan(missing.ghi_annual_kwh_m2[0]))
            with self.assertRaises(ValueError):
                table_cube(pd.concat([df, df.iloc[:1]]), c)

    def test_csv_parquet_netcdf_zarr_geotiff_equivalence(self):
        import rasterio
        from rasterio.transform import from_origin

        with tempfile.TemporaryDirectory() as folder:
            p = Path(folder)
            df = monthly()
            df.to_csv(p / "a.csv", index=False)
            df.to_parquet(p / "a.parquet")
            a = extract_features(load_dataset(p / "a.csv", BASE))
            b = extract_features(load_dataset(p / "a.parquet", {**BASE, "format": "parquet"}))
            np.testing.assert_allclose(a.select_dtypes("number"), b.select_dtypes("number"))
            # Reversed coordinates and longitudes 0..360 must still preserve the data.
            t = np.broadcast_to(df.temperature_c.to_numpy()[:, None, None], (12, 2, 2)).copy()
            h = np.full_like(t, 100.0)
            t[:, 0, 0] += 3
            ds = xr.Dataset(
                {"T": (("month", "lat", "lon"), t), "H": (("month", "lat", "lon"), h)},
                coords={"month": range(1, 13), "lat": [19.5, 20.5], "lon": [359.5, 0.5]},
            )
            nc = {
                **BASE,
                "format": "netcdf",
                "variables": {
                    "temperature": {"name": "T", "unit": "C"},
                    "ghi": {"name": "H", "unit": "kWh/m2"},
                },
            }
            ds.to_netcdf(p / "a.nc")
            cube = load_dataset(p / "a.nc", nc)
            self.assertEqual(cube.latitude.tolist(), [20.5, 20.5, 19.5, 19.5])
            self.assertEqual(cube.longitude.tolist(), [-0.5, 0.5, -0.5, 0.5])
            np.testing.assert_allclose(cube.values["temperature"][:, 2], df.temperature_c + 3)
            ds.to_zarr(p / "a.zarr", zarr_format=2)
            z = load_dataset(p / "a.zarr", {**nc, "format": "zarr"})
            np.testing.assert_allclose(z.values["temperature"], cube.values["temperature"])
            for name, data in [("T", t[:, ::-1]), ("H", h[:, ::-1])]:
                with rasterio.open(
                    p / f"{name}.tif",
                    "w",
                    driver="GTiff",
                    width=2,
                    height=2,
                    count=12,
                    dtype="float32",
                    crs="EPSG:4326",
                    transform=from_origin(-1, 21, 1, 1),
                ) as dst:
                    dst.write(data.astype("float32"))
            gc = {
                **BASE,
                "format": "geotiff",
                "variables": {
                    "temperature": {"file": "T.tif", "unit": "C"},
                    "ghi": {"file": "H.tif", "unit": "kWh/m2"},
                },
            }
            g = load_dataset(p, gc)
            np.testing.assert_allclose(g.values["temperature"], cube.values["temperature"])
            self.assertIsNotNone(g.metadata["sha256"])
            with self.assertRaises(ValueError):
                load_dataset(p / "T.tif", gc)

    def test_cf_360_day_and_missing_year(self):
        with tempfile.TemporaryDirectory() as folder:
            p = Path(folder) / "cf.nc"
            time = xr.date_range(
                "2000-01-01", periods=24, freq="MS", calendar="360_day", use_cftime=True
            )
            ds = xr.Dataset(
                {
                    "T": (("time", "lat", "lon"), np.full((24, 1, 1), 293.15)),
                    "H": (("time", "lat", "lon"), np.full((24, 1, 1), 3.6e6)),
                },
                coords={"time": time, "lat": [0], "lon": [0]},
            )
            ds.to_netcdf(p)
            c = {
                "format": "netcdf",
                "frequency": "monthly",
                "variables": {
                    "temperature": {"name": "T", "unit": "K"},
                    "ghi": {"name": "H", "unit": "J/m2/day"},
                },
            }
            cube = load_dataset(p, c)
            self.assertEqual(cube.days[:, 0].tolist(), [30] * 12)
            self.assertAlmostEqual(extract_features(cube).ghi_annual_kwh_m2[0], 360)
            ds.isel(time=[i for i in range(24) if i != 13]).to_netcdf(p, mode="w")
            cube = load_dataset(p, c)
            self.assertTrue(np.isnan(extract_features(cube).ghi_annual_kwh_m2[0]))


class MLTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.f = (
            pd.read_parquet(ROOT / "examples/global-climate-features.parquet")
            .sample(700, random_state=11)
            .reset_index(drop=True)
        )

    def test_determinism_spatial_holdout_portable_model_missing_and_outliers(self):
        m, p = train_clusters(self.f, "pv", 4, 17, True)
        m2, p2 = train_clusters(self.f, "pv", 4, 17, True)
        self.assertEqual(m, m2)
        np.testing.assert_array_equal(p.zone_id.to_numpy(), p2.zone_id.to_numpy())
        self.assertEqual(m["diagnostics"]["overlapping_blocks"], 0)
        self.assertGreater(m["diagnostics"]["holdout_locations"], 0)
        x = self.f[m["features"]].to_numpy()
        z = (x - m["mean"]) / m["scale"]
        centres = np.array(m["centres"])
        expected = np.argmin(((z[:, None, :] - centres[None, :, :]) ** 2).sum(2), axis=1) + 1
        np.testing.assert_array_equal(p.zone_id.to_numpy(), expected)
        altered = self.f.iloc[:2].copy()
        altered.loc[0, m["features"][0]] = np.nan
        altered.loc[1, m["features"][0]] = 1e8
        r = predict_clusters(altered, m)
        self.assertEqual(r.zone_id.iloc[0], 0)
        self.assertEqual(r.status.iloc[1], "Outside typical training conditions")
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "model.json"
            save_model(m, path)
            self.assertEqual(load_model(path), m)

    def test_target_path_with_synthetic_test_fixture(self):
        # ONLY a software fixture; never written into the atlas or reported as validation.
        f = self.f.iloc[:150].copy()
        f["fixture_target"] = 0.7 * f.ghi_annual_kwh_m2 + 0.4 * f.solar_weighted_temperature_c
        r = evaluate_target(f, "fixture_target")
        self.assertEqual(len(r["folds"]), 5)
        self.assertTrue(all(np.isfinite(d["rmse"]) for d in r["folds"]))

    def test_python_javascript_parity(self):
        rows = []
        for h in [1130, 1130.001, 1560, 1560.001, 2070, 2070.001]:
            for t in [9.999, 10, 25, 25.001]:
                for ratio in [0.349, 0.35, 0.749, 0.75]:
                    rows.append(
                        frow(
                            ghi_annual_kwh_m2=h,
                            solar_weighted_temperature_c=t,
                            weak_month_ratio=ratio,
                        )
                    )
        rows.extend(
            [
                frow(temperature_coldest_month_c=4.99, temperature_warmest_month_c=30.01),
                frow(ghi_annual_kwh_m2=np.nan),
            ]
        )
        f = pd.DataFrame(rows)
        fixture = {
            "features": json.loads(f.to_json(orient="records")),
            "rules": load_rules(),
            "expected": {
                t: classify_features(f, t).zone_id.tolist() for t in ["pv", "hybrid", "bess"]
            },
            "csv": (ROOT / "examples/monthly-climate.csv").read_text(),
            "mapping": json.loads((ROOT / "examples/monthly-mapping.json").read_text()),
        }
        ef = extract_features(
            load_dataset(ROOT / "examples/monthly-climate.csv", fixture["mapping"])
        )
        fixture["example_features"] = json.loads(ef.to_json(orient="records", double_precision=15))
        fixture["models"] = {
            t: load_model(ROOT / f"atlas/models/{t}.json") for t in ["pv", "hybrid", "bess"]
        }
        fixture["predictions"] = {
            t: json.loads(predict_clusters(ef, m).to_json(orient="records", double_precision=15))
            for t, m in fixture["models"].items()
        }
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "fixture.json"
            path.write_text(json.dumps(fixture, allow_nan=False))
            subprocess.run(
                ["node", str(ROOT / "tests/test_energy_core.mjs"), str(path)],
                cwd=ROOT,
                check=True,
                text=True,
            )


if __name__ == "__main__":
    unittest.main()
