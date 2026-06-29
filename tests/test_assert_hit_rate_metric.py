"""TestForge — assert_hit_rate metric (Sprint 3 of run decommission plan).

Why: intermediate steps can heal to the wrong screen and still count as
healing_success. What matters for the pilot is whether the assert that
carries the user's recorded expectation was reached. assert_hit_rate
isolates that signal:

    assert_hit_rate = asserts_validated_in_run / total_asserts_in_script

Asserts count as "hit" when their step status is one of:
  passed, healed_validated, shadow_healed
(anything else — healing_rejected, failed, blocked, skipped — counts
as a miss).
"""
from __future__ import annotations
from unittest.mock import MagicMock

import pytest

from testforge.metrics.metrics_repository import MetricsRepository, MetricsSnapshot
from testforge.runner.incremental_runner import IncrementalRunner
from testforge.runner.step_result import IncrementalStepResult


class TestSnapshotAssertHitRate:
    def test_zero_when_no_asserts(self):
        s = MetricsSnapshot()
        assert s.assert_hit_rate == 0.0
        assert s.asserts_total == 0
        assert s.asserts_hit == 0

    def test_one_when_all_asserts_hit(self):
        s = MetricsSnapshot(asserts_total=3, asserts_hit=3)
        assert s.assert_hit_rate == 1.0

    def test_partial_rate(self):
        s = MetricsSnapshot(asserts_total=4, asserts_hit=1)
        assert s.assert_hit_rate == 0.25

    def test_to_dict_includes_assert_fields(self):
        s = MetricsSnapshot(asserts_total=4, asserts_hit=3)
        d = s.to_dict()
        assert d["asserts_total"] == 4
        assert d["asserts_hit"] == 3
        assert d["assert_hit_rate"] == 0.75


class TestRepositoryRecordAssert:
    def test_record_hit_increments_both_counters(self):
        repo = MetricsRepository()
        repo.record_assert(hit=True)
        assert repo.snapshot.asserts_total == 1
        assert repo.snapshot.asserts_hit == 1

    def test_record_miss_increments_only_total(self):
        repo = MetricsRepository()
        repo.record_assert(hit=False)
        assert repo.snapshot.asserts_total == 1
        assert repo.snapshot.asserts_hit == 0

    def test_mixed_record_calls_aggregate(self):
        repo = MetricsRepository()
        for hit in [True, True, False, True, False]:
            repo.record_assert(hit=hit)
        assert repo.snapshot.asserts_total == 5
        assert repo.snapshot.asserts_hit == 3
        assert repo.snapshot.assert_hit_rate == 0.6

    def test_summary_displays_assert_hit_rate(self):
        repo = MetricsRepository()
        repo.record_assert(hit=True)
        repo.record_assert(hit=False)
        out = repo.summary(show_per_step=True)
        assert "Assert hit rate:" in out
        assert "Asserts no script:" in out
        assert "50.00%" in out


class TestRunnerWiresAssertsToMetrics:
    def _make_result(self, step_num, action, status):
        return IncrementalStepResult(
            step_num=step_num,
            action=action,
            status=status,
        )

    def _make_runner_with_results(self, results, with_metrics=True):
        r = IncrementalRunner.__new__(IncrementalRunner)
        r.step_results = results
        r.metrics = MetricsRepository() if with_metrics else None
        return r

    def test_compute_totals_counts_asserts(self):
        results = [
            self._make_result(1, "click", "passed"),
            self._make_result(2, "assert", "passed"),
            self._make_result(3, "click", "healed_validated"),
            self._make_result(4, "assert", "healing_rejected"),
            self._make_result(5, "assert", "healed_validated"),
        ]
        r = self._make_runner_with_results(results)
        totals = r._compute_totals()
        assert totals["asserts_total"] == 3
        assert totals["asserts_hit"] == 2

    def test_compute_totals_pipes_to_metrics(self):
        results = [
            self._make_result(1, "assert", "passed"),
            self._make_result(2, "assert", "healed_validated"),
            self._make_result(3, "assert", "healing_rejected"),
        ]
        r = self._make_runner_with_results(results)
        r._compute_totals()
        assert r.metrics.snapshot.asserts_total == 3
        assert r.metrics.snapshot.asserts_hit == 2
        assert abs(r.metrics.snapshot.assert_hit_rate - 2/3) < 1e-6

    def test_compute_totals_handles_no_metrics(self):
        results = [self._make_result(1, "assert", "passed")]
        r = self._make_runner_with_results(results, with_metrics=False)
        totals = r._compute_totals()
        assert totals["asserts_total"] == 1
        assert totals["asserts_hit"] == 1

    def test_assert_failed_status_counts_as_miss(self):
        results = [
            self._make_result(1, "assert", "failed"),
            self._make_result(2, "assert", "blocked"),
            self._make_result(3, "assert", "skipped"),
        ]
        r = self._make_runner_with_results(results)
        r._compute_totals()
        assert r.metrics.snapshot.asserts_total == 3
        assert r.metrics.snapshot.asserts_hit == 0

    def test_shadow_healed_assert_counts_as_hit(self):
        results = [self._make_result(1, "assert", "shadow_healed")]
        r = self._make_runner_with_results(results)
        r._compute_totals()
        assert r.metrics.snapshot.asserts_hit == 1
