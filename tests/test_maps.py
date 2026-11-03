"""Check geographic alignment and nodata without requiring plotting extras."""

import numpy as np
import pandas as pd
import pytest

from energyclimates.analysis.maps import regular_grid


def test_grid_orientation_missing_cells_and_dateline():
    cells = pd.DataFrame(
        {
            "latitude": [89.75, -89.75, 0.25, 0.25],
            "longitude": [-179.75, 179.75, -0.25, 0.25],
            "value": [1, 2, 3, np.nan],
        }
    )
    grid = regular_grid(cells, "value")
    assert grid.shape == (360, 720)
    assert grid[0, 0] == 1
    assert grid[-1, -1] == 2
    assert grid[179, 359] == 3
    assert np.isnan(grid[179, 360])
    assert np.isfinite(grid).sum() == 3
    np.testing.assert_equal(grid, regular_grid(cells.iloc[::-1], "value"))


@pytest.mark.parametrize(
    "latitude,longitude,message",
    [
        (0, 0.25, "cell centres"),
        (0.25, 180.25, "outside"),
        (np.nan, 0.25, "finite"),
    ],
)
def test_invalid_coordinates_are_not_silently_snapped(latitude, longitude, message):
    frame = pd.DataFrame({"latitude": [latitude], "longitude": [longitude], "v": [1]})
    with pytest.raises(ValueError, match=message):
        regular_grid(frame, "v")


def test_duplicate_cells_are_not_silently_overwritten():
    frame = pd.DataFrame({"latitude": [0.25, 0.25], "longitude": [0.25, 0.25], "v": [1, 2]})
    with pytest.raises(ValueError, match="exactly one"):
        regular_grid(frame, "v")


@pytest.mark.parametrize("resolution", [0, -1, np.nan, 0.7, 0.001])
def test_invalid_or_excessive_resolution(resolution):
    frame = pd.DataFrame(columns=["latitude", "longitude", "v"])
    with pytest.raises(ValueError, match="resolution|grid"):
        regular_grid(frame, "v", resolution=resolution)
