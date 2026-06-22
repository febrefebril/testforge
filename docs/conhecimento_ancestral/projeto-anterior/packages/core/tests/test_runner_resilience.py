"""Tests for Story E.1: Runner resilience features."""
import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from testforge.core.models.step import StepResult
from testforge.core.execution.runner import TestRunner, PostActionValidator, CONSOLE_ERROR_PATTERNS


class TestPostActionValidator:
    def test_valid_no_error(self):
        page = MagicMock()
        page.evaluate.return_value = None
        v = PostActionValidator()
        assert v.validate(page, "click") is None

    def test_detects_console_error(self):
        v = PostActionValidator()
        result = v._check_console(["Error: CPF inválido"])
        assert result is not None
        assert "Console" in result

    def test_console_none_returns_none(self):
        v = PostActionValidator()
        assert v._check_console(None) is None
        assert v._check_console([]) is None

    def test_detects_network_5xx(self):
        v = PostActionValidator()
        result = v._check_network(["500 https://api.caixa.gov.br/consulta"])
        assert result is not None
        assert "Network" in result

    def test_network_4xx_no_pattern(self):
        v = PostActionValidator()
        result = v._check_network(["404 https://analytics.google.com/beacon"])
        assert result is None

    def test_detects_network_with_erro_text(self):
        v = PostActionValidator()
        result = v._check_network(["400 https://api.com/erro-validacao"])
        assert result is not None

    def test_check_url_no_error(self):
        page = MagicMock()
        page.evaluate.return_value = "https://www.caixa.gov.br/simulador"
        v = PostActionValidator()
        assert v._check_url(page) is None

    def test_check_url_with_error_indicator(self):
        page = MagicMock()
        page.evaluate.return_value = "https://www.caixa.gov.br/erro?code=500"
        v = PostActionValidator()
        assert v._check_url(page) is not None

    def test_check_url_evaluate_fails(self):
        page = MagicMock()
        page.evaluate.side_effect = Exception("fail")
        v = PostActionValidator()
        assert v._check_url(page) is None

    def test_selectors_js_finds_none(self):
        page = MagicMock()
        page.evaluate.return_value = None
        v = PostActionValidator()
        assert v._check_selectors_js(page, v.ERROR_SELECTORS) is None

    def test_selectors_js_finds_error(self):
        page = MagicMock()
        page.evaluate.return_value = {
            "selector": ".blockUI",
            "text": "",
            "visible": True,
        }
        v = PostActionValidator()
        result = v._check_selectors_js(page, v.ERROR_SELECTORS + v.BLOCKING_SELECTORS)
        assert result is not None
        assert "blockUI" in result

    def test_selectors_js_invisible(self):
        page = MagicMock()
        page.evaluate.return_value = None
        v = PostActionValidator()
        result = v._check_selectors_js(page, v.ERROR_SELECTORS + v.BLOCKING_SELECTORS)
        assert result is None

    def test_error_text_js_finds_pattern(self):
        page = MagicMock()
        page.evaluate.return_value = "cpf inválido"
        v = PostActionValidator()
        result = v._check_error_text_js(page)
        assert result is not None
        assert "cpf inválido" in result

    def test_error_text_js_finds_none(self):
        page = MagicMock()
        page.evaluate.return_value = None
        v = PostActionValidator()
        assert v._check_error_text_js(page) is None

    def test_error_text_js_evaluate_fails(self):
        page = MagicMock()
        page.evaluate.side_effect = Exception("fail")
        v = PostActionValidator()
        result = v.validate(page, "click")
        assert result is None

