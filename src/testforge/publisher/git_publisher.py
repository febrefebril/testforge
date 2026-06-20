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
    ):
        self._url = url
        self._token = token
        self._branch = branch
        self._path_prefix = path_prefix
        self._log = logging.getLogger("testforge.publisher")

    @classmethod
    def from_env(cls) -> Optional[GitPublisher]:
        url = os.getenv("TESTFORGE_GIT_URL", "")
        token = os.getenv("TESTFORGE_GIT_TOKEN", "")
        if not url or not token:
            return None
        branch = os.getenv("TESTFORGE_GIT_BRANCH", "main")
        prefix = os.getenv("TESTFORGE_GIT_PATH_PREFIX", "recordings")
        return cls(url=url, token=token, branch=branch, path_prefix=prefix)

    def publish(
        self,
        recording_id: str,
        recordings_dir: str | pathlib.Path,
        semantic_tests_dir: str | pathlib.Path,
    ) -> PublishResult:
        """Publish recording artifacts to configured Git repo."""
        try:
            recordings_dir = str(recordings_dir)
            semantic_tests_dir = str(semantic_tests_dir)

            # Load metadata
            metadata_path = os.path.join(recordings_dir, recording_id, "recording_metadata.json")
            if not os.path.exists(metadata_path):
                return PublishResult(
                    recording_id=recording_id,
                    success=False,
                    error=f"metadata not found: {metadata_path}",
                )

            with open(metadata_path) as f:
                metadata = json.load(f)

            with tempfile.TemporaryDirectory() as tmp_dir:
                # Clone shallow
                self._clone_shallow(tmp_dir)
                repo_dir = os.path.join(tmp_dir, "repo")

                # Create destination directory
                dest_dir = os.path.join(repo_dir, self._path_prefix, recording_id)
                os.makedirs(dest_dir, exist_ok=True)

                # Copy artifacts
                copied = self._copy_artifacts(
                    repo_dir, recording_id, recordings_dir, semantic_tests_dir
                )

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
                    # Nothing changed
                    return PublishResult(
                        recording_id=recording_id,
                        success=True,
                        remote_path=os.path.join(self._path_prefix, recording_id),
                        commit_sha="",
                        artifacts_copied=copied,
                        summary_generated=summary_generated,
                    )

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
                    f"chore: testforge recording {recording_id}",
                    cwd=repo_dir,
                    env=commit_env,
                )

                # Push
                self._git("push", "origin", self._branch, cwd=repo_dir)

                # Get commit SHA
                sha = self._git("rev-parse", "HEAD", cwd=repo_dir)

                return PublishResult(
                    recording_id=recording_id,
                    success=True,
                    remote_path=os.path.join(self._path_prefix, recording_id),
                    commit_sha=sha,
                    artifacts_copied=copied,
                    summary_generated=summary_generated,
                )

        except Exception as exc:
            scrubbed_error = self._scrub_token(str(exc))
            return PublishResult(
                recording_id=recording_id,
                success=False,
                error=scrubbed_error,
            )

    def _git(self, *args: str, cwd: str, env: dict | None = None) -> str:
        """Run a git command. Never logs the token. Returns stdout."""
        if env is None:
            env = os.environ.copy()
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
            raise subprocess.CalledProcessError(result.returncode, ["git", args[0]], stderr=err)
        return result.stdout.strip()

    def _scrub_token(self, text: str) -> str:
        """Replace token with *** in text."""
        if self._token and self._token in text:
            return text.replace(self._token, "***")
        return text

    def _clone_shallow(self, tmp_dir: str) -> None:
        """Clone repo with --depth 1."""
        auth_url = self._url.replace("https://", f"https://:{self._token}@")

        try:
            # Try clone with branch
            self._git("clone", "--depth", "1", "--branch", self._branch, auth_url, "repo", cwd=tmp_dir)
        except subprocess.CalledProcessError:
            # Branch doesn't exist, clone without branch and create it
            self._git("clone", "--depth", "1", auth_url, "repo", cwd=tmp_dir)
            repo_dir = os.path.join(tmp_dir, "repo")
            self._git("checkout", "-b", self._branch, cwd=repo_dir)

    def _copy_artifacts(
        self,
        repo_dir: str,
        recording_id: str,
        recordings_dir: str,
        semantic_tests_dir: str,
    ) -> list[str]:
        """Copy recording and semantic test artifacts. Returns list of copied files."""
        copied = []
        dest_dir = os.path.join(repo_dir, self._path_prefix, recording_id)

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

        md = f"""# TestForge Recording: {recording_id}

**Application**: {app}
**Base URL**: {url}
**Started**: {started}
**Finished**: {finished}
**Status**: {status}

## Artifacts

- recording_metadata.json
- raw_events.jsonl
- steps.jsonl
- field_snapshots.jsonl
- value_mutations.jsonl
- final_state_snapshot.json
- network_log.json
- recording_config.json
- dom_snapshots/ (directory)
- screenshots/ (if captured)
- test_*.py (if compiled)
- semantic_steps.jsonl (if compiled)

## Status History

| Status | Timestamp | Details |
|--------|-----------|---------|
"""
        for entry in status_history:
            s = entry.get("status", "")
            ts = entry.get("timestamp", "")
            md += f"| {s} | {ts} | |\n"

        return md
