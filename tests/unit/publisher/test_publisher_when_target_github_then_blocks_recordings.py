"""Bloco 0.6: publisher target=github filtra artefatos de gravacao."""
import pytest


@pytest.mark.unit
class TestPublisherWhenTargetGithubThenBlocksRecordings:
    def test_recordings_in_blocklist(self):
        from testforge.publisher.git_publisher import _GITHUB_BLOCKLIST_GLOBS
        assert "recordings/**" in _GITHUB_BLOCKLIST_GLOBS
        assert "**/raw_events.jsonl" in _GITHUB_BLOCKLIST_GLOBS
        assert "**/keystroke_buffer.jsonl" in _GITHUB_BLOCKLIST_GLOBS
        assert "**/dom_snapshots/**" in _GITHUB_BLOCKLIST_GLOBS
        assert "**/ax_snapshots/**" in _GITHUB_BLOCKLIST_GLOBS

    def test_env_and_secrets_blocked(self):
        from testforge.publisher.git_publisher import _GITHUB_BLOCKLIST_GLOBS
        assert ".env" in _GITHUB_BLOCKLIST_GLOBS
        assert ".testforge/secrets/**" in _GITHUB_BLOCKLIST_GLOBS

    def test_scan_flags_raw_events(self):
        from testforge.publisher.git_publisher import GitPublisher, PublishTarget
        ok, blocked = GitPublisher._scan_before_publish(
            ["src/testforge/foo.py", "recordings/x/raw_events.jsonl"],
            PublishTarget.GITHUB,
        )
        assert "src/testforge/foo.py" in ok
        assert "recordings/x/raw_events.jsonl" in blocked

    def test_scan_flags_multiple_artifact_types(self):
        from testforge.publisher.git_publisher import GitPublisher, PublishTarget
        files = [
            "src/foo.py",
            "docs/bar.md",
            "recordings/x/raw_events.jsonl",
            "recordings/x/keystroke_buffer.jsonl",
            "recordings/x/dom_snapshots/evt_001.html",
            "PLATAFORMA DES/system/raw_events.jsonl",  # rooted at CWD
            ".env",
            ".testforge/secrets/pat.txt",
        ]
        ok, blocked = GitPublisher._scan_before_publish(files, PublishTarget.GITHUB)
        assert "src/foo.py" in ok
        assert "docs/bar.md" in ok
        # all sensitive should be flagged
        for f in [
            "recordings/x/raw_events.jsonl",
            "recordings/x/keystroke_buffer.jsonl",
            "recordings/x/dom_snapshots/evt_001.html",
            ".env",
            ".testforge/secrets/pat.txt",
        ]:
            assert f in blocked, f"expected {f} blocked for github target"

    def test_local_target_no_filter(self):
        from testforge.publisher.git_publisher import GitPublisher, PublishTarget
        files = ["recordings/x/raw_events.jsonl", "src/foo.py", ".env"]
        ok, blocked = GitPublisher._scan_before_publish(files, PublishTarget.LOCAL)
        assert set(ok) == set(files)
        assert blocked == []

    def test_empty_input_returns_empty(self):
        from testforge.publisher.git_publisher import GitPublisher, PublishTarget
        ok, blocked = GitPublisher._scan_before_publish([], PublishTarget.GITHUB)
        assert ok == []
        assert blocked == []
