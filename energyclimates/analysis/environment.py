"""Connect environmental inputs and methods to auditable study outputs."""

import json
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from energyclimates.inputs.environment import read_environment
from energyclimates.methods.environment import (
    DAYS,
    population_screen,
    snow_screen,
    soiling_screen,
    storm_report_grid,
    vegetation_screen,
)

from energyclimates.methods.hail import hail_probability_screen

METHODS = {
    "soiling": (
        soiling_screen,
        {"deposition_velocity_m_s": 0.001, "tilt_degrees": 30, "days": DAYS.tolist()},
        "Dust-only dry deposition scenario; no rain, cleaning or PV loss model.",
    ),
    "snow": (
        snow_screen,
        {"threshold_mm": 1.0, "days": DAYS.tolist()},
        "Ground monthly-mean SWE exposure, not module snow cover or PV loss.",
    ),
    "vegetation": (
        vegetation_screen,
        {"days": DAYS.tolist()},
        "Model leaf-area index, not land cover, tree height or shading.",
    ),
    "population": (
        population_screen,
        {},
        "Census-based density; not population totals or electricity demand.",
    ),
    "thunderstorm": (
        storm_report_grid,
        {"event_types": ["Thunderstorm Wind", "Lightning"], "resolution": 1.0},
        "Reported damaging/significant U.S. events, not all thunderstorms or probability.",
    ),
    "global_hail": (
        hail_probability_screen,
        {"n_days": 365},
        "Single modeled year of large hail >2.5 cm; not annual probability, climatology or PV damage.",
    ),
    "hail": (
        storm_report_grid,
        {"event_types": ["Hail"], "resolution": 1.0, "minimum_hail_mm": 25.4},
        "Reported U.S. hail >=25.4 mm; reporting bias, no return-period or module-damage model.",
    ),
}


OUTPUT_UNITS = {
    "latitude": "degrees_north",
    "longitude": "degrees_east",
    "valid_months": "months",
    "mean_dust_ug_m3": "µg/m³",
    "dry_deposition_g_m2_day": "g/m²/day",
    "peak_month_deposition_g_m2_day": "g/m²/day",
    "mean_swe_mm": "mm water equivalent",
    "peak_month_swe_mm": "mm water equivalent",
    "months_mean_swe_above_threshold": "months",
    "mean_lai": "m² leaf/m² ground",
    "seasonal_lai_range": "m² leaf/m² ground",
    "population_density_km2": "people/km²",
    "log10_population_density_plus_one": "log10(1 + density in people/km²)",
    "reported_events": "reports",
    "reported_days": "distinct local calendar dates",
    "reported_days_per_year": "distinct local calendar dates/year",
    "maximum_reported_hail_mm": "mm",
    "modeled_hail_day_equivalents": "sum of daily probability fractions (days)",
    "mean_daily_hail_probability": "fraction",
}


@dataclass
class EnvironmentStudy:
    """Computed indicator table and a source/assumption manifest."""

    indicators: pd.DataFrame
    manifest: dict

    def write(self, output):
        """Save indicators.csv and manifest.json in a dedicated output folder."""
        folder = Path(output)
        folder.mkdir(parents=True, exist_ok=True)
        self.indicators.to_csv(folder / "indicators.csv", index=False)
        (folder / "manifest.json").write_text(json.dumps(self.manifest, indent=2, allow_nan=False))
        return folder


def run_environment(source, kind, **parameters):
    """Run a registered study on a snapshot path or normalized DataFrame.

    Available ``kind`` names are listed in ``METHODS``.
    Storm studies require explicit ``start_year`` and ``end_year``. Inputs must
    match the units documented by the selected method. In-memory inputs should
    carry provenance in ``attrs``; no provenance is invented when it is absent.
    """
    if kind not in METHODS:
        raise ValueError(f"Unknown environmental study: {kind}")
    frame = source.copy() if isinstance(source, pd.DataFrame) else read_environment(source)
    function, defaults, limitations = METHODS[kind]
    options = {**defaults, **parameters}
    if "days" in options:
        options["days"] = list(map(float, options["days"]))
    indicators = function(frame, **options)
    manifest = {
        "schema": "energyclimates-environment-v1",
        "kind": kind,
        "input": frame.attrs,
        "method": function.__name__,
        "parameters": options,
        "output_units": {column: OUTPUT_UNITS[column] for column in indicators.columns},
        "missing_data": "Incomplete monthly or daily series stay missing; unreported event cells stay absent.",
        "limitations": limitations,
    }
    indicators.attrs = manifest
    return EnvironmentStudy(indicators, manifest)
