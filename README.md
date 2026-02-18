# AGENTS.md Generator (`agentsgen`)
Repo Docs Guard
AGENTS.md Generator — safe repo docs + PR Guard + LLMO Pack
A safe-by-default repo docs toolchain for coding agents.

[![CI](https://github.com/markoblogo/AGENTS.md_generator/actions/workflows/ci.yml/badge.svg)](https://github.com/markoblogo/AGENTS.md_generator/actions/workflows/ci.yml)
[![Pages](https://github.com/markoblogo/AGENTS.md_generator/actions/workflows/pages/pages-build-deployment/badge.svg)](https://github.com/markoblogo/AGENTS.md_generator/actions/workflows/pages/pages-build-deployment)
[![Release](https://img.shields.io/github/v/release/markoblogo/AGENTS.md_generator?display_name=tag&sort=semver)](https://github.com/markoblogo/AGENTS.md_generator/releases)
[![License](https://img.shields.io/github/license/markoblogo/AGENTS.md_generator)](LICENSE)
[![Python](https://img.shields.io/badge/python-%3E%3D3.11-blue)](pyproject.toml)

![AGENTS.md Generator landing page (v0.1.2)](docs/assets/agentsmd-landing-v0.1.2.png)
Landing: https://agentsmd.abvx.xyz/

Small, production-grade CLI to generate and safely update:
New: Recipes — copy-paste starter kits (explicit commands + PR Guard workflow).

- `AGENTS.md` (strict repo contract for coding agents)
- `RUNBOOK.md` (human-friendly command/run cheatsheet)

## Safety Model

The tool is safe-by-default and follows a strict 3-mode policy per file:

1. File missing: create it with marker sections.
2. File exists and markers exist: update only content inside markers.
3. File exists but markers missing: do not modify it; write `*.generated.md` instead.

Marker format:

```md
<!-- AGENTSGEN:START section=commands -->
... generated content ...
<!-- AGENTSGEN:END section=commands -->
```

## Install (from source, for contributors)

```sh
python3 -m venv .venv
. .venv/bin/activate
pip install -e ".[dev]"
```

## Quickstart

Canonical onboarding path for a new repo:

1. Install (`pipx` recommended):

```sh
pipx install git+https://github.com/markoblogo/AGENTS.md_generator.git
```

2. Bootstrap docs with autodetect:

```sh
agentsgen init . --defaults --autodetect
```

3. Add PR guard workflow (`.github/workflows/agentsgen-ci.yml`):

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

4. Optional LLMO bundle:

```sh
agentsgen pack . --autodetect
```

5. Profit: fewer agent mistakes, safer updates, and better indexable repo context.

Deep dives:
- Action options: `docs/gh-action.md`
- LLMO pack details: `docs/llmo-pack.md`
- Release process: `docs/release-checklist.md`

## Recipes

Copy-paste starter kits (each includes an example `.agentsgen.json` with explicit commands + a PR Guard workflow snippet):
Pick one → copy .agentsgen.json to your repo root → run: agentsgen init . --defaults --autodetect

- **Python library (Poetry + pytest):** [`recipes/python-lib/`](recipes/python-lib/)
- **Next.js app (pnpm):** [`recipes/nextjs-app/`](recipes/nextjs-app/)
- **JS monorepo (workspaces):** [`recipes/monorepo-js/`](recipes/monorepo-js/)
- **Node CLI tool:** [`recipes/cli-tool/`](recipes/cli-tool/)

## GitHub Action: PR Guard

Use the reusable `agentsgen-guard` action to fail PRs when `AGENTS.md` / `RUNBOOK.md` are missing or out of date.

```yaml
name: agentsgen-guard

on:
  pull_request:

permissions:
  contents: read
  # pull-requests: write  # only if comment: "true"

jobs:
  guard:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: markoblogo/AGENTS.md_generator/.github/actions/agentsgen-guard@v0.1.2
        with:
          path: "."
          files: "AGENTS.md,RUNBOOK.md"
          comment: "true"
          pack_check: "true"
          pack_format: "json"
          # pack_autodetect: "true"
          # pack_llms_format: "md"
          # pack_output_dir: "docs/ai"
          # pack_files: |
          #   llms
          #   SECURITY_AI.md
```

- Optional PR comment: use `comment: "false"` if you prefer log-only mode.
- Fork-safe by default: no extra secrets required.
- Most users only need these inputs: `comment`, `files`, `pack_check`.
- Advanced knobs: `pack_format`, `pack_autodetect`, `pack_llms_format`, `pack_output_dir`, `pack_files`.
- `files` input is an action-level filter for reported file findings; core validation still runs through `check_repo`.
- `pack_check: "true"` enforces `agentsgen pack --autodetect --check` in the same guard run.
- `pack` is still supported as a backward-compatible alias (deprecated; prefer `pack_check`).
- Example workflow: `.github/workflows/agentsgen-guard.example.yml`
- Full action docs: `docs/gh-action.md`

## Usage

```sh
agentsgen init
agentsgen update
agentsgen pack
agentsgen check
agentsgen detect . --format json
agentsgen init --defaults --stack python --dry-run --print-diff
pipx uninstall agentsgen
```

## LLMO Pack

`agentsgen pack` generates an AI/LLMO-ready documentation bundle:

- `llms.txt` (or `LLMS.md` with `--llms-format md`)
- `docs/ai/how-to-run.md`
- `docs/ai/how-to-test.md`
- `docs/ai/architecture.md`
- `docs/ai/data-contracts.md`
- `SECURITY_AI.md`
- `CONTRIBUTING_AI.md`
- `README_SNIPPETS.md`

By default, pack writes AI docs into docs/ai/ (override via pack_output_dir).
Use --print-plan to preview what pack will write.

What it is:
- a compact, agent-first context bundle for coding agents and LLM indexing.

What it is not:
- not a traffic/SEO promise, and not a full developer handbook replacement.

### Why it matters
- **Less agent babysitting.** Repos with `AGENTS.md` + `docs/ai/` reduce back-and-forth and "where is X?" questions for Codex/Claude.
- **Safer automation by default.** Marker-only updates + `*.generated.*` fallback prevents accidental overwrites of hand-written docs.
- **CI keeps it honest.** `agentsgen-guard` + `agentsgen pack --check` catches drift early, before docs rot and agents start hallucinating.

Safety model is identical to `init`/`update`:

1. Missing file -> create with markers.
2. Existing file with markers -> update only marker sections.
3. Existing file without markers -> keep original and write `*.generated.*`.

See full details: `docs/llmo-pack.md`.

## Known Limitations

- Auto-detect is intentionally conservative (file heuristics only; no “smart” analysis).
- Monorepos may detect as `mixed`, and commands can be empty on purpose (better empty than wrong).
- If a Makefile exists, Makefile targets win over other toolchains by design.
- Templates are minimal for v0.1.x: `python`, `node`, `static`.
- The tool only owns content inside `AGENTSGEN` marker sections; keep custom content outside markers.

## Landing Page (GitHub Pages)

This repo includes a minimal one-page landing in `docs/index.html`.

- GitHub: Settings -> Pages
- Source: Deploy from a branch
- Branch: `main`
- Folder: `/docs`

## Snapshot Commits

If you want cheap “backup commits” with a green-test gate:

```sh
make snapshot
```

This runs `ruff format`, `ruff check`, `pytest`, then commits only if there are changes and tests are green.

## Definition Of Done (DoD)

- `agentsgen init` works in an empty folder and creates:
  - `.agentsgen.json`
  - `AGENTS.md`
  - `RUNBOOK.md`
- `agentsgen update`:
  - updates only marker sections
  - preserves content outside markers
  - writes `*.generated.md` if markers are missing
- `agentsgen check` returns non-zero exit code on problems
- 3 smoke tests exist: `python -m agentsgen._smoke`
  - init in empty dir creates files
  - edit outside markers persists after update
  - no-markers files produce `*.generated.md` and leave originals untouched

## Contributing

Template PRs welcome (shared sections and stack-specific notes).

## Releasing

- Use checklist: `docs/release-checklist.md`
- Run releases from an activated venv (`. .venv/bin/activate`); the script also auto-prefers `.venv/bin/python` when present.
- Write release notes: `RELEASES/template.md -> RELEASES/vX.Y.Z.md`
- Run: `./scripts/release.sh vX.Y.Z A|B|C`
- Shorthand: `./scripts/release.sh A` (auto-suggests next version)
- Tags follow `vX.Y.Z` and should point to the release commit
