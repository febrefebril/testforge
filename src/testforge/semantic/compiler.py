"""TestForge — Compilador Python Playwright.

Le SemanticTestCase e gera script Python executavel com loop de fallback.
Suporte a data-driven testing: extrai valores para JSON externo.

Fase 3: `compile_v2` opcional emite script minimalista que delega
a cadeia de fallback ao LocatorResolver em runtime. Candidatos de cada
passo sao persistidos em `<output_dir>/candidates/step_NNN.json`
e consultados em tempo de execucao. O `compile` legado permanece inalterado.
"""
import logging
import os
import re
import textwrap
import json as _json
from typing import Optional

from .data_extractor import _best_field_name
from .locator.intent import normalize_intent
from .model import FieldValueMap, SemanticAction, SemanticTarget, SemanticTestCase

logger = logging.getLogger(__name__)


def _derive_intent(action: SemanticAction) -> str:
    """Usa target.intent_text se presente, senao deriva de atributos."""
    target = action.target
    if target and target.intent_text:
        return target.intent_text
    if not target:
        return action.action
    return normalize_intent(
        action=action.action,
        role=target.role,
        accessible_name=target.accessible_name,
        label=target.label,
        placeholder=target.placeholder,
        text=target.text,
        value=action.value,
        ancestor_roles=getattr(target, "ancestor_roles", []) or [],
    )


def _candidates_dict(target: SemanticTarget) -> list[dict]:
    """Serializa target.candidates para dicts simples prontos para JSON."""
    out: list[dict] = []
    for c in target.candidates or []:
        item = {
            "strategy": c.strategy,
            "selector": c.selector,
            "score": c.score,
            "reason": c.reason,
        }
        if getattr(c, "playwright_call", None):
            item["playwright_call"] = c.playwright_call
        if getattr(c, "intent_text", None):
            item["intent_text"] = c.intent_text
        if getattr(c, "attribute_stability", None):
            item["attribute_stability"] = c.attribute_stability
        if getattr(c, "ancestor_roles", None):
            item["ancestor_roles"] = c.ancestor_roles
        if getattr(c, "backend_node_id", None) is not None:
            item["backend_node_id"] = c.backend_node_id
        out.append(item)
    return out


