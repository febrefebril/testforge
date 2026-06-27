"""H22b — dedupe diagnostics on RecordingNormalizer.

Background: see .planning/spikes/SPIKE-keyboard-type-mask.md (H22
section) and the 2026-06-27 H22a entry in DECISIONS-LOG.md.

H22a re-ranked the source priority table so `final_state` outranks
`setter_hook`. H22b adds per-call telemetry that counts how often each
source actually beats another. The signal feeds the H22c decision: if
`setter_hook` is dominated by `final_state` in every recording, the
prototype hook (and its companion value_mutations.jsonl pipeline) can
be deleted.

This file pins:
1. The stats structure exists on each instance.
2. Stats reset between `normalize()` calls.
3. The `setter_hook_dominated_by_final_state` counter increments when
   both sources fire for the same field and final_state wins.
4. The `setter_hook_uncontested` counter increments when setter_hook
   produces a value with no other source for that key — this is the
   remaining justification for keeping the hook.
"""
from __future__ import annotations

from testforge.semantic.recording_normalizer import RecordingNormalizer


def _make_entry(key: str, value: str, source: str) -> dict:
    return {
        "field_key": key,
        "value": value,
        "intention": f"fill {key} ({source})",
        "identifiers": {"id": key},
        "source": source,
        "step_index": 0,
        "fingerprint": f"input#{key}[name=]",
    }


class TestStatsShape:
    def test_fresh_stats_has_expected_keys(self):
        n = RecordingNormalizer()
        assert set(n.ir_dedupe_stats.keys()) == {
            "loser_counts",
            "winner_counts",
            "setter_hook_dominated_by_final_state",
            "final_state_uncontested",
            "setter_hook_uncontested",
        }

    def test_stats_are_per_instance(self):
        """Two normalizers should not share dedupe stats — H22b uses
        instance state precisely to avoid the class-level mutable-state
        bug that bit us in earlier P2/P3 regressions."""
        a = RecordingNormalizer()
        b = RecordingNormalizer()
        a.ir_dedupe_stats["loser_counts"]["setter_hook"] = 99
        assert b.ir_dedupe_stats["loser_counts"].get("setter_hook", 0) == 0


class TestDedupeAccountsWinsAndLosses:
    def test_final_state_beats_setter_hook_increments_counter(self):
        n = RecordingNormalizer()
        entries = [
            _make_entry("valor", "1,00", "setter_hook"),
            _make_entry("valor", "10.000,00", "final_state"),
        ]
        out = n._ir_dedupe_entries(entries)
        assert len(out) == 1
        assert out[0]["source"] == "final_state"
        assert n.ir_dedupe_stats["setter_hook_dominated_by_final_state"] == 1
        assert n.ir_dedupe_stats["loser_counts"].get("setter_hook") == 1
        assert n.ir_dedupe_stats["winner_counts"].get("final_state") == 1

    def test_setter_hook_uncontested_when_no_competing_source(self):
        """If setter_hook is the only source that produced a value for a
        key, the hook is still load-bearing. This counter tracks how
        often that happens so H22c (delete _hookValue) can be made
        evidence-based."""
        n = RecordingNormalizer()
        entries = [
            _make_entry("only_setter_field", "1,00", "setter_hook"),
        ]
        n._ir_dedupe_entries(entries)
        assert n.ir_dedupe_stats["setter_hook_uncontested"] == 1
        assert n.ir_dedupe_stats["final_state_uncontested"] == 0

    def test_final_state_uncontested_when_no_competing_source(self):
        n = RecordingNormalizer()
        entries = [
            _make_entry("only_final_field", "10,00", "final_state"),
        ]
        n._ir_dedupe_entries(entries)
        assert n.ir_dedupe_stats["final_state_uncontested"] == 1
        assert n.ir_dedupe_stats["setter_hook_uncontested"] == 0

    def test_setter_hook_beats_lower_source(self):
        """The new ordering must still let setter_hook beat
        network_payload / polling / snapshot_diff. Pin it so H22a's
        promotion doesn't accidentally invert those too."""
        n = RecordingNormalizer()
        entries = [
            _make_entry("field", "polling_val", "polling"),
            _make_entry("field", "setter_val", "setter_hook"),
        ]
        out = n._ir_dedupe_entries(entries)
        assert len(out) == 1
        assert out[0]["source"] == "setter_hook"
        assert n.ir_dedupe_stats["loser_counts"].get("polling") == 1


class TestStatsResetPerNormalize:
    def test_stats_reset_on_normalize_call(self, tmp_path):
        """A second normalize() invocation should not carry stats from
        the first. This mirrors the lifecycle of CLI invocations where
        the normalizer instance can be reused across recordings."""
        n = RecordingNormalizer()
        # Manually pollute stats as if a prior call had run.
        n.ir_dedupe_stats["setter_hook_dominated_by_final_state"] = 5
        n.ir_dedupe_stats["loser_counts"]["setter_hook"] = 10
        # Run normalize on an empty recording dir.
        # An empty dir produces an empty STC but should still reset
        # stats — that's the H22b contract.
        try:
            n.normalize(str(tmp_path))
        except Exception:
            # Empty dirs may raise on missing raw_events.jsonl; that's
            # fine for this test — the stats reset happens before any
            # file IO.
            pass
        assert n.ir_dedupe_stats["setter_hook_dominated_by_final_state"] == 0
        assert n.ir_dedupe_stats["loser_counts"] == {}
