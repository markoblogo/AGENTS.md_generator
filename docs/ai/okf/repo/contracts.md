---
type: "Data Contract"
title: "Data Contracts"
description: "Compatibility, invariants, and change-safety guidance."
tags:
  - "repo"
  - "contracts"
  - "compatibility"
canonical: "docs/ai/data-contracts.md"
source: "agentsgen"
status: "active"
kind: "contracts"
---
# Data Contracts (AI)

<!-- AGENTSGEN:START section=data_contracts -->
## Contract checklist
- Document request/response shapes before changing behavior.
- Keep backward compatibility unless task explicitly allows breakage.
- Add tests when changing serialization, schemas, or external payloads.

## Repository hints
- Config locations: `Makefile`, `pyproject.toml`, `.github/workflows/`
- Source dirs: `src`

## TODO (maintainer)
- List critical contract files/endpoints for this repo.
<!-- AGENTSGEN:END section=data_contracts -->

## Maintainer route hints
- `repo_direct`: normal repo edits and verification happen here.
- `review_contract`: if behavior, safety, or release confidence is unclear, route to the repo's review contract first.
- `set_orchestration`: cross-repo packaging and reusable route receipts belong in SET.
- `local_reference_only`: generated hints describe next governing files, not execution authority.
