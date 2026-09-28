from agentsgen.shared_sections import render_workflow


def test_workflow_emphasizes_scoped_isolation_and_evidence() -> None:
    workflow = render_workflow({})

    assert "inspect the current worktree" in workflow
    assert "genuinely shared mechanics" in workflow
    assert "narrowest useful evidence" in workflow
    assert "same important view/state before and after" in workflow
    assert (
        "distinguish local checks from CI, deployment, and release status" in workflow
    )
    assert "Do not commit, push, or deploy unless requested" in workflow
