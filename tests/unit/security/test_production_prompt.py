"""Production domain prompt before recording (BUG-REC-59/86)."""
import io
import sys
from unittest.mock import patch

import pytest


@pytest.mark.unit
class TestProductionPrompt:
    def test_when_des_url_then_prompt_returns_true_without_asking(self):
        # Arrange
        from testforge.cli.app import _prompt_production_domain

        # Act
        result = _prompt_production_domain(
            "https://sifap-frontend-internet-v2-des.apps.nprd.caixa/",
            no_interactive=False,
        )

        # Assert
        assert result is True  # DES URL — no prompt

    def test_when_tqs_url_then_prompt_returns_true(self):
        from testforge.cli.app import _prompt_production_domain
        assert _prompt_production_domain(
            "https://sifap-front-v2-tqs.apps.nprd.caixa/", no_interactive=False
        ) is True

    def test_when_production_url_and_no_interactive_then_warns_but_proceeds(self, capsys):
        # Arrange
        from testforge.cli.app import _prompt_production_domain

        # Act
        result = _prompt_production_domain(
            "https://simuladorhabitacao.caixa.gov.br/home",
            no_interactive=True,
        )

        # Assert
        assert result is True  # non-interactive proceeds with warning
        captured = capsys.readouterr()
        assert "PRODUCAO DETECTADA" in captured.err
        assert "simuladorhabitacao.caixa.gov.br" in captured.err

    def test_when_production_url_and_user_declines_then_returns_false(self, capsys, monkeypatch):
        # Arrange
        from testforge.cli.app import _prompt_production_domain

        monkeypatch.setattr("sys.stdin", io.StringIO("n\n"))
        monkeypatch.setattr("sys.stdin.isatty", lambda: True)

        # Act
        result = _prompt_production_domain(
            "https://simuladorhabitacao.caixa.gov.br/home",
            no_interactive=False,
        )

        # Assert
        assert result is False
        captured = capsys.readouterr()
        assert "Gravacao cancelada" in captured.err

    def test_when_production_url_and_user_confirms_yes_then_returns_true(self, capsys, monkeypatch):
        from testforge.cli.app import _prompt_production_domain
        monkeypatch.setattr("sys.stdin", io.StringIO("y\n"))
        monkeypatch.setattr("sys.stdin.isatty", lambda: True)

        result = _prompt_production_domain(
            "https://simuladorhabitacao.caixa.gov.br/home",
            no_interactive=False,
        )
        assert result is True

    def test_when_empty_url_then_returns_true_no_check(self):
        from testforge.cli.app import _prompt_production_domain
        assert _prompt_production_domain("", no_interactive=False) is True
        assert _prompt_production_domain(None, no_interactive=False) is True
