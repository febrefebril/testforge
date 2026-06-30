"""Phase 2: V2 LocatorExtractor.

Consumes target_data (from JS overlay or new CDP recorder) plus the
optional AX-tree snapshot to produce ranked super-selector candidates.

Candidates are ordered by combined score
    score = stability * strategy_weight
where stability comes from `scorer.attribute_stability` and
strategy_weight reflects the locator strategy (Playwright native >
CSS attribute > text > positional).

This does NOT replace the legacy `_build_target` yet — it produces
candidates in parallel. Phase 3 compiler consumes the v2 list directly.
"""
from __future__ import annotations

from typing import Optional

from ..model import LocatorCandidate
from .intent import normalize_intent
from .playwright_codegen import (
    emit_ancestor_scoped,
    emit_get_by_role,
    emit_playwright_call,
)
from .scorer import attribute_stability


# Strategy multipliers reflect Playwright's own ranking
# (https://playwright.dev/docs/best-practices). Native > CSS > positional.
STRATEGY_WEIGHTS = {
    "playwright_native": 1.00,
    "playwright_native_scoped": 0.98,
    # Sprint M (2026-06-30): material_form_field eh ancora estrutural mais
    # estavel que aria-label (volatiliza no blur) e mat-input-N id
    # (renumera). Score 0.99 acima de test_id e aria_label. Compiler ja
    # emitia este candidate em Sprint J; resolver agora reconhece o nome
    # de estrategia para metrics + healing rollups.
    "material_form_field": 0.99,
    "test_id_css": 0.85,
    "aria_label_css": 0.85,
    "label_css": 0.80,
    "placeholder_css": 0.75,
    "name_css": 0.75,
    "id_css": 0.70,
    "data_attr_css": 0.65,
    "text_css": 0.55,
    "css_path": 0.40,
    "nth_child_css": 0.25,
    "xpath": 0.15,
}


