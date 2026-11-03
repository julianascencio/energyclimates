# Environmental risk and exposure maps

Runnable studies connect public-data inputs, reusable methods and analysis exports.
The bundled snapshots run offline. Source periods, grids and geographic coverage
remain explicit; these are screening indicators, not calibrated hazard probabilities,
engineering loads or PV-loss predictions.

```{toctree}
:maxdepth: 1

environment-soiling
environment-snow
environment-thunderstorm
environment-hail
```

| Layer and runnable example | Input | Method and analysis output |
| --- | --- | --- |
| {doc}`Soiling <auto_examples/plot_13_map_soiling>` | NASA MERRA-2 GMI modeled monthly surface dust, 2019; sampled land cells | Day-weighted dust concentration and an explicit dry-deposition scenario, g/m²/day |
| {doc}`Snow <auto_examples/plot_14_map_snow>` | NOAA NCEP/NCAR Reanalysis 1 ground snow-water equivalent, 1981–2010 | Months with monthly-mean SWE ≥1 mm, mean and peak monthly SWE |
| {doc}`Thunderstorms <auto_examples/plot_15_map_thunderstorm>` | NOAA NCEI U.S. Thunderstorm Wind and Lightning reports, 2020–2024 | Distinct local report dates/year in 1° bins; separate wind and lightning maps |
| {doc}`Hail <auto_examples/plot_16_map_hail>` | NOAA NCEI U.S. hail reports and diameters, 2020–2024 | Report days/year for hail ≥25.4 mm and largest reported diameter per 1° bin |

## Input contracts

`energyclimates.inputs.environment.read_environment(path)` loads a Parquet
snapshot, verifies its SHA-256 against the adjacent `.metadata.json` and attaches
provenance to the DataFrame. Every input includes `latitude` and `longitude` in
WGS84 degrees. Monthly arrays contain January through December in that order.

| Study | Required additional input columns | Units / semantics |
| --- | --- | --- |
| Soiling | `dust_ug_m3_months` | Twelve monthly surface-dust means, µg/m³; not column AOD or total PM10 |
| Snow | `swe_mm_months` | Twelve monthly-mean ground SWE values, mm water equivalent |
| Storms / hail | `event_id`, `event_type`, `date`, `hail_diameter_mm` | Unique report IDs, local calendar dates, hail diameter in mm; size missing for wind/lightning |

For your own normalized table, pass a DataFrame directly to `run_environment`.
Attach source, period and unit declarations to `frame.attrs`. Invalid coordinates,
duplicate location rows in gridded indicators, duplicate event IDs, invalid
parameters and negative physical quantities are rejected. Missing monthly
values remain missing: all twelve are required for annual/seasonal indicators.

`storm_events(frame)` adapts the original NOAA details CSV columns. It keeps only
Hail, Thunderstorm Wind and Lightning, converts hail inches ×25.4, and counts
excluded records with missing/invalid dates or coordinates, including 0,0
sentinels. Wind magnitudes are not interpreted as hail sizes. Input metadata
records archive URLs, checksums, selected counts and exclusions.


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
