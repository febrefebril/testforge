"""RC-9 regression: IDs como #next não devem ser o candidato de maior score.

Cobre R2/R3: botão 'Próximo' em formulário multi-step com id="next" — antes do
fix, o seletor #next era primary (score=0.75) e colidiria com outros
botões #next em steps diferentes. Após o fix, score=0.35 (generic, demoted).
"""
import pytest
from testforge.semantic.recording_normalizer import RecordingNormalizer


@pytest.fixture
def normalizer():
    return RecordingNormalizer()


@pytest.mark.regression
@pytest.mark.unit
class TestR2R3NoNextReusedSelector:

    def test_next_id_not_primary_when_role_available(self, normalizer):
        # Arrange — R2/R3 pattern: button with id=next and role=button + accessible_name
        target_data = {
            "tag": "button",
            "id": "next",
            "role": "button",
            "accessible_name": "Próximo",
            "text": "Próximo",
        }

        # Act
        target = normalizer._build_target(target_data)

        # Assert — id=next must NOT be top candidate
        top = target.candidates[0]
        assert top.strategy != "id" or top.score > 0.35, (
            f"#next should not be top candidate; top={top.strategy}:{top.score}"
        )
        # Role+name should outscore the generic id
        id_cands = [c for c in target.candidates if c.strategy == "id"]
        role_cands = [c for c in target.candidates if c.strategy == "role"]
        assert id_cands and role_cands
        assert role_cands[0].score > id_cands[0].score

    def test_prev_id_not_primary(self, normalizer):
        # Arrange
        target_data = {
            "tag": "button",
            "id": "prev",
            "accessible_name": "Anterior",
        }

        # Act
        target = normalizer._build_target(target_data)

        # Assert
        id_cands = [c for c in target.candidates if c.strategy == "id"]
        assert id_cands
        assert id_cands[0].score <= 0.35

    def test_specific_id_remains_primary(self, normalizer):
        # Arrange — specific ID must not be affected by blacklist
        target_data = {
            "tag": "button",
            "id": "btn-solicitar-credito",
            "role": "button",
        }

        # Act
        target = normalizer._build_target(target_data)

        # Assert
        id_cands = [c for c in target.candidates if c.strategy == "id"]
        assert id_cands
        assert id_cands[0].score >= 0.70
