"""Global modeled hail indicators; daily fractions are not annual probability."""

import numpy as np

from energyclimates.inputs.environment import validate_coordinates


def hail_probability_screen(frame, *, n_days=365):
    """Summarize a complete year's sum of daily large-hail probability fractions.

    The sum is a modeled expected-day indicator by linearity of expectation,
    without assuming independent days. It can exceed one. Missing annual sums
    stay missing. No return period, event count or module damage is inferred.
    """
    if n_days not in (365, 366):
        raise ValueError("days must be 365 or 366 for a complete calendar year")
    validate_coordinates(frame)
    if frame.duplicated(["latitude", "longitude"]).any():
        raise ValueError("Duplicate geographic cells")
    values = frame["sum_daily_hail_probability"].to_numpy(dtype=float)
    valid = values[np.isfinite(values)]
    if np.isinf(values).any() or ((valid < 0) | (valid > n_days)).any():
        raise ValueError("Annual probability sum outside physical range [0, days]")
    result = frame[["latitude", "longitude"]].copy()
    result["modeled_hail_day_equivalents"] = values
    result["mean_daily_hail_probability"] = values / n_days
    return result
