"""Contract test: normalizer produces semantic steps from raw_events even when
steps.jsonl only contains asserts.

Historic assumption (BUG-REC-01): `steps.jsonl` publica só asserts → compile
gera teste vazio. WRONG — normalizer combines raw_events (source of truth for
actions) with steps.jsonl (assert curation only) to build SemanticTestCase.

This contract locks that invariant so a future fix doesn't inadvertently
collapse compile to steps.jsonl only.
"""
import pytest
from pathlib import Path


ANCHOR = Path(__file__).resolve().parents[1] / "fixtures" / "recordings" / "r5a_sifap_credentials"


@pytest.mark.contract
@pytest.mark.critical
class TestNormalizerMultiSource:
    def test_normalizer_produces_steps_beyond_steps_jsonl_count(self):
        """steps.jsonl in R5a has 1 assert. raw_events has 17 events.
        stc.steps must be > 1 (many actions + the assert)."""
        # Arrange
        assert ANCHOR.is_dir(), f"anchor missing: {ANCHOR}"
        raw = (ANCHOR / "raw_events.jsonl").read_text(encoding="utf-8")
        raw_count = len([l for l in raw.splitlines() if l.strip()])
        steps = (ANCHOR / "steps.jsonl").read_text(encoding="utf-8")
        steps_count = len([l for l in steps.splitlines() if l.strip()])
        assert raw_count > 5, "anchor should have >5 raw events"
        assert steps_count == 1, "anchor should have exactly 1 assert in steps.jsonl"

        from testforge.semantic import RecordingNormalizer

        # Act
        normalizer = RecordingNormalizer()
        stc = normalizer.normalize(str(ANCHOR))

        # Assert — semantic steps includes actions AND the assert
        assert len(stc.steps) > steps_count, (
            f"CONTRACT VIOLATION: stc.steps ({len(stc.steps)}) should be > "
            f"steps.jsonl count ({steps_count}). Normalizer must consume "
            f"raw_events for actions."
        )
        action_types = {s.action for s in stc.steps}
        # At least one action type beyond assert
        non_assert = action_types - {"assert"}
        assert non_assert, (
            f"CONTRACT VIOLATION: normalizer produced only asserts. "
            f"action_types={action_types}. Expected clicks/fills/navigations "
            f"from raw_events.jsonl."
        )

    def test_source_of_truth_documentation(self):
        """Meta-test: ensures architecture doc lists both sources."""
        docs = Path(__file__).resolve().parents[2] / "docs"
        arch = docs / "ARCHITECTURE-V2.md"
        if not arch.exists():
            pytest.skip("ARCHITECTURE-V2.md missing")
        content = arch.read_text(encoding="utf-8").lower()
        # Must mention both artifacts as sources
        assert "raw_events" in content
        assert "steps.jsonl" in content
