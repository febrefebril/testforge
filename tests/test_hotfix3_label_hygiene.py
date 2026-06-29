"""Hotfix 3 — limpeza de icones Material + pular linhas Gherkin com rotulo vazio."""
from __future__ import annotations

import os
import tempfile

import pytest

from testforge.diagnostic.gherkin_writer import (
    GherkinWriter,
    _clean_material_icons,
    _safe_label,
)


class TestMaterialIconStrip:
    @pytest.mark.parametrize("input,expected", [
        ("table_view Calculadora poder de compra",
         "Calculadora poder de compra"),
        ("attach_money Pela prestação", "Pela prestação"),
        ("home Valor do imóvel", "Valor do imóvel"),
        ("check_circle Imóvel quitado", "Imóvel quitado"),
        ("arrow_back Página Inicial", "Página Inicial"),
        # Multiplos icones no inicio
        ("home arrow_back Voltar", "Voltar"),
        # Icone no final
        ("Confirmar arrow_forward", "Confirmar"),
        # Sem icone, inalterado
        ("Calcular agora", "Calcular agora"),
        # Rotulos apenas com icone: manter ultimo token (regra de unico token)
        # para que usuarios vejam *algo* — estes casos sao raros e nao valem
        # a pena reduzir a nada.
        ("home arrow_back", "arrow_back"),
        # Entrada vazia
        ("", ""),
        # Colapso de espacos em branco
        ("table_view   Calculadora", "Calculadora"),
    ])
    def test_clean(self, input, expected):
        assert _clean_material_icons(input) == expected


class TestSafeLabel:
    def test_strips_icon_from_accessible_name(self):
        target = {"accessible_name": "table_view Calculadora poder de compra"}
        assert _safe_label(target) == "Calculadora poder de compra"

    def test_single_word_label_kept_even_if_icon_name(self):
        # Regra conservadora: rotulo de unico token nunca e removido.
        target = {"accessible_name": "home"}
        assert _safe_label(target) == "home"

    def test_empty_fallback_when_nothing_meaningful(self):
        assert _safe_label({}) == ""
        assert _safe_label({"text": "  "}) == ""

    def test_custom_fallback(self):
        assert _safe_label({}, fallback="custom") == "custom"


class TestGherkinSkipsEmptyLabel:
    def test_click_with_no_label_skipped(self):
        with tempfile.TemporaryDirectory() as d:
            w = GherkinWriter(d)
            line = w.on_step("click", target={})
            assert line is None
            assert w.steps == []

    def test_click_with_single_word_label_kept(self):
        # Rotulos de unico token sao conservadores: nunca removidos, mesmo
        # quando a palavra e um icone Material. Melhor exibir "home" do
        # que pular silenciosamente.
        with tempfile.TemporaryDirectory() as d:
            w = GherkinWriter(d)
            line = w.on_step("click", target={"accessible_name": "home"})
            assert line is not None
            assert 'home' in line

    def test_fill_with_no_label_skipped(self):
        with tempfile.TemporaryDirectory() as d:
            w = GherkinWriter(d)
            assert w.on_step("fill", target={}, value="x") is None

    def test_assert_with_no_text_skipped(self):
        with tempfile.TemporaryDirectory() as d:
            w = GherkinWriter(d)
            assert w.on_step("assert", target={}, value="") is None

    def test_keyword_progress_only_on_emitted(self):
        with tempfile.TemporaryDirectory() as d:
            w = GherkinWriter(d)
            # Primeiro clique sem rotulo -> pulado, nenhum Quando emitido
            assert w.on_step("click", target={}) is None
            # Clique real -> deve emitir Quando, nao E
            real = w.on_step("click", target={"accessible_name": "Login"})
            assert real.startswith("  Quando")


class TestEndToEndCleanFeature:
    def test_feature_omits_icon_and_empty_lines(self):
        with tempfile.TemporaryDirectory() as d:
            w = GherkinWriter(d)
            w.on_navigation("http://app/", title="Simulador")
            w.on_step("click", target={"accessible_name": "table_view Calculadora poder de compra"})
            w.on_step("click", target={})  # pulado
            w.on_step("fill", target={"label": "Renda mensal"}, value="R$ 5.000,00")
            w.on_step("click", target={"accessible_name": "arrow_back Voltar"})
            path = w.write()
            content = open(path).read()
            assert "table_view" not in content
            assert "arrow_back" not in content
            assert "elemento" not in content
            assert 'Calculadora poder de compra' in content
            assert 'Voltar' in content
