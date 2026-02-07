# AGENTS.md

This file is for coding agents (Codex/Claude/Cursor/etc.). Keep it strict and actionable.

## Overview

<!-- AGENTSGEN:START section=overview -->
- **Project:** AGENTS.md Generator
- **Stack:** python (vanilla)
- Keep changes small and verifiable.
<!-- AGENTSGEN:END section=overview -->

<!-- AGENTSGEN:START section=repo_context -->
### Repo context (read this first)

**Project:** AGENTS.md Generator
**Stack:** python
**Repo root:** `.`

#### Quick orientation
- Start here:
  - `README.md`
- CI workflows live in: `.github/workflows/`

- Planning/spec drafts (if used):
  - Plans: `plans/`
  - Drafts/specs: `drafts/`
- Useful scripts (if any): `scripts/`

#### Commands (copy/paste)
**Lint**
```bash
make lint
```
**Format**
```bash
make format
```
**Tests**
```bash
make test
```

#### Local environment notes

- Prefer the repo's existing toolchain (don't upgrade it).
- If you need new env vars: document names, don't invent secrets.
- If a command fails due to missing deps, explain the minimal install step.

#### Where to put new things

- Small scripts/utilities — `scripts/`
- Specs/exec notes — `drafts/`
- Plans (if requested) — `plans/`
<!-- AGENTSGEN:END section=repo_context -->

<!-- AGENTSGEN:START section=guardrails -->
### Guardrails (how to not break AGENTS.md Generator)

**Your job:** be useful, be safe, be boring. Small diffs. Deterministic output. No surprises.

#### 0) Scope & intent
- Implement exactly what's requested. If requirements are ambiguous: ask one precise question (or make the smallest reasonable assumption and state it).
- Prefer changing existing code over adding new systems.
- Avoid framework upgrades unless explicitly asked.

#### 1) Safe edits only
- Keep diffs small (target: <300 lines unless unavoidable).
- Never rewrite whole files when a patch will do.
- Preserve formatting, naming patterns, and local conventions.

#### 2) No destructive operations
- Do not delete data, migrations, buckets, or user files.
- Avoid broad refactors touching many modules at once.
- Never remove features because unused without explicit instruction.

#### 3) Secrets & credentials
- Never hardcode tokens/keys.
- Never print secrets into logs.
- If a secret is needed: use env vars + document the name.

#### 4) Side effects / dangerous actions
- Don't run commands that can modify the system/network unless asked.
- Don't use dangerous flags unless explicitly approved.
- If a task involves running arbitrary tools/scripts: isolate and explain.

#### 5) Ask-before list (must confirm)
Before doing any of these, ask:
- schema changes
- auth/payments/crypto
- deletions or large refactors
- new build tooling/CI changes
- new major dependencies

#### 6) Definition of Done (DoD)
A change is done only if:
- the behavior is correct,
- tests/checks are run (or you explain why they can't be run),
- the diff is minimal and readable,
- docs/comments are updated if behavior changed.

#### 7) Output protocol
When responding, include:
- what changed (1-3 bullets),
- how to verify (commands / steps),
- risks/assumptions (if any).
<!-- AGENTSGEN:END section=guardrails -->

<!-- AGENTSGEN:START section=workflow -->
### Workflow (how we ship changes in AGENTS.md Generator)

#### 1) Start with reality
- Read the nearest README / docs / existing patterns.
- If there's a failing case: reproduce it (or create a minimal reproduction).

#### 2) Work in thin slices
- Prefer one small working increment over a big redesign.
- Change one thing, verify, then move to the next.

#### 3) Make changes reviewable
- Keep diffs minimal.
- Avoid unrelated formatting churn.
- Prefer refactoring after the fix works, not before.

#### 4) Verification loop
- Run fast checks after each meaningful change.
- Run full checks before finalizing.
- If you cannot run checks, explain why and what to run.

#### 5) Commit / PR discipline (even if you don't actually commit)
Think like you're preparing a PR:
- Clear intent
- Small diff
- Tests included
- No breaking changes without warning

**Commit message style (suggested):**
- Allowed types: feat, fix, test, docs, refactor
- Example: `fix: handle empty input in parser`

#### 6) Communication rules
- If the task is blocked by missing info: ask one concrete question.
- If you make an assumption: state it explicitly and keep it reversible.
<!-- AGENTSGEN:END section=workflow -->

<!-- AGENTSGEN:START section=verification -->
### Verification (don't trust yourself, verify)

#### Fast checks (run often)
- Define a fast check for this repo (lint / unit tests / smoke test).
- If none exists, add a minimal smoke check.

#### Full checks (run before finalizing)
- Run the repo's full test suite (or the closest equivalent).

#### If checks cannot be run
State:
- why (missing deps / CI-only / platform),
- what to run,
- expected outcome.
<!-- AGENTSGEN:END section=verification -->

<!-- AGENTSGEN:START section=style -->
### Style & conventions (python)

#### 1) Follow the repo
- Match existing naming, structure, and patterns.
- Don't introduce new abstractions unless they reduce complexity.

#### 2) Readability wins
- Prefer clear code over clever code.
- Keep functions small and single-purpose.
- Choose explicit names over short names.

#### 3) Errors & edge cases
- Validate inputs at boundaries.
- Fail loudly for programmer errors, gracefully for user errors.
- Add helpful error messages (actionable, not vague).

#### 4) Logging (if applicable)
- Log meaningful events, not noise.
- Never log secrets or personal data.

#### 5) Types / docs (if applicable)
- Add type hints where it improves clarity.
- Add docstrings for public functions and tricky logic.
- Write comments only when the why is non-obvious.

#### 6) Dependencies
- Prefer standard library / existing deps.
- Avoid adding heavy dependencies for small tasks.
<!-- AGENTSGEN:END section=style -->

## Rules Of Engagement

<!-- AGENTSGEN:START section=rules -->
**DO**
- Prefer small diffs.
- Add or update tests when behavior changes.
- Run repo checks before finishing.

**DON'T**
- Do not rewrite unrelated code.
- Do not refactor without confirming intent.
- Do not commit secrets or local env files.

**If uncertain**
- Ask a short clarifying question before making big changes.

**Warnings**
- (none)
<!-- AGENTSGEN:END section=rules -->

## Commands

<!-- AGENTSGEN:START section=commands -->
- **Test:** `make test`
- **Lint:** `make lint`
- **Format:** `make format`

- **Run a single test:** (not specified)
- **Where configs live:** `.github/workflows/`, `Makefile`, `pyproject.toml`
<!-- AGENTSGEN:END section=commands -->

<!-- AGENTSGEN:START section=python -->
## Python project notes

### Local setup
- Create venv: `python -m venv .venv && source .venv/bin/activate`
- Install: `pip install -e .`

### Common commands
- Tests: `pytest`
- Lint: `ruff check .`
- Format: `ruff format .`

### Packaging expectations
- Keep dependencies minimal
- Prefer standard library where reasonable
- Ensure CLI help output is clear and stable
<!-- AGENTSGEN:END section=python -->

## Repo Structure

<!-- AGENTSGEN:START section=structure -->
- **Source:** `src`
- **Config:** `.github/workflows/`, `Makefile`, `pyproject.toml`
<!-- AGENTSGEN:END section=structure -->

## Output Protocol

<!-- AGENTSGEN:START section=output_protocol -->
When you finish work, include:
- Summary (1-3 bullets)
- Files changed (list paths)
- Verification (exact commands to run)
<!-- AGENTSGEN:END section=output_protocol -->
