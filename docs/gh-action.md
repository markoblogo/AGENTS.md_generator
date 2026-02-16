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
      - uses: markoblogo/AGENTS.md_generator/.github/actions/agentsgen-guard@v0.1.0
        with:
          path: "."
          files: "AGENTS.md,RUNBOOK.md"
          comment: "false"
```

## Inputs

- `path` (default: `"."`) - target directory to validate
- `files` (default: `"AGENTS.md,RUNBOOK.md"`) - comma-separated files to enforce
- `comment` (default: `"false"`) - post/update a short PR comment on failure (best effort)
- `token` (default: `${{ github.token }}`) - token for comment API calls
- `show_commands` (default: `"true"`) - include local fix commands in logs/comment
- `version` (default: `"repo"`) - install mode: `repo` or `pypi`

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
- uses: markoblogo/AGENTS.md_generator/.github/actions/agentsgen-guard@v0.1.0
  with:
    comment: "true"
```

If comment write fails (common on fork PRs with restricted permissions), the action logs a warning and still enforces the check result.

## Local remediation

When guard fails:

```bash
agentsgen init .
agentsgen update .
agentsgen check .
```

