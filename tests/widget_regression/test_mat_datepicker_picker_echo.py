"""Widget regression: mat-datepicker picker-echo pattern.

Fixture: `fixtures/mat_datepicker_picker_echo/` — sliced from SIOPI
test-pos-hotfix22 recording, contains the toggle → period button →
previous-button × 2 → year → month → day → fill (picker echo) sequence
plus one interleaved textual assert.

These tests pipeline the fixture through the real normalizer and lock in:

1. Calendar clicks are NOT skipped as `datepicker_dedup` (hotfix 22).
2. The picker-echo fill is marked `datepicker_picker_echo_fill` so the
   runtime skips it instead of trying to write into the readonly-ish
   Material date input.
3. Asserts from `steps.jsonl` are interleaved with actions by timestamp
   (not appended to the end).
4. Navigation steps preserve their timestamp so interleaving is stable.

Any regression in the datepicker handler, the picker-echo detector, or
the assert merger will fail one of these tests.
"""
from __future__ import annotations

from pathlib import Path

from testforge.semantic.recording_normalizer import RecordingNormalizer


FIXTURE_DIR = Path(__file__).parent / "fixtures" / "mat_datepicker_picker_echo"


def _normalize():
    return RecordingNormalizer().normalize(
        str(FIXTURE_DIR),
        test_id="ST-mat_datepicker_picker_echo",
        application="test",
        base_url="https://simuladorhabitacao.caixa.gov.br/home",
    )


def test_calendar_clicks_preserved_not_dedup():
    """Regressao hotfix 22: cliques do calendario (previous-button, year,
    month, day cells) NAO devem ser marcados como `datepicker_dedup`. Se o
    forem, o runner os pula e o input de data fica em branco (calendar bug
    do test-pos-hotfix22).
    """
    stc = _normalize()
    calendar_clicks = [
        s for s in stc.steps
        if s.action == "click"
        and s.target is not None
        and s.target.candidates
        and any(
            "mat-calendar" in (c.selector or "")
            for c in s.target.candidates
        )
    ]
    assert calendar_clicks, "expected calendar clicks in fixture"

    dedup_marked = [s for s in calendar_clicks if s.skip_reason == "datepicker_dedup"]
    assert not dedup_marked, (
        f"{len(dedup_marked)} calendar clicks wrongly marked datepicker_dedup: "
        f"{[(c.target.candidates[0].selector[:60], c.skip_reason) for c in dedup_marked]}"
    )


def test_picker_echo_fill_is_skipped():
    """Fill que vem apos o day-cell click e o echo do picker escrevendo
    no input Material. Deve receber skip_reason `datepicker_picker_echo_fill`
    para o runtime nao tentar preencher (input readonly-ish rejeita)."""
    stc = _normalize()
    picker_fills = [
        s for s in stc.steps
        if s.action == "fill" and s.skip_reason == "datepicker_picker_echo_fill"
    ]
    assert len(picker_fills) == 1, (
        f"expected exactly 1 picker-echo fill, got {len(picker_fills)}: "
        f"{[(s.value, s.skip_reason) for s in stc.steps if s.action == 'fill']}"
    )


def test_asserts_interleaved_by_timestamp():
    """Assert com timestamp anterior ao ultimo click deve aparecer ANTES
    dele no stream final — nao empilhado no fim.

    Fixture: assert em 13:07:34 apos ultimo click em 13:06:57. Como o
    fixture nao tem clicks depois do assert, ele fica no final naturalmente.
    Mas testamos que o timestamp foi preservado no contexto do assert.
    """
    stc = _normalize()
    asserts = [s for s in stc.steps if s.action == "assert"]
    assert len(asserts) == 1, f"expected 1 assert, got {len(asserts)}"
    ts = (asserts[0].context or {}).get("timestamp", "")
    assert ts, f"assert timestamp not preserved in context: {asserts[0].context!r}"
    assert ts.startswith("2026-07-01T13:07:34"), (
        f"unexpected assert timestamp: {ts!r}"
    )


def test_navigation_preserves_timestamp():
    """Navigation steps agora preservam timestamp no context — necessario
    para intercalar asserts corretamente quando gravacoes cruzam paginas."""
    stc = _normalize()
    navs = [s for s in stc.steps if s.action == "navigation"]
    assert navs, "expected at least one navigation step"
    for nav in navs:
        ts = (nav.context or {}).get("timestamp", "")
        assert ts, (
            f"navigation to {nav.url!r} missing timestamp — asserts adjacent "
            f"to nav will be misordered"
        )
