from __future__ import annotations

from typing import Any


def _bullets(items: list[str]) -> str:
    return "\n".join([f"- {x}" for x in items])


def render_guardrails(cfg: dict[str, Any]) -> str:
    project = cfg.get("project", {}) or {}
    defaults = cfg.get("defaults", {}) or {}

    project_name = str(project.get("name") or "this repo")

    g = (defaults.get("guardrails", {}) or {}) if isinstance(defaults, dict) else {}
    diff_budget = int(g.get("diff_budget_lines") or 300)
    ask_before = g.get(
        "ask_before",
        [
            "schema changes",
            "auth/payments/crypto",
            "deletions or large refactors",
            "new build tooling/CI changes",
            "new major dependencies",
        ],
    )
    ask_before = [str(x) for x in (ask_before or []) if str(x).strip()]

    return "\n".join(
        [
            f"### Guardrails (how to not break {project_name})",
            "",
            "**Your job:** be useful, be safe, be boring. Small diffs. Deterministic output. No surprises.",
            "",
            "#### 0) Scope & intent",
            "- Implement exactly what's requested. If requirements are ambiguous: ask one precise question (or make the smallest reasonable assumption and state it).",
            "- Prefer changing existing code over adding new systems.",
            "- Avoid framework upgrades unless explicitly asked.",
            "",
            "#### 1) Safe edits only",
            f"- Keep diffs small (target: <{diff_budget} lines unless unavoidable).",
            "- Never rewrite whole files when a patch will do.",
            "- Preserve formatting, naming patterns, and local conventions.",
            "",
            "#### 2) No destructive operations",
            "- Do not delete data, migrations, buckets, or user files.",
            "- Avoid broad refactors touching many modules at once.",
            "- Never remove features because unused without explicit instruction.",
            "",
            "#### 3) Secrets & credentials",
            "- Never hardcode tokens/keys.",
            "- Never print secrets into logs.",
            "- If a secret is needed: use env vars + document the name.",
            "",
            "#### 4) Side effects / dangerous actions",
            "- Don't run commands that can modify the system/network unless asked.",
            "- Don't use dangerous flags unless explicitly approved.",
            "- If a task involves running arbitrary tools/scripts: isolate and explain.",
            "",
            "#### 5) Ask-before list (must confirm)",
            "Before doing any of these, ask:",
            _bullets(ask_before) if ask_before else "- (none)",
            "",
            "#### 6) Definition of Done (DoD)",
            "A change is done only if:",
            "- the behavior is correct,",
            "- tests/checks are run (or you explain why they can't be run),",
            "- the diff is minimal and readable,",
            "- docs/comments are updated if behavior changed.",
            "",
            "#### 7) Output protocol",
            "When responding, include:",
            "- what changed (1-3 bullets),",
            "- how to verify (commands / steps),",
            "- risks/assumptions (if any).",
        ]
    )


def render_workflow(cfg: dict[str, Any]) -> str:
    project = cfg.get("project", {}) or {}
    defaults = cfg.get("defaults", {}) or {}

    project_name = str(project.get("name") or "this repo")

    wf = (defaults.get("workflow", {}) or {}) if isinstance(defaults, dict) else {}
    thin_slices = bool(wf.get("thin_slices", True))
    commit_types = wf.get("recommended_commit_types", ["feat", "fix", "test", "docs", "refactor"])
    commit_types = [str(x) for x in (commit_types or []) if str(x).strip()]

    thin = (
        "\n".join(
            [
                "- Prefer one small working increment over a big redesign.",
                "- Change one thing, verify, then move to the next.",
            ]
        )
        if thin_slices
        else "- Keep the approach incremental and testable."
    )

    return "\n".join(
        [
            f"### Workflow (how we ship changes in {project_name})",
            "",
            "#### 1) Start with reality",
            "- Read the nearest README / docs / existing patterns.",
            "- If there's a failing case: reproduce it (or create a minimal reproduction).",
            "",
            "#### 2) Work in thin slices",
            thin,
            "",
            "#### 3) Make changes reviewable",
            "- Keep diffs minimal.",
            "- Avoid unrelated formatting churn.",
            "- Prefer refactoring after the fix works, not before.",
            "",
            "#### 4) Verification loop",
            "- Run fast checks after each meaningful change.",
            "- Run full checks before finalizing.",
            "- If you cannot run checks, explain why and what to run.",
            "",
            "#### 5) Commit / PR discipline (even if you don't actually commit)",
            "Think like you're preparing a PR:",
            "- Clear intent",
            "- Small diff",
            "- Tests included",
            "- No breaking changes without warning",
            "",
            "**Commit message style (suggested):**",
            f"- Allowed types: {', '.join(commit_types) if commit_types else '(not set)'}",
            "- Example: `fix: handle empty input in parser`",
            "",
            "#### 6) Communication rules",
            "- If the task is blocked by missing info: ask one concrete question.",
            "- If you make an assumption: state it explicitly and keep it reversible.",
        ]
    )


