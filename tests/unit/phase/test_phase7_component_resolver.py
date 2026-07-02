"""Fase 7 — ComponentResolver orientado a YAML.

Verifica paridade com o registro legado `handlers.detect_handler()`
e que adicionar/trocar padroes e puramente declarativo.
"""
from __future__ import annotations

import os
import tempfile
from unittest.mock import MagicMock

import pytest

from testforge.handlers import detect_handler as legacy_detect_handler
from testforge.handlers.component_resolver import (
    ComponentPattern,
    ComponentResolver,
)
from testforge.semantic.model import (
    LocatorCandidate,
    SemanticAction,
    SemanticTarget,
)


def _step(tag: str = "", element_id: str = "", selectors: list[str] | None = None):
    selectors = selectors or []
    target = SemanticTarget(
        tag=tag, element_id=element_id,
        candidates=[LocatorCandidate(strategy="x", selector=s, score=0.5)
                    for s in selectors],
    )
    return SemanticAction(action="click", target=target)


class TestPatternMatching:
    def test_tag_in(self):
        p = ComponentPattern(
            name="t", handler_class="testforge.handlers.angular_material:AngularMaterialHandler",
            detect={"tag_in": ["mat-select"]},
        )
        assert p.matches([], "", "mat-select") is True
        assert p.matches([], "", "input") is False

    def test_element_id_starts_with(self):
        p = ComponentPattern(
            name="t", handler_class="x:Y",
            detect={"element_id_starts_with": ["mat-select-"]},
        )
        assert p.matches([], "mat-select-42", "input") is True
        assert p.matches([], "mat-select-", "input") is True
        assert p.matches([], "foo", "input") is False

    def test_selector_contains_any(self):
        p = ComponentPattern(
            name="t", handler_class="x:Y",
            detect={"selector_contains_any": ["mat-select"]},
        )
        assert p.matches(["div.mat-select-trigger"], "", "div") is True
        assert p.matches(["#foo"], "", "div") is False

    def test_selector_contains_any_lower(self):
        p = ComponentPattern(
            name="t", handler_class="x:Y",
            detect={"selector_contains_any_lower": ["primefaces"]},
        )
        assert p.matches(["DIV.PrimeFaces-Widget"], "", "div") is True

    def test_selector_skip_filter_per_candidate(self):
        p = ComponentPattern(
            name="t", handler_class="x:Y",
            detect={
                "selector_skip_if_contains": ["mat-radio"],
                "selector_contains_any": ["mat-select"],
            },
        )
        # Seletor mat-radio e filtrado, restando nada para corresponder.
        assert p.matches(["mat-radio-button:has-text('Yes')"], "", "input") is False
        # Quando um seletor mat-select nao-radio tambem esta presente, ainda corresponde.
        assert p.matches([
            "mat-radio-button:has-text('Yes')",
            "div.mat-select-trigger",
        ], "", "input") is True


class TestResolverLoading:
    def test_loads_default_yaml(self):
        r = ComponentResolver()
        assert "angular-material" in r.pattern_names
        assert "primefaces" in r.pattern_names
        assert "react-mui" in r.pattern_names

    def test_missing_yaml_returns_empty(self):
        with tempfile.TemporaryDirectory() as d:
            r = ComponentResolver(yaml_path=os.path.join(d, "missing.yaml"))
            assert r.pattern_names == []
            assert r.find_handler(_step(tag="mat-select")) is None

    def test_custom_yaml(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "custom.yaml")
            with open(path, "w") as f:
                f.write("""
patterns:
  - name: only-foo
    handler_class: testforge.handlers.primeFaces:PrimeFacesHandler
    detect:
      selector_contains_any: ["only-foo"]
""")
            r = ComponentResolver(yaml_path=path)
            assert r.pattern_names == ["only-foo"]


class TestParityWithLegacy:
    """For inputs that the legacy registry recognizes, ComponentResolver
    must return a handler of the same component_type."""

    def _assert_parity(self, step):
        legacy = legacy_detect_handler(step)
        ours = ComponentResolver().find_handler(step)
        if legacy is None:
            assert ours is None, f"new resolver fired where legacy did not for {step}"
        else:
            assert ours is not None, f"new resolver missed where legacy claimed {step}"
            assert ours.component_type == legacy.component_type

    def test_mat_select_tag(self):
        self._assert_parity(_step(tag="mat-select"))

    def test_mat_option_id(self):
        self._assert_parity(_step(element_id="mat-option-42"))

    def test_mat_dialog_selector(self):
        self._assert_parity(_step(selectors=['div.mat-dialog-container button']))

    def test_mat_tab_role(self):
        self._assert_parity(_step(selectors=['[role="tab"][aria-selected="false"]']))

    def test_mat_radio_falls_through(self):
        # Legacy explicitly skips mat-radio; ours must too.
        self._assert_parity(_step(selectors=['mat-radio-button:has-text("Yes")']))

    def test_primefaces_dropdown(self):
        self._assert_parity(_step(selectors=['div.ui-selectonemenu-trigger']))

    def test_primefaces_j_idt_id(self):
        self._assert_parity(_step(element_id="form:j_idt142"))

    def test_react_mui_select(self):
        self._assert_parity(_step(selectors=['div.MuiSelect-root']))

    def test_react_mui_popper(self):
        self._assert_parity(_step(selectors=['div[data-popper-placement="bottom"]']))

    def test_plain_input_unmatched(self):
        self._assert_parity(_step(tag="input", element_id="user-email"))

    def test_button_unmatched(self):
        self._assert_parity(_step(tag="button", selectors=['button.btn-primary']))


class TestPrecedence:
    def test_angular_material_wins_over_primefaces(self):
        # Seletores com 'mat-' e 'ui-' devem resolver para angular-material
        # porque o YAML o lista primeiro.
        r = ComponentResolver()
        s = _step(tag="mat-select", selectors=['ui-selectonemenu mat-select'])
        h = r.find_handler(s)
        assert h is not None
        assert h.component_type == "angular-material"
