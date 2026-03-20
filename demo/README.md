# Demo

From repo root:

```sh
pipx install .
```

Then:

```sh
mkdir -p /tmp/agentsgen-demo && cd /tmp/agentsgen-demo
agentsgen presets
agentsgen init
# edit AGENTS.md outside markers
agentsgen update
agentsgen status .
agentsgen snippets .
agentsgen check
```
