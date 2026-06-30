"""TestForge — UX Sprint (2026-06-30): wizard QA + defaults internos.

Antes: usuario precisava lembrar 6+ flags a cada gravacao
  testforge record --name X --app SIOPI --complete --pipeline-and-diagnostic-mode \\
    --suite Y --test-case Z https://app/

Agora: comando minimo + wizard interativo so para info de QA
  testforge record https://app/
    > Nome do teste [REC-2026...]:
    > Sistema/aplicacao [SIOPI]:
    > Suite [...]:
    > Caso de teste [...]:

Defaults internos automaticamente ON:
- --complete
- --pipeline-and-diagnostic-mode

Flags de opt-out adicionadas: --no-wizard, --no-complete,
--no-pipeline-and-diagnostic-mode. Para CI / batch use --no-wizard.
"""
from __future__ import annotations
import argparse
import io
import sys
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from testforge.cli.app import _record_qa_wizard


def _make_args(**kw):
    defaults = dict(
        url="https://app/",
        name=None,
        app=None,
        system=None,
        suite=None,
        test_case=None,
        no_wizard=False,
        complete=False,
        no_complete=False,
        pipeline_and_diagnostic_mode=False,
        no_pipeline_and_diagnostic_mode=False,
        diagnostic_mode=False,
    )
    defaults.update(kw)
    return SimpleNamespace(**defaults)


class TestWizardSkipsWhenNotTTY:
    def test_wizard_returns_unchanged_when_stdin_not_tty(self):
        args = _make_args()
        with patch("sys.stdin.isatty", return_value=False):
            out = _record_qa_wizard(args)
        assert out.name is None
        assert out.system is None
        assert out.suite is None

    def test_wizard_returns_unchanged_when_no_wizard_flag(self):
        args = _make_args(no_wizard=True)
        with patch("sys.stdin.isatty", return_value=True):
            out = _record_qa_wizard(args)
        assert out.name is None


class TestWizardPromptsOnlyMissingFields:
    def _patch_tty_and_input(self, responses):
        """Returns context managers: stdin.isatty=True, input() returns each
        response in order."""
        responses_iter = iter(responses)
        return patch.multiple(
            "sys.stdin",
            isatty=lambda: True,
        ), patch("builtins.input", lambda _: next(responses_iter))

    def test_prompts_for_all_missing_when_all_absent(self):
        args = _make_args()
        with patch("sys.stdin.isatty", return_value=True), \
             patch("builtins.input", side_effect=[
                 "MeuTeste", "SIOPI", "regressao", "fluxo-pdc",
             ]):
            out = _record_qa_wizard(args)
        assert out.name == "MeuTeste"
        assert out.system == "SIOPI"
        assert out.suite == "regressao"
        assert out.test_case == "fluxo-pdc"

    def test_name_already_set_not_prompted(self):
        args = _make_args(name="X")
        with patch("sys.stdin.isatty", return_value=True), \
             patch("builtins.input", side_effect=["", "", ""]):
            out = _record_qa_wizard(args)
        assert out.name == "X"  # nao mudou

    def test_app_already_set_does_not_prompt_system(self):
        args = _make_args(app="ALR")
        with patch("sys.stdin.isatty", return_value=True), \
             patch("builtins.input", side_effect=["TestName", "", ""]):
            out = _record_qa_wizard(args)
        # System nao foi prompted porque app ja estava setado
        assert out.app == "ALR"

    def test_empty_response_uses_default(self):
        """Pressionar Enter aceita o default mostrado entre colchetes."""
        args = _make_args()
        with patch("sys.stdin.isatty", return_value=True), \
             patch("builtins.input", side_effect=["", "SIOPI", "", ""]):
            out = _record_qa_wizard(args)
        # name="" → fica com default REC-... gerado pelo wizard (nao vazio)
        assert out.name and out.name.startswith("REC-")

    def test_keyboard_interrupt_keeps_default(self):
        """Ctrl+C durante prompt nao deve crashar — usa default em curso."""
        args = _make_args()
        # input raise KeyboardInterrupt
        with patch("sys.stdin.isatty", return_value=True), \
             patch("builtins.input", side_effect=KeyboardInterrupt):
            out = _record_qa_wizard(args)
        # Nao crashou; valores ficam None (defaults nao aplicados em ctrl+c)
        assert out is args


class TestOptOutFlagsRegistered:
    def test_no_wizard_flag_in_cli_help(self):
        from pathlib import Path
        src = (Path(__file__).parent.parent
               / "src" / "testforge" / "cli" / "app.py").read_text(encoding="utf-8")
        # Flag de opt-out do wizard precisa estar registrada
        assert 'dest="no_wizard"' in src or "dest='no_wizard'" in src

    def test_no_complete_flag_exists_in_cli_help(self):
        from pathlib import Path
        src = (Path(__file__).parent.parent
               / "src" / "testforge" / "cli" / "app.py").read_text(encoding="utf-8")
        assert '--no-complete' in src
        assert '--no-wizard' in src
        assert '--no-pipeline-and-diagnostic-mode' in src
