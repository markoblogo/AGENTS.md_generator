# Recipe: Python library (Poetry + pytest)

This recipe bootstraps a typical Python library repo:
- Poetry for dependencies and packaging
- pytest for tests
- ruff for lint/format (optional but common)

It gives you:
- `AGENTS.md` / `RUNBOOK.md` with safe marker-only sections
- A ready-to-use `.agentsgen.json` with explicit commands
- A PR Guard workflow snippet you can copy into `.github/workflows/agentsgen-guard.yml`

## Expected repo structure (example)

- `pyproject.toml`
- `src/<package_name>/...`
- `tests/...`

## Quickstart

1) Copy `.agentsgen.json` from this folder to your repo root.

2) Run:
```bash
agentsgen init . --defaults
agentsgen update . --dry-run --print-diff
# Optional: create/update the pack files
agentsgen pack . --check --format json
```

3. Commit generated docs (once you’re happy with the diff).

## PR Guard workflow (copy/paste)

Create .github/workflows/agentsgen-guard.yml:

```yaml
name: agentsgen guard + pack check

on:
  pull_request:
  push:
    branches: [ main ]

permissions:
  contents: read
  pull-requests: write

jobs:
  agentsgen:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: markoblogo/AGENTS.md_generator/.github/actions/agentsgen-guard@v0.1.2
        with:
          comment: "true"
          files: "AGENTS.md,RUNBOOK.md"
          pack_check: "true"
          pack_format: "json"
```

Notes:

- comment: "true" posts a PR comment with results (safe default).
- pack_check: "true" enforces drift detection for pack files in the same job.

### Common tweaks
- Edit the `commands` block in `.agentsgen.json` if your project uses `uv`/`pip` instead of Poetry, or if your test command isn’t `pytest -q`.
- If your package isn’t under `src/`, update any paths mentioned in AGENTS/RUNBOOK after the first init (the generator won’t guess your layout).
