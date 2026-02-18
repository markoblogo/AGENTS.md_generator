# Recipe: CLI tool (Node.js)

This recipe bootstraps a typical Node CLI repo:
- a small CLI published as npm package (or internal tool)
- build via TypeScript (optional) and lint/test scripts

It gives you:
- `AGENTS.md` / `RUNBOOK.md` with marker-only safe updates
- `.agentsgen.json` with explicit commands
- PR Guard workflow snippet

## Expected repo structure (example)

- `package.json`
- `src/` (TypeScript) or `bin/` / `index.js`
- `tsconfig.json` (if TS)
- `dist/` (if build output)

## Quickstart

1) Copy `.agentsgen.json` from this folder to your repo root.
2) Run:
```bash
agentsgen init . --defaults
agentsgen update . --dry-run --print-diff
agentsgen pack . --check --format json
```

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

### Common tweaks
- Replace the default `commands` in `.agentsgen.json` to match your CLI setup (Typer/Click for Python, or `node ./bin` for Node).
- If your CLI code is not at repo root (e.g. `packages/cli`), point init/update to that folder or set a workspace path in `.agentsgen.json`.
