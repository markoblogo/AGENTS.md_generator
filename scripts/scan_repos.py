from __future__ import annotations

import argparse
import datetime as dt
import json
import os
from dataclasses import asdict
from pathlib import Path
from typing import Any

from agentsgen.actions import apply_config, load_tool_config
from agentsgen.config import ToolConfig
from agentsgen.detect import detect_repo


def is_git_repo(p: Path) -> bool:
    # Supports normal .git directory and worktrees/submodules where .git can be a file.
    g = p / ".git"
    return g.is_dir() or g.is_file()


def iter_git_repos(roots: list[Path], max_depth: int) -> list[Path]:
    repos: list[Path] = []

    def walk(root: Path, depth: int) -> None:
        if depth < 0:
            return
        try:
            entries = list(root.iterdir())
        except Exception:
            return
        for e in entries:
            if not e.is_dir():
                continue
            name = e.name
            if name in {".venv", "node_modules", ".tox", ".mypy_cache", ".pytest_cache", ".git"}:
                continue
            if is_git_repo(e):
                repos.append(e)
                continue
            walk(e, depth - 1)

    for r in roots:
        walk(r, max_depth)

    # De-dup + stable sort.
    uniq = sorted({p.resolve() for p in repos})
    return uniq


def file_mode(repo: Path, name: str) -> str:
    p = repo / name
    if not p.exists():
        return "missing"
    txt = None
    try:
        txt = p.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return "unreadable"
    if "<!-- AGENTSGEN:START" in txt and "<!-- AGENTSGEN:END" in txt:
        return "markers"
    return "no_markers"


def run_repo(repo: Path) -> dict[str, Any]:
    row: dict[str, Any] = {
        "repo": str(repo),
        "agents_mode": file_mode(repo, "AGENTS.md"),
        "runbook_mode": file_mode(repo, "RUNBOOK.md"),
        "has_config": (repo / ".agentsgen.json").is_file(),
        "detect": {},
        "plan": [],
        "errors": [],
    }

    try:
        if row["has_config"]:
            cfg = load_tool_config(repo)
        else:
            det = detect_repo(repo)
            row["detect"] = det.to_json()
            cfg = ToolConfig.from_detect(det)

        # Simulate what init/update would do (no diffs, no writes).
        res = apply_config(repo, cfg, write_prompts=False, dry_run=True, print_diff=False)
        row["plan"] = [
            {
                "path": str(r.path),
                "action": r.action,
                "message": r.message,
                "changed": bool(r.changed),
            }
            for r in res
        ]

        # Flag repos that require manual one-time marker insertion.
        row["needs_manual_markers"] = (
            row["agents_mode"] == "no_markers" or row["runbook_mode"] == "no_markers"
        )

    except Exception as e:
        row["errors"].append(f"{type(e).__name__}: {e}")

    return row


def render_md(report: dict[str, Any]) -> str:
    lines: list[str] = []
    lines.append(f"# agentsgen migration scan")
    lines.append("")
    lines.append(f"Scanned at: `{report['meta']['timestamp']}`")
    lines.append(f"Roots: {', '.join('`'+r+'`' for r in report['meta']['roots'])}")
    lines.append("")

    rows = report["repos"]
    total = len(rows)
    failed = sum(1 for r in rows if r["errors"])
    needs_manual = sum(1 for r in rows if r.get("needs_manual_markers"))

    lines.append(f"- Total repos: **{total}**")
    lines.append(f"- Failed scans: **{failed}**")
    lines.append(f"- Need manual markers (will produce `*.generated.md`): **{needs_manual}**")
    lines.append("")

    lines.append("| repo | stack | AGENTS.md | RUNBOOK.md | has config | plan summary | errors |")
    lines.append("|---|---|---:|---:|---:|---|---|")

    for r in rows:
        detect = r.get("detect") or {}
        stack = ""
        if detect:
            stack = str((detect.get("project") or {}).get("primary_stack") or "")
        else:
            stack = "(from config)"

        plan = r.get("plan") or []
        summary = []
        for a in plan:
            summary.append(a["action"])
        summary_txt = ",".join(summary) if summary else ""

        err = "; ".join(r.get("errors") or [])

        lines.append(
            "| "
            + " | ".join(
                [
                    f"`{r['repo']}`",
                    stack,
                    r["agents_mode"],
                    r["runbook_mode"],
                    "yes" if r["has_config"] else "no",
                    summary_txt,
                    err,
                ]
            )
            + " |"
        )

    lines.append("")
    lines.append("## Next step")
    lines.append("")
    lines.append("Pick 3 pilot repos (python/node/static) and run:")
    lines.append("")
    lines.append("```sh")
    lines.append("git checkout -b chore/agentsgen")
    lines.append("agentsgen init --autodetect --defaults --dry-run --print-diff")
    lines.append("agentsgen init --autodetect --defaults")
    lines.append("agentsgen update")
    lines.append("agentsgen check")
    lines.append("```")

    return "\n".join(lines) + "\n"


def main() -> None:
    ap = argparse.ArgumentParser(description="Scan many git repos and report agentsgen migration plan (dry-run only)")
    ap.add_argument("--root", action="append", required=True, help="Root directory to scan (repeatable)")
    ap.add_argument("--max-depth", type=int, default=2, help="Max directory depth under roots")
    ap.add_argument("--out", default="", help="Write markdown report to this path (default: /tmp/...) ")
    ap.add_argument("--json-out", default="", help="Write json report to this path (default: /tmp/...) ")

    args = ap.parse_args()

    roots = [Path(os.path.expanduser(r)).resolve() for r in args.root]
    ts = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    md_out = Path(args.out) if args.out else Path(f"/tmp/agentsgen-scan-{ts}.md")
    js_out = Path(args.json_out) if args.json_out else Path(f"/tmp/agentsgen-scan-{ts}.json")

    repos = iter_git_repos(roots, max_depth=args.max_depth)
    data = {
        "meta": {
            "timestamp": dt.datetime.now().isoformat(timespec="seconds"),
            "roots": [str(r) for r in roots],
            "max_depth": args.max_depth,
        },
        "repos": [run_repo(r) for r in repos],
    }

    js_out.write_text(json.dumps(data, indent=2), encoding="utf-8")
    md_out.write_text(render_md(data), encoding="utf-8")

    print(str(md_out))
    print(str(js_out))


if __name__ == "__main__":
    main()
