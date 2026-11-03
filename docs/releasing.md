# Building and releasing

## Local verification

```bash
python -m pip install -e '.[dev,docs]'
python -m pytest
node tests/test_map_math.cjs
python -m build
python -m twine check dist/*
python scripts/check_distribution.py dist
python scripts/build_docs.py
```

`check_distribution.py` checks both archives, creates an isolated temporary target
for the wheel, then runs public APIs and every CLI alias outside the checkout.
Runtime dependencies come from the active environment; package code comes only
from the built wheel. CI also builds from the sdist through `python -m build`.

## GitHub Pages

The `Documentation` workflow builds on pull requests and publishes only pushes to
`main` or a manual run on `main`. It runs every gallery example and treats Sphinx
warnings as errors, then copies/rebuilds the atlas under `atlas/`.

In repository **Settings → Pages**, choose **GitHub Actions** as the build source.
The repository initially had Pages disabled; adding a workflow alone does not
claim the site is already live. The deployment job uses `configure-pages` with
`enablement: true`; if GitHub requires repository administration for first-time
setup, select that setting manually and rerun the workflow.

Expected site: <https://julianascencio.github.io/energyclimates/>.

## PyPI release

The single version source is `energyclimates.__version__`. The workflow runs when
a GitHub release is published and requires tag `v<version>` to match the package.
It runs tests and distribution checks before publishing.

One-time setup in your PyPI account: create the `energyclimates` project (or a
pending publisher) and configure this trusted publisher exactly:

| Field | Value |
| --- | --- |
| Owner | `julianascencio` |
| Repository | `energyclimates` |
| Workflow | `publish.yml` |
| Environment | `pypi` |

Create the GitHub environment `pypi` with any desired release-review rules. No
long-lived PyPI token is needed. Publish a GitHub release tagged `v0.2.0` only after
merging and reviewing CI. The release workflow uploads the verified wheel and sdist
as Actions artifacts and publishes the same artifacts to PyPI using OIDC.
A configured workflow does not mean the PyPI project or publisher already exists.

References: [PyPA packaging](https://packaging.python.org/en/latest/tutorials/packaging-projects/)
and [trusted publishers](https://docs.pypi.org/trusted-publishers/using-a-publisher/).
