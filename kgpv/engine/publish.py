"""Add a computed categorical GeoTIFF to the existing static atlas catalogue."""

import json
import re
from pathlib import Path
from urllib.parse import urlparse
import numpy as np
import rasterio
from ..export import write_layer


def add_layer(raster, dist, layer_id, title, source, period=None):
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,79}", layer_id):
        raise ValueError("Use a short lowercase layer ID containing letters, numbers and hyphens")
    if not layer_id.startswith("custom-"):
        layer_id = "custom-" + layer_id
    if urlparse(source).scheme not in ["http", "https"]:
        raise ValueError("Supply an http(s) source or provenance URL")
    dist = Path(dist)
    cat_path = dist / "data/catalog.json"
    cat = json.loads(cat_path.read_text())
    with rasterio.open(raster) as ds:
        if ds.crs is None or ds.crs.to_epsg() != 4326 or ds.count != 1:
            raise ValueError("Use a single-band EPSG:4326 classification raster")
        a = ds.read(1, masked=True).astype(float).filled(np.nan)
        transform = ds.transform
        tags = ds.tags()
    finite = a[np.isfinite(a) & (a != 0)]
    if (
        not len(finite)
        or not np.equal(finite, finite.astype(int)).all()
        or finite.min() < 1
        or finite.max() > 255
    ):
        raise ValueError("Expected positive integer classes 1–255 with zero or NaN as no data")
    label_rows = json.loads(tags.get("labels", "[]"))
    if not label_rows:
        raise ValueError(
            "Raster needs labels metadata; use GeoTIFFs produced by pvclimate classify or predict"
        )
    labels = ["No data"] + [f"Class {i}" for i in range(1, int(finite.max()) + 1)]
    for row in label_rows:
        n = int(row["zone_id"])
        if 0 < n < len(labels):
            labels[n] = str(row["zone_name"])
    palette = [
        "#366b9b",
        "#69abb9",
        "#80b992",
        "#d7bd64",
        "#eb9852",
        "#b3554f",
        "#835b97",
        "#5c82b3",
        "#babca7",
        "#668c71",
        "#a99564",
        "#954f73",
    ]
    colors = ["#00000000"] + [palette[i % len(palette)] for i in range(len(labels) - 1)]
    layer = write_layer(
        dist,
        layer_id,
        title,
        a,
        "Your classifications",
        period or tags.get("period", "Not supplied"),
        "",
        "User-calculated climate classification. Consult its run manifest for input mapping and method.",
        source,
        labels=labels,
        colors=colors,
        limits=(1, len(labels) - 1),
        transform=transform,
        warning="User dataset and classification; check its stated period, resolution and validation.",
    )
    cat["layers"] = [l for l in cat["layers"] if l["id"] != layer_id] + [layer]
    ext_path = dist / "data/external-catalog.json"
    ext = json.loads(ext_path.read_text()) if ext_path.exists() else {}
    ext["layers"] = [l for l in ext.get("layers", []) if l["id"] != layer_id] + [layer]
    ext_path.write_text(json.dumps(ext, ensure_ascii=False, indent=2))
    cat_path.write_text(json.dumps(cat, ensure_ascii=False, indent=2))
    print(
        f"Added {layer_id}. Serve or republish {dist}; it appears under all scientific layers and in the overlay selector."
    )
