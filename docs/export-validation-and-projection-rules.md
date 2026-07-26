# Export Validation And Projection Rules

`agentsgen` may emit multiple repo-contract projections, but each export class
should validate against its own drift rule.

## Export classes

- `core-docs` — `AGENTS.md`, `RUNBOOK.md`
- `entrypoints` — `agents.entrypoints.json`
- `pack` — `docs/ai/*`
- `snippets` — `README_SNIPPETS.generated.md`
- `discovery` — public metadata such as `llms.txt` or site discovery files
- `task-artifacts` — `docs/ai/tasks/<task-id>/...`

## Validation gate

Do not rely only on one broad `check`.

Each export class should be individually understandable as:

- generated from which source;
- checked by which command or mode;
- safe to commit or safe to leave local-only;
- allowed to differ by harness capability or not.

## Projection rules

Use idiomatic harness-specific export when:

- the harness can consume a richer native file shape;
- the richer shape preserves more contract meaning;
- the projection remains reproducible from repo truth.

Use a fallback export when:

- the harness cannot consume the richer surface;
- adding a native export would create fragile or duplicative maintenance;
- the pack bundle already preserves the necessary minimum.

## Boundary language

Keep these surfaces distinct:

- repo contract — source-owned repo truth;
- generated manifests — reproducible machine-readable projections;
- local MCP surface — local execution helper;
- public discovery files — site/discovery metadata;
- package distribution — install and release surfaces.

Do not let one of these surfaces impersonate another.
