from pathlib import Path

from testforge.cli.app import cmd_compile


class _Args:
    def __init__(self, recording):
        self.recording = recording
        self.app = ""
        self.application = ""
        self.base_url = ""
        self.check = False
        self.audit = False
        self.data = False
        self.scenarios = False
        self.use_v2_compiler = False
        self.output = None


def test_when_bug_report_exists_then_compile_emits_bug_markdown(tmp_path, monkeypatch):
    from testforge.cli import app as app_mod

    project_root = tmp_path
    rec_dir = project_root / "recordings" / "rec_bug"
    rec_dir.mkdir(parents=True, exist_ok=True)

    # Minimal metadata and empty events to allow compile path to execute.
    (rec_dir / "recording_metadata.json").write_text(
        '{"application":"app","base_url":"http://localhost","recording_status":"intent_complete"}',
        encoding="utf-8",
    )
    (rec_dir / "raw_events.jsonl").write_text("", encoding="utf-8")
    (rec_dir / "bug_report.jsonl").write_text(
        '{"bug_id":"BUG-20260701-12345","timestamp":"2026-07-01T12:00:00Z","recording_id":"rec_bug","step_idx":1,"signals":[],"observed_behavior":"500","user_expected_behavior":"success","source":"application_under_test","severity":"critical"}\n',
        encoding="utf-8",
    )

    monkeypatch.setattr(app_mod, "_PROJECT_ROOT", project_root)

    class _DummyStatus:
        value = "intent_complete"

    class _DummyRecordingStatus:
        @staticmethod
        def blocked_compile_states():
            return set()

        def __new__(cls, _value):
            return _DummyStatus()

    monkeypatch.setattr(app_mod, "RecordingStatus", _DummyRecordingStatus)

    # Keep compile lightweight by stubbing normalizer/compiler hot path.
    class _DummySTC:
        steps = []
        base_url = "http://localhost"
        test_id = "ST-rec_bug"
        source_recording_id = "rec_bug"
        application = "app"

    class _DummyNormalizer:
        def normalize(self, *args, **kwargs):
            return _DummySTC()

    class _DummyCompiler:
        def compile(self, stc, out_dir, data_file=""):
            out = Path(out_dir)
            out.mkdir(parents=True, exist_ok=True)
            script = out / "test_st_rec_bug.py"
            script.write_text("def test_stub():\n    assert True\n", encoding="utf-8")
            return str(script)

        def compile_semantic_steps(self, stc, out_dir):
            out = Path(out_dir) / "semantic_steps.jsonl"
            out.write_text('{"type":"metadata"}\n', encoding="utf-8")
            return str(out)

    monkeypatch.setattr(app_mod, "RecordingNormalizer", _DummyNormalizer)
    monkeypatch.setattr(app_mod, "PlaywrightCompiler", _DummyCompiler)
    monkeypatch.setattr(app_mod, "IntentCompletenessChecker", lambda: None)

    class _DummyAuditor:
        def audit(self, rec):
            return {}

        def print_report(self, rep):
            return None

    monkeypatch.setitem(__import__("sys").modules, "testforge.recorder.recording_auditor", type("M", (), {"RecordingAuditor": _DummyAuditor}))

    args = _Args("rec_bug")
    cmd_compile(args)

    bug_doc = project_root / "docs" / "bugs" / "BUG-20260701-12345.md"
    assert bug_doc.exists()
    content = bug_doc.read_text(encoding="utf-8")
    assert "Comportamento observado" in content
    assert "Referencia no teste gerado" in content
