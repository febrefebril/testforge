"""Testes do OracleRunner e PromotionGate."""
from playwright.sync_api import Page

from testforge.oracle import OracleRunner, OracleResult
from testforge.promotion import PromotionGate, PromotionState


class TestOracleRunner:
    def test_visual_dom_visible(self, page: Page):
        page.set_content("<h1 id='title'>TestForge</h1>")
        runner = OracleRunner(page)
        result = runner.run_visual_dom("#title", "TestForge")
        assert result.status == "passed"
        assert result.oracle_type == "visual_dom"

    def test_visual_dom_not_found(self, page: Page):
        page.set_content("<h1>Test</h1>")
        runner = OracleRunner(page)
        result = runner.run_visual_dom("#nao-existe")
        assert result.status == "failed"

    def test_visual_dom_wrong_text(self, page: Page):
        page.set_content("<h1 id='title'>Outro</h1>")
        runner = OracleRunner(page)
        result = runner.run_visual_dom("#title", "TestForge")
        assert result.status == "failed"

    def test_business_state_match(self, page: Page):
        page.set_content("<div id='cpf'>123.456.789-00</div>")
        runner = OracleRunner(page)
        result = runner.run_business_state("#cpf", "123.456.789-00")
        assert result.status == "passed"
        assert "123.456.789-00" in result.actual

    def test_business_state_not_found(self, page: Page):
        page.set_content("<div>Test</div>")
        runner = OracleRunner(page)
        result = runner.run_business_state("#nao-existe", "x")
        assert result.status == "failed"

    def test_business_state_diverge(self, page: Page):
        page.set_content("<div id='v'>A</div>")
        runner = OracleRunner(page)
        result = runner.run_business_state("#v", "B")
        assert result.status == "failed"

    def test_run_all(self, page: Page):
        page.set_content("<h1 id='t'>OK</h1>")
        runner = OracleRunner(page)
        results = runner.run_all([
            {"type": "visual_dom", "selector": "#t", "expected": "OK"},
            {"type": "business_state", "selector": "#t", "expected": "OK"},
        ])
        assert len(results) == 2
        assert all(r.status == "passed" for r in results)


class TestPromotionGate:
    def test_all_pass_promotes(self):
        gate = PromotionGate()
        results = [
            OracleResult("visual_dom", "passed"),
            OracleResult("business_state", "passed"),
        ]
        decision = gate.evaluate(results, {"screenshots": ["a.png"]})
        assert decision.allowed is True
        assert decision.state == PromotionState.SHADOW_VALIDATED

    def test_oracle_failed_rejects(self):
        gate = PromotionGate()
        results = [OracleResult("visual_dom", "failed")]
        decision = gate.evaluate(results, {"screenshots": ["a.png"]})
        assert decision.allowed is False
        assert "oracle_failed" in decision.blocks

    def test_missing_evidence_rejects(self):
        gate = PromotionGate()
        results = [OracleResult("visual_dom", "passed")]
        decision = gate.evaluate(results, {})
        assert decision.allowed is False
        assert "evidence_incomplete" in decision.blocks

    def test_missing_oracle_rejects(self):
        gate = PromotionGate()
        decision = gate.evaluate([], {"screenshots": ["a.png"]})
        assert decision.allowed is False
        assert "oracle_missing" in decision.blocks

    def test_conflict_oracles_rejects(self):
        gate = PromotionGate()
        results = [
            OracleResult("visual_dom", "passed"),
            OracleResult("business_state", "failed"),
        ]
        decision = gate.evaluate(results, {"screenshots": ["a.png"]})
        assert decision.allowed is False
        assert "oracle_conflict" in decision.blocks

    def test_low_uniqueness_rejects(self):
        gate = PromotionGate()
        results = [OracleResult("visual_dom", "passed")]
        decision = gate.evaluate(results, {"screenshots": ["a.png"]}, uniqueness_score=0.1)
        assert "uniqueness_low" in decision.blocks
