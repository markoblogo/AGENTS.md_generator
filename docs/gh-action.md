# GitHub Action: agentsgen-guard

`agentsgen-guard` fails PRs when `AGENTS.md` / `RUNBOOK.md` are missing, invalid, or out of date based on `agentsgen check`.

## Why

- Keep agent instructions consistent across repositories
- Prevent drift in marker-managed sections
- Enforce a safe, repeatable docs workflow in PRs

## Quickstart

```yaml
name: agentsgen-guard

on:
  pull_request:

permissions:
  contents: read

jobs:
  guard:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: markoblogo/AGENTS.md_generator/.github/actions/agentsgen-guard@v0.1.2
        with:
          path: "."
          files: "AGENTS.md,RUNBOOK.md"
          comment: "false"
          pack_check: "false"
```

## Inputs

- `path` (default: `"."`) - target directory to validate
- `files` (default: `"AGENTS.md,RUNBOOK.md"`) - comma-separated files to enforce
- `comment` (default: `"false"`) - post/update a short PR comment on failure (best effort)
- `token` (default: `${{ github.token }}`) - token for comment API calls
- `show_commands` (default: `"true"`) - include local fix commands in logs/comment
- `pack_check` (default: `"false"`) - enforce `agentsgen pack --autodetect --check`
- `pack` (default: `"false"`) - deprecated alias for `pack_check` (kept for backward compatibility)
- `pack_format` (default: `"json"`) - output format for pack check (`text|json`)
- `pack_autodetect` (default: `"true"`) - pass `--autodetect` (or `--no-autodetect`)
- `pack_llms_format` (default: empty) - optional `--llms-format` for pack check
- `pack_output_dir` (default: empty) - optional `--output-dir` for pack check
- `pack_files` (default: empty) - optional newline/comma-separated allowlist passed to `--files`
- `version` (default: `"repo"`) - install mode: `repo` or `pypi`

### Note about `files`

`agentsgen check` currently validates the repo as a whole (no native `--files` CLI flag).
The guard still uses core `check_repo` as source of truth, then filters reported file-specific findings
to match the `files` input. This keeps behavior compatible and conservative.

## Outputs

- `status`: `ok` or `fail`
- `summary`: short human-readable result

## Optional PR comment

Enable comments only when needed.

```yaml
permissions:
  contents: read
  pull-requests: write
```

```yaml
- uses: markoblogo/AGENTS.md_generator/.github/actions/agentsgen-guard@v0.1.2
  with:
    comment: "true"
```

If comment write fails (common on fork PRs with restricted permissions), the action logs a warning and still enforces the check result.

To also guard LLMO pack drift:

```yaml
- uses: markoblogo/AGENTS.md_generator/.github/actions/agentsgen-guard@v0.1.2
  with:
    comment: "false"
    pack_check: "true"
    pack_format: "json"
    pack_autodetect: "true"
    # pack_llms_format: "md"
    # pack_output_dir: "docs/ai"
    # pack_files: |
    #   llms
    #   SECURITY_AI.md
```

Example workflow file in this repo:

- `.github/workflows/agentsgen-guard.example.yml`
- `.github/workflows/agentsgen-ci.yml`

## Local remediation

When guard fails:

```bash
agentsgen init .
agentsgen update .
agentsgen check .
```
