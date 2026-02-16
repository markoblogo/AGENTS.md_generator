# Release Checklist (tags + GitHub Releases)

## Release modes

### Mode A - Early OSS (default right now)

Goal: release quickly without breaking users.  
Guarantee: tag + GitHub Release + short notes.  
Requirements: smoke + (recommended) pytest.

Use this before `v1.0`, while CLI/action behavior may change frequently.

### Mode B - Stable OSS

Goal: predictable releases with lower regression risk.  
Guarantee: everything in Early OSS + compatibility + stricter checks.  
Requirements: CI green, pytest required, docs up to date, workflow examples verified.

Use this when external users adopt the action/CLI in production repositories.

### Mode C - Product (future)

Goal: release as a full product drop.  
Guarantee: everything in Stable OSS + landing update + changelog discipline + optional distribution.  
Requirements: rollout notes, upgrade guidance, deprecation policy.

Use this when distribution/monetization/support flows are active.

## Versioning rule

- Tags follow SemVer: `vX.Y.Z`
- Patch `X.Y.(Z+1)`: fixes/docs/small improvements, no major behavior changes
- Minor `X.(Y+1).0`: new backward-compatible features
- Major `(X+1).0.0`: breaking changes (must be documented)

## Common pre-flight (all modes)

- `git checkout main && git pull`
- `git status -sb` is clean
- CI on `main` is green (or tests just ran locally)
- target version is chosen (`vX.Y.Z`)
- Optional helper script: `./scripts/release.sh vX.Y.Z A|B|C` (or shorthand `./scripts/release.sh A`)

## Mode A checklist (5-10 min)

### 1) Run minimal checks

- `python -m agentsgen._smoke`
- `pytest -q` (recommended; if unavailable, run at least smoke)

### 2) Write release notes

- Create `RELEASES/vX.Y.Z.md` from `RELEASES/template.md`
- Include:
  - What is inside
  - Safety model
  - Quickstart
  - Known limitations

### 3) Update versioned docs references (if needed)

- If docs/README include `@v...` snippets, update to `@vX.Y.Z`

### 4) Commit + tag + push

- `git add -A`
- `git commit -m "release: vX.Y.Z"`
- `git tag vX.Y.Z`
- `git push && git push --tags`

### 5) Create GitHub Release object

UI: GitHub Releases -> Draft new release -> choose tag -> paste `RELEASES/vX.Y.Z.md`.

CLI (optional):

```bash
gh release create vX.Y.Z --title "vX.Y.Z - ..." --notes-file RELEASES/vX.Y.Z.md
```

### 6) Post-release sanity

- Release page renders correctly
- Tag exists and points to intended commit
- README/docs snippets reference `@vX.Y.Z`
- Example workflow still matches current action inputs

## Mode B checklist (adds constraints)

Do everything in Mode A, plus:

- CI on `main` must be green after release commit
- `pytest -q` is mandatory
- If detect/guard behavior changed:
  - add/update fixture under `tests/fixtures/*`
  - add/update test coverage for that behavior
- For behavior changes:
  - add "Behavior changes" section in release notes
  - add short upgrade notes
- Verify `.github/workflows/agentsgen-guard.example.yml`:
  - pinned to `@vX.Y.Z`
  - permissions minimal and correct
  - documented inputs match action inputs

## Mode C checklist (future)

Do everything in Mode B, plus:

- update landing "Latest version" and snippets
- add a short "Why it matters" paragraph in notes
- optional migration/deprecation guide
- optional package distribution (PyPI)
- short public announcement

## Hard stop (do not release)

- CI red or smoke failing
- user-facing change without release notes
- tag would not match intended release commit
- docs/actions reference stale tag while behavior changed

## Release notes template

```md
## What's inside
- ...

## Safety model
- ...

## Quickstart
```bash
# install / usage
...
```

## Known limitations
- ...
```
