# Interactive atlas

The existing atlas is published alongside this documentation. It retains its
scientific layers, two-map comparisons, location inspection and browser-local
monthly CSV calculator.

```{raw} html
<p><a class="sd-btn sd-btn-primary" href="atlas/index.html">Open the interactive atlas →</a></p>
```

The current bundle has 49 layers. Rebuild its browser PNG/binary representations
from the native GeoTIFFs and serve it locally:

```bash
energyclimates prepare-website --dist atlas
python -m http.server 8000 --directory atlas
```

Open `http://localhost:8000`. The basemap requires internet access; bundled
scientific layers and browser CSV processing run locally. The atlas uses relative
asset URLs so it can also run under the GitHub Pages project subpath.

Build the complete documentation and atlas together:

```bash
python scripts/build_docs.py
python -m http.server 8000 --directory docs/_build/html
```

See the [atlas reference](ATLAS_REFERENCE.md) for periods, sources, the suspected
original KGPV label-order issue and interpretation limits. The rebuild does not
retrieve or refresh upstream climate data.

## Open the atlas in RustGIS

From the repository checkout on Python 3.12 or later, select catalogue layer IDs
in the order you want them to appear. The first layer is visible on opening.
Omitting the IDs selects the atlas default.

```bash
python -m pip install -e '.[rustgis]'
energyclimates rustgis ghi-1996-2022 energy-pv --atlas atlas --output results/solar.rgis
```

Open `results/solar.rgis` in RustGIS. The project embeds the source GeoTIFFs, so
you can move it or open it offline. The **Atlas layers** table records the source,
period, units, warnings and SHA-256 checksum for each layer. **Class codes**
maps the numeric categories to the atlas labels. Colours use RustGIS symbology.
Continuous layers use the atlas display limits. Identify reads the underlying
cell even when its value lies outside those display limits.

The same layers are available to Python for site inspection and rendering:

```python
from energyclimates.analysis.rustgis import open_rustgis_atlas

session = open_rustgis_atlas("atlas", "ghi-1996-2022", "energy-pv")
pixel = session.run("identify", lon=-70.33, lat=-27.37)  # Copiapó, Chile
print(pixel["attributes"]["Band 1"])  # annual GHI, kWh/m²/year
session.to_png("solar.png", width=1200, height=800)
```

Available IDs are listed under `layers[].id` in `atlas/data/catalog.json`.
An installed wheel can use the atlas directory from a separate checkout.
See the [Chile screening example](auto_examples/plot_19_rustgis_atlas)
and the [RustGIS Python guide](https://rustgis.app/python/).
