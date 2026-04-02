# AGENTS.md Generator (`agentsgen`)
Safe repo docs + PR Guard + AI docs bundle for coding agents.

[![CI](https://github.com/markoblogo/AGENTS.md_generator/actions/workflows/ci.yml/badge.svg)](https://github.com/markoblogo/AGENTS.md_generator/actions/workflows/ci.yml)
[![Pages](https://github.com/markoblogo/AGENTS.md_generator/actions/workflows/pages/pages-build-deployment/badge.svg)](https://github.com/markoblogo/AGENTS.md_generator/actions/workflows/pages/pages-build-deployment)
[![Release](https://img.shields.io/github/v/release/markoblogo/AGENTS.md_generator?display_name=tag&sort=semver)](https://github.com/markoblogo/AGENTS.md_generator/releases)
[![License](https://img.shields.io/github/license/markoblogo/AGENTS.md_generator)](LICENSE)
[![Python](https://img.shields.io/badge/python-%3E%3D3.11-blue)](pyproject.toml)

Landing: https://agentsmd.abvx.xyz/
Manifest: https://github.com/markoblogo/AGENTS.md_generator/blob/main/docs/manifest.md
ID integration: https://github.com/markoblogo/ID/blob/main/docs/AGENTSGEN_INTEGRATION.md
Listed on ABVX Lab: https://lab.abvx.xyz/
Orchestrated with SET: https://github.com/markoblogo/SET
Human context with ID: https://github.com/markoblogo/ID

`agentsgen` is the repo-intelligence runtime in the ABVX ecosystem: use it directly in a repo, or call it through `SET` when you want one thin orchestration entrypoint.
Pair it with `ID` when you also need portable human-AI context and repo-local integration hooks across tools: `agentsgen pack` now emits a repo-local handoff manifest at `docs/ai/id-context.json` for that bridge. `ID` remains the human/profile layer: https://github.com/markoblogo/ID

Small, production-grade CLI to generate and safely update:

- `AGENTS.md` (strict repo contract for coding agents)
- `RUNBOOK.md` (human-friendly command/run cheatsheet)
- proof-loop task artifacts under `docs/ai/tasks/`

## References

- https://arxiv.org/abs/2602.11988
- https://arxiv.org/abs/2602.20478

## Safety Model

The tool is safe-by-default and follows a strict 3-mode policy per file:

1. File missing: create it with marker sections.
2. File exists and markers exist: update only content inside markers.
3. File exists but markers missing: do not modify it; write `*.generated.md` instead.

- Optional review guideline for coding agents: `docs/agent-guidelines.md`.

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

Or start from a built-in preset:

```sh
agentsgen init . --preset nextjs
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
      - uses: markoblogo/AGENTS.md_generator/.github/actions/agentsgen-guard@main
        with:
          comment: "true"
          files: "AGENTS.md,RUNBOOK.md"
          pack_check: "true"
          pack_format: "json"
```

4. Read-only repo snapshot:

```sh
agentsgen status .
```

5. Canonical README extracts for agents and CI:

```sh
agentsgen snippets .
```

6. Optional AI docs bundle:

```sh
agentsgen pack . --autodetect
cat agents.entrypoints.json
cat docs/ai/id-context.json
```

For public website mode:

```sh
agentsgen pack . --site https://example.com
```

Companion guide for site-oriented AI visibility work: `docs/assets/llmo-quick-start.pdf`. For multi-repo orchestration, use `SET`: `https://github.com/markoblogo/SET`. For portable human-AI context across tools, pair with `ID`: `https://github.com/markoblogo/ID`

7. Profit: fewer agent mistakes, safer updates, and better indexable repo context.

Deep dives:
- Action options: `docs/gh-action.md`
- Pack bundle details: `docs/llmo-pack.md`
- Free AI visibility guide (PDF): `docs/assets/llmo-quick-start.pdf`
- Release process: `docs/release-checklist.md`

## Presets

Presets are conservative starter `.agentsgen.json` templates for common repo shapes.
Use them to get explicit commands quickly, then edit the generated config to match your real toolchain. Pair them with `agentsgen status` for a read-only snapshot and `agentsgen snippets` for canonical README extracts.

```sh
agentsgen presets
agentsgen init . --preset nextjs
agentsgen init . --preset cli-python
```

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
      - uses: markoblogo/AGENTS.md_generator/.github/actions/agentsgen-guard@main
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
agentsgen presets
agentsgen init . --preset nextjs
agentsgen update
agentsgen pack
agentsgen snippets .
agentsgen snippets . --check
agentsgen check
agentsgen check . --pack-check
agentsgen check . --all --ci
agentsgen check . --format json
agentsgen status .
agentsgen detect . --format json
agentsgen analyze https://example.com
agentsgen meta https://example.com
agentsgen task init proof-loop-v0 . --summary "Capture proof artifacts for this task"
agentsgen task evidence proof-loop-v0 . --check "pytest=passed" --check "ruff=passed"
agentsgen task verdict proof-loop-v0 . --status needs-review --summary "Manual review still pending"
agentsgen init --defaults --stack python --dry-run --print-diff
pipx uninstall agentsgen
```

agentsgen status is a read-only overview of managed files, markers, generated fallbacks, and pack drift.
It is lighter and more diagnostic than `agentsgen check`, which focuses on repo readiness errors/warnings.
`agentsgen task evidence` and `agentsgen task verdict` now write richer summaries for checks, artifacts, decision state, and review readiness under `docs/ai/tasks/<task-id>/`.

`agentsgen check` can also aggregate optional drift checks:
- `agentsgen check . --pack-check` adds `pack --check`
- `agentsgen check . --all` enables both pack and snippets checks
- `agentsgen check . --format json` emits a stable machine-readable payload
- `agentsgen check . --ci` prints a compact CI summary without path-heavy log noise
- `agentsgen pack . --site https://example.com` generates a site-oriented `llms.txt` from the homepage and sitemap

## README Snippets (mini-validator)

Use snippet markers in `README.md` to define canonical agent-facing extracts without editing generated output by hand.
The command writes `README_SNIPPETS.generated.md`.

Marker format:

```md
<!-- AGENTSGEN:SNIPPET name=install -->
python -m pip install -e ".[dev]"
<!-- AGENTSGEN:ENDSNIPPET -->
```

```sh
agentsgen snippets .
agentsgen snippets . --check
```

## Proof-loop v0

For larger tasks, `agentsgen` can keep a lightweight proof bundle in-repo:

- `docs/ai/tasks/<task-id>/contract.md`
- `docs/ai/tasks/<task-id>/evidence.json`
- `docs/ai/tasks/<task-id>/verdict.json`

```sh
agentsgen task init proof-loop-v0 . --summary "Capture proof artifacts for this task"
agentsgen task evidence proof-loop-v0 . --check "pytest=passed"
agentsgen task verdict proof-loop-v0 . --status needs-review --summary "Manual review still pending"
```

## Pack bundle

`agentsgen pack` generates an AI-readable documentation bundle:

- `llms.txt` (or `LLMS.md` with `--llms-format md`)
- `agents.entrypoints.json` (machine-readable command manifest for agents/CI)
- `docs/ai/id-context.json` (machine-readable repo handoff manifest for `ID`-compatible flows)
- `docs/ai/how-to-run.md`
- `docs/ai/how-to-test.md`
- `docs/ai/architecture.md`
- `docs/ai/data-contracts.md`
- `SECURITY_AI.md`
- `CONTRIBUTING_AI.md`
- `README_SNIPPETS.md`

New:
- `agents.entrypoints.json` — a machine-readable manifest of repo commands (install/test/lint/build/run) derived from `.agentsgen.json` / autodetect.
- `docs/ai/id-context.json` — a repo-scoped handoff manifest that gives `ID` a stable entrypoint into repo docs, command manifests, repomap artifacts, and proof-loop surfaces.

By default, pack writes AI docs into docs/ai/ (override via pack_output_dir).
Use --print-plan to preview what pack will write.

What it is:
- a compact, agent-first context bundle for coding agents and LLM indexing.

## Repo understanding artifacts

`agentsgen understand` generates a deterministic repo map, compact token-budgeted map, import graph, and machine-readable knowledge file.
It uses local heuristics only: no network calls, no LLM calls.
Artifacts are written with the same safe update policy used elsewhere in `agentsgen`.

`agentsgen understand .`
`agentsgen understand . --compact-budget 4000`
`agentsgen understand . --focus cli`
`agentsgen understand . --changed`

Artifacts:
- `docs/ai/repomap.md`
- `docs/ai/repomap.compact.md`
- `docs/ai/graph.mmd`
- `agents.knowledge.json`

`repomap.compact.md` ranks files by import graph signals, entrypoint proximity, and local git changes, then trims the output to an approximate token budget for agent context handoff.
Use `--focus <query>` for a query-specific slice, or `--changed` to bias the compact map toward current git changes and their immediate import neighbors.

What it is not:
- not a traffic/SEO promise, and not a full developer handbook replacement.

`agentsgen analyze` audits a public URL and writes `docs/ai/llmo-score.json`.
It uses deterministic heuristics by default and can add an optional advisory AI review with `--use-ai`.

`agentsgen meta` generates `docs/ai/llmo-meta.json` with AI-oriented title, description, keywords, and short description suggestions for a public URL.

Companion guide for these public-site workflows: `docs/assets/llmo-quick-start.pdf`.

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
- Templates are still intentionally minimal: `python`, `node`, `static`.
- The tool only owns content inside `AGENTSGEN` marker sections; keep custom content outside markers.

## Landing Page (GitHub Pages)

This repo includes a minimal one-page landing in `docs/index.html`.

- GitHub: Settings -> Pages
- Source: Deploy from a branch
- Branch: `main`
- Folder: `/docs`

## Experimental: ASCII theme (landing)

- The landing page includes an experimental ASCII theme as a visual/UX experiment.
- Toggle it from the header next to the light/dark switch.
- The setting is saved in localStorage.
- This is UI-only and does not affect the generator output.
- Reuse pointers:
  - `docs/ascii/ascii.css`
  - `docs/ascii/ascii.js`

## Snapshot Commits

If you want cheap “backup commits” with a green-test gate:

```sh
make snapshot
```

This runs `ruff format`, `ruff check`, `pytest`, then commits only if there are changes and tests are green.

## Local Smoke

If direct `python -m agentsgen ...` runs are flaky in your local shell or runner, use the repo wrapper:

```sh
make smoke
```

This uses `scripts/smoke.sh`, which prefers `.venv/bin/python` and launches Python through a minimal `perl exec` shim when `perl` is available. The smoke run covers:

- `python -m agentsgen --version`
- `python -m agentsgen._smoke`
- short `pytest` / `CliRunner` coverage for presets, status, snippets, and detect

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
- 3 builtin smoke tests exist: `python -m agentsgen._smoke`
  - init in empty dir creates files
  - edit outside markers persists after update
  - no-markers files produce `*.generated.md` and leave originals untouched
- recommended local smoke entrypoint: `make smoke`

## Contributing

Template PRs welcome (shared sections and stack-specific notes).

## Releasing

- Use checklist: `docs/release-checklist.md`
- Run releases from an activated venv (`. .venv/bin/activate`); the script also auto-prefers `.venv/bin/python` when present.
- Write release notes: `RELEASES/template.md -> RELEASES/vX.Y.Z.md`
- Run: `./scripts/release.sh vX.Y.Z A|B|C`
- Shorthand: `./scripts/release.sh A` (auto-suggests next version)
- Tags follow `vX.Y.Z` and should point to the release commit
