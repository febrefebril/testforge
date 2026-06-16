"""Tests for TestForge pipeline models: PipelineStage, PipelineManifest, PipelineInspector."""
import json
import os
import tempfile

from testforge.models import PipelineStage, PipelineManifest, PipelineInspector


def _make_raw_events(path: str, events: list[dict] | None = None) -> str:
    """Create a raw_events.jsonl file. Returns the file path."""
    if events is None:
        events = [
            {"event_id": "evt_00001", "type": "navigation",
             "timestamp": "2026-06-16T00:00:00",
             "url": "http://localhost:8765", "page_title": "App"},
            {"event_id": "evt_00002", "type": "fill",
             "timestamp": "2026-06-16T00:00:01",
             "url": "http://localhost:8765", "page_title": "App",
             "target": {"tag": "input", "id": "nameField", "placeholder": "Nome"},
             "value": "João"},
            {"event_id": "evt_00003", "type": "click",
             "timestamp": "2026-06-16T00:00:02",
             "url": "http://localhost:8765", "page_title": "App",
             "target": {"tag": "button", "text": "Enviar", "role": "button"},
             "screenshot": "screenshots/evt_00003.png"},
        ]
    file_path = os.path.join(path, "raw_events.jsonl")
    with open(file_path, "w") as f:
        for e in events:
            f.write(json.dumps(e) + "\n")
    return file_path


def _make_steps(path: str, steps: list[dict] | None = None) -> str:
    """Create a steps.jsonl file. Returns the file path."""
    if steps is None:
        steps = [
            {"step_id": "step_0001", "action": "click",
             "selector": "#btnPesquisar", "tagName": "button",
             "text": "Pesquisar", "value": "",
             "timestamp": "2026-06-16T00:00:03"},
            {"step_id": "step_0002", "action": "assert",
             "selector": "#resultado", "tagName": "div",
             "text": "Resultado encontrado", "value": "",
             "assert_type": "textual",
             "expected_value": "Resultado encontrado"},
        ]
    file_path = os.path.join(path, "steps.jsonl")
    with open(file_path, "w") as f:
        for s in steps:
            f.write(json.dumps(s) + "\n")
    return file_path


def _make_semantic_steps(path: str, steps: list[dict] | None = None,
                         metadata: dict | None = None) -> str:
    """Create a semantic_steps.jsonl file. Returns the file path."""
    if metadata is None:
        metadata = {"type": "metadata", "test_id": "ST-TEST",
                    "source_recording_id": "REC-001",
                    "application": "fake-bank",
                    "base_url": "http://localhost:8765",
                    "step_count": 3}
    if steps is None:
        steps = [
            {"action": "fill", "value": "12345678900",
             "target": {"role": "textbox", "label": "CPF",
                        "candidates": [
                            {"strategy": "id", "selector": "#cpfField", "score": 0.95},
                        ]}},
            {"action": "click",
             "target": {"role": "button", "label": "Pesquisar",
                        "candidates": [
                            {"strategy": "role", "selector": "role=button[name=\"Pesquisar\"]", "score": 0.95},
                        ]}},
            {"action": "click", "skip_reason": "Step 3: skipped — duplicate"},
        ]
    file_path = os.path.join(path, "semantic_steps.jsonl")
    with open(file_path, "w") as f:
        f.write(json.dumps(metadata, ensure_ascii=False) + "\n")
        for s in steps:
            f.write(json.dumps(s, ensure_ascii=False) + "\n")
    return file_path


def _make_script(path: str) -> str:
    """Create a test_flow.py script. Returns the file path."""
    content = '''"""Teste gerado pelo TestForge."""
from playwright.sync_api import Page, expect

BASE_URL = "http://localhost:8765"

def test_meu_fluxo(page: Page):
    """Fluxo gravado — source: REC-001."""
    page.goto(BASE_URL)

    # Step 1: fill (CPF)
    _sels = ['#cpfField']
    for _sel in _sels:
        try:
            page.fill(_sel, "12345678900")
            page.wait_for_timeout(200)
            break
        except Exception:
            continue
    else:
        raise AssertionError("fill step 1 falhou")
'''
    file_path = os.path.join(path, "test_meu_fluxo.py")
    with open(file_path, "w") as f:
        f.write(content)
    return file_path


# ---------------------------------------------------------------------------
# PipelineStage
# ---------------------------------------------------------------------------

