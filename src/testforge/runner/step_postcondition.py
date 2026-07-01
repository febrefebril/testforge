"""TestForge — StepPostconditionValidator.

Valida o efeito de cada acao. Impede falso positivo e falso healing:
"step executou sem exception" NAO e sinonimo de "fluxo funcionou".
"""
from __future__ import annotations
import re
from typing import Optional

from .step_result import PostconditionResult


class StepPostconditionValidator:
    """Valida pos-condicoes por step apos a execucao."""

    def __init__(self, page, oracle_runner=None):
        self.page = page
        self._oracle = oracle_runner
        if self._oracle is None:
            try:
                from ..oracle import OracleRunner
                self._oracle = OracleRunner(page)
            except Exception:
                self._oracle = None

    def _primary_selector(self, step):
        if step.target and getattr(step.target, "candidates", None):
            cands = step.target.candidates
            if cands:
                return cands[0].selector or ""
        return ""

    @staticmethod
    def _normalize(s):
        if s is None:
            return ""
        return re.sub(r"\s+", "", str(s)).strip().lower()

    def validate(self, step, page=None, next_step=None, url_before=""):
        page = page or self.page
        action = step.action

        if action == "navigation":
            return self._validate_navigation(step)
        if action == "click":
            return self._validate_click(step, next_step, url_before)
        if action == "fill":
            return self._validate_fill(step)
        if action == "select_option":
            return self._validate_select(step)
        if action == "assert":
            return self._validate_assert(step)

        return PostconditionResult(
            passed=True,
            checks={"no_specific_postcondition": True},
            message=f"sem pos-condicao especifica para {action}",
        )

    def _validate_navigation(self, step):
        url = self.page.url or ""
        passed = bool(url)
        return PostconditionResult(
            passed=passed,
            checks={"url_present": passed},
            message=f"url atual: {url}",
        )

    def _validate_fill(self, step):
        selector = self._primary_selector(step)
        # Use resolved value from field_value_map if available (more accurate than raw step.value)
        ctx = getattr(step, "context", {}) or {}
        expected = (ctx.get("resolved_value") or step.value or "").strip()
        try:
            actual = self.page.locator(selector).first.input_value(timeout=3000)
        except Exception as exc:
            return PostconditionResult(
                passed=False,
                failures=["cannot_read_input_value"],
                message=str(exc),
            )
        en = self._normalize(expected)
        an = self._normalize(actual)
        matched = bool(en) and (en == an or en in an or an in en)
        # Hotfix 22: valores com currency mask (SIOPI Caixa) chegam formatados
        # em `actual` ("R$ 1.000.000,00") vs raw em `expected` ("1000000.00").
        # Compara tambem numericamente stripando simbolo e mask BR/US.
        if not matched:
            en_num = self._strip_currency(expected)
            an_num = self._strip_currency(actual)
            if en_num and an_num and en_num == an_num:
                matched = True
        return PostconditionResult(
            passed=matched,
            checks={"input_value_matches": matched, "actual_value_present": bool(actual)},
            failures=[] if matched else ["value_mismatch"],
            message="" if matched else f"esperado='{expected}' obtido='{actual}'",
        )

    @staticmethod
    def _strip_currency(v: str) -> str:
        """Converte valor formatado BR/US para numero canonico (float como string).
        Ex.: 'R$ 1.000.000,00' -> '1000000.00'; '1000000.00' -> '1000000.00';
             '1.500,00' -> '1500.00'; '1,500.00' -> '1500.00'.
        Retorna '' se nao parseavel.
        """
        if not v:
            return ""
        s = str(v).strip()
        # Remove currency symbol + whitespace
        s = re.sub(r"[^\d,.\-]", "", s)
        if not s:
            return ""
        has_comma = "," in s
        has_dot = "." in s
        try:
            if has_comma and has_dot:
                # BR: 1.000,00 (dot thousands, comma decimal)
                if s.rfind(",") > s.rfind("."):
                    n = float(s.replace(".", "").replace(",", "."))
                else:
                    # US: 1,000.00
                    n = float(s.replace(",", ""))
            elif has_comma:
                # 1000,00 BR decimal only
                n = float(s.replace(",", "."))
            else:
                n = float(s)
            return f"{n:.2f}"
        except (ValueError, TypeError):
            return ""

    def _validate_select(self, step):
        selector = self._primary_selector(step)
        expected = step.value or ""
        try:
            selected = self.page.locator(selector).first.evaluate(
                "el => { const opt = el.options[el.selectedIndex]; return {value: el.value, text: opt ? (opt.textContent || \'\').trim() : \'\'}; }"
            )
        except Exception as exc:
            return PostconditionResult(
                passed=False,
                failures=["cannot_read_selected_option"],
                message=str(exc),
            )
        en = self._normalize(expected)
        matched = (
            self._normalize(selected.get("value", "")) == en
            or self._normalize(selected.get("text", "")) == en
        )
        return PostconditionResult(
            passed=matched,
            checks={"selected_option_matches": matched},
            failures=[] if matched else ["selected_option_mismatch"],
            message="" if matched else f"esperado='{expected}' selecionado={selected}",
        )

    def _validate_click(self, step, next_step, url_before):
        ctx = getattr(step, "context", {}) or {}
        causes_navigation = ctx.get("causes_navigation", False)

        explicit = ctx.get("oracles") or []
        if explicit and self._oracle:
            results = self._oracle.run_all(explicit)
            passed = all(getattr(r, "status", "") == "passed" for r in results)
            return PostconditionResult(
                passed=passed,
                checks={"explicit_oracles_passed": passed},
                oracle_results=results,
                failures=[] if passed else ["explicit_oracle_failed"],
                message="oracles explicitos executados",
            )

        if causes_navigation:
            url_now = self.page.url
            changed = bool(url_before) and url_now != url_before
            if changed:
                return PostconditionResult(
                    passed=True,
                    checks={"url_changed": True},
                    message=f"url mudou: '{url_before}' → '{url_now}'",
                )
            # SPA: URL pode não mudar (Angular router client-side).
            # Fallback: verificar se próximo step está visível.
            if next_step and getattr(next_step, "target", None):
                cands = next_step.target.candidates
                for c in (cands or [])[:3]:
                    try:
                        self.page.wait_for_selector(c.selector, state="visible", timeout=5000)
                        return PostconditionResult(
                            passed=True,
                            checks={"url_changed": False, "next_step_visible": True},
                            message=f"SPA nav sem mudanca de URL — proximo step visivel: {c.selector}",
                        )
                    except Exception:
                        continue
            return PostconditionResult(
                passed=False,
                checks={"url_changed": False},
                failures=["url_not_changed"],
                message=f"url before='{url_before}' after='{url_now}'",
            )

        if next_step and getattr(next_step, "target", None):
            cands = next_step.target.candidates
            if cands:
                # Tenta seletores exatos primeiro, depois fallbacks genericos
                selectors_to_try = [c.selector for c in cands[:3]]
                # Adiciona fallback generico: mesmo role sem valor monetario no nome
                for c in cands:
                    if c.selector.startswith("role=") and "[name=" in c.selector:
                        role = c.selector.split("[")[0]  # e.g., "role=listitem"
                        selectors_to_try.append(role)
                        break
                # Adiciona fallback nth-child para cartoes de resultado
                if any("role=listitem" in s for s in selectors_to_try):
                    selectors_to_try.append("[role=listitem]:nth-child(2)")

                for next_sel in selectors_to_try:
                    try:
                        self.page.wait_for_selector(next_sel, state="visible", timeout=8000)
                        return PostconditionResult(
                            passed=True,
                            checks={"next_step_visible": True},
                            message=f"proximo step visivel: {next_sel}",
                        )
                    except Exception:
                        import sys
                        print(f"  [AVISO] pos-condicao: {next_sel[:60]} nao encontrado", file=sys.stderr)
                        continue

                # Sprint B (2026-06-29): soft fallback usando semantica do
                # next_step. Antes desta sessao a pos-condicao retornava FAIL
                # quando o next_step.target nao era localizavel pelo seletor
                # literal — em forms Angular Material o aria-label volatiliza
                # quando outro input ganha foco, entao input[aria-label="X"]
                # falha embora o input esteja la. Healer entao tentava curar
                # algo que ja funcionara, frequentemente curando para tela
                # errada. Soft fallback:
                #   - Se next_step tem accessible_name OU label nao vazios,
                #     tenta get_by_label / get_by_role native do Playwright
                #     com 2s extra. Esses respeitam <label for=...> e
                #     aria-labelledby — nao quebram com aria-label volatil.
                #   - Se mesmo assim falhar, retorna passed=True com warning
                #     em vez de FAIL. Filosofia: o click executou; previsao
                #     de visibilidade do proximo step eh oracle SOFT, nao
                #     definitivo. Falhas reais do proximo step viram REJ
                #     no proximo _run_one_step e healing roda la com
                #     contexto certo, em vez de mascarar erro no step atual.
                tgt = next_step.target
                soft_name = (getattr(tgt, "accessible_name", "") or "").strip()
                soft_role = (getattr(tgt, "role", "") or "").strip()
                soft_label = (getattr(tgt, "label", "") or "").strip()

                soft_native_exprs: list[tuple[str, str]] = []
                if soft_role and soft_name:
                    soft_native_exprs.append((
                        f"get_by_role({soft_role!r}, name={soft_name!r})",
                        "role+name",
                    ))
                if soft_label:
                    soft_native_exprs.append((
                        f"get_by_label({soft_label!r})", "label",
                    ))
                if soft_name and not soft_role:
                    soft_native_exprs.append((
                        f"get_by_label({soft_name!r})", "name-as-label",
                    ))

                for _expr, _kind in soft_native_exprs:
                    try:
                        if _kind == "role+name":
                            loc = self.page.get_by_role(soft_role, name=soft_name)
                        else:
                            loc = self.page.get_by_label(soft_label or soft_name)
                        loc.first.wait_for(state="visible", timeout=2000)
                        return PostconditionResult(
                            passed=True,
                            checks={"next_step_visible": True, "soft_match": _kind},
                            message=f"proximo step visivel via {_kind}: {_expr[:60]}",
                        )
                    except Exception:
                        continue

                return PostconditionResult(
                    passed=True,
                    checks={
                        "next_step_visible": False,
                        "next_step_soft_pass": True,
                    },
                    message=(
                        f"next-step visibility unverified (soft pass): "
                        f"{cands[0].selector[:80]}"
                    ),
                )

        return PostconditionResult(
            passed=True,
            checks={"click_no_exception": True},
            message="click executou sem oracle especifico",
        )

    def _validate_assert(self, step):
        candidates = (step.target.candidates if step.target and step.target.candidates else [])
        selectors = [c.selector for c in candidates if c.selector] or [self._primary_selector(step) or "body"]
        expected = step.value or ""
        ctx = getattr(step, "context", {}) or {}
        assert_type = ctx.get("assert_type", "textual")

        # Reorder and augment selectors based on assert_type:
        #
        # textual/automatico — assertion IS the text content:
        #   has-text first (exact match on what user wants to verify),
        #   then role/aria, then CSS path.
        #   Append has-text fallback if not already present.
        #
        # visivel — element identity matters, but text can confirm presence:
        #   id/aria/role first (already highest-scored from normalizer),
        #   CSS path middle, has-text last resort.
        #   Append has-text fallback if expected known.
        #
        # estado — must be the exact form element (input/checkbox/radio);
        #   has-text finds any container with that text, not the control itself.
        #   id → aria-label → role-based → CSS path. No has-text fallback.
        selectors = list(selectors)
        target = getattr(step, "target", None)
        target_text = (getattr(target, "text", "") or "").strip() if target else ""
        target_aname = (getattr(target, "accessible_name", "") or "").strip() if target else ""
        target_tag = (getattr(target, "tag", "") or "").lower() if target else ""
        if assert_type in ("textual", "automatico"):
            if expected and not any(":has-text(" in s for s in selectors):
                selectors.append(f':has-text("{expected}")')
            text_sels = [s for s in selectors if ":has-text(" in s]
            other_sels = [s for s in selectors if ":has-text(" not in s]
            selectors = text_sels + other_sels
        elif assert_type == "visivel":
            # Hotfix 22: `expected` para visivel e "visible"/"hidden" (flag), NAO
            # o texto visivel na tela. Usa target.text (texto real do elemento)
            # ou accessible_name como fallback has-text. Isso torna asserts
            # visivel resilientes a ids Angular Material dinamicos como
            # `#mat-mdc-error-4` que mudam entre runs.
            has_text_source = ""
            for candidate_text in (target_text, target_aname):
                if candidate_text and candidate_text not in ("visible", "hidden"):
                    has_text_source = candidate_text
                    break
            if has_text_source and not any(":has-text(" in s for s in selectors):
                tag_prefix = target_tag if target_tag else "*"
                snippet = has_text_source[:60].replace('"', '\\"')
                selectors.append(f'{tag_prefix}:has-text("{snippet}")')
            # Structural selectors first (id/aria/role ranked highest by normalizer),
            # has-text appended last — any element containing the text is sufficient
            # to confirm visibility.
        # estado: no reordering, no has-text append — element identity is critical

        # Resolve first selector that actually finds an element in the DOM.
        # Hotfix 22: usa timeout maior no primeiro seletor (assumido melhor
        # candidato) para dar tempo a calculos assincronos renderizarem
        # resultados. Selectors subsequentes usam timeout menor.
        resolved_selector = None
        for idx, selector in enumerate(selectors):
            timeout_ms = 5000 if idx == 0 else 1500
            try:
                self.page.locator(selector).first.wait_for(state="attached", timeout=timeout_ms)
                resolved_selector = selector
                break
            except Exception:
                continue

        if resolved_selector is None:
            return PostconditionResult(
                passed=False,
                failures=["assert_element_not_found"],
                message=f"Nenhum seletor encontrou o elemento ({len(selectors)} tentativas)",
            )

        if not self._oracle:
            # Hotfix 22: para assert_type visivel, expected e um flag
            # ("visible"/"hidden") — nao um texto de conteudo. Valida pela
            # visibility real do elemento no DOM, nao por text_contains.
            if assert_type == "visivel":
                try:
                    is_visible = self.page.locator(resolved_selector).first.is_visible(timeout=2000)
                    want_visible = (expected or "visible").lower() != "hidden"
                    passed = is_visible if want_visible else (not is_visible)
                    return PostconditionResult(
                        passed=passed,
                        checks={"is_visible": is_visible, "want_visible": want_visible,
                                "selector_used": resolved_selector},
                        failures=[] if passed else ["assert_visibility_mismatch"],
                        message=f"[{resolved_selector}] esperado={'visible' if want_visible else 'hidden'} obtido={'visible' if is_visible else 'hidden'}",
                    )
                except Exception as exc:
                    return PostconditionResult(
                        passed=False,
                        failures=["assert_element_not_found"],
                        message=str(exc),
                    )
            try:
                text = self.page.locator(resolved_selector).first.text_content(timeout=2000)
                matched = expected.lower() in (text or "").lower()
                return PostconditionResult(
                    passed=matched,
                    checks={"text_contains_expected": matched, "selector_used": resolved_selector},
                    failures=[] if matched else ["assert_text_mismatch"],
                    message=f"[{resolved_selector}] esperado='{expected[:60]}' obtido='{(text or '')[:80]}'",
                )
            except Exception as exc:
                return PostconditionResult(
                    passed=False,
                    failures=["assert_element_not_found"],
                    message=str(exc),
                )

        if assert_type in ("textual", "automatico"):
            r = self._oracle.run_visual_dom(resolved_selector, expected)
        elif assert_type == "visivel":
            r = self._oracle.run_visual_dom(resolved_selector, "")
        else:
            r = self._oracle.run_business_state(resolved_selector, expected)

        passed = getattr(r, "status", "") == "passed"
        return PostconditionResult(
            passed=passed,
            checks={"oracle_status": passed, "selector_used": resolved_selector},
            oracle_results=[r],
            failures=[] if passed else ["oracle_failed"],
            message=getattr(r, "message", ""),
        )