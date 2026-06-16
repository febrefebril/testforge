"""Testes do RunReport — full untruncated execution reports (BUG-016)."""
import json
import os
import tempfile
from testforge.reporting import RunReport, StepReport, save_report


class TestStepReport:
    """Testes do StepReport — captura completa de cada step."""

    def test_default_attributes(self):
        sr = StepReport(step_num=1, action="click")
        assert sr.step_num == 1
        assert sr.action == "click"
        assert sr.success is False
        assert sr.error_message == ""
        assert sr.candidates == []
        assert sr.selector_used == ""
        assert sr.value == ""
        assert sr.healing_attempted is False
        assert sr.healing_success is False
        assert sr.healing_layer == ""
        assert sr.healing_family == ""
        assert sr.healing_proposal_locator == ""
        assert sr.healing_confidence == 0.0
        assert sr.healing_raw_response == ""

    def test_full_candidates_not_truncated(self):
        """BUG-016: candidates must NOT be truncated — full list preserved."""
        full_candidates = [
            {"selector": "button:has-text('Pesquisar')", "score": 0.95},
            {"selector": "[type='submit']", "score": 0.80},
            {"selector": "#btnPesquisar", "score": 0.70},
            {"selector": ".search-btn", "score": 0.50},
            {"selector": "button.btn-primary", "score": 0.30},
        ]
        sr = StepReport(step_num=1, action="click", candidates=full_candidates)
        assert len(sr.candidates) == 5  # todos preservados, nao so [:3]

    def test_long_error_message_preserved(self):
        """BUG-016: error messages NOT truncated to [:300]."""
        long_error = "ERR: " + ("x" * 500) + " — final"
        sr = StepReport(step_num=2, action="fill", error_message=long_error)
        assert len(sr.error_message) > 300
        assert sr.error_message.endswith("— final")

    def test_long_healing_raw_response_preserved(self):
        """BUG-016: LLM raw_response NOT truncated to [:200]."""
        long_response = "RESP: " + ("y" * 500) + " — end"
        sr = StepReport(step_num=3, action="click",
                        healing_raw_response=long_response)
        assert len(sr.healing_raw_response) > 200
        assert sr.healing_raw_response.endswith("— end")

    def test_long_healing_locator_preserved(self):
        """BUG-016: healing locator NOT truncated to [:60]."""
        long_locator = "button[data-testid='submit-button-main'] >> text=" + ("z" * 80)
        sr = StepReport(step_num=4, action="click",
                        healing_proposal_locator=long_locator)
        assert len(sr.healing_proposal_locator) > 60
        assert sr.healing_proposal_locator.startswith("button[data-testid='submit-button-main']")

    def test_healing_success_tracking(self):
        sr = StepReport(step_num=1, action="fill")
        sr.healing_attempted = True
        sr.healing_success = True
        sr.healing_layer = "L2"
        sr.healing_family = "selector_resolution"
        assert sr.healing_attempted is True
        assert sr.healing_success is True
        assert sr.healing_layer == "L2"

    def test_skip_reason(self):
        sr = StepReport(step_num=5, action="fill", skip_reason="sem seletor")
        assert sr.skip_reason == "sem seletor"
        assert sr.success is False

    def test_assert_details(self):
        sr = StepReport(step_num=6, action="assert",
                        assert_type="textual", assert_expected="CPF encontrado",
                        assert_actual="CPF encontrado")
        assert sr.assert_type == "textual"
        assert sr.assert_expected == "CPF encontrado"
        assert sr.assert_actual == "CPF encontrado"

    def test_to_dict(self):
        sr = StepReport(
            step_num=1, action="click", success=True,
            candidates=[{"selector": "#btn", "score": 0.9}],
            selector_used="#btn",
            healing_attempted=False,
        )
        d = sr.to_dict()
        assert d["step_num"] == 1
        assert d["action"] == "click"
        assert d["success"] is True
        assert len(d["candidates"]) == 1
        assert d["candidates"][0]["selector"] == "#btn"