class TestPipelineStage:
    """Tests for the PipelineStage enum."""

    def test_four_members_exist(self):
        """All four pipeline stages must be present."""
        members = list(PipelineStage)
        assert len(members) == 4
        values = {s.value for s in members}
        assert values == {"raw_events", "steps", "semantic_steps", "script"}

    def test_labels_are_human_readable(self):
        """Each stage should have a non-empty, human-readable label."""
        for stage in PipelineStage:
            assert stage.label, f"Empty label for {stage}"
            assert isinstance(stage.label, str)

    def test_stage_types_match(self):
        """Stage types should map correctly."""
        assert PipelineStage.RAW_EVENTS.stage_type == "capture"
        assert PipelineStage.STEPS.stage_type == "curated"
        assert PipelineStage.SEMANTIC_STEPS.stage_type == "compiled"
        assert PipelineStage.SCRIPT.stage_type == "executable"

    def test_file_names(self):
        """File names should match recording conventions."""
        assert PipelineStage.RAW_EVENTS.file_name == "raw_events.jsonl"
        assert PipelineStage.STEPS.file_name == "steps.jsonl"
        assert PipelineStage.SEMANTIC_STEPS.file_name == "semantic_steps.jsonl"
        assert PipelineStage.SCRIPT.file_name is None  # Script name varies

    def test_descriptions_non_empty(self):
        """Every stage should have a detailed description string."""
        for stage in PipelineStage:
            desc = stage.description
            assert desc, f"Empty description for {stage}"
            assert len(desc) > 50, f"Description too short for {stage}"

    def test_consumes_produces_consistency(self):
        """Pipeline graph must be acyclic and consistent."""
        # raw_events consumes nothing, is consumed by semantic_steps
        assert PipelineStage.RAW_EVENTS.consumes == []
        assert PipelineStage.SEMANTIC_STEPS in PipelineStage.RAW_EVENTS.produces

        # steps consumes nothing, is consumed by semantic_steps
        assert PipelineStage.STEPS.consumes == []
        assert PipelineStage.SEMANTIC_STEPS in PipelineStage.STEPS.produces

        # semantic_steps consumes raw_events + steps, produces script
        assert PipelineStage.RAW_EVENTS in PipelineStage.SEMANTIC_STEPS.consumes
        assert PipelineStage.STEPS in PipelineStage.SEMANTIC_STEPS.consumes
        assert PipelineStage.SCRIPT in PipelineStage.SEMANTIC_STEPS.produces

        # script consumes semantic_steps, produces nothing
        assert PipelineStage.SEMANTIC_STEPS in PipelineStage.SCRIPT.consumes
        assert PipelineStage.SCRIPT.produces == []

    def test_access_by_value(self):
        """Should be able to access PipelineStage by string value."""
        assert PipelineStage("raw_events") == PipelineStage.RAW_EVENTS
        assert PipelineStage("steps") == PipelineStage.STEPS
        assert PipelineStage("semantic_steps") == PipelineStage.SEMANTIC_STEPS
        assert PipelineStage("script") == PipelineStage.SCRIPT


# ---------------------------------------------------------------------------
# PipelineManifest
# ---------------------------------------------------------------------------

