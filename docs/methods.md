# Methods

The method layer operates on normalized cubes or feature tables. It does not
choose a provider, write a study, or publish an atlas.

| Method | API | Required evidence | Status |
| --- | --- | --- | --- |
| Climate features | `extract_features(cube)` | Complete monthly values for each derived signal | Implemented |
| PV / hybrid / BESS profiles | `classify_features(features, technology)` | Temperature; PV/hybrid also require GHI | Experimental rules |
| KGPV | `classify_kgpv(cube)` | Monthly temperature, precipitation, GHI | Published method, explicit implementation conventions |
| PVCZ | `classify_pvcz(module_temperature, specific_humidity)` | Equivalent module temperature and specific humidity | Published scheme, explicit boundary convention |
| PVCZ stressors | `pvcz_stressors(...)` | Subdaily inputs; see API | Engineering stressor calculations |
| ML groups | `methods.ml.train_clusters`, `predict_clusters` | Climate features; sufficient geographic blocks for training | Experimental, independent of published Delft/PVZones assignments |
| Target evaluation | `methods.ml.evaluate_target` | Independently measured or consistently simulated target | Spatial cross-validation; no operational target bundled |

Temperature and GHI features do not establish module or battery-cell temperature.
In particular, monthly ambient temperature is not a substitute for PVCZ equivalent
module temperature. KGPV has six temperature/precipitation groups and a fixed
24-to-12 merge; it does not implement all 30 Köppen–Geiger subtypes.

The [engine guide](ENGINE_GUIDE.md) gives exact threshold/equality rules,
aggregation conventions, geographic holdout design and model serialization.
The [reference catalogue](references.md) distinguishes published methods from
experimental profiles. IDs are local to a scheme; do not compare their numbers
as if they were a common physical scale.

`all` in the analysis/CLI API means PV, hybrid and BESS. KGPV is selected separately.
Missing required months yield `zone_id=0` and an insufficient-data status.
