from __future__ import annotations

from pathlib import Path

from .constants import SECTION_NAMES
from .model import ProjectInfo, RenderPlan
from .render import load_template, render_template


def build_render_plan(info: ProjectInfo) -> RenderPlan:
    warnings_md = "\n".join([f"- {w}" for w in (info.warnings or [])]) or "- (none)"

    overview = "\n".join(
        [
            f"- **Project:** {info.project_name}",
            f"- **Stack:** {info.stack}" + (
                f" ({info.package_manager})" if info.package_manager else (
                    f" ({info.python_tooling})" if info.python_tooling else ""
                )
            ),
            "- Keep changes small and verifiable.",
        ]
    )

    rules = "\n".join(
        [
            "**DO**",
            "- Prefer small diffs.",
            "- Add or update tests when behavior changes.",
            "- Run repo checks before finishing.",
            "",
            "**DON'T**",
            "- Do not rewrite unrelated code.",
            "- Do not refactor without confirming intent.",
            "- Do not commit secrets or local env files.",
            "",
            "**If uncertain**",
            "- Ask a short clarifying question before making big changes.",
            "",
            "**Warnings**",
            warnings_md,
        ]
    )

    def cmd_line(label: str, key: str) -> str | None:
        v = (info.commands.get(key, "") or "").strip()
        if not v:
            return None
        return f"- **{label}:** `{v}`"

    commands_lines = [
        cmd_line("Install", "install"),
        cmd_line("Dev", "dev"),
        cmd_line("Test", "test"),
        cmd_line("Lint", "lint"),
        cmd_line("Format", "format"),
        cmd_line("Build", "build"),
    ]
    commands = "\n".join([x for x in commands_lines if x]) or "- (no commands configured)"

    structure_parts: list[str] = []
    if info.source_dirs:
        structure_parts.append("- **Source:** " + ", ".join([f"`{p}`" for p in info.source_dirs]))
    if info.config_locations:
        structure_parts.append(
            "- **Config:** " + ", ".join([f"`{p}`" for p in info.config_locations])
        )
    if info.branching_model:
        structure_parts.append(f"- **Branching:** {info.branching_model}")
    structure = "\n".join(structure_parts) or "- (not specified)"

    output_protocol = "\n".join(
        [
            "When you finish work, include:",
            "- Summary (1-3 bullets)",
            "- Files changed (list paths)",
            "- Verification (exact commands to run)",
        ]
    )

    python_notes = "\n".join(
        [
            "## Python project notes",
            "",
            "### Local setup",
            "- Create venv: `python -m venv .venv && source .venv/bin/activate`",
            "- Install: `pip install -e .`",
            "",
            "### Common commands",
            "- Tests: `pytest`",
            "- Lint: `ruff check .`",
            "- Format: `ruff format .`",
            "",
            "### Packaging expectations",
            "- Keep dependencies minimal",
            "- Prefer standard library where reasonable",
            "- Ensure CLI help output is clear and stable",
        ]
    )

    node_notes = "\n".join(
        [
            "## Node project notes",
            "",
            "### Common commands",
            "- Install: `npm ci` (or `pnpm i --frozen-lockfile`)",
            "- Tests: `npm test`",
            "- Lint: `npm run lint`",
            "- Build: `npm run build`",
            "",
            "### Guardrails",
            "- Don't update lockfiles unless necessary",
            "- Prefer minimal dependency changes",
        ]
    )

    static_notes = "\n".join(
        [
            "## Static site / docs notes",
            "",
            "### Safe edits",
            "- Avoid large HTML/CSS refactors unless requested",
            "- Prefer small layout changes with predictable impact",
            "- If mobile layout changes: verify at least one narrow breakpoint",
            "",
            "### Quick checks",
            "- Run formatter (if present)",
            "- Validate links (spot-check)",
        ]
    )

    return RenderPlan(
        sections={
            "overview": overview,
            "rules": rules,
            "commands": commands,
            "structure": structure,
            "output_protocol": output_protocol,
            "python": python_notes,
            "node": node_notes,
            "static": static_notes,
        }
    )


def render_agents_md(
    info: ProjectInfo,
    template_path: Path,
    *,
    single_test_hint: str,
    configs_hint: str,
    shared_blocks: dict[str, str],
) -> str:
    plan = build_render_plan(info)

    ctx: dict[str, str] = {
        "project_name": info.project_name,
        "stack": info.stack,
        "package_manager": info.package_manager,
        "python_tooling": info.python_tooling,
        "overview_block": plan.sections["overview"],
        "rules_block": plan.sections["rules"],
        "commands_block": plan.sections["commands"],
        "structure_block": plan.sections["structure"],
        "output_protocol_block": plan.sections["output_protocol"],
        "single_test_hint": single_test_hint,
        "configs_hint": configs_hint,
        "repo_context_block": shared_blocks.get("repo_context", "").strip(),
        "guardrails_block": shared_blocks.get("guardrails", "").strip(),
        "workflow_block": shared_blocks.get("workflow", "").strip(),
        "verification_block": shared_blocks.get("verification", "").strip(),
        "style_block": shared_blocks.get("style", "").strip(),
        "python_block": plan.sections["python"],
        "node_block": plan.sections["node"],
        "static_block": plan.sections["static"],
    }

    return render_template(load_template(template_path), ctx)


def render_runbook_md(info: ProjectInfo, template_path: Path) -> str:
    c = info.commands
    quick_cmds = [x.strip() for x in [c.get("install", ""), c.get("dev", ""), c.get("test", ""), c.get("lint", "")] if x and x.strip()]

    if quick_cmds:
        quickstart = "\n".join([f"```sh\n{cmd}\n```" for cmd in quick_cmds[:6]])
    else:
        quickstart = "- (no quickstart commands configured)"

    common_tasks = "\n".join(
        [
            "- Run tests: " + (f"`{c.get('test','').strip()}`" if c.get("test", "").strip() else "(not set)"),
            "- Lint: " + (f"`{c.get('lint','').strip()}`" if c.get("lint", "").strip() else "(not set)"),
            "- Build: " + (f"`{c.get('build','').strip()}`" if c.get("build", "").strip() else "(not set)"),
        ]
    )

    troubleshooting = "\n".join(
        [
            "- If dependencies fail: verify the expected Node/Python version for this repo.",
            "- If tests are flaky: re-run once, then isolate and fix the root cause.",
            "- If environment is unclear: ask for the expected OS/tooling versions.",
        ]
    )

    ctx: dict[str, str] = {
        "project_name": info.project_name,
        "stack": info.stack,
        "quickstart_block": quickstart,
        "common_tasks_block": common_tasks,
        "troubleshooting_block": troubleshooting,
    }

    return render_template(load_template(template_path), ctx)


def template_paths(base: Path, stack: str) -> tuple[Path, Path]:
    agents_tpl = base / stack / "AGENTS.md.tpl"
    runbook_tpl = base / stack / "RUNBOOK.md.tpl"
    return agents_tpl, runbook_tpl


def required_sections(stack: str) -> list[str]:
    stack = (stack or "").strip().lower()
    base = [
        "overview",
        "repo_context",
        "guardrails",
        "workflow",
        "verification",
        "style",
        "rules",
        "commands",
        "structure",
        "output_protocol",
    ]
    if stack in ("python", "node", "static"):
        return base + [stack]
    return base


def required_runbook_sections() -> list[str]:
    return ["quickstart", "common_tasks", "troubleshooting"]
