"""Teste base do fluxo CPF — sem mutacao."""
import pytest
from playwright.sync_api import Page, expect

BASE_URL = "http://localhost:8765"


@pytest.fixture(autouse=True)
def page(page: Page):
    page.set_viewport_size({"width": 1280, "height": 720})
    yield page


def test_consulta_cpf_fluxo_base(page: Page):
    """Fluxo completo sem mutacao: preencher CPF, clicar Pesquisar, ver resultado."""
    page.goto(BASE_URL)

    # Preencher CPF
    cpf_input = page.get_by_placeholder("000.000.000-00")
    cpf_input.fill("12345678900")

    # Clicar Pesquisar
    btn = page.get_by_role("button", name="Pesquisar")
    btn.click()

    # Verificar resultado
    resultado = page.get_by_text("CPF consultado: 12345678900")
    expect(resultado).to_be_visible()
