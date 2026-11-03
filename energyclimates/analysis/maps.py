"""Offline maps of existing regular geographic cells, without interpolation.

Plotting requires the ``examples`` extra. Matplotlib is imported only by the
plotting functions; grid reconstruction works with the base installation.
"""

import numpy as np


def regular_grid(frame, column, *, resolution=0.5):
    """Return a north-up global array from cell-centred longitude/latitude rows.

    The grid is anchored at (-180, 90) in EPSG:4326. ``resolution`` is the cell
    size in degrees, not an inferred spatial accuracy. Absent cells and missing
    values remain NaN. Duplicate cells, nonfinite coordinates and coordinates
    that do not lie on this grid raise ValueError instead of being aggregated or
    shifted. The returned extent is always (-180, 180, -90, 90).
    """
    if not np.isfinite(resolution) or not 0 < resolution <= 180:
        raise ValueError("resolution must be finite and between 0 and 180 degrees")
    shape = np.array([180 / resolution, 360 / resolution])
    if not np.allclose(shape, np.rint(shape), rtol=0, atol=1e-8):
        raise ValueError("resolution must divide both 180 and 360 degrees")
    if np.prod(shape) > 10_000_000:
        raise ValueError("Requested global grid exceeds ten million cells")
    height, width = np.rint(shape).astype(int)
    latitude = frame["latitude"].to_numpy(dtype=float)
    longitude = frame["longitude"].to_numpy(dtype=float)
    if not np.isfinite(latitude).all() or not np.isfinite(longitude).all():
        raise ValueError("Coordinates must be finite")
    row = (90 - latitude) / resolution - 0.5
    col = (longitude + 180) / resolution - 0.5
    if not (
        np.allclose(row, np.rint(row), rtol=0, atol=1e-6)
        and np.allclose(col, np.rint(col), rtol=0, atol=1e-6)
    ):
        raise ValueError("Coordinates must be cell centres on the declared global grid")
    row, col = np.rint(row).astype(int), np.rint(col).astype(int)
    if ((row < 0) | (row >= height) | (col < 0) | (col >= width)).any():
        raise ValueError("Coordinates lie outside the geographic grid")
    indices = row * width + col
    if len(np.unique(indices)) != len(indices):
        raise ValueError("Each geographic cell must have exactly one row")
    values = frame[column].to_numpy(dtype=float, na_value=np.nan)
    grid = np.full((height, width), np.nan)
    grid[row, col] = np.where(np.isfinite(values), values, np.nan)
    return grid


def plot_grid_map(
    frame,
    column,
    *,
    ax=None,
    resolution=0.5,
    bounds=(-180, 180, -60, 85),
    title=None,
    cmap="viridis",
    norm=None,
    vmin=None,
    vmax=None,
):
    """Plot existing cells and return the Matplotlib image for a colour bar.

    ``bounds`` is (west, east, south, north) without antimeridian wrapping.
    Coordinates use an equirectangular display, not an equal-area projection.
    The background means no supplied value, not zero or a land/ocean mask.
    No basemap, boundary files or network requests are used.
    """
    import matplotlib.pyplot as plt

    west, east, south, north = bounds
    if not (-180 <= west < east <= 180 and -90 <= south < north <= 90):
        raise ValueError("bounds must be ordered geographic west, east, south, north")
    if ax is None:
        _, ax = plt.subplots(figsize=(11, 5), layout="constrained")
    palette = plt.get_cmap(cmap).copy()
    palette.set_bad("#e8eef2")
    image = ax.imshow(
        np.ma.masked_invalid(regular_grid(frame, column, resolution=resolution)),
        extent=(-180, 180, -90, 90),
        origin="upper",
        interpolation="nearest",
        cmap=palette,
        norm=norm,
        vmin=vmin,
        vmax=vmax,
        rasterized=True,
    )
    ax.set(
        xlim=(west, east),
        ylim=(south, north),
        xlabel="Longitude (°)",
        ylabel="Latitude (°)",
        title=title or column,
    )
    ax.grid(color="#576879", alpha=0.15, linewidth=0.5)
    ax.tick_params(labelsize=9)
    for spine in ax.spines.values():
        spine.set_color("#a5b4c0")
    return image


