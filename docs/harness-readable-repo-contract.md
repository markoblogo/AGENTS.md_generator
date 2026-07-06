# Harness-Readable Repo Contract

`agentsgen` treats a repo as an input surface for agent harnesses, not only as prose for a coding assistant.

A harness needs stable answers before it can run an agent safely:

- what commands exist;
- which files describe architecture and data contracts;
- what checks prove a change;
- which actions require approval;
- which docs are always-loaded vs on-demand;
- how proof, evidence, and review readiness are recorded.

`agentsgen` emits those answers as a small contract:

- `AGENTS.md` and `RUNBOOK.md` for human-readable rules and commands;
- `.agentsgen.json` for marker-managed generation policy;
- `agents.entrypoints.json` for install/test/lint/build/run command discovery;
- `docs/ai/*` for compact repo context, architecture, data contracts, testing, and contribution rules;
- proof-loop task artifacts under `docs/ai/tasks/<task-id>/` when a change needs evidence and verdicts;
- local MCP surface through `agentsgen mcp` when a harness wants stdio access to repo operations.

## Relationship To Harnesses

- The harness owns loop execution, tool calls, memory, permissions, sandboxing, scheduling, observability, and evals.
- `agentsgen` owns the repo-local contract the harness reads before acting.
- ABVX Agent Skills own reusable workflow discipline on top of that contract.

This keeps the layers separate: repo facts stay in the repo, harness policy stays in the runtime, and skills decide which workflow gate to apply.
