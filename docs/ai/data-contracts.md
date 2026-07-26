# Data Contracts (AI)

<!-- AGENTSGEN:START section=data_contracts -->
## Contract checklist
- Document request/response shapes before changing behavior.
- Keep backward compatibility unless task explicitly allows breakage.
- Add tests when changing serialization, schemas, or external payloads.

## Repository hints
- Config locations: `Makefile`, `pyproject.toml`, `.github/workflows/`
- Source dirs: `src`

## Route hints
- `repo_direct`: normal repo edits and verification happen here.
- `review_contract`: if behavior, safety, or release confidence is unclear, route to the repo's review contract first.
- `set_orchestration`: if work needs cross-repo packaging, explicit approval gates, or reusable route receipts, escalate to `SET`.
- `local_reference_only`: generated hints describe next governing files, not execution authority.

## TODO (maintainer)
- List critical contract files/endpoints for this repo.
<!-- AGENTSGEN:END section=data_contracts -->
