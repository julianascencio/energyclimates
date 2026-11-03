# Environmental risk and exposure maps

Six runnable studies extend the gallery with **soiling, snow, thunderstorms,
hail, vegetation and population**. Each page executes the input → method →
analysis workflow and displays the resulting maps and numeric summaries.
The bundled public-data snapshots run **offline**, with no accounts or downloads.

These layers have different periods, grids and geographic coverage. They are
screening indicators with physical units, not calibrated hazard probabilities,
engineering design loads or PV-loss predictions. Do not combine them into a
single risk score without a separately validated model.

| Layer and runnable example | Input | Method and analysis output |
| --- | --- | --- |
| {doc}`Soiling <auto_examples/plot_13_map_soiling>` | NASA MERRA-2 GMI modeled monthly surface dust, 2019; sampled land cells | Day-weighted dust concentration and an explicit dry-deposition scenario, g/m²/day |
| {doc}`Snow <auto_examples/plot_14_map_snow>` | NOAA NCEP/NCAR Reanalysis 1 ground snow-water equivalent, 1981–2010 | Months with monthly-mean SWE ≥1 mm, mean and peak monthly SWE |
| {doc}`Thunderstorms <auto_examples/plot_15_map_thunderstorm>` | NOAA NCEI U.S. Thunderstorm Wind and Lightning reports, 2020–2024 | Distinct local report dates/year in 1° bins; separate wind and lightning maps |
| {doc}`Hail <auto_examples/plot_16_map_hail>` | NOAA NCEI U.S. hail reports and diameters, 2020–2024 | Report days/year for hail ≥25.4 mm and largest reported diameter per 1° bin |
| {doc}`Vegetation <auto_examples/plot_17_map_vegetation>` | NASA MERRA-2 GMI model monthly leaf-area index, 2019 | Day-weighted mean LAI and seasonal range, m² leaf/m² ground |
| {doc}`Population <auto_examples/plot_18_map_population>` | CIESIN / NASA SEDAC GPWv4.11 2020 density via Stanford's mirror | 0.5° arithmetic density preview and log10(1+density), preserving real zeros |

{download}`Download executed maps, CSV results and provenance (ZIP) <_generated/map-results.zip>`

## Input contracts

`energyclimates.inputs.environment.read_environment(path)` loads a Parquet
snapshot, verifies its SHA-256 against the adjacent `.metadata.json` and attaches
provenance to the DataFrame. Every input includes `latitude` and `longitude` in
WGS84 degrees. Monthly arrays contain January through December in that order.

| Study | Required additional input columns | Units / semantics |
| --- | --- | --- |
| Soiling | `dust_ug_m3_months` | Twelve monthly surface-dust means, µg/m³; not column AOD or total PM10 |
| Snow | `swe_mm_months` | Twelve monthly-mean ground SWE values, mm water equivalent |
| Vegetation | `lai_months` | Twelve monthly-mean LAI values, m² leaf/m² ground |
| Storms / hail | `event_id`, `event_type`, `date`, `hail_diameter_mm` | Unique report IDs, local calendar dates, hail diameter in mm; size missing for wind/lightning |
| Population | `population_density_km2` | People/km²; missing is distinct from zero |

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

## Methods and their limits

### Soiling: dust deposition potential

For each monthly concentration $C$ in µg/m³, deposition velocity $v$ in m/s and
panel tilt $\theta$ measured from horizontal, the illustrative dry mass flux is

$$F = C\,v\,\cos(\theta)\,86400/10^6 \quad [\mathrm{g\,m^{-2}\,day^{-1}}].$$

The defaults are **v = 0.001 m/s** and **tilt = 30°**. They are explicit scenario
assumptions, not locally calibrated constants or a published universal soiling
model. Annual means use month-length weights; the gallery uses the actual 2019
month lengths. Changing velocity scales the output linearly.

This omits rain washing, scheduled cleaning, resuspension, adhesion, particle-size
distribution, sea salt, soot and pollen. It does not turn deposition into optical
losses, annual retained mass or PV energy loss. Actual soiling-loss analysis needs
site-specific particulate and rainfall time series, cleaning records, module
geometry and a validated loss model. MERRA-2 **GMI** is a replay simulation;
unlike MERRA-2 itself, its aerosol optical depth is not constrained by observations.

### Snow: modeled ground exposure

`mean_swe_mm` is a day-weighted mean; `peak_month_swe_mm` is the maximum of the
monthly means. `months_mean_swe_above_threshold` counts monthly means **≥1 mm**,
with a configurable positive threshold. A month above that threshold is not a
count of snow-covered days. One kg/m² of SWE equals one mm liquid-water equivalent,
not one mm physical snow depth.

The 94×192 Gaussian source grid is drawn with its native latitude coordinates,
using midpoint display edges, without inventing a regular 0.5° grid. Only source
months with all 30 contributing years are retained. A representative non-leap
year weights the monthly climatology. The native static land mask excludes ocean and sea-ice cells; large ice-sheet values are retained and the peak panel uses a log scale.
Terrain, module snow cover, sliding, heating, tilt and energy loss are outside
this method.

### Thunderstorms and hail: reported-event exposure

The method uses the event's **BEGIN** point and local calendar date, bins the
point into an explicitly declared grid and counts unique dates. Multiple events
on the same day in one cell count as one report day. Divide by the declared
inclusive record length, **five years**, including years without a matching
report. Event counts remain available separately.

Thunderstorm wind and lightning are analyzed separately. The hail example
selects reported diameters **≥25.4 mm**, rejects missing diameter from this
threshold selection, and retains each occupied cell's largest reported size.
The example threshold is a screening choice, not a module qualification rating.

