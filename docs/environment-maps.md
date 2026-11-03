# Environmental risk and exposure maps

Runnable studies connect public-data inputs, reusable methods and analysis exports.
The bundled snapshots run offline. Source periods, grids and geographic coverage
remain explicit; these are screening indicators, not calibrated hazard probabilities,
engineering loads or PV-loss predictions.

```{toctree}
:maxdepth: 1

environment-soiling
```

| Layer and runnable example | Input | Method and analysis output |
| --- | --- | --- |
| {doc}`Soiling <auto_examples/plot_13_map_soiling>` | NASA MERRA-2 GMI modeled monthly surface dust, 2019; sampled land cells | Day-weighted dust concentration and an explicit dry-deposition scenario, g/m²/day |

## Input contracts

`energyclimates.inputs.environment.read_environment(path)` loads a Parquet
snapshot, verifies its SHA-256 against the adjacent `.metadata.json` and attaches
provenance to the DataFrame. Every input includes `latitude` and `longitude` in
WGS84 degrees. Monthly arrays contain January through December in that order.

| Study | Required additional input columns | Units / semantics |
| --- | --- | --- |
| Soiling | `dust_ug_m3_months` | Twelve monthly surface-dust means, µg/m³; not column AOD or total PM10 |

For your own normalized table, pass a DataFrame directly to `run_environment`.
Attach source, period and unit declarations to `frame.attrs`. Invalid coordinates,
duplicate location rows in gridded indicators, duplicate event IDs, invalid
parameters and negative physical quantities are rejected. Missing monthly
values remain missing: all twelve are required for annual/seasonal indicators.



## Batch export

{download}`Download executed maps, CSV results and provenance (ZIP) <_generated/map-results.zip>`

```bash
python scripts/run_map_gallery.py --output results/map-gallery \
  --archive results/map-gallery.zip
```

Each study exports PNG/SVG figures, numerical CSVs, source code and checksummed
manifests. The snapshots ship in the source archive, not the wheel. Missing cells
stay missing; display limits never clip CSV values. Native source axes preserve
grid gaps and dateline cells without interpolation. See each map's page for units,
limitations and its independently selectable input-refresh command.
