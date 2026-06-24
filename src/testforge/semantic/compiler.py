"""TestForge — Playwright Python Compiler.

Le SemanticTestCase e gera script Python executavel com fallback loop.
Suporte a data-driven testing: extrai valores para JSON externo.
"""
import logging
import os
import re
import textwrap
import json as _json
from typing import Optional

from .model import SemanticTestCase, SemanticAction, SemanticTarget, FieldValueMap
from .data_extractor import _best_field_name

logger = logging.getLogger(__name__)


class PlaywrightCompiler:
    """Gera script Playwright Python a partir de SemanticTestCase."""

    def compile(
        self,
        test_case: SemanticTestCase,
        output_dir: str,
        data_file: str = "",
        field_values: Optional[dict[str, FieldValueMap]] = None,
        data_file_dict: Optional[dict] = None,
    ) -> str:
        """Compila caso de teste para script Python Playwright.

        Args:
            test_case: SemanticTestCase para compilar.
            output_dir: Diretório de saída para o script gerado.
            data_file: Caminho opcional para arquivo JSON de dados de teste.
                       Se fornecido, script lê valores do JSON em vez de hardcoding.
            field_values: Mapa opcional de campo → FieldValueMap com valores capturados.
                          Quando presente, valores de fill são substituídos pelos do mapa.
            data_file_dict: Dict opcional para injeção via --data (leitura externa).
                            Usado como fallback quando field_value está vazio.
        """
        os.makedirs(output_dir, exist_ok=True)
        safe_id = re.sub(r'[^a-zA-Z0-9_-]', '_', test_case.test_id)
        safe_id = re.sub(r'_+', '_', safe_id).strip('_').lower()
        test_name = safe_id
        filename = f"test_{test_name}.py"
        path = os.path.join(output_dir, filename)

        step_count = len(test_case.steps)
        logger.info("Compiling test_id=%s steps=%d output=%s",
                     test_case.test_id, step_count, path)
        try:
            code = self._generate(
                test_case,
                data_file=data_file,
                field_values=field_values,
                data_file_dict=data_file_dict,
            )
        except Exception as exc:
            logger.error("Compilation FAILED test_id=%s: %s",
                          test_case.test_id, exc, exc_info=True)
            raise
        code_len = len(code)
        with open(path, "w", encoding="utf-8") as f:
            f.write(code)
        logger.info("Compilation OK test_id=%s lines=%d bytes=%d",
                     test_case.test_id, code.count('\n'), code_len)
        return path

    def compile_semantic_steps(
        self,
        test_case: SemanticTestCase,
        output_dir: str,
    ) -> str:
        """Generate semantic_steps.jsonl alongside compiled script.

        Each line is a self-contained JSON object representing one
        semantic step — includes action, value, target, candidates,
        url, context, and skip_reason for full audit trail.

        Returns path to generated file.
        """
        os.makedirs(output_dir, exist_ok=True)
        path = os.path.join(output_dir, "semantic_steps.jsonl")

        with open(path, "w", encoding="utf-8") as f:
            # Header line: metadata
            metadata = {
                "type": "metadata",
                "test_id": test_case.test_id,
                "source_recording_id": test_case.source_recording_id,
                "application": test_case.application,
                "base_url": test_case.base_url,
                "step_count": len(test_case.steps),
            }
            f.write(_json.dumps(metadata, ensure_ascii=False) + "\n")

            # One step per line
            for step in test_case.steps:
                record = self._step_to_record(step)
                f.write(_json.dumps(record, ensure_ascii=False) + "\n")

        return path

    def _step_to_record(self, step: SemanticAction) -> dict:
        """Convert a SemanticAction to a JSONL record dict."""
        record: dict = {"action": step.action}
        if step.value:
            record["value"] = step.value
        if step.url:
            record["url"] = step.url
        if step.page_title:
            record["page_title"] = step.page_title
        if step.context:
            record["context"] = step.context
        if step.skip_reason:
            record["skip_reason"] = step.skip_reason
        if step.blocking:
            record["blocking"] = True
        if step.depends_on:
            record["depends_on"] = step.depends_on

        if step.target:
            t: dict = {}
            if step.target.role:
                t["role"] = step.target.role
            if step.target.accessible_name:
                t["accessible_name"] = step.target.accessible_name
            if step.target.label:
                t["label"] = step.target.label
            if step.target.placeholder:
                t["placeholder"] = step.target.placeholder
            if step.target.test_id:
                t["test_id"] = step.target.test_id
            if step.target.text:
                t["text"] = step.target.text
            if step.target.tag:
                t["tag"] = step.target.tag
            if step.target.element_id:
                t["id"] = step.target.element_id
            if step.target.name:
                t["name"] = step.target.name
            if step.target.candidates:
                t["candidates"] = [
                    {
                        "strategy": c.strategy,
                        "selector": c.selector,
                        "score": c.score,
                        "reason": c.reason,
                    }
                    for c in step.target.candidates
                ]
            record["target"] = t

        return record

    def _generate(
        self,
        tc: SemanticTestCase,
        data_file: str = "",
        field_values: Optional[dict[str, FieldValueMap]] = None,
        data_file_dict: Optional[dict] = None,
    ) -> str:
        lines = []
        lines.append('"""Teste gerado pelo TestForge — fonte de verdade: SemanticTestCase."""')
        lines.append("from playwright.sync_api import Page, expect")
        lines.append("import json, os, re")
        lines.append("from testforge.runtime.healer import resolve_selector")

        if data_file:
            # Data-driven: carrega JSON externo no script gerado
            data_path = os.path.basename(data_file)
            lines.append("")
            lines.append(f"# Dados de teste: fixture JSON externo")
            lines.append(f"_DATA_FILE = os.path.join(os.path.dirname(__file__), \"{data_path}\")")
            lines.append("_data = {}")
            lines.append("if os.path.exists(_DATA_FILE):")
            lines.append("    with open(_DATA_FILE) as f:")
            lines.append("        _raw = json.load(f)")
            lines.append("    # Suporte a formato flat e scenario-based")
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
        lines.append("")
        lines.append("    # Navegação inicial: carrega página sob teste")
        lines.append(f"    page.goto(BASE_URL)")
        lines.append("")

        step_idx = 0
        for action in tc.steps:
            # Injetar espera de overlay antes de steps de overlay
            if action.context.get("overlay_step") and not action.context.get("overlay_trigger"):
                lines.append("    # Aguarda overlay (calendário, modal, dialog)")
                lines.append("    try:")
                lines.append("        page.wait_for_selector('.cdk-overlay-container', state='visible', timeout=5000)")
                lines.append("        page.wait_for_timeout(300)")
                lines.append("    except Exception:")
                lines.append("        pass")

            if action.action == "navigation":
                # Navegação redundante ignorada — página já carregada via BASE_URL.
                continue
            elif action.action == "fill" and action.target and (action.target.tag or "").lower() == "select":
                step_idx += 1
                lines.extend(self._gen_select(action, step_idx, data_file, field_values, data_file_dict))
            elif action.action == "fill":
                step_idx += 1
                lines.extend(self._gen_fill(action, step_idx, data_file, field_values, data_file_dict))
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

    def _resolve_field_key(self, action: SemanticAction) -> str:
        """Retorna a chave do campo para lookup em field_values ou data_file_dict.

        Usa label > placeholder > campo gerado como prioridade.
        """
        if action.target:
            label = (action.target.label or "").strip()
            if label:
                return _best_field_name({"target": {"label": label}}, 0)
            placeholder = (action.target.placeholder or "").strip()
            if placeholder:
                return _best_field_name({"target": {"placeholder": placeholder}}, 0)
            name = (action.target.name or "").strip()
            if name:
                return name
            el_id = (action.target.element_id or "").strip()
            if el_id:
                return el_id
        return ""

    def _resolved_value(
        self,
        action: SemanticAction,
        idx: int,
        data_file: str,
        field_values: Optional[dict[str, FieldValueMap]] = None,
        data_file_dict: Optional[dict] = None,
    ) -> str:
        """Resolve valor de fill com prioridade: field_values > data_file > original.

        Ordem de resolução (em tempo de compilação):
        1. field_values[field_key].value  — valor capturado na gravação (preferido)
        2. data_file_dict[field_key]      — injeção externa via --data (fallback de missing_fill)
        3. data_file (caminho)            — script gerado lê JSON em runtime
        4. action.value                   — valor hardcoded original (fallback final)
        """
        value = action.value or ""
        escaped_value = value.replace('"', '\\"')
        field_key = self._resolve_field_key(action)

        # Prioridade 1: field_values com valor não-vazio
        if field_values and field_key and field_key in field_values:
            fv = field_values[field_key]
            resolved = fv.value
            # Prioridade 2: data_file_dict preenche missing_fill quando value está vazio
            if not resolved and data_file_dict and field_key in data_file_dict:
                resolved = str(data_file_dict[field_key])
            escaped_resolved = resolved.replace('"', '\\"')
            return f'"{escaped_resolved}"'

        # Prioridade 3: data_file_dict sem field_values (injeção direta)
        if data_file_dict and field_key and field_key in data_file_dict:
            escaped_resolved = str(data_file_dict[field_key]).replace('"', '\\"')
            return f'"{escaped_resolved}"'

        # Prioridade 4: script gerado lê JSON em runtime (comportamento original)
        if data_file:
            field = self._data_field_name(action)
            if field:
                return f'_data.get("{field}", "{escaped_value}")'

        # Fallback final: valor hardcoded original
        return f'"{escaped_value}"'

    def _esc(self, sel: str) -> str:
        """Escapa seletor para string Python segura (usa aspas simples)."""
        return "'" + sel.replace("\\", "\\\\").replace("'", "\\'") + "'"

    def _playwright_locator_expr(self, target: SemanticTarget | None) -> str | None:
        """Generate Playwright-native locator expression from target info.

        Returns e.g. \"page.get_by_role('button', name='Submit')\" or None.
        Priority: role+name > test_id > label > placeholder > role > text.
        """
        if not target:
            return None
        t = target

        # 1. get_by_role + name (most semantic, accessible)
        if t.role and t.accessible_name:
            role = self._esc(t.role)
            name = self._esc(t.accessible_name)
            return f"page.get_by_role({role}, name={name})"

        # 2. get_by_test_id
        if t.test_id:
            return f"page.get_by_test_id({self._esc(t.test_id)})"

        # 3. get_by_label (for input/textarea/select)
        if t.label:
            return f"page.get_by_label({self._esc(t.label)})"

        # 4. get_by_placeholder
        if t.placeholder:
            return f"page.get_by_placeholder({self._esc(t.placeholder)})"

        # 5. get_by_role without name
        if t.role:
            return f"page.get_by_role({self._esc(t.role)})"

        # 6. get_by_text for clickable elements
        if t.text and t.tag in ("button", "a", "span", "div", "label"):
            return f"page.get_by_text({self._esc(t.text[:60])})"

        return None

    def _top_css_selectors(self, target: SemanticTarget | None, limit: int = 5) -> list[str]:
        """Return top N CSS selector strings from candidates."""
        candidates = target.candidates if target else []
        sorted_c = sorted(candidates, key=lambda c: c.score, reverse=True)
        return [c.selector for c in sorted_c[:limit]]

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

    def _l0_5_role_expr(self, target: SemanticTarget | None) -> str | None:
        """Generate L0.5 get_by_role with regex fuzzy name matching.

        Returns e.g. \"page.get_by_role('button', name=re.compile(re.escape('Enviar'), re.I))\"
        or None when role/accessible_name unavailable.
        Tried AFTER primary PW locator fails, BEFORE CSS fallback loop.
        """
        if not target or not target.role:
            return None
        name = target.accessible_name or ""
        if not name or len(name) < 2:
            return None
        role = self._esc(target.role)
        escaped_name = self._esc(name[:40])
        return (f"page.get_by_role({role}, "
                f"name=re.compile(re.escape({escaped_name}), re.I))")

    def _l0_5_role_expr_str(self, target: SemanticTarget | None) -> str | None:
        """Like _l0_5_role_expr but returns raw string for expect() usage.

        Returns e.g. \"page.get_by_role('button', name=re.compile(...))\"
        without wrapping in ..._str — used when the expr is passed to expect().
        """
        return self._l0_5_role_expr(target)

    def _fingerprint_to_code(self, fingerprint: dict) -> str:
        """Serialize fingerprint dict to inline Python dict literal."""
        if not fingerprint:
            return "None"
        items = []
        for k, v in fingerprint.items():
            if isinstance(v, str):
                escaped = v.replace("\\", "\\\\").replace("'", "\\'")
                items.append(f"'{k}': '{escaped}'")
            elif isinstance(v, (int, float)):
                items.append(f"'{k}': {v}")
            elif isinstance(v, list):
                items.append(f"'{k}': {v}")
            else:
                items.append(f"'{k}': {v}")
        return "{" + ", ".join(items) + "}"

    def _gen_healer_loop(
        self,
        target: SemanticTarget | None,
        css_sels: list[str],
        step_idx: int,
        indent: str,
        action_code: str,
        wait_code: str = "",
    ) -> list[str]:
        """Generate CSS fallback lines: resolve_selector (healer) or legacy for-loop.

        Args:
            action_code: Single-line template with {sel} placeholder,
                         e.g. ``page.fill({sel}, "abc")``.
            wait_code: Optional wait line, e.g. ``page.wait_for_timeout(200)``.
        """
        lines: list[str] = []
        sels_str = ", ".join(self._esc(s) for s in css_sels)
        has_fp = bool(target and target.fingerprint)

        lines.append(f"{indent}_sels = [{sels_str}]")
        if has_fp:
            fp_code = self._fingerprint_to_code(target.fingerprint)
            lines.append(f"{indent}_fp = {fp_code}")
            lines.append(f"{indent}_best = resolve_selector(page, _sels, _fp)")
            lines.append(f"{indent}if _best:")
            lines.append(f"{indent}    {action_code.replace('{sel}', '_best')}")
            if wait_code:
                lines.append(f"{indent}    {wait_code}")
            lines.append(f"{indent}else:")
            lines.append(f'{indent}    raise AssertionError(f"step {step_idx} falhou '
                          f'— nenhum candidato corresponde ao fingerprint")')
        else:
            lines.append(f"{indent}for _sel in _sels:")
            lines.append(f"{indent}    try:")
            lines.append(f"{indent}        {action_code.replace('{sel}', '_sel')}")
            if wait_code:
                lines.append(f"{indent}        {wait_code}")
            lines.append(f"{indent}        break")
            lines.append(f"{indent}    except Exception:")
            lines.append(f"{indent}        continue")
        return lines

    def _gen_select(
        self,
        action: SemanticAction,
        idx: int,
        data_file: str = "",
        field_values: Optional[dict[str, FieldValueMap]] = None,
        data_file_dict: Optional[dict] = None,
    ) -> list[str]:
        """Gera page.select_option() com Playwright locator + fallback."""
        value = self._resolved_value(action, idx, data_file, field_values, data_file_dict)
        pw_expr = self._playwright_locator_expr(action.target)
        css_sels = self._top_css_selectors(action.target)
        lines = [f"    # Step {idx}: select ({self._data_field_name(action) or action.value})"]

        l0_5_expr = self._l0_5_role_expr(action.target)

        def _sel_call(sel: str) -> str:
            return f"page.select_option({sel}, {value})"

        if pw_expr:
            lines.append("    try:")
            lines.append(f"        {pw_expr}.select_option({value})")
            lines.append("        page.wait_for_timeout(200)")
            if css_sels:
                action_tpl = _sel_call("{sel}")
                lines.append("    except Exception:")
                if l0_5_expr:
                    lines.append("        try:")
                    lines.append(f"            {l0_5_expr}.select_option({value})")
                    lines.append("            page.wait_for_timeout(200)")
                    lines.append("        except Exception:")
                    lines.extend(self._gen_healer_loop(
                        action.target, css_sels, idx, "            ",
                        action_tpl, "page.wait_for_timeout(200)",
                    ))
                else:
                    lines.extend(self._gen_healer_loop(
                        action.target, css_sels, idx, "        ",
                        action_tpl, "page.wait_for_timeout(200)",
                    ))
            else:
                fallback = self._fallback_selector(action)
                lines.append("    except Exception:")
                lines.append(f"        page.select_option({self._esc(fallback)}, {value})")
                lines.append("        page.wait_for_timeout(200)")
        else:
            # CSS-only fallback
            if css_sels:
                action_tpl = _sel_call("{sel}")
                lines.extend(self._gen_healer_loop(
                    action.target, css_sels, idx, "    ",
                    action_tpl, "page.wait_for_timeout(200)",
                ))
            else:
                sel = self._fallback_selector(action)
                lines.append(f"    page.select_option({self._esc(sel)}, {value})")
                lines.append(f"    page.wait_for_timeout(200)")
        lines.append("")
        return lines

    def _gen_fill(
        self,
        action: SemanticAction,
        idx: int,
        data_file: str = "",
        field_values: Optional[dict[str, FieldValueMap]] = None,
        data_file_dict: Optional[dict] = None,
    ) -> list[str]:
        """Gera page.fill() com Playwright locator + fallback loop CSS."""
        value = self._resolved_value(action, idx, data_file, field_values, data_file_dict)
        pw_expr = self._playwright_locator_expr(action.target)
        css_sels = self._top_css_selectors(action.target)
        lines = [f"    # Step {idx}: fill ({self._data_field_name(action) or action.value})"]

        l0_5_expr = self._l0_5_role_expr(action.target)

        def _fill_call(sel: str) -> str:
            return f"page.fill({sel}, {value})"

        if pw_expr:
            lines.append("    try:")
            lines.append(f"        {pw_expr}.fill({value})")
            lines.append("        page.wait_for_timeout(200)")
            if css_sels:
                action_tpl = _fill_call("{sel}")
                lines.append("    except Exception:")
                if l0_5_expr:
                    lines.append("        try:")
                    lines.append(f"            {l0_5_expr}.fill({value})")
                    lines.append("            page.wait_for_timeout(200)")
                    lines.append("        except Exception:")
                    lines.extend(self._gen_healer_loop(
                        action.target, css_sels, idx, "            ",
                        action_tpl, "page.wait_for_timeout(200)",
                    ))
                else:
                    lines.extend(self._gen_healer_loop(
                        action.target, css_sels, idx, "        ",
                        action_tpl, "page.wait_for_timeout(200)",
                    ))
            else:
                fallback = self._fallback_selector(action)
                lines.append("    except Exception:")
                lines.append(f"        page.fill({self._esc(fallback)}, {value})")
                lines.append("        page.wait_for_timeout(200)")
        else:
            # CSS-only fallback
            if css_sels:
                action_tpl = _fill_call("{sel}")
                lines.extend(self._gen_healer_loop(
                    action.target, css_sels, idx, "    ",
                    action_tpl, "page.wait_for_timeout(200)",
                ))
            else:
                sel = self._fallback_selector(action)
                lines.append(f"    page.fill({self._esc(sel)}, {value})")
                lines.append(f"    page.wait_for_timeout(200)")
        lines.append("")
        return lines

    def _gen_click(self, action: SemanticAction, idx: int, is_submit: bool = False) -> list[str]:
        pw_expr = self._playwright_locator_expr(action.target)
        css_sels = self._top_css_selectors(action.target)
        causes_navigation = action.context.get("causes_navigation", False) if action.context else False
        lines = [f"    # Step {idx}: click"]

        def _gen_click_pw(pw_expr: str, indent: str = "") -> list[str]:
            """Generate click via Playwright locator."""
            clines = []
            if is_submit:
                clines.append(f"{indent}with page.expect_navigation(wait_until='load'):")
                clines.append(f"{indent}    {pw_expr}.click()")
            else:
                clines.append(f"{indent}{pw_expr}.click()")
            return clines

        def _gen_click_css(sel: str, indent: str = "") -> list[str]:
            """Generate click via CSS selector."""
            clines = []
            if is_submit:
                clines.append(f"{indent}with page.expect_navigation(wait_until='load'):")
                clines.append(f"{indent}    page.click({sel})")
            else:
                clines.append(f"{indent}page.click({sel})")
            return clines

        def _gen_wait(indent: str = "") -> str:
            if is_submit:
                return ""  # expect_navigation waits for load
            if causes_navigation:
                return f"{indent}page.wait_for_timeout(3000)  # SPA navigation"
            return f"{indent}page.wait_for_timeout(800)  # wait for DOM render"

        def _gen_click_resolve(
            sels: list[str], step_idx: int, indent: str,
        ) -> list[str]:
            """CSS fallback block — healer or legacy for-loop for click."""
            clines: list[str] = []
            sels_str = ", ".join(self._esc(s) for s in sels)
            has_fp = bool(action.target and action.target.fingerprint)
            clines.append(f"{indent}_sels = [{sels_str}]")
            if has_fp:
                fp_code = self._fingerprint_to_code(action.target.fingerprint)
                clines.append(f"{indent}_fp = {fp_code}")
                clines.append(f"{indent}_best = resolve_selector(page, _sels, _fp)")
                clines.append(f"{indent}if _best:")
                clines.extend(_gen_click_css("_best", f"{indent}    "))
                wl = _gen_wait(f"{indent}    ")
                if wl:
                    clines.append(wl)
                clines.append(f"{indent}else:")
                clines.append(f'{indent}    raise AssertionError(f"click step {step_idx} falhou '
                              f'— nenhum candidato corresponde ao fingerprint")')
            else:
                clines.append(f"{indent}for _sel in _sels:")
                clines.append(f"{indent}    try:")
                clines.extend(_gen_click_css("_sel", f"{indent}        "))
                wl = _gen_wait(f"{indent}        ")
                if wl:
                    clines.append(wl)
                clines.append(f"{indent}        break")
                clines.append(f"{indent}    except Exception:")
                clines.append(f"{indent}        continue")
            return clines

        l0_5_expr = self._l0_5_role_expr(action.target)
        if pw_expr:
            lines.append("    try:")
            lines.extend(_gen_click_pw(pw_expr, "        "))
            wl = _gen_wait("        ")
            if wl:
                lines.append(wl)
            if css_sels:
                lines.append("    except Exception:")
                if l0_5_expr:
                    lines.append("        try:")
                    lines.extend(_gen_click_pw(l0_5_expr, "            "))
                    wl_l0 = _gen_wait("            ")
                    if wl_l0:
                        lines.append(wl_l0)
                    lines.append("        except Exception:")
                    lines.extend(_gen_click_resolve(css_sels, idx, "            "))
                else:
                    lines.extend(_gen_click_resolve(css_sels, idx, "        "))
            else:
                fallback_sel = self._fallback_selector(action)
                lines.append("    except Exception:")
                lines.extend(_gen_click_css(self._esc(fallback_sel), "        "))
                wl3 = _gen_wait("        ")
                if wl3:
                    lines.append(wl3)
        else:
            # CSS-only
            if css_sels:
                lines.extend(_gen_click_resolve(css_sels, idx, "    "))
            else:
                text = (action.target.text or "")[:30] if action.target else ""
                if is_submit:
                    lines.append(f"    with page.expect_navigation(wait_until='load'):")
                    lines.append(f"        page.click({self._esc(text)})")
                else:
                    lines.append(f"    page.click({self._esc(text)})")
                    wl5 = _gen_wait("    ")
                    if wl5:
                        lines.append(wl5)
        lines.append("")
        return lines

    _BAD_ASSERT_EXPRS = {"body", "html"}

    def _gen_assert(self, action: SemanticAction, idx: int) -> list[str]:
        assert_type = action.context.get("assert_type", "textual") if action.context else "textual"
        expected = action.value or ""
        lines = [f"    # Step {idx}: assert ({assert_type})"]

        # Try Playwright locator first, fallback to CSS
        pw_expr = self._playwright_locator_expr(action.target)
        if pw_expr:
            locator_expr = pw_expr
        else:
            # L0.5: fuzzy get_by_role with regex before CSS
            l0_5_expr = self._l0_5_role_expr(action.target)
            if l0_5_expr:
                locator_expr = l0_5_expr
            else:
                css_sels = self._top_css_selectors(action.target)
                if css_sels:
                    locator_expr = f"page.locator({self._esc(css_sels[0])})"
                elif action.target and action.target.element_id:
                    locator_expr = f"page.locator({self._esc('#' + action.target.element_id)})"
                elif action.target and action.target.text:
                    locator_expr = f"page.get_by_text({self._esc(action.target.text[:60])})"
                else:
                    lines.append(f"    # SKIP: assert on unknown element — re-record with Shift+A")
                    return lines

        # Extract raw locator string from pw_expr for bad-check
        raw = locator_expr.lower()
        if any(bad in raw for bad in self._BAD_ASSERT_EXPRS):
            if "get_by" in raw or "locator" in raw:
                pass  # Playwright locators with body/html are fine (e.g. get_by_role)
            else:
                lines.append(f"    # SKIP: assert on body/page (no element selected) — re-record with Shift+A")
                return lines

        if assert_type == "textual" or assert_type == "automatico":
            lines.append(f"    expect({locator_expr}).to_contain_text({self._esc(expected)})")
        elif assert_type == "estado":
            state = action.context.get("assert_state", "enabled") if action.context else "enabled"
            state_map = {
                "checked": "to_be_checked",
                "unchecked": "not_to_be_checked",
                "disabled": "to_be_disabled",
                "enabled": "to_be_enabled",
            }
            method = state_map.get(state, "to_be_enabled")
            lines.append(f"    expect({locator_expr}).{method}()")
        elif assert_type == "visivel":
            lines.append(f"    expect({locator_expr}).to_be_visible()")

        lines.append("")
        return lines
