"""Phase 4 — curator should degrade when no step runner is available."""
from __future__ import annotations

from dataclasses import dataclass

from testforge.healing.curator import CuradorAutomatico, ProgressResult
from testforge.healing.evidence_payload import EvidencePayload
from testforge.healing.llm_healer import LLMHealingProposal


@dataclass
class _Recipe:
    recipe_id: str = "REC-001"
    priority: int = 9
    solution_selector: str = 'button[data-testid="continue"]'
    solution_strategy: str = "data_testid_fallback"
    taxonomy_id: str = "SEL-004"


class _Catalog:
    def match_recipes(self, error, family=""):
        return [_Recipe()]

    def record_usage(self, recipe_id):
        return None

    def record_success(self, recipe_id):
        return None


class _Agent:
    def heal(self, evidence, error_message):
        return LLMHealingProposal(
            taxonomy_id="SEL-004",
            family="FAM-01",
            strategy="has_text_fallback",
            new_locator='text="Continuar"',
            confidence=0.9,
            rationale="unit-test",
        )


class TestCuratorDegradedNoRunner:
    def test_l0_when_runner_missing_then_returns_degraded(self):
        # Arrange
        curator = CuradorAutomatico(catalog=_Catalog(), step_runner=None)

        # Act
        outcome = curator._try_layer0_catalog(
            family="FAM-01",
            step_data={"selector": "a.dead-link"},
            error_message="not found",
        )

        # Assert
        assert outcome is not None
        assert outcome.status == ProgressResult.DEGRADED
        assert outcome.layer_used == "L0"
        assert outcome.reason == "no_step_runner"
        assert outcome.proposal is not None

    def test_l2_when_runner_missing_then_returns_degraded(self, monkeypatch):
        # Arrange
        from testforge.healing import agents as agents_mod

        monkeypatch.setattr(agents_mod, "route_to_agent", lambda family, llm_healer=None: _Agent())
        curator = CuradorAutomatico(catalog=_Catalog(), step_runner=None)
        evidence = EvidencePayload(
            step_context={"selector": "#x"},
            dom_snapshot="<html><body>" + ("x" * 120) + "</body></html>",
            console_errors=[],
            network_state=[],
            screenshot_b64="",
            is_sufficient=True,
            insufficiency_reason="",
        )

        # Act
        outcome = curator._try_layer2_agents(
            family="FAM-01",
            step_data={"selector": "#x"},
            error_message="not found",
            evidence=evidence,
        )

        # Assert
        assert outcome is not None
        assert outcome.status == ProgressResult.DEGRADED
        assert outcome.layer_used == "L2"
        assert outcome.reason == "no_step_runner"
        assert outcome.proposal is not None
