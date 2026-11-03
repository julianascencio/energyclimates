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

Before the first deployment, a repository administrator must enable Pages:

1. Open [Settings → Pages](https://github.com/julianascencio/energyclimates/settings/pages).
2. Under **Build and deployment → Source**, select **GitHub Actions**.
3. Open the failed **Documentation** workflow run and choose **Re-run failed jobs**,
   or run **Documentation → Run workflow** on `main`.

The standard `GITHUB_TOKEN` can deploy to an existing Pages site with the workflow's
`pages: write` and `id-token: write` permissions. It cannot create the site for the
first time. Setting `enablement: true` in `configure-pages` does not change that:
it requires a separate token with additional permissions. This workflow deliberately
uses the standard token and the one-time repository setting, with no extra secret.
See the [configure-pages inputs](https://github.com/actions/configure-pages#inputs).

If the build passes but deployment reports `Get Pages site failed: Not Found` or
`Create Pages site failed: Resource not accessible by integration`, check the Pages
source setting first. Do not rerun the build repeatedly or broaden workflow token
permissions to try to enable Pages. A successful build alone does not mean the site
is live; confirm that the deployment job succeeds and the URL below loads.

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
