# Installation

Python 3.11–3.13 are tested in CI. Use a virtual environment.

## Install the current repository

```bash
python -m pip install "energyclimates @ git+https://github.com/julianascencio/energyclimates.git"
```

The redesigned API is available after its pull request is merged; before then,
install its branch or a wheel downloaded from that PR's test artifacts.
Do not assume a PyPI release exists just because packaging is configured.

## Install a wheel

```bash
python -m pip install ./energyclimates-0.2.0-py3-none-any.whl
python -m energyclimates --help
```

After a maintainer publishes the release, the index install is
`python -m pip install energyclimates`. The wheel contains the `energyclimates`
and compatibility `kgpv` packages, canonical rules JSON and licence notices.
It does not contain the atlas rasters, trained atlas models or large feature table.

## Work on the project

```bash
git clone https://github.com/julianascencio/energyclimates.git
cd energyclimates
python -m pip install -e '.[dev,docs]'
```

The `examples` extra adds Matplotlib. The `docs` extra adds Sphinx, the PyData theme,
MyST, Sphinx Design and the executable gallery. Existing runtime dependencies are
retained so current provider, raster and ML commands continue to work.

Node.js 20+ is required for browser parity tests; it is not a Python runtime dependency.
