from __future__ import annotations

import json
from pathlib import Path

from .io_utils import read_text
from .patch_engine import generated_sibling_path, write_or_diff
from .result_types import FileResult


def handle_generated_json_artifact(
    path: Path,
    generated_full: str,
    *,
    dry_run: bool,
    print_diff: bool,
) -> FileResult:
    if not path.exists():
        changed, diff = write_or_diff(
            path, generated_full, dry_run=dry_run, print_diff=print_diff
        )
        return FileResult(
            path=path, action="created", message="created", changed=changed, diff=diff
        )

    existing = read_text(path)
    try:
        parsed = json.loads(existing)
    except Exception:
        parsed = None

    if isinstance(parsed, dict) and str(parsed.get("generated_by", "")) == "agentsgen":
        changed, diff = write_or_diff(
            path, generated_full, dry_run=dry_run, print_diff=print_diff
        )
        return FileResult(
            path=path,
            action="updated" if changed else "skipped",
            message="updated" if changed else "no changes",
            changed=changed,
            diff=diff,
        )

    gen_path = generated_sibling_path(path)
    changed, diff = write_or_diff(
        gen_path, generated_full, dry_run=dry_run, print_diff=print_diff
    )
    return FileResult(
        path=gen_path,
        action="generated",
        message=f"{path.name} has no markers; wrote {gen_path.name} instead",
        changed=changed,
        diff=diff,
    )
