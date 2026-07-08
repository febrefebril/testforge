"""Fase 4 BUG-REC-19/51/52/53/54: value_mutation dedup + placeholder skip
+ whitespace strip.

Static tests on overlay_inject.js verifying invariants.
"""
import re
from pathlib import Path

import pytest


OVERLAY_JS = (
    Path(__file__).resolve().parents[3]
    / "src" / "testforge" / "recorder" / "overlay_inject.js"
)


@pytest.fixture(scope="module")
def overlay_source() -> str:
    return OVERLAY_JS.read_text(encoding="utf-8")


@pytest.mark.unit
class TestValueMutationDedup:
    def test_last_mutation_by_fp_dict_initialized(self, overlay_source):
        assert "__tfLastMutationByFp" in overlay_source, (
            "Missing dedup dict. BUG-REC-19/51 regression: currency mask "
            "emits 13 mutations per '1.000,00'."
        )

    def test_hook_value_dedups_consecutive_identical(self, overlay_source):
        # Verify the setter hook checks __tfLastMutationByFp before push
        pattern = re.compile(
            r"__tfLastMutationByFp\[_fp\]\s*===\s*_vTrim.*?return",
            re.DOTALL,
        )
        assert pattern.search(overlay_source), (
            "Value setter must dedup by fingerprint. BUG-REC-19."
        )

    def test_hook_value_strips_whitespace(self, overlay_source):
        # BUG-REC-53: currency mask emits ' 1.000,00 ' with padding
        assert "_vTrim = _vRaw.trim()" in overlay_source, (
            "Value must be trimmed. BUG-REC-53: currency space padding leak."
        )

    def test_hook_value_skips_placeholder(self, overlay_source):
        # BUG-REC-54: DD/MM/AAAA, c999999 leaked into value_mutations despite f1c1881
        pattern = re.compile(
            r"_ph\s*&&\s*_vTrim\s*===\s*_ph.*?return",
            re.DOTALL,
        )
        assert pattern.search(overlay_source), (
            "Setter hook must skip when value equals placeholder. BUG-REC-54."
        )

    def test_schedule_fill_also_skips_placeholder(self, overlay_source):
        # Cross-source fix: fill scheduler AND setter hook both filter placeholder
        # so no source emits placeholder as fill.
        pattern = re.compile(
            r"_scheduleFillFromMutation.*?ph\s*&&\s*val\s*===\s*ph.*?return",
            re.DOTALL,
        )
        assert pattern.search(overlay_source), (
            "_scheduleFillFromMutation must also skip placeholder values."
        )

    def test_bug_rec_traceability_comments(self, overlay_source):
        # Anti-regression: future maintainers see WHY
        assert "BUG-REC-19" in overlay_source
        assert "BUG-REC-53" in overlay_source
        assert "BUG-REC-54" in overlay_source
