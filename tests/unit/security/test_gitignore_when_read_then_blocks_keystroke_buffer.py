"""NB-12: .gitignore no root bloqueia keystroke_buffer.jsonl em qualquer subpath."""
import pathlib
import pytest


@pytest.mark.unit
class TestGitignoreWhenReadThenBlocksKeystrokeBuffer:
    def test_gitignore_lists_keystroke_buffer(self):
        """.gitignore must include **/keystroke_buffer.jsonl."""
        # Arrange
        gi = pathlib.Path(__file__).resolve().parents[3] / ".gitignore"
        # Act
        content = gi.read_text(encoding="utf-8")
        # Assert
        assert "**/keystroke_buffer.jsonl" in content, (
            "NB-12: .gitignore must include **/keystroke_buffer.jsonl."
        )
