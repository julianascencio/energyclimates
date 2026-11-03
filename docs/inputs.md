# Inputs

```python
from energyclimates.inputs import ClimateCube, load_dataset, table_cube, example_climate
```

`load_dataset(path, mapping)` reads local files. `table_cube(frame, mapping)`
normalizes an in-memory Pandas table. `example_climate()` returns explicitly
synthetic data, independent of the checkout and network.

| Quantity | Canonical cube unit | Meaning |
| --- | --- | --- |
| `temperature` | °C | Monthly mean ambient air temperature |
| `ghi` | kWh/m²/month | Monthly irradiation energy, not instantaneous irradiance |
| `precipitation` | mm/month | Monthly accumulated precipitation |
| `relative_humidity` | % | Monthly mean relative humidity |
| `wind_speed` | m/s | Monthly mean wind speed |

Each array has shape `(12, number_of_locations)` in January–December order.
Latitude/longitude are geographic degrees; cube longitudes are −180…180.
Optional `days` records the month lengths for the actual calendar/period.

## Local formats and provenance

CSV/Parquet use one interval per location. NetCDF/Zarr require 1D geographic
latitude and longitude axes and explicit selection of extra dimensions.
GeoTIFF uses one twelve-band monthly file per variable. See the
[full mapping and calendar contract](ENGINE_GUIDE.md#bring-data-from-any-provider).

File adapters hash the source and preserve mappings, period and missing-data
policy in cube metadata and subsequent feature tables. In-memory inputs must
supply their own provenance. Missing values are never silently filled.

## Providers

The input namespace also exposes the existing `fetch_baseline`, `fetch_climate`,
`fetch_era5_ncar` and `fetch_era5_cds` functions. Calls can download substantial
archives. They run only when explicitly invoked, and CDS access requires your
own credentials and accepted dataset terms. Importing the package downloads nothing.
The earlier `kgpv fetch` commands remain available; consult `kgpv --help`.

Use [DATA_LICENSES.md](https://github.com/julianascencio/energyclimates/blob/main/DATA_LICENSES.md)
for source-specific terms. A data provider's licence is separate from the code's MIT licence.

## Environmental inputs

See the [environmental map workflows](environment-maps.md) for available studies,
input contracts, units, scientific limits and offline runnable examples.
