# Demo

From repo root:

```sh
pipx install git+https://github.com/markoblogo/AGENTS.md_generator.git
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
