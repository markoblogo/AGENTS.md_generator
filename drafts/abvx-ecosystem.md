# ABVX Ecosystem Draft

This document fixes the current architecture direction for the ABVX development tools ecosystem.

## Goal

Build a compact ecosystem of developer tools that:

- stays small and understandable,
- avoids unnecessary new repos,
- keeps repo-facing logic inside `agentsgen` when possible,
- adds orchestration without turning the system into a monolith.

## Core layers

### 1. `agentsgen`

`agentsgen` is the repo intelligence runtime.

It owns:

- repo docs bootstrap and updates,
- pack/check/detect/status flows,
- deterministic repo artifacts,
- future repo-facing analysis commands such as `analyze`, `meta`, or `health`.

Rule:
- if a tool primarily reads or writes repo files, analyzes repo structure, or emits repo artifacts, it should default to a new `agentsgen` command.

### 2. `abvx-setup`

`abvx-setup` is the orchestration layer.

It should be a separate repo with a GitHub Action entrypoint. Its job is not to reimplement tool logic. Its job is to:

- install required tools,
- resolve enabled modules,
- run them in the right order,
- expose a stable configuration surface for CI.

Rule:
- `abvx-setup` should stay thin. It orchestrates existing tools instead of absorbing their logic.

### 3. `lab.abvx`

`lab.abvx` is the public catalog and later the control plane UI.

It owns:

- tool discovery,
- public tool pages,
- ecosystem naming,
- later: repo config UI, status views, and orchestration controls.

Rule:
- the Lab is the public directory and dashboard surface, not the implementation runtime for repo tools.

### 4. Standalone tools

Some tools should remain separate repos because they can live independently of `agentsgen`.

Examples:

- `git-tweet`
- `abvx-shortener`
- `asciitheme`

Rule:
- a standalone tool should justify its own repo by being independently useful outside `agentsgen`.

## Tool taxonomy

### Type A: `agentsgen` command

Use this when the tool:

- works on a local repo,
- emits repo artifacts,
- fits repo setup / repo docs / repo analysis / repo CI guard workflows,
- does not require its own backend or long-running service.

Examples:

- `init`
- `update`
- `pack`
- `check`
- `detect`
- `status`
- `snippets`
- `repomap`
- future `analyze`
- future `meta`
- future `repo-health`

### Type B: standalone tool

Use this when the tool:

- has its own runtime, service, or API,
- is useful outside repo setup,
- can be adopted independently of `agentsgen`.

Examples:

- `git-tweet`
- `abvx-shortener`
- `asciitheme`

### Type C: control-plane integration

Use this for orchestration and management capabilities rather than end-user tools.

Examples:

- repo configuration registry,
- workflow installer,
- dashboard status sync,
- PR-based config apply.

## `llmo-abvx` direction

`llmo-abvx` should not survive as a full SaaS product inside the ecosystem if its remaining value is only a few reusable capabilities.

The likely migration path is:

### Move into `agentsgen`

- external URL analyzer -> `agentsgen analyze <url>`
- metadata generator -> `agentsgen meta <url>`
- site-oriented `llms.txt` generation -> `agentsgen pack --site <url>`

### Do not preserve

- Stripe
- Supabase SaaS scaffolding
- NextAuth shell
- admin panel
- general product shell not required for repo tooling

Rule:
- only reusable capability logic should move forward; SaaS scaffolding should be dropped unless it is still required by a standalone product decision.

## Recommended roadmap

### Phase 1: capability extraction

1. Audit `llmo-abvx`
2. Identify reusable prompts and logic
3. Port analyzer into `agentsgen`
4. Port metadata generation into `agentsgen`
5. Extend `pack` with site-aware mode only after the first two commands are stable

### Phase 2: orchestration

1. Create `abvx-setup`
2. Ship a minimal v0.1 Action:
   - install `agentsgen`
   - run `agentsgen init`
   - optionally run `agentsgen pack`
   - optionally run `agentsgen check --all --ci`
3. Add presets and registry-driven orchestration later

### Phase 3: catalog + dashboard

1. Add `abvx-setup` page in `lab.abvx`
2. Keep Lab as a public catalog first
3. Add read-only dashboard views next
4. Add config apply / PR generation only after the config schema is stable

### Phase 4: archive old shell

When the reusable capability logic has moved:

- archive `llmo-abvx`
- leave a README note pointing to the replacement commands

## Backend direction for dashboard

### Default recommendation: GitHub as backend

Use GitHub as the first backend for the personal dashboard.

Why:

- lower operational complexity,
- no separate OAuth/backend required at the start,
- config changes are naturally reviewable through PRs,
- repo state already lives in GitHub.

Good first capabilities:

- show configured repos,
- show enabled tools,
- show last workflow status,
- generate PRs to apply config changes.

### Optional upgrade: Cloudflare Worker backend

Use a Worker only after the GitHub-backed approach becomes limiting.

Valid reasons to add a Worker later:

- direct repo writes without PRs,
- background sync,
- OAuth flows,
- server-side token management,
- cross-repo state aggregation that becomes awkward in pure GitHub mode.

Rule:
- do not start with a Worker unless GitHub-backed configuration already proves too limiting.

## Non-goals

- No new monolith that swallows all tools.
- No automatic new repo creation for every idea.
- No orchestration layer that duplicates tool internals.
- No dashboard backend before the tool contract and repo config schema are stable.

## Working definition

- `agentsgen` = repo intelligence runtime
- `abvx-setup` = orchestration contract
- `lab.abvx` = catalog + control plane
- standalone repos = independent products

