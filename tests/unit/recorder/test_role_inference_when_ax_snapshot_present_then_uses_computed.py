"""RC-9 regression: role=menuitem without accessible_name must be demoted (score≤0.25).
RC-10 regression: select text candidate skipped when raw text length > 60 chars
(concatenated all-options text from old overlay data)."""
import pytest
from testforge.semantic.recording_normalizer import RecordingNormalizer


@pytest.fixture
def normalizer():
    return RecordingNormalizer()


@pytest.mark.unit
class TestRoleInferenceWhenAxSnapshotPresentThenUsesComputed:

    # ---- role=menuitem ----

    def test_menuitem_without_name_demoted(self, normalizer):
        # Arrange — menuitem with no accessible_name: ambiguous (many menuitems on page)
        target_data = {"tag": "li", "role": "menuitem", "css_path": "#nav > ul > li:nth-child(3)"}

        # Act
        target = normalizer._build_target(target_data)

        # Assert
        role_cands = [c for c in target.candidates if c.strategy == "role"]
        assert role_cands, "role candidate must be generated"
        assert role_cands[0].score <= 0.25, f"nameless menuitem score should be ≤0.25, got {role_cands[0].score}"

    def test_menuitem_with_name_not_demoted(self, normalizer):
        # Arrange — menuitem with accessible_name: unambiguous
        target_data = {
            "tag": "li",
            "role": "menuitem",
            "accessible_name": "Configurações",
            "css_path": "#nav > ul > li",
        }

        # Act
        target = normalizer._build_target(target_data)

        # Assert
        role_cands = [c for c in target.candidates if c.strategy == "role"]
        assert role_cands
        assert role_cands[0].score >= 0.90, f"menuitem with name should score ≥0.90, got {role_cands[0].score}"

    def test_button_without_name_uses_normal_ambiguous_score(self, normalizer):
        # Arrange — button without name should use default 0.45 (not 0.25 menuitem special)
        target_data = {"tag": "button", "role": "button"}

        # Act
        target = normalizer._build_target(target_data)

        # Assert
        role_cands = [c for c in target.candidates if c.strategy == "role"]
        assert role_cands
        assert role_cands[0].score >= 0.40

    def test_menuitem_no_text_no_name_uses_css_fallback(self, normalizer):
        # Arrange — menuitem with no text AND no accessible_name: role gets demoted (0.25),
        # css_path becomes the primary fallback.
        target_data = {
            "tag": "li",
            "role": "menuitem",
            "css_path": "#nav > ul > li:nth-child(3)",
        }

        # Act
        target = normalizer._build_target(target_data)

        # Assert — role demoted, css_path (0.60) should rank above role (0.25)
        role_cands = [c for c in target.candidates if c.strategy == "role"]
        css_cands = [c for c in target.candidates if c.strategy == "css_path"]
        assert role_cands
        assert role_cands[0].score <= 0.25
        if css_cands:
            assert css_cands[0].score > role_cands[0].score

    # ---- select text RC-10 ----

    def test_select_long_text_candidate_skipped(self, normalizer):
        # Arrange — text = all options concatenated (>60 chars)
        long_text = "Opção Um Opção Dois Opção Três Opção Quatro Opção Cinco Opção Seis"
        target_data = {"tag": "select", "id": "uf", "text": long_text}

        # Act
        target = normalizer._build_target(target_data)

        # Assert — text candidate should NOT be added when raw text > 60 chars
        text_cands = [c for c in target.candidates if c.strategy == "text"]
        assert not text_cands, "long concatenated option text should not produce a text candidate"

    def test_select_short_text_candidate_included(self, normalizer):
        # Arrange — text = single selected option label (short)
        target_data = {"tag": "select", "id": "uf", "text": "São Paulo"}

        # Act
        target = normalizer._build_target(target_data)

        # Assert
        text_cands = [c for c in target.candidates if c.strategy == "text"]
        assert text_cands, "short single-option text should produce text candidate"
