"""REC-49: menu assert inclui 4o tipo 'erro_esperado' com visual (vermelho)."""
import re
from pathlib import Path

import pytest


OVERLAY_JS = (
    Path(__file__).resolve().parents[3]
    / "src" / "testforge" / "recorder" / "overlay_inject.js"
)


@pytest.fixture(scope="module")
def overlay_source() -> str:
    return OVERLAY_JS.read_text(encoding="utf-8")


@pytest.mark.unit
class TestAssertMenuWhenErroTypeDeclaredThenPresent:
    def test_erro_esperado_type_in_menu(self, overlay_source):
        assert "erro_esperado" in overlay_source, (
            "REC-49: menu assert deve incluir tipo 'erro_esperado' para asserts em mensagens de erro."
        )

    def test_erro_esperado_has_red_bg(self, overlay_source):
        pattern = re.compile(
            r"type:\s*['\"]erro_esperado['\"][^}]*bg:\s*['\"]#[a-fA-F0-9]{6}['\"]",
            re.DOTALL,
        )
        match = pattern.search(overlay_source)
        assert match, (
            "REC-49: entry erro_esperado precisa cor de fundo (bg) hex definido."
        )
        # cor deve ser tom vermelho (dc, d0, ef, e0, e9 no leading hex)
        color_pattern = re.compile(
            r"type:\s*['\"]erro_esperado['\"][^}]*bg:\s*['\"](#[a-fA-F0-9]{6})['\"]",
            re.DOTALL,
        )
        color = color_pattern.search(overlay_source).group(1).lower()
        assert color.startswith("#dc") or color.startswith("#d0") or \
               color.startswith("#e0") or color.startswith("#ef") or \
               color.startswith("#b0") or color.startswith("#c0"), (
            f"REC-49: cor {color} nao parece tom vermelho (esperado #dc*, #d0*, #e0*, #ef*, #b0*, #c0*)"
        )

    def test_erro_label_localized(self, overlay_source):
        """Label do botao deve ser reconhecivel — 'Error', 'Erro', ou similar."""
        pattern = re.compile(
            r"type:\s*['\"]erro_esperado['\"][^}]*label:\s*['\"]([^'\"]+)['\"]",
            re.DOTALL,
        )
        match = pattern.search(overlay_source)
        assert match, "REC-49: erro_esperado precisa label textual."
        label = match.group(1).lower()
        assert "err" in label or "falha" in label, (
            f"REC-49: label '{match.group(1)}' nao denota erro (esperado 'Erro'/'Error')"
        )
