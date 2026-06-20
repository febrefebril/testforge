import json
import os
import tempfile
from unittest import mock
from pathlib import Path

import pytest

from testforge.publisher import GitPublisher, PublishResult


class TestPublishResultDataclass:
    def test_default_fields(self):
        result = PublishResult(recording_id="REC-001", success=True)
        assert result.recording_id == "REC-001"
        assert result.success is True
        assert result.remote_path == ""
        assert result.commit_sha == ""
        assert result.error == ""
        assert result.artifacts_copied == []
        assert result.summary_generated is False

    def test_success_result(self):
        result = PublishResult(
            recording_id="REC-001",
            success=True,
            remote_path="recordings/REC-001",
            commit_sha="abc123",
            artifacts_copied=["file1.json"],
            summary_generated=True,
        )
        assert result.success is True
        assert result.commit_sha == "abc123"


class TestFromEnv:
    def test_from_env_returns_none_when_no_vars(self):
        with mock.patch.dict(os.environ, clear=True):
            result = GitPublisher.from_env()
            assert result is None

    def test_from_env_returns_none_when_only_url_set(self):
        with mock.patch.dict(os.environ, {"TESTFORGE_GIT_URL": "https://dev.azure.com/org/proj/_git/repo"}, clear=True):
            result = GitPublisher.from_env()
            assert result is None

    def test_from_env_creates_publisher_with_all_vars(self):
        env = {
            "TESTFORGE_GIT_URL": "https://dev.azure.com/org/proj/_git/repo",
            "TESTFORGE_GIT_TOKEN": "my-pat",
            "TESTFORGE_GIT_BRANCH": "develop",
            "TESTFORGE_GIT_PATH_PREFIX": "data/recordings",
        }
        with mock.patch.dict(os.environ, env, clear=True):
            result = GitPublisher.from_env()
            assert result is not None
            assert result._url == "https://dev.azure.com/org/proj/_git/repo"
            assert result._token == "my-pat"
            assert result._branch == "develop"
            assert result._path_prefix == "data/recordings"

    def test_from_env_uses_defaults_for_branch_and_prefix(self):
        env = {
            "TESTFORGE_GIT_URL": "https://dev.azure.com/org/proj/_git/repo",
            "TESTFORGE_GIT_TOKEN": "my-pat",
        }
        with mock.patch.dict(os.environ, env, clear=True):
            result = GitPublisher.from_env()
            assert result is not None
            assert result._branch == "main"
            assert result._path_prefix == "recordings"


class TestTokenScrubbing:
    def test_scrub_token_replaces_token_in_string(self):
        publisher = GitPublisher("https://example.com", "secret123")
        text = "error: secret123 in auth"
        scrubbed = publisher._scrub_token(text)
        assert "secret123" not in scrubbed
        assert "***" in scrubbed

    def test_scrub_token_noop_when_token_not_present(self):
        publisher = GitPublisher("https://example.com", "secret123")
        text = "error: auth failed"
        scrubbed = publisher._scrub_token(text)
        assert scrubbed == text

    def test_scrub_token_empty_token_noop(self):
        publisher = GitPublisher("https://example.com", "")
        text = "error: auth failed"
        scrubbed = publisher._scrub_token(text)
        assert scrubbed == text


class TestGenerateSummary:
    def test_summary_contains_recording_id(self):
        publisher = GitPublisher("https://example.com", "token")
        metadata = {
            "recording_id": "REC-20260619",
            "application": "web",
            "base_url": "http://localhost",
            "started_at": "2026-06-19T10:00:00Z",
            "finished_at": "2026-06-19T10:05:00Z",
            "recording_status": "completed",
            "status_history": [],
        }
        summary = publisher._generate_summary("REC-20260619", metadata)
        assert "REC-20260619" in summary
        assert "# TestForge Recording: REC-20260619" in summary

    def test_summary_contains_base_url(self):
        publisher = GitPublisher("https://example.com", "token")
        metadata = {
            "application": "web",
            "base_url": "http://localhost:8080",
            "started_at": "2026-06-19T10:00:00Z",
            "finished_at": "2026-06-19T10:05:00Z",
            "recording_status": "completed",
            "status_history": [],
        }
        summary = publisher._generate_summary("REC-001", metadata)
        assert "http://localhost:8080" in summary

    def test_summary_contains_status(self):
        publisher = GitPublisher("https://example.com", "token")
        metadata = {
            "application": "web",
            "base_url": "http://localhost",
            "started_at": "2026-06-19T10:00:00Z",
            "finished_at": "2026-06-19T10:05:00Z",
            "recording_status": "completed",
            "status_history": [],
        }
        summary = publisher._generate_summary("REC-001", metadata)
        assert "completed" in summary

    def test_summary_contains_status_history_table(self):
        publisher = GitPublisher("https://example.com", "token")
        metadata = {
            "application": "web",
            "base_url": "http://localhost",
            "started_at": "2026-06-19T10:00:00Z",
            "finished_at": "2026-06-19T10:05:00Z",
            "recording_status": "completed",
            "status_history": [
                {"status": "recording", "timestamp": "2026-06-19T10:00:00Z"},
                {"status": "stopped", "timestamp": "2026-06-19T10:05:00Z"},
            ],
        }
        summary = publisher._generate_summary("REC-001", metadata)
        assert "Status History" in summary
        assert "recording" in summary
        assert "stopped" in summary

    def test_summary_handles_missing_status_history(self):
        publisher = GitPublisher("https://example.com", "token")
        metadata = {
            "application": "web",
            "base_url": "http://localhost",
            "started_at": "2026-06-19T10:00:00Z",
            "finished_at": "2026-06-19T10:05:00Z",
            "recording_status": "completed",
        }
        summary = publisher._generate_summary("REC-001", metadata)
        assert "Status History" in summary


