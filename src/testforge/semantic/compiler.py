"""TestForge — Playwright Python Compiler.

Le SemanticTestCase e gera script Python executavel com fallback loop.
Suporte a data-driven testing: extrai valores para JSON externo.
"""
import os
import re
import textwrap
import json as _json

from .model import SemanticTestCase, SemanticAction
from .data_extractor import _best_field_name


class PlaywrightCompiler:
    """Gera script Playwright Python a partir de SemanticTestCase."""

    def compile(
        self,
        test_case: SemanticTestCase,
        output_dir: str,
        data_file: str = "",
    ) -> str:
        """Compile test case to Playwright Python script.

        Args:
            test_case: SemanticTestCase to compile.
            output_dir: Output directory for the generated script.
            data_file: Optional path to JSON test data file.
                       If provided, script reads values from JSON instead of hardcoding.
        """
        os.makedirs(output_dir, exist_ok=True)
        safe_id = re.sub(r'[^a-zA-Z0-9_-]', '_', test_case.test_id)
        safe_id = re.sub(r'_+', '_', safe_id).strip('_').lower()
        test_name = safe_id
        filename = f"test_{test_name}.py"
        path = os.path.join(output_dir, filename)

        code = self._generate(test_case, data_file=data_file)
        with open(path, "w") as f:
            f.write(code)

        return path

    def _generate(self, tc: SemanticTestCase, data_file: str = "") -> str:
        lines = []
        lines.append('"""Teste gerado pelo TestForge — fonte de verdade: SemanticTestCase."""')
        lines.append("from playwright.sync_api import Page, expect")
        lines.append("import json, os")

        if data_file:
            # Data-driven: load external JSON
            data_path = os.path.basename(data_file)
            lines.append("")
            lines.append(f"# Test data: external JSON fixture")
            lines.append(f"_DATA_FILE = os.path.join(os.path.dirname(__file__), \"{data_path}\")")
            lines.append("_data = {}")
            lines.append("if os.path.exists(_DATA_FILE):")
            lines.append("    with open(_DATA_FILE) as f:")
            lines.append("        _raw = json.load(f)")
            lines.append("    # Support both flat and scenario-based formats")
            lines.append("    if \"scenarios\" in _raw:")
            lines.append("        _data = _raw[\"scenarios\"].get(\"default\", {})")
            lines.append("    elif \"fields\" in _raw:")
            lines.append("        _data = _raw[\"fields\"]")
            lines.append("    else:")
            lines.append("        _data = _raw")
            lines.append("")

        lines.append("")
        lines.append(f"BASE_URL = \"{tc.base_url}\"")
        lines.append("")

        safe_name = re.sub(r'[^a-zA-Z0-9_]', '_', tc.test_id).lower()
        safe_name = re.sub(r'_+', '_', safe_name).strip('_')
        lines.append(f"def test_{safe_name}(page: Page):")
        lines.append(f'    """{tc.application or "Fluxo gravado"} — source: {tc.source_recording_id}."""')

        step_idx = 0
        for action in tc.steps:
            if action.action == "navigation":
                lines.append(f"    page.goto(BASE_URL)")
            elif action.action == "fill" and action.target and (action.target.tag or "").lower() == "select":
                step_idx += 1
                lines.extend(self._gen_select(action, step_idx, data_file))
            elif action.action == "fill":
                step_idx += 1
                lines.extend(self._gen_fill(action, step_idx, data_file))
            elif action.action == "click":
                step_idx += 1
                is_submit = action.context.get("is_submit", False) if action.context else False
                lines.extend(self._gen_click(action, step_idx, is_submit=is_submit))
            elif action.action == "assert":
                step_idx += 1
                lines.extend(self._gen_assert(action, step_idx))

        return "\n".join(lines) + "\n"

    def _data_field_name(self, action: SemanticAction) -> str:
        """Get the JSON field name for a fill action's value."""
        if action.target:
            label = (action.target.label or "").strip()
            if label:
                return _best_field_name({"target": {"label": label}}, 0)
            placeholder = (action.target.placeholder or "").strip()
            if placeholder:
                return _best_field_name({"target": {"placeholder": placeholder}}, 0)
        return ""

    def _resolved_value(self, action: SemanticAction, idx: int, data_file: str) -> str:
        """Resolve fill value: from JSON data_file or hardcoded fallback."""
        value = action.value or ""
        escaped_value = value.replace('"', '\\"')
        if data_file:
            field = self._data_field_name(action)
            if field:
                return f'_data.get("{field}", "{escaped_value}")'
        return f'"{escaped_value}"'

    def _esc(self, sel: str) -> str:
        """Escapa seletor para string Python segura (usa aspas simples)."""
        return "'" + sel.replace("\\", "\\\\").replace("'", "\\'") + "'"

    def _fallback_selector(self, action: SemanticAction) -> str:
        t = action.target
        tag = (t.tag or "").lower() if t else ""
        if tag == "select":
            if t and t.name:
                return f"select[name='{t.name}']"
            if t and t.element_id:
                return f"#{t.element_id}"
            return "select"
        if t and t.label and t.element_id:
            return f"label[for='{t.element_id}']"
        if t and t.label:
            return f"label:has-text('{t.label}') + input"
        if t and t.placeholder:
            return f"[placeholder='{t.placeholder}']"
        if t and t.element_id:
            return f"#{t.element_id}"
        return "input"

    def _gen_select(self, action: SemanticAction, idx: int, data_file: str = "") -> list[str]:
        """Generate page.select_option() for <select> elements."""
        value = self._resolved_value(action, idx, data_file)
        candidates = action.target.candidates if action.target else []
        sorted_candidates = sorted(candidates, key=lambda c: c.score, reverse=True)

        if not sorted_candidates:
            sel = self._fallback_selector(action)
            lines = [
                f"    # Step {idx}: select {action.target.label if action.target else 'select'}",
                f"    page.select_option({self._esc(sel)}, {value})",
                f"    page.wait_for_timeout(200)",
                "",
            ]
            return lines

        selectors = [self._esc(c.selector) for c in sorted_candidates[:5]]
        lines = [f"    # Step {idx}: select ({self._data_field_name(action) or action.value})"]
        lines.append(f"    _sels = [{', '.join(selectors)}]")
        lines.append("    for _sel in _sels:")
        lines.append("        try:")
        lines.append(f"            page.select_option(_sel, {value})")
        lines.append("            page.wait_for_timeout(200)")
        lines.append("            break")
        lines.append("        except Exception:")
        lines.append("            continue")
        lines.append("    else:")
        lines.append(f"        raise AssertionError(f\"select step {idx} falhou "
                      f"— selectors tried: {{_sels}}\")")
        lines.append("")
        return lines

    def _gen_fill(self, action: SemanticAction, idx: int, data_file: str = "") -> list[str]:
        value = self._resolved_value(action, idx, data_file)
        candidates = action.target.candidates if action.target else []

        # Ordena por score decrescente
        sorted_candidates = sorted(candidates, key=lambda c: c.score, reverse=True)

        if not sorted_candidates:
            sel = self._fallback_selector(action)
            lines = [
                f"    # Step {idx}: fill {action.target.label if action.target else 'input'}",
                f"    page.fill({self._esc(sel)}, {value})",
                f"    page.wait_for_timeout(200)",
                "",
            ]
            return lines

        lines = [f"    # Step {idx}: fill ({self._data_field_name(action) or action.value})"]
        selectors = [self._esc(c.selector) for c in sorted_candidates[:5]]

        lines.append(f"    _sels = [{', '.join(selectors)}]")
        lines.append("    for _sel in _sels:")
        lines.append("        try:")
        lines.append(f"            page.fill(_sel, {value})")
        lines.append("            page.wait_for_timeout(200)")
        lines.append("            break")
        lines.append("        except Exception:")
        lines.append("            continue")
        lines.append("    else:")
        lines.append(f"        raise AssertionError(f\"fill step {idx} falhou "
                      f"— selectors tried: {{_sels}}\")")
        lines.append("")
        return lines

    def _gen_click(self, action: SemanticAction, idx: int, is_submit: bool = False) -> list[str]:
        candidates = action.target.candidates if action.target else []
        sorted_candidates = sorted(candidates, key=lambda c: c.score, reverse=True)

        if not sorted_candidates:
            text = (action.target.text or "")[:30]
            lines = [
                f"    # Step {idx}: click",
                f"    page.click({self._esc(text)})",
                f"    page.wait_for_timeout(300)",
            ]
            if is_submit:
                lines.append(f"    page.wait_for_load_state('networkidle')")
            lines.append("")
            return lines

        lines = [f"    # Step {idx}: click"]
        selectors = [self._esc(c.selector) for c in sorted_candidates[:5]]

        lines.append(f"    _sels = [{', '.join(selectors)}]")
        lines.append("    for _sel in _sels:")
        lines.append("        try:")
        lines.append("            page.click(_sel)")
        lines.append("            page.wait_for_timeout(300)")
        if is_submit:
            lines.append("            page.wait_for_load_state('networkidle')")
        lines.append("            break")
        lines.append("        except Exception:")
        lines.append("            continue")
        lines.append("    else:")
        lines.append(f"        raise AssertionError(f\"click step {idx} falhou "
                      f"— selectors tried: {{_sels}}\")")
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
            lines.append(f"    expect(page.locator({self._esc(sel)})).to_contain_text({self._esc(expected)})")
        elif assert_type == "estado":
            state = action.context.get("assert_state", "enabled") if action.context else "enabled"
            state_map = {
                "checked": "to_be_checked",
                "unchecked": "not_to_be_checked",
                "disabled": "to_be_disabled",
                "enabled": "to_be_enabled",
            }
            method = state_map.get(state, "to_be_enabled")
            lines.append(f"    expect(page.locator({self._esc(sel)})).{method}()")
        elif assert_type == "visivel":
            lines.append(f"    expect(page.locator({self._esc(sel)})).to_be_visible()")

        lines.append("")
        return lines
