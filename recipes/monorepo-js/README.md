# Recipe: JS monorepo (workspaces + root commands)

This recipe bootstraps a JS monorepo where:
- root `package.json` defines workspace tooling
- commands are run at the root and cover the whole workspace
- package managers supported: pnpm (recommended), yarn, npm

It gives you:
- `AGENTS.md` / `RUNBOOK.md` with safe marker-only sections
- `.agentsgen.json` with explicit root commands
- PR Guard workflow snippet

## Expected repo structure (example)

- `package.json` (workspaces configured)
- `pnpm-workspace.yaml` (pnpm) OR `yarn.lock` (yarn) OR `package-lock.json` (npm)
- `packages/*` (or `apps/*`, `libs/*`)

## Quickstart

1) Copy `.agentsgen.json` from this folder to your monorepo root.
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

Notes:

- This recipe assumes you have root scripts like lint, test, build.
- If your monorepo uses turbo/nx, point the scripts to those tools.

### Common tweaks
- Set the monorepo root commands in `.agentsgen.json -> commands` (often `pnpm -w lint/test/build`) to match your actual workspace tooling.
- If you want per-package docs, run `agentsgen init` in each package folder (or set up a separate config per workspace).
