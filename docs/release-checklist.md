# Release checklist

1. Run lint, formatting, type checks, the full test suite and the repo's own guard.
2. Build sdist and wheel; run `twine check`; install the wheel into a fresh environment.
3. Run `scripts/release_smoke.py` against the installed CLI and check the supported SET pair.
4. Merge only after CI succeeds. Tag the reviewed commit; publish GitHub release and PyPI package.
5. Verify a fresh public-index install and the public release URLs.

A local green test run is not proof of published availability. Record those gates separately.
The publish workflow repeats tests and installed-wheel demos before uploading.

Create a reviewed version commit, then push tag `vX.Y.Z`. The release workflow checks
the tag/version match, builds and smoke-tests the installed wheel, uploads both package
artifacts to GitHub, and dispatches the trusted PyPI publisher. A manual GitHub release
still triggers PyPI publication as a recovery path.
