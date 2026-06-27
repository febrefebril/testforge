"""H22a — source priority re-rank after the Material currencymask spike.

Background: see .planning/spikes/SPIKE-keyboard-type-mask.md (H22 section)
and the 2026-06-27 H22 entry in .planning/DECISIONS-LOG.md.

The spike showed that `value_mutations.jsonl` (source=`setter_hook`) only
catches mask-driven writes that delegate to the prototype `value` setter.
For ng2-currency-mask-style instance overrides (and for real keyboard
typing on plain inputs) the hook captures nothing. `final_state_snapshot`
reads `el.value` via the canonical instance getter, so it survives every
mask pattern that displays a value on screen.

Decision: promote `final_state` above `setter_hook` in the priority table.

This file pins:
1. The new ordering (so a future refactor cannot silently reverse it).
2. The merge behaviour when both sources have a value for the same
   physical field — `final_state` must win.
3. The single-source-of-truth invariant (only `IR_SOURCE_PRIORITY`
   should drive the priority).
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from testforge.semantic.recording_normalizer import RecordingNormalizer
from testforge.semantic.model import (
    LocatorCandidate,
    SemanticAction,
    SemanticTarget,
)


# ---- 1. Ordering invariant -------------------------------------------------


class TestIR_SOURCE_PRIORITY_ranking:
    def test_final_state_above_setter_hook(self):
        """H22a: final_state must outrank setter_hook because setter_hook
        misses the instance-override and plain-typing failure modes."""
        p = RecordingNormalizer.IR_SOURCE_PRIORITY
        assert p["final_state"] > p["setter_hook"], (
            "final_state must outrank setter_hook (H22a). The setter hook "
            "is structurally insufficient for masks that don't delegate "
            "to the prototype setter. See SPIKE-keyboard-type-mask.md."
        )

    def test_form_values_remains_top(self):
        p = RecordingNormalizer.IR_SOURCE_PRIORITY
        for other in ("fill_event", "final_state", "setter_hook",
                      "snapshot_diff", "network_payload",
                      "polling", "missing_fill"):
            assert p["form_values"] > p[other], (
                f"form_values must outrank {other}; it is the only source "
                "that reflects what the browser actually submitted."
            )

    def test_fill_event_above_final_state(self):
        """fill_event represents an explicit user action captured at the
        right moment; final_state is a session-end snapshot. fill_event
        should still win when present."""
        p = RecordingNormalizer.IR_SOURCE_PRIORITY
        assert p["fill_event"] > p["final_state"]

    def test_missing_fill_remains_bottom(self):
        p = RecordingNormalizer.IR_SOURCE_PRIORITY
        for other in [k for k in p if k != "missing_fill"]:
            assert p["missing_fill"] < p[other], (
                f"missing_fill must rank below {other} so any real source "
                "can replace a placeholder."
            )

    def test_no_collisions(self):
        """Distinct sources must have distinct priority numbers — ties
        in `_ir_dedupe_entries` fall back to a value-length comparison,
        which is fragile."""
        p = RecordingNormalizer.IR_SOURCE_PRIORITY
        assert len(set(p.values())) == len(p), (
            "Duplicate priority values in IR_SOURCE_PRIORITY: " + repr(p)
        )


# ---- 2. Merge behaviour (integration) --------------------------------------


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    with open(path, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")


def _write_json(path: Path, payload: dict) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f)


class TestFinalStateBeatsSetterHookOnMerge:
    """Pin H22a behaviour: when both sources fire for the same physical
    field, final_state's value must be the one stored in field_values."""

    def test_final_state_wins_when_both_sources_present(self, tmp_path):
        # value_mutations.jsonl — setter_hook source
        _write_jsonl(tmp_path / "value_mutations.jsonl", [
            {
                "type": "value_mutation",
                "timestamp": "2026-06-27T10:00:00Z",
                "fingerprint": "input#mat-input-1[name=]",
                "value": "1,00",  # stale mid-typing snapshot
            },
            {
                "type": "value_mutation",
                "timestamp": "2026-06-27T10:00:01Z",
                "fingerprint": "input#mat-input-1[name=]",
                "value": "10,00",  # also stale; mask kept reformatting
            },
        ])
        # final_state_snapshot.json — final_state source, ground truth
        _write_json(tmp_path / "final_state_snapshot.json", {
            "reason": "session_end",
            "timestamp": "2026-06-27T10:05:00Z",
            "url": "https://example.test/calc",
            "page_title": "Calc",
            "fields": [
                {
                    "fingerprint": "input#mat-input-1[name=]",
                    "identifiers": {
                        "id": "mat-input-1",
                        "name": None,
                        "label": "Valor do imóvel *",
                        "placeholder": "0,00",
                        "aria-label": None,
                    },
                    "tag": "input",
                    "type": "text",
                    "value": "10.000,00",  # canonical formatted value
                    "checked": None,
                    "visibility": "visible",
                    "enabled": True,
                },
            ],
        })

        target = SemanticTarget(
            accessible_name="Valor do imóvel *",
            placeholder="0,00",
            element_id="mat-input-1",
            tag="input",
            candidates=[LocatorCandidate(
                strategy="css", score=1.0,
                selector="input#mat-input-1",
            )],
        )
        step = SemanticAction(action="click", target=target)

        n = RecordingNormalizer()
        entries = n._ir_all(str(tmp_path), [step])
        # Find the entry that points at our masked input.
        candidates = [
            e for e in entries
            if e.get("identifiers", {}).get("id") == "mat-input-1"
            or "mat-input-1" in e.get("fingerprint", "")
            or "valor" in e.get("field_key", "").lower()
        ]
        assert candidates, (
            f"_ir_all dropped both sources for the masked input. Got: {entries}"
        )

        # After dedup, the winner for this physical field must be final_state.
        winner = n._ir_dedupe_entries(candidates)
        assert len(winner) >= 1
        chosen = winner[0]
        assert chosen["source"] == "final_state", (
            f"setter_hook ({chosen.get('value')!r}) beat final_state — "
            f"H22a regression. Winner: {chosen}"
        )
        assert chosen["value"] == "10.000,00", (
            f"Wrong value picked: {chosen.get('value')!r}"
        )


# ---- 3. Single-source-of-truth invariant -----------------------------------


class TestNoInlinePriorityMaps:
    """Pin: no inline copy of the priority map should survive in
    recording_normalizer.py. H22a unified them to `IR_SOURCE_PRIORITY`.

    A future PR that copies the table inline (a common
    refactor-without-thinking pattern) would silently re-fork the
    rankings. This invariant catches that at CI time.
    """

    def test_no_competing_priority_dicts_in_normalizer(self):
        src = Path(
            "src/testforge/semantic/recording_normalizer.py"
        ).read_text(encoding="utf-8")
        # The literal `"form_values": 100` paired with `"setter_hook":`
        # in the SAME block is the inline-copy signature we removed.
        # Allow exactly one occurrence (the IR_SOURCE_PRIORITY constant).
        marker = '"form_values": 100'
        count = src.count(marker)
        assert count == 1, (
            f"Expected exactly 1 occurrence of {marker!r} (the "
            f"IR_SOURCE_PRIORITY constant). Found {count}. A new inline "
            "copy of the priority map was added — fold it into "
            "RecordingNormalizer.IR_SOURCE_PRIORITY instead."
        )
