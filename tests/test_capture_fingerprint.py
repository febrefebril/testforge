"""Capture fingerprint contract.

Pins the H22 followup decision: every new recording embeds a small
identity block so the normalizer can warn when an older recording was
written by an incompatible recorder.

The block lives under `recording_metadata.json["fingerprint"]` and
covers: capture_schema_version, testforge_version,
overlay_inject_sha256, git_head_sha, recorded_at.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from testforge.recorder.capture_fingerprint import (
    CAPTURE_SCHEMA_VERSION,
    compute_fingerprint,
    overlay_inject_sha256,
    verify_fingerprint,
)
from testforge.recorder.recording_session import RecordingSessionManager
from testforge.semantic.recording_normalizer import RecordingNormalizer


class TestFingerprintBlock:
    def test_compute_returns_expected_keys(self):
        fp = compute_fingerprint()
        assert set(fp.keys()) == {
            "capture_schema_version",
            "testforge_version",
            "overlay_inject_sha256",
            "git_head_sha",
            "recorded_at",
        }

    def test_capture_schema_version_is_an_integer(self):
        assert isinstance(CAPTURE_SCHEMA_VERSION, int)
        assert CAPTURE_SCHEMA_VERSION >= 1

    def test_overlay_sha_is_64_hex_chars(self):
        sha = overlay_inject_sha256()
        assert len(sha) == 64
        assert all(c in "0123456789abcdef" for c in sha)

    def test_compute_is_deterministic_between_calls(self):
        a = compute_fingerprint()
        b = compute_fingerprint()
        # recorded_at will differ but the rest should be stable.
        for key in ("capture_schema_version", "overlay_inject_sha256",
                    "git_head_sha", "testforge_version"):
            assert a[key] == b[key], f"{key} drifted between calls"


class TestRecordingSessionEmbedsFingerprint:
    def test_new_recording_metadata_includes_fingerprint(self, tmp_path):
        mgr = RecordingSessionManager(recordings_root=str(tmp_path))
        session = mgr.start(
            recording_id="rec_fingerprint_test",
            application="WebApp",
            base_url="https://example.test",
        )
        meta_path = Path(session.metadata_path)
        assert meta_path.exists()
        metadata = json.loads(meta_path.read_text(encoding="utf-8"))
        assert "fingerprint" in metadata, (
            "RecordingSession must embed `fingerprint` on session start "
            "so future normalizers can detect schema drift."
        )
        fp = metadata["fingerprint"]
        assert fp["capture_schema_version"] == CAPTURE_SCHEMA_VERSION
        assert len(fp["overlay_inject_sha256"]) == 64
        mgr.stop()
        mgr.finalize()

    def test_finalize_preserves_fingerprint(self, tmp_path):
        mgr = RecordingSessionManager(recordings_root=str(tmp_path))
        session = mgr.start("rec_fp_finalize", "WebApp", "https://example.test")
        original_fp = dict(session.fingerprint)
        mgr.stop()
        mgr.finalize()
        meta = json.loads(Path(session.metadata_path).read_text(encoding="utf-8"))
        assert meta["fingerprint"] == original_fp, (
            "Fingerprint must survive stop/finalize unchanged."
        )


class TestVerifyFingerprint:
    def test_recording_with_matching_fingerprint_is_compatible(self):
        current = compute_fingerprint()
        result = verify_fingerprint({"fingerprint": current})
        assert result["compatible"] is True
        assert result["warnings"] == []

    def test_recording_without_fingerprint_flagged_as_legacy(self):
        result = verify_fingerprint({})
        assert result["compatible"] is False
        assert result["recorded"] is None
        assert any("legacy" in w.lower() or "no fingerprint" in w.lower()
                   for w in result["warnings"])

    def test_schema_version_mismatch_emits_warning(self):
        current = compute_fingerprint()
        old = dict(current)
        old["capture_schema_version"] = 0
        result = verify_fingerprint({"fingerprint": old})
        assert any("capture_schema_version" in w for w in result["warnings"])

    def test_overlay_sha_mismatch_emits_warning(self):
        current = compute_fingerprint()
        forged = dict(current)
        forged["overlay_inject_sha256"] = "0" * 64  # not the real sha
        result = verify_fingerprint({"fingerprint": forged})
        assert any("overlay_inject.js" in w for w in result["warnings"])


class TestNormalizerCachesFingerprintCheck:
    def test_normalize_populates_fingerprint_check_on_instance(self, tmp_path):
        # Build a minimal valid recording dir: empty raw_events.jsonl is
        # enough — the normalizer's verify call runs before the parse.
        rec_dir = tmp_path / "rec_legacy"
        rec_dir.mkdir()
        (rec_dir / "raw_events.jsonl").write_text("", encoding="utf-8")
        # No metadata file at all → must be flagged as legacy.
        n = RecordingNormalizer()
        try:
            n.normalize(str(rec_dir))
        except Exception:
            # Empty events may raise downstream; we only care that the
            # fingerprint check ran.
            pass
        assert hasattr(n, "fingerprint_check")
        assert n.fingerprint_check["compatible"] is False
        assert n.fingerprint_check["recorded"] is None

    def test_normalize_marks_matching_recording_compatible(self, tmp_path):
        rec_dir = tmp_path / "rec_current"
        rec_dir.mkdir()
        (rec_dir / "raw_events.jsonl").write_text("", encoding="utf-8")
        (rec_dir / "recording_metadata.json").write_text(
            json.dumps({"fingerprint": compute_fingerprint()}),
            encoding="utf-8",
        )
        n = RecordingNormalizer()
        try:
            n.normalize(str(rec_dir))
        except Exception:
            pass
        assert n.fingerprint_check["compatible"] is True
        assert n.fingerprint_check["warnings"] == []