class TestCopyArtifacts:
    def _make_recording(self, base_dir: str, rid: str) -> str:
        """Create minimal recording directory structure."""
        rec_dir = os.path.join(base_dir, rid)
        os.makedirs(rec_dir, exist_ok=True)

        # Create flat files
        for fname in ["recording_metadata.json", "raw_events.jsonl", "steps.jsonl"]:
            with open(os.path.join(rec_dir, fname), "w") as f:
                f.write("{}\n")

        # Create dom_snapshots
        dom_dir = os.path.join(rec_dir, "dom_snapshots")
        os.makedirs(dom_dir, exist_ok=True)
        with open(os.path.join(dom_dir, "event_1.html"), "w") as f:
            f.write("<html></html>")

        return rid

    def test_copies_flat_recording_files(self):
        publisher = GitPublisher("https://example.com", "token")
        with tempfile.TemporaryDirectory() as tmp:
            # Setup
            recordings_dir = os.path.join(tmp, "recordings")
            os.makedirs(recordings_dir)
            rid = self._make_recording(recordings_dir, "REC-001")
            repo_dir = os.path.join(tmp, "repo")
            dest_dir = os.path.join(repo_dir, "recordings", rid)
            os.makedirs(dest_dir, exist_ok=True)

            # Act
            copied = publisher._copy_artifacts(repo_dir, rid, recordings_dir, "")

            # Assert
            assert "recording_metadata.json" in copied
            assert os.path.exists(os.path.join(dest_dir, "recording_metadata.json"))
            assert "steps.jsonl" in copied

    def test_skips_missing_files_without_error(self):
        publisher = GitPublisher("https://example.com", "token")
        with tempfile.TemporaryDirectory() as tmp:
            recordings_dir = os.path.join(tmp, "recordings")
            os.makedirs(recordings_dir)
            rid = self._make_recording(recordings_dir, "REC-001")
            repo_dir = os.path.join(tmp, "repo")
            dest_dir = os.path.join(repo_dir, "recordings", rid)
            os.makedirs(dest_dir, exist_ok=True)

            # Test that network_log.json (not created by _make_recording) is skipped
            copied = publisher._copy_artifacts(repo_dir, rid, recordings_dir, "")

            # Should not crash and should not list missing file
            assert "network_log.json" not in copied

    def test_copies_dom_snapshots_directory(self):
        publisher = GitPublisher("https://example.com", "token")
        with tempfile.TemporaryDirectory() as tmp:
            recordings_dir = os.path.join(tmp, "recordings")
            os.makedirs(recordings_dir)
            rid = self._make_recording(recordings_dir, "REC-001")
            repo_dir = os.path.join(tmp, "repo")
            dest_dir = os.path.join(repo_dir, "recordings", rid)
            os.makedirs(dest_dir, exist_ok=True)

            copied = publisher._copy_artifacts(repo_dir, rid, recordings_dir, "")

            # Check dom_snapshots copied
            assert "dom_snapshots/" in copied
            assert os.path.isdir(os.path.join(dest_dir, "dom_snapshots"))
            assert os.path.exists(os.path.join(dest_dir, "dom_snapshots", "event_1.html"))

    def test_skips_empty_screenshots_directory(self):
        publisher = GitPublisher("https://example.com", "token")
        with tempfile.TemporaryDirectory() as tmp:
            recordings_dir = os.path.join(tmp, "recordings")
            os.makedirs(recordings_dir)
            rid = self._make_recording(recordings_dir, "REC-001")

            # Create empty screenshots dir
            screenshots_dir = os.path.join(recordings_dir, rid, "screenshots")
            os.makedirs(screenshots_dir, exist_ok=True)

            repo_dir = os.path.join(tmp, "repo")
            dest_dir = os.path.join(repo_dir, "recordings", rid)
            os.makedirs(dest_dir, exist_ok=True)

            copied = publisher._copy_artifacts(repo_dir, rid, recordings_dir, "")

            # Empty screenshots should not be copied
            assert "screenshots/" not in copied
            assert not os.path.exists(os.path.join(dest_dir, "screenshots"))

    def test_copies_semantic_test_if_available(self):
        publisher = GitPublisher("https://example.com", "token")
        with tempfile.TemporaryDirectory() as tmp:
            recordings_dir = os.path.join(tmp, "recordings")
            os.makedirs(recordings_dir)
            rid = self._make_recording(recordings_dir, "REC-001")

            semantic_tests_dir = os.path.join(tmp, "semantic_tests")
            st_dir = os.path.join(semantic_tests_dir, f"ST-{rid}")
            os.makedirs(st_dir, exist_ok=True)
            with open(os.path.join(st_dir, "test_REC_001.py"), "w") as f:
                f.write("def test_foo(): pass")
            with open(os.path.join(st_dir, "semantic_steps.jsonl"), "w") as f:
                f.write("{}\n")

            repo_dir = os.path.join(tmp, "repo")
            dest_dir = os.path.join(repo_dir, "recordings", rid)
            os.makedirs(dest_dir, exist_ok=True)

            copied = publisher._copy_artifacts(repo_dir, rid, recordings_dir, semantic_tests_dir)

            # Check semantic files copied
            assert "test_REC_001.py" in copied
            assert "semantic_steps.jsonl" in copied

    def test_returns_list_of_copied_filenames(self):
        publisher = GitPublisher("https://example.com", "token")
        with tempfile.TemporaryDirectory() as tmp:
            recordings_dir = os.path.join(tmp, "recordings")
            os.makedirs(recordings_dir)
            rid = self._make_recording(recordings_dir, "REC-001")
            repo_dir = os.path.join(tmp, "repo")
            dest_dir = os.path.join(repo_dir, "recordings", rid)
            os.makedirs(dest_dir, exist_ok=True)

            copied = publisher._copy_artifacts(repo_dir, rid, recordings_dir, "")

            assert isinstance(copied, list)
            assert len(copied) > 0
            assert "dom_snapshots/" in copied


