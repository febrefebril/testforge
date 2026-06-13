"""Testes do MetricsRepository."""
from testforge.metrics import MetricsRepository, MetricsSnapshot


class TestMetrics:
    def test_empty_snapshot(self):
        s = MetricsSnapshot()
        assert s.total_runs == 0
        assert s.false_heal_rate == 0.0
        assert s.precision == 1.0

    def test_record_run_no_healing(self):
        repo = MetricsRepository()
        repo.record_run(oracle_passed=2, oracle_failed=0)
        assert repo.snapshot.total_runs == 1
        assert repo.snapshot.total_healings == 0
        assert repo.snapshot.oracle_passed == 2

    def test_record_healing_true(self):
        repo = MetricsRepository()
        repo.record_run(healed=True, false_heal=False, oracle_passed=1)
        assert repo.snapshot.true_heals == 1
        assert repo.snapshot.false_heals == 0
        assert repo.snapshot.precision == 1.0

    def test_record_healing_false(self):
        repo = MetricsRepository()
        repo.record_run(healed=True, false_heal=True)
        repo.record_run(healed=True, false_heal=False)
        assert repo.snapshot.total_healings == 2
        assert repo.snapshot.precision == 0.5
        assert repo.snapshot.false_heal_rate == 0.5

    def test_llm_escalation(self):
        repo = MetricsRepository()
        repo.record_run(llm_used=True)
        repo.record_run(llm_used=False)
        assert repo.snapshot.llm_escalations == 1
        assert repo.snapshot.llm_rate == 0.5

    def test_summary(self):
        repo = MetricsRepository()
        repo.record_run(healed=True, false_heal=False, oracle_passed=2)
        s = repo.summary()
        assert "True heals" in s
        assert "100.00%" in s

    def test_to_dict(self):
        repo = MetricsRepository()
        repo.record_run(oracle_passed=1)
        d = repo.snapshot.to_dict()
        assert d["total_runs"] == 1
        assert "false_heal_rate" in d
