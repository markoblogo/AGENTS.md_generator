# Experimental LLM Enhancement

`agentsgen` keeps LLM enhancement strictly opt-in.

## Install

```sh
pip install -e ".[llm]"
```

## CLI usage

```sh
agentsgen init . --llm-enhance --llm-provider openai
agentsgen update . --llm-enhance --llm-provider anthropic
```

## Provider behavior

- `openai` requires `OPENAI_API_KEY`
- `anthropic` requires `ANTHROPIC_API_KEY`
- if credentials are missing, enhancement falls back to local-only generation
- if a provider raises `TimeoutError`, enhancement falls back to local-only generation
- if a provider raises any other exception, enhancement falls back to local-only generation

## Current contract surface

The normalized LLM request options include:

- `enabled`
- `provider`
- `model`
- `timeout_seconds`
- `narrative_sections`

The normalized enhancement result includes:

- `provider`
- `applied`
- `sections`
- `message`

## Notes on `model` and `timeout_seconds`

These fields are already part of the versioned contract surface for CLI/MCP callers.

- `model` is accepted now so MCP and future provider integrations do not need another breaking contract change.
- `timeout_seconds` is normalized now and reserved for provider implementations that perform real network calls.
- the current built-in stub providers do not yet vary output by `model` and do not enforce a transport timeout internally.

## Safety boundary

- only narrative sections are eligible for enhancement
- detected commands are not rewritten by the enhancer
- marker layout and managed-file safety rules remain unchanged
