"""Physical environmental indicators; no calibrated loss or probability claims."""

import numpy as np

from energyclimates.inputs.environment import validate_coordinates

DAYS = np.array([31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31], dtype=float)


def _monthly(frame, column, *, maximum=None):
    values = np.stack(frame[column]).astype(float)
    if values.shape != (len(frame), 12):
        raise ValueError(f"{column} must have twelve January–December values per location")
    finite = np.isfinite(values)
    if (values[finite] < 0).any() or (maximum is not None and (values[finite] > maximum).any()):
        raise ValueError(f"{column} contains values outside its physical range")
    values[~finite] = np.nan
    return values, finite.all(axis=1), finite.sum(axis=1)


def _base(frame):
    validate_coordinates(frame)
    if frame.duplicated(["latitude", "longitude"]).any():
        raise ValueError("One row per geographic location is required")
    return frame[["latitude", "longitude"]].copy().reset_index(drop=True)


def _weights(days):
    weights = np.asarray(days, dtype=float)
    if weights.shape != (12,) or not np.isfinite(weights).all() or (weights <= 0).any():
        raise ValueError("days must contain twelve finite positive month lengths")
    return weights / weights.sum()


def soiling_screen(frame, *, deposition_velocity_m_s=0.001, tilt_degrees=30, days=DAYS):
    """Dust-only dry deposition potential from monthly dust in micrograms/m³.

    Mass flux = concentration × velocity × cos(tilt). Convert to g/m²/day.
    Velocity and tilt are scenario assumptions, not locally fitted parameters.
    No rain, cleaning, resuspension, non-dust particles or optical losses are
    modelled. This is NOT a soiling ratio or annual PV energy-loss estimate.
    All twelve monthly concentrations are required for annual and peak outputs.
    """
    if not np.isfinite(deposition_velocity_m_s) or deposition_velocity_m_s <= 0:
        raise ValueError("deposition velocity must be finite and positive")
    if not np.isfinite(tilt_degrees) or not 0 <= tilt_degrees <= 90:
        raise ValueError("tilt must be between 0 and 90 degrees")
    values, valid, count = _monthly(frame, "dust_ug_m3_months")
    flux = values * deposition_velocity_m_s * np.cos(np.deg2rad(tilt_degrees)) * 86400 / 1e6
    result = _base(frame)
    result["valid_months"] = count
    result["mean_dust_ug_m3"] = np.where(valid, values @ _weights(days), np.nan)
    result["dry_deposition_g_m2_day"] = np.where(valid, flux @ _weights(days), np.nan)
    result["peak_month_deposition_g_m2_day"] = np.where(valid, flux.max(axis=1), np.nan)
    return result


def snow_screen(frame, *, threshold_mm=1.0, days=DAYS):
    """Ground snow exposure from twelve monthly snow-water equivalents (mm).

    Count monthly MEANS at or above ``threshold_mm``; this is not snow-cover
    days or snow depth. Ground SWE does not estimate snow on modules or PV loss.
    Incomplete years keep all aggregate indicators missing.
    """
    if not np.isfinite(threshold_mm) or threshold_mm <= 0:
        raise ValueError("snow threshold must be finite and positive")
    values, valid, count = _monthly(frame, "swe_mm_months")
    result = _base(frame)
    result["valid_months"] = count
    result["mean_swe_mm"] = np.where(valid, values @ _weights(days), np.nan)
    result["peak_month_swe_mm"] = np.where(valid, values.max(axis=1), np.nan)
    result["months_mean_swe_above_threshold"] = np.where(
        valid, (values >= threshold_mm).sum(axis=1), np.nan
    )
    return result
