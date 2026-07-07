from __future__ import annotations

import dataclasses
import filecmp
import glob
import json
import logging
import os
import pathlib
import shutil
import subprocess
import tempfile
import re
from pathlib import PurePosixPath
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

from testforge.subprocess_utils import run_hidden


@dataclass
class PublishResult:
    recording_id: str
    success: bool
    remote_path: str = ""
    commit_sha: str = ""
    error: str = ""
    artifacts_copied: list[str] = field(default_factory=list)
    summary_generated: bool = False


class GitPublisher:
    def __init__(
        self,
        url: str,
        token: str,
        branch: str = "main",
        path_prefix: str = "recordings",
        local_mode: bool = False,
        git_root: str = "",
        remote: str = "origin",
    ):
        self._url = url
        self._token = token
        self._branch = branch
        self._path_prefix = path_prefix
        self._local_mode = local_mode
        self._git_root = git_root
        self._remote = remote
        self._log = logging.getLogger("testforge.publisher")

    @classmethod
    def from_env(cls) -> Optional[GitPublisher]:
        log = logging.getLogger("testforge.publisher")
        url = os.getenv("TESTFORGE_GIT_URL", "")
        token = os.getenv("TESTFORGE_GIT_TOKEN", "")
        if not url:
            log.debug("from_env: TESTFORGE_GIT_URL nao definido — publisher desabilitado")
            return None
        branch = os.getenv("TESTFORGE_GIT_BRANCH", "main")
        prefix = os.getenv("TESTFORGE_GIT_PATH_PREFIX", "recordings")
        log.info("from_env: modo remoto — url=%s branch=%s prefix=%s token=%s",
                 url, branch, prefix, "***" if token else "(sem token)")
        return cls(url=url, token=token, branch=branch, path_prefix=prefix)

    @classmethod
    def from_config(cls, cwd: str = None) -> Optional[GitPublisher]:
        """Carrega de .testforge/config.yml. Tenta cwd primeiro, depois git root."""
        log = logging.getLogger("testforge.publisher")
        cwd = cwd or os.getcwd()
        # Sempre resolve git root — necessario para publicacao modo local independentemente
        # de onde o arquivo de config e encontrado.
        git_root = cls._find_git_root(cwd)
        log.debug("from_config: cwd=%s git_root=%s", cwd, git_root)
        # 1. Tenta cwd/.testforge/config.yml
        config_path = os.path.join(cwd, ".testforge", "config.yml")
        # 2. Fallback para git root/.testforge/config.yml
        if not os.path.exists(config_path) and git_root:
            config_path = os.path.join(git_root, ".testforge", "config.yml")
        if not os.path.exists(config_path):
            log.debug("from_config: nenhum config encontrado em %s", config_path)
            return None
        log.debug("from_config: carregando %s", config_path)
        import yaml
        with open(config_path) as f:
            cfg = yaml.safe_load(f) or {}
        pub = cfg.get("publisher", {})
        if not pub.get("enabled", True):
            log.info("from_config: publisher desabilitado no config")
            return None
        url = pub.get("url", "").strip()
        token = pub.get("token", "").strip()
        local_mode = not bool(url)
        log.info(
            "from_config: carregado — modo=%s branch=%s prefix=%s git_root=%s token=%s",
            "local" if local_mode else "remoto",
            pub.get("branch", "main"),
            pub.get("path_prefix", "recordings"),
            git_root,
            "***" if token else "(sem token)",
        )
        return cls(
            url=url,
            token=token,
            branch=pub.get("branch", "main"),
            path_prefix=pub.get("path_prefix", "recordings"),
            local_mode=local_mode,
            git_root=git_root or "",
            remote=pub.get("remote", "origin"),
        )

    @staticmethod
    def _find_git_root(start: str) -> Optional[str]:
        """Sobe a partir de start procurando diretorio .git."""
        path = os.path.abspath(start)
        while True:
            if os.path.isdir(os.path.join(path, ".git")):
                return path
            parent = os.path.dirname(path)
            if parent == path:
                return None
            path = parent

    def publish(
        self,
        recording_id: str,
        recordings_dir: str | pathlib.Path,
        semantic_tests_dir: str | pathlib.Path,
        failed_recordings_dir: str | pathlib.Path | None = None,
    ) -> PublishResult:
        """Publica artefatos de gravacao no repositorio Git configurado."""
        if self._local_mode:
            return self._local_publish(
                recording_id,
                recordings_dir,
                semantic_tests_dir,
                failed_recordings_dir=failed_recordings_dir,
            )
        self._log.info("publish: iniciando modo remoto — recording=%s url=%s", recording_id, self._url)
        try:
            recordings_dir = str(recordings_dir)
            semantic_tests_dir = str(semantic_tests_dir)

            # Load metadata
            metadata_path = os.path.join(recordings_dir, recording_id, "recording_metadata.json")
            if not os.path.exists(metadata_path):
                self._log.error("publish: metadata nao encontrado em %s", metadata_path)
                return PublishResult(
                    recording_id=recording_id,
                    success=False,
                    error=f"metadata nao encontrado: {metadata_path}",
                )

            with open(metadata_path) as f:
                metadata = json.load(f)
            self._log.debug("publish: metadata carregado — system=%s suite=%s",
                            metadata.get("system"), metadata.get("suite"))

            with tempfile.TemporaryDirectory() as tmp_dir:
                # Clone raso
                self._clone_shallow(tmp_dir)
                repo_dir = os.path.join(tmp_dir, "repo")

                # Calcula caminho remoto hierarquico a partir de system/suite/test_case
                remote_path = self._build_remote_path(recording_id, metadata)
                self._log.info("publish: caminho remoto = %s", remote_path)

                # Create destination directory
                dest_dir = os.path.join(repo_dir, *remote_path.split("/"))
                os.makedirs(dest_dir, exist_ok=True)

                # Copia artefatos
                copied = self._copy_artifacts(
                    repo_dir, recording_id, recordings_dir, semantic_tests_dir,
                    remote_path=remote_path,
                    failed_recordings_dir=failed_recordings_dir,
                )
                self._log.info("publish: %d artefato(s) copiado(s): %s", len(copied), copied)

                # Gera relatorio de submissao (compacto, voltado ao time)
                submission_report = self._generate_submission_report(
                    recording_id, metadata, recordings_dir
                )
                # Salva localmente no diretorio da gravacao (copia permanente)
                local_report_path = os.path.join(recordings_dir, recording_id, "submission_report.json")
                with open(local_report_path, "w", encoding="utf-8") as f:
                    json.dump(submission_report, f, indent=2, default=str)
                # Copy to repo
                report_path = os.path.join(dest_dir, "submission_report.json")
                shutil.copy2(local_report_path, report_path)
                copied.append("submission_report.json")

                # Gera sumario
                summary_md = self._generate_summary(recording_id, metadata)
                summary_path = os.path.join(dest_dir, "SUMMARY.md")
                with open(summary_path, "w", encoding="utf-8") as f:
                    f.write(summary_md)
                summary_generated = True

                # Prepara alteracoes (stage)
                self._git("add", ".", cwd=repo_dir)

                # Verifica se ha alteracoes staged
                staged = self._git("diff", "--cached", "--name-only", cwd=repo_dir)
                if not staged.strip():
                    self._log.info("publish: sem alteracoes para commitar (artefatos ja existem no repo)")
                    return PublishResult(
                        recording_id=recording_id,
                        success=True,
                        remote_path=remote_path,
                        commit_sha="",
                        artifacts_copied=copied,
                        summary_generated=summary_generated,
                    )
                self._log.debug("publish: arquivos staged:\n%s", staged)

                # Commit com variaveis de ambiente git author
                commit_env = os.environ.copy()
                commit_env.update({
                    "GIT_AUTHOR_NAME": "TestForge",
                    "GIT_AUTHOR_EMAIL": "testforge@noreply",
                    "GIT_COMMITTER_NAME": "TestForge",
                    "GIT_COMMITTER_EMAIL": "testforge@noreply",
                })
                self._git(
                    "commit",
                    "-m",
                    f"chore: gravacao testforge {recording_id}",
                    cwd=repo_dir,
                    env=commit_env,
                )
                self._log.info("publish: commit criado")

                # Push
                self._log.info("publish: enviando para origin/%s ...", self._branch)
                self._git("push", "origin", self._branch, cwd=repo_dir)

                # Obtem SHA do commit
                sha = self._git("rev-parse", "HEAD", cwd=repo_dir)
                self._log.info("publish: push concluido — sha=%s", sha[:12] if sha else "?")

                return PublishResult(
                    recording_id=recording_id,
                    success=True,
                    remote_path=remote_path,
                    commit_sha=sha,
                    artifacts_copied=copied,
                    summary_generated=summary_generated,
                )

        except Exception as exc:
            scrubbed_error = self._scrub_token(str(exc))
            self._log.error("publish: falhou — %s", scrubbed_error)
            return PublishResult(
                recording_id=recording_id,
                success=False,
                error=scrubbed_error,
            )

    def _local_publish(
        self,
        recording_id: str,
        recordings_dir: str | pathlib.Path,
        semantic_tests_dir: str | pathlib.Path,
        failed_recordings_dir: str | pathlib.Path | None = None,
    ) -> PublishResult:
        """Publica commitando diretamente no repo git local. Nenhum token necessario."""
        self._log.info(
            "_local_publish: iniciando — recording=%s git_root=%s remote=%s branch=%s",
            recording_id, self._git_root, self._remote, self._branch,
        )
        if not self._git_root:
            err = "_local_publish: git_root nao definido — nao esta em um repositorio git"
            self._log.error(err)
            return PublishResult(recording_id=recording_id, success=False, error=err)
        try:
            recordings_dir = str(recordings_dir)
            semantic_tests_dir = str(semantic_tests_dir)

            metadata_path = os.path.join(recordings_dir, recording_id, "recording_metadata.json")
            if not os.path.exists(metadata_path):
                self._log.error("_local_publish: metadata nao encontrado em %s", metadata_path)
                return PublishResult(
                    recording_id=recording_id,
                    success=False,
                    error=f"metadata nao encontrado: {metadata_path}",
                )

            with open(metadata_path) as f:
                metadata = json.load(f)
            self._log.debug("_local_publish: metadata carregado — system=%s suite=%s",
                            metadata.get("system"), metadata.get("suite"))

            remote_path = self._build_remote_path(recording_id, metadata)
            self._log.info("_local_publish: caminho no repo = %s", remote_path)
            dest_dir = os.path.join(self._git_root, *remote_path.split("/"))
            os.makedirs(dest_dir, exist_ok=True)

            copied = self._copy_artifacts(
                self._git_root, recording_id, recordings_dir, semantic_tests_dir,
                remote_path=remote_path,
                failed_recordings_dir=failed_recordings_dir,
            )
            self._log.info("_local_publish: %d artefato(s) copiado(s): %s", len(copied), copied)

            submission_report = self._generate_submission_report(
                recording_id, metadata, recordings_dir
            )
            local_report_path = os.path.join(recordings_dir, recording_id, "submission_report.json")
            with open(local_report_path, "w", encoding="utf-8") as f:
                json.dump(submission_report, f, indent=2, default=str)
            shutil.copy2(local_report_path, os.path.join(dest_dir, "submission_report.json"))
            if "submission_report.json" not in copied:
                copied.append("submission_report.json")

            summary_md = self._generate_summary(recording_id, metadata)
            with open(os.path.join(dest_dir, "SUMMARY.md"), "w") as f:
                f.write(summary_md)

            rel_dest = os.path.relpath(dest_dir, self._git_root).replace("\\", "/")
            # Hotfix BUG 11: force-add because `recordings/` is normally in
            # .gitignore. The publisher's whole job is to lift selected
            # recording dirs into a git-tracked snapshot — `git add -f` is
            # what the user wants every single time the publisher runs.
            self._git("add", "-f", rel_dest, cwd=self._git_root)

            staged = self._git("diff", "--cached", "--name-only", cwd=self._git_root)
            if not staged.strip():
                self._log.info("_local_publish: sem alteracoes para commitar")
                return PublishResult(
                    recording_id=recording_id,
                    success=True,
                    remote_path=remote_path,
                    commit_sha="(no changes)",
                    artifacts_copied=copied,
                    summary_generated=True,
                )
            self._log.debug("_local_publish: arquivos staged:\n%s", staged)

            commit_env = os.environ.copy()
            commit_env.update({
                "GIT_AUTHOR_NAME": "TestForge",
                "GIT_AUTHOR_EMAIL": "testforge@noreply",
                "GIT_COMMITTER_NAME": "TestForge",
                "GIT_COMMITTER_EMAIL": "testforge@noreply",
            })
            self._git(
                "commit", "-m", f"chore: gravacao testforge {recording_id}",
                cwd=self._git_root, env=commit_env,
            )
            self._log.info("_local_publish: commit criado")
            self._log.info("_local_publish: enviando para %s HEAD:%s ...", self._remote, self._branch)
            self._git("push", self._remote, f"HEAD:{self._branch}", cwd=self._git_root)
            sha = self._git("rev-parse", "HEAD", cwd=self._git_root)
            self._log.info("_local_publish: push concluido — sha=%s", sha[:12] if sha else "?")

            return PublishResult(
                recording_id=recording_id,
                success=True,
                remote_path=remote_path,
                commit_sha=sha[:12],
                artifacts_copied=copied,
                summary_generated=True,
            )

        except Exception as exc:
            scrubbed = self._scrub_token(str(exc))
            self._log.error("_local_publish: falhou — %s", scrubbed)
            return PublishResult(recording_id=recording_id, success=False, error=scrubbed)

    def _git(self, *args: str, cwd: str, env: dict | None = None) -> str:
        """Executa comando git. Nunca registra o token no log. Retorna stdout."""
        if env is None:
            env = os.environ.copy()
        safe_args = [self._scrub_token(a) for a in args]
        self._log.debug("git %s (cwd=%s)", " ".join(safe_args), cwd)
        result = run_hidden(
            ["git", *args],
            cwd=cwd,
            capture_output=True,
            text=True,
            check=False,
            env=env,
        )
        if result.returncode != 0:
            err = self._scrub_token(result.stderr or "")
            self._log.error(
                "git %s falhou (rc=%d): %s",
                safe_args[0] if safe_args else "?",
                result.returncode,
                err.strip(),
            )
            raise subprocess.CalledProcessError(
                result.returncode, ["git", *safe_args], stderr=err
            )
        stdout = result.stdout.strip()
        if stdout:
            self._log.debug("git %s → %s", safe_args[0] if safe_args else "?", stdout[:200])
        return stdout

    def _scrub_token(self, text: str) -> str:
        """Substitui token por *** no texto."""
        if self._token and self._token in text:
            return text.replace(self._token, "***")
        return text

    def _clone_shallow(self, tmp_dir: str) -> None:
        """Clona repo com --depth 1."""
        if self._token:
            auth_url = self._url.replace("https://", f"https://:{self._token}@")
        else:
            auth_url = self._url  # relies on OS credential manager (e.g. Windows GCM)

        safe_url = self._scrub_token(auth_url)
        self._log.info("clone: url=%s branch=%s", safe_url, self._branch)
        try:
            self._git("clone", "--depth", "1", "--branch", self._branch, auth_url, "repo", cwd=tmp_dir)
            self._log.debug("clone: branch '%s' clonado com sucesso", self._branch)
        except subprocess.CalledProcessError as exc:
            err_lower = (exc.stderr or "").lower()
            auth_keywords = (
                "authentication", "403", "401", "credential",
                "could not read username", "permission denied",
                "invalid username or password", "access denied",
            )
            if any(kw in err_lower for kw in auth_keywords):
                self._log.error(
                    "clone: falha de autenticacao em %s — verifique token/credenciais. Erro: %s",
                    safe_url, exc.stderr.strip() if exc.stderr else "(sem mensagem)",
                )
                raise
            # Branch nao existe no remoto — clona padrao e cria localmente
            self._log.info(
                "clone: branch '%s' nao encontrado — clonando branch padrao e criando localmente",
                self._branch,
            )
            self._git("clone", "--depth", "1", auth_url, "repo", cwd=tmp_dir)
            repo_dir = os.path.join(tmp_dir, "repo")
            self._git("checkout", "-b", self._branch, cwd=repo_dir)

    def _build_remote_path(self, recording_id: str, metadata: dict) -> str:
        """Constroi caminho hierarquico a partir de system/suite/test_case.

        Regras:
          1. Sem qualquer classificacao -> {prefix}/uncategorized/{recording_id}
          2. Aceita segmentos em qualquer campo (system/suite/test_case),
             inclusive quando vierem no formato "a/b/c" ou "a\\b\\c".
          3. Evita duplicar o ultimo segmento quando ele ja eh o recording_id.
        """

        def _split_segments(value: str) -> list[str]:
            raw = (value or "").strip()
            if not raw:
                return []
            # Accept values pasted as paths (e.g. "/simax/pesquisa de vagas/")
            # and ignore wrapper quotes often introduced by copy/paste.
            raw = raw.strip("\"'")
            return [
                seg.strip("\"'").strip()
                for seg in re.split(r"[\\/]+", raw)
                if seg and seg.strip("\"'").strip()
            ]

        prefix_parts = _split_segments(self._path_prefix) or ["recordings"]
        classification_parts: list[str] = []
        classification_parts.extend(_split_segments(str(metadata.get("system") or "")))
        classification_parts.extend(_split_segments(str(metadata.get("suite") or "")))
        classification_parts.extend(_split_segments(str(metadata.get("test_case") or "")))

        if not classification_parts:
            return str(PurePosixPath(*prefix_parts, "uncategorized", recording_id))

        if classification_parts[-1] == recording_id:
            return str(PurePosixPath(*prefix_parts, *classification_parts))

        return str(PurePosixPath(*prefix_parts, *classification_parts, recording_id))

    def _generate_submission_report(
        self,
        recording_id: str,
        metadata: dict,
        recordings_dir: str,
    ) -> dict:
        """Gera relatorio de submissao compacto voltado ao time.

        Le readiness_report.json se disponivel. Caso contrario deriva status dos metadados.
        A flag `testforge_issue` e definida quando veredito nao e 'pass', sinalizando ao
        time que algo no TestForge precisa de correcao (nao apenas a gravacao).
        """
        rec_dir = os.path.join(recordings_dir, recording_id)

        # Le relatorio de prontidao se disponivel
        readiness_path = os.path.join(rec_dir, "readiness", "readiness_report.json")
        verdict = "not_evaluated"
        criteria_passed = 0
        criteria_total = 5
        steps: dict = {}
        failures: list = []
        warnings: list = []

        if os.path.exists(readiness_path):
            try:
                with open(readiness_path) as f:
                    rr = json.load(f).get("readiness_report", {})
                verdict = rr.get("verdict", "not_evaluated")
                criteria = rr.get("criteria", {})
                criteria_passed = sum(1 for v in criteria.values() if v)
                steps = rr.get("steps", {})
                failures = rr.get("failures", [])
                warnings = rr.get("warnings", [])
            except Exception:
                pass

        # Le versao do testforge
        version = "unknown"
        try:
            version_file = pathlib.Path(__file__).parent.parent.parent.parent / "VERSION"
            if version_file.exists():
                version = version_file.read_text().strip()
        except Exception:
            pass

        status = metadata.get("recording_status") or metadata.get("status", "unknown")

        # Fase 2 (BUG-REC-01/16): expose per-artifact counts so consumers can
        # distinguish "asserts curated via Shift+A" (steps.jsonl) from "steps
        # executed post-compile" (steps.total). Prior confusion: consumers
        # assumed steps.jsonl.length == test size.
        artifact_counts = {
            "raw_events": self._count_lines(rec_dir, "raw_events.jsonl"),
            "asserts_curated": self._count_lines(rec_dir, "steps.jsonl"),
            "value_mutations": self._count_lines(rec_dir, "value_mutations.jsonl"),
            "field_snapshots": self._count_lines(rec_dir, "field_snapshots.jsonl"),
        }

        report = {
            "testforge_version": version,
            "submitted_at": datetime.now(timezone.utc).isoformat(),
            "recording_id": recording_id,
            "system": metadata.get("system", ""),
            "suite": metadata.get("suite", ""),
            "test_case": metadata.get("test_case", ""),
            "application": metadata.get("application", ""),
            "base_url": metadata.get("base_url", ""),
            "status": status,
            "verdict": verdict,
            "criteria_passed": criteria_passed,
            "criteria_total": criteria_total,
            "steps": steps,
            "artifact_counts": artifact_counts,
            "failures": failures,
            "warnings": warnings,
            "testforge_issue": verdict not in ("pass", "not_evaluated"),
        }
        return report

    @staticmethod
    def _count_lines(rec_dir: str, filename: str) -> int:
        p = os.path.join(rec_dir, filename)
        if not os.path.exists(p):
            return 0
        try:
            with open(p, "r", encoding="utf-8") as f:
                return sum(1 for line in f if line.strip())
        except Exception:
            return 0

    def _copy_artifacts(
        self,
        repo_dir: str,
        recording_id: str,
        recordings_dir: str,
        semantic_tests_dir: str,
        remote_path: str = "",
        failed_recordings_dir: str | pathlib.Path | None = None,
    ) -> list[str]:
        """Copia artefatos de gravacao e teste semantico. Retorna lista de arquivos copiados."""
        copied = []
        copied_files_rel: set[str] = set()
        dest_dir = (
            os.path.join(repo_dir, *remote_path.split("/"))
            if remote_path
            else os.path.join(repo_dir, self._path_prefix, recording_id)
        )
        os.makedirs(dest_dir, exist_ok=True)

        # Copia recursivamente tudo que existir no diretorio da gravacao.
        # Isso garante envio de novas pastas/arquivos (ex.: completeness)
        # sem precisar atualizar lista fixa no publisher.
        rec_dir = os.path.join(recordings_dir, recording_id)
        if os.path.isdir(rec_dir):
            for root, dirs, files in os.walk(rec_dir):
                rel_root = os.path.relpath(root, rec_dir)

                # Evita copiar diretorios vazios para manter compatibilidade
                # com comportamento anterior (ex.: screenshots vazio).
                for dname in list(dirs):
                    src_d = os.path.join(root, dname)
                    rel_d = dname if rel_root == "." else os.path.join(rel_root, dname)
                    if not any(pathlib.Path(src_d).rglob("*")):
                        dirs.remove(dname)
                        continue
                    dest_d = os.path.join(dest_dir, rel_d)
                    os.makedirs(dest_d, exist_ok=True)
                    copied.append(rel_d.replace("\\", "/") + "/")

                for fname in files:
                    src_f = os.path.join(root, fname)
                    rel_f = fname if rel_root == "." else os.path.join(rel_root, fname)
                    dest_f = os.path.join(dest_dir, rel_f)
                    os.makedirs(os.path.dirname(dest_f), exist_ok=True)
                    shutil.copy2(src_f, dest_f)
                    copied.append(rel_f.replace("\\", "/"))
                    copied_files_rel.add(os.path.normpath(rel_f).lower())

        # Arquivos de teste semantico (se existirem)
        st_base = os.path.join(semantic_tests_dir, f"ST-{recording_id}")
        if os.path.isdir(st_base):
            # Encontra test_*.py
            test_files = glob.glob(os.path.join(st_base, "test_*.py"))
            for test_file in test_files:
                shutil.copy2(test_file, dest_dir)
                copied.append(os.path.basename(test_file))
                copied_files_rel.add(os.path.normpath(os.path.basename(test_file)).lower())

            # semantic_steps.jsonl
            steps_file = os.path.join(st_base, "semantic_steps.jsonl")
            if os.path.exists(steps_file):
                shutil.copy2(steps_file, dest_dir)
                copied.append("semantic_steps.jsonl")
                copied_files_rel.add(os.path.normpath("semantic_steps.jsonl").lower())

        # Copia snapshots de falha relacionados ao recording_id (se existirem).
        # Estrutura destino: <remote_path>/recordings_failed/<folder>/...
        if failed_recordings_dir:
            failed_root = str(failed_recordings_dir)
            if os.path.isdir(failed_root):
                prefix = f"{recording_id}_"
                for name in sorted(os.listdir(failed_root)):
                    if not (name == recording_id or name.startswith(prefix)):
                        continue
                    src_failed = os.path.join(failed_root, name)
                    if not os.path.isdir(src_failed):
                        continue
                    rel_failed_root = os.path.join("recordings_failed", name)
                    dst_failed = os.path.join(dest_dir, rel_failed_root)
                    os.makedirs(dst_failed, exist_ok=True)

                    for root, _dirs, files in os.walk(src_failed):
                        rel_root = os.path.relpath(root, src_failed)
                        for fname in files:
                            src_f = os.path.join(root, fname)
                            rel_f = fname if rel_root == "." else os.path.join(rel_root, fname)

                            # Dedup: nao copia se o mesmo arquivo relativo ja foi enviado
                            # no pacote principal e tiver exatamente o mesmo conteudo.
                            main_key = os.path.normpath(rel_f).lower()
                            if main_key in copied_files_rel:
                                main_dest = os.path.join(dest_dir, rel_f)
                                try:
                                    if os.path.exists(main_dest) and filecmp.cmp(src_f, main_dest, shallow=False):
                                        continue
                                except Exception:
                                    pass

                            dst_f = os.path.join(dst_failed, rel_f)
                            os.makedirs(os.path.dirname(dst_f), exist_ok=True)
                            shutil.copy2(src_f, dst_f)
                    copied.append(rel_failed_root.replace("\\", "/") + "/")

        # Remove duplicados preservando ordem.
        return list(dict.fromkeys(copied))

    def _generate_summary(self, recording_id: str, metadata: dict) -> str:
        """Gera conteudo de SUMMARY.md."""
        app = metadata.get("application", "unknown")
        url = metadata.get("base_url", "")
        started = metadata.get("started_at", "")
        finished = metadata.get("finished_at", "")
        status = metadata.get("recording_status", "unknown")
        status_history = metadata.get("status_history", [])

        md = f"""# Gravacao TestForge: {recording_id}

**Aplicacao**: {app}
**URL Base**: {url}
**Iniciado**: {started}
**Finalizado**: {finished}
**Status**: {status}

## Artefatos

- recording_metadata.json
- raw_events.jsonl
- steps.jsonl
- field_snapshots.jsonl
- value_mutations.jsonl
- final_state_snapshot.json
- network_log.json
- recording_config.json
- dom_snapshots/ (diretorio)
- screenshots/ (se capturado)
- test_*.py (se compilado)
- semantic_steps.jsonl (se compilado)

## Historico de Status

| Status | Timestamp | Detalhes |
|--------|-----------|---------|
"""
        for entry in status_history:
            s = entry.get("status", "")
            ts = entry.get("timestamp", "")
            md += f"| {s} | {ts} | |\n"

        return md
