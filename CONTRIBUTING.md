# Contributing to EnergyClimates

Bug reports, provider adapters, reproducibility checks and new energy-climate
methods are welcome. Open an issue before a substantial new classification.

## Scientific contributions

A new method should include:

1. The energy-system question it answers and the relevant publication or rationale.
2. Required variables, units, calendar, time resolution and spatial coverage.
3. Exact thresholds, equality conventions, missing-data treatment and version.
4. A plain-language label alongside stable technical identifiers.
5. Independent validation where available, with limits stated explicitly.
6. Data provenance, licences and reproducible commands.

Keep published methods separate from experimental proposals. Do not rename a
new cluster analysis as a reproduction of another author's map without checking
its data, preprocessing, features and assignments. Geographic model evaluation
must avoid fitting transformations on the held-out blocks. Explain which metric
measures climate grouping and which actually measures energy-system value.

## Local setup

```bash
python -m venv .venv
# Activate the environment using your platform's standard command.
python -m pip install -e '.[dev]'
python -m unittest discover -s tests -v
node tests/test_map_math.cjs
```

Python 3.11+ and Node 20+ are used by CI. Add a test when fixing a numerical bug
or introducing an adapter. Do not add raw provider archives or credentials.
Generated browser `.bin` / `.png` layers are ignored because they can be rebuilt
from the native rasters. Update provenance when replacing scientific inputs.

The public API lives in `energyclimates/`; `kgpv/` retains the initial
implementation for compatibility. Existing CLI aliases must continue to work
unless a deprecation and migration path is documented.

By submitting code, you agree that your original contribution can be distributed
under the project's MIT licence. Dataset contributions must retain their actual
upstream terms; they are not automatically relicensed as MIT.
