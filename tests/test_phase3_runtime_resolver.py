"""Fase 3 — LocatorResolver em tempo de execucao + step API + compilador v2.

Testes unitarios cobrem:
- dispatcher baseado em AST rejeita codigo arbitrario
- LocatorResolver cache L0 + cadeia de fallback L1
- helpers step.* roteiam via resolver
- compile_v2 emite script minimo + candidatos JSON por step
"""
from __future__ import annotations

import json
import os
import tempfile
from unittest.mock import MagicMock, call

import pytest

from testforge.runtime import LocatorResolver, LocatorNotFoundError, step
from testforge.runtime._pw_dispatch import dispatch
from testforge.semantic.compiler import PlaywrightCompiler
from testforge.semantic.model import (
    LocatorCandidate,
    SemanticAction,
    SemanticTarget,
    SemanticTestCase,
)


class TestPwDispatcher:
    def test_get_by_role_with_name(self):
        page = MagicMock()
        page.get_by_role.return_value = "ROLE_LOCATOR"
        result = dispatch(page, 'get_by_role("button", name="Salvar")')
        page.get_by_role.assert_called_once_with("button", name="Salvar")
        assert result == "ROLE_LOCATOR"

    def test_get_by_test_id(self):
        page = MagicMock()
        page.get_by_test_id.return_value = "TID"
        result = dispatch(page, 'get_by_test_id("save-btn")')
        page.get_by_test_id.assert_called_once_with("save-btn")
        assert result == "TID"

    def test_chained_get_by_role_dialog(self):
        page = MagicMock()
        inner = MagicMock()
        page.get_by_role.return_value = inner
        inner.get_by_role.return_value = "CHILD"
        result = dispatch(page, 'get_by_role("dialog").get_by_role("button", name="Salvar")')
        page.get_by_role.assert_called_once_with("dialog")
        inner.get_by_role.assert_called_once_with("button", name="Salvar")
        assert result == "CHILD"

    def test_rejects_non_allowlisted_method(self):
        page = MagicMock()
        with pytest.raises(ValueError, match="not allowed"):
            dispatch(page, 'evaluate("alert(1)")')

    def test_rejects_arbitrary_code(self):
        page = MagicMock()
        with pytest.raises(Exception):
            dispatch(page, '__import__("os").system("ls")')

    def test_locator_method_allowed(self):
        page = MagicMock()
        page.locator.return_value = "L"
        assert dispatch(page, 'locator("#foo")') == "L"
        page.locator.assert_called_once_with("#foo")


