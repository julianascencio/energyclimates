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
