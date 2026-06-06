from __future__ import annotations

import json
from pathlib import Path

from agentsgen.contracts import schema_snapshots


GOLDEN = Path(__file__).parent / "golden" / "schemas"


def _stable_json(payload: dict[str, object]) -> str:
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


def test_contract_schema_snapshots() -> None:
    for name, schema in schema_snapshots().items():
        golden_path = GOLDEN / f"{name}.json"
        assert golden_path.exists(), f"Missing golden schema snapshot: {golden_path}"
        expected = golden_path.read_text(encoding="utf-8")
        assert _stable_json(schema) == expected
