"""REC-77: Unicode NFKD normalization ensures single convention for accented chars."""
import unicodedata
import pytest


@pytest.mark.unit
class TestSanitizeNameWhenCedilhaThenUniqueConvention:
    def test_terca_always_produces_terca(self):
        """Both NFC and NFD input must produce identical output."""
        # Arrange
        from testforge.cli.app import _sanitize_name
        nfc_input = unicodedata.normalize("NFC", "ter\u00e7a")
        nfd_input = unicodedata.normalize("NFD", "ter\u00e7a")
        # Act & Assert
        assert _sanitize_name(nfc_input) == _sanitize_name(nfd_input)
        assert _sanitize_name("ter\u00e7a") == "terca"

    def test_horario_strips_accent(self):
        """Accented 'a' should become plain 'a'."""
        # Arrange
        from testforge.cli.app import _sanitize_name
        # Act
        result = _sanitize_name("hor\u00e1rio")
        # Assert
        assert result == "horario"

    def test_cedilha_produces_c_not_underscore(self):
        """'\u00e7' must become 'c', not '_'."""
        # Arrange
        from testforge.cli.app import _sanitize_name
        # Act
        result = _sanitize_name("\u00e7a")
        # Assert
        assert result == "ca", f"Expected 'ca', got '{result}'"

    def test_ascii_unchanged(self):
        """ASCII strings should pass through unmodified."""
        # Arrange
        from testforge.cli.app import _sanitize_name
        # Act
        result = _sanitize_name("login_cpf")
        # Assert
        assert result == "login_cpf"

    def test_spaces_become_underscore(self):
        """Spaces should become underscores."""
        # Arrange
        from testforge.cli.app import _sanitize_name
        # Act
        result = _sanitize_name("deve logar")
        # Assert
        assert result == "deve_logar"
