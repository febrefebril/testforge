"""Sprint 0 — GherkinWriter unit tests."""
from __future__ import annotations

import os
import tempfile

import pytest

from testforge.diagnostic.gherkin_writer import GherkinWriter


class TestSequencing:
    def test_first_interactive_is_quando(self):
        with tempfile.TemporaryDirectory() as d:
            w = GherkinWriter(d)
            line = w.on_step("click", target={"accessible_name": "Logar"})
            assert line.startswith("  Quando clico no botão")

    def test_subsequent_interactive_is_E(self):
        with tempfile.TemporaryDirectory() as d:
            w = GherkinWriter(d)
            w.on_step("click", target={"accessible_name": "Logar"})
            line2 = w.on_step("fill", target={"label": "Email"}, value="u@x.com")
            assert line2.startswith("  E preencho")

    def test_first_assert_is_entao(self):
        with tempfile.TemporaryDirectory() as d:
            w = GherkinWriter(d)
            w.on_step("click", target={"accessible_name": "Logar"})
            a = w.on_step("assert", target={"text": "Bem-vindo"})
            assert a.startswith("  Então vejo o texto")

    def test_second_assert_is_E(self):
        with tempfile.TemporaryDirectory() as d:
            w = GherkinWriter(d)
            w.on_step("click", target={"accessible_name": "Logar"})
            w.on_step("assert", target={"text": "Bem-vindo"})
            a2 = w.on_step("assert", target={"text": "Painel"})
            assert a2.startswith("  E vejo o texto")


class TestValueKindOpaque:
    def test_currency_phrase(self):
        with tempfile.TemporaryDirectory() as d:
            w = GherkinWriter(d)
            line = w.on_step("fill", target={"label": "Renda mensal *"},
                              value="R$ 5.000,00")
            assert line == '  Quando preencho "Renda mensal *" com valor monetário'
            assert "5.000" not in line  # value never leaks

    def test_date_phrase(self):
        with tempfile.TemporaryDirectory() as d:
            w = GherkinWriter(d)
            line = w.on_step("fill", target={"label": "Nascimento"},
                              value="12/12/1970")
            assert "com data" in line

    def test_cpf_phrase(self):
        with tempfile.TemporaryDirectory() as d:
            w = GherkinWriter(d)
            line = w.on_step("fill", target={"label": "CPF"},
                              value="12345678900")
            assert "com CPF" in line

    def test_email_phrase(self):
        with tempfile.TemporaryDirectory() as d:
            w = GherkinWriter(d)
            line = w.on_step("fill", target={"label": "Email"},
                              value="a@b.com")
            assert "com email" in line

    def test_missing_value_no_suffix(self):
        with tempfile.TemporaryDirectory() as d:
            w = GherkinWriter(d)
            line = w.on_step("fill", target={"label": "X"})
            assert line == '  Quando preencho "X"'


class TestLabelFallback:
    def test_uses_accessible_name_first(self):
        with tempfile.TemporaryDirectory() as d:
            w = GherkinWriter(d)
            line = w.on_step("click", target={
                "accessible_name": "Salvar",
                "label": "Submit form",
                "text": "Pressione aqui",
            })
            assert '"Salvar"' in line

    def test_falls_back_to_label(self):
        with tempfile.TemporaryDirectory() as d:
            w = GherkinWriter(d)
            line = w.on_step("click", target={"label": "Submit"})
            assert '"Submit"' in line

    def test_escapes_quotes_in_label(self):
        with tempfile.TemporaryDirectory() as d:
            w = GherkinWriter(d)
            line = w.on_step("click", target={"accessible_name": 'Click "now"'})
            assert "Click 'now'" in line


class TestNavigationAndFuncionalidade:
    def test_first_navigation_seeds_funcionalidade(self):
        with tempfile.TemporaryDirectory() as d:
            w = GherkinWriter(d)
            w.on_navigation("http://x/", title="App Inicial")
            assert w.auto_funcionalidade() == "App Inicial"

    def test_dado_lines_dedup(self):
        with tempfile.TemporaryDirectory() as d:
            w = GherkinWriter(d)
            w.on_navigation("http://x/", title="A")
            w.on_navigation("http://x/", title="A")  # same URL
            path = w.write()
            content = open(path).read()
            assert content.count("Dado que acesso") == 1

    def test_falls_back_to_url_when_no_title(self):
        with tempfile.TemporaryDirectory() as d:
            w = GherkinWriter(d)
            w.on_navigation("http://x/login")
            assert w.auto_funcionalidade() == "http://x/login"


class TestAutoCenario:
    def test_uses_first_click_label(self):
        with tempfile.TemporaryDirectory() as d:
            w = GherkinWriter(d)
            w.on_step("click", target={"accessible_name": "Calcular"})
            w.on_step("fill", target={"label": "X"})
            assert w.auto_cenario_from_sequence() == "Fluxo iniciado por 'Calcular'"

    def test_falls_back_to_funcionalidade(self):
        with tempfile.TemporaryDirectory() as d:
            w = GherkinWriter(d)
            w.on_navigation("http://x/", title="App")
            assert "App" in w.auto_cenario_from_sequence()

    def test_default_when_nothing_known(self):
        with tempfile.TemporaryDirectory() as d:
            w = GherkinWriter(d)
            assert w.auto_cenario_from_sequence() == "Cenário gravado"


class TestWriteOutput:
    def test_writes_complete_feature(self):
        with tempfile.TemporaryDirectory() as d:
            w = GherkinWriter(d)
            w.on_navigation("http://x/", title="Simulador")
            w.on_step("click", target={"accessible_name": "Calcular"})
            w.on_step("fill", target={"label": "Renda"}, value="R$ 5.000,00")
            w.on_step("assert", target={"text": "Parcela estimada"})
            path = w.write()
            assert os.path.exists(path)
            content = open(path).read()
            assert content.startswith("# language: pt\n")
            assert "Funcionalidade: Simulador" in content
            assert "Cenário: Fluxo iniciado por 'Calcular'" in content
            assert "Dado que acesso \"http://x/\"" in content
            assert "Quando clico no botão \"Calcular\"" in content
            assert "E preencho \"Renda\" com valor monetário" in content
            assert "Então vejo o texto \"Parcela estimada\"" in content

    def test_override_funcionalidade_and_cenario(self):
        with tempfile.TemporaryDirectory() as d:
            w = GherkinWriter(d)
            w.on_navigation("http://x/", title="Auto")
            w.on_step("click", target={"accessible_name": "Y"})
            path = w.write(
                funcionalidade_override="Login do usuário",
                cenario_override="Login com sucesso",
            )
            content = open(path).read()
            assert "Funcionalidade: Login do usuário" in content
            assert "Cenário: Login com sucesso" in content
