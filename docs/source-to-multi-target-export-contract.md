# Source To Multi-Target Export Contract

`agentsgen` may adapt the useful part of `yusufkaraaslan/Skill_Seekers`:
prepare one reviewed source configuration, then project it into multiple
agent-readable targets.

This is a contract for repo-context export. It is not permission to install
Skill Seekers, scrape sources automatically, upload generated assets, or publish
skills.

Source: https://github.com/yusufkaraaslan/Skill_Seekers

## Source config

Every generated knowledge asset starts from an explicit source config:

- source kind: docs, repo, local codebase, PDF, video, OpenAPI, or other;
- source location and owner;
- source version, commit, date, or checksum when available;
- allowed depth: `quick`, `standard`, or `comprehensive`;
- included and excluded paths;
- secrets and data-egress risk;
- intended export targets.

## Generated assets

Generated assets are outputs, not source truth.

They may include:

- agent context markdown;
- generated skill drafts;
- RAG chunks;
- platform-specific projection files;
- quality reports;
- source manifests.

Generated assets must be reproducible or explicitly marked as reviewed manual
output.

## Target projections

Target projections can differ by harness:

- Codex / AGENTS surfaces;
- Claude skill draft;
- Cursor or IDE context file;
- generic Markdown or JSON;
- RAG chunk bundle.

Do not claim target parity unless each projection has been checked. If a target
cannot safely represent the source asset, mark it `unavailable`.

## Required lifecycle

- `dry_run`: inspect planned sources and outputs before generation.
- `generate`: create local assets only.
- `quality_gate`: run structural, provenance, and target-fit checks.
- `review`: human accepts, revises, or rejects the generated asset.
- `publish`: separate explicit action; never automatic.

## Boundary

Do not enable:

- auto-publish to marketplaces;
- cloud/vector uploads;
- broad crawling from a guessed source;
- hidden LLM enhancement without a recorded model/agent;
- generated files as a second source of truth.

If this contract conflicts with `docs/multi-harness-export-contract.md`, the
existing `agentsgen` source-owned and generated-owned boundary wins.
