# LLMO Pack

`agentsgen pack` generates and safely updates an AI/LLMO documentation bundle for a repository.

## Generated files (MVP)

- `llms.txt` (default) or `LLMS.md` (`--llms-format md` or config)
- `agents.entrypoints.json`
- `docs/ai/how-to-run.md`
- `docs/ai/how-to-test.md`
- `docs/ai/architecture.md`
- `docs/ai/data-contracts.md`
- `SECURITY_AI.md`
- `CONTRIBUTING_AI.md`
- `README_SNIPPETS.md`

**New file: agents.entrypoints.json**

A machine-readable list of canonical repo commands (install/test/lint/build/run). It’s derived from `.agentsgen.json` and conservative autodetect evidence. Useful for CI summaries and agent tooling.

## Pack file map

| File | Purpose | Primary reader |
| --- | --- | --- |
| `llms.txt` / `LLMS.md` | Compact entrypoint for AI/LLM crawlers and agents | External LLM indexers + coding agents |
| `docs/ai/how-to-run.md` | Exact run commands and environment hints | Coding agents |
| `docs/ai/how-to-test.md` | Test/lint/verification commands | Coding agents + reviewers |
| `docs/ai/architecture.md` | High-level structure and boundaries | Coding agents |
| `docs/ai/data-contracts.md` | Contract-change checklist and invariants | Coding agents + maintainers |
| `SECURITY_AI.md` | Security guardrails for automated edits | Coding agents |
| `CONTRIBUTING_AI.md` | Contribution protocol and output expectations | Coding agents |
| `README_SNIPPETS.md` | Copy-ready README fragments | Maintainers |

## Safety model

Same rules as AGENTS/RUNBOOK generation:

1. If file does not exist -> create with AGENTSGEN markers.
2. If file exists and has markers -> patch only marker ranges.
3. If file exists and has no markers -> do not overwrite; write sibling `*.generated.*`.

Supports preview mode:

- `--dry-run`
- `--print-diff`

## CLI

```bash
agentsgen pack --autodetect --dry-run --print-diff
agentsgen pack
agentsgen pack --check
agentsgen pack --format json --dry-run
```

Optional overrides:

- `--stack python|node|static`
- `--llms-format txt|md`
- `--output-dir docs/ai`
- `--files "llms,how-to-run.md,SECURITY_AI.md"`
- `--check` (non-zero if pack files drift from expected generated content)
- `--format json` (machine-readable summary of actions/status)

## Config (`.agentsgen.json`)

```json
{
  "pack": {
    "enabled": true,
    "llms_format": "txt",
    "output_dir": "docs/ai",
    "files": []
  }
}
```

Notes:

- `files` is an optional allowlist; empty means default bundle.
- Command detection is reused from existing autodetect (`Makefile > package.json scripts > Python heuristics`).
- For mixed/monorepo detection, pack templates use conservative placeholders instead of invented commands.
