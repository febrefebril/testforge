"""Sprint 0 commit 6 — Publicador Azure DevOps (G4) + cadeia de credenciais Z1+Z5.

Envia artefatos de diagnostico para um repositorio Git privado do Azure DevOps
sem que o testador veja um PAT. A cadeia de coleta (Z5) le
credenciais nesta ordem:

    1. env  AZURE_DEVOPS_PAT
    2. arquivo ~/.testforge/secrets             (chmod 600, escrito por Z1)
    3. arquivo ~/.azure/credentials              (helper legado az CLI)
    4. git credential helper                  (`git credential fill`)

Faz fallback para SSH push se `prefer_ssh: true` ou nenhum PAT for resolvido.

O caminho admin Z1 e enviado como comando CLI `testforge admin install-pat`
(conectado em cli/app.py) — executa uma vez por maquina, apos o qual o
testador apenas executa `testforge diagnose <url>` e a publicacao e silenciosa.
"""
from __future__ import annotations

import json
import logging
import os
import shutil
import stat
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


_SECRETS_PATH = Path.home() / ".testforge" / "secrets"


@dataclass
class AzureDevOpsCreds:
    pat: str
    org: str
    project: str
    repo: str
    source: str  # 'env' | 'secrets_file' | 'azure_credentials' | 'git_helper' | 'config'


# ----------------------------------------------------------------------
# Z1 — instalacao admin
# ----------------------------------------------------------------------

def install_pat(pat: str, org: str, project: str, repo: str,
                 path: Path = _SECRETS_PATH) -> Path:
    """Persiste credenciais Azure DevOps com permissao 0600."""
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "azure_devops": {
            "pat": pat, "org": org, "project": project, "repo": repo,
        }
    }
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    try:
        path.chmod(stat.S_IRUSR | stat.S_IWUSR)  # 0600
    except Exception:
        pass
    return path


# ----------------------------------------------------------------------
# Z5 — cadeia de coleta de credenciais
# ----------------------------------------------------------------------

def resolve_credentials(
    org: str = "", project: str = "", repo: str = "",
    secrets_path: Path = _SECRETS_PATH,
) -> Optional[AzureDevOpsCreds]:
    """Percorre a cadeia, retorna primeiro resultado. None quando nada resolve."""
    # 1. Variavel de ambiente
    pat = os.environ.get("AZURE_DEVOPS_PAT", "").strip()
    if pat and org and project and repo:
        return AzureDevOpsCreds(pat=pat, org=org, project=project,
                                 repo=repo, source="env")

    # 2. ~/.testforge/secrets
    if secrets_path.exists():
        try:
            data = json.loads(secrets_path.read_text(encoding="utf-8"))
            az = data.get("azure_devops") or {}
            if az.get("pat") and az.get("org") and az.get("project") and az.get("repo"):
                return AzureDevOpsCreds(
                    pat=az["pat"], org=az["org"],
                    project=az["project"], repo=az["repo"],
                    source="secrets_file",
                )
        except Exception as exc:
            logger.warning("secrets file parse failed: %s", exc)

    # 3. ~/.azure/credentials (helper legado az CLI)
    azure_creds = Path.home() / ".azure" / "credentials"
    if pat == "" and azure_creds.exists() and org and project and repo:
        try:
            for line in azure_creds.read_text(encoding="utf-8").splitlines():
                if line.lower().startswith("azure_devops_pat"):
                    _, _, val = line.partition("=")
                    pat = val.strip().strip('"').strip("'")
                    if pat:
                        return AzureDevOpsCreds(
                            pat=pat, org=org, project=project, repo=repo,
                            source="azure_credentials",
                        )
        except Exception:
            pass

    # 4. Helper git credential
    if pat == "" and org and project and repo:
        try:
            req = (
                "protocol=https\n"
                "host=dev.azure.com\n"
                f"path={org}/{project}/_git/{repo}\n"
            )
            proc = subprocess.run(
                ["git", "credential", "fill"],
                input=req, capture_output=True, text=True, timeout=4,
            )
            for line in (proc.stdout or "").splitlines():
                if line.startswith("password="):
                    pat = line[len("password="):].strip()
                    if pat:
                        return AzureDevOpsCreds(
                            pat=pat, org=org, project=project, repo=repo,
                            source="git_helper",
                        )
        except Exception:
            pass

    return None


# ----------------------------------------------------------------------
# Publicador
# ----------------------------------------------------------------------

