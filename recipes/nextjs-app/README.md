# Recipe: Next.js app (pnpm + build + lint)

This recipe bootstraps a typical Next.js repo:
- pnpm for package management
- next build for CI confidence
- lint via `next lint` (or your own script)

It gives you:
- `AGENTS.md` / `RUNBOOK.md` with safe marker-only sections
- `.agentsgen.json` with explicit commands for install/dev/test/lint/build
- PR Guard workflow snippet

## Expected repo structure (example)

- `package.json`
- `pnpm-lock.yaml`
- `next.config.js` (optional)
- `app/` or `pages/`

## Quickstart

1) Copy `.agentsgen.json` from this folder to your repo root.

2) Run:
```bash
agentsgen init . --defaults
agentsgen update . --dry-run --print-diff
agentsgen pack . --check --format json
```

3. Commit generated docs once you’re happy.

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
- Update `.agentsgen.json -> commands` if your repo uses `npm` or `yarn` instead of `pnpm`, or if your scripts are named differently.
- If the app lives in a subfolder (e.g. `apps/web`), set a workspace path in `.agentsgen.json` (or run `agentsgen init <path-to-app>`).
