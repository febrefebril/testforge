"""Phase 2: Per-attribute stability scoring.

Replaces hand-tuned magic numbers (0.95, 0.92, 0.87, ...) in `_build_target`
with deterministic rules grounded in why each attribute breaks:

- test_id        intentional, stable, rarely changes ............. 0.95
- data-* (other) typed but app-specific .......................... 0.70
- aria-label     stable on a11y-aware UIs; risk of i18n change ... 0.85
- accessible name from <label> association ...................... 0.85
- role           stable, but ambiguous without a name ............ 0.50 alone / 0.95 with name
- placeholder    i18n risk, only present on inputs ............... 0.70
- name attribute server-side stable, no i18n risk ............... 0.75
- id (semantic)  user-set, stable ............................... 0.80
- id (auto)      mat-, ng-, ember-, react- prefixes ............. 0.20
- visible text   short + non-generic = stable .................... 0.55
                 generic ("OK", "Cancelar") ...................... 0.10
                 long (>40 chars) ................................ -0.10
- css_path       structural, breaks on layout refactors .......... 0.40
- nth_child      positional, breaks when siblings added/removed .. 0.25
- xpath          worst — full ancestor path, fragile .............. 0.15

Stability is a probability the candidate will still resolve after a
typical sprint of DOM changes. Not a confidence in correctness — that
is handled by the candidate score combining stability with the locator
strategy itself.
"""
from __future__ import annotations

import re

_AUTO_ID_PREFIXES = ("mat-", "ng-", "ember", "react-", "css-", "jss")
_GENERIC_TEXT = {
    "ok", "cancelar", "voltar", "salvar", "enviar", "fechar", "selecione",
    "buscar", "pesquisar", "limpar", "confirmar", "continuar", "avançar",
    "sim", "não", "aceitar", "rejeitar",
}


def _is_auto_id(value: str) -> bool:
    return any(value.startswith(p) for p in _AUTO_ID_PREFIXES)


def _is_generic_text(value: str) -> bool:
    if not value:
        return True
    clean = re.sub(r"\s+", " ", value).strip().lower()
    if clean in _GENERIC_TEXT:
        return True
    if len(clean) <= 1 or clean.isdigit():
        return True
    return False


def attribute_stability(target_data: dict) -> dict[str, float]:
    """Return a per-attribute stability map for the given target.

    Keys correspond to attribute names in target_data. Values in [0, 1].
    Attributes not present in target_data are absent from the result.
    """
    out: dict[str, float] = {}

    test_id = target_data.get("test_id")
    if test_id:
        out["test_id"] = 0.95

    role = target_data.get("role")
    name = (target_data.get("accessible_name")
            or target_data.get("label")
            or "")
    if role:
        out["role"] = 0.95 if name else 0.50

    aria = (target_data.get("aria_attrs") or {}).get("aria-label") or \
           target_data.get("accessible_name")
    if aria:
        out["aria-label"] = 0.85

    label = target_data.get("label")
    if label:
        out["label"] = 0.85

    placeholder = target_data.get("placeholder")
    if placeholder:
        out["placeholder"] = 0.70

    name_attr = target_data.get("name")
    if name_attr:
        out["name"] = 0.75

    el_id = target_data.get("id") or target_data.get("element_id")
    if el_id:
        out["id"] = 0.20 if _is_auto_id(el_id) else 0.80

    text = target_data.get("text")
    if text:
        clean = re.sub(r"\s+", " ", str(text)).strip()
        if _is_generic_text(clean):
            score = 0.10
        else:
            score = 0.55
            if len(clean) > 40:
                score -= 0.10
            elif len(clean) > 20:
                score -= 0.05
        out["text"] = max(0.05, round(score, 2))

    data_attrs = target_data.get("data_attrs") or {}
    non_testid_data = [k for k in data_attrs if k != "data-testid"]
    if non_testid_data:
        out["data_attr"] = 0.70

    if target_data.get("css_path"):
        out["css_path"] = 0.40
    if target_data.get("nth_child"):
        out["nth_child"] = 0.25
    if target_data.get("xpath"):
        out["xpath"] = 0.15

    return out
