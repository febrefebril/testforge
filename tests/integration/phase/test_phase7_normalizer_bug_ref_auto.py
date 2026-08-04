
from pathlib import Path

from testforge.semantic.model import LocatorCandidate, SemanticAction, SemanticTarget
from testforge.semantic.recording_normalizer import RecordingNormalizer


def test_when_bug_report_exists_then_normalize_attaches_has_bug_ref(tmp_path, monkeypatch):
    rec_dir = Path(tmp_path) / "rec"
    rec_dir.mkdir(parents=True, exist_ok=True)

    (rec_dir / "raw_events.jsonl").write_text(
        '{"event_id":"evt_00001","type":"navigation","timestamp":"2026-07-01T12:00:00Z"}\n'
        '{"event_id":"evt_00002","type":"click","timestamp":"2026-07-01T12:00:01Z"}\n',
        encoding="utf-8",
    )

    (rec_dir / "bug_report.jsonl").write_text(
        '{"bug_id":"BUG-20260701-00077","timestamp":"2026-07-01T12:00:05Z","step_idx":1,'
        '"observed_behavior":"500","user_expected_behavior":"success",'
        '"severity":"critical","source":"application_under_test"}\n',
        encoding="utf-8",
    )

    normalizer = RecordingNormalizer()

    def _fake_convert_event(raw):
        typ = raw.get("type")
        if typ == "navigation":
            return SemanticAction(action="navigation", context={"timestamp": raw.get("timestamp", "")})
        if typ == "click":
            return SemanticAction(
                action="click",
                target=SemanticTarget(
                    role="button",
                    accessible_name="Salvar",
                    tag="button",
                    candidates=[
                        LocatorCandidate(
                            strategy="role",
                            selector='role=button[name="Salvar"]',
                            score=0.9,
                        )
                    ],
                ),
                context={"timestamp": raw.get("timestamp", "")},
            )
        return None

    monkeypatch.setattr(normalizer, "_convert_event", _fake_convert_event)
    monkeypatch.setattr(normalizer, "_detect_overlay_steps", lambda steps: None)
    monkeypatch.setattr(normalizer, "_deduplicate_steps", lambda steps: None)
    monkeypatch.setattr(normalizer, "_mark_non_actionable", lambda steps: None)
    monkeypatch.setattr(normalizer, "_detect_step_dependencies", lambda steps: None)
    monkeypatch.setattr(normalizer, "_detect_navigation_clicks", lambda steps: None)
    monkeypatch.setattr(normalizer, "_reconstruct_intents", lambda stc, rec: None)
    monkeypatch.setattr(normalizer, "_detect_missing_fills", lambda steps: None)
    monkeypatch.setattr(normalizer, "_build_field_value_map", lambda stc: None)
    monkeypatch.setattr(normalizer, "_eliminate_prefill_clicks", lambda steps, recording_dir="": None)
    monkeypatch.setattr(normalizer, "_detect_stale_asserts", lambda steps: None)
    monkeypatch.setattr(normalizer, "_audit_blind_spots", lambda stc: None)

    stc = normalizer.normalize(str(rec_dir), test_id="ST-rec", application="app", base_url="http://localhost")

    non_nav = [s for s in stc.steps if s.action != "navigation"]
    assert len(non_nav) == 1
    bug_ref = non_nav[0].context.get("has_bug_ref")
    assert bug_ref is not None
    assert bug_ref["bug_id"] == "BUG-20260701-00077"
    assert bug_ref["severity"] == "critical"


def test_when_multiple_reports_same_step_then_highest_severity_selected(tmp_path):
    normalizer = RecordingNormalizer()
    step = SemanticAction(action="click", context={})

    class _Stc:
        steps = [step]

    reports = [
        {
            "bug_id": "BUG-LOW",
            "step_idx": 1,
            "severity": "low",
            "timestamp": "2026-07-01T10:00:00Z",
            "observed_behavior": "minor",
            "user_expected_behavior": "ok",
            "source": "application_under_test",
        },
        {
            "bug_id": "BUG-CRIT",
            "step_idx": 1,
            "severity": "critical",
            "timestamp": "2026-07-01T09:00:00Z",
            "observed_behavior": "major",
            "user_expected_behavior": "ok",
            "source": "application_under_test",
        },
    ]

    normalizer._attach_bug_refs(_Stc(), reports)

    assert step.context["has_bug_ref"]["bug_id"] == "BUG-CRIT"

