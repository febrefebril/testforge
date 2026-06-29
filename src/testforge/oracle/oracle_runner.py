"""TestForge — Executor Oracle."""
from dataclasses import dataclass, field
from typing import Optional

from playwright.sync_api import Page


@dataclass
class OracleResult:
    oracle_type: str
    status: str  # passed, failed, inconclusive
    expected: str = ""
    actual: str = ""
    message: str = ""


class OracleRunner:
    """Executa oracles pos-acao para validar resultado."""

    def __init__(self, page: Page):
        self._page = page

    def run_visual_dom(self, expected_selector: str, expected_text: str = "") -> OracleResult:
        """Oracle visual/DOM: verifica se elemento esperado esta visivel ou contem texto."""
        try:
            locator = self._page.locator(expected_selector)
            if not locator.count():
                return OracleResult(
                    oracle_type="visual_dom", status="failed",
                    expected=expected_selector,
                    message=f"Elemento nao encontrado: {expected_selector}"
                )
            el = locator.first
            if not el.is_visible():
                return OracleResult(
                    oracle_type="visual_dom", status="failed",
                    expected="visible",
                    actual="hidden",
                    message=f"Elemento {expected_selector} nao visivel"
                )
            if expected_text:
                import re
                text = el.text_content() or ""
                # Normaliza espacos antes de comparar — DOM text_content() preserva
                # espacamento bruto incluindo prefixos de texto de icone e espacos extras entre
                # nos. Playwright has-text() normaliza internamente; espelhamos isso.
                _norm = lambda s: re.sub(r'\s+', ' ', s).strip().lower()
                if _norm(expected_text) not in _norm(text):
                    return OracleResult(
                        oracle_type="visual_dom", status="failed",
                        expected=expected_text,
                        actual=text[:100],
                        message=f"Texto esperado '{expected_text}' nao encontrado"
                    )
            return OracleResult(
                oracle_type="visual_dom", status="passed",
                expected=expected_text or "visible",
                message="Elemento visivel e texto OK"
            )
        except Exception as e:
            return OracleResult(
                oracle_type="visual_dom", status="inconclusive",
                message=str(e)[:100]
            )

    def run_business_state(self, selector: str, expected_value: str,
                           extract_js: str = "el => el.textContent.trim()") -> OracleResult:
        """Oracle business_state: extrai valor via JS e compara com esperado."""
        try:
            actual = self._page.evaluate(f"""
                (() => {{
                    const el = document.querySelector('{selector}');
                    if (!el) return null;
                    return ({extract_js})(el);
                }})()
            """)
            if actual is None:
                return OracleResult(
                    oracle_type="business_state", status="failed",
                    expected=expected_value,
                    message=f"Elemento {selector} nao encontrado"
                )
            actual_str = str(actual).strip()
            if expected_value in actual_str:
                return OracleResult(
                    oracle_type="business_state", status="passed",
                    expected=expected_value, actual=actual_str[:100],
                    message="Valor corresponde"
                )
            return OracleResult(
                oracle_type="business_state", status="failed",
                expected=expected_value, actual=actual_str[:100],
                message=f"Valor diverge: esperado '{expected_value}'"
            )
        except Exception as e:
            return OracleResult(
                oracle_type="business_state", status="inconclusive",
                message=str(e)[:100]
            )

    def run_all(self, assertions: list[dict]) -> list[OracleResult]:
        """Executa multiplos oracles definidos em assertions."""
        results = []
        for a in assertions:
            atype = a.get("type", "visual_dom")
            if atype == "visual_dom":
                r = self.run_visual_dom(
                    a.get("selector", "body"),
                    a.get("expected", "")
                )
            elif atype == "business_state":
                r = self.run_business_state(
                    a.get("selector", "body"),
                    a.get("expected", ""),
                    a.get("extract_js", "el => el.textContent.trim()")
                )
            else:
                r = OracleResult(oracle_type=atype, status="inconclusive",
                                 message=f"Tipo desconhecido: {atype}")
            results.append(r)
        return results
