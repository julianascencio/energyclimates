"""
Screen three Chilean locations with RustGIS
===========================================

Compare annual global horizontal irradiation (GHI) in the 0.5° ERA5 atlas
cells containing Calama, Copiapó and Chillán, using the 1996–2022 climatology.
The markers locate the cities. The values describe grid cells and measure
incoming solar energy per horizontal area. Estimating PV generation would
also require a system design and a model of losses.

Run from a checkout with the ``rustgis`` and ``examples`` extras on Python 3.12+.
All rasters and the basemap are local.
"""

import json
from io import BytesIO
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.cm import ScalarMappable
from matplotlib.colors import Normalize

from energyclimates.analysis.rustgis import open_rustgis_atlas

start = Path(__file__).resolve().parent if "__file__" in globals() else Path.cwd()
root = next(p for p in (start, *start.parents) if (p / "atlas/data/catalog.json").is_file())
session = open_rustgis_atlas(root / "atlas", "ghi-1996-2022", "energy-pv")
cities = {"Calama": (-68.93, -22.46), "Copiapó": (-70.33, -27.37), "Chillán": (-72.10, -36.61)}

# Identify the raster before adding markers so the topmost layer is the GHI grid.
points = []
for city, (lon, lat) in cities.items():
    hit = session.run("identify", lon=lon, lat=lat)
    ghi = hit["attributes"]["Band 1"]
    print(f"{city}: {ghi} kWh/m²/year")
    points.append(
        {
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [lon, lat]},
            "properties": {"city": city, "caption": f"{city} · {ghi}"},
        }
    )

sites = session.add_geojson({"type": "FeatureCollection", "features": points}, name="Cities")
session.run("labels.field", layer=sites, field="caption")
session.run("labels.enable", layer=sites, on=True)
session.run("labels.style", layer=sites, size=13, bold=True, halo=True)
session.zoom_to((-76, -39, -65, -20))
png = session.to_png(width=820, height=720)

fig, ax = plt.subplots(figsize=(7.2, 6.4), layout="constrained")
ax.imshow(plt.imread(BytesIO(png), format="png"))
ax.set_axis_off()
ax.set_title("Annual horizontal irradiation in Chile\nERA5 · 1996–2022 · kWh/m²/year")
catalog = json.loads((root / "atlas/data/catalog.json").read_text(encoding="utf-8"))
ghi_layer = next(entry for entry in catalog["layers"] if entry["id"] == "ghi-1996-2022")
scale = ScalarMappable(norm=Normalize(ghi_layer["min"], ghi_layer["max"]), cmap="viridis")
fig.colorbar(scale, ax=ax, label="kWh/m²/year", extend="both", shrink=0.75)
plt.show()