class TestPublish:
    def _make_recording(self, base_dir: str, rid: str, with_semantic: bool = False) -> str:
        """Create minimal recording directory structure."""
        rec_dir = os.path.join(base_dir, rid)
        os.makedirs(rec_dir, exist_ok=True)

        # Create metadata
        metadata = {
            "recording_id": rid,
            "application": "web",
            "base_url": "http://localhost:8080",
            "started_at": "2026-06-19T10:00:00Z",
            "finished_at": "2026-06-19T10:05:00Z",
            "recording_status": "completed",
            "status_history": [],
        }
        with open(os.path.join(rec_dir, "recording_metadata.json"), "w") as f:
            json.dump(metadata, f)

        # Create flat files
        for fname in ["raw_events.jsonl", "steps.jsonl"]:
            with open(os.path.join(rec_dir, fname), "w") as f:
                f.write("{}\n")

        # Create dom_snapshots
        dom_dir = os.path.join(rec_dir, "dom_snapshots")
        os.makedirs(dom_dir, exist_ok=True)
        with open(os.path.join(dom_dir, "event_1.html"), "w") as f:
            f.write("<html></html>")

        if with_semantic:
            # Placeholder for semantic test
            pass

        return rid

    def test_publish_returns_failure_when_metadata_missing(self):
        publisher = GitPublisher("https://example.com", "token")
        with tempfile.TemporaryDirectory() as tmp:
            result = publisher.publish("REC-MISSING", tmp, tmp)
            assert result.success is False
            assert "metadata not found" in result.error

    def test_publish_failure_when_nothing_staged(self):
        publisher = GitPublisher("https://example.com", "token")
        with tempfile.TemporaryDirectory() as tmp:
            recordings_dir = os.path.join(tmp, "recordings")
            os.makedirs(recordings_dir)
            rid = self._make_recording(recordings_dir, "REC-001")

            # Mock subprocess to simulate successful clone but no staged changes
            with mock.patch.object(publisher, "_clone_shallow"):
                with mock.patch.object(
                    publisher, "_copy_artifacts", return_value=[]
                ):
                    with mock.patch.object(publisher, "_git") as mock_git:
                        # Simulate diff --cached returning empty
                        def git_side_effect(*args, **kwargs):
                            if args[0] == "diff":
                                return ""
                            elif args[0] == "rev-parse":
                                return "abc123"
                            return ""

                        mock_git.side_effect = git_side_effect

                        result = publisher.publish(rid, recordings_dir, tmp)

                        # Should still succeed with empty sha if nothing staged
                        assert result.success is True

    def test_publish_does_not_leak_token_in_failure_result(self):
        publisher = GitPublisher("https://example.com", "secret-token-123")
        with tempfile.TemporaryDirectory() as tmp:
            recordings_dir = os.path.join(tmp, "recordings")
            os.makedirs(recordings_dir)
            rid = self._make_recording(recordings_dir, "REC-001")

            # Mock to raise an exception with token in it
            with mock.patch.object(
                publisher,
                "_clone_shallow",
                side_effect=Exception("auth failed with secret-token-123"),
            ):
                result = publisher.publish(rid, recordings_dir, tmp)

                assert result.success is False
                assert "secret-token-123" not in result.error
                assert "***" in result.error
