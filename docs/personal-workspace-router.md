# Personal Workspace Router

`agentsgen` is repo-scoped by default, but the same contract pattern also works for a local personal workspace that spans multiple repos and life/work domains.

The useful shape is a root router plus small on-demand domain contexts:

```text
WORKSPACE/
├── AGENTS.md
├── MEMORY.md
├── DECISIONS.md
├── ROUTING-LOG.md
└── domains/
    ├── lab/
    ├── index/
    ├── mn7r/
    ├── cropto/
    ├── content/
    └── personal/
```

## Layer Roles

- `AGENTS.md`: root routing map, work style, approval policy, and memory rules.
- `MEMORY.md`: user-triggered persistent memory only.
- `DECISIONS.md`: durable preference signals from meaningful forks.
- `ROUTING-LOG.md`: routing corrections and repeated ambiguity patterns, not every successful route.
- `domains/<name>/AGENTS.md`: local instructions, repo paths, boundaries, and default stance for that domain.
- `domains/<name>/MEMORY.md`: isolated memory for the domain.

## Rules

- Read only the routed domain context, not every domain.
- Ask a routing question only when the wrong route would create real risk or wasted work.
- Write memory only when the user explicitly asks.
- Log routing corrections sparingly.
- Keep secrets, credentials, private contacts, and bulky transcripts out of durable memory.

This is not a replacement for repo-local `AGENTS.md`. It is a local operating layer above repos: the workspace routes the request, then the selected repo contract governs implementation.
