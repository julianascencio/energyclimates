# Runnable climate maps

Twelve map studies execute from bundled public-data snapshots. The six climate
studies share 67,420 CRU TS 4.10 + ERA5/NCAR cells, 1996–2022, at 0.5° resolution.
Six [environmental studies](environment-maps.md) add soiling, snow, thunderstorms,
hail, vegetation and population, each with its own period, grid and coverage.
The gallery shows figures and numeric results produced during the docs build.
Every page includes Python and notebook downloads. All examples run offline
after installation, without API credentials, map tiles or boundary downloads.

{download}`Download all executed map results (ZIP) <_generated/map-results.zip>`

The archive contains twelve figures (25 map panels), PNG and SVG versions, sixteen CSV
tables, printed results, runnable example sources, and per-study JSON manifests.
Each manifest records source-file and code SHA-256 hashes, package/dependency
versions, units, period, grid resolution and output checksums. Data attribution
and licence notices are included. Figures are rendered again on every docs build;
they are not manually supplied screenshots.

| Runnable study | Visible result | Numeric output |
| --- | --- | --- |
| {doc}`Global resource <auto_examples/plot_07_map_resource>` | Annual GHI and solar-weighted air temperature | 67,420 rows with both features |
| {doc}`Solar seasonality <auto_examples/plot_08_map_seasonality>` | Weakest-month daily GHI and weak-month ratio | 67,420 rows with both features |
| {doc}`PV, hybrid and BESS profiles <auto_examples/plot_09_map_profiles>` | Three classifications recomputed from the versioned rules | Three tables of 67,420 classifications |
| {doc}`Chile and neighbouring cells <auto_examples/plot_10_map_chile>` | Annual GHI and weak-month availability | 1,382 cells in the selected rectangle |
| {doc}`Europe and neighbouring cells <auto_examples/plot_11_map_europe_storage>` | Weakest-month GHI and BESS thermal profiles | Features and classifications for 5,595 cells |
| {doc}`Global ML groups <auto_examples/plot_12_map_ml>` | PV clusters and assignment separation | 67,420 predictions, distances, separation and status |

The six additional examples, input contracts and interpretation guidance are in
[Environmental risk and exposure maps](environment-maps.md).

## Run and save results

From a repository checkout, install the plotting extra:

```bash
python -m pip install -e '.[examples]'
python examples/gallery/plot_10_map_chile.py
```

Run all twelve studies headlessly and retain the complete result bundle:

```bash
python scripts/run_map_gallery.py --output results/map-gallery \
  --archive results/map-gallery.zip
```

Each study gets its own directory with `figure-1.png`, `figure-1.svg`, CSVs,
`results.txt`, source and `manifest.json`. Matching generated files are replaced
on a rerun; unrelated files are not added to the archive. The example data and
models live in the repository/source distribution, not in the Python wheel.
Downloaded notebooks should be run inside that checkout with the package installed.

To rebuild the gallery pages and the downloadable archive together:

```bash
python -m pip install -e '.[docs]'
python scripts/build_docs.py
```

## Reuse the map functions

`energyclimates.analysis.maps` supplies `regular_grid`, `plot_grid_map` and
`plot_category_map`. Pass a table with cell-centred `latitude`, `longitude` and
the desired value column. Declare its true cell size using `resolution`; these
helpers do not interpolate station data or infer fine spatial resolution.
Classification labels and colours are indexed by category ID, preserving their
meaning between regional and global views. ID zero remains unclassified.

The grid is anchored at longitude −180° and latitude 90°. Duplicate cells,
off-grid coordinates and invalid coordinates are rejected rather than silently
shifted or averaged. Missing cells stay missing. Matplotlib is optional and is
only loaded when a plotting function is called.

## Interpretation and sources

The figures use longitude/latitude (equirectangular) displays, not equal-area
maps. Grey means no supplied value or an unclassified cell; it is not a coastline
dataset. Regional views select rectangles and include neighbouring countries.
Cell counts are counts, not area-weighted shares or national statistics.

GHI is horizontal irradiation, not PV electricity production. Temperature is
ambient monthly-mean air temperature. The 27-year common period is not a 30-year
climate normal. Neither these climate features nor the experimental rules/model
establish yield, storage sizing, battery safety, lifetime or economic return.
ML separation is a feature-space distance metric, not confidence, and the global
prediction example includes the model's training domain.

The bundled feature table and its metadata are produced by
`scripts/build_energy_atlas.py`; the full source-file provenance is retained in
`atlas/data/energy-provenance.json`. The map studies reuse this snapshot and
existing algorithms; they do not claim to regenerate raw climate inputs.
See [references](references.md), [validation](validation.md) and the repository's
[data licences](https://github.com/julianascencio/energyclimates/blob/main/DATA_LICENSES.md).
