"""Testes para cada mutacao do synthetic lab."""
import pytest
from playwright.sync_api import Page, expect, TimeoutError as PlaywrightTimeout

BASE_URL = "http://localhost:8765"


def test_mutation_change_id(page: Page):
    """ID do botao muda — seletor por ID falha, mas por role+name funciona."""
    page.goto(BASE_URL + "?mutation=change_id")
    page.get_by_placeholder("000.000.000-00").fill("12345678900")
    page.get_by_role("button", name="Pesquisar").click()
    expect(page.get_by_text("CPF consultado: 12345678900")).to_be_visible()


def test_mutation_change_accessible_name(page: Page):
    """Label muda de 'CPF' para 'Documento' — seletor por label falha, placeholder funciona."""
    page.goto(BASE_URL + "?mutation=change_accessible_name")
    page.get_by_placeholder("000.000.000-00").fill("12345678900")
    page.get_by_role("button", name="Pesquisar").click()
    expect(page.get_by_text("CPF consultado: 12345678900")).to_be_visible()


def test_mutation_duplicate_button_text(page: Page):
    """Dois botoes 'Pesquisar' — precisa de contexto para desambiguar."""
    page.goto(BASE_URL + "?mutation=duplicate_button_text")
    page.get_by_placeholder("000.000.000-00").fill("12345678900")
    # Usa o primeiro botao (ainda funciona mas pode ser ambiguo)
    page.get_by_role("button", name="Pesquisar").first.click()
    expect(page.get_by_text("CPF consultado: 12345678900")).to_be_visible()


def test_mutation_overlay_blocks_click(page: Page):
    """Overlay bloqueia clique — espera overlay desaparecer e clica normalmente."""
    page.goto(BASE_URL + "?mutation=overlay_blocks_click")
    page.get_by_placeholder("000.000.000-00").fill("12345678900")
    btn = page.get_by_role("button", name="Pesquisar")
    # Overlay fica ativo por 8s — espera desaparecer
    overlay = page.locator("#overlayBlock")
    expect(overlay).to_be_visible(timeout=2000)  # confirma que overlay existe
    overlay.wait_for(state="hidden", timeout=10000)  # espera sumir
    btn.click()
    expect(page.get_by_text("CPF consultado: 12345678900")).to_be_visible()


def test_mutation_disabled_button(page: Page):
    """Botao disabled — precisa esperar habilitar."""
    page.goto(BASE_URL + "?mutation=disabled_button")
    page.get_by_placeholder("000.000.000-00").fill("12345678900")
    btn = page.get_by_role("button", name="Pesquisar")
    # Espera o botao ficar enabled (max 10s)
    btn.wait_for(state="attached")
    page.wait_for_timeout(8500)  # espera o setTimeout de 8s
    expect(btn).to_be_enabled()
    btn.click()
    expect(page.get_by_text("CPF consultado: 12345678900")).to_be_visible()
