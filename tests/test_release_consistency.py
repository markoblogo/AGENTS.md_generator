from __future__ import annotations

import re
import tomllib
from pathlib import Path

import agentsgen


ROOT = Path(__file__).resolve().parents[1]
RELEASE = "0.5.1"
SET_RELEASE = "0.4.0"
ID_RELEASE = "0.5.2"


def test_package_versions_match() -> None:
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    assert project["project"]["version"] == RELEASE
    assert agentsgen.__version__ == RELEASE


def test_public_docs_name_current_compatibility() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    integrations = (ROOT / "docs" / "ecosystem-integrations.md").read_text(
        encoding="utf-8"
    )
    site = (ROOT / "docs" / "index.html").read_text(encoding="utf-8")
    assert f"agentsgen {RELEASE} + SET {SET_RELEASE} + ID {ID_RELEASE}" in readme
    assert f"agentsgen {RELEASE}" in integrations
    assert f"SET {SET_RELEASE}" in integrations
    assert f"ID {ID_RELEASE}" in integrations
    assert f'"softwareVersion": "{RELEASE}"' in site
    assert f"V{RELEASE}" in site


def test_workflow_action_versions_are_current() -> None:
    workflow_text = "\n".join(
        path.read_text(encoding="utf-8")
        for path in (ROOT / ".github" / "workflows").glob("*.yml")
    )
    action = (
        ROOT / ".github" / "actions" / "agentsgen-guard" / "action.yml"
    ).read_text(encoding="utf-8")
    combined = workflow_text + action
    assert not re.search(r"actions/checkout@v[1-6](?:\D|$)", combined)
    assert "actions/setup-python@v7" in combined
