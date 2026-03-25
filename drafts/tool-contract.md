# Tool Contract Draft

This document defines how a new tool joins the ABVX ecosystem.

The purpose is to avoid ad-hoc integration and to make every new tool predictable for:

- `agentsgen`
- `abvx-setup`
- `lab.abvx`
- future dashboard/config workflows

## First decision: what kind of tool is it?

Every new tool must be classified before implementation.

### Type A: `agentsgen` command

Choose this when the tool:

- works with repo files,
- emits repo artifacts,
- runs locally or in CI,
- fits repo setup, repo docs, repo analysis, or repo validation.

### Type B: standalone tool

Choose this when the tool:

- has an independent runtime or product boundary,
- is useful outside `agentsgen`,
- can be adopted on its own.

### Type C: control-plane integration

Choose this when the work is about orchestration, configuration, or dashboard state instead of a user-facing tool.

## Contract for Type A tools

Minimum shape:

```text
src/agentsgen/
├── commands/
│   └── mycommand.py
├── modules/
│   └── mymodule.py
└── tests/
    └── test_mycommand.py
```

Rules:

- keep business logic in a module, not in the CLI wrapper,
- keep the CLI wrapper thin,
- add at least one smoke or fixture test,
- prefer deterministic outputs,
- expose machine-readable output when it helps CI or orchestration.

### Required metadata

Each command should have enough metadata to be called by `abvx-setup`.

Suggested contract shape:

```yaml
id: repomap
kind: agentsgen-command
package: agentsgen
entrypoint: agentsgen understand
inputs:
  - path
  - format
outputs:
  - docs/ai/repomap.md
  - docs/ai/graph.mmd
  - agents.knowledge.json
lab:
  slug: repomap
  live_url: https://agentsmd.abvx.xyz/
orchestrator:
  input_flag: repomap
  enabled_by_default: false
```

## Contract for Type B tools

Minimum requirements:

1. Separate repo
2. Clear entrypoint (`action.yml`, CLI, service endpoint, or webhook path)
3. Self-description in repo docs
4. Lab tool page
5. Orchestrator registration

Suggested contract shape:

```yaml
id: git-tweet
kind: standalone
repo: markoblogo/git-tweet
entrypoint: webhook
inputs:
  - repository
  - release_event
outputs:
  - x_post
  - bluesky_post
lab:
  slug: git-tweet
  live_url: https://git-tweet.abvx.xyz/
orchestrator:
  input_flag: git_tweet
  enabled_by_default: false
```

## Lab registration rules

A tool is not considered part of the ecosystem until it is registered in `lab.abvx`.

Minimum Lab requirements:

- tool page under `docs/tools/<slug>/index.html`
- home card entry
- correct one-liner
- GitHub / Docs / Live links where applicable
- sitemap entry
- `NEW` sticker moved if the tool is the most recent addition

## Orchestrator registration rules

If a tool should be callable by `abvx-setup`, it must define:

- a stable id,
- its type,
- its entrypoint,
- required inputs,
- expected outputs,
- whether it is enabled by default,
- dependency notes if ordering matters.

Examples of dependency notes:

- `pack` may depend on repo config being present
- `check --all` may depend on `pack`
- release posting tools should not be part of default bootstrap presets

## Categories

Every tool should also declare one category for ecosystem grouping.

Initial categories:

- `repo-docs`
- `repo-analysis`
- `ci-guard`
- `release-distribution`
- `developer-experience`

This is useful for:

- presets,
- dashboard filters,
- Lab organization,
- future reporting.

## Checklist for a new tool

```text
[ ] Tool type chosen (A / B / C)
[ ] Contract fields defined
[ ] Tests added
[ ] Docs updated
[ ] Lab page added or updated
[ ] Orchestrator registration added
[ ] NEW sticker rule applied if needed
```

## Rule of restraint

Do not create a new repo just because it feels organizationally neat.

Default to a new `agentsgen` command unless the tool clearly needs:

- its own runtime,
- its own deployment,
- or independent product identity.

