from __future__ import annotations

import dataclasses
import glob
import json
import logging
import os
import pathlib
import shutil
import subprocess
import tempfile
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional


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
        """Load from .testforge/config.yml. Probes cwd first, then git root."""
        log = logging.getLogger("testforge.publisher")
        cwd = cwd or os.getcwd()
        # Always resolve git root — needed for local-mode publishing regardless
        # of where the config file is found.
        git_root = cls._find_git_root(cwd)
        log.debug("from_config: cwd=%s git_root=%s", cwd, git_root)
        # 1. Try cwd/.testforge/config.yml
        config_path = os.path.join(cwd, ".testforge", "config.yml")
        # 2. Fallback to git root/.testforge/config.yml
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
        """Walk up from start looking for .git directory."""
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
    ) -> PublishResult:
        """Publish recording artifacts to configured Git repo."""
        if self._local_mode:
            return self._local_publish(recording_id, recordings_dir, semantic_tests_dir)
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
                    error=f"metadata not found: {metadata_path}",
                )

            with open(metadata_path) as f:
                metadata = json.load(f)
            self._log.debug("publish: metadata carregado — system=%s suite=%s",
                            metadata.get("system"), metadata.get("suite"))

            with tempfile.TemporaryDirectory() as tmp_dir:
                # Clone shallow
                self._clone_shallow(tmp_dir)
                repo_dir = os.path.join(tmp_dir, "repo")

                # Compute hierarchical remote path from system/suite/test_case
                remote_path = self._build_remote_path(recording_id, metadata)
                self._log.info("publish: caminho remoto = %s", remote_path)

                # Create destination directory
                dest_dir = os.path.join(repo_dir, remote_path)
                os.makedirs(dest_dir, exist_ok=True)

                # Copy artifacts
                copied = self._copy_artifacts(
                    repo_dir, recording_id, recordings_dir, semantic_tests_dir,
                    remote_path=remote_path,
                )
                self._log.info("publish: %d artefato(s) copiado(s): %s", len(copied), copied)

                # Generate submission report (compact, team-facing)
                submission_report = self._generate_submission_report(
                    recording_id, metadata, recordings_dir
                )
                # Save locally in recording dir (permanent copy)
                local_report_path = os.path.join(recordings_dir, recording_id, "submission_report.json")
                with open(local_report_path, "w") as f:
                    json.dump(submission_report, f, indent=2, default=str)
                # Copy to repo
                report_path = os.path.join(dest_dir, "submission_report.json")
                shutil.copy2(local_report_path, report_path)
                copied.append("submission_report.json")

                # Generate summary
                summary_md = self._generate_summary(recording_id, metadata)
                summary_path = os.path.join(dest_dir, "SUMMARY.md")
                with open(summary_path, "w") as f:
                    f.write(summary_md)
                summary_generated = True

                # Stage changes
                self._git("add", ".", cwd=repo_dir)

                # Check if there are staged changes
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

                # Commit with git author env vars
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

                # Get commit SHA
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
    ) -> PublishResult:
        """Publish by committing directly to the local git repo. No token required."""
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
                    error=f"metadata not found: {metadata_path}",
                )

            with open(metadata_path) as f:
                metadata = json.load(f)
            self._log.debug("_local_publish: metadata carregado — system=%s suite=%s",
                            metadata.get("system"), metadata.get("suite"))

            remote_path = self._build_remote_path(recording_id, metadata)
            self._log.info("_local_publish: caminho no repo = %s", remote_path)
            dest_dir = os.path.join(self._git_root, remote_path)
            os.makedirs(dest_dir, exist_ok=True)

            copied = self._copy_artifacts(
                self._git_root, recording_id, recordings_dir, semantic_tests_dir,
                remote_path=remote_path,
            )
            self._log.info("_local_publish: %d artefato(s) copiado(s): %s", len(copied), copied)

            submission_report = self._generate_submission_report(
                recording_id, metadata, recordings_dir
            )
            local_report_path = os.path.join(recordings_dir, recording_id, "submission_report.json")
            with open(local_report_path, "w") as f:
                json.dump(submission_report, f, indent=2, default=str)
            shutil.copy2(local_report_path, os.path.join(dest_dir, "submission_report.json"))
            if "submission_report.json" not in copied:
                copied.append("submission_report.json")

            summary_md = self._generate_summary(recording_id, metadata)
            with open(os.path.join(dest_dir, "SUMMARY.md"), "w") as f:
                f.write(summary_md)

            rel_dest = os.path.relpath(dest_dir, self._git_root)
            self._git("add", rel_dest, cwd=self._git_root)

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
        """Run a git command. Never logs the token. Returns stdout."""
        if env is None:
            env = os.environ.copy()
        safe_args = [self._scrub_token(a) for a in args]
        self._log.debug("git %s (cwd=%s)", " ".join(safe_args), cwd)
        result = subprocess.run(
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
        """Replace token with *** in text."""
        if self._token and self._token in text:
            return text.replace(self._token, "***")
        return text

    def _clone_shallow(self, tmp_dir: str) -> None:
        """Clone repo with --depth 1."""
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
            # Branch doesn't exist on remote — clone default and create it
            self._log.info(
                "clone: branch '%s' nao encontrado — clonando branch padrao e criando localmente",
                self._branch,
            )
            self._git("clone", "--depth", "1", auth_url, "repo", cwd=tmp_dir)
            repo_dir = os.path.join(tmp_dir, "repo")
            self._git("checkout", "-b", self._branch, cwd=repo_dir)

    def _build_remote_path(self, recording_id: str, metadata: dict) -> str:
        """Build hierarchical remote path from system/suite/test_case metadata.

        Returns: {prefix}/{system}/{suite}/{test_case}/{recording_id}
        Falls back to {prefix}/uncategorized/{recording_id} if fields missing.
        """
        system = metadata.get("system", "").strip()
        suite = metadata.get("suite", "").strip()
        test_case = metadata.get("test_case", "").strip()
        if system and suite:
            parts = [self._path_prefix, system, suite]
            if test_case and test_case != recording_id:
                parts.append(test_case)
            parts.append(recording_id)
            return os.path.join(*parts)
        return os.path.join(self._path_prefix, "uncategorized", recording_id)

    def _generate_submission_report(
        self,
        recording_id: str,
        metadata: dict,
        recordings_dir: str,
    ) -> dict:
        """Generate compact team-facing submission report.

        Reads readiness_report.json if available. Otherwise derives status from metadata.
        The `testforge_issue` flag is set when verdict is not 'pass', signalling the
        team that something in TestForge needs fixing (not just the recording).
        """
        rec_dir = os.path.join(recordings_dir, recording_id)

        # Read readiness report if available
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

        # Read testforge version
        version = "unknown"
        try:
            version_file = pathlib.Path(__file__).parent.parent.parent.parent / "VERSION"
            if version_file.exists():
                version = version_file.read_text().strip()
        except Exception:
            pass

        status = metadata.get("recording_status") or metadata.get("status", "unknown")

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
            "failures": failures,
            "warnings": warnings,
            "testforge_issue": verdict not in ("pass", "not_evaluated"),
        }
        return report

    def _copy_artifacts(
        self,
        repo_dir: str,
        recording_id: str,
        recordings_dir: str,
        semantic_tests_dir: str,
        remote_path: str = "",
    ) -> list[str]:
        """Copy recording and semantic test artifacts. Returns list of copied files."""
        copied = []
        dest_dir = os.path.join(repo_dir, remote_path) if remote_path else os.path.join(repo_dir, self._path_prefix, recording_id)

        # Flat files from recordings/
        rec_dir = os.path.join(recordings_dir, recording_id)
        flat_files = [
            "recording_metadata.json",
            "raw_events.jsonl",
            "steps.jsonl",
            "field_snapshots.jsonl",
            "value_mutations.jsonl",
            "final_state_snapshot.json",
            "network_log.json",
            "recording_config.json",
            "submission_report.json",
        ]
        for fname in flat_files:
            src = os.path.join(rec_dir, fname)
            if os.path.exists(src):
                shutil.copy2(src, os.path.join(dest_dir, fname))
                copied.append(fname)

        # dom_snapshots directory (always present)
        dom_src = os.path.join(rec_dir, "dom_snapshots")
        if os.path.isdir(dom_src):
            dom_dest = os.path.join(dest_dir, "dom_snapshots")
            if os.path.exists(dom_dest):
                shutil.rmtree(dom_dest)
            shutil.copytree(dom_src, dom_dest)
            copied.append("dom_snapshots/")

        # screenshots directory (only if non-empty)
        screenshots_src = os.path.join(rec_dir, "screenshots")
        if os.path.isdir(screenshots_src) and os.listdir(screenshots_src):
            screenshots_dest = os.path.join(dest_dir, "screenshots")
            if os.path.exists(screenshots_dest):
                shutil.rmtree(screenshots_dest)
            shutil.copytree(screenshots_src, screenshots_dest)
            copied.append("screenshots/")

        # Semantic test files (if they exist)
        st_base = os.path.join(semantic_tests_dir, f"ST-{recording_id}")
        if os.path.isdir(st_base):
            # Find test_*.py
            test_files = glob.glob(os.path.join(st_base, "test_*.py"))
            for test_file in test_files:
                shutil.copy2(test_file, dest_dir)
                copied.append(os.path.basename(test_file))

            # semantic_steps.jsonl
            steps_file = os.path.join(st_base, "semantic_steps.jsonl")
            if os.path.exists(steps_file):
                shutil.copy2(steps_file, dest_dir)
                copied.append("semantic_steps.jsonl")

        return copied

    def _generate_summary(self, recording_id: str, metadata: dict) -> str:
        """Generate SUMMARY.md content."""
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