class TestRunReport:
    """Testes do RunReport — relatorio completo da execucao."""

    def test_create_empty_report(self):
        rr = RunReport(recording_id="REC-001", base_url="http://localhost")
        assert rr.recording_id == "REC-001"
        assert rr.base_url == "http://localhost"
        assert rr.total_steps == 0
        assert rr.failed_steps == 0
        assert rr.healed_steps == 0
        assert rr.steps == []
        assert rr.timestamp != ""

    def test_add_step(self):
        rr = RunReport(recording_id="REC-001", base_url="http://localhost")
        sr = StepReport(step_num=1, action="fill", success=True)
        rr.add_step(sr)
        assert len(rr.steps) == 1
        assert rr.steps[0].step_num == 1

    def test_add_multiple_steps(self):
        rr = RunReport(recording_id="REC-002", base_url="http://localhost",
                       total_steps=3)
        rr.add_step(StepReport(step_num=1, action="fill", success=True))
        rr.add_step(StepReport(step_num=2, action="click", success=True))
        rr.add_step(StepReport(step_num=3, action="assert", success=True,
                               error_message="assert failed"))
        assert len(rr.steps) == 3
        assert rr.steps[2].error_message == "assert failed"

    def test_to_dict_structure(self):
        rr = RunReport(recording_id="REC-001", base_url="http://localhost",
                       script_path="/path/test.py", total_steps=2,
                       failed_steps=1, healed_steps=1)
        rr.add_step(StepReport(step_num=1, action="fill", success=True))
        rr.add_step(StepReport(step_num=2, action="click",
                               error_message="not found",
                               healing_attempted=True,
                               healing_success=True,
                               healing_layer="L2"))
        d = rr.to_dict()
        assert d["recording_id"] == "REC-001"
        assert d["base_url"] == "http://localhost"
        assert d["script_path"] == "/path/test.py"
        assert d["total_steps"] == 2
        assert d["failed_steps"] == 1
        assert d["healed_steps"] == 1
        assert len(d["steps"]) == 2
        assert d["steps"][1]["healing_attempted"] is True

    def test_save_creates_json_file(self):
        rr = RunReport(recording_id="REC-TEST", base_url="http://localhost")
        rr.add_step(StepReport(step_num=1, action="fill", success=True))
        with tempfile.TemporaryDirectory() as tmpdir:
            path = rr.save(tmpdir)
            assert os.path.exists(path)
            assert path.endswith(".json")
            with open(path) as f:
                data = json.load(f)
            assert data["recording_id"] == "REC-TEST"
            assert len(data["steps"]) == 1

    def test_save_creates_directory_if_needed(self):
        rr = RunReport(recording_id="REC-TEST", base_url="http://localhost")
        with tempfile.TemporaryDirectory() as tmpdir:
            nested = os.path.join(tmpdir, "nested", "dir")
            path = rr.save(nested)
            assert os.path.exists(path)

    def test_save_report_convenience_function(self):
        rr = RunReport(recording_id="REC-TEST", base_url="http://localhost")
        with tempfile.TemporaryDirectory() as tmpdir:
            path = save_report(rr, tmpdir)
            assert os.path.exists(path)

    def test_full_candidates_serialized_without_truncation(self):
        """BUG-016: full candidates preserved in JSON output."""
        candidates = [
            {"selector": "x" * 100, "score": 0.9},
            {"selector": "y" * 100, "score": 0.8},
            {"selector": "z" * 100, "score": 0.7},
            {"selector": "w" * 100, "score": 0.6},
        ]
        rr = RunReport(recording_id="REC-FULL", base_url="http://localhost")
        sr = StepReport(step_num=1, action="click", candidates=candidates,
                        error_message="e" * 500,
                        healing_raw_response="r" * 500,
                        healing_proposal_locator="l" * 200)
        rr.add_step(sr)
        with tempfile.TemporaryDirectory() as tmpdir:
            path = rr.save(tmpdir)
            with open(path) as f:
                data = json.load(f)
            step = data["steps"][0]
            assert len(step["candidates"]) == 4  # todos preservados
            assert len(step["candidates"][0]["selector"]) == 100
            assert len(step["error_message"]) == 500
            assert len(step["healing_raw_response"]) == 500
            assert len(step["healing_proposal_locator"]) == 200
