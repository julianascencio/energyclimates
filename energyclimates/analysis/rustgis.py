"""Build portable RustGIS projects from the EnergyClimates atlas catalogue."""

from __future__ import annotations

import base64
import csv
import hashlib
import json
from io import StringIO
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import rustgis


def _add_table(session, name, fields, rows):
    stream = StringIO(newline="")
    writer = csv.writer(stream)
    writer.writerow(fields)
    writer.writerows(rows)
    session.run("layer.addDataText", fileName=f"{name}.csv", name=name, text=stream.getvalue())


def open_rustgis_atlas(atlas: str | Path, *layer_ids: str) -> rustgis.Session:
    """Open selected catalogue layers as embedded GeoTIFFs in a native RustGIS session.

    Pass the atlas directory containing ``data/catalog.json`` and zero or more
    layer IDs in display order. The catalogue default is used when IDs are
    omitted. The first layer is visible. Other layers can be toggled by ID.

    The project includes an Atlas layers table with provenance and GeoTIFF
    checksums, plus a Class codes table for categorical layers. Call
    ``session.save("climate.rgis")`` to keep a portable project or
    ``session.to_png("map.png")`` to render the current view.
    """
    try:
        import rustgis
    except ModuleNotFoundError as exc:
        if exc.name != "rustgis":
            raise
        raise ImportError(
            "RustGIS requires Python 3.12+ and the EnergyClimates rustgis extra. "
            "From the checkout run: python -m pip install -e '.[rustgis]'"
        ) from exc

    root = Path(atlas).resolve()
    catalog = json.loads((root / "data/catalog.json").read_text(encoding="utf-8"))
    layers = {entry["id"]: entry for entry in catalog["layers"]}
    selected = layer_ids or (catalog["default"],)
    if len(set(selected)) != len(selected):
        raise ValueError("Request each atlas layer ID only once.")
    unknown = [key for key in selected if key not in layers]
    if unknown:
        raise ValueError(
            f"Unknown atlas layer {', '.join(unknown)}. Available: {', '.join(layers)}"
        )

    session = rustgis.Session()
    metadata = []
    codes = []
    fields = (
        "title",
        "period",
        "units",
        "source",
        "description",
        "warning",
        "license",
        "source_commit",
    )
    # RustGIS inserts each new layer on top. Load bottom first to keep the requested order.
    for key in reversed(selected):
        entry = layers[key]
        path = (root / entry["download"].lstrip("/")).resolve()
        if not path.is_relative_to(root) or path.suffix.lower() not in {".tif", ".tiff"}:
            raise ValueError(f"Expected a local atlas GeoTIFF for {key}: {entry['download']}")
        data = path.read_bytes()
        try:
            session.run(
                "layer.addDataBytes",
                fileName=path.name,
                name=key,
                data=base64.b64encode(data).decode("ascii"),
                zoom=False,
            )
            labels = entry.get("labels")
            if labels:
                session.run("raster.symbology", layer=key, type="unique", ramp="viridis")
                codes.extend((key, i, label) for i, label in enumerate(labels) if i and label)
            else:
                session.run("raster.symbology", layer=key, type="stretch", ramp="viridis")
                session.run(
                    "raster.stretch", layer=key, type="custom", min=entry["min"], max=entry["max"]
                )
            session.run("raster.resampling", layer=key, type="nearest")
            session[key].visible = key == selected[0]
        except rustgis.RustGISError as exc:
            raise ValueError(
                f"RustGIS could not load atlas layer {key} ({path.name}): {exc}"
            ) from exc
        metadata.append((key, *(entry.get(f) for f in fields), hashlib.sha256(data).hexdigest()))

    _add_table(session, "Atlas layers", ("layer_id", *fields, "sha256"), reversed(metadata))
    if codes:
        _add_table(session, "Class codes", ("layer_id", "code", "label"), codes)
    session.zoom_to(selected[0])
    return session
