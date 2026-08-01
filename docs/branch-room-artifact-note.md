# Branch Room Artifact Note

`agentsgen` may generate or point to a branch-room artifact: a compact file that
acts like a project room for one branch, PR, feature, fix, or incident.

This adapts the useful part of `block/buzz`: branch context, patches, CI,
review, and merge decisions should live in one auditable record. `agentsgen`
does not adopt Buzz, Nostr, a relay, or a chat workspace.

Source: https://github.com/block/buzz

## Artifact purpose

A branch-room artifact should answer:

- what is this branch trying to do?
- what context should an agent read first?
- what files or modules are in scope?
- what proof commands or CI checks matter?
- what review or owner approval is required?
- what decision closed the work?

## Suggested fields

```text
room_id:
branch:
pr:
project:
owner:
requested_by:
scope:
out_of_scope:
read_order:
proof_commands:
evidence_refs:
review_refs:
decision_state:
follow_up:
```

## Generated boundary

`agentsgen` may emit this as:

- `docs/ai/branch-room.md`;
- `docs/ai/tasks/<task-id>/room.md`;
- a README snippet pointing to an existing PR/task artifact.

Generated room artifacts are guidance and evidence indexes. They do not create
execution authority, run agents, merge branches, or publish changes.

## Acceptance rule

A branch-room artifact is useful only when it stays short, source-linked, and
specific to one unit of work. If it becomes a generic status dashboard, split it
or archive it.
