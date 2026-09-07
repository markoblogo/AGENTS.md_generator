# CLI and advanced reference

Start with the [quickstart](../README.md). Experimental surfaces are optional.

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
agentsgen check . --all --report
agentsgen check . --format json
agentsgen fix . --all
agentsgen fix . --all --dry-run --print-diff
agentsgen fleet scan ~/code --max-depth 2
agentsgen fleet scan ~/code --format json
agentsgen doctor . --all --ci
agentsgen status .
agentsgen status . --format json
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
`agentsgen doctor` is an exact alias for `agentsgen check`.
Invalid `.agentsgen.json` files now fail as structured CLI errors instead of raw tracebacks.
`agentsgen status --format json` includes pack-level findings and pack-level errors for machine consumers.
`agentsgen task evidence` and `agentsgen task verdict` now write richer summaries for checks, artifacts, decision state, and review readiness under `docs/ai/tasks/<task-id>/`.

`agentsgen check` can also aggregate optional drift checks:
- `agentsgen check . --pack-check` adds `pack --check`
- `agentsgen check . --all` enables both pack and snippets checks
- `agentsgen check . --all --report` prints an Agent Readiness Score and recommended fix commands
- `agentsgen check . --format json` emits a stable machine-readable payload
- `agentsgen check . --ci` prints a compact CI summary without path-heavy log noise
- `agentsgen pack . --site https://example.com` generates a site-oriented `llms.txt` from the homepage and sitemap

`agentsgen fix` is deliberately conservative:
- `agentsgen fix .` updates only marker-managed `AGENTS.md` / `RUNBOOK.md` sections from `.agentsgen.json`
- `agentsgen fix . --pack` also refreshes pack artifacts
- `agentsgen fix . --snippets` also refreshes `README_SNIPPETS.generated.md`
- `agentsgen fix . --all` enables both pack and snippets remediation
- `--dry-run --print-diff` previews the exact writes

It does not invent commands, rewrite unmarked docs, or mutate repo code. If `.agentsgen.json` is missing, run `agentsgen init` first.

## Team / fleet mode

`agentsgen fleet scan` is the read-only portfolio view for teams that want to roll out repo contracts across many repositories.
It walks git repos under one or more roots, runs the same dry-run planning engine, and reports which repos need init, marker review, or safe fixes.

```sh
agentsgen fleet scan ~/code --max-depth 2
agentsgen fleet scan ~/code ~/work --max-depth 3 --format json
agentsgen fleet scan ~/code --out /tmp/agentsgen-fleet.md --json-out /tmp/agentsgen-fleet.json
```

The JSON payload is validated as `fleet_scan_report` and includes:

- repo count, failed scans, repos needing init, repos needing manual marker review, and planned changed-file count;
- one row per repo with `AGENTS.md` / `RUNBOOK.md` marker state;
- dry-run plan actions;
- a `recommended_next` command for each repo.

This mode does not write to scanned repos. The legacy `scripts/scan_repos.py` wrapper still exists for automation that already calls it, but the stable API is now `agentsgen fleet scan`.

## Experimental surfaces

These features are opt-in and do not change the default local-only CLI path.

- `agentsgen init . --llm-enhance --llm-provider openai`
- `agentsgen update . --llm-enhance --llm-provider anthropic`
- `agentsgen mcp`

Experimental notes:

- `--llm-enhance` only appends narrative context sections grounded in local `understand` artifacts.
- Provider failures and timeouts fall back to local-only generation.
- MCP currently exposes read and write tools with versioned JSON contracts for `status`, `check`, `detect`, `understand`, `init`, `update`, and `pack`.
- Install optional extras first: `pip install -e ".[llm,mcp]"`.
- Provider-specific notes: `docs/experimental-llm.md`.

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

## Experimental OKF export

`agentsgen okf export` derives an [Open Knowledge Format](https://github.com/GoogleCloudPlatform/knowledge-catalog/tree/main/okf) style markdown bundle from the repo-local AI docs that `agentsgen pack` already generates.

Current export target:

- `docs/ai/okf/index.md`
- `docs/ai/okf/repo/overview.md`
- `docs/ai/okf/repo/architecture.md`
- `docs/ai/okf/repo/runbook.md`
- `docs/ai/okf/repo/test-flow.md`
- `docs/ai/okf/repo/contracts.md`
- `docs/ai/okf/assets/entrypoints.md`

Usage:

```sh
agentsgen pack . --autodetect
agentsgen okf export .
agentsgen okf export . --check
```

Why it exists:

- keep `docs/ai/` as the primary repo-facing output
- add a portable markdown+frontmatter bundle for downstream catalogs, viewers, and agents
- avoid turning OKF into a required internal source format too early

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

Run the built-in smoke entrypoint directly from the activated virtualenv:

```sh
python -m agentsgen._smoke
pytest -q
```

Release automation uses the same smoke entrypoint before tagging.

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
- recommended local smoke entrypoint: `python -m agentsgen._smoke`

## Contributing

Template PRs welcome (shared sections and stack-specific notes).

## Releasing

- Use checklist: `docs/release-checklist.md`
- Run releases from an activated venv (`. .venv/bin/activate`); the script also auto-prefers `.venv/bin/python` when present.
- Write release notes: `RELEASES/template.md -> RELEASES/vX.Y.Z.md`
- Run: `./scripts/release.sh vX.Y.Z A|B|C`
- Shorthand: `./scripts/release.sh A` (auto-suggests next version)
- Tags follow `vX.Y.Z` and should point to the release commit
