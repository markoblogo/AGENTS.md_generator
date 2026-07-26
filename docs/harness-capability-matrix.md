# Harness Capability Matrix

`agentsgen` should describe harness support as an explicit matrix, not as a
generic “works everywhere” claim.

## States

Use only these availability states:

- `confirmed` — the repo ships and validates this surface today;
- `partial` — a useful subset exists, but not the full surface;
- `unavailable` — not exported or not supported;
- `local_only` — available only in local execution, not as a hosted/public
  surface.

Do not imply parity when the harnesses consume different projections.

## Current matrix

| Surface | Codex | Claude Code | Cursor | Copilot Workspace | Aider | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| `AGENTS.md` / `RUNBOOK.md` | confirmed | confirmed | confirmed | confirmed | confirmed | repo-readable core contract |
| `agents.entrypoints.json` | confirmed | confirmed | confirmed | confirmed | partial | machine-readable command surface; usefulness depends on harness integration |
| `docs/ai/*` pack bundle | confirmed | confirmed | confirmed | confirmed | partial | good general fallback for harnesses that can read files but not richer manifests |
| `docs/ai/id-context.json` | confirmed | confirmed | confirmed | confirmed | partial | repo-local handoff surface for `ID` / orchestration-aware flows |
| local MCP (`agentsgen mcp`) | local_only | local_only | local_only | local_only | local_only | stdio/local execution only, not a hosted endpoint |
| public discovery files | confirmed | confirmed | confirmed | confirmed | confirmed | site-level discovery, not runtime execution authority |

## Rule

If one harness can consume a richer native export than another, document the
difference and keep the richer export.

Fallback is allowed. Fake parity is not.
