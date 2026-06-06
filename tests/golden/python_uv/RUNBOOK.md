# RUNBOOK.md

## Quickstart

<!-- AGENTSGEN:START section=quickstart -->
```sh
uv run pytest
```
```sh
uv run ruff check .
```
<!-- AGENTSGEN:END section=quickstart -->

## Common Tasks

<!-- AGENTSGEN:START section=common_tasks -->
- Run tests: `uv run pytest`
- Lint: `uv run ruff check .`
- Build: (not set)
<!-- AGENTSGEN:END section=common_tasks -->

## Troubleshooting

<!-- AGENTSGEN:START section=troubleshooting -->
- If dependencies fail: verify the expected Node/Python version for this repo.
- If tests are flaky: re-run once, then isolate and fix the root cause.
- If environment is unclear: ask for the expected OS/tooling versions.
<!-- AGENTSGEN:END section=troubleshooting -->
