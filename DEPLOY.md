# Deployment Instructions

Releasing has moved to a tag-triggered flow. See [RELEASING.md](RELEASING.md).

The manual `~/.pypirc` + `twine upload dist/*` procedure that used to live here
is no longer the release path — publishing is done by
`.github/workflows/pypi.yml` when a `vX.Y.Z` tag is pushed.
