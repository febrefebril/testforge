"""Sprint 0 — Testes do publisher Azure DevOps + cadeia de credenciais Z1+Z5."""
from __future__ import annotations

import json
import os
import stat
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from testforge.publisher.azure_devops import (
    AzureDevOpsCreds,
    AzureDevOpsPublisher,
    install_pat,
    resolve_credentials,
)


class TestInstallPat:
    def test_writes_secrets_with_0600(self, tmp_path):
        path = tmp_path / "secrets"
        install_pat(pat="abc123", org="o", project="p", repo="r", path=path)
        assert path.exists()
        data = json.loads(path.read_text())
        assert data["azure_devops"]["pat"] == "abc123"
        assert data["azure_devops"]["org"] == "o"
        mode = stat.S_IMODE(path.stat().st_mode)
        assert mode == 0o600

    def test_creates_parent_dir(self, tmp_path):
        path = tmp_path / "sub" / "secrets"
        install_pat(pat="x", org="o", project="p", repo="r", path=path)
        assert path.exists()


class TestResolveChainEnv:
    def test_env_wins_when_all_args_supplied(self, monkeypatch, tmp_path):
        monkeypatch.setenv("AZURE_DEVOPS_PAT", "from-env")
        creds = resolve_credentials(org="o", project="p", repo="r",
                                      secrets_path=tmp_path / "missing")
        assert creds.source == "env"
        assert creds.pat == "from-env"


class TestResolveChainSecretsFile:
    def test_secrets_file_used_when_env_missing(self, monkeypatch, tmp_path):
        monkeypatch.delenv("AZURE_DEVOPS_PAT", raising=False)
        sec = tmp_path / "secrets"
        install_pat(pat="from-file", org="o1", project="p1", repo="r1", path=sec)
        creds = resolve_credentials(org="", project="", repo="",
                                      secrets_path=sec)
        assert creds.source == "secrets_file"
        assert creds.pat == "from-file"
        assert creds.org == "o1"

    def test_secrets_file_malformed_falls_through(self, monkeypatch, tmp_path):
        monkeypatch.delenv("AZURE_DEVOPS_PAT", raising=False)
        sec = tmp_path / "secrets"
        sec.write_text("{ not json")
        creds = resolve_credentials(org="", project="", repo="",
                                      secrets_path=sec)
        assert creds is None  # nada mais disponivel


class TestResolveChainNothing:
    def test_returns_none_when_no_source(self, monkeypatch, tmp_path):
        monkeypatch.delenv("AZURE_DEVOPS_PAT", raising=False)
        # credenciais azure + git helper ausentes no ambiente de teste
        creds = resolve_credentials(org="", project="", repo="",
                                      secrets_path=tmp_path / "missing")
        assert creds is None


class TestRemoteUrls:
    def test_https_with_pat_embeds_token(self):
        pub = AzureDevOpsPublisher(org="myorg", project="QA", repo="diag")
        url = pub.remote_https(pat="SECRET")
        assert "SECRET" in url
        assert "dev.azure.com/myorg/QA/_git/diag" in url

    def test_https_no_pat_omits_creds(self):
        pub = AzureDevOpsPublisher(org="o", project="p", repo="r")
        url = pub.remote_https()
        assert "anything:" not in url

    def test_ssh_format(self):
        pub = AzureDevOpsPublisher(org="o", project="p", repo="r")
        assert pub.remote_ssh() == "git@ssh.dev.azure.com:v3/o/p/r"


class TestPublishFlow:
    @patch("testforge.publisher.azure_devops.subprocess.run")
    def test_publish_returns_failure_when_no_creds(self, mock_run, tmp_path, monkeypatch):
        monkeypatch.delenv("AZURE_DEVOPS_PAT", raising=False)
        diag = tmp_path / "diag"
        diag.mkdir()
        (diag / "session.json").write_text("{}")
        pub = AzureDevOpsPublisher(org="o", project="p", repo="r",
                                      secrets_path=tmp_path / "missing")
        result = pub.publish("rec_1", str(diag))
        assert result["success"] is False
        assert "PAT" in result["error"]

    @patch("testforge.publisher.azure_devops.subprocess.run")
    def test_publish_returns_failure_when_diag_dir_missing(self, mock_run, tmp_path):
        pub = AzureDevOpsPublisher(org="o", project="p", repo="r")
        result = pub.publish("rec_1", str(tmp_path / "nope"))
        assert result["success"] is False
        assert "not found" in result["error"]

    @patch("testforge.publisher.azure_devops.subprocess.run")
    def test_publish_success_path(self, mock_run, monkeypatch, tmp_path):
        # Fornece PAT via env
        monkeypatch.setenv("AZURE_DEVOPS_PAT", "tok")
        # subprocess.run retorna OK para toda chamada; rev-parse final retorna SHA
        def _run(args, **kw):
            if "rev-parse" in args:
                return subprocess.CompletedProcess(args=args, returncode=0,
                                                      stdout="abc123def\n", stderr="")
            return subprocess.CompletedProcess(args=args, returncode=0,
                                                  stdout="", stderr="")
        mock_run.side_effect = _run
        diag = tmp_path / "diag"
        diag.mkdir()
        (diag / "session.json").write_text('{"x":1}')
        (diag / "steps.jsonl").write_text('{"a":1}\n')
        pub = AzureDevOpsPublisher(org="o", project="p", repo="r",
                                      secrets_path=tmp_path / "missing")
        result = pub.publish("rec_1", str(diag))
        assert result["success"] is True
        assert result["remote_path"] == "diagnostic/rec_1"
        assert result["commit_sha"].startswith("abc")
        assert set(result["artifacts_copied"]) == {"session.json", "steps.jsonl"}
        assert result["credential_source"] == "env"
