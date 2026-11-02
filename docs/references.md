# References and attribution

Cite the software revision and the actual methods and datasets used in a study.
The original project references and provider terms remain in
[ATLAS_REFERENCE](ATLAS_REFERENCE.md) and
[DATA_LICENSES.md](https://github.com/julianascencio/energyclimates/blob/main/DATA_LICENSES.md).

| Source | Relationship to this repository |
| --- | --- |
| [KGPV (2019), Solar Energy](https://doi.org/10.1016/j.solener.2019.08.072) | Implemented climate/irradiation classification; boundary and original-label issues documented |
| [Todd Karin's PVCZ](https://github.com/toddkarin/pvcz) | Published layers, import checksums, temperature/humidity and stressor utilities |
| [Delft ML classification (2025)](https://doi.org/10.1016/j.renene.2025.123685) | Referenced background; geographic assignments are not bundled |
| [PVZones (2025)](https://doi.org/10.1016/j.apenergy.2025.126192) | Referenced background; atlas ML models are not a reproduction |
| CRU TS, GPCC, ERA5/NCAR and Copernicus CDS | Input data; exact periods, provenance and terms in the atlas reference and data licences |

Experimental PV/hybrid/BESS cutoffs are repository assumptions. Their portable
JSON definitions and fitted ML models do not establish independent scientific
validation or operational value.

## Creator and development

Created and maintained by **ASVA Consulting**.
[asvaconsulting.com](https://asvaconsulting.com) ·
[contacto@asvaconsulting.com](mailto:contacto@asvaconsulting.com).
Original contributor attribution and separate third-party/data terms are preserved.

AI assistance is used for code, documentation, examples and tests under developer
direction. Specific literature and datasets define the evidence base. Validation
is incomplete and errors may remain; check assumptions and results against the
cited sources. Tests of software behavior are not independent validation of
energy-system performance.

## Documentation and packaging

The site follows the Sphinx/PyData format used in OrbitalPV and Energy Data Insights.
Release tooling follows the [Python Packaging User Guide](https://packaging.python.org/en/latest/tutorials/packaging-projects/)
and [PyPI Trusted Publishing](https://docs.pypi.org/trusted-publishers/using-a-publisher/).
