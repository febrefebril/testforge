"""TestForge — Playwright Python Compiler.

Le SemanticTestCase e gera script Python executavel com fallback loop.
"""
import os
import textwrap

from .model import SemanticTestCase, SemanticAction


class PlaywrightCompiler:
    """Gera script Playwright Python a partir de SemanticTestCase."""

    def compile(self, test_case: SemanticTestCase, output_dir: str) -> str:
        os.makedirs(output_dir, exist_ok=True)
        test_name = test_case.test_id.replace("-", "_").lower()
        filename = f"test_{test_name}.py"
        path = os.path.join(output_dir, filename)

        code = self._generate(test_case)
        with open(path, "w") as f:
            f.write(code)

        return path

    def _generate(self, tc: SemanticTestCase) -> str:
        lines = []
        lines.append('"""Teste gerado pelo TestForge — fonte de verdade: SemanticTestCase."""')
        lines.append("from playwright.sync_api import Page, expect")
        lines.append("")
        lines.append(f"BASE_URL = \"{tc.base_url}\"")
        lines.append("")
        lines.append("")
        lines.append(f"def test_{tc.test_id.replace('-', '_').lower()}(page: Page):")
        lines.append(f'    """{tc.application or "Fluxo gravado"} — source: {tc.source_recording_id}."""')

        step_idx = 0
        for action in tc.steps:
            if action.action == "navigation":
                lines.append(f"    page.goto(BASE_URL)")
            elif action.action == "fill":
                step_idx += 1
                lines.extend(self._gen_fill(action, step_idx))
            elif action.action == "click":
                step_idx += 1
                lines.extend(self._gen_click(action, step_idx))
            elif action.action == "assert":
                step_idx += 1
                lines.extend(self._gen_assert(action, step_idx))

        return "\n".join(lines) + "\n"

    def _gen_fill(self, action: SemanticAction, idx: int) -> list[str]:
        value = action.value or ""
        candidates = action.target.candidates if action.target else []

        # Ordena por score decrescente
        sorted_candidates = sorted(candidates, key=lambda c: c.score, reverse=True)

        if not sorted_candidates:
            # Fallback basico: placeholder ou label
            if action.target and action.target.label:
                sel = f"label:has-text(\"{action.target.label}\")"
            elif action.target and action.target.placeholder:
                sel = f"[placeholder=\"{action.target.placeholder}\"]"
            else:
                sel = "input"
            return [
                f"    # Step {idx}: fill {action.target.label if action.target else 'input'}",
                f"    page.fill(\"{sel}\", \"{value}\")",
                f"    page.wait_for_timeout(200)",
                "",
            ]

        lines = [f"    # Step {idx}: fill (value=\"{value[:30]}\")"]
        selectors = [f"\"{c.selector}\"" for c in sorted_candidates[:5]]

        lines.append(f"    _sels = [{', '.join(selectors)}]")
        lines.append("    for _sel in _sels:")
        lines.append("        try:")
        lines.append(f"            page.fill(_sel, \"{value}\")")
        lines.append("            page.wait_for_timeout(200)")
        lines.append("            break")
        lines.append("        except Exception:")
        lines.append("            continue")
        lines.append("    else:")
        lines.append(f"        raise AssertionError(f\"fill step {idx} falhou\")")
        lines.append("")
        return lines

    def _gen_click(self, action: SemanticAction, idx: int) -> list[str]:
        candidates = action.target.candidates if action.target else []
        sorted_candidates = sorted(candidates, key=lambda c: c.score, reverse=True)

        if not sorted_candidates:
            text = (action.target.text or "")[:30]
            return [
                f"    # Step {idx}: click",
                f"    page.click(\"text={text}\")",
                f"    page.wait_for_timeout(300)",
                "",
            ]

        lines = [f"    # Step {idx}: click"]
        selectors = [f"\"{c.selector}\"" for c in sorted_candidates[:5]]

        lines.append(f"    _sels = [{', '.join(selectors)}]")
        lines.append("    for _sel in _sels:")
        lines.append("        try:")
        lines.append("            page.click(_sel)")
        lines.append("            page.wait_for_timeout(300)")
        lines.append("            break")
        lines.append("        except Exception:")
        lines.append("            continue")
        lines.append("    else:")
        lines.append(f"        raise AssertionError(f\"click step {idx} falhou\")")
        lines.append("")
        return lines

    def _gen_assert(self, action: SemanticAction, idx: int) -> list[str]:
        assert_type = action.context.get("assert_type", "textual") if action.context else "textual"
        expected = action.value or ""
        lines = [f"    # Step {idx}: assert ({assert_type})"]

        candidates = action.target.candidates if action.target else []
        sorted_candidates = sorted(candidates, key=lambda c: c.score, reverse=True)

        if sorted_candidates:
            sel = sorted_candidates[0].selector
        elif action.target and action.target.element_id:
            sel = f"#{action.target.element_id}"
        elif action.target and action.target.text:
            sel = f"text={action.target.text[:30]}"
        else:
            sel = "body"

        if assert_type == "textual" or assert_type == "automatico":
            lines.append(f"    expect(page.locator(\"{sel}\")).to_contain_text(\"{expected}\")")
        elif assert_type == "estado":
            state = action.context.get("assert_state", "enabled") if action.context else "enabled"
            state_map = {
                "checked": "to_be_checked",
                "unchecked": "not_to_be_checked",
                "disabled": "to_be_disabled",
                "enabled": "to_be_enabled",
            }
            method = state_map.get(state, "to_be_enabled")
            lines.append(f"    expect(page.locator(\"{sel}\")).{method}()")
        elif assert_type == "visivel":
            lines.append(f"    expect(page.locator(\"{sel}\")).to_be_visible()")

        lines.append("")
        return lines
