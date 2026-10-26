# Deployment Instructions
The `Test & Deploy Numerai CLI` workflow tests every pushed branch and publishes
to PyPI when `master` passes. For Classic v6, keep the release PR unmerged until
the data and submission release is approved; merging publishes the package.

1. Update the Classic example and its tests, then bump `setup.py` (v6: 1.1.8).
2. Run `python -m unittest discover -s tests -v` with the example requirements
   installed, and verify the package includes the updated example files.
3. Push the release branch and require the Python and Docker CI checks to pass.
4. After release approval, merge, monitor the PyPI release job, and tag the merged
   commit with the matching version. Do not publish a tag from an unmerged branch.
5. Verify installation and `numerai copy-example`; existing nodes must copy the
   changes, retrain on v6, and redeploy.

The commands below are a manual publishing fallback, not an additional required
upload after the automated release.

Create a .pypirc file in your home directory like so:
```
▶ cat ~/.pypirc
[distutils]
index-servers =
    pypi

[pypi]
repository: https://upload.pypi.org/legacy/
username: REPLACE_ME
password: ***
```

Install twine:
```
pip3 install twine
```

Build the dist packages:
```
rm -rf dist
python3 setup.py sdist bdist_wheel
```

Deploy:
```
twine upload dist/*
```
