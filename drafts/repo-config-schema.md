# Repo Config Schema Draft

This document defines the first configuration model for ABVX ecosystem orchestration.

The same config should be usable by:

- `abvx-setup`
- future `lab.abvx` dashboard views
- PR-based config apply flows

## Goals

- simple enough for manual review,
- stable enough for automation,
- explicit enough to avoid hidden behavior,
- extensible enough for new tools later.

## Proposed schema (v1)

```yaml
version: 1
repo: markoblogo/example-repo

site:
  url: https://example.com

tools:
  agentsgen:
    init: true
    pack: true
    check: true
    repomap: false
    snippets: false
    analyze_url: null
    meta_url: null

  git_tweet:
    enabled: false

presets:
  - repo-docs
  - ci-guard
```

## Top-level fields

### `version`

Schema version.

Required.

### `repo`

Canonical repository name in `owner/name` format.

Required.

### `site`

Optional site-related data used by URL-based tools.

Suggested fields:

- `url`

### `tools`

Tool configuration grouped by package or product boundary.

Required.

### `presets`

Optional list of named presets that expand to a known baseline.

Examples:

- `minimal`
- `repo-docs`
- `ci-guard`
- `site-ai`

Rule:
- explicit tool values should override preset defaults.

## `agentsgen` block

This block is for Type A repo tools.

Example:

```yaml
tools:
  agentsgen:
    init: true
    pack: true
    check: true
    repomap: true
    snippets: false
    analyze_url: https://example.com
    meta_url: https://example.com
```

Interpretation:

- boolean flags enable or disable commands,
- URL fields are command inputs,
- absent values should behave the same as `false` or `null`, depending on the field.

## Standalone tool blocks

Standalone tools should get their own block under `tools`.

Example:

```yaml
tools:
  git_tweet:
    enabled: true
```

Later versions can add nested settings, but v1 should stay small.

## Preset behavior

Presets should be treated as named bundles, not as hidden code paths.

Examples:

### `minimal`

- `agentsgen.init=true`

### `repo-docs`

- `agentsgen.init=true`
- `agentsgen.pack=true`
- `agentsgen.check=true`

### `ci-guard`

- `agentsgen.check=true`

### `site-ai`

- `agentsgen.analyze_url=<site.url>`
- `agentsgen.meta_url=<site.url>`
- optional later: `agentsgen.pack --site`

## Where this config should live

Two likely options:

### Option A: per-repo config file

Store config in each target repo.

Pros:

- local ownership,
- changes review naturally with repo code,
- easier repo-specific overrides.

### Option B: central registry

Store config in a central repo such as `lab.abvx`.

Pros:

- easy portfolio overview,
- easier dashboard control,
- easy multi-repo inventory.

Recommended near-term approach:

- central registry first for visibility,
- PR-based apply into target repos where needed.

## Non-goals for v1

- no secrets in config,
- no runtime auth tokens,
- no complex conditional logic,
- no multi-environment matrix,
- no per-step shell overrides unless they become necessary later.

## Validation rules

At minimum, schema validation should check:

- `version` is supported,
- `repo` is present,
- `tools` is an object,
- known tool blocks have known fields,
- preset names are from an allowed list.

## Example with future growth in mind

```yaml
version: 1
repo: markoblogo/repo-c

site:
  url: https://repo-c.example

tools:
  agentsgen:
    init: true
    pack: true
    check: true
    repomap: true
    snippets: true
    analyze_url: https://repo-c.example
    meta_url: https://repo-c.example

  git_tweet:
    enabled: true

presets:
  - repo-docs
  - site-ai
```

This keeps the model explicit while still leaving room for more tools later.

