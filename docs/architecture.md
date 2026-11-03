# Package architecture

One installable distribution, `energyclimates`, contains three public layers.
The layers reuse the existing scientific implementation; they do not duplicate it.

| Layer | Public namespace | Responsibility | Output |
| --- | --- | --- | --- |
| Input | `energyclimates.inputs` | Read declared local formats, normalize units/calendar, preserve source provenance; explicit provider downloads | `ClimateCube` |
| Methods | `energyclimates.methods` and `.methods.ml` | Features, classifications, ML training/prediction/evaluation | Tables, class IDs, model dictionaries |
| Analysis | `energyclimates.analysis` | Compose a study and export its evidence | `ClassificationStudy`, CSV/JSON/GeoJSON, eligible GeoTIFFs |

`ClimateCube` has 12 × N monthly arrays, N fixed geographic locations, declared
month lengths, period and metadata. Feature tables have one row per location.
Classification tables have one row per location and selected technology.

## Compatibility

Existing `from energyclimates import load_dataset, extract_features, classify_features`
imports remain valid, as do `energyclimates.ml`, `energyclimates.pvcz`, the `kgpv`
package and all three command names: `energyclimates`, `pvclimate`, `kgpv`.
`kgpv/engine/` remains the implementation shared by old and new namespaces.
The command line and new study API share the same export implementation.

## Repository responsibilities

| Path | Role |
| --- | --- |
| `energyclimates/inputs/` | Public input contract and synthetic wheel quickstart |
| `energyclimates/methods/` | Public scientific method APIs |
| `energyclimates/analysis/` | Applied workflow and study results |
| `kgpv/` | Existing implementation and compatibility interfaces |
| `configs/` | Explicit provider/format mapping examples |
| `examples/` | Real sample and reproducible scripts |
| `examples/gallery/` | Executable documentation examples |
| `docs/` | Sphinx/PyData guides, API, references and validation |
| `atlas/` | Existing standalone atlas, native rasters, provenance and models |
| `tests/` | Scientific, compatibility and distribution checks |
| `.github/workflows/` | Tests, wheel builds, documentation deployment and releases |

Large provider archives stay out of Git. The atlas is published alongside the
documentation at `atlas/index.html`; it is not bundled into the Python wheel.
The source distribution includes the repository examples and atlas for reproducibility.
