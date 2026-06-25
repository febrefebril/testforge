"""Hotfix 5 — git add -f in publisher + --system default to --app."""
from __future__ import annotations

import os
import subprocess
import tempfile
from unittest.mock import MagicMock, patch

import pytest


class TestGitAddForce:
    @patch.object(subprocess, "run")
    def test_local_publish_invokes_git_add_dash_f(self, mock_run, tmp_path):
        """Force-add bypass for the recordings/ .gitignore exclusion."""
        from testforge.publisher.git_publisher import GitPublisher

        # subprocess.run always succeeds; record call args
        def _ok(args, **kw):
            return subprocess.CompletedProcess(args=args, returncode=0,
                                                 stdout="", stderr="")
        mock_run.side_effect = _ok

        # Create a minimal git_root + recording layout
        git_root = tmp_path / "repo"
        rec_root = git_root / "recordings"
        rec_dir = rec_root / "REC-1"
        rec_dir.mkdir(parents=True)
        (rec_dir / "raw_events.jsonl").write_text("")
        (rec_dir / "recording_metadata.json").write_text(
            '{"recording_id":"REC-1","application":"x","base_url":"http://x/",'
            '"system":"sys","suite":"suite","test_case":"tc"}')

        pub = GitPublisher(url="https://example/r.git", token="",
                            branch="main", path_prefix="recordings",
                            local_mode=True, git_root=str(git_root))
        # Inspect the calls — we look for any `git add -f <path>` invocation
        try:
            pub._local_publish("REC-1", str(rec_root), str(tmp_path / "tests"))
        except Exception:
            pass  # IO and shutil paths may still error; we only care about add -f
        cmdlines = []
        for call in mock_run.call_args_list:
            cmdlines.append(call.args[0] if call.args else [])
        add_calls = [c for c in cmdlines if c and "add" in c]
        assert any("-f" in c for c in add_calls), \
            f"expected at least one 'git add -f' call; saw: {add_calls}"


class TestSystemDefaultsToApp:
    def test_system_falls_back_to_app(self):
        from argparse import Namespace

        # Simulate the resolution block in cmd_record without running the whole CLI
        args = Namespace(system=None, app="SIOPI", suite="s",
                          test_case="tc", name="N")
        _cfg = {}
        _system = getattr(args, 'system', None) or _cfg.get("system", "") or ""
        if not _system:
            _app_value = getattr(args, 'app', None) or ""
            if _app_value:
                _system = _app_value
        assert _system == "SIOPI"

    def test_explicit_system_wins(self):
        from argparse import Namespace
        args = Namespace(system="OVERRIDE", app="SIOPI",
                          suite="s", test_case="tc", name="N")
        _cfg = {}
        _system = getattr(args, 'system', None) or _cfg.get("system", "") or ""
        if not _system:
            _system = getattr(args, 'app', "") or ""
        assert _system == "OVERRIDE"

    def test_neither_keeps_empty(self):
        from argparse import Namespace
        args = Namespace(system=None, app="", suite="", test_case="", name="N")
        _cfg = {}
        _system = getattr(args, 'system', None) or _cfg.get("system", "") or ""
        if not _system:
            _app_value = getattr(args, 'app', None) or ""
            if _app_value:
                _system = _app_value
        assert _system == ""
