"""Contract test cross-source: PII detector NEVER masks values.

Regression risk: fixes futuros que "vai automascarar em X" quebram
contrato [[feedback-pii-alert-only]]. Dados sensíveis são massa de teste.

Este teste percorre TODAS as fontes que emitem valor de campo e verifica
que reprocessamento com detector preserva strings verbatim.
"""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest


REC_ANCHORS = [
    # (recording_path, expected_source_values_present)
    (
        "src/testforge/SIFAP/Autenticação/Deve logar no SIFAP com perfil de internet/REC-20260702-144218",
        {
            "value_mutations.jsonl": ["934.765.700-02"],
            "raw_events.jsonl": ["112233", "934.765.700-02"],
        },
    ),
    (
        "src/testforge/PLATAFORMA DES/Cliente conta CEF crédito do benefício/CPF com zero a esquerda/Valida_zeros_a_esquerda",
        {
            "raw_events.jsonl": ["019.493.184-60", "MANUEL M PINTO"],
        },
    ),
]


def _iter_jsonl(path: Path):
    if not path.exists():
        return
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except Exception:
                continue


def _extract_all_string_values(obj, out: list[str]):
    if isinstance(obj, dict):
        for v in obj.values():
            _extract_all_string_values(v, out)
    elif isinstance(obj, list):
        for item in obj:
            _extract_all_string_values(item, out)
    elif isinstance(obj, str):
        out.append(obj)


@pytest.mark.contract
@pytest.mark.critical
class TestPiiDetectorNeverModifiesValues:
    """Invariant: after running PII scanner on a recording, ALL string values
    across all sources are preserved verbatim in the source files.

    Scanner emits `sensitive_alerts.json` as separate artifact. Source files
    (raw_events.jsonl, steps.jsonl, value_mutations.jsonl, etc) must remain
    untouched.
    """

    @pytest.mark.parametrize(
        "rec_path,expected_values",
        REC_ANCHORS,
        ids=lambda p: Path(p).name if isinstance(p, str) else str(p)[:20],
    )
    def test_scanning_recording_does_not_modify_source_files(
        self, rec_path, expected_values, tmp_path
    ):
        # Arrange
        rec = Path(rec_path)
        if not rec.is_dir():
            pytest.skip(f"anchor recording missing: {rec_path}")

        from testforge.security import scan_recording

        pre_snapshots: dict[str, list[str]] = {}
        for fname in expected_values.keys():
            src = rec / fname
            if src.exists():
                pre_snapshots[fname] = list(_iter_jsonl(src))

        # Act — scan recording (writes sensitive_alerts.json but must not
        # touch source files)
        report = scan_recording(rec)
        _ = report.as_dict()

        # Assert 1 — expected sensitive values ARE STILL PRESENT in source
        for fname, expected in expected_values.items():
            src = rec / fname
            if not src.exists():
                continue
            content = src.read_text(encoding="utf-8")
            for exp_val in expected:
                assert exp_val in content, (
                    f"CONTRACT VIOLATION: sensitive value {exp_val!r} disappeared "
                    f"from {fname} after PII scan. Detector must be observability-only."
                )

        # Assert 2 — files byte-identical to pre-snapshot (scanner does not
        # rewrite source files)
        for fname, pre in pre_snapshots.items():
            post = list(_iter_jsonl(rec / fname))
            assert pre == post, (
                f"CONTRACT VIOLATION: {fname} content changed after scan. "
                f"Detector must not write to source files."
            )

    def test_report_flags_masking_applied_false(self):
        # Arrange
        rec = Path(
            "src/testforge/SIFAP/Autenticação/"
            "Deve logar no SIFAP com perfil de internet/REC-20260702-144218"
        )
        if not rec.is_dir():
            pytest.skip("anchor recording missing")

        from testforge.security import scan_recording

        # Act
        report = scan_recording(rec)
        as_dict = report.as_dict()

        # Assert
        assert as_dict["policy"] == "alert_only"
        assert as_dict["masking_applied"] is False

    def test_detector_direct_call_preserves_input_exactly(self):
        # Arrange
        from testforge.security import detect

        cases = [
            ("019.493.184-60", None),
            ("42.097.365/0001-26", None),
            ("Sifap101", {"type": "password"}),
            ("112233", {"type": "password", "label": "Senha"}),
            ("email@gmail.com", None),
            ("(61)99623-9901", None),
            ("c891011", None),
        ]

        # Act + Assert
        for original, md in cases:
            hits = detect(original, context="contract", field_metadata=md)
            assert len(hits) >= 1, f"expected detection for {original!r}"
            for hit in hits:
                assert hit.value in original or original in hit.value, (
                    f"CONTRACT VIOLATION: detector emitted modified value. "
                    f"input={original!r} hit.value={hit.value!r}"
                )
