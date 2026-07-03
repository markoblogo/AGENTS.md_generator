from __future__ import annotations

import argparse
import datetime as dt
from pathlib import Path

from agentsgen.fleet import (
    build_fleet_scan_report,
    write_fleet_scan_outputs,
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Scan many git repos and report agentsgen readiness (dry-run only)"
    )
    parser.add_argument("--root", action="append", required=True)
    parser.add_argument("--max-depth", type=int, default=2)
    parser.add_argument("--out", default="")
    parser.add_argument("--json-out", default="")
    args = parser.parse_args()

    timestamp = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    stamp = timestamp.replace(":", "").replace("+", "-")
    markdown_path = (
        Path(args.out) if args.out else Path(f"/tmp/agentsgen-scan-{stamp}.md")
    )
    json_path = (
        Path(args.json_out)
        if args.json_out
        else Path(f"/tmp/agentsgen-scan-{stamp}.json")
    )
    report = build_fleet_scan_report(
        [Path(root) for root in args.root],
        max_depth=args.max_depth,
        timestamp=timestamp,
    )
    write_fleet_scan_outputs(report, markdown_path=markdown_path, json_path=json_path)
    print(str(markdown_path))
    print(str(json_path))


if __name__ == "__main__":
    main()
