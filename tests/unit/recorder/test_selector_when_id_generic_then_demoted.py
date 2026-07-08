"""RC-9 regression: generic IDs (next, submit, save, etc.) must be demoted to
score=0.35 so role+name and label candidates rank above them."""
import pytest
from testforge.semantic.recording_normalizer import RecordingNormalizer, _GENERIC_ID_BLACKLIST


@pytest.fixture
def normalizer():
    return RecordingNormalizer()


@pytest.mark.unit
class TestSelectorWhenIdGenericThenDemoted:

    def test_id_next_scores_below_threshold(self, normalizer):
        # Arrange
        target_data = {"tag": "button", "id": "next", "text": "Próximo"}

        # Act
        target = normalizer._build_target(target_data)

        # Assert
        id_cands = [c for c in target.candidates if c.strategy == "id"]
        assert id_cands, "id candidate should still be generated"
        assert id_cands[0].score <= 0.35, f"generic id score should be ≤0.35, got {id_cands[0].score}"

    def test_id_submit_scores_below_threshold(self, normalizer):
        # Arrange
        target_data = {"tag": "button", "id": "submit", "role": "button"}

        # Act
        target = normalizer._build_target(target_data)

        # Assert
        id_cands = [c for c in target.candidates if c.strategy == "id"]
        assert id_cands
        assert id_cands[0].score <= 0.35

    def test_id_save_scores_below_threshold(self, normalizer):
        # Arrange
        target_data = {"tag": "button", "id": "save", "text": "Salvar"}

        # Act
        target = normalizer._build_target(target_data)

        # Assert
        id_cands = [c for c in target.candidates if c.strategy == "id"]
        assert id_cands
        assert id_cands[0].score <= 0.35

    def test_id_specific_scores_normal(self, normalizer):
        # Arrange — ID "btnSolicitarCredito" is not generic
        target_data = {"tag": "button", "id": "btnSolicitarCredito", "text": "Solicitar"}

        # Act
        target = normalizer._build_target(target_data)

        # Assert
        id_cands = [c for c in target.candidates if c.strategy == "id"]
        assert id_cands
        assert id_cands[0].score >= 0.70, f"specific id should score ≥0.70, got {id_cands[0].score}"

    def test_generic_id_reason_mentions_demoted(self, normalizer):
        # Arrange
        target_data = {"tag": "button", "id": "cancel"}

        # Act
        target = normalizer._build_target(target_data)

        # Assert
        id_cands = [c for c in target.candidates if c.strategy == "id"]
        assert id_cands
        assert "generic" in id_cands[0].reason.lower() or "demoted" in id_cands[0].reason.lower()

    def test_blacklist_covers_expected_ids(self):
        # Arrange / Assert: contract test — these IDs must be in blacklist
        required = {"next", "prev", "submit", "save", "cancel", "continue", "ok", "confirm"}
        missing = required - _GENERIC_ID_BLACKLIST
        assert not missing, f"Missing from blacklist: {missing}"

    def test_role_name_beats_generic_id(self, normalizer):
        # Arrange — generic id but has role+name, which should win
        target_data = {
            "tag": "button",
            "id": "next",
            "role": "button",
            "accessible_name": "Próximo passo",
        }

        # Act
        target = normalizer._build_target(target_data)

        # Assert
        top = target.candidates[0]
        assert top.strategy == "role", f"role candidate should rank first, got {top.strategy}"
        assert top.score >= 0.90
