# Changelog

Notable changes to numerai-cli. Update this file as part of the version-bump
commit for each release (see [RELEASING.md](RELEASING.md)).

Releases before 1.2.0 were not tracked here — their notes live in the pull
requests that cut them.

## 1.2.0 - 2026-08-12

### Added

- Python 3.14 support. The CI test matrix now covers Python 3.10 through 3.14,
  and the example prediction nodes build on `python:3.14` Docker images.
- Tag-triggered PyPI release workflow (`.github/workflows/pypi.yml`). Pushing a
  bare version tag (e.g. `1.2.0`, `1.2.0.dev0`) is now the only thing that
  publishes. The workflow refuses to publish if the tag has a `v` prefix, if it
  doesn't match `numerai_cli_version` in `setup.py`, or if a final (non-`.devN`)
  release is tagged off a commit that isn't on `master`.
- [RELEASING.md](RELEASING.md), documenting the release flow: beta `.devN`
  pre-releases from topic branches, final releases from `master`, and hotfixes.
- Tests for the platform setup scripts (`tests/test_setup_scripts.py`), run by
  CI on every push.
- This changelog.

### Changed

- Upgraded the pinned dependencies in all three example nodes
  (`tournament-python3`, `signals-python3`, `crypto-python3`):
  - `pandas` 2.3.3 → 3.0.5 (pandas 3 support)
  - `pyarrow` 18.1.0 → 23.0.1
  - `lightgbm` 4.5.0 → 4.7.0 — required for the new scikit-learn pin: the
    scikit-learn estimator API in lightgbm ≤ 4.5.0 is incompatible with
    scikit-learn ≥ 1.6 (`__sklearn_tags__` change). 4.7.0 also adds official
    Python 3.14 and pandas 3 support.
  - `scikit-learn` 1.6.1 → 1.8.0
- The platform setup scripts (`setup-mac.sh`, `setup-win10.ps1`) now install
  Python 3.12.10 instead of 3.9.1. The macOS script uses the single universal2
  installer, which supports both Intel and Apple Silicon on macOS 10.13+.
- Branch pushes no longer publish anything. The old `pypi-release` job was
  removed from `test-and-deploy.yml`, which now only runs the test matrix and
  the example Docker build.
- `DEPLOY.md`'s manual `~/.pypirc` + `twine` instructions were replaced with a
  pointer to [RELEASING.md](RELEASING.md).

### Fixed

- The macOS setup script's Python and OS-version detection checks, which could
  never match (a broken `which` comparison and a malformed version regex), were
  rewritten using `command -v` and `sw_vers`.
- Publishing a version that already exists on PyPI now fails loudly instead of
  silently succeeding: the publish step no longer passes `--skip-existing` to
  twine, so forgetting to bump `setup.py` can't ship nothing on a green build.
