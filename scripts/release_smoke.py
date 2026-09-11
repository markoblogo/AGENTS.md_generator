"""Reproducible release demos against the installed CLI; no API keys needed."""

import argparse
import hashlib
import json
import subprocess
import tempfile
import time
from pathlib import Path


def run(exe, root, args, expected=0):
    result = subprocess.run(
        [exe, args[0], str(root), *args[1:]],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != expected:
        raise SystemExit(
            f"{args}: expected {expected}, got {result.returncode}\n{result.stdout}\n{result.stderr}"
        )
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--exe", default="agentsgen")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    rows = []
    with tempfile.TemporaryDirectory() as temp:
        base = Path(temp)
        for case in ("handwritten", "stale-command", "clean-start"):
            root = base / case
            root.mkdir()
            started = time.perf_counter()
            if case == "handwritten":
                original = b"# Team rules\nNever discard handwritten instructions.\n"
                (root / "AGENTS.md").write_bytes(original)
                run(args.exe, root, ["init", "--defaults", "--autodetect"])
                assert (root / "AGENTS.md").read_bytes() == original
                assert (root / "AGENTS.generated.md").is_file()
                detail = {
                    "original_sha256": hashlib.sha256(original).hexdigest(),
                    "preserved": True,
                }
            elif case == "stale-command":
                manifest = root / "package.json"
                manifest.write_text(
                    json.dumps({"name": "demo", "scripts": {"test": "node --test"}})
                )
                run(args.exe, root, ["init", "--defaults", "--autodetect"])
                run(args.exe, root, ["check", "--ci"])
                manifest.write_text(json.dumps({"name": "demo", "scripts": {}}))
                run(args.exe, root, ["check", "--ci"], expected=1)
                detail = {"valid_exit": 0, "deleted_script_exit": 1}
            else:
                run(args.exe, root, ["init", "--defaults", "--autodetect"])
                agents_text = (root / "AGENTS.md").read_text(encoding="utf-8")
                agents_lines = len(agents_text.splitlines())
                agents_bytes = len(agents_text.encode("utf-8"))
                assert agents_lines <= 160
                run(args.exe, root, ["check", "--ci"])
                run(args.exe, root, ["fix", "--all"])
                before = {
                    str(p.relative_to(root)): p.read_bytes()
                    for p in root.rglob("*")
                    if p.is_file()
                }
                run(args.exe, root, ["fix", "--all"])
                after = {
                    str(p.relative_to(root)): p.read_bytes()
                    for p in root.rglob("*")
                    if p.is_file()
                }
                assert before == after
                run(args.exe, root, ["check", "--all", "--ci"])
                detail = {
                    "agents_md_lines": agents_lines,
                    "agents_md_bytes": agents_bytes,
                    "second_fix_changed_files": 0,
                    "full_check_exit": 0,
                }
            rows.append(
                {
                    "demo": case,
                    "seconds": round(time.perf_counter() - started, 3),
                    **detail,
                }
            )
    report = {
        "version": 1,
        "measurement": "local CLI wall time; not an AI performance benchmark",
        "results": rows,
    }
    text = json.dumps(report, indent=2) + "\n"
    if args.output:
        args.output.write_text(text)
    print(text, end="")


if __name__ == "__main__":
    main()
