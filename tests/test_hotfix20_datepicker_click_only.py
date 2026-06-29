"""Hotfix 20: AngularMaterialHandler deve manter sequencias de datepicker apenas com clique.

Regressao: pre-hotfix-20 o metodo _dedup_datepicker_sequences do handler
classificava qualquer sequencia de datepicker sem um passo `fill` subsequente
como "abandonada" e suprimia todos os cliques de navegacao do calendario. Em
producao (Caixa SIOPI), o input de data tem uma mascara que suprime o evento
de input, entao o usuario seleciona uma data inteiramente clicando em celulas
do calendario — o gravador captura cliques, nenhum fill nunca dispara. O ramo
abandonado do handler suprimia esses cliques em tempo de execucao, deixando o
input de data vazio e quebrando o botao Calcular downstream.

Hotfix 20 adiciona um terceiro ramo: se o ultimo clique do calendario na
sequencia pousou em uma celula de dia (mat-calendar-body-cell ou um alvo de
texto numerico dentro do overlay), a sequencia e tratada como conclusao apenas
com clique. Todos os cliques sao mantidos. Testes abaixo fixam tanto este caso
quanto os dois originais (fill subsequente; verdadeiramente abandonado).
"""
from __future__ import annotations

from testforge.handlers.angular_material import AngularMaterialHandler
from testforge.semantic.model import (
    SemanticAction, SemanticTarget, LocatorCandidate,
)


def _make_step(action, selector, value="", overlay=False, text=""):
    target = SemanticTarget(
        candidates=[LocatorCandidate(strategy="css", selector=selector, score=1.0)],
        text=text,
    )
    step = SemanticAction(action=action, target=target, value=value)
    if overlay:
        step.context["overlay_step"] = True
    return step


def test_click_only_date_selection_keeps_all_clicks():
    """Forma SIOPI: toggle + navegacao + clique em celula de dia, sem fill subsequente."""
    handler = AngularMaterialHandler()
    steps = [
        _make_step("click", "span.mat-mdc-button-touch-target"
                            ".mat-datepicker-toggle button"),
        _make_step("click", "button.mat-calendar-period-button",
                   overlay=True, text="JUN 2026"),
        _make_step("click", "button.mat-calendar-previous-button span",
                   overlay=True),
        _make_step("click", "span.mat-calendar-body-cell-content",
                   overlay=True, text="1994"),
        _make_step("click", "span.mat-calendar-body-cell-content",
                   overlay=True, text="MAR"),
        _make_step("click", "span.mat-calendar-body-cell-content",
                   overlay=True, text="3"),
        _make_step("click", "input[aria-label='Prestação']"),  # next field
    ]
    handler._dedup_datepicker_sequences(steps)
    # Os passos do datepicker NAO devem ser marcados como datepicker_dedup
    for i, s in enumerate(steps[:6]):
        assert s.skip_reason != "datepicker_dedup", (
            f"step {i} was wrongly suppressed: {s.skip_reason}"
        )
    # O clique no campo seguinte permanece inalterado
    assert steps[6].skip_reason == ""


def test_fill_followup_still_suppresses_clicks():
    """Forma classica: toggle + navegacao + fill de data — cliques suprimidos."""
    handler = AngularMaterialHandler()
    steps = [
        _make_step("click", "mat-datepicker-toggle button"),
        _make_step("click", "button.mat-calendar-previous-button",
                   overlay=True),
        _make_step("click", "span.mat-calendar-body-cell-content",
                   overlay=True, text="15"),
        _make_step("fill", "input[name='date']", value="15/03/2026"),
    ]
    handler._dedup_datepicker_sequences(steps)
    # Cliques antes do fill sao suprimidos
    assert steps[0].skip_reason == "datepicker_dedup"
    assert steps[1].skip_reason == "datepicker_dedup"
    assert steps[2].skip_reason == "datepicker_dedup"
    # O fill de data e a intencao canonica — mantido
    assert steps[3].skip_reason == ""


def test_truly_abandoned_sequence_still_suppresses_calendar():
    """Usuario abriu o seletor, navegou, entao clicou fora sem selecionar
    um dia. O clique fora do calendario e mantido; navegacao do calendario e
    suprimida."""
    handler = AngularMaterialHandler()
    steps = [
        _make_step("click", "mat-datepicker-toggle button"),
        _make_step("click", "button.mat-calendar-previous-button",
                   overlay=True),
        # Botao anterior do calendario sem celula de dia no final
        _make_step("click", "button#somewhere-else"),  # clique fora do calendario
    ]
    handler._dedup_datepicker_sequences(steps)
    # Os dois passos do calendario sao suprimidos
    assert steps[0].skip_reason == "datepicker_dedup"
    assert steps[1].skip_reason == "datepicker_dedup"
    # O clique de saida permanece
    assert steps[2].skip_reason == ""


def test_day_cell_detected_by_numeric_text_in_overlay():
    """Algumas cadeias de seletor nao contem mat-calendar-body-cell. A
    deteccao de fallback usa texto numerico dentro de um passo overlay."""
    handler = AngularMaterialHandler()
    steps = [
        _make_step("click", "mat-datepicker-toggle button"),
        # Sem mat-calendar-body-cell no seletor, mas texto e um dia
        _make_step("click", "span.some-other-class", overlay=True, text="15"),
        _make_step("click", "input[aria-label='Prestação']"),
    ]
    handler._dedup_datepicker_sequences(steps)
    assert steps[0].skip_reason == ""
    assert steps[1].skip_reason == ""
    assert steps[2].skip_reason == ""
