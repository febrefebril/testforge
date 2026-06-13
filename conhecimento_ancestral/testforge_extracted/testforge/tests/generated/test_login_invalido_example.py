"""
TestForge — Example generated test
Test: Login com usuário inválido
Description: Verifica que mensagem de erro aparece ao digitar credenciais erradas
Assert hint: A mensagem 'Usuário ou senha inválidos' deve estar visível
"""
from __future__ import annotations

import logging
import re

import pytest
from playwright.sync_api import Page, expect

log = logging.getLogger(__name__)

# ── Selector constants (multi-selector self-healing support) ──────────────────

SELECTORS = {
    0: {  # Email input
        "data_testid": '[data-testid="email-input"]',
        "aria": '[aria-label="Email"]',
        "text": '[placeholder="Digite seu email"]',
        "css": "form > div:nth-of-type(1) > input",
        "xpath": "//input[@type='email']",
    },
    1: {  # Password input
        "data_testid": '[data-testid="password-input"]',
        "aria": '[aria-label="Senha"]',
        "text": '[placeholder="Digite sua senha"]',
        "css": "form > div:nth-of-type(2) > input",
        "xpath": "//input[@type='password']",
    },
    2: {  # Submit button
        "data_testid": '[data-testid="login-btn"]',
        "aria": '[role="button"][aria-label="Entrar"]',
        "text": "text=Entrar",
        "css": "button[type='submit']",
        "xpath": "//button[contains(text(),'Entrar')]",
    },
    3: {  # Error message
        "data_testid": '[data-testid="error-message"]',
        "aria": '[role="alert"]',
        "text": "text=Usuário ou senha inválidos",
        "css": ".error-message, .alert-danger, [class*='error']",
        "xpath": "//*[contains(@class,'error') or @role='alert']",
    },
}

PRIORITY = ["data_testid", "aria", "text", "css", "xpath"]
DEFAULT_TIMEOUT = 10000


def find_element(page: Page, action_id: int, extra_timeout: int = DEFAULT_TIMEOUT):
    """
    Attempts each selector in priority order for the given action_id.
    Logs which selector succeeded. Raises if all fail.
    """
    selectors = SELECTORS.get(action_id, {})
    last_error = None

    for key in PRIORITY:
        sel = selectors.get(key)
        if not sel:
            continue
        try:
            if key == "text" and sel.startswith("text="):
                locator = page.get_by_text(sel[5:], exact=False)
            elif key == "xpath":
                locator = page.locator(f"xpath={sel}")
            else:
                locator = page.locator(sel)

            locator.wait_for(state="visible", timeout=extra_timeout)
            log.info(f"[action={action_id}] Found via [{key}]: {sel!r}")
            return locator
        except Exception as e:
            log.debug(f"[action={action_id}] Failed [{key}]: {sel!r} — {e}")
            last_error = e
            continue

    raise RuntimeError(
        f"All selectors failed for action_id={action_id}. "
        f"Last error: {last_error}"
    )


# ── Test ──────────────────────────────────────────────────────────────────────

@pytest.mark.auth
@pytest.mark.negativo
def test_login_com_usuario_invalido(page: Page):
    """
    Fluxo negativo de autenticação.
    Verifica que a mensagem 'Usuário ou senha inválidos' aparece
    quando o usuário digita credenciais incorretas.
    """
    # Step 0: Navigate to login page
    page.goto("https://example.com/login", wait_until="domcontentloaded")

    # Step 1: Fill email field
    email_input = find_element(page, 0)
    email_input.fill("usuario@invalido.com")
    page.wait_for_timeout(300)

    # Step 2: Fill password field
    password_input = find_element(page, 1)
    password_input.fill("senha_errada_123")
    page.wait_for_timeout(300)

    # Step 3: Click submit button
    submit_btn = find_element(page, 2)
    submit_btn.click()
    page.wait_for_load_state("networkidle", timeout=15000)

    # ── Assert: error message must be visible ─────────────────────────────────
    # Hint: "A mensagem 'Usuário ou senha inválidos' deve estar visível"
    error_el = find_element(page, 3, extra_timeout=8000)
    expect(error_el).to_be_visible()
    expect(error_el).to_contain_text(re.compile(r"inválid|invalid|incorrect", re.IGNORECASE))