class TestLocatorResolver:
    def _candidate(self, strategy="role", call_str='get_by_role("button", name="X")',
                   score=0.9, selector="page.get_by_role(\"button\", name=\"X\")"):
        return {"strategy": strategy, "playwright_call": call_str,
                "selector": selector, "score": score}

    def test_l1_hit_first_candidate(self):
        page = MagicMock()
        locator = MagicMock()
        locator.count.return_value = 1
        page.get_by_role.return_value = locator
        resolver = LocatorResolver(page)
        result = resolver.resolve("click button X", [self._candidate()])
        assert result.level == "L1_candidate"
        assert result.strategy == "role"
        assert result.candidate_index == 0
        assert result.locator is locator

    def test_l1_skips_failing_first(self):
        page = MagicMock()
        bad = MagicMock(); bad.count.return_value = 0
        good = MagicMock(); good.count.return_value = 1
        page.get_by_role.return_value = bad
        page.get_by_test_id.return_value = good
        resolver = LocatorResolver(page)
        cands = [
            self._candidate(strategy="role"),
            {"strategy": "test_id", "playwright_call": 'get_by_test_id("save")',
             "selector": 'page.get_by_test_id("save")', "score": 0.8},
        ]
        result = resolver.resolve("click", cands)
        assert result.strategy == "test_id"
        assert result.candidate_index == 1

    def test_l0_cache_hit_on_repeat(self):
        page = MagicMock()
        locator = MagicMock(); locator.count.return_value = 1
        page.get_by_role.return_value = locator
        resolver = LocatorResolver(page)
        # Primeira chamada popula cache
        resolver.resolve("click button X", [self._candidate()])
        # Segunda chamada DEVE retornar como L0
        result = resolver.resolve("click button X", [self._candidate()])
        assert result.level == "L0_cache"

    def test_raises_when_no_candidate_hits(self):
        page = MagicMock()
        bad = MagicMock(); bad.count.return_value = 0
        page.get_by_role.return_value = bad
        resolver = LocatorResolver(page)
        with pytest.raises(LocatorNotFoundError) as exc:
            resolver.resolve("click X", [self._candidate()])
        assert exc.value.intent == "click X"

    def test_resolves_via_selector_when_no_playwright_call(self):
        page = MagicMock()
        locator = MagicMock(); locator.count.return_value = 1
        page.locator.return_value = locator
        resolver = LocatorResolver(page)
        cand = {"strategy": "css_path", "selector": "div > button", "score": 0.4}
        result = resolver.resolve("c", [cand])
        page.locator.assert_called_once_with("div > button")
        assert result.locator is locator

    def test_resolve_from_file(self):
        page = MagicMock()
        locator = MagicMock(); locator.count.return_value = 1
        page.get_by_role.return_value = locator
        resolver = LocatorResolver(page)
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "step.json")
            with open(path, "w") as f:
                json.dump({"candidates": [self._candidate()]}, f)
            result = resolver.resolve_from_file(path, "click")
        assert result.locator is locator

    def test_resolve_strips_page_prefix(self):
        page = MagicMock()
        locator = MagicMock(); locator.count.return_value = 1
        page.locator.return_value = locator
        resolver = LocatorResolver(page)
        cand = {"strategy": "css", "selector": 'page.locator("#foo")', "score": 0.5}
        resolver.resolve("c", [cand])
        page.locator.assert_called_once_with("#foo")


class TestStepHelpers:
    def test_click_dispatches_to_resolver(self):
        page = MagicMock()
        loc = MagicMock(); loc.count.return_value = 1
        page.get_by_role.return_value = loc
        step.click(page, intent="click X", candidates=[
            {"strategy": "role", "playwright_call": 'get_by_role("button", name="X")',
             "selector": 'page.get_by_role("button", name="X")', "score": 0.9}
        ])
        loc.click.assert_called_once()

    def test_fill_presses_tab_for_blur(self):
        page = MagicMock()
        loc = MagicMock(); loc.count.return_value = 1
        loc_first = MagicMock()
        loc.first = loc_first
        page.get_by_label.return_value = loc
        step.fill(page, intent="fill Email", value="x@y.com", candidates=[
            {"strategy": "label", "playwright_call": 'get_by_label("Email")',
             "selector": 'page.get_by_label("Email")', "score": 0.85}
        ])
        loc.fill.assert_called_once_with("x@y.com", timeout=5000)
        loc_first.press.assert_called_once_with("Tab")

    def test_select_calls_select_option(self):
        page = MagicMock()
        loc = MagicMock(); loc.count.return_value = 1
        page.get_by_label.return_value = loc
        step.select(page, intent="select Estado", value="SP", candidates=[
            {"strategy": "label", "playwright_call": 'get_by_label("Estado")',
             "selector": 'page.get_by_label("Estado")', "score": 0.85}
        ])
        loc.select_option.assert_called_once_with("SP", timeout=5000)

    def test_assert_text_raises_on_mismatch(self):
        page = MagicMock()
        loc = MagicMock(); loc.count.return_value = 1
        loc.first.text_content.return_value = "Hello"
        page.get_by_role.return_value = loc
        with pytest.raises(AssertionError):
            step.assert_text(page, intent="x", expected="Bye", candidates=[
                {"strategy": "role", "playwright_call": 'get_by_role("heading")',
                 "selector": 'page.get_by_role("heading")', "score": 0.9}
            ])

    def test_assert_text_passes_when_substring(self):
        page = MagicMock()
        loc = MagicMock(); loc.count.return_value = 1
        loc.first.text_content.return_value = "Welcome, Alice"
        page.get_by_role.return_value = loc
        step.assert_text(page, intent="x", expected="welcome", candidates=[
            {"strategy": "role", "playwright_call": 'get_by_role("heading")',
             "selector": 'page.get_by_role("heading")', "score": 0.9}
        ])


