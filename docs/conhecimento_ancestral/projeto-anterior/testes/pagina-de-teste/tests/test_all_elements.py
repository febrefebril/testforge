"""TestForge — Epic A: Validate all taxonomy elements against the test page.

Covers: SEL-004, SEL-006, SEL-007, SEL-009, SEL-010
        INP-002, INP-005, INP-006, INP-007, INP-009, INP-010
        TIM-006
        CTX-001, CTX-003, CTX-006
        STA-002, STA-004
        DOM-002, DOM-005
"""

import asyncio
from pathlib import Path

import pytest

BASE_URL = "http://localhost:8080"


def _accept_dialogs(page):
    page.on("dialog", lambda dialog: asyncio.create_task(dialog.accept()))


# ====================================================================
# FAM-01: Seletores Frágeis
# ====================================================================


def test_sel_006_input_sem_id(page):
    page.goto(BASE_URL)
    campo = page.locator('input.no-id-input')
    campo.fill("teste sem id")
    assert campo.input_value() == "teste sem id"


def test_sel_010_label_sem_for(page):
    page.goto(BASE_URL)
    campo = page.locator('#campo-label-for')
    campo.fill("teste label sem for")
    assert campo.input_value() == "teste label sem for"


def test_sel_010_radio_label_custom(page):
    page.goto(BASE_URL)
    label_b = page.locator('.radio-label-custom[data-value="opcao-b"]')
    label_b.click()
    assert "selected" in (label_b.get_attribute("class") or "")
    radio_b = page.locator('input.hidden-radio[value="opcao-b"]')
    assert radio_b.is_checked()


def test_sel_009_texto_duplicado(page):
    _accept_dialogs(page)
    page.goto(BASE_URL)
    botoes = page.locator('button.acao-duplicada')
    assert botoes.count() == 2
    botoes.nth(0).click()
    botoes.nth(1).click()


def test_sel_004_div_generica(page):
    _accept_dialogs(page)
    page.goto(BASE_URL)
    span = page.locator('#secao-seletores .field-row:nth-child(5) span')
    span.click()


def test_sel_007_botao_fora_form(page):
    _accept_dialogs(page)
    page.goto(BASE_URL)
    page.locator('#btn-fora-form').click()


# ====================================================================
# FAM-06: Input e Interação Especializada
# ====================================================================


def test_inp_007_mascara_cpf(page):
    page.goto(BASE_URL)
    campo = page.locator('#campo-cpf')
    campo.fill("12345678901")
    assert campo.input_value() == "123.456.789-01"


def test_inp_009_datepicker(page):
    page.goto(BASE_URL)
    campo = page.locator('#campo-data')
    campo.click()
    page.wait_for_timeout(500)
    page.locator('.ui-datepicker-title').wait_for(timeout=3000)
    day = page.locator('.ui-datepicker-calendar a').first
    selected_text = day.get_attribute("text") or day.text_content()
    day.click()
    val = campo.input_value()
    assert len(val) > 0, "Datepicker deveria ter preenchido o campo"


def test_inp_010_combobox(page):
    page.goto(BASE_URL)
    campo = page.locator('#campo-combobox')
    campo.click()
    campo.fill("Python")
    page.locator('.combobox-item[data-value="py"]').click()
    assert campo.input_value() == "Python"


def test_inp_002_upload(page):
    page.goto(BASE_URL)
    file_input = page.locator('#campo-upload')
    tmp_file = Path("/tmp/testforge-upload-test.txt")
    tmp_file.write_text("conteudo de teste")
    file_input.set_input_files(str(tmp_file))
    tmp_file.unlink()


def test_inp_005_drag_and_drop(page):
    page.goto(BASE_URL)
    item = page.locator('#sortable-list li[data-id="1"]')
    target = page.locator('#drop-zone')
    item.drag_to(target)
    page.wait_for_timeout(300)
    assert "Item solto aqui!" in target.text_content()


def test_inp_006_contenteditable(page):
    page.goto(BASE_URL)
    edit = page.locator('#campo-richedit')
    edit.click()
    edit.fill("texto digitado no rich edit")
    assert edit.text_content() == "texto digitado no rich edit"


# ====================================================================
# TIM-006: Autocomplete
# ====================================================================


def test_tim_006_autocomplete(page):
    page.goto(BASE_URL)
    campo = page.locator('#campo-autocomplete')
    campo.fill("Bras")
    page.wait_for_timeout(600)
    menu = page.locator('.ui-menu-item')
    menu.first.wait_for(timeout=3000)
    menu.first.click()
    val = campo.input_value()
    assert len(val) > 0, "Autocomplete deveria ter preenchido com cidade"


# ====================================================================
# FAM-03: Contexto e Escopo
# ====================================================================


def test_ctx_003_shadow_dom(page):
    page.goto(BASE_URL)
    host = page.locator('#shadow-host')
    shadow_input = host.locator('input')
    shadow_input.wait_for(timeout=3000)
    shadow_input.fill("teste shadow dom")
    assert shadow_input.input_value() == "teste shadow dom"


def test_ctx_001_iframe(page):
    page.goto(BASE_URL)
    iframe = page.frame_locator('#iframe-teste')
    campo = iframe.locator('#campo-iframe')
    campo.fill("teste iframe")
    assert campo.input_value() == "teste iframe"


def test_ctx_006_modal(page):
    _accept_dialogs(page)
    page.goto(BASE_URL)
    page.locator('#btn-abrir-modal').click()
    modal = page.locator('#modal-overlay.show')
    modal.wait_for(timeout=2000)
    campo = modal.locator('#campo-modal')
    campo.fill("teste modal")
    assert campo.input_value() == "teste modal"
    page.locator('#btn-confirmar-modal').click()


# ====================================================================
# FAM-04: Estado da Aplicação
# ====================================================================


def test_sta_002_overlay(page):
    _accept_dialogs(page)
    page.goto(BASE_URL)
    page.locator('#btn-mostrar-overlay').click()
    overlay = page.locator('#overlay-blocker')
    overlay.wait_for(timeout=2000)
    page.locator('#btn-fechar-overlay').click()
    page.wait_for_timeout(500)
    assert "show" not in (overlay.get_attribute("class") or "")
    page.locator('#btn-atras-overlay').click()


def test_sta_004_alert(page):
    page.on("dialog", lambda dialog: asyncio.create_task(dialog.accept()))
    page.goto(BASE_URL)
    page.locator('#btn-alert').click()


def test_sta_004_confirm(page):
    page.on("dialog", lambda dialog: asyncio.create_task(dialog.accept()))
    page.goto(BASE_URL)
    page.locator('#btn-confirm').click()


def test_sta_004_prompt(page):
    page.goto(BASE_URL)
    page.on("dialog", lambda dialog: dialog.accept(prompt_text="valor digitado"))
    page.locator('#btn-prompt').click()
    page.wait_for_timeout(500)


# ====================================================================
# FAM-05: DOM Dinâmico
# ====================================================================


def test_dom_002_lista_reordenada(page):
    page.goto(BASE_URL)
    container = page.locator('#lista-reordenavel')
    items_antes = container.locator('.item-lista')
    ordem_antes = items_antes.all_text_contents()
    page.locator('#btn-reordenar').click()
    page.wait_for_timeout(300)
    items_depois = container.locator('.item-lista')
    ordem_depois = items_depois.all_text_contents()
    assert ordem_antes != ordem_depois, "Lista deveria ter sido reordenada"


def test_dom_005_conteudo_dinamico(page):
    page.goto(BASE_URL)
    page.locator('#btn-carregar-conteudo').click()
    campo = page.locator('#campo-dinamico')
    campo.wait_for(timeout=2000)
    campo.fill("teste dinamico")
    assert campo.input_value() == "teste dinamico"


# ====================================================================
# TIM-006: Conteúdo com delay
# ====================================================================


def test_tim_006_lazy_content(page):
    page.goto(BASE_URL)
    container = page.locator('#lazy-container')
    container.wait_for(timeout=5000)
    campo = page.locator('#campo-lazy')
    campo.wait_for(timeout=5000)
    campo.fill("teste lazy")
    assert campo.input_value() == "teste lazy"


def test_tim_006_select_assincrono(page):
    page.goto(BASE_URL)
    select = page.locator('#select-assincrono')
    select.wait_for(timeout=5000)
    select.select_option('opcao2')
    assert select.input_value() == 'opcao2'
