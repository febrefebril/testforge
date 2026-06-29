"""TestForge — StepExecutor.

Executa um step com a estrategia apropriada por acao.
Nao decide se o step passou semanticamente — isso e papel da pos-condicao.
Usa field_value_map para ligar campo → valor com intencao e fallback.
"""
from __future__ import annotations
import logging
import re
from typing import Optional

logger = logging.getLogger(__name__)


# CS-1 / hotfix 18: deteccao de mask vive aqui, nao em 4 helpers de fill
# diferentes. Qualquer coisa que precise saber "este input tem mask, e como?"
# chama _detect_mask_kind. Qualquer coisa que precise preencher um input chama
# _fill_masked. Nao ha outro caminho. Recurrencias hotfix-por-helper
# (16, 17) aconteceram porque a mesma logica vivia em 4 lugares e divergiu.
_DATE_MASK_PLACEHOLDER_HINTS = (
    "dd/mm", "mm/dd", "aaaa", "yyyy", "__/__/____", "dd/mm/aaaa",
)
# `currency` e o mask_kind para qualquer input cuja mask remove nao-digitos
# e digita digitos crus. Cobre moeda BRL (R$ 0,00), CPF
# (000.000.000-00), CNPJ (00.000.000/0000-00), CEP (00000-000), telefone
# brasileiro ((00) 00000-0000). Mesmo algoritmo — nome mantido estavel para
# back-compat com os testes / spans existentes.
_CURRENCY_MASK_PLACEHOLDER_HINTS = (
    "r$", "0,00",          # currency
    "000.000.000",         # CPF
    "00.000.000/",         # CNPJ
    "00000-000",           # CEP
    "(00) ",               # phone with area code
    "(0",                  # phone (loose)
    "00.000.000-",         # generic Brazilian doc with hyphen
)