class TestRunnerCascading:
    @pytest.fixture
    def runner(self):
        r = TestRunner.__new__(TestRunner)
        r.script_path = Path("test.py")
        r.data_path = Path("test.data.json")
        r.headed = False
        r.global_timeout = 30000
        r.slow_mo = 0
        r.debug = False
        r.healing_db = ""
        r.results = []
        r._screenshot_dir = None
        r._step_console_errors = []
        r._step_network_errors = []
        r._cascading_failures = {}
        r._last_error_message = ""
        r._cascading_stop = False
        r._dialog_dismiss_attempted = False
        r._first_error_step = 0
        return r

    def test_cascading_stops_after_4_identical(self, runner):
        error = "Erro visível: .blockUI"
        runner._last_error_message = error
        runner._cascading_failures = {error: 3}
        assert runner._cascading_failures.get(error, 0) >= 3

    def test_cascading_not_triggered_by_different_errors(self, runner):
        runner._last_error_message = "Error 1"
        runner._cascading_failures["Error 1"] = 1
        runner._last_error_message = "Error 2"
        runner._cascading_failures = {"Error 2": 1}
        assert runner._cascading_failures.get("Error 1", 0) == 0
        assert runner._cascading_failures.get("Error 2", 0) == 1

    def test_report_root_cause_extraction(self, runner):
        runner.results = [
            StepResult(name="passo_1", status="passed"),
            StepResult(name="passo_2", status="failed", error_message="Erro: .ui-dialog"),
            StepResult(name="passo_3", status="failed", error_message="Erro: .ui-dialog"),
            StepResult(name="passo_4", status="failed", error_message="Erro: .ui-dialog"),
            StepResult(name="passo_5", status="skipped", error_message="Erro: .ui-dialog"),
        ]
        runner._last_error_message = "Erro: .ui-dialog"
        runner._cascading_stop = True
        runner._first_error_step = 2
        root = runner._extract_root_cause()
        assert "Erro: .ui-dialog" in root
        assert "passo 2" in root

    def test_root_cause_from_steps_without_cascading(self, runner):
        runner.results = [
            StepResult(name="passo_1", status="failed", error_message="Erro 1"),
            StepResult(name="passo_2", status="failed", error_message="Erro 1"),
            StepResult(name="passo_3", status="passed"),
        ]
        runner._last_error_message = ""
        runner._cascading_stop = False
        root = runner._extract_root_cause()
        assert "Erro 1" in root
        assert "passo 1" in root

    def test_no_root_cause_when_all_unique(self, runner):
        runner.results = [
            StepResult(name="passo_1", status="failed", error_message="Erro A"),
            StepResult(name="passo_2", status="failed", error_message="Erro B"),
            StepResult(name="passo_3", status="passed"),
        ]
        runner._last_error_message = ""
        runner._cascading_stop = False
        root = runner._extract_root_cause()
        assert root == ""

    def test_build_executive_with_root_cause(self, runner):
        result = runner._build_executive(1, 3, 30, 34, "Erro: .ui-dialog-titlebar")
        assert "Causa raiz" in result
        assert "ui-dialog-titlebar" in result
        assert "1 passaram" not in result
        assert "3 falharam" not in result

    def test_build_executive_all_passed(self, runner):
        result = runner._build_executive(34, 0, 0, 34)
        assert "concluído com sucesso" in result

    def test_build_executive_with_skips(self, runner):
        result = runner._build_executive(30, 0, 4, 34)
        assert "ignorado" in result

    def test_is_dialog_error_on_runner(self, runner):
        assert runner._is_dialog_error(".ui-dialog-titlebar")
        assert runner._is_dialog_error(".blockUI")
        assert not runner._is_dialog_error("Texto de erro")
        assert not runner._is_dialog_error(".alert-danger")


class TestActionConfidence:
    def test_fill_with_empty_result(self):
        page = MagicMock()
        page.evaluate.return_value = {"ok": False, "reason": "empty"}
        runner = TestRunner.__new__(TestRunner)
        runner._step_console_errors = []
        runner._step_network_errors = []
        result = runner._check_action_effect(page, "fill", "#input", "123", {})
        assert result is not None
        assert "vazio" in result

    def test_fill_ignored_when_value_present(self):
        page = MagicMock()
        page.evaluate.return_value = {"ok": True}
        runner = TestRunner.__new__(TestRunner)
        result = runner._check_action_effect(page, "fill", "#input", "123", {})
        assert result is None

    def test_fill_no_selector(self):
        runner = TestRunner.__new__(TestRunner)
        result = runner._check_action_effect(MagicMock(), "fill", "", "", {})
        assert result is None

    def test_fill_ignored_with_masked_value(self):
        page = MagicMock()
        page.evaluate.return_value = {"ok": True}
        runner = TestRunner.__new__(TestRunner)
        result = runner._check_action_effect(page, "fill", "#input", "12345678901", {})
        assert result is None

    def test_click_not_checked(self):
        runner = TestRunner.__new__(TestRunner)
        result = runner._check_action_effect(MagicMock(), "click", "#btn_next", "", {})
        assert result is None

    def test_select_empty_after_select_action(self):
        page = MagicMock()
        page.evaluate.return_value = {"ok": False, "reason": "select_mismatch", "actual": "", "expected": "opt1"}
        runner = TestRunner.__new__(TestRunner)
        runner._step_console_errors = []
        runner._step_network_errors = []
        result = runner._check_action_effect(page, "select", "#select1", "opt1", {})
        assert result is not None
        assert "select=" in result

    def test_combobox_fill_detects_empty_hidden_select(self):
        page = MagicMock()
        page.evaluate.return_value = {"ok": False, "reason": "combobox_empty", "actual": "Residencial", "expected": "Residencial"}
        runner = TestRunner.__new__(TestRunner)
        result = runner._check_action_effect(page, "fill", "#tipoImovel_input", "Residencial", {})
        assert result is not None
        assert "select" in result.lower() and "oculto" in result.lower()

    def test_click_autocomplete_detects_stale_combobox(self):
        page = MagicMock()
        page.evaluate.return_value = {"id": "tipoImovel_input", "val": "Residencial"}
        runner = TestRunner.__new__(TestRunner)
        runner._last_combobox_input = "#tipoImovel_input"
        result = runner._check_action_effect(page, "click", "a:has-text(\"Residencial\")", "", {"fallbacks": ["a:has-text(\"Residencial\")", "#ui-id-14"]})
        assert result is not None
        assert "combobox" in result.lower()


class TestConsoleErrorPatterns:
    def test_patterns_contain_portuguese_keywords(self):
        assert "erro" in CONSOLE_ERROR_PATTERNS
        assert "cpf" in CONSOLE_ERROR_PATTERNS
        assert "bloque" in CONSOLE_ERROR_PATTERNS
        assert "invalid" in CONSOLE_ERROR_PATTERNS

    def test_all_patterns_are_lowercase(self):
        for p in CONSOLE_ERROR_PATTERNS:
            assert p == p.lower(), f"Pattern '{p}' is not lowercase"