class PlaywrightCompiler:
    """Gera script Playwright Python a partir de SemanticTestCase."""

    # ------------------------------------------------------------------
    # Fase 3: compilador v2
    # ------------------------------------------------------------------
    def compile_v2(
        self,
        test_case: SemanticTestCase,
        output_dir: str,
        data_file: str = "",
    ) -> str:
        """Emite script minimalista que delega resolucao ao LocatorResolver.

        Efeitos colaterais:
        - escreve `<output_dir>/candidates/step_NNN.json` por passo
        - escreve `<output_dir>/test_<safe_id>.py` chamando step.click/fill/...

        O script compilado NAO contem cadeia de fallback try/except — o
        resolvedor em runtime consome os arquivos de candidato por passo.
        """
        os.makedirs(output_dir, exist_ok=True)
        candidates_dir = os.path.join(output_dir, "candidates")
        os.makedirs(candidates_dir, exist_ok=True)

        safe_id = re.sub(r"[^a-zA-Z0-9_-]", "_", test_case.test_id)
        safe_id = re.sub(r"_+", "_", safe_id).strip("_").lower()
        script_path = os.path.join(output_dir, f"test_{safe_id}.py")

        lines: list[str] = []
        lines.append('"""Compilado pelo TestForge v2 — cadeia de fallback executa no LocatorResolver em runtime."""')
        lines.append("from playwright.sync_api import Page")
        lines.append("from testforge.runtime import step")
        lines.append("")
        lines.append(f"BASE_URL = {_json.dumps(test_case.base_url)}")
        lines.append("")
        lines.append(f"def test_{safe_id}(page: Page):")
        lines.append(f'    """{test_case.application or "Fluxo gravado"} — source: {test_case.source_recording_id}."""')
        lines.append("    step.go(page, BASE_URL)")

        step_idx = 0
        for action in test_case.steps:
            if action.action == "navigation":
                continue
            if action.skip_reason:
                continue

            step_idx += 1
            step_filename = f"step_{step_idx:03d}.json"
            step_path = os.path.join(candidates_dir, step_filename)
            target = action.target or SemanticTarget()
            intent = _derive_intent(action)

            payload = {
                "step_id": f"step_{step_idx:03d}",
                "action": action.action,
                "intent_text": intent,
                "value": action.value or "",
                "url": action.url or "",
                "candidates": _candidates_dict(target),
            }
            with open(step_path, "w", encoding="utf-8") as f:
                _json.dump(payload, f, ensure_ascii=False, indent=2)

            call = self._emit_v2_call(action, intent, step_filename)
            lines.append(f"    {call}")

        code = "\n".join(lines) + "\n"
        with open(script_path, "w", encoding="utf-8") as f:
            f.write(code)
        logger.info("v2 compile OK test_id=%s steps=%d script=%s candidates_dir=%s",
                     test_case.test_id, step_idx, script_path, candidates_dir)
        return script_path

    def _emit_v2_call(self, action: SemanticAction, intent: str, step_filename: str) -> str:
        """Renderiza uma chamada `step.<verb>(page, ...)` para o script v2."""
        intent_lit = _json.dumps(intent, ensure_ascii=False)
        file_lit = _json.dumps(step_filename)
        value_lit = _json.dumps(action.value or "", ensure_ascii=False)
        tag = ((action.target.tag if action.target else "") or "").lower()

        if action.action == "click":
            return f"step.click(page, intent={intent_lit}, candidates_file={file_lit})"
        if action.action == "fill" and tag == "select":
            return f"step.select(page, intent={intent_lit}, value={value_lit}, candidates_file={file_lit})"
        if action.action == "fill":
            return f"step.fill(page, intent={intent_lit}, value={value_lit}, candidates_file={file_lit})"
        if action.action in ("select_option",):
            return f"step.select(page, intent={intent_lit}, value={value_lit}, candidates_file={file_lit})"
        if action.action == "assert":
            expected = action.target.text if action.target and action.target.text else (action.value or "")
            expected_lit = _json.dumps(expected, ensure_ascii=False)
            return f"step.assert_text(page, intent={intent_lit}, expected={expected_lit}, candidates_file={file_lit})"
        # Acao desconhecida — emite um stub para o script permanecer sintaticamente valido.
        return (
            f"# TODO: unsupported v2 action {action.action!r} — "
            f"intent={intent_lit}, candidates_file={file_lit}"
        )

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
        """Gera semantic_steps.jsonl junto com script compilado.

        Cada linha eh um objeto JSON autocontido representando um
        passo semantico — inclui action, value, target, candidates,
        url, context e skip_reason para trilha de auditoria completa.

        Retorna caminho para arquivo gerado.
        """
        os.makedirs(output_dir, exist_ok=True)
        path = os.path.join(output_dir, "semantic_steps.jsonl")

        with open(path, "w", encoding="utf-8") as f:
            # Linha de cabecalho: metadados
            metadata = {
                "type": "metadata",
                "test_id": test_case.test_id,
                "source_recording_id": test_case.source_recording_id,
                "application": test_case.application,
                "base_url": test_case.base_url,
                "step_count": len(test_case.steps),
            }
            f.write(_json.dumps(metadata, ensure_ascii=False) + "\n")

            # Um passo por linha
            for step in test_case.steps:
                record = self._step_to_record(step)
                f.write(_json.dumps(record, ensure_ascii=False) + "\n")

        return path

    def _step_to_record(self, step: SemanticAction) -> dict:
        """Converte um SemanticAction em dict de registro JSONL."""
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
        lines.append('"""Teste gerado pelo TestForge — fonte da verdade: SemanticTestCase."""')
        lines.append("from playwright.sync_api import Page, expect")
        lines.append("import json, os, re")
        lines.append("from testforge.runtime.healer import resolve_selector")

        if data_file:
            # Data-driven: carrega JSON externo no script gerado
            data_path = os.path.basename(data_file)
            lines.append("")
            lines.append(f"# Dados de teste: fixture JSON externa")
            lines.append(f"_DATA_FILE = os.path.join(os.path.dirname(__file__), \"{data_path}\")")
            lines.append("_data = {}")
            lines.append("if os.path.exists(_DATA_FILE):")
            lines.append("    with open(_DATA_FILE) as f:")
            lines.append("        _raw = json.load(f)")
            lines.append("    # Suporte a formato plano e baseado em cenario")
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

        base_safe = re.sub(r'[^a-zA-Z0-9_]', '_', tc.test_id).lower()
        base_safe = re.sub(r'_+', '_', base_safe).strip('_')

        # B29: when the recorder marked scenario boundaries with Shift+N,
        # emit one pytest function per segment so failures isolate to the
        # scenario that broke. Default (single segment) → one function as
        # before.
        segments = list(getattr(tc, "scenario_segments", None) or [])
        if not segments:
            segments = [{
                "start_step": 0,
                "end_step_exclusive": len(tc.steps),
                "name": "default",
            }]

        def _seg_safe(name: str, idx: int) -> str:
            n = re.sub(r'[^a-zA-Z0-9_]', '_', (name or "").lower())
            n = re.sub(r'_+', '_', n).strip('_')
            return n or f"cenario_{idx + 1}"

        for seg_idx, seg in enumerate(segments):
            start = max(0, int(seg.get("start_step", 0)))
            end = max(start, int(seg.get("end_step_exclusive", len(tc.steps))))
            seg_name = seg.get("name") or f"cenario_{seg_idx + 1}"
            if len(segments) == 1:
                fn_name = f"test_{base_safe}"
            else:
                fn_name = f"test_{base_safe}__{_seg_safe(seg_name, seg_idx)}"
            lines.append(f"def {fn_name}(page: Page):")
            doc_app = tc.application or "Fluxo gravado"
            scenario_doc = (
                f" — cenário: {seg_name}" if len(segments) > 1 else ""
            )
            lines.append(
                f'    """{doc_app} — source: {tc.source_recording_id}{scenario_doc}."""'
            )
            lines.append("")
            lines.append("    # Navegacao inicial: carrega pagina sob teste")
            lines.append(f"    page.goto(BASE_URL)")
            lines.append("")

            step_idx = 0
            for action in tc.steps[start:end]:
                # Injeta espera de overlay antes de passos de overlay
                if action.context.get("overlay_step") and not action.context.get("overlay_trigger"):
                    lines.append("    # Aguarda overlay (calendario, modal, dialog)")
                    lines.append("    try:")
                    lines.append("        page.wait_for_selector('.cdk-overlay-container', state='visible', timeout=5000)")
                    lines.append("        page.wait_for_timeout(300)")
                    lines.append("    except Exception:")
                    lines.append("        pass")

                if action.action == "navigation":
                    # Navegacao redundante ignorada — pagina ja carregada via BASE_URL.
                    continue
                elif action.action in ("fill", "select_option") and action.target and (action.target.tag or "").lower() == "select":
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
            lines.append("")

        return "\n".join(lines) + "\n"

    def _data_field_name(self, action: SemanticAction) -> str:
        """Obtem nome do campo JSON para o valor de uma acao fill."""
        if action.target:
            label = (action.target.label or "").strip()
            if label:
                return _best_field_name({"target": {"label": label}}, 0)
            placeholder = (action.target.placeholder or "").strip()
            if placeholder:
                return _best_field_name({"target": {"placeholder": placeholder}}, 0)
        return ""

    def _resolve_field_key(self, action: SemanticAction) -> str:
        """Retorna chave do campo para consulta em field_values ou data_file_dict.

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

        Ordem de resolucao (em tempo de compilacao):
        1. field_values[field_key].value  — valor capturado na gravacao (preferido)
        2. data_file_dict[field_key]      — injecao externa via --data (fallback missing_fill)
        3. data_file (caminho)            — script gerado le JSON em runtime
        4. action.value                   — valor hardcoded original (fallback final)
        """
        value = action.value or ""
        escaped_value = value.replace('"', '\\"')
        field_key = self._resolve_field_key(action)

        # Prioridade 1: field_values com valor nao vazio
        if field_values and field_key and field_key in field_values:
            fv = field_values[field_key]
            resolved = fv.value
            # Prioridade 2: data_file_dict preenche missing_fill quando value esta vazio
            if not resolved and data_file_dict and field_key in data_file_dict:
                resolved = str(data_file_dict[field_key])
            escaped_resolved = resolved.replace('"', '\\"')
            return f'"{escaped_resolved}"'

        # Prioridade 3: data_file_dict sem field_values (injecao direta)
        if data_file_dict and field_key and field_key in data_file_dict:
            escaped_resolved = str(data_file_dict[field_key]).replace('"', '\\"')
            return f'"{escaped_resolved}"'

        # Prioridade 4: script gerado le JSON em runtime (comportamento original)
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
        """Gera expressao de localizador nativo Playwright a partir do alvo.

        Retorna ex.: \"page.get_by_role('button', name='Submit')\" ou None.
        Prioridade: role+nome > test_id > label > placeholder > role > texto.
        """
        if not target:
            return None
        t = target

        # 1. get_by_role + nome (mais semantico, acessivel)
        if t.role and t.accessible_name:
            role = self._esc(t.role)
            name = self._esc(t.accessible_name)
            return f"page.get_by_role({role}, name={name})"

        # 2. get_by_test_id
        if t.test_id:
            return f"page.get_by_test_id({self._esc(t.test_id)})"

        # 3. get_by_label (para input/textarea/select)
        if t.label:
            return f"page.get_by_label({self._esc(t.label)})"

        # 4. get_by_placeholder
        if t.placeholder:
            return f"page.get_by_placeholder({self._esc(t.placeholder)})"

        # 5. get_by_role without name
        if t.role:
            return f"page.get_by_role({self._esc(t.role)})"

        # 6. get_by_text para elementos clicaveis
        if t.text and t.tag in ("button", "a", "span", "div", "label"):
            return f"page.get_by_text({self._esc(t.text[:60])})"

        return None

    # Sprint B (2026-06-29): seletores que sao "so placeholder" ou
    # "so name comum" e que aparecem em formularios SIOPI tipicos (multiplos
    # inputs com mesma mascara) provocam healing para tela errada. Filtrados
    # aqui — o resolvedor runtime ainda tem fingerprint para disambiguar
    # entre os candidatos mais especificos (aria-label+placeholder, etc).
    _SPRINT_B_GENERIC_PLACEHOLDERS = {
        "r$0,00", "r$ 0,00", "0,00", "dd/mm/aaaa", "dd/mm/yyyy",
        "(00) 00000-0000", "000.000.000-00", "00.000.000/0000-00",
        "00000-000", "00000000",
    }

    @classmethod
    def _is_ambiguous_only_selector(cls, selector: str) -> bool:
        """True quando seletor consiste so de placeholder/nome generico sem
        outro atributo desambiguador (aria-label, id, name customizado).

        Exemplos verdadeiros:
          input[placeholder="R$0,00"]
          input[placeholder^="DD/MM/AAAA"]

        Exemplos falsos (manter):
          input[placeholder="R$0,00"][aria-label="Renda mensal *"]
          input#renda
        """
        if not selector or "[" not in selector:
            return False
        body = selector.split("[", 1)[1]
        # Multiplos atributos = nao ambiguo
        if body.count("[") >= 1:
            return False
        if "]" not in body:
            return False
        attr_body = body.split("]", 1)[0]
        if "=" not in attr_body:
            return False
        attr_name, _, attr_value = attr_body.partition("=")
        attr_name = attr_name.rstrip("^$*~|").strip()
        attr_value = attr_value.strip().strip('"').strip("'")
        if attr_name not in ("placeholder",):
            return False
        return attr_value.lower() in cls._SPRINT_B_GENERIC_PLACEHOLDERS

    def _top_css_selectors(self, target: SemanticTarget | None, limit: int = 5) -> list[str]:
        """Retorna os N principais seletores CSS dos candidatos.

        Filtra seletores ambiguos (placeholder generico isolado) quando ja
        existe um seletor mais especifico no topo da lista — evita que o
        compiler emita uma cascata onde a 3a tentativa eh um seletor que
        casa com 2-3 inputs do form e o healing acaba acertando o errado.
        """
        candidates = target.candidates if target else []
        sorted_c = sorted(candidates, key=lambda c: c.score, reverse=True)
        sels = [c.selector for c in sorted_c[:limit]]
        if not sels:
            return sels
        has_specific = any(not self._is_ambiguous_only_selector(s) for s in sels)
        if not has_specific:
            return sels
        return [s for s in sels if not self._is_ambiguous_only_selector(s)]

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
        """Gera L0.5 get_by_role com correspondencia fuzzy regex de nome.

        Retorna ex.: \"page.get_by_role('button', name=re.compile(re.escape('Enviar'), re.I))\"
        ou None quando role/accessible_name indisponivel.
        Tentado APOS falha do localizador PW principal, ANTES do loop CSS fallback.
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
        """Similar a _l0_5_role_expr mas retorna string crua para uso com expect().

        Retorna ex.: \"page.get_by_role('button', name=re.compile(...))\"
        sem envolver em ..._str — usado quando expressao eh passada para expect().
        """
        return self._l0_5_role_expr(target)

    def _fingerprint_to_code(self, fingerprint: dict) -> str:
        """Serializa dict fingerprint para literal dict Python inline."""
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
        """Gera linhas de fallback CSS: resolve_selector (healer) ou laco for-legado.

        Argumentos:
            action_code: Template de linha unica com placeholder {sel},
                         ex.: ``page.fill({sel}, "abc")``.
            wait_code: Linha de espera opcional, ex.: ``page.wait_for_timeout(200)``.
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
            lines.append(f'{indent}    raise AssertionError(f"passo {step_idx} falhou '
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
        """Gera page.select_option() com localizador Playwright + fallback."""
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
            # Fallback apenas CSS
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
        """Gera page.fill() com localizador Playwright + loop de fallback CSS."""
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
            # Fallback apenas CSS
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
            """Gera clique via localizador Playwright."""
            clines = []
            if is_submit:
                clines.append(f"{indent}with page.expect_navigation(wait_until='load'):")
                clines.append(f"{indent}    {pw_expr}.click()")
            else:
                clines.append(f"{indent}{pw_expr}.click()")
            return clines

        def _gen_click_css(sel: str, indent: str = "") -> list[str]:
            """Gera clique via seletor CSS."""
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
                return f"{indent}page.wait_for_timeout(3000)  # Navegacao SPA"
            return f"{indent}page.wait_for_timeout(800)  # aguarda renderizacao DOM"

        def _gen_click_resolve(
            sels: list[str], step_idx: int, indent: str,
        ) -> list[str]:
            """Bloco de fallback CSS — healer ou laco legado para clique."""
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
                clines.append(f'{indent}    raise AssertionError(f"passo de clique {step_idx} falhou '
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
            # Apenas CSS
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

    _BAD_ASSERT_EXPRS = {"body", "html"}  # Expressoes de assert invalidas

    def _gen_assert(self, action: SemanticAction, idx: int) -> list[str]:
        assert_type = action.context.get("assert_type", "textual") if action.context else "textual"
        expected = action.value or ""
        lines = [f"    # Passo {idx}: assert ({assert_type})"]

        # Hotfix 22: para asserts textuais, o VALOR esperado e o sinal — texto
        # visivel na tela. Preferimos localizador text-based (get_by_text) que
        # busca o elemento PELO TEXTO diretamente, mesmo quando o overlay
        # gerou um css_path posicional nao-unico (ex.: 5 asserts diferentes
        # todos apontando para `div:nth-of-type(1) > .text-size-smaller`).
        text_first = (assert_type in ("textual", "automatico")) and bool(expected)

        if text_first:
            locator_expr = f"page.get_by_text({self._esc(expected)}, exact=False).first"
        else:
            # Tenta localizador Playwright primeiro, fallback para CSS
            pw_expr = self._playwright_locator_expr(action.target)
            if pw_expr:
                locator_expr = pw_expr
            else:
                # L0.5: get_by_role fuzzy com regex antes de CSS
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
                        lines.append(f"    # SKIP: assert em elemento desconhecido — regrave com Shift+A")
                        return lines

        # Extrai string crua do localizador de pw_expr para verificacao
        raw = locator_expr.lower()
        if any(bad in raw for bad in self._BAD_ASSERT_EXPRS):
            if "get_by" in raw or "locator" in raw:
                pass  # Localizadores Playwright com body/html sao ok (ex.: get_by_role)
            else:
                lines.append(f"    # SKIP: assert em body/pagina (nenhum elemento selecionado) — regrave com Shift+A")
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