NOAA Storm Events is a U.S. inventory of significant/damaging weather reports,
with population, observation and reporting biases. It is not a worldwide storm
climatology. The maps display the contiguous-U.S. rectangle; the CSVs retain
qualifying reports elsewhere in the U.S. **Unreported cells stay absent** and
are not evidence of zero hazard. No annual probability, return period, lightning
flash density, hail kinetic energy or PV damage is inferred. Records cover only
2020–2024 and should not be treated as a long-term climate normal.

### Vegetation: model leaf area

Compute the month-length-weighted annual mean LAI and the difference between
maximum and minimum monthly LAI. The 2019 NASA GMI snapshot selects every fourth
native latitude/longitude centre, yielding **2°×2.5° sample spacing** from a
0.5°×0.625° model. These are samples, not block means. At least one valid LAI
month establishes the example's model-land mask; incomplete series retain
missing output indicators. Complete source axes are supplied to plotting so
missing cells cannot stretch their neighbours.

LAI is not NDVI, land-cover class, biomass, canopy height or tree-clearance
information. Local shade analysis needs height, geometry and finer observations.
A single modeled year cannot establish current vegetation conditions or trends.

### Population: density preview

GPW density divides source population counts by source land area. The bundled
preview takes an **arithmetic mean of valid native densities** in each 60×60
pixel block (0.5°). It reads original raster pixels, not unknown precomputed
overviews. Zero remains zero; a block with no valid pixels stays missing.
The second panel uses `log10(1 + density)` so zero can be displayed.

This is deliberately a density-screening preview, **not a count-conserving or
land-area-weighted population aggregate**. Do not sum densities or multiply by
whole geographic cell area to obtain people; coastal and partial-land cells
make that incorrect. For totals, aggregate the original count and land-area
rasters consistently. The 2020 census-based estimate is not current population,
electricity consumption or a demand forecast.

## Run, analyze and export

Install from a repository checkout; the example snapshots are distributed in
the repository/source archive, not the Python wheel:

```bash
python -m pip install -e '.[examples]'
python examples/gallery/plot_13_map_soiling.py
python examples/gallery/plot_14_map_snow.py
python scripts/run_map_gallery.py --output results/map-gallery \
  --archive results/map-gallery.zip
```

Reusable analysis, with explicit assumptions saved beside numeric results:

```python
from energyclimates.analysis.environment import run_environment

soiling = run_environment(
    "examples/environment/gmi-2019.parquet", "soiling",
    deposition_velocity_m_s=0.001, tilt_degrees=20,
)
soiling.write("results/soiling")

hail = run_environment(
    "examples/environment/storm-reports-2020-2024.parquet", "hail",
    start_year=2020, end_year=2024, resolution=1.0, minimum_hail_mm=50.8,
)
hail.write("results/hail")
```

`EnvironmentStudy.indicators` is the result table. `manifest` retains the input
metadata, method, actual parameters and interpretation limits. `write()` saves
`indicators.csv` and `manifest.json`. The gallery runner additionally exports
PNG/SVG figures, runnable example source, CSVs, printed statistics, source/code
hashes and per-example grid metadata. Colour-bar extensions identify values above
fixed display limits; the CSV values are never clipped. A log scale cannot display
zero; the snow peak panel therefore masks zero SWE on that panel only.

## Sources and refreshing snapshots

- [NASA MERRA-2 GMI project and model description](https://acd-ext.gsfc.nasa.gov/Projects/GEOSCCM/MERRA2GMI/)
  and [NCCS public OPeNDAP collections](https://opendap.nccs.nasa.gov/dods/merra2_gmi).
  Inputs use `dusmass` from `tavgM_2d_aer_Nx` and `lai` from `tavgM_2d_lnd_Nx`.
- [NOAA PSL NCEP/NCAR derived data catalog](https://psl.noaa.gov/thredds/catalog/Datasets/ncep.reanalysis.derived/surface_gauss/catalog.html):
  `weasd.sfc.mon.1981-2010.ltm.nc` with the matching NCEP static land mask.
- [NOAA Storm Events bulk archive](https://www.ncei.noaa.gov/pub/data/swdi/stormevents/csvfiles/)
  and [field definitions](https://www.ncei.noaa.gov/pub/data/swdi/stormevents/csvfiles/Storm-Data-Bulk-csv-Format.pdf).
  Exact annual revision filenames are pinned in the builder and metadata.
- [CIESIN GPWv4.11 population density DOI](https://doi.org/10.7927/H49C6VHW),
  [NASA dataset description](https://data.nasa.gov/dataset/gridded-population-of-the-world-version-4-gpwv4-population-density-revision-11)
  and [Stanford-distributed source GeoTIFF](https://data.naturalcapitalalliance.stanford.edu/download/global/ciesin-nasa-gpw-grdi/ciesen_nasa_gpw_v4_population_density_2020.tif).

Optional upstream refresh (approximately 410 MB downloaded/cached):

```bash
python scripts/build_environment_inputs.py
```

This command is explicit and never runs during gallery, tests or docs builds.
It caches raw provider files in `raw/environment`, normalizes units and writes
four compact Parquet snapshots with metadata in `examples/environment`. Existing
cached files are reused; use a new `--cache` directory to refetch. Inspect metadata
and checksums before committing refreshed inputs: upstream archives can be
revised or removed. The script records the exact retrieved bytes, transformations,
units and grid, rather than claiming that a future download is byte-identical.
See the repository [data notices](https://github.com/julianascencio/energyclimates/blob/main/DATA_LICENSES.md).
