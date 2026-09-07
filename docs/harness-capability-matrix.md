# Client compatibility

The CLI and CI guard operate on files and do not depend on an AI client.
The release suite verifies file generation, preservation, drift checks and JSON contracts.

| Surface | Verified here | Client setup |
| --- | --- | --- |
| AGENTS.md / RUNBOOK.md | Generated files and marker-safe updates | Point your client at the files; automatic loading depends on the client |
| Command manifests and docs/ai | JSON contracts and reproducible outputs | Explicit file access or an integration |
| MCP | Server contract tests | Optional `mcp` extra and local stdio client configuration |
| Native Claude/Cursor/Copilot rules | Not exported by the stable core | No automatic parity claim |

We do not currently run an end-to-end client matrix for Codex, Claude Code, Cursor,
Copilot or Aider. File readability is not proof of native discovery or identical behavior.
Multi-harness design notes describe possible future projections, not a support guarantee.