class TestPipelineManifest:
    """Tests for PipelineManifest — directory scanning."""

    def test_empty_directory(self):
        """Manifest of empty/nonexistent directory should show zero stages."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manifest = PipelineManifest(tmpdir)
            assert manifest.pipeline_depth == 0
            assert manifest.stages_present == []
            assert len(manifest.stages_missing) == 4
            assert not manifest.is_complete
            assert manifest.stage_path(PipelineStage.RAW_EVENTS) is None

    def test_missing_directory(self):
        """Manifest for non-existent directory handles gracefully."""
        manifest = PipelineManifest("/tmp/does_not_exist_xyz_testforge")
        assert manifest.pipeline_depth == 0

    def test_only_raw_events(self):
        """Directory with only raw_events.jsonl."""
        with tempfile.TemporaryDirectory() as tmpdir:
            _make_raw_events(tmpdir)
            manifest = PipelineManifest(tmpdir)
            assert manifest.pipeline_depth == 1
            assert PipelineStage.RAW_EVENTS in manifest.stages_present
            assert PipelineStage.STEPS not in manifest.stages_present
            assert manifest.stage_path(PipelineStage.RAW_EVENTS)
            assert not manifest.is_complete

    def test_only_steps(self):
        """Directory with only steps.jsonl."""
        with tempfile.TemporaryDirectory() as tmpdir:
            _make_steps(tmpdir)
            manifest = PipelineManifest(tmpdir)
            assert manifest.pipeline_depth == 1
            assert PipelineStage.STEPS in manifest.stages_present

    def test_full_four_stages(self):
        """Directory with all four pipeline stage files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            _make_raw_events(tmpdir)
            _make_steps(tmpdir)
            _make_semantic_steps(tmpdir)
            _make_script(tmpdir)
            manifest = PipelineManifest(tmpdir)
            assert manifest.pipeline_depth == 4
            assert manifest.is_complete
            assert manifest.stages_missing == []
            assert all(
                manifest.stage_path(s) is not None
                for s in PipelineStage
            )

    def test_script_detection_by_pattern(self):
        """Script detection uses test_*.py glob pattern."""
        with tempfile.TemporaryDirectory() as tmpdir:
            _make_script(tmpdir)
            manifest = PipelineManifest(tmpdir)
            assert manifest.script_path.endswith("test_meu_fluxo.py")

    def test_to_dict(self):
        """to_dict() should serialize manifest state."""
        with tempfile.TemporaryDirectory() as tmpdir:
            _make_raw_events(tmpdir)
            manifest = PipelineManifest(tmpdir)
            d = manifest.to_dict()
            assert d["recording_dir"] == tmpdir
            assert len(d["stages_present"]) == 1
            assert d["stages_present"][0] == "raw_events"
            assert d["pipeline_depth"] == 1
            assert not d["is_complete"]
            assert d["paths"]["raw_events"] is not None
            assert d["paths"]["steps"] is None

    def test_refresh_picks_up_new_files(self):
        """Calling refresh() after writing files should detect them."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manifest = PipelineManifest(tmpdir)
            assert manifest.pipeline_depth == 0

            _make_raw_events(tmpdir)
            manifest.refresh()
            assert manifest.pipeline_depth == 1

            _make_steps(tmpdir)
            manifest.refresh()
            assert manifest.pipeline_depth == 2


# ---------------------------------------------------------------------------
# PipelineInspector
# ---------------------------------------------------------------------------

class TestPipelineInspector:
    """Tests for PipelineInspector — file introspection."""

    # -- raw_events inspection --
    def test_inspect_raw_events(self):
        """inspect_raw_events should report event count and type histogram."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = _make_raw_events(tmpdir)
            result = PipelineInspector.inspect_raw_events(path)
            assert result["stage"] == "raw_events"
            assert result["event_count"] == 3
            assert result["event_types"] == {
                "navigation": 1, "fill": 1, "click": 1,
            }
            assert "http://localhost:8765" in result["unique_urls"]
            assert result["has_screenshots"] is True
            assert result["has_dom_snapshots"] is False

    def test_inspect_raw_events_empty(self):
        """Empty raw_events.jsonl should report zero events."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = _make_raw_events(tmpdir, events=[])
            result = PipelineInspector.inspect_raw_events(path)
            assert result["event_count"] == 0

    def test_inspect_raw_events_missing(self):
        """Inspecting a non-existent file should raise FileNotFoundError."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "raw_events.jsonl")
            try:
                PipelineInspector.inspect_raw_events(path)
                assert False, "Expected FileNotFoundError"
            except FileNotFoundError:
                pass

    # -- steps inspection --
    def test_inspect_steps(self):
        """inspect_steps should report step count and action breakdown."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = _make_steps(tmpdir)
            result = PipelineInspector.inspect_steps(path)
            assert result["stage"] == "steps"
            assert result["step_count"] == 2
            assert result["actions"] == {"click": 1, "assert": 1}
            assert "textual" in result["assert_types"]
            assert not result["has_blocking_steps"]
            assert not result["has_dependency_chains"]

    def test_inspect_steps_with_blocking(self):
        """Steps with blocking and depends_on should be detected."""
        with tempfile.TemporaryDirectory() as tmpdir:
            _make_steps(tmpdir, steps=[
                {"step_id": "step_0001", "action": "select_option",
                 "selector": "#uf", "tagName": "select", "blocking": True},
                {"step_id": "step_0002", "action": "click",
                 "selector": "#btn", "tagName": "button",
                 "depends_on": "step_0001"},
            ])
            result = PipelineInspector.inspect_steps(
                os.path.join(tmpdir, "steps.jsonl"))
            assert result["has_blocking_steps"] is True
            assert result["has_dependency_chains"] is True

    def test_inspect_steps_missing(self):
        """Inspecting a missing steps file should raise."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "steps.jsonl")
            try:
                PipelineInspector.inspect_steps(path)
                assert False, "Expected FileNotFoundError"
            except FileNotFoundError:
                pass

    # -- semantic_steps inspection --
    def test_inspect_semantic_steps(self):
        """inspect_semantic_steps should report metadata, steps, skip reasons."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = _make_semantic_steps(tmpdir)
            result = PipelineInspector.inspect_semantic_steps(path)
            assert result["stage"] == "semantic_steps"
            assert result["metadata"]["test_id"] == "ST-TEST"
            assert result["step_count"] == 3
            assert result["actions"] == {"fill": 1, "click": 2}
            assert len(result["skip_reasons"]) == 1
            assert "duplicate" in list(result["skip_reasons"].keys())[0]
            assert result["total_locator_candidates"] == 2

    def test_inspect_semantic_steps_empty_steps(self):
        """semantic_steps.jsonl with only metadata header."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = _make_semantic_steps(tmpdir, steps=[])
            result = PipelineInspector.inspect_semantic_steps(path)
            assert result["step_count"] == 0

    def test_inspect_semantic_steps_missing(self):
        """Inspecting a missing semantic_steps file should raise."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "semantic_steps.jsonl")
            try:
                PipelineInspector.inspect_semantic_steps(path)
                assert False, "Expected FileNotFoundError"
            except FileNotFoundError:
                pass

    # -- script inspection --
    def test_inspect_script(self):
        """inspect_script should report line count, function, step count."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = _make_script(tmpdir)
            result = PipelineInspector.inspect_script(path)
            assert result["stage"] == "script"
            assert result["function_name"] == "test_meu_fluxo"
            assert result["test_steps"] == 1
            assert result["line_count"] > 0
            assert result["has_fallback_loops"] is True
            assert result["has_data_driven_support"] is False

    def test_inspect_script_with_data_driven(self):
        """Script with data-driven JSON fixture should be detected."""
        with tempfile.TemporaryDirectory() as tmpdir:
            content = '''"""Teste."""
from playwright.sync_api import Page

BASE_URL = "http://localhost:8765"
_DATA_FILE = os.path.join(os.path.dirname(__file__), "data.json")
_data = {}
def test_fluxo(page: Page):
    page.goto(BASE_URL)
    # Step 1: fill
'''
            path = os.path.join(tmpdir, "test_fluxo.py")
            with open(path, "w") as f:
                f.write(content)
            result = PipelineInspector.inspect_script(path)
            assert result["has_data_driven_support"] is True

    def test_inspect_script_missing(self):
        """Inspecting a missing script should raise."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "test_missing.py")
            try:
                PipelineInspector.inspect_script(path)
                assert False, "Expected FileNotFoundError"
            except FileNotFoundError:
                pass

    # -- auto-dispatch inspection --
    def test_inspect_stage_dispatches_correctly(self):
        """inspect_stage() should dispatch to correct specialist inspector."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = _make_raw_events(tmpdir)
            result = PipelineInspector.inspect_stage(
                PipelineStage.RAW_EVENTS, path)
            assert result["stage"] == "raw_events"
            assert result["event_count"] == 3

    def test_inspect_stage_invalid_stage(self):
        """inspect_stage() with invalid stage should raise ValueError."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = _make_raw_events(tmpdir)
            try:
                PipelineInspector.inspect_stage(None, path)
                assert False, "Expected ValueError"
            except ValueError:
                pass

    # -- directory inspection --
    def test_inspect_directory_all_stages(self):
        """inspect_directory should discover and report on all found stages."""
        with tempfile.TemporaryDirectory() as tmpdir:
            _make_raw_events(tmpdir)
            _make_steps(tmpdir)
            _make_semantic_steps(tmpdir)
            _make_script(tmpdir)
            results = PipelineInspector.inspect_directory(tmpdir)
            assert len(results) == 4
            assert "raw_events" in results
            assert "steps" in results
            assert "semantic_steps" in results
            assert "script" in results
            for stage_key, report in results.items():
                assert report["stage"] == stage_key

    def test_inspect_directory_partial(self):
        """inspect_directory should only report on present stages."""
        with tempfile.TemporaryDirectory() as tmpdir:
            _make_raw_events(tmpdir)
            _make_steps(tmpdir)
            # No semantic_steps or script
            results = PipelineInspector.inspect_directory(tmpdir)
            assert len(results) == 2
            assert "raw_events" in results
            assert "steps" in results

    def test_inspect_directory_empty(self):
        """inspect_directory of empty dir should return empty dict."""
        with tempfile.TemporaryDirectory() as tmpdir:
            results = PipelineInspector.inspect_directory(tmpdir)
            assert results == {}
