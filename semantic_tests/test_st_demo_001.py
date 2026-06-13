"""Teste gerado pelo TestForge — fonte de verdade: SemanticTestCase."""
from playwright.sync_api import Page, expect

BASE_URL = "http://localhost:8765"


def test_st_demo_001(page: Page):
    """fake-bank — source: DEMO-001."""
    page.goto(BASE_URL)
    # Step 1: fill (value="12345678900")
    _sels = ["label:has-text("CPF")", "[placeholder="000.000.000-00"]", "[name="cpf"]"]
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
    _sels = ["text=Pesquisar"]
    for _sel in _sels:
        try:
            page.click(_sel)
            page.wait_for_timeout(300)
            break
        except Exception:
            continue
    else:
        raise AssertionError(f"click step 2 falhou")

    page.goto(BASE_URL)
    # Step 3: fill (value="12345678900")
    _sels = ["label:has-text("CPF")", "[placeholder="000.000.000-00"]", "[name="cpf"]"]
    for _sel in _sels:
        try:
            page.fill(_sel, "12345678900")
            page.wait_for_timeout(200)
            break
        except Exception:
            continue
    else:
        raise AssertionError(f"fill step 3 falhou")

    # Step 4: click
    _sels = ["text=Pesquisar"]
    for _sel in _sels:
        try:
            page.click(_sel)
            page.wait_for_timeout(300)
            break
        except Exception:
            continue
    else:
        raise AssertionError(f"click step 4 falhou")

    page.goto(BASE_URL)
    # Step 5: fill (value="12345678900")
    _sels = ["label:has-text("CPF")", "[placeholder="000.000.000-00"]", "[name="cpf"]"]
    for _sel in _sels:
        try:
            page.fill(_sel, "12345678900")
            page.wait_for_timeout(200)
            break
        except Exception:
            continue
    else:
        raise AssertionError(f"fill step 5 falhou")

    # Step 6: click
    _sels = ["text=Pesquisar"]
    for _sel in _sels:
        try:
            page.click(_sel)
            page.wait_for_timeout(300)
            break
        except Exception:
            continue
    else:
        raise AssertionError(f"click step 6 falhou")

    # Step 7: assert (textual)
    expect(page.locator("#resultadoSection")).to_contain_text("CPF consultado: 12345678900")

    # Step 8: assert (textual)
    expect(page.locator("#resultadoSection")).to_contain_text("visible")

    # Step 9: assert (textual)
    expect(page.locator("#resultadoSection")).to_contain_text("CPF consultado: 12345678900")

    # Step 10: assert (textual)
    expect(page.locator("#resultadoSection")).to_contain_text("visible")

    # Step 11: assert (textual)
    expect(page.locator("#resultadoSection")).to_contain_text("CPF consultado: 12345678900")

    # Step 12: assert (textual)
    expect(page.locator("#resultadoSection")).to_contain_text("visible")

