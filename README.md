# AGENTS.md Generator (`agentsgen`)

[![CI](https://github.com/markoblogo/AGENTS.md_generator/actions/workflows/ci.yml/badge.svg)](https://github.com/markoblogo/AGENTS.md_generator/actions/workflows/ci.yml)
[![Pages](https://github.com/markoblogo/AGENTS.md_generator/actions/workflows/pages/pages-build-deployment/badge.svg)](https://github.com/markoblogo/AGENTS.md_generator/actions/workflows/pages/pages-build-deployment)
[![Release](https://img.shields.io/github/v/release/markoblogo/AGENTS.md_generator?display_name=tag&sort=semver)](https://github.com/markoblogo/AGENTS.md_generator/releases)
[![License](https://img.shields.io/github/license/markoblogo/AGENTS.md_generator)](LICENSE)
[![Python](https://img.shields.io/badge/python-%3E%3D3.11-blue)](pyproject.toml)

![AGENTS.md Generator landing page](docs/agentsmdscreen.png)

Small, production-grade CLI to generate and safely update:

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

## Install (from source)

```sh
python3 -m venv .venv
. .venv/bin/activate
pip install -e .
```

## Quickstart

Install (recommended for dev tools):

```sh
pipx install git+https://github.com/markoblogo/AGENTS.md_generator.git
```

Generate files (autodetect on by default):

```sh
agentsgen init --defaults
```

Preview changes safely:

```sh
agentsgen update --dry-run --print-diff
```

Apply updates + validate:

```sh
agentsgen update
agentsgen check
```

Uninstall:

```sh
pipx uninstall agentsgen
```

## Usage

```sh
agentsgen init
agentsgen update
agentsgen check
agentsgen init --defaults --stack python --dry-run --print-diff
pipx uninstall agentsgen
```

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