class TestCompileV2:
    def _make_tc(self) -> SemanticTestCase:
        tc = SemanticTestCase(
            test_id="ST-LOGIN", source_recording_id="REC-001",
            application="bank", base_url="http://localhost:8765",
        )
        target = SemanticTarget(
            role="textbox", accessible_name="Email", tag="input",
            label="Email", intent_text='fill textbox "Email"',
            candidates=[LocatorCandidate(
                strategy="playwright_native",
                selector='page.get_by_label("Email")',
                score=0.85, reason="native",
                playwright_call='get_by_label("Email")',
                intent_text='fill textbox "Email"',
            )],
        )
        fill_action = SemanticAction(action="fill", target=target, value="alice@x.com")

        btn_target = SemanticTarget(
            role="button", accessible_name="Login", tag="button",
            intent_text='click button "Login"',
            candidates=[LocatorCandidate(
                strategy="playwright_native",
                selector='page.get_by_role("button", name="Login")',
                score=0.95, reason="native",
                playwright_call='get_by_role("button", name="Login")',
                intent_text='click button "Login"',
            )],
        )
        click_action = SemanticAction(action="click", target=btn_target)
        tc.steps = [fill_action, click_action]
        return tc

    def test_writes_script_and_candidates(self):
        tc = self._make_tc()
        with tempfile.TemporaryDirectory() as d:
            path = PlaywrightCompiler().compile_v2(tc, d)
            assert os.path.exists(path)
            content = open(path).read()
            assert "from testforge.runtime import step" in content
            assert "step.fill(page, intent=" in content
            assert "step.click(page, intent=" in content
            assert 'BASE_URL = "http://localhost:8765"' in content
            candidates_dir = os.path.join(d, "candidates")
            assert os.path.isdir(candidates_dir)
            files = sorted(os.listdir(candidates_dir))
            assert files == ["step_001.json", "step_002.json"]
            step1 = json.load(open(os.path.join(candidates_dir, "step_001.json")))
            assert step1["action"] == "fill"
            assert step1["intent_text"] == 'fill textbox "Email"'
            assert step1["value"] == "alice@x.com"
            assert step1["candidates"][0]["playwright_call"] == 'get_by_label("Email")'

    def test_skips_navigation_and_skipped_steps(self):
        tc = self._make_tc()
        tc.steps.insert(0, SemanticAction(action="navigation"))
        tc.steps.append(SemanticAction(action="click", target=SemanticTarget(),
                                        skip_reason="dedup"))
        with tempfile.TemporaryDirectory() as d:
            path = PlaywrightCompiler().compile_v2(tc, d)
            content = open(path).read()
            # Apenas 2 chamadas step.*; navegacao e pulados excluidos
            assert content.count("step.fill") + content.count("step.click") == 2

    def test_emits_select_for_select_tag(self):
        tc = SemanticTestCase(test_id="ST-S", source_recording_id="R",
                              application="x", base_url="about:blank")
        target = SemanticTarget(
            role="combobox", label="Estado", tag="select",
            intent_text='select combobox "Estado"',
            candidates=[LocatorCandidate(
                strategy="playwright_native",
                selector='page.get_by_label("Estado")',
                score=0.85, reason="native",
                playwright_call='get_by_label("Estado")',
                intent_text='select combobox "Estado"',
            )],
        )
        tc.steps = [SemanticAction(action="fill", target=target, value="SP")]
        with tempfile.TemporaryDirectory() as d:
            path = PlaywrightCompiler().compile_v2(tc, d)
            content = open(path).read()
            assert "step.select(page, intent=" in content
            assert "value=\"SP\"" in content
