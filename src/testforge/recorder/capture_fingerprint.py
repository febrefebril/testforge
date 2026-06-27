"""Capture fingerprint for recordings (2026-06-27, H22 followup).

Embeds a small block into every new recording so we can tell, later,
whether the recording was produced by a compatible recorder. Saves us
from the situation where a hotfix to the normalizer claims a "bug" in
a recording that was actually written by a pre-hotfix recorder with a
different capture schema.

Block shape (written into `recording_metadata.json` under "fingerprint"):

    {
        "capture_schema_version": 1,
        "testforge_version": "0.x.y",
        "overlay_inject_sha256": "<64 hex>",
        "git_head_sha": "<40 hex or empty>",
        "recorded_at": "2026-06-27T22:10:00+00:00"
    }

When the normalizer reads an old recording with `capture_schema_version`
< current, it logs a single WARN and tags the report. Existing
recordings without a fingerprint are treated as `version=0` ("legacy
pre-fingerprint").

Bump `CAPTURE_SCHEMA_VERSION` when the overlay JS or
`_persist_raw_event` flow changes a field that affects how
`raw_events.jsonl`, `value_mutations.jsonl`, `field_snapshots.jsonl`,
`final_state_snapshot.json`, or `steps.jsonl` are written. Do NOT bump
for changes that only affect timing, retry strategy, or perf.
"""
from __future__ import annotations

import hashlib
import logging
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


# Bump policy: when the WRITE format of a recording artefact changes.
#   v0 — implicit legacy marker for recordings that pre-date this file.
#        Anything written before 2026-06-27 22:00 UTC has no fingerprint
#        block and is treated as v0.
#   v1 — first explicit fingerprint. Capture format unchanged from
#        post-hotfix-14 recorder. Establishes the baseline.
CAPTURE_SCHEMA_VERSION = 1


def _overlay_path() -> Path:
    return Path(__file__).resolve().parent / "overlay_inject.js"


def overlay_inject_sha256() -> str:
    path = _overlay_path()
    if not path.exists():
        return ""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _git_head_sha(repo_root: Optional[Path] = None) -> str:
    if repo_root is None:
        # src/testforge/recorder/capture_fingerprint.py → repo root is parents[3]
        repo_root = Path(__file__).resolve().parents[3]
    try:
        result = subprocess.run(
            ["git", "-C", str(repo_root), "rev-parse", "HEAD"],
            capture_output=True, text=True, timeout=2, check=False,
        )
        sha = (result.stdout or "").strip()
        # Only return a clean 40-char hex; never write partial output.
        if len(sha) == 40 and all(c in "0123456789abcdef" for c in sha):
            return sha
    except Exception:
        pass
    return ""


def _testforge_version() -> str:
    try:
        from testforge import __version__
        return str(__version__)
    except Exception:
        pass
    try:
        from importlib.metadata import version
        return version("testforge")
    except Exception:
        return ""


def compute_fingerprint() -> dict:
    """Return the fingerprint block to embed in recording_metadata.json."""
    return {
        "capture_schema_version": CAPTURE_SCHEMA_VERSION,
        "testforge_version": _testforge_version(),
        "overlay_inject_sha256": overlay_inject_sha256(),
        "git_head_sha": _git_head_sha(),
        "recorded_at": datetime.now(timezone.utc).isoformat(),
    }


def verify_fingerprint(metadata: dict) -> dict:
    """Compare a recording's fingerprint against the current recorder.

    Returns a dict the caller can log / surface:

        {
            "compatible": bool,
            "warnings": [str],
            "recorded": dict | None,    # fingerprint block from the metadata
            "current": dict,            # current recorder fingerprint
        }
    """
    current = compute_fingerprint()
    recorded = (metadata or {}).get("fingerprint")
    warnings: list[str] = []

    if not recorded:
        # Legacy pre-fingerprint recording. Treat as v0.
        warnings.append(
            "recording has no fingerprint block — treating as legacy "
            "v0 (pre-2026-06-27). It may have been produced by a "
            "recorder with a different capture schema. Cross-check "
            "started_at against the recorder hotfix history before "
            "trusting normalizer output."
        )
        return {
            "compatible": False,
            "warnings": warnings,
            "recorded": None,
            "current": current,
        }

    recorded_version = recorded.get("capture_schema_version", 0)
    current_version = current["capture_schema_version"]
    if recorded_version != current_version:
        warnings.append(
            f"capture_schema_version mismatch: recording={recorded_version}, "
            f"current={current_version}. The recorder write format has "
            "changed since this recording was produced. Treat any "
            "missing-field claims with skepticism."
        )

    recorded_sha = (recorded.get("overlay_inject_sha256") or "").lower()
    current_sha = (current["overlay_inject_sha256"] or "").lower()
    if recorded_sha and current_sha and recorded_sha != current_sha:
        warnings.append(
            f"overlay_inject.js changed since recording (recorded "
            f"sha={recorded_sha[:12]}..., current={current_sha[:12]}...). "
            "Capture behaviour may differ."
        )

    return {
        "compatible": not warnings,
        "warnings": warnings,
        "recorded": recorded,
        "current": current,
    }
