# Multi-Harness Export Contract

`agentsgen` may export one repo contract into multiple harness-readable
surfaces, but it should do so without collapsing everything into one lowest
common denominator format.

This is a compact adaptation of the useful part of multi-harness agent
marketplace repos such as `wshobson/agents`: one source tree, harness-native
outputs, explicit validation, and clear generated/committed boundaries.

## Goal

Keep one durable source of truth for repo context while allowing different
agent harnesses to consume idiomatic outputs.

## Core rule

The source contract stays canonical. Harness-native files are projections.

That means:

- source config and repo-owned docs stay human-reviewed;
- generated harness artifacts may differ by harness capability;
- no harness output becomes a second source of truth.

## What belongs in the source layer

The source layer includes:

- `.agentsgen.json`
- marker-managed repo docs such as `AGENTS.md` and `RUNBOOK.md`
- pack inputs under repo-owned docs
- stable commands, entrypoints, proof paths, and policy boundaries

## What belongs in the generated layer

The generated layer may include:

- `agents.entrypoints.json`
- pack bundles under `docs/ai/`
- `README_SNIPPETS.generated.md`
- future harness-specific exports, manifests, or metadata files

Generated artifacts must remain reproducible from the source layer.

## Generated / committed boundary

Generated artifacts may be committed when they are part of the published repo
contract, CI guard surface, or public discovery surface.

Commit generated artifacts when they:

- are consumed directly by agent tooling or CI;
- help reviewers inspect the effective repo contract;
- are expected to stay stable across machines;
- are validated in PRs.

Do not commit generated artifacts when they are:

- local cache or machine-specific noise;
- disposable debug output;
- temporary experiments that are not part of the maintained contract.

## Harness-native rule

Different harnesses may need different projections.

Allowed:

- harness-specific metadata files;
- slightly different field layouts per harness;
- capability-aware omission when a harness cannot consume a feature.

Not allowed:

- fake parity claims;
- silently dropping important contract meaning;
- forcing every harness through the weakest format if a better native export is
  available.

## Validation

Any multi-harness export should be checked for:

- source completeness;
- generated artifact reproducibility;
- drift between committed generated files and regenerated output;
- stable field ownership;
- discoverability from the main README or docs index.

## Boundary

- `agentsgen` does not become a plugin marketplace;
- it does not vendor external harness runtimes;
- it does not promise support for every agent client;
- it exports repo-readable contract surfaces, not an omni-agent platform.