class AzureDevOpsPublisher:
    """G4 — HTTPS+PAT primario, fallback SSH."""

    def __init__(self, org: str, project: str, repo: str,
                 branch: str = "main", prefer_ssh: bool = False,
                 path_prefix: str = "diagnostic",
                 secrets_path: Path = _SECRETS_PATH) -> None:
        self._org = org
        self._project = project
        self._repo = repo
        self._branch = branch
        self._prefer_ssh = prefer_ssh
        self._path_prefix = path_prefix
        self._secrets_path = secrets_path

    # ------------------------------------------------------------------
    def remote_https(self, pat: Optional[str] = None) -> str:
        if pat:
            return (f"https://anything:{pat}@dev.azure.com/"
                    f"{self._org}/{self._project}/_git/{self._repo}")
        return (f"https://dev.azure.com/{self._org}/"
                f"{self._project}/_git/{self._repo}")

    def remote_ssh(self) -> str:
        return f"git@ssh.dev.azure.com:v3/{self._org}/{self._project}/{self._repo}"

    # ------------------------------------------------------------------
    def publish(self, recording_id: str, diagnostic_dir: str) -> dict:
        """Clona, copia artefatos de diagnostico, commita, faz push.

        Retorna dict com success/error/remote_path/commit_sha.
        """
        if not os.path.isdir(diagnostic_dir):
            return {"success": False, "error": f"diagnostic_dir not found: {diagnostic_dir}"}

        creds = resolve_credentials(self._org, self._project, self._repo,
                                      secrets_path=self._secrets_path)
        if not creds and not self._prefer_ssh:
            return {"success": False,
                    "error": "no Azure DevOps PAT resolvable (env / secrets / azure / git helper)"}

        push_url = self.remote_ssh() if self._prefer_ssh else self.remote_https(creds.pat if creds else None)
        clone_url = push_url  # same URL for clone and push

        with tempfile.TemporaryDirectory() as work:
            try:
                self._git(["clone", "--depth", "1", "--branch", self._branch,
                            clone_url, work], cwd=None, log_url=push_url)
            except subprocess.CalledProcessError as exc:
                # Repo vazio ou branch ausente: init+push depois
                logger.info("Clone failed (treating as empty repo): %s", exc)
                self._git(["init"], cwd=work)
                self._git(["checkout", "-b", self._branch], cwd=work)
                self._git(["remote", "add", "origin", push_url], cwd=work)

            target_dir = Path(work) / self._path_prefix / recording_id
            target_dir.mkdir(parents=True, exist_ok=True)
            copied: list[str] = []
            for entry in os.listdir(diagnostic_dir):
                src = Path(diagnostic_dir) / entry
                dst = target_dir / entry
                if src.is_dir():
                    shutil.copytree(src, dst, dirs_exist_ok=True)
                else:
                    shutil.copy2(src, dst)
                copied.append(entry)

            try:
                self._git(["add", "-f", "."], cwd=work)
            except subprocess.CalledProcessError as exc:
                return {"success": False, "error": f"git add: {exc}"}
            try:
                self._git(["-c", "user.email=testforge@local",
                            "-c", "user.name=TestForge Diagnostic",
                            "commit", "-m", f"diag: {recording_id}"], cwd=work)
            except subprocess.CalledProcessError as exc:
                # Nada para commitar e ok
                if b"nothing to commit" not in (getattr(exc, "stderr", b"") or b""):
                    logger.warning("commit: %s", exc)
            try:
                self._git(["push", "origin", self._branch], cwd=work, log_url=push_url)
            except subprocess.CalledProcessError as exc:
                return {"success": False, "error": f"git push: {exc}"}

            sha = self._git(["rev-parse", "HEAD"], cwd=work, capture=True).strip()
            return {
                "success": True,
                "remote_path": f"{self._path_prefix}/{recording_id}",
                "commit_sha": sha,
                "artifacts_copied": copied,
                "credential_source": creds.source if creds else "ssh",
            }

    # ------------------------------------------------------------------
    def _git(self, args: list[str], cwd: Optional[str], capture: bool = False,
             log_url: Optional[str] = None) -> str:
        # Mascara PAT na saida do log
        log_args = list(args)
        if log_url:
            logger.debug("git %s (url=%s...)", " ".join(log_args), log_url[:40])
        else:
            logger.debug("git %s", " ".join(log_args))
        proc = subprocess.run(
            ["git"] + args, cwd=cwd, capture_output=True, text=True,
            check=True, timeout=60,
        )
        return proc.stdout