def plot_category_map(frame, *, labels, colors, ax=None, column="zone_id", **kwargs):
    """Plot integer IDs using stable label/colour lists indexed by category ID.

    ID 0 and missing values are unclassified. The legend shows only categories
    present inside the plotted bounds; each ID keeps its colour across regions.
    Remaining keyword arguments are forwarded to :func:`plot_grid_map`.
    """
    from matplotlib.colors import BoundaryNorm, ListedColormap
    from matplotlib.patches import Patch

    if len(labels) != len(colors) or len(labels) < 2:
        raise ValueError("Provide matching labels and colors including ID 0")
    values = frame[column].to_numpy(dtype=float, na_value=np.nan)
    valid = values[np.isfinite(values)]
    if ((valid < 0) | (valid >= len(labels)) | (valid != np.rint(valid))).any():
        raise ValueError("Category IDs must be integers covered by labels and colors")
    mapped = frame.copy()
    mapped[column] = np.where(values == 0, np.nan, values)
    image = plot_grid_map(
        mapped,
        column,
        ax=ax,
        cmap=ListedColormap(colors),
        norm=BoundaryNorm(np.arange(len(labels) + 1) - 0.5, len(labels)),
        **kwargs,
    )
    ax = image.axes
    west, east = ax.get_xlim()
    south, north = ax.get_ylim()
    visible = frame.longitude.between(west, east) & frame.latitude.between(south, north)
    present = sorted(set(values[visible & np.isfinite(values)]) - {0})
    if present:
        ax.legend(
            handles=[Patch(facecolor=colors[int(i)], label=labels[int(i)]) for i in present],
            loc="center left",
            bbox_to_anchor=(1.01, 0.5),
            frameon=False,
            fontsize=9,
        )
    return image


def plot_rectilinear_map(
    frame,
    column,
    *,
    latitude,
    longitude,
    ax=None,
    bounds=(-180, 180, -60, 85),
    title=None,
    cmap="viridis",
    norm=None,
    vmin=None,
    vmax=None,
):
    """Plot declared rectilinear centres, including a Gaussian latitude axis.

    Coordinates must be unique, strictly increasing and within WGS84 limits.
    Midpoint edges are inferred and clipped at the poles/dateline. Supply the
    COMPLETE source axes, including missing rows/columns, to avoid stretching
    across gaps. Sparse values stay missing; no interpolation is performed.
    Sampled grids describe sampling footprints, not spatially averaged cells.
    """
    import matplotlib.pyplot as plt

    from energyclimates.inputs.environment import validate_coordinates

    validate_coordinates(frame)
    lat = np.asarray(latitude, dtype=float)
    lon = np.asarray(longitude, dtype=float)
    for name, values, limit in [("latitude", lat, 90), ("longitude", lon, 180)]:
        if (
            values.ndim != 1
            or len(values) < 2
            or not np.isfinite(values).all()
            or (np.diff(values) <= 0).any()
            or (np.abs(values) > limit).any()
        ):
            raise ValueError(f"{name} must be a finite, increasing geographic axis")
    if len(lat) * len(lon) > 10_000_000:
        raise ValueError("Requested grid exceeds ten million cells")
    if frame.duplicated(["latitude", "longitude"]).any():
        raise ValueError("Duplicate geographic cells")
    rows = np.searchsorted(lat, frame.latitude.to_numpy())
    cols = np.searchsorted(lon, frame.longitude.to_numpy())
    if (rows >= len(lat)).any() or (cols >= len(lon)).any():
        raise ValueError("Coordinates are not on the supplied axes")
    if not np.allclose(lat[rows], frame.latitude, atol=1e-7, rtol=0) or not np.allclose(
        lon[cols], frame.longitude, atol=1e-7, rtol=0
    ):
        raise ValueError("Coordinates are not on the supplied axes")

    def edges(values, limit):
        return np.clip(
            np.r_[
                values[0] - (values[1] - values[0]) / 2,
                (values[:-1] + values[1:]) / 2,
                values[-1] + (values[-1] - values[-2]) / 2,
            ],
            -limit,
            limit,
        )

    west, east, south, north = bounds
    if not (-180 <= west < east <= 180 and -90 <= south < north <= 90):
        raise ValueError("Invalid geographic bounds")
    grid = np.full((len(lat), len(lon)), np.nan)
    grid[rows, cols] = frame[column].to_numpy(dtype=float)
    # A global axis centred on -180 needs its wrapped half-cell at +180 too.
    spacing = np.diff(lon)
    if (
        np.allclose(spacing, spacing[0])
        and np.isclose(lon[-1] - lon[0] + spacing[0], 360)
        and np.isclose(lon[0], -180)
    ):
        lon = np.r_[lon, 180.0]
        grid = np.column_stack([grid, grid[:, 0]])
    if ax is None:
        _, ax = plt.subplots(figsize=(11, 5), layout="constrained")
    palette = plt.get_cmap(cmap).copy()
    palette.set_bad("#e8eef2")
    image = ax.pcolormesh(
        edges(lon, 180),
        edges(lat, 90),
        np.ma.masked_invalid(grid),
        cmap=palette,
        norm=norm,
        vmin=vmin,
        vmax=vmax,
        shading="flat",
        rasterized=True,
    )
    ax.set(
        xlim=(west, east),
        ylim=(south, north),
        xlabel="Longitude (°)",
        ylabel="Latitude (°)",
        title=title or column,
        aspect="equal",
        facecolor="#e8eef2",
    )
    ax.grid(color="#576879", alpha=0.15, linewidth=0.5)
    return image
