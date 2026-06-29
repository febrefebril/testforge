"""B32 — compile autodetects sibling recording when target dir is empty.

The recorder silently suffix-bumps the recording name when the chosen
name already exists (e.g. `test-pos-hotfix11` → `test-pos-hotfix11_3`
on the third attempt). User keeps typing the original name and runs
`testforge compile --check recordings/test-pos-hotfix11`, which hits
an empty directory and dies with `raw_events.jsonl nao encontrado`.

Fix: when the requested dir has no raw_events.jsonl, look for the
most-recent sibling `<rec_id>_<n>` that actually has one and switch.
A separate visible WARN on `testforge record` also surfaces the
bumped name so the user can copy it.

This file pins the fallback logic via a small helper that mirrors
the behaviour added to cmd_compile.
"""
from __future__ import annotations

import glob
import os
from pathlib import Path


def _find_populated_sibling(rec_root: Path, rec_id: str) -> str | None:
    """Mirror of the cmd_compile fallback. Returns the sibling
    recording_id with raw_events.jsonl, or None."""
    siblings = sorted(
        glob.glob(str(rec_root / f"{rec_id}_*")),
        key=lambda p: os.path.getmtime(p) if os.path.isdir(p) else 0,
        reverse=True,
    )
    for sibling in siblings:
        if os.path.isfile(os.path.join(sibling, "raw_events.jsonl")):
            return os.path.basename(sibling)
    return None


def _mkdir(p: Path) -> Path:
    p.mkdir(parents=True, exist_ok=True)
    return p


def _touch(p: Path, content: str = "") -> Path:
    p.write_text(content, encoding="utf-8")
    return p


class TestSiblingFallback:
    def test_picks_most_recent_populated_sibling(self, tmp_path):
        rec_root = tmp_path / "recordings"
        rec_root.mkdir()
        _mkdir(rec_root / "x")           # empty original
        sib2 = _mkdir(rec_root / "x_2")  # empty
        sib3 = _mkdir(rec_root / "x_3")  # has raw_events
        _touch(sib3 / "raw_events.jsonl", "")
        chosen = _find_populated_sibling(rec_root, "x")
        assert chosen == "x_3"

    def test_returns_none_when_no_populated_siblings(self, tmp_path):
        rec_root = tmp_path / "recordings"
        rec_root.mkdir()
        _mkdir(rec_root / "y")
        _mkdir(rec_root / "y_2")
        _mkdir(rec_root / "y_3")
        assert _find_populated_sibling(rec_root, "y") is None

    def test_skips_siblings_without_raw_events(self, tmp_path):
        rec_root = tmp_path / "recordings"
        rec_root.mkdir()
        _mkdir(rec_root / "z")
        sib2 = _mkdir(rec_root / "z_2")
        sib3 = _mkdir(rec_root / "z_3")  # this is the newest
        # Only z_2 has raw_events.
        _touch(sib2 / "raw_events.jsonl", "")
        chosen = _find_populated_sibling(rec_root, "z")
        assert chosen == "z_2"

    def test_ignores_unrelated_dirs_with_prefix_only(self, tmp_path):
        """rec_id='foo' must NOT match rec_id='foobar_1'."""
        rec_root = tmp_path / "recordings"
        rec_root.mkdir()
        _mkdir(rec_root / "foo")
        unrelated = _mkdir(rec_root / "foobar_1")
        _touch(unrelated / "raw_events.jsonl", "")
        assert _find_populated_sibling(rec_root, "foo") is None
