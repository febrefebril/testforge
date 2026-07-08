"""TestForge — StepPreconditionValidator.

Valida se um step pode ser executado: actionability, dependencias,
selector ausente, candidato primario, e regras especificas por acao.
"""
from __future__ import annotations
from typing import Optional

from .step_result import PreconditionResult


class StepPreconditionValidator:
    """Valida pre-condicoes por step antes da execucao."""

    def __init__(self, page, actionability_validator=None):
        self.page = page
        self._actionability = actionability_validator
        if self._actionability is None:
            try:
                from ..actionability import ActionabilityValidator
                self._actionability = ActionabilityValidator(page)
            except Exception:
                self._actionability = None

    def _primary_selector(self, step) -> str:
        if step.target and getattr(step.target, "candidates", None):
            cands = step.target.candidates
            if cands:
                return cands[0].selector or ""
        return ""

    def _check_dependency(self, step, failed_step_indices: set, all_steps: list) -> Optional[str]:
        if not getattr(step, "depends_on", ""):
            return None
        import re
        m = re.match(r"step_(\d+)", step.depends_on)
        if not m:
            return None
        idx = int(m.group(1)) - 1
        if idx in failed_step_indices:
            return f"blocked_by_previous_failure (depends on {step.depends_on})"
        return None

    def validate(self, step, failed_step_indices: Optional[set] = None,
                 all_steps: Optional[list] = None) -> PreconditionResult:
        failed_step_indices = failed_step_indices or set()
        all_steps = all_steps or []
        result = PreconditionResult(passed=False)

        if getattr(step, "skip_reason", ""):
            result.passed = True
            result.message = f"skipped: {step.skip_reason}"
            result.checks["skipped"] = True
            return result

        dep_block = self._check_dependency(step, failed_step_indices, all_steps)
        if dep_block:
            result.failures.append("blocked_by_previous_failure")
            result.message = dep_block
            return result

        action = step.action
        if action == "navigation":
            result.passed = True
            result.checks["navigation_ok"] = True
            return result

        selector = self._primary_selector(step)

        if action == "click":
            return self._validate_click(step, selector, result)
        if action == "fill":
            return self._validate_fill(step, selector, result)
        if action == "select_option":
            return self._validate_select(step, selector, result)
        if action == "assert":
            return self._validate_assert(step, selector, result)

        result.passed = True
        result.message = f"nenhuma pre-condicao especifica para acao={action}"
        return result

    def _validate_click(self, step, selector, result):
        result.checks["selector_present"] = bool(selector)
        if not selector:
            result.failures.append("missing_selector")
            result.message = "click sem selector"
            return result
        if self._actionability:
            try:
                ar = self._actionability.validate(selector, timeout=3000)
                result.checks["actionable"] = ar.actionable
                result.checks["visible"] = ar.visible
                result.checks["enabled"] = ar.enabled
                result.checks["area_positive"] = ar.area_positive
                if not ar.actionable:
                    result.failures.extend(ar.failures)
                    result.message = ar.message
                    return result
            except Exception as exc:
                result.failures.append(f"actionability_error: {exc}")
                result.message = str(exc)
                return result
        result.passed = True
        result.message = "click precondition ok"
        return result

    def _validate_fill(self, step, selector, result):
        result.checks["selector_present"] = bool(selector)
        if not selector:
            result.failures.append("missing_selector")
            result.message = "fill sem selector"
            return result
        value = step.value or ""
        result.checks["value_present"] = bool(value)
        if not value:
            result.failures.append("missing_value")
            result.message = "fill sem valor"
            return result
        try:
            el = self.page.locator(selector).first
            el.wait_for(state="visible", timeout=3000)
            result.checks["visible"] = True
            readonly = el.get_attribute("readonly")
            disabled = el.get_attribute("disabled")
            result.checks["editable"] = not (readonly or disabled)
            if readonly or disabled:
                result.failures.append("not_editable")
                result.message = "campo readonly/disabled"
                return result
        except Exception as exc:
            result.failures.append(f"locator_error: {exc}")
            result.message = str(exc)
            return result
        result.passed = True
        result.message = "fill precondition ok"
        return result

    def _validate_select(self, step, selector, result):
        result.checks["selector_present"] = bool(selector)
        if not selector:
            result.failures.append("missing_selector")
            return result
        try:
            el = self.page.locator(selector).first
            el.wait_for(state="attached", timeout=3000)
            tag = el.evaluate("e => e.tagName.toLowerCase()")
            result.checks["target_is_select"] = (tag == "select")
            if tag != "select":
                result.failures.append("target_not_select")
                result.message = f"alvo nao e <select>, e <{tag}>"
                return result
            expected = step.value or ""
            if expected:
                options = el.evaluate(
                    "e => Array.from(e.options).map(o => ({value: o.value, text: (o.textContent||'').trim()}))"
                )
                exists = any(
                    o["value"] == expected or o["text"] == expected
                    for o in options
                )
                result.checks["option_exists"] = exists
                if not exists:
                    result.failures.append("option_not_found")
                    result.message = f"opcao '{expected}' nao existe"
                    return result
        except Exception as exc:
            result.failures.append(f"select_error: {exc}")
            result.message = str(exc)
            return result
        result.passed = True
        result.message = "select precondition ok"
        return result

    def _validate_assert(self, step, selector, result):
        if not selector:
            selector = "body"
        result.checks["selector_present"] = True
        expected = step.value or ""
        result.checks["expected_present"] = bool(expected)
        if not expected:
            result.failures.append("missing_expected")
            result.message = "assert sem valor esperado"
            return result
        result.passed = True
        result.message = "assert precondition ok"
        return result