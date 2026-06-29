"""H9 — desbloqueio QA piloto: erros de certificado HTTPS ignorados por padrao.

3 de 11 gravacoes de producao falharam no passo 1 com ERR_CERT_AUTHORITY_INVALID em
*.apps.nprd.caixa. O padrao deve pular verificacao de certificado; --verify-ssl e opt-in.

Fixacoes:
- `_make_context_kwargs(verify_ssl=False)` define `ignore_https_errors=True`.
- `launch_browser(verify_ssl=False)` adiciona arg `--ignore-certificate-errors`.
- `IncrementalRunner` padrao `verify_ssl=False`.
"""
from __future__ import annotations

from unittest.mock import MagicMock

from testforge.browser import launch_browser
from testforge.cli.app import _make_context_kwargs
from testforge.runner.incremental_runner import IncrementalRunner


class TestContextKwargsHttpsDefault:
    def test_default_verify_ssl_false_yields_ignore_https_errors(self):
        kw = _make_context_kwargs(headless=True, verify_ssl=False)
        assert kw.get("ignore_https_errors") is True

    def test_verify_ssl_true_omits_ignore_https_errors(self):
        kw = _make_context_kwargs(headless=True, verify_ssl=True)
        assert "ignore_https_errors" not in kw

    def test_headless_viewport_preserved(self):
        kw = _make_context_kwargs(headless=True, verify_ssl=False)
        assert kw["viewport"] == {"width": 1280, "height": 720}
        assert kw["ignore_https_errors"] is True

    def test_headed_no_viewport_preserved(self):
        kw = _make_context_kwargs(headless=False, verify_ssl=False)
        assert kw.get("no_viewport") is True
        assert kw["ignore_https_errors"] is True


class TestLaunchBrowserHttpsArgs:
    def test_verify_ssl_false_adds_ignore_certificate_errors_arg(self):
        pw = MagicMock()
        pw.chromium.launch.return_value = MagicMock()
        launch_browser(pw, "chromium", headless=True, verify_ssl=False)
        kwargs = pw.chromium.launch.call_args.kwargs
        assert "--ignore-certificate-errors" in kwargs.get("args", [])

    def test_verify_ssl_true_omits_ignore_certificate_errors_arg(self):
        pw = MagicMock()
        pw.chromium.launch.return_value = MagicMock()
        launch_browser(pw, "chromium", headless=True, verify_ssl=True)
        call = pw.chromium.launch.call_args
        # No caminho verify_ssl=True em nao-Windows passa apenas {"headless": ...}
        assert "--ignore-certificate-errors" not in call.kwargs.get("args", [])


class TestIncrementalRunnerDefault:
    def test_constructor_default_verify_ssl_is_false(self):
        runner = IncrementalRunner(script_path="/tmp/nonexistent.py")
        assert runner.verify_ssl is False
