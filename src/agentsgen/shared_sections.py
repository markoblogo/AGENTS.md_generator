from __future__ import annotations

from typing import Any


def render_guardrails(cfg: dict[str, Any]) -> str:
    defaults = cfg.get("defaults", {}) or {}
    guardrails = (
        (defaults.get("guardrails", {}) or {}) if isinstance(defaults, dict) else {}
    )
    diff_budget = int(guardrails.get("diff_budget_lines") or 300)
    ask_before = guardrails.get(
        "ask_before",
        [
            "schema changes",
            "auth/payments/crypto",
            "deletions or large refactors",
            "new build tooling/CI changes",
            "new major dependencies",
        ],
    )
    ask_before = [str(item) for item in (ask_before or []) if str(item).strip()]
    lines = [
        "### Guardrails",
        "",
        "- Work only within the requested scope and preserve local conventions.",
        f"- Prefer focused changes; use {diff_budget} changed lines as a review signal, not a hard limit.",
        "- Never discard user files, handwritten content, migrations, or data.",
        "- Never hardcode tokens/keys. Never print secrets; document required environment-variable names.",
        "- Run side-effecting or destructive operations only with existing authorization.",
        "- Before changing these areas, confirm intent unless the current task already authorizes it:",
    ]
    lines.extend(f"  - {item}" for item in ask_before)
    lines.append(
        "- A change is complete when behavior, relevant tests, and affected docs agree."
    )
    return "\n".join(lines)


def render_workflow(cfg: dict[str, Any]) -> str:
    return "\n".join(
        [
            "### Workflow",
            "",
            "1. Read the nearest instructions; inspect the current worktree and reproduce the behavior before editing.",
            "2. Isolate work when changes overlap or run concurrently; otherwise keep the workflow lightweight and preserve existing user changes.",
            "3. Implement the smallest coherent change. Reuse a service layer for genuinely shared mechanics; avoid speculative abstractions.",
            "4. Verify the changed behavior with the narrowest useful evidence, then run broader checks appropriate to the change. For visual changes, compare the same important view/state before and after when feasible.",
            "5. Update docs and contracts when behavior changes; distinguish local checks from CI, deployment, and release status.",
            "6. Report what changed, what evidence passed, and any material limitation. Do not commit, push, or deploy unless requested.",
        ]
    )


def render_style(cfg: dict[str, Any]) -> str:
    project = cfg.get("project", {}) or {}
    stack = str(project.get("primary_stack") or "unknown")
    return "\n".join(
        [
            f"### Style ({stack})",
            "",
            "- Match existing naming, formatting, and module boundaries.",
            "- Prefer direct code and explicit errors over new abstractions.",
            "- Validate external input at system boundaries.",
            "- Keep logs free of secrets and personal data.",
            "- Add types or comments where they clarify a public or non-obvious contract.",
            "- Reuse current dependencies unless a new one materially reduces complexity.",
        ]
    )


def render_verification(cfg: dict[str, Any]) -> str:
    commands = cfg.get("commands", {}) or {}
    fast = str(commands.get("fast") or "").strip()
    full = str(commands.get("full") or "").strip()
    lines = ["### Verification", ""]
    if fast:
        lines.append(f"- Fast: `{fast}`")
    if full:
        lines.append(f"- Full: `{full}`")
    else:
        lines.append(
            "- Run the repository's full test suite or the closest documented equivalent."
        )
    lines.append("- If a check cannot run, state why and name the remaining command.")
    return "\n".join(lines)


def render_repo_context(cfg: dict[str, Any]) -> str:
    project = cfg.get("project", {}) or {}
    paths = cfg.get("paths", {}) or {}
    project_name = str(project.get("name") or "this repo")
    stack = str(project.get("primary_stack") or "unknown")
    repo_root = str(project.get("repo_root") or ".")
    docs = [str(item) for item in (paths.get("docs", ["README.md"]) or ["README.md"])]
    ci = str(paths.get("ci") or ".github/workflows/")
    entrypoints = [str(item) for item in (project.get("entrypoints", []) or [])]
    services = project.get("services", []) or []

    lines = [
        "### Repo context",
        "",
        f"- Project: {project_name}",
        f"- Stack: {stack}",
        f"- Root: `{repo_root}`",
        "- Start with:",
    ]
    lines.extend(f"  - `{path}`" for path in docs)
    lines.append(f"- CI: `{ci}`")
    if entrypoints:
        lines.append("- Entrypoints:")
        lines.extend(f"  - `{entrypoint}`" for entrypoint in entrypoints)
    if services:
        lines.append("- Services:")
        for service in services:
            if isinstance(service, dict):
                name = str(service.get("name") or "service")
                path = str(service.get("path") or "").strip()
                notes = str(service.get("notes") or "").strip()
                suffix = f": `{path}`" if path else ""
                suffix += f" — {notes}" if notes else ""
                lines.append(f"  - {name}{suffix}")
            else:
                lines.append(f"  - {service}")
    return "\n".join(lines)


def render_all_shared(cfg: dict[str, Any]) -> dict[str, str]:
    return {
        "repo_context": render_repo_context(cfg),
        "guardrails": render_guardrails(cfg),
        "workflow": render_workflow(cfg),
        "style": render_style(cfg),
        "verification": render_verification(cfg),
    }
