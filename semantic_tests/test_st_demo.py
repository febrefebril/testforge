"""Teste gerado pelo TestForge — fonte de verdade: SemanticTestCase."""
from playwright.sync_api import Page, expect

BASE_URL = "http://localhost:8765"


def test_st_demo(page: Page):
    """fake-bank — source: DEMO-001."""
    page.goto(BASE_URL)
    # Step 1: fill (value="12345678900")
    _sels = ['label:has-text("CPF") + input', '[placeholder="000.000.000-00"]', '[name="cpf"]']
    for _sel in _sels:
        try:
            page.fill(_sel, "12345678900")
            page.wait_for_timeout(200)
            break
        except Exception:
            continue
    else:
        raise AssertionError(f"fill step 1 falhou")

    # Step 2: click
    _sels = ['text=Pesquisar']
    for _sel in _sels:
        try:
            page.click(_sel)
            page.wait_for_timeout(300)
            break
        except Exception:
            continue
    else:
        raise AssertionError(f"click step 2 falhou")

    # Step 3: assert (textual)
    expect(page.locator('#resultadoSection')).to_contain_text('CPF consultado: 12345678900')

    # Step 4: assert (visivel)
    expect(page.locator('#resultadoSection')).to_be_visible()

