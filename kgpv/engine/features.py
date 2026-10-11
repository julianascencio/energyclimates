"""A small, explicit data contract: twelve monthly climate values per location."""

from dataclasses import dataclass, field
import numpy as np
import pandas as pd

DAYS = np.array([31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31], dtype=float)
FEATURE_UNITS = {
    "ghi_annual_kwh_m2": "kWh/m²/year",
    "temperature_mean_c": "°C",
    "temperature_coldest_month_c": "°C",
    "temperature_warmest_month_c": "°C",
    "solar_weighted_temperature_c": "°C",
    "weak_month_ratio": "fraction",
    "ghi_daily_weakest_month": "kWh/m²/day",
    "solar_seasonality_cv": "dimensionless",
    "precipitation_annual_mm": "mm/year",
    "relative_humidity_mean_pct": "%",
    "wind_speed_mean_m_s": "m/s",
}


@dataclass
class ClimateCube:
    ids: np.ndarray
    latitude: np.ndarray
    longitude: np.ndarray
    values: dict
    days: np.ndarray = field(default_factory=lambda: DAYS.copy())
    period: str = "User-supplied climatology"
    metadata: dict = field(default_factory=dict)

    def __post_init__(self):
        self.ids = np.asarray(self.ids, dtype=str)
        n = len(self.ids)
        if n == 0 or len(set(self.ids)) != n:
            raise ValueError("Location IDs must be nonempty and unique")
        self.latitude = np.asarray(self.latitude, float)
        self.longitude = np.asarray(self.longitude, float)
        for a, limit, name in [(self.latitude, 90, "latitude"), (self.longitude, 180, "longitude")]:
            if a.shape != (n,) or not np.isfinite(a).all() or (abs(a) > limit).any():
                raise ValueError(f"Invalid {name}")
        self.days = np.asarray(self.days, float)
        if self.days.shape == (12,):
            self.days = np.broadcast_to(self.days[:, None], (12, n)).copy()
        if self.days.shape != (12, n) or not np.isfinite(self.days).all() or (self.days <= 0).any():
            raise ValueError("Expected twelve positive month lengths")
        if not self.values:
            raise ValueError("No climate variables supplied")
        for key, a in list(self.values.items()):
            a = np.asarray(a, float)
            if a.shape != (12, n):
                raise ValueError(f"{key}: expected shape (12, {n})")
            if np.isinf(a).any():
                raise ValueError(f"{key}: infinite values are invalid")
            if key == "temperature":
                valid = (a >= -100) & (a <= 70)
            elif key == "relative_humidity":
                valid = (a >= 0) & (a <= 100)
            else:
                valid = a >= 0
            if (np.isfinite(a) & ~valid).any():
                raise ValueError(f"{key}: values outside supported physical range")
            self.values[key] = a

    def get(self, name):
        return self.values.get(name, np.full((12, len(self.ids)), np.nan))


def extract_features(cube):
    """Missing months stay missing. No nearest-land substitution or imputation."""
    t, h, p = cube.get("temperature"), cube.get("ghi"), cube.get("precipitation")
    tf = np.isfinite(t).all(0)
    hf = np.isfinite(h).all(0) & (h >= 0).all(0)
    with np.errstate(invalid="ignore", divide="ignore"):
        annual = h.sum(0)
        daily = h / cube.days
        mean_daily = annual / cube.days.sum(0)
        d = {
            "location_id": cube.ids,
            "latitude": cube.latitude,
            "longitude": cube.longitude,
            "temperature_months": np.isfinite(t).sum(0),
            "ghi_months": np.isfinite(h).sum(0),
            "temperature_mean_c": np.where(tf, t.mean(0), np.nan),
            "temperature_coldest_month_c": np.where(tf, t.min(0), np.nan),
            "temperature_warmest_month_c": np.where(tf, t.max(0), np.nan),
            "ghi_annual_kwh_m2": np.where(hf, annual, np.nan),
            "solar_weighted_temperature_c": np.where(
                tf & hf & (annual > 0), (t * h).sum(0) / annual, np.nan
            ),
            "weak_month_ratio": np.where(hf & (annual > 0), daily.min(0) / mean_daily, np.nan),
            "ghi_daily_weakest_month": np.where(hf, daily.min(0), np.nan),
            "solar_seasonality_cv": np.where(
                hf & (annual > 0), daily.std(0) / daily.mean(0), np.nan
            ),
            "precipitation_annual_mm": np.where(
                np.isfinite(p).all(0) & (p >= 0).all(0), p.sum(0), np.nan
            ),
        }
        for key, out in [
            ("relative_humidity", "relative_humidity_mean_pct"),
            ("wind_speed", "wind_speed_mean_m_s"),
        ]:
            a = cube.get(key)
            d[out] = np.where(
                np.isfinite(a).all(0), (a * cube.days).sum(0) / cube.days.sum(0), np.nan
            )
    f = pd.DataFrame(d)
    f.attrs.update(
        {
            "period": cube.period,
            "metadata": cube.metadata,
            "feature_schema": "monthly-climate-v1",
            "units": FEATURE_UNITS,
        }
    )
    return f
