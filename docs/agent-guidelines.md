# Agent Guidelines (Minimal, Reviewable Changes)

These rules exist for one goal: make agent output easy to review and safe to apply.

## Core principle
**Do the smallest correct change that solves the requested task.**
If a change is not requested and not strictly necessary, don’t do it.

## Change scope
### Prefer
- Implement exactly what was asked.
- Keep solutions simple and direct.
- Touch as few files as possible.
- Make edits locally consistent (only around the changed code).

### Avoid
- “Improving” surrounding code while fixing a bug.
- Adding extra options, configurability, feature flags, or compatibility shims.
- Refactors, formatting sweeps, or style changes outside the touched area.

## Documentation / comments / types
- Don’t add docstrings/comments/types to code you didn’t change.
- Add comments only when the logic is not self-evident *in the changed code*.

## Error handling
- Trust internal invariants and framework guarantees.
- Validate only at system boundaries (user input, external APIs, network).
- Don’t add defensive code for scenarios that can’t happen.

## Abstractions
- Don’t create helpers/utilities for one-off operations.
- Don’t design for hypothetical future requirements.
- Three similar lines are often better than a premature abstraction.

## Deletions
- Don’t leave “removed” comments or backwards-compat hacks.
- If you’re confident something is unused, delete it completely.

## Output expectations
- Provide a short summary of what changed and why.
- If you made a tradeoff, state it explicitly.

## **Как встроить в AGENTS.md Generator (аккуратно, без “шума”)**

### **Где ссылаться**
1. В AGENTS.md — короткая ссылка в секции guardrails (или рядом):
- “Follow our agent guidelines: docs/agent-guidelines.md”
2. В pack (LLMS.md или llms.txt) — добавить “Recommended sources” и включить:
- docs/agent-guidelines.md - ну и коммит-пуш по завершению
