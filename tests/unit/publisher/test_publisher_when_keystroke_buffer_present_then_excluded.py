"""NB-12: git_publisher exclui keystroke_buffer.jsonl do snapshot copiado."""
import pytest


@pytest.mark.unit
class TestPublisherWhenKeystrokeBufferPresentThenExcluded:
    def test_never_publish_list_contains_keystroke_buffer(self):
        """_NEVER_PUBLISH_FILENAMES must include keystroke_buffer.jsonl."""
        # Arrange & Act
        from testforge.publisher.git_publisher import _NEVER_PUBLISH_FILENAMES
        # Assert
        assert "keystroke_buffer.jsonl" in _NEVER_PUBLISH_FILENAMES, (
            "NB-12: _NEVER_PUBLISH_FILENAMES must include keystroke_buffer.jsonl."
        )
