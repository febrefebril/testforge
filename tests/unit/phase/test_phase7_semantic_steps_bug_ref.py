from testforge.semantic.compiler import PlaywrightCompiler
from testforge.semantic.model import SemanticAction


def test_when_step_context_has_bug_ref_then_semantic_record_includes_bug_ref():
    compiler = PlaywrightCompiler()
    step = SemanticAction(
        action="click",
        context={
            "has_bug_ref": {
                "bug_id": "BUG-20260701-00001",
                "observed_behavior": "500",
                "user_expected_behavior": "success",
            }
        },
    )

    record = compiler._step_to_record(step)

    assert "has_bug_ref" in record
    assert record["has_bug_ref"]["bug_id"] == "BUG-20260701-00001"
