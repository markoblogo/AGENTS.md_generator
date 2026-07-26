# Repo Route Hints And Generated Boundary

`agentsgen` should help a repo declare where work should go next without
pretending to own execution.

That means two things:

- generated agent files may carry compact route hints;
- those hints must stay separate from generated ownership and execution
  authority.

## Repo route hints

Generated repo surfaces may include short hints such as:

- work directly in this repo;
- consult a repo-local skill or review contract;
- escalate to `SET` for orchestration or approval packaging;
- stop at local-only guidance.

Hints should stay compact and procedural. They are guidance for a consuming
agent, not a hidden workflow engine.

## Good hint shape

A useful route hint says:

- which route class applies;
- why it applies;
- where the next governing file lives;
- whether the route is local-only, proposal-only, or mutation-capable.

Example classes:

- `repo_direct`
- `review_contract`
- `set_orchestration`
- `local_reference_only`

## Generated boundary

Keep these layers distinct:

- source-owned repo contract;
- generated repo projections;
- local helper surfaces;
- external orchestration surfaces.

Generated files may point at a route, but they must not impersonate the source
of truth for authority.

## Commit boundary

Commit generated route hints only when they are:

- reproducible from repo truth;
- stable enough to review;
- useful to downstream agents or CI.

Keep them local when they are:

- host-specific;
- experiment-only;
- derived from temporary local tooling;
- likely to drift without repo-owned inputs.

## Boundary

- `agentsgen` does not ship tasks;
- it does not approve routes;
- it does not replace repo policy or `SET`;
- it only helps project the repo's intended next-step guidance safely.

## Attribution

Adapted from the routing emphasis in
[AgentSystemLabs/core](https://github.com/AgentSystemLabs/core), rewritten for
repo-generated agent context and generated-file safety.
