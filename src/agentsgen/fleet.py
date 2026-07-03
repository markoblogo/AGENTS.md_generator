from __future__ import annotations

import datetime as dt
import json
from pathlib import Path
from typing import Any

from .actions import apply_config, load_tool_config
from .config import ToolConfig
from .detect import detect_repo
from .validators import validate_fleet_scan_report_payload


SKIP_DIRS = {
    ".git",
    ".mypy_cache",
    ".pytest_cache",
    ".tox",
    ".venv",
    "node_modules",
}


def is_git_repo(path: Path) -> bool:
    git_path = path / ".git"
    return git_path.is_dir() or git_path.is_file()


def iter_git_repos(roots: list[Path], max_depth: int) -> list[Path]:
    repos: list[Path] = []

    def walk(root: Path, depth: int) -> None:
        if depth < 0:
            return
        try:
            entries = list(root.iterdir())
        except Exception:
            return
        for entry in entries:
            if not entry.is_dir():
                continue
            if entry.name in SKIP_DIRS:
                continue
            if is_git_repo(entry):
                repos.append(entry)
                continue
            walk(entry, depth - 1)

    for root in roots:
        if is_git_repo(root):
            repos.append(root)
        walk(root, max_depth)

    return sorted({repo.resolve() for repo in repos})


def file_mode(repo: Path, name: str) -> str:
    path = repo / name
    if not path.exists():
        return "missing"
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return "unreadable"
    if "<!-- AGENTSGEN:START" in text and "<!-- AGENTSGEN:END" in text:
        return "markers"
    return "no_markers"


def _result_payload(results) -> list[dict[str, object]]:
    return [
        {
            "path": str(row.path),
            "action": row.action,
            "message": row.message,
            "changed": bool(row.changed),
        }
        for row in results
    ]


def _recommended_next(row: dict[str, Any]) -> str:
    if row["errors"]:
        return "inspect scan errors"
    if not row["has_config"]:
        return "agentsgen init . --defaults --autodetect"
    if row["needs_manual_markers"]:
        return "review generated siblings or add AGENTSGEN markers"
    if row["changed_count"]:
        return "agentsgen fix ."
    return "agentsgen check . --all --report"


def scan_repo(repo: Path) -> dict[str, Any]:
    row: dict[str, Any] = {
        "repo": str(repo.resolve()),
        "agents_mode": file_mode(repo, "AGENTS.md"),
        "runbook_mode": file_mode(repo, "RUNBOOK.md"),
        "has_config": (repo / ".agentsgen.json").is_file(),
        "detect": {},
        "plan": [],
        "changed_count": 0,
        "needs_manual_markers": False,
        "errors": [],
        "recommended_next": "",
    }

    try:
        if row["has_config"]:
            cfg = load_tool_config(repo)
        else:
            det = detect_repo(repo)
            row["detect"] = det.to_json()
            cfg = ToolConfig.from_detect(det)

        results = apply_config(
            repo, cfg, write_prompts=False, dry_run=True, print_diff=False
        )
        row["plan"] = _result_payload(results)
        row["changed_count"] = sum(1 for result in results if result.changed)
        row["needs_manual_markers"] = (
            row["agents_mode"] == "no_markers" or row["runbook_mode"] == "no_markers"
        )
    except Exception as exc:
        row["errors"].append(f"{type(exc).__name__}: {exc}")

    row["recommended_next"] = _recommended_next(row)
    return row


def build_fleet_scan_report(
    roots: list[Path],
    *,
    max_depth: int,
    timestamp: str | None = None,
) -> dict[str, Any]:
    resolved_roots = [root.expanduser().resolve() for root in roots]
    repos = [scan_repo(repo) for repo in iter_git_repos(resolved_roots, max_depth)]
    summary = {
        "repos_count": len(repos),
        "failed_count": sum(1 for row in repos if row["errors"]),
        "needs_init_count": sum(1 for row in repos if not row["has_config"]),
        "needs_manual_markers_count": sum(
            1 for row in repos if row["needs_manual_markers"]
        ),
        "changed_count": sum(int(row["changed_count"]) for row in repos),
    }
    payload = {
        "version": 1,
        "command": "fleet scan",
        "meta": {
            "timestamp": timestamp
            or dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
            "roots": [str(root) for root in resolved_roots],
            "max_depth": max_depth,
        },
        "summary": summary,
        "repos": repos,
    }
    validate_fleet_scan_report_payload(payload)
    return payload


def render_fleet_scan_markdown(report: dict[str, Any]) -> str:
    meta = report["meta"]
    summary = report["summary"]
    lines = [
        "# agentsgen fleet scan",
        "",
        f"Scanned at: `{meta['timestamp']}`",
        f"Roots: {', '.join('`' + root + '`' for root in meta['roots'])}",
        f"Max depth: `{meta['max_depth']}`",
        "",
        f"- Total repos: **{summary['repos_count']}**",
        f"- Failed scans: **{summary['failed_count']}**",
        f"- Need init: **{summary['needs_init_count']}**",
        f"- Need manual markers: **{summary['needs_manual_markers_count']}**",
        f"- Planned changed files: **{summary['changed_count']}**",
        "",
        "| repo | AGENTS.md | RUNBOOK.md | config | changed | next | errors |",
        "|---|---:|---:|---:|---:|---|---|",
    ]
    for row in report["repos"]:
        errors = "; ".join(row["errors"])
        lines.append(
            "| "
            + " | ".join(
                [
                    f"`{row['repo']}`",
                    row["agents_mode"],
                    row["runbook_mode"],
                    "yes" if row["has_config"] else "no",
                    str(row["changed_count"]),
                    row["recommended_next"],
                    errors,
                ]
            )
            + " |"
        )
    lines.extend(
        [
            "",
            "## Next step",
            "",
            "Pick a pilot repo and run:",
            "",
            "```sh",
            "agentsgen check . --all --report",
            "agentsgen fix . --all --dry-run --print-diff",
            "```",
        ]
    )
    return "\n".join(lines) + "\n"


def write_fleet_scan_outputs(
    report: dict[str, Any],
    *,
    markdown_path: Path | None,
    json_path: Path | None,
) -> list[Path]:
    written: list[Path] = []
    if markdown_path is not None:
        markdown_path.parent.mkdir(parents=True, exist_ok=True)
        markdown_path.write_text(render_fleet_scan_markdown(report), encoding="utf-8")
        written.append(markdown_path)
    if json_path is not None:
        json_path.parent.mkdir(parents=True, exist_ok=True)
        json_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        written.append(json_path)
    return written
