# Proof-Loop v0

Proof-loop v0 is an optional ABVX layer for complex tasks.

It does not replace `SET` planning or `Lab` control-plane views. It adds durable task artifacts that make implementation claims easier to verify and review.

## Goals

- freeze a lightweight task contract before execution
- collect evidence in a durable repo-local format
- record an explicit verdict (`pass`, `fail`, `needs-review`)
- keep everything deterministic and safe to regenerate

## Artifact layout

- `docs/ai/tasks/<task-id>/contract.md`
- `docs/ai/tasks/<task-id>/evidence.json`
- `docs/ai/tasks/<task-id>/verdict.json`

## CLI surface

- `agentsgen task init <task-id>`
- `agentsgen task evidence <task-id>`
- `agentsgen task verdict <task-id>`

## v0 constraints

- optional only
- no autonomous loop
- no hidden state outside repo artifacts
- no mandatory `.agent/tasks/...` layout

## Ecosystem role

- `agentsgen`: writes proof artifacts
- `SET`: can optionally run proof-loop steps in CI
- `Lab`: can show read-only proof status per repo/task
