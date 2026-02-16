# LLMO Pack

`agentsgen pack` generates and safely updates an AI/LLMO documentation bundle for a repository.

## Generated files (MVP)

- `llms.txt` (default) or `LLMS.md` (`--llms-format md` or config)
- `docs/ai/how-to-run.md`
- `docs/ai/how-to-test.md`
- `docs/ai/architecture.md`
- `docs/ai/data-contracts.md`
- `SECURITY_AI.md`
- `CONTRIBUTING_AI.md`
- `README_SNIPPETS.md`

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
```

Optional overrides:

- `--stack python|node|static`
- `--llms-format txt|md`
- `--output-dir docs/ai`
- `--files "llms,how-to-run.md,SECURITY_AI.md"`

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

