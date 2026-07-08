"""Regression tests: PII scanner output matches golden files for anchor recordings.

Fails when a fix adds/removes patterns unintentionally. Golden update requires
explicit PR justification per docs/ANTI-REGRESSION-PLAN.md Camada 3.
"""
import json
from pathlib import Path

import pytest

FIXTURES = Path(__file__).resolve().parents[2] / "fixtures" / "recordings"

ANCHORS = [
    "r5a_sifap_credentials",
    "r7a_siopi_producao",
]


@pytest.mark.regression
@pytest.mark.critical
@pytest.mark.parametrize("anchor", ANCHORS)
class TestPiiScanAnchorGoldens:
    def test_scan_summary_matches_golden(self, anchor):
        # Arrange
        rec = FIXTURES / anchor
        assert rec.is_dir(), f"anchor missing: {rec}"
        golden_path = rec / "expected" / "pii_scan_summary.json"
        assert golden_path.exists(), f"golden missing: {golden_path}"
        golden = json.loads(golden_path.read_text(encoding="utf-8"))

        from testforge.security import scan_recording

        # Act
        report = scan_recording(rec)
        actual = report.as_dict()

        # Assert — policy invariants
        assert actual["policy"] == golden["policy"] == "alert_only"
        assert actual["masking_applied"] is False
        assert golden["masking_applied"] is False

        # Assert — totals
        assert actual["totals"]["hits"] == golden["totals"]["hits"], (
            f"hit count changed. anchor={anchor} "
            f"expected={golden['totals']['hits']} actual={actual['totals']['hits']}"
        )
        assert actual["totals"]["critical"] == golden["totals"]["critical"], (
            f"critical count changed. anchor={anchor}"
        )
        assert actual["totals"]["by_pattern"] == golden["totals"]["by_pattern"], (
            f"pattern distribution changed. anchor={anchor}"
        )

        # Assert — production detection
        assert actual["production_domain_detected"] == golden["production_domain_detected"]

        # Assert — sources
        actual_sources = sorted(actual["hits_by_source"].keys())
        assert actual_sources == golden["sources_with_hits"], (
            f"source list changed. anchor={anchor} "
            f"golden={golden['sources_with_hits']} actual={actual_sources}"
        )
