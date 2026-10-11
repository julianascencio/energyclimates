# Validation of the delivered research edition

Executed 12 September 2026.

- Six scientific tests passed: temperature and dryness boundaries, classification
  precedence, hemisphere seasonality, 24-to-12 class mapping, missing/duplicate
  periods, and leap-year conversion of ERA5 mean daily energy to monthly totals.
- The 1996–2022 computation required all 324 calendar months from each provider.
- The 1996–2025 climate refresh required all 360 months for temperature and rain.
- Both runs have 67,183 valid temperature–precipitation cells on the 0.5° grid.
- All 20 exported layers passed full-array GeoTIFF/binary equality and valid-cell
  count checks. Class land-share weights sum to 100% within rounding tolerance.
- JavaScript syntax was checked with Node. All referenced local assets and
  download entrypoints were checked after packaging.
- The full world raster was visually inspected for geographic orientation and
  gross classification errors; this is not independent scientific validation.

Illustrative recalculated cells (1996–2022, coordinates requested rather than
cell centres; rounded values):

| Latitude | Longitude | KGPV | GHI kWh/m²/year | Air temperature °C | Rain mm/year |
|---:|---:|---|---:|---:|---:|
| -23.5 | -69.5 | BK | 2641 | 12.7 | 7 |
| 28.3 | -16.5 | CK | 2073 | 17.9 | 341 |
| 46 | 14 | DM | 1322 | 9.3 | 1544 |
| 2 | 20 | AH | 1918 | 25.5 | 1784 |
| 65 | 25 | EL | 899 | 3.1 | 545 |

Limitations: no authenticated CDS retrieval, browser interaction testing or
WebMCP runtime validation was performed. The WebMCP hooks are optional and
feature-detected. The original deposited labels have an unresolved ordering
issue, so no classification-change statistics are published. The 2025 full
irradiation refresh, future scenario rasters and new PV-performance simulations
are not included.

## PVCZ and comparison update · 13 September 2026

- Added 18 layers from Todd Karin's PVCZ v0.2, pinned to upstream commit
  `aa89fab8d1d66f46f4ea8575e2452aa75a927535`. Data period: 2010–2018.
- Verified all three input SHA-256 checksums. Loaded numeric NPZ arrays with
  `allow_pickle=False`; no upstream pickle or code was executed.
- Matched all 230,742 rounded CSV coordinate rows to their exact metadata
  positions. The 52,975 duplicate rounded coordinate pairs were not merged.
- Compared every source row against every one of the 18 exported native grids.
  Preserved the zero-based source's first class through the documented +1
  raster encoding. All 37 occupied combined PVCZ classes remain available.
- Checked ASCE missing-value masks separately from the special wind category.
- All 38 rasters passed binary/GeoTIFF equality, native transform, cell count,
  category range, palette size, area-share and PNG-size checks.
- Six existing scientific tests passed. Node unit checks passed for 0.25° point
  sampling, absent cells, longitude wrapping, scaled swipe geometry, and removal
  of clipping when changing to blend mode.
- JavaScript syntax, local links, unique element IDs, JS element references,
  and ARIA control targets passed source checks. Browser interaction testing
  and WebMCP runtime validation were not performed.
- Verified KGPV citations in both ML papers. The Delft supplement could not be
  retrieved from the publisher; no georeferenced PVZones deposit was located.
  These research entries are explicitly marked as lacking imported rasters.

## Plain-language energy profiles and ML · 13 September 2026

- Generated 11 additional layers from actual CRU TS 4.10 and ERA5/NCAR monthly
  climate inputs for 1996–2022: three rule profiles, three independent ML maps
  and five climate-driver layers. The catalogue now contains 49 layers.
- Used 67,420 complete temperature/irradiation land cells. Annual GHI and mean
  temperature agree with the existing atlas within float32 precision. The
  canonical monthly cache is float32, giving the same fresh/cached computation.
- Sixteen Python scientific/software tests passed. Coverage includes exact
  solar/temperature/seasonality boundaries, missing data, battery independence
  from sunlight, KGPV and PVCZ stressor inputs, unit conversions, duplicate and
  missing hourly/daily observations, leap years, all five input formats,
  longitude/latitude reordering and a CF 360-day calendar.
- Python and JavaScript agree on 98 rule-boundary/missing-data cases for all
  three systems, the six real example feature vectors and all three models'
  assignments, distance measures and novelty flags.
- Repeated ML training with identical data, configuration and seed produced
  identical model JSON. Geographic holdout blocks have no overlap with training
  blocks. The scaler is fitted on training blocks for holdout evaluation.
- The full feature-table CLI training exactly reproduced the shipped battery
  model. Real example classify/predict commands produced the expected 18 rule
  profiles and six ML predictions, CSVs, GIS points and manifests.
- A real four-cell subset passed CLI feature classification, labelled GeoTIFF
  export, atlas catalogue insertion and exact reconstruction of browser binary
  and PNG assets from the GeoTIFF. Temporary test layers were not added to the
  delivered catalogue.
- The optional outcome-evaluation path passed a synthetic software fixture.
  This is not independent PV-yield or battery-performance validation. No real
  operational outcomes were supplied or invented.
- All 49 GeoTIFFs/binaries passed value, transform, count, category, palette,
  class-share and PNG dimension checks. Regional-grid sampling and existing
  comparison clipping passed Node unit checks.
- HTML parsed without errors; unique element IDs, view targets, JS element
  references and ARIA targets passed source checks. No browser interaction or
  WebMCP runtime testing was performed in this update.

The new temperature/seasonality thresholds and requested cluster counts remain
provisional. Monthly air temperature cannot establish daily extremes, module
or cell temperature, battery safety, storage size, lifetime, cooling load or
financial value. The website marks the new profiles and ML groups experimental.
The current 27-year common period is not a 30-year climate normal. The full
2025 KGPV still awaits newer ERA5 inputs through configured CDS access. Published
Delft and PVZones assignments remain unavailable and are not replaced by these
independent atlas ML models.

## EnergyClimates public package · 11 October 2026

- The `energyclimates` public API, module entry point and command were installed
  from the repository in Python 3.12. The earlier commands remain compatible.
- All 16 Python tests passed again, including Python/JavaScript parity, with the
  new package and atlas directory layout. The Node map-math checks passed.
- The documented classification command and public-API example produced 18
  profiles for the six real sample locations; the example also ran ML prediction.
- Rebuilt all 49 browser layers from the included native GeoTIFFs and verified
  full-array equality, transforms, labels, counts and PNG dimensions.
- Built the Python source distribution and wheel successfully. The wheel includes
  the canonical rules JSON and separate software/data licence notices.
- Added GitHub Actions for Python 3.11, 3.12 and 3.13. This is configuration, not
  a claim that those remote jobs have already passed.

The source datasets, periods and experimental scientific status are unchanged.
This packaging check did not repeat raw-provider downloads or browser interaction
tests, and it is not independent validation of energy-system performance.