def render_style(cfg: dict[str, Any]) -> str:
    project = cfg.get("project", {}) or {}
    stack = str(project.get("primary_stack") or "unknown")

    return "\n".join(
        [
            f"### Style & conventions ({stack})",
            "",
            "#### 1) Follow the repo",
            "- Match existing naming, structure, and patterns.",
            "- Don't introduce new abstractions unless they reduce complexity.",
            "",
            "#### 2) Readability wins",
            "- Prefer clear code over clever code.",
            "- Keep functions small and single-purpose.",
            "- Choose explicit names over short names.",
            "",
            "#### 3) Errors & edge cases",
            "- Validate inputs at boundaries.",
            "- Fail loudly for programmer errors, gracefully for user errors.",
            "- Add helpful error messages (actionable, not vague).",
            "",
            "#### 4) Logging (if applicable)",
            "- Log meaningful events, not noise.",
            "- Never log secrets or personal data.",
            "",
            "#### 5) Types / docs (if applicable)",
            "- Add type hints where it improves clarity.",
            "- Add docstrings for public functions and tricky logic.",
            "- Write comments only when the why is non-obvious.",
            "",
            "#### 6) Dependencies",
            "- Prefer standard library / existing deps.",
            "- Avoid adding heavy dependencies for small tasks.",
        ]
    )


def render_verification(cfg: dict[str, Any]) -> str:
    commands = cfg.get("commands", {}) or {}
    fast = str(commands.get("fast") or "").strip()
    full = str(commands.get("full") or "").strip()

    fast_block = (
        "\n".join(["```bash", fast, "```"])
        if fast
        else "\n".join(
            [
                "- Define a fast check for this repo (lint / unit tests / smoke test).",
                "- If none exists, add a minimal smoke check.",
            ]
        )
    )
    full_block = (
        "\n".join(["```bash", full, "```"])
        if full
        else "- Run the repo's full test suite (or the closest equivalent)."
    )

    return "\n".join(
        [
            "### Verification (don't trust yourself, verify)",
            "",
            "#### Fast checks (run often)",
            fast_block,
            "",
            "#### Full checks (run before finalizing)",
            full_block,
            "",
            "#### If checks cannot be run",
            "State:",
            "- why (missing deps / CI-only / platform),",
            "- what to run,",
            "- expected outcome.",
        ]
    )


def render_repo_context(cfg: dict[str, Any]) -> str:
    project = cfg.get("project", {}) or {}
    paths = cfg.get("paths", {}) or {}
    commands = cfg.get("commands", {}) or {}

    project_name = str(project.get("name") or "this repo")
    stack = str(project.get("primary_stack") or "unknown")
    repo_root = str(project.get("repo_root") or ".")

    docs = paths.get("docs", ["README.md"]) or ["README.md"]
    docs = [str(x) for x in docs if str(x).strip()]
    ci = str(paths.get("ci") or ".github/workflows/")
    plans_dir = str(paths.get("plans") or "plans/")
    drafts_dir = str(paths.get("drafts") or "drafts/")
    scripts_dir = str(paths.get("scripts") or "scripts/")

    entrypoints = project.get("entrypoints", []) or []
    entrypoints = [str(x) for x in entrypoints if str(x).strip()]

    def fenced(label: str, cmd: str) -> str:
        if not cmd.strip():
            return ""
        return "\n".join([f"**{label}**", "```bash", cmd.strip(), "```", ""])

    parts: list[str] = []
    parts.append("### Repo context (read this first)")
    parts.append("")
    parts.append(f"**Project:** {project_name}  ")
    parts.append(f"**Stack:** {stack}  ")
    parts.append(f"**Repo root:** `{repo_root}`")
    parts.append("")
    parts.append("#### Quick orientation")
    parts.append("- Start here:")
    parts.extend([f"  - `{d}`" for d in docs] or ["  - `README.md`"])
    parts.append(f"- CI workflows live in: `{ci}`" if ci else "- CI: (not detected)")
    parts.append("")
    parts.append("- Planning/spec drafts (if used):")
    parts.append(f"  - Plans: `{plans_dir}`")
    parts.append(f"  - Drafts/specs: `{drafts_dir}`")
    parts.append(f"- Useful scripts (if any): `{scripts_dir}`")

    if entrypoints:
        parts.append("")
        parts.append("#### Entrypoints (what actually runs)")
        parts.extend([f"- `{ep}`" for ep in entrypoints])

    parts.append("")
    parts.append("#### Commands (copy/paste)")
    for label, key in [
        ("Dev / run", "dev"),
        ("Build", "build"),
        ("Lint", "lint"),
        ("Format", "format"),
        ("Typecheck", "typecheck"),
        ("Tests", "test"),
    ]:
        block = fenced(label, str(commands.get(key) or ""))
        if block:
            parts.append(block.rstrip())

    if commands.get("fast") or commands.get("full"):
        parts.append("")
        parts.append("**Verification loop**")
        if str(commands.get("fast") or "").strip():
            parts.append("Fast:")
            parts.append("```bash")
            parts.append(str(commands.get("fast") or "").strip())
            parts.append("```")
        if str(commands.get("full") or "").strip():
            parts.append("Full:")
            parts.append("```bash")
            parts.append(str(commands.get("full") or "").strip())
            parts.append("```")

    parts.append("")
    parts.append("#### Local environment notes")
    parts.append("")
    parts.append("- Prefer the repo's existing toolchain (don't upgrade it).")
    parts.append("- If you need new env vars: document names, don't invent secrets.")
    parts.append("- If a command fails due to missing deps, explain the minimal install step.")
    parts.append("")
    parts.append("#### Where to put new things")
    parts.append("")
    parts.append(f"- Small scripts/utilities — `{scripts_dir}`")
    parts.append(f"- Specs/exec notes — `{drafts_dir}`")
    parts.append(f"- Plans (if requested) — `{plans_dir}`")

    return "\n".join(parts).strip()


def render_all_shared(cfg: dict[str, Any]) -> dict[str, str]:
    return {
        "repo_context": render_repo_context(cfg),
        "guardrails": render_guardrails(cfg),
        "workflow": render_workflow(cfg),
        "style": render_style(cfg),
        "verification": render_verification(cfg),
    }