class LocatorExtractor:
    """Builds v2 super-selector candidates from target_data + AX context."""

    def __init__(
        self,
        ax_snapshot: Optional[dict] = None,
        backend_node_id: Optional[int] = None,
        ancestor_roles: Optional[list] = None,
    ) -> None:
        self._ax = ax_snapshot
        self._backend_node_id = backend_node_id
        self._ancestor_roles = ancestor_roles or []

    def extract(self, target_data: dict, action: str = "click",
                value: str = "") -> list[LocatorCandidate]:
        """Return a list of LocatorCandidate ordered by score desc."""
        stability = attribute_stability(target_data)
        intent = normalize_intent(
            action=action,
            role=target_data.get("role"),
            accessible_name=target_data.get("accessible_name"),
            label=target_data.get("label"),
            placeholder=target_data.get("placeholder"),
            text=target_data.get("text"),
            value=value,
            ancestor_roles=self._ancestor_roles,
        )

        candidates: list[LocatorCandidate] = []

        # 0) Sprint M (2026-06-30): material_form_field ancora estrutural.
        # mat-form-field eh wrapper estavel — mat-label dentro persiste entre
        # sessoes mesmo quando aria-label do input volatiliza. Material Angular
        # cobre SIOPI 100%; generaliza para qualquer site Material via .mat-form-field.
        material_label = target_data.get("material_field_label")
        if material_label:
            tag = (target_data.get("tag") or "input").lower()
            esc = material_label.replace("\\", "\\\\").replace('"', '\\"')
            mat_sel = f'mat-form-field:has(mat-label:has-text("{esc}")) {tag}'
            candidates.append(self._mk(
                strategy="material_form_field",
                selector=mat_sel,
                base_stability=0.99,
                target_data=target_data,
                intent=intent,
                reason=f"mat-form-field anchor mat-label='{material_label}'",
            ))

        # 1) Playwright-native (highest tier)
        native = emit_playwright_call(target_data)
        if native:
            disambiguating = self._pick_disambiguating_ancestor()
            if disambiguating:
                scoped = emit_ancestor_scoped(disambiguating, native)
                candidates.append(self._mk(
                    strategy="playwright_native_scoped",
                    selector=f"page.{scoped}",
                    playwright_call=scoped,
                    base_stability=max(stability.get("role", 0.0),
                                       stability.get("test_id", 0.0),
                                       stability.get("label", 0.0)),
                    target_data=target_data,
                    intent=intent,
                    reason=f"native call scoped under {disambiguating}",
                ))
            candidates.append(self._mk(
                strategy="playwright_native",
                selector=f"page.{native}",
                playwright_call=native,
                base_stability=max(stability.get("role", 0.0),
                                   stability.get("test_id", 0.0),
                                   stability.get("label", 0.0),
                                   stability.get("placeholder", 0.0)),
                target_data=target_data,
                intent=intent,
                reason="Playwright-native locator",
            ))

        # 2) test_id CSS fallback (when js framework wraps the data-testid)
        if target_data.get("test_id"):
            tid = target_data["test_id"]
            candidates.append(self._mk(
                strategy="test_id_css",
                selector=f'[data-testid="{tid}"]',
                base_stability=stability.get("test_id", 0.0),
                target_data=target_data,
                intent=intent,
                reason=f"data-testid={tid}",
            ))

        # 3) aria-label CSS
        aria = ((target_data.get("aria_attrs") or {}).get("aria-label")
                or target_data.get("accessible_name"))
        if aria:
            tag = (target_data.get("tag") or "").lower()
            prefix = tag if tag in ("input", "textarea", "button", "a") else ""
            sel = f'{prefix}[aria-label="{aria}"]' if prefix else f'[aria-label="{aria}"]'
            candidates.append(self._mk(
                strategy="aria_label_css",
                selector=sel,
                base_stability=stability.get("aria-label", 0.0),
                target_data=target_data,
                intent=intent,
                reason=f"aria-label={aria}",
            ))

        # 4) label CSS
        label = target_data.get("label")
        el_id = target_data.get("id") or target_data.get("element_id")
        if label and el_id:
            candidates.append(self._mk(
                strategy="label_css",
                selector=f'label[for="{el_id}"]',
                base_stability=stability.get("label", 0.0),
                target_data=target_data,
                intent=intent,
                reason=f"label for={el_id}",
            ))

        # 5) placeholder CSS
        placeholder = target_data.get("placeholder")
        if placeholder:
            tag = (target_data.get("tag") or "").lower()
            sel = f'{tag}[placeholder="{placeholder}"]' if tag in ("input", "textarea") \
                  else f'[placeholder="{placeholder}"]'
            candidates.append(self._mk(
                strategy="placeholder_css",
                selector=sel,
                base_stability=stability.get("placeholder", 0.0),
                target_data=target_data,
                intent=intent,
                reason=f"placeholder={placeholder}",
            ))

        # 6) name CSS
        name_attr = target_data.get("name")
        if name_attr:
            candidates.append(self._mk(
                strategy="name_css",
                selector=f'[name="{name_attr}"]',
                base_stability=stability.get("name", 0.0),
                target_data=target_data,
                intent=intent,
                reason=f"name={name_attr}",
            ))

        # 7) id CSS (penalized when auto-generated)
        if el_id:
            candidates.append(self._mk(
                strategy="id_css",
                selector=f"#{el_id}",
                base_stability=stability.get("id", 0.0),
                target_data=target_data,
                intent=intent,
                reason=f"id={el_id}",
            ))

        # 8) css_path (structural fallback)
        css_path = target_data.get("css_path")
        if css_path and ">" in css_path and len(css_path) > 4:
            candidates.append(self._mk(
                strategy="css_path",
                selector=css_path,
                base_stability=stability.get("css_path", 0.0),
                target_data=target_data,
                intent=intent,
                reason="structural css_path",
            ))

        # Sort by score descending; stable secondary key by strategy weight.
        candidates.sort(key=lambda c: (c.score, STRATEGY_WEIGHTS.get(c.strategy, 0.0)),
                        reverse=True)
        return candidates

    # ------------------------------------------------------------------
    def _pick_disambiguating_ancestor(self) -> Optional[str]:
        """Return the closest meaningful ancestor role for scoping."""
        skip = {"WebArea", "generic", "main", "region", "group", "navigation"}
        for role in self._ancestor_roles:
            if role and role not in skip:
                return role
        return None

    def _mk(
        self,
        *,
        strategy: str,
        selector: str,
        target_data: dict,
        base_stability: float,
        intent: str,
        reason: str,
        playwright_call: Optional[str] = None,
    ) -> LocatorCandidate:
        weight = STRATEGY_WEIGHTS.get(strategy, 0.50)
        score = round(max(0.0, min(1.0, base_stability * weight)), 3)
        return LocatorCandidate(
            strategy=strategy,
            selector=selector,
            score=score,
            reason=reason,
            backend_node_id=self._backend_node_id,
            role=target_data.get("role"),
            accessible_name=target_data.get("accessible_name"),
            ax_path=list(self._ancestor_roles),
            attributes={
                k: v for k, v in (target_data.get("all_attributes") or {}).items()
                if v
            },
            ancestor_roles=list(self._ancestor_roles),
            attribute_stability=attribute_stability(target_data),
            playwright_call=playwright_call,
            intent_text=intent,
        )