class StepExecutor:
    """Executa uma unica acao no browser via Playwright."""

    DEFAULT_TIMEOUT = 5000

    def __init__(self, page):
        self.page = page

    def _primary_selector(self, step) -> str:
        cands = self._all_selectors(step)
        return cands[0] if cands else ""

    def _all_selectors(self, step) -> list:
        """Retorna TODOS os seletores candidatos do alvo do step, melhor primeiro."""
        if step.target and getattr(step.target, "candidates", None):
            return [c.selector for c in step.target.candidates if c.selector]
        return []

    def _canonical(self, s: str) -> str:
        """Normaliza string para comparacao — minuscula, remove espacos, colapsa whitespace."""
        if not s:
            return ""
        import re
        return re.sub(r'[-_\s]+', '_', s.strip().lower())

    def _resolve_field_value(self, step, data_values: dict, field_value_map: dict) -> tuple:
        """Resolve valor e intencao para campo do step usando field_value_map + data_values.

        Prioridade:
        1. Correspondencia exata em field_value_map por identificadores de alvo (name, aria_label, placeholder, id)
        2. Correspondencia exata em data_values pelos mesmos identificadores
        3. Correspondencia de chave canonica em field_value_map
        4. Correspondencia de chave canonica em data_values
        5. Correspondencia de substring em data_values (fallback legado)

        Retorna (value, intention) — ambas strings vazias se sem correspondencia.
        """
        # Collect identifiers from step target (use getattr for test fakes)
        ids = {}
        if step.target:
            for attr, key in [('name', 'name'), ('accessible_name', 'aria_label'),
                              ('placeholder', 'placeholder'), ('element_id', 'id'),
                              ('label', 'label')]:
                val = getattr(step.target, attr, None) or ''
                if val:
                    ids[key] = val

        if not ids and not data_values and not field_value_map:
            return ("", "")

        # Auxiliar: tenta correspondência contra um dict (field_value_map ou data_values)
        def _unwrap(entry) -> tuple:
            """CS-4c / hotfix 19: stc.field_values tem chaves para instancias
            FieldValueMap dataclass, nao dicts simples. O caminho de codigo anterior

                if isinstance(entry, dict):
                    return (entry["value"], entry["intention"])
                return (str(entry), "")

            silenciosamente pegou o ramo str(entry) para todo objeto
            FieldValueMap e digitou o __repr__ da dataclass (ex:
            "FieldValueMap(field_key='...', value='1.000,00', ...)" —
            ~370 chars com ~19 digitos) no input mascarado. A mask
            removeu os digitos, produzindo R$ 1.000.001.000.000.012,00
            ou similar. O usuario viu "concatenacao" — era na verdade
            uma serializacao repr.

            Este unwrap trata dict, objetos com formato FieldValueMap
            (qualquer coisa com atributo `.value`), e escalares simples.
            """
            if isinstance(entry, dict):
                return (entry.get("value", "") or "",
                        entry.get("intention", "") or "")
            value = getattr(entry, "value", None)
            if value is not None:
                return (str(value),
                        str(getattr(entry, "intention", "") or ""))
            return (str(entry), "")

        def _match(identifiers: dict, target_dict: dict) -> tuple:
            # Tenta cada identificador em ordem de prioridade
            for id_type in ("name", "aria_label", "label", "placeholder", "id"):
                id_val = identifiers.get(id_type, "")
                if not id_val:
                    continue
                # Exact match
                if id_val in target_dict:
                    return _unwrap(target_dict[id_val])
                # Canonical match
                cid = self._canonical(id_val)
                for key in target_dict:
                    if self._canonical(key) == cid:
                        return _unwrap(target_dict[key])
                # Substring match (data_values only, not field_value_map)
                if target_dict is data_values:
                    for key, val in target_dict.items():
                        if cid and (cid in self._canonical(key) or self._canonical(key) in cid):
                            return _unwrap(val)
            return ("", "")

        if field_value_map:
            val, intention = _match(ids, field_value_map)
            if val:
                return (val, intention)

        if data_values:
            val, intention = _match(ids, data_values)
            if val:
                return (val, intention)

        # Last resort: try data_values by canonical step index
        ctx = getattr(step, "context", {}) or {}
        if data_values and ctx.get("missing_fill"):
            fill_label = ctx.get("fill_label", "")
            if fill_label:
                for key, val in data_values.items():
                    if fill_label and (key in fill_label or fill_label in key):
                        return (str(val), fill_label)

        return ("", "")

    def _inject_intention(self, step, value: str, intention: str) -> None:
        """Armazena intencao resolvida no contexto do step para healing/fallback."""
        ctx = getattr(step, "context", {}) or {}
        if value:
            ctx["resolved_value"] = value
        if intention:
            ctx["resolved_intention"] = intention
        step.context = ctx

    def execute(self, step, base_url: str = "", data_values: Optional[dict] = None,
                field_value_map: Optional[dict] = None) -> str:
        data_values = data_values or {}
        field_value_map = field_value_map or {}
        action = step.action
        selectors = self._all_selectors(step)
        selector = selectors[0] if selectors else ""

        # Delega para handler de componente registrado quando o step alvo um componente de framework conhecido.
        # Handlers declaram ownership via detect() — apenas o primeiro handler correspondente e usado.
        if action == "click":
            from ..handlers import detect_handler
            _handler = detect_handler(step)
            if _handler is not None:
                return _handler.execute(self.page, step)

        if action == "navigation":
            url = step.url or base_url
            if url and url != self.page.url:
                self.page.goto(url)
                self.page.wait_for_timeout(400)
            return ""

        if action == "click":
            from ..healing import MaterialComponentDetector
            detector = MaterialComponentDetector()

            tag = (step.target.tag or "").lower() if step.target else ""
            # Radio buttons (Angular Material mat-radio-button) devem ser clicados, nao preenchidos.
            # Detectados pelo prefixo element_id ou seletor do top candidate contendo mat-radio-button.
            # Nao precisa de guard de candidates — detector verifica element_id e selector.
            _el_id = (getattr(step.target, "element_id", "") or "") if step.target else ""
            _top_sel = (step.target.candidates[0].selector if step.target and step.target.candidates else "")
            _is_radio = detector.is_material_radio_button(_el_id, _top_sel)
            if tag in ("input", "textarea") and not _is_radio:
                ctx = getattr(step, "context", {}) or {}

                # Resolve valor + intencao do field_value_map + data_values
                resolved_val, intention = self._resolve_field_value(step, data_values, field_value_map)
                self._inject_intention(step, resolved_val, intention)

                # Prioridade 1: form_values do submit capture
                form_vals = ctx.get("form_values") or {}
                if form_vals:
                    for name, val in form_vals.items():
                        if self._fill_input(self.page, label=name, value=val):
                            return f"submit_form:{name}"

                # Prioridade 2: valor resolvido do field_value_map.
                # Usa accessible_name/label/placeholder do target como fill label —
                # a string intention e uma descricao legivel, nao um aria-label valido.
                if resolved_val:
                    fill_label = (
                        ((step.target.accessible_name or "") if step.target else "")
                        or ((step.target.label or "") if step.target else "")
                        or ((step.target.placeholder or "") if step.target else "")
                        or intention
                    )
                    if self._fill_input(self.page, label=fill_label, value=resolved_val):
                        return f"field_map:{fill_label}"

                # Prioridade 3: missing_fill → corresponde data_values por fill_label
                if ctx.get("missing_fill"):
                    fill_label = ctx.get("fill_label", "")
                    if fill_label and data_values:
                        for k, v in data_values.items():
                            if fill_label and (k in fill_label or fill_label in k):
                                self._fill_input(page=self.page, label=k, value=str(v))
                                return selector

                # Prioridade 4: fallback aria-label
                if selector.startswith("[aria-"):
                    return self._fill_by_aria_label(step, data_values) or selector

                # Prioridade 5: tenta data fill por label/placeholder
                if data_values:
                    if self._try_data_fill(step, selector, data_values):
                        return selector

                # Prioridade 6: se temos valor resolvido mas todas as estrategias falharam,
                # levanta com contexto de intencao para fallback de healing
                if resolved_val:
                    raise ValueError(
                        f"fill_failed: '{intention or 'unknown'}' value='{resolved_val}' "
                        f"selector='{selector}' — nenhuma estrategia funcionou"
                    )
            return self._execute_click(step, selectors)

        if action == "fill":
            # Resolve valor + intencao
            resolved_val, intention = self._resolve_field_value(step, data_values, field_value_map)
            # step.value tem prioridade — field_value_map so preenche quando step esta vazio.
            # Isso evita que field_value_map sobrescreva fills posteriores do mesmo campo
            # (ex: recording tem 3 fills: 10.000 → 100.000 → 1.000.000 no mesmo input).
            use_val = step.value or resolved_val
            self._inject_intention(step, use_val, intention)
            return self._execute_fill(step, selectors, data_values, field_value_map)

        if action == "select_option":
            return self._execute_select(step, selector)

        if action == "assert":
            if selector:
                try:
                    self.page.locator(selector).first.wait_for(state="visible", timeout=self.DEFAULT_TIMEOUT)
                except Exception:
                    pass
            return selector

        raise NotImplementedError(f"acao desconhecida: {action}")

    def _fill_input(self, page, label: str, value: str) -> bool:
        """Encontra um input por aria-label / placeholder / name e preenche.

        CS-1: tratamento de mask, limpar-antes-de-digitar e normalizacao de valor
        vivem em `_fill_masked`. O trabalho deste metodo e apenas selecao de locator.
        """
        patterns = [
            f'input[aria-label="{label}"]',
            f'textarea[aria-label="{label}"]',
            f'input[placeholder="{label}"]',
            f'textarea[placeholder="{label}"]',
        ]
        if label and not label.startswith("step_"):
            patterns.extend([
                f'input[name="{label}"]',
                f'textarea[name="{label}"]',
            ])
        for sel_pattern in patterns:
            try:
                el = page.locator(sel_pattern)
                if el.count() == 1:
                    self._fill_masked(
                        el, value,
                        fill_path="_fill_input",
                        selector_used=sel_pattern,
                    )
                    return True
            except Exception:
                continue
        return False

    def _fill_by_aria_label(self, step, data_values) -> Optional[str]:
        """Tenta encontrar e preencher um input por aria-label das chaves de data_values.

        CS-1: tratamento de mask delegado a `_fill_masked`.
        """
        if not data_values:
            return None
        for key, val in data_values.items():
            try:
                sel_pattern = (
                    f'input[aria-label="{key}"], textarea[aria-label="{key}"]'
                )
                el = self.page.locator(sel_pattern)
                if el.count() == 1:
                    self._fill_masked(
                        el, str(val),
                        fill_path="_fill_by_aria_label",
                        selector_used=sel_pattern,
                    )
                    return f'aria-label="{key}"'
            except Exception:
                continue
        return None

    def _try_data_fill(self, step, selector, data_values) -> bool:
        """Tenta preencher a partir de data_values. Retorna True se fill foi tentado."""
        if not data_values:
            return False
        label = ""
        if step.target:
            label = getattr(step.target, "label", "") or getattr(step.target, "placeholder", "")
        fill_val = data_values.get(label, "")
        if not fill_val:
            for k, v in data_values.items():
                if label and k in label:
                    fill_val = str(v)
                    break
        if not fill_val:
            return False

        try:
            el = self.page.locator(selector).first
            # CS-1: mask detection + clear + digit normalization in one place.
            self._fill_masked(
                el, str(fill_val),
                fill_path="_try_data_fill",
                selector_used=selector,
            )
            return True
        except Exception:
            return False

    # ----------------------------------------------------------------
    # CS-1 / hotfix 18 — fonte unica de verdade para fills com mask.
    # Os quatro helpers de fill (_execute_fill, _fill_input,
    # _fill_by_aria_label, _try_data_fill) chamam _fill_masked. Nenhum
    # deles reimplementa deteccao de mask ou a sequencia limpar-e-digitar.
    # Quando um bug aparece, vive em exatamente um lugar. Telemetria CS-3
    # esta aqui para que todo fill seja auditavel de .testforge/spans.jsonl.
    # ----------------------------------------------------------------

    def _detect_mask_kind(self, el) -> tuple[str, str]:
        """Retorna (mask_kind, mask_detect) onde:

        mask_kind   ∈ {"currency", "date", "none"}
        mask_detect ∈ {"attribute", "placeholder", "date_placeholder", "none"}

        Deteccao de mask consulta o atributo HTML `currencymask` primeiro
        (camada de dados Caixa legada) e faz fallback para inspecao de
        placeholder para que inputs Material sem o atributo (ex:
        SIOPI `<input placeholder="R$0,00">`) ainda sejam reconhecidos.
        """
        try:
            if el.get_attribute("currencymask") is not None:
                return "currency", "attribute"
        except Exception:
            pass
        try:
            placeholder = (el.get_attribute("placeholder") or "").lower()
        except Exception:
            placeholder = ""
        if any(p in placeholder for p in _DATE_MASK_PLACEHOLDER_HINTS):
            return "date", "date_placeholder"
        if any(p in placeholder for p in _CURRENCY_MASK_PLACEHOLDER_HINTS):
            return "currency", "placeholder"
        return "none", "none"

    def _fill_masked(self, el, value: str, *, fill_path: str,
                     selector_used: str = "") -> str:
        """Preenche `el` com `value`, respeitando tipo de mask. Retorna mask_kind.

        Sempre:
        - Limpa o campo via triplo-clique antes de digitar para que re-execucoes
          e retentativas de healing nao concatenem teclas.
        - Para masks de moeda: digita digitos crus extraidos via regex —
          a mask formata em "R$ X.XXX,XX".
        - Para masks de data: digita o valor formatado com barras —
          a mask usa as barras para posicionar o cursor.
        - Para inputs sem mask: chama `el.fill` que limpa + define.
        - Emite um span `fill.attempted` com trilha de auditoria completa.

        Funcao unica. Quatro chamadores. Nenhuma divergencia possivel por
        construcao. Veja CS-1 / `.planning/CONSOLIDATION-SPRINT.md`.
        """
        value = "" if value is None else str(value)
        mask_kind, mask_detect = self._detect_mask_kind(el)
        cleared = False
        type_val: Optional[str] = None
        status = "ok"
        error_msg = ""

        try:
            if mask_kind == "none":
                el.fill(value, timeout=self.DEFAULT_TIMEOUT)
                self.page.wait_for_timeout(150)
                # el.fill clears implicitly.
                cleared = True
                type_val = value
            else:
                el.click()
                self.page.wait_for_timeout(150)
                el.click(click_count=3)
                self.page.wait_for_timeout(80)
                cleared = True
                if mask_kind == "date":
                    type_val = value
                else:  # currency
                    digits = re.sub(r"[^0-9]", "", value)
                    type_val = digits if digits else value
                el.press_sequentially(type_val, delay=50)
                self.page.keyboard.press("Tab")
                self.page.wait_for_timeout(200)
        except Exception as exc:
            status = "error"
            error_msg = str(exc)[:200]
            raise
        finally:
            self._emit_fill_span(
                fill_path=fill_path, selector_used=selector_used,
                mask_kind=mask_kind, mask_detect=mask_detect,
                cleared=cleared, type_val=type_val, value=value,
                status=status, error_msg=error_msg,
            )
        return mask_kind

    def _emit_fill_span(self, *, fill_path: str, selector_used: str,
                        mask_kind: str, mask_detect: str, cleared: bool,
                        type_val: Optional[str], value: str,
                        status: str, error_msg: str) -> None:
        """CS-3 — span JSONL fill.attempted para que a proxima sessao de debug
        possa responder "qual caminho de fill executou no step N?" sem re-executar.

        `value` e `type_val` brutos sao ocultados — apenas length e o
        bucket value_kind sao logados. Strings de selector sao truncadas.
        """
        try:
            from testforge.metrics.telemetry import get_tracer
            tracer = get_tracer()
            if not tracer.enabled:
                return
            attrs = {
                "fill_path": fill_path,
                "selector_used": (selector_used or "")[:200],
                "mask_kind": mask_kind,
                "mask_detect": mask_detect,
                "cleared": cleared,
                "value_len": len(value or ""),
                "type_val_len": len(type_val or "") if type_val is not None else 0,
                "status": status,
            }
            if error_msg:
                attrs["error.message"] = error_msg
            with tracer.start_span("fill.attempted") as span:
                for k, v in attrs.items():
                    span.set_attribute(k, v)
        except Exception:
            # Telemetria nunca deve quebrar a execucao.
            logger.debug("telemetry emit failed for fill.attempted", exc_info=True)

    def _execute_click(self, step, selectors):
        if not selectors:
            raise ValueError(f"click sem selector (step {step.action})")

        from ..healing import MaterialComponentDetector
        detector = MaterialComponentDetector()

        # Hotfix BUG 1: quando o alvo do click vive dentro de um overlay CDK
        # (Angular Material datepicker calendar, dialog, autocomplete panel),
        # a primeira interacao e racing — o overlay comeca a animar
        # APOS o click trigger anterior resolver, e o click imediato seguinte
        # cai ou em nada ou no backdrop que ainda esta sumindo.
        # Aguarda o container do overlay ficar visivel (best effort) antes
        # de qualquer click cujo selector mencione cdk-overlay ou mat-calendar.
        try:
            if any(_inside_cdk_overlay(s) for s in selectors if s):
                self.page.wait_for_selector(
                    ".cdk-overlay-container .cdk-overlay-pane",
                    state="visible", timeout=2500,
                )
                # Tambem aguarda qualquer animacao CDK estabilizar.
                self.page.wait_for_timeout(250)
        except Exception:
            # Se a espera falhar, apenas prossegue — o loop de click abaixo tem
                # seu proprio comportamento de retry.
            pass

        last_error = None
        for sel in selectors:
            if not sel:
                continue
            try:
                # Verifica se e um radio button Material (sem necessidade de guard de candidates)
                if detector.is_material_radio_button("", sel):
                    loc = self.page.locator(sel).first
                    loc.dispatch_event("click")
                    self.page.wait_for_timeout(300)
                    return sel
                self.page.click(sel, timeout=self.DEFAULT_TIMEOUT)
                self.page.wait_for_timeout(200)
                return sel
            except Exception as e:
                last_error = e
                continue
        raise last_error or ValueError(f"click falhou — todos os selectores tentados ({len(selectors)})")

    def _execute_fill(self, step, selectors, data_values, field_value_map=None):
        if not selectors:
            raise ValueError("fill sem selector")
        field_value_map = field_value_map or {}

        # Resolve valor — step.value tem prioridade sobre field_value_map.
        # field_value_map so preenche quando step value esta vazio (ex: placeholder do
        # IntentReconstructor). Isso evita sobrescrever fills posteriores no mesmo campo
        # (ex: 3 fills: 10.000 → 100.000 → 1.000.000 no mesmo input de moeda).
        resolved_val, intention = self._resolve_field_value(step, data_values, field_value_map)
        value = (step.value or resolved_val or "").strip()

        if not value:
            raise ValueError(f"fill sem valor: step='{step.action}'")

        last_error = None
        for selector in selectors:
            if not selector:
                continue
            try:
                el = self.page.locator(selector).first
                # CS-1: primitiva unica de fill. Trata deteccao de mask,
                # limpar com triplo-clique, ramos de digito-cru / data-formatada /
                # fill-simples, e emite o span fill.attempted.
                mask_kind = self._fill_masked(
                    el, (step.value or value).strip(),
                    fill_path="_execute_fill",
                    selector_used=selector,
                )
                # Caminho com mask retorna imediatamente. Caminho sem mask tambem
                # sucedeu se nenhuma exception subiu. De qualquer forma o
                # selector resolveu e escrevemos um valor — retorna.
                if mask_kind != "none":
                    self.page.wait_for_timeout(200)
                return selector
            except Exception as e:
                last_error = e
                continue
        raise last_error or ValueError(
            f"fill falhou — todos os {len(selectors)} selectores tentados"
        )

    def _execute_select(self, step, selector):
        if not selector:
            raise ValueError("select_option sem selector")
        value = step.value or ""
        try:
            self.page.select_option(selector, value=value, timeout=self.DEFAULT_TIMEOUT)
        except Exception:
            self.page.select_option(selector, label=value, timeout=self.DEFAULT_TIMEOUT)
        self.page.wait_for_timeout(200)
        return selector


def _inside_cdk_overlay(selector: str) -> bool:
    """Helper Hotfix BUG 1 — detecta seletores que vivem dentro de um overlay CDK."""
    if not selector:
        return False
    s = selector.lower()
    return any(token in s for token in (
        "cdk-overlay", "mat-calendar", "mat-datepicker",
        "mat-dialog", "mat-autocomplete-panel",
    ))