"""Teste gerado pelo TestForge — fonte da verdade: SemanticTestCase."""
import pytest
from playwright.sync_api import Page, expect
import json, os, re
from testforge.runtime.healer import resolve_selector

BASE_URL = "https://simax.caixa/simax/"

def test_st_nova_massagem(page: Page):
    """web — source: nova_massagem."""

    # Navegacao inicial: carrega pagina sob teste
    page.goto(BASE_URL)

    # Step 1: click
    _sels = ['input']
    _fp = {'tag': 'input'}
    _best = resolve_selector(page, _sels, _fp)
    if _best:
        page.click(_best)
        page.wait_for_timeout(800)  # aguarda renderizacao DOM
    else:
        raise AssertionError(f"passo de clique 1 falhou — nenhum candidato corresponde ao fingerprint")

    # Step 2: click
    try:
        page.get_by_text('Novo agendamento').click()
        page.wait_for_timeout(3000)  # Navegacao SPA
    except Exception:
        _sels = ['#btnNovoAgendamento', '[id^="btnNovoAgendamento"]', '[id$="btnNovoAgendamento"]', 'button:has-text("Novo agendamento")', '[id*="btnNovoAgendamento" i]']
        _fp = {'tag': 'button', 'id': 'btnNovoAgendamento', 'text': 'Novo agendamento', 'class_list': ['btn', 'btn-lg', 'btn-custom']}
        _best = resolve_selector(page, _sels, _fp)
        if _best:
            page.click(_best)
            page.wait_for_timeout(3000)  # Navegacao SPA
        else:
            raise AssertionError(f"passo de clique 2 falhou — nenhum candidato corresponde ao fingerprint")

    # Step 3: select (uf)
    try:
        page.get_by_label('UF').select_option("GO")
        page.wait_for_timeout(200)
    except Exception:
        _sels = ['select[name=\'lstUf\']', '#lstUf', 'label[for="lstUf"]', 'mat-form-field:has(mat-label:has-text("UF")) select', 'select[aria-label=\'UF\']']
        _fp = {'tag': 'select', 'label': 'UF', 'name': 'lstUf', 'id': 'lstUf', 'text': 'Selecione AL AM CE DF ES GO MA MG MS MT PA PB PE PI PR RJ RN RO RR RS SC SE SP', 'class_list': ['form-select', 'form-select-sm']}
        _best = resolve_selector(page, _sels, _fp)
        if _best:
            page.select_option(_best, "GO")
            page.wait_for_timeout(200)
        else:
            raise AssertionError(f"passo 3 falhou — nenhum candidato corresponde ao fingerprint")

    # Step 4: select (edif_cio)
    try:
        page.get_by_label('Edifício').select_option("21")
        page.wait_for_timeout(200)
    except Exception:
        _sels = ['select[name=\'lstEdificio\']', '#lstEdificio', 'label[for="lstEdificio"]', 'mat-form-field:has(mat-label:has-text("Edifício")) select', 'select[aria-label=\'Edifício\']']
        _fp = {'tag': 'select', 'label': 'Edifício', 'name': 'lstEdificio', 'id': 'lstEdificio', 'text': 'Selecione ED. SEDE - GOIANIA/GO (Rua 11, 250 - Setor Central)', 'class_list': ['form-select', 'form-select-sm']}
        _best = resolve_selector(page, _sels, _fp)
        if _best:
            page.select_option(_best, "21")
            page.wait_for_timeout(200)
        else:
            raise AssertionError(f"passo 4 falhou — nenhum candidato corresponde ao fingerprint")

    # Step 5: select (data)
    try:
        page.get_by_label('Data').select_option("2026-07-09")
        page.wait_for_timeout(200)
    except Exception:
        _sels = ['select[name=\'lstData\']', '#lstData', 'label[for="lstData"]', 'mat-form-field:has(mat-label:has-text("Data")) select', 'select[aria-label=\'Data\']']
        _fp = {'tag': 'select', 'label': 'Data', 'name': 'lstData', 'id': 'lstData', 'text': 'Selecione 06/07/2026 (segunda-feira) 07/07/2026 (terça-feira) 08/07/2026 (quarta-feira) 09/07/2026 (quinta-feira)', 'class_list': ['form-select', 'form-select-sm']}
        _best = resolve_selector(page, _sels, _fp)
        if _best:
            page.select_option(_best, "2026-07-09")
            page.wait_for_timeout(200)
        else:
            raise AssertionError(f"passo 5 falhou — nenhum candidato corresponde ao fingerprint")


