# Ecosystem integrations

Tested release set: **agentsgen 0.5.1 + SET 0.4.0 + ID 0.5.2**. ABVX Agent
Skills 0.15.0 is an optional workflow library. Each product remains independently
installable and has a narrow responsibility.

| Product | Responsibility | Integration boundary |
| --- | --- | --- |
| agentsgen | Repository commands, constraints, and generated context | Produces reviewed files and CI checks |
| [ID](https://github.com/markoblogo/ID) | Portable human and policy context | `docs/ai/id-context.json`; load `soul.md` first and expand only when needed |
| [SET](https://github.com/markoblogo/SET) | Reviewable orchestration and planning | Pin `markoblogo/SET@v0.4.0`; agentsgen remains usable without it |
| [ABVX Agent Skills](https://github.com/markoblogo/abvx-agent-skills) | Reusable task workflows | Opt in per task; no agentsgen runtime dependency |
| [Git Tweet](https://github.com/markoblogo/git-tweet) | Release-to-social publishing | Consumes a published GitHub Release downstream; no source-code coupling |

## Recommended flow

1. Use agentsgen to generate and verify lean repository context.
2. Add ID only when the task needs human preferences or policy context.
3. Use SET for a repeatable multi-step workflow or exported plan.
4. Activate individual skills for the work being performed.
5. After the reviewed change becomes a GitHub Release, let Git Tweet turn that
   release into a social draft or post according to its own approval policy.

This boundary keeps release announcements factual: Git Tweet receives a completed
release, while agentsgen remains focused on repository readiness and evidence.
