"""Physical environmental indicators; no calibrated loss or probability claims."""

import numpy as np
import pandas as pd

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


def storm_report_grid(
    frame, *, event_types, start_year, end_year, resolution=1.0, minimum_hail_mm=None
):
    """Count distinct local report dates and events in occupied geographic bins.

    Denominator is the explicitly declared inclusive record period, never the
    years containing events. Caller must establish archive coverage. A bin with
    no selected report is absent, NOT a measured zero hazard. All days with a
    matching event at its BEGIN location count once per bin, regardless of report
    multiplicity. Hail size is a reported maximum, not a return-period estimate.
    """
    validate_coordinates(frame)
    if frame.event_id.isna().any() or frame.event_id.duplicated().any():
        raise ValueError("Event IDs must be unique and present")
    if not event_types or not set(event_types) <= {"Hail", "Thunderstorm Wind", "Lightning"}:
        raise ValueError("Unsupported event types")
    if (
        not isinstance(start_year, (int, np.integer))
        or not isinstance(end_year, (int, np.integer))
        or not 1900 <= start_year <= end_year
    ):
        raise ValueError("Declare an ordered inclusive year range")
    if (
        not np.isfinite(resolution)
        or not 0 < resolution <= 90
        or not np.isclose(180 / resolution, round(180 / resolution))
    ):
        raise ValueError("Resolution must be positive and divide 180 degrees")
    if minimum_hail_mm is not None and (
        set(event_types) != {"Hail"} or not np.isfinite(minimum_hail_mm) or minimum_hail_mm <= 0
    ):
        raise ValueError("A positive hail threshold applies only to Hail reports")
    dates = pd.to_datetime(frame.date, errors="raise")
    if dates.isna().any():
        raise ValueError("Storm report dates must be present")
    hail_size = frame.loc[frame.event_type.eq("Hail"), "hail_diameter_mm"].to_numpy(dtype=float)
    if np.isinf(hail_size).any() or (hail_size[np.isfinite(hail_size)] < 0).any():
        raise ValueError("Hail diameters must be nonnegative or missing")
    selected = frame.loc[
        dates.dt.year.between(start_year, end_year) & frame.event_type.isin(event_types)
    ].copy()
    selected["date"] = dates.loc[selected.index].dt.normalize()
    if minimum_hail_mm is not None:
        selected = selected[selected.hail_diameter_mm >= minimum_hail_mm].copy()
    # East/north boundary points belong to the last cell; +180 wraps to -180.
    selected["longitude"] = (
        np.floor(((selected.longitude + 180) % 360) / resolution) * resolution
        - 180
        + resolution / 2
    )
    selected["latitude"] = (
        np.minimum(np.floor((selected.latitude + 90) / resolution), 180 / resolution - 1)
        * resolution
        - 90
        + resolution / 2
    )
    result = selected.groupby(["latitude", "longitude"], as_index=False).agg(
        reported_events=("event_id", "nunique"),
        reported_days=("date", "nunique"),
        maximum_reported_hail_mm=("hail_diameter_mm", "max"),
    )
    if "Hail" not in event_types:
        result = result.drop(columns="maximum_reported_hail_mm")
    result["reported_days_per_year"] = result.reported_days / (end_year - start_year + 1)
    return result
