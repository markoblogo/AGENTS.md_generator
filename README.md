# AGENTS.md Generator (`agentsgen`)

Generate repo instructions, preserve handwritten rules, and catch stale command references in pull requests.

[![CI](https://github.com/markoblogo/AGENTS.md_generator/actions/workflows/ci.yml/badge.svg)](https://github.com/markoblogo/AGENTS.md_generator/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/agentsgen)](https://pypi.org/project/agentsgen/)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

## Start in one minute

Requires Python 3.11+. Install it as an isolated CLI with
[uv](https://docs.astral.sh/uv/) (recommended) or
[pipx](https://pipx.pypa.io/stable/installation/).
Run inside your repository:

<!-- AGENTSGEN:SNIPPET name=install -->
```sh
uv tool install agentsgen
```
<!-- AGENTSGEN:ENDSNIPPET -->

```sh
agentsgen init . --defaults --autodetect
agentsgen check . --ci
```

Creates `.agentsgen.json`, `AGENTS.md`, and `RUNBOOK.md` (plus starter prompts).
Review the detected commands in `.agentsgen.json` before committing.
No API key is required for these commands.

Prefer pipx? Run `pipx install agentsgen`.

Already have handwritten instructions? The original stays unchanged and proposals
appear in `AGENTS.generated.md` / `RUNBOOK.generated.md`. Review and copy the
sections you want into your original file, retaining their markers. Until then,
`check` reports the unmanaged document; it does not silently adopt it.

## See what it catches

```text
package.json: remove scripts.test
AGENTS.md:    still recommends npm test
agentsgen check . --ci
→ DRIFT (exit 1)
```

The JSON report identifies the missing script and asks you to review
`.agentsgen.json`. The checker reads files; it never runs your project commands.

Three [reproducible demos](demo/README.md) cover handwritten preservation,
stale-command detection, and repeatable setup without a README.

## Safe updates

```sh
agentsgen update . --dry-run --print-diff
agentsgen update .
agentsgen check . --report
```

Only `AGENTSGEN` marker sections are regenerated. Text outside them stays yours.
Missing files are created; existing files without markers get generated siblings.
Update config when your toolchain changes; `fix` cannot infer your intended replacement command.

## Add a pull-request guard

```yaml
name: Agent instructions
on: [push, pull_request]
permissions:
  contents: read
jobs:
  check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v7
      - uses: markoblogo/AGENTS.md_generator/.github/actions/agentsgen-guard@v0.5.1
```

For immutable dependencies, pin the action to the reviewed release commit SHA.
[Advanced guard options](docs/gh-action.md) include optional pack checks and PR comments.

## Optional context bundle

```sh
agentsgen pack . --autodetect
agentsgen check . --pack-check --ci
```

The bundle provides command manifests and on-demand documents under `docs/ai/`.
Use `--all` only when you want pack and README snippet validation too.
Without `README.md`, aggregate snippet checks are explicitly skipped.

## What is verified

| Check | Scope |
| --- | --- |
| Core documents | Required markers and generated sections agree with config |
| Commands | Root npm/pnpm/yarn script references and literal Make targets exist |
| Config paths | Concrete configured paths exist |
| Optional pack/snippets | Generated output matches current inputs |

Compound commands, custom executables, dynamic Make targets, and patterns are
reported as **not verified**. Existence does not prove that a command succeeds.
Run your actual tests separately. `check --format json` includes warning details.
The readiness score is a heuristic, not a measure of AI task quality.

## ABVX ecosystem

**One repository:** install agentsgen directly; SET is optional.
**Workflow orchestration:** [SET](https://github.com/markoblogo/SET) adds presets,
repo-local planning configuration, and reviewable workflow exports.
The tested stack is **agentsgen 0.5.1 + SET 0.4.0 + ID 0.5.2**.
See the [SET guide](docs/set-integration.md) and
[ecosystem integration guide](docs/ecosystem-integrations.md).

[abvx-agent-skills](https://github.com/markoblogo/abvx-agent-skills) supplies reusable
workflows; it is not installed or required by this CLI.
[ID](https://github.com/markoblogo/ID) supplies portable human context, with
`docs/ai/id-context.json` as the explicit bridge. [Git Tweet](https://github.com/markoblogo/git-tweet)
can publish a completed GitHub Release downstream; it is not part of generation or CI.

## Documentation and contributions

- [CLI and experimental features](docs/cli-reference.md): fleet, repo maps, MCP, proof artifacts, reflection and exports.
- [Recipes](recipes/): Python, Next.js, monorepo and Node CLI starting configs.
- [Compatibility and limits](docs/harness-capability-matrix.md): reading a file is distinct from native client integration.
- [Release checklist](docs/release-checklist.md) and [contributing](CONTRIBUTING_AI.md).

Report a bug with the package version, a minimal repo fixture, the command,
and expected/actual output. Remove secrets before sharing a fixture.

Contributor setup: `python3 -m venv .venv`, activate it, then `pip install -e ".[dev]"`.
Run `pytest -q`, `ruff check .`, `ruff format --check .`, and `mypy src`.
