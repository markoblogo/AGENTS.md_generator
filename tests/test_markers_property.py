from __future__ import annotations

from hypothesis import given, strategies as st

from agentsgen.markers import replace_section_content, validate_markers


@given(st.text(alphabet=st.characters(blacklist_categories=("Cs",)), max_size=40))
def test_replace_section_content_is_idempotent(body: str) -> None:
    text = (
        "<!-- AGENTSGEN:START section=workflow -->\n"
        "old\n"
        "<!-- AGENTSGEN:END section=workflow -->\n"
    )
    once, ok = replace_section_content(text, "workflow", body)
    twice, ok2 = replace_section_content(once, "workflow", body)
    assert ok is True
    assert ok2 is True
    assert once == twice


def test_validate_markers_reports_nested_duplicate_mismatch_and_unclosed() -> None:
    text = """
<!-- AGENTSGEN:START section=alpha -->
<!-- AGENTSGEN:START section=alpha -->
<!-- AGENTSGEN:END section=beta -->
"""
    problems = validate_markers(text)
    kinds = {item.kind for item in problems}
    assert "nested" in kinds
    assert "duplicate" in kinds
    assert "mismatch" in kinds or "unclosed" in kinds


def test_validate_markers_accepts_legacy_and_current_syntax() -> None:
    text = """
<!-- AGENTSGEN:START workflow -->
ok
<!-- AGENTSGEN:END workflow -->
<!-- AGENTSGEN:START section=repo_context -->
ok
<!-- AGENTSGEN:END section=repo_context -->
"""
    assert validate_markers(text) == []
