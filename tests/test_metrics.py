"""Testes do MetricsRepository — per-step metrics (BUG-011)."""
from testforge.metrics import MetricsRepository, MetricsSnapshot, StepOutcome


class TestMetrics:
    """Testes de metricas globais (existentes)."""

    def test_empty_snapshot(self):
        s = MetricsSnapshot()
        assert s.total_runs == 0
        assert s.false_heal_rate == 0.0
        assert s.precision == 1.0
        # BUG-011: per-step defaults
        assert s.falhas_detectadas == 0
        assert s.healings_tentados == 0
        assert s.aplicados == 0
        assert s.validados == 0
        assert s.rejeitados == 0

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
        # BUG-011: per-step fields in dict
        assert "falhas_detectadas" in d
        assert "healings_tentados" in d
        assert "aplicados" in d
        assert "validados" in d
        assert "rejeitados" in d
        assert "healing_success_rate" in d


class TestPerStepMetrics:
    """BUG-011: Per-step metricas individuais."""

    def test_record_step_failure_detected(self):
        repo = MetricsRepository()
        repo.record_step(StepOutcome.FAILURE_DETECTED, step_num=1, action="click")
        assert repo.snapshot.falhas_detectadas == 1
        assert repo.snapshot.healings_tentados == 0
        assert repo.snapshot.aplicados == 0

    def test_record_step_healing_attempted(self):
        repo = MetricsRepository()
        repo.record_step(StepOutcome.HEALING_ATTEMPTED, step_num=1, action="fill",
                         family_code="FAM-01", healing_layer="L2",
                         selector="#campo-nome")
        assert repo.snapshot.healings_tentados == 1
        assert len(repo.step_history) == 1
        entry = repo.step_history[0]
        assert entry["step_num"] == 1
        assert entry["action"] == "fill"
        assert entry["outcome"] == "healing_tentado"
        assert entry["family_code"] == "FAM-01"
        assert entry["healing_layer"] == "L2"

    def test_record_step_healing_applied(self):
        repo = MetricsRepository()
        repo.record_step(StepOutcome.HEALING_APPLIED, step_num=2, action="click",
                         healing_layer="L1", selector="button:has-text('Enviar')")
        assert repo.snapshot.aplicados == 1

    def test_record_step_oracle_validated(self):
        repo = MetricsRepository()
        repo.record_step(StepOutcome.ORACLE_VALIDATED, step_num=1,
                         action="oracle_visual_dom", healing_layer="L3")
        assert repo.snapshot.validados == 1

    def test_record_step_healing_rejected(self):
        repo = MetricsRepository()
        repo.record_step(StepOutcome.HEALING_REJECTED, step_num=1, action="click",
                         family_code="FAM-01", healing_layer="L0")
        assert repo.snapshot.rejeitados == 1

    def test_multiple_step_outcomes(self):
        """Simula fluxo completo: falha → tentativa → aplicado."""
        repo = MetricsRepository()
        repo.record_step(StepOutcome.FAILURE_DETECTED, step_num=1, action="click")
        repo.record_step(StepOutcome.HEALING_ATTEMPTED, step_num=1, action="click",
                         family_code="FAM-01", healing_layer="L2")
        repo.record_step(StepOutcome.HEALING_APPLIED, step_num=1, action="click",
                         healing_layer="L2")
        repo.record_step(StepOutcome.ORACLE_VALIDATED, step_num=1, action="oracle_visual_dom")
        assert repo.snapshot.falhas_detectadas == 1
        assert repo.snapshot.healings_tentados == 1
        assert repo.snapshot.aplicados == 1
        assert repo.snapshot.validados == 1
        assert repo.snapshot.rejeitados == 0
        assert len(repo.step_history) == 4

    def test_step_with_failure_and_rejection(self):
        """Simula fluxo: falha → tentativa → rejeitado."""
        repo = MetricsRepository()
        repo.record_step(StepOutcome.FAILURE_DETECTED, step_num=3, action="fill")
        repo.record_step(StepOutcome.HEALING_ATTEMPTED, step_num=3, action="fill",
                         family_code="FAM-06", healing_layer="L3")
        repo.record_step(StepOutcome.HEALING_REJECTED, step_num=3, action="fill",
                         family_code="FAM-06", healing_layer="L3")
        assert repo.snapshot.falhas_detectadas == 1
        assert repo.snapshot.healings_tentados == 1
        assert repo.snapshot.aplicados == 0
        assert repo.snapshot.validados == 0
        assert repo.snapshot.rejeitados == 1

    def test_healing_success_rate(self):
        """Taxa de sucesso: aplicados+validados / total com desfecho."""
        repo = MetricsRepository()
        # 2 aplicados, 1 validado, 2 rejeitados → 3/5 = 0.6
        repo.record_step(StepOutcome.HEALING_APPLIED, step_num=1, action="click")
        repo.record_step(StepOutcome.HEALING_APPLIED, step_num=2, action="fill")
        repo.record_step(StepOutcome.ORACLE_VALIDATED, step_num=3, action="oracle_dom")
        repo.record_step(StepOutcome.HEALING_REJECTED, step_num=4, action="click")
        repo.record_step(StepOutcome.HEALING_REJECTED, step_num=5, action="click")
        assert repo.snapshot.healing_success_rate == 0.6

    def test_healing_success_rate_zero_when_no_outcomes(self):
        repo = MetricsRepository()
        assert repo.snapshot.healing_success_rate == 0.0
        repo.record_step(StepOutcome.FAILURE_DETECTED, step_num=1, action="click")
        assert repo.snapshot.healing_success_rate == 0.0

    def test_summary_includes_per_step(self):
        """summary() deve mostrar secao de per-step metrics."""
        repo = MetricsRepository()
        repo.record_step(StepOutcome.FAILURE_DETECTED, step_num=1, action="click")
        repo.record_step(StepOutcome.HEALING_ATTEMPTED, step_num=1, action="click",
                         family_code="FAM-01", healing_layer="L2")
        repo.record_step(StepOutcome.HEALING_APPLIED, step_num=1, action="click",
                         healing_layer="L2")
        s = repo.summary(show_per_step=True)
        assert "Per-Step Metrics" in s
        assert "Falhas detectadas:" in s
        assert "Healings tentados:" in s
        assert "Aplicados:" in s
        assert "Validados:" in s
        assert "Rejeitados:" in s
        assert "Healing success:" in s

    def test_summary_hides_per_step_when_disabled(self):
        repo = MetricsRepository()
        repo.record_step(StepOutcome.FAILURE_DETECTED, step_num=1, action="click")
        s = repo.summary(show_per_step=False)
        assert "Per-Step Metrics" not in s
        assert "Falhas detectadas:" not in s

    def test_step_history_immutable(self):
        """step_history retorna copia — nao modifica original."""
        repo = MetricsRepository()
        repo.record_step(StepOutcome.FAILURE_DETECTED, step_num=1, action="click")
        history = repo.step_history
        history.append({"injected": True})
        assert len(repo.step_history) == 1

    def test_combined_global_and_per_step(self):
        """record_run e record_step coexistem sem conflito."""
        repo = MetricsRepository()
        repo.record_step(StepOutcome.FAILURE_DETECTED, step_num=1, action="click")
        repo.record_step(StepOutcome.HEALING_APPLIED, step_num=1, action="click")
        repo.record_run(healed=True, false_heal=False, oracle_passed=1)
        assert repo.snapshot.total_runs == 1
        assert repo.snapshot.aplicados == 1
        assert repo.snapshot.falhas_detectadas == 1

    def test_selector_empty_if_none_passed(self):
        """Seletor vazio quando nao informado — nao crasha."""
        repo = MetricsRepository()
        repo.record_step(StepOutcome.FAILURE_DETECTED, step_num=1, action="navigate")
        entry = repo.step_history[0]
        assert entry["selector"] == ""

    def test_selector_truncated(self):
        """Seletor longo truncado a 80 chars no historico."""
        long_selector = "#" + "x" * 200
        repo = MetricsRepository()
        repo.record_step(StepOutcome.FAILURE_DETECTED, step_num=1,
                         action="click", selector=long_selector)
        entry = repo.step_history[0]
        assert len(entry["selector"]) <= 80
