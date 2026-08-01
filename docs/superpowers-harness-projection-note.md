# Superpowers Harness Projection Note

`obra/superpowers` is useful to `agentsgen` mainly as a multi-harness packaging
reference.

It demonstrates that the same agent methodology can surface through different
harness-specific files and plugin layouts. `agentsgen` should adapt that lesson
without becoming a plugin marketplace or agent runtime.

Source: https://github.com/obra/superpowers

## Adopted minimum

When a repo contract is projected into several agent harnesses:

- keep one source-owned repo contract;
- emit harness-specific projections only when the harness can consume them;
- mark capability as `declared`, `probed`, `confirmed`, or `unavailable`;
- keep generated files reproducible and separately registered;
- do not claim feature parity across Codex, Claude, Cursor, OpenCode, Kimi, or
  other clients unless it has been confirmed.

## Session-start hints

Generated surfaces may include compact startup hints such as:

- read order;
- proof commands;
- owner approval boundary;
- local skill references;
- route hints such as `design_before_plan`, `review_first`, or
  `verify_before_ship`.

Those hints remain guidance. They do not install Superpowers, grant tool
authority, create worktrees, run subagents, or override repo-local `AGENTS.md`
instructions.

## Generated boundary

Superpowers-inspired exports are acceptable when they are:

- derived from source-owned config or docs;
- reproducible by `agentsgen`;
- listed in the generated artifact registry;
- validated per export class;
- safe to omit for harnesses that cannot consume them.

Reject exports that introduce a second source of truth, vendor a full external
runtime, or require a hidden marketplace/plugin dependency.
