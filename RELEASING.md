# Releasing numerai-cli

numerai-cli ships to **PyPI only**. The Docker build in CI is a smoke test — no
image is pushed anywhere, and nothing in this repo deploys to a cloud account.
Users get everything by running `pip install numerai-cli`.

This flow is deliberately close to the one in `numerapi/RELEASING.md`, so
switching between the two repos should not require re-learning anything. The
differences that matter are called out under [Caveats specific to this
repo](#caveats-specific-to-this-repo).

## The model

Two rules explain everything else:

1. **`numerai_cli_version` in `setup.py` is the release.** The git tag is only
   the trigger. Whatever that string says is what lands on PyPI.
2. **The version string picks the channel**, not the branch. A
   [PEP 440](https://peps.python.org/pep-0440/) pre-release (`1.1.7.dev0`) is
   invisible to `pip install numerai-cli`; a final version (`1.1.7`) is what
   everyone gets by default.

| Ref | Role |
| --- | --- |
| `<user>/<topic>` | all work; branch off `master` |
| `master` | released state; **final** releases are cut here |
| `X.Y.Z.devN` tag | publishes a pre-release, from **any** branch |
| `X.Y.Z` tag | publishes a final release, **must** be on `master` |

Nothing publishes on a branch push. Only pushing a tag publishes.

| What a user runs | What they get |
| --- | --- |
| `pip install numerai-cli` / `pip install -U numerai-cli` | latest **final** version |
| `pip install 'numerai-cli==1.1.7.dev0'` | that exact pre-release |
| `pip install --pre numerai-cli` | latest including pre-releases |

## Conventions

- **Tags are bare version numbers and must match `setup.py` exactly:** `1.1.7`,
  `1.1.7.dev0`. A `v` prefix is not allowed — CI rejects `v1.1.7` with an
  explicit error.
- Use the canonical PEP 440 spelling with the dot: `1.1.7.dev0`, not
  `1.1.7dev0`. Both normalize to the same release, but the canonical form avoids
  confusion.
- Pre-releases use `.devN`. Increment `N` for each beta on the same version line.
- **A version number can never be reused.** PyPI permanently rejects re-uploading
  a version, even one that was deleted. If you burn a number, move to the next.

## Develop without releasing

```bash
git checkout master && git pull
git checkout -b josh/some-feature
# ... work ...
git push -u origin josh/some-feature
gh pr create --base master
```

The Python matrix (3.10–3.14) and the Docker build run on every push. No tag
means nothing is published. Leave `setup.py` alone until you are actually
cutting something.

## Cut a beta

For beta users who need the code before it is stable. There is no integration
branch here — cut it straight from your topic branch, before it merges.

```bash
git checkout josh/some-feature

# setup.py:  numerai_cli_version = "1.1.7.dev0"
git commit -am "numerai-cli 1.1.7.dev0"
git push origin josh/some-feature     # publishes nothing

# tag and push — this is the release event
git tag 1.1.7.dev0
git push origin 1.1.7.dev0
```

Verify:

```bash
gh run list --workflow=pypi.yml --limit 1                 # expect success
pip install 'numerai-cli==1.1.7.dev0'                     # what beta users run
pip install -U numerai-cli                                # must NOT be the dev version
```

Tell beta users to install the exact version. Note that `pip index versions` and
the simple index can lag a few minutes behind a successful publish on CDN cache;
an exact-version install works immediately.

For the next beta, repeat with `.dev1`, `.dev2`, …

## Promote to a final release (from `master`)

Flip the version to final **as the last commit before merging**, so `master`
never holds a pre-release string and picks up the release version atomically at
merge.

```bash
git checkout josh/some-feature

# setup.py:  numerai_cli_version = "1.1.7"      (drop the .devN suffix)
git commit -am "numerai-cli 1.1.7"
git push origin josh/some-feature

gh pr create --base master --title "numerai-cli 1.1.7"
gh pr merge <n> --squash

git checkout master && git pull
grep numerai_cli_version setup.py                # must read exactly 1.1.7
git tag 1.1.7
git push origin 1.1.7
```

Verify with `pip install -U numerai-cli`, then `numerai --help` and
`numerai copy-example` on a clean virtualenv.

## Hotfix a released version

`master` is the only long-lived branch, so a hotfix is just the normal flow with
a patch bump:

```bash
git checkout -b hotfix/1.1.8 master
# fix + setup.py 1.1.8
gh pr create --base master
# after merge:
git checkout master && git pull
git tag 1.1.8 && git push origin 1.1.8
```

## What CI enforces

`.github/workflows/pypi.yml` runs on tag pushes that start with a digit (and on
`v`-prefixed tags, solely to reject them). It refuses to publish unless:

1. **The tag has no `v` prefix.** `v1.1.7` fails with an error telling you to
   re-tag as `1.1.7`.
2. **The tag matches `setup.py`.** Compared as normalized PEP 440 versions, so
   `1.1.7dev0` and `1.1.7.dev0` are equivalent, but `1.1.7` against a `setup.py`
   of `1.1.7.dev0` fails.
3. **Final releases point at a commit on `master`.** Pre-releases skip this
   check, so betas can be cut from a topic branch but a final one cannot.

`.github/workflows/test-and-deploy.yml` runs the Python 3.10–3.14 matrix
(`pip install .`, `python -m unittest discover -s tests`, `numerai copy-example`)
and the example Docker build on every push.

## Caveats specific to this repo

**There is no `preview` branch, and that is on purpose.** numerapi has one
because `tournament-monorepo` pins it and needs somewhere unreleased work can
sit indefinitely. numerai-cli is a leaf — no internal service depends on it, so
a second long-lived branch would be pure overhead. The practical consequence is
that betas are cut from topic branches rather than from an integration branch.

**Tests do not gate the publish.** `pypi.yml` and `test-and-deploy.yml` are
separate workflows, and GitHub Actions cannot express a cross-workflow
dependency. Pushing a tag does start the test matrix against the tagged commit,
but it runs *concurrently* with the publish — a red test suite will not stop the
upload. Tag commits that have already gone green on a branch push.

**A duplicate version now fails loudly.** The old `pypi-release` job used
`twine upload --skip-existing`, which meant forgetting to bump `setup.py` was a
silent no-op: green build, nothing shipped. That is how `setup.py` reached
`1.1.6` while PyPI's latest was `1.1.5`. The flag is gone; a duplicate version
now errors. See [Troubleshooting](#troubleshooting).

**A release ships more than Python code.** `MANIFEST.in` is
`recursive-include numerai *`, so the terraform modules under
`numerai/terraform/` and every example under `numerai/examples/` (Dockerfiles,
`requirements.txt`, `predict.py`) go out with the package. A release can
therefore change the infrastructure users apply to their own cloud accounts and
the images their prediction nodes build. Blast radius is wider than for a pure
library — this is the main reason the `.devN` channel is worth using here rather
than shipping straight to final.

**CHANGELOG.md** Edit `CHANGELOG.md` as part of the version-bump commit when cutting a release.

**Version is only in `setup.py`.** The package exposes no `__version__` and
nothing else in the tree hardcodes it, so `numerai_cli_version` is the single
place to edit.

**The PyPI secret is `PYPI_API_KEY`** in this repo, not `PYPI_API_TOKEN` as in
numerapi. Publishing uses `twine` directly rather than
`pypa/gh-action-pypi-publish` — it is the path this repo's token is already set
up for.

**Do not retro-tag old releases.** Any new tag starting with a digit triggers a
publish attempt that will fail on a duplicate version. The only historical tag is
`v0.1.22`, which predates the bare-number convention — leave it alone. It already
exists on `origin`, so it fires nothing; re-pushing it would only hit the
`v`-prefix rejection. The 99 releases on PyPI predating this flow were published
by branch-push CI and have no corresponding tags at all. Two junk tags (`list`,
`liost`, both typos pointing at the same commit) existed locally and have been
deleted — they were never pushed to `origin`.

**Pre-releases are not new here.** PyPI already holds 49 of them from the 0.3.x
era (`0.3.0.dev10` … `0.3.4.dev1`), published back when CircleCI released from
every branch. The `.devN` convention above matches what is already there.

## Troubleshooting

**`File already exists` on publish.** That version is already on PyPI. Bump to
the next number — you cannot re-upload, and you cannot fix it by deleting the
release on PyPI either.

**Tag mismatch error.** You tagged without bumping `setup.py`, or vice versa.
Fix `setup.py`, commit, delete the tag locally and on origin
(`git push origin :refs/tags/X.Y.Z`), then re-tag. Deleting a tag never publishes
anything.

**"Release tags must be bare version numbers."** You tagged `v1.1.7` out of
habit. Delete the tag locally and on origin, then re-tag as `1.1.7`.

**"Final release tags must point at a commit on master."** You tagged a
suffix-free version on a topic branch. Either merge to `master` first, or cut it
as a `.devN` pre-release instead.

**A bad version is already public.** You cannot unpublish, but you can
`yank` it on PyPI, which hides it from resolution while leaving existing pins
working. Then ship the fix as the next version.
