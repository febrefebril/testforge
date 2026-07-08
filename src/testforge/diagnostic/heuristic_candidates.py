"""Sprint 0 hotfix — fast heuristic candidate builder.

Sprint 0 originally passed `candidates=None` from RecorderController to
DiagnosticSession.assess_event, which silently disabled ReplayCheck.
This module gives the recorder a 5-strategy rapid candidate list so
the replay probe can run during recording without invoking the heavy
LocatorExtractor (Phase 2).

Strategies (in priority order, all cheap):
1. data-testid     — `[data-testid="..."]`
2. role+name       — `role=role[name="..."]`
3. aria-label      — `<tag>[aria-label="..."]`
4. placeholder     — `<tag>[placeholder="..."]`
5. id              — `#id`  (skipped for auto-IDs like mat-input-0)

The resulting dicts are LocatorResolver-compatible (strategy, selector,
score, optional playwright_call) — the recorder feeds them directly
to ReplayCheck without further translation.
"""
from __future__ import annotations

from typing import Optional


_AUTO_ID_PREFIXES = ("mat-input-", "mat-select-", "mat-autocomplete-",
                      "ng-", "ember", "react-", "jss-")


def _is_auto_id(value: str) -> bool:
    return any(value.startswith(p) for p in _AUTO_ID_PREFIXES)


def _quote(value: str) -> str:
    return value.replace('"', '\\"')


def build_quick_candidates(target_data: Optional[dict]) -> list[dict]:
    """Retorna ate 5 candidatos derivados de target_data. Barato (<1 ms)."""
    if not target_data:
        return []
    out: list[dict] = []
    tag = (target_data.get("tag") or "").lower()
    role = target_data.get("role")
    name = (target_data.get("accessible_name")
            or target_data.get("label")
            or target_data.get("text") or "")
    test_id = target_data.get("test_id")
    aria_label = ((target_data.get("aria_attrs") or {}).get("aria-label")
                  or target_data.get("accessible_name"))
    placeholder = target_data.get("placeholder")
    el_id = target_data.get("element_id") or target_data.get("id")

    if test_id:
        out.append({
            "strategy": "test_id_css",
            "selector": f'[data-testid="{_quote(test_id)}"]',
            "score": 0.95,
            "playwright_call": f'get_by_test_id("{_quote(test_id)}")',
        })

    if role and name and len(name) <= 80:
        clean = _quote(name.strip())[:80]
        out.append({
            "strategy": "playwright_native",
            "selector": f'page.get_by_role("{role}", name="{clean}")',
            "score": 0.90,
            "playwright_call": f'get_by_role("{role}", name="{clean}")',
        })

    if aria_label:
        clean = _quote(aria_label)
        prefix = tag if tag in ("input", "textarea", "button", "a") else ""
        sel = (f'{prefix}[aria-label="{clean}"]'
               if prefix else f'[aria-label="{clean}"]')
        out.append({
            "strategy": "aria_label_css",
            "selector": sel,
            "score": 0.85,
        })

    if placeholder:
        clean = _quote(placeholder)
        prefix = tag if tag in ("input", "textarea") else ""
        sel = (f'{prefix}[placeholder="{clean}"]'
               if prefix else f'[placeholder="{clean}"]')
        out.append({
            "strategy": "placeholder_css",
            "selector": sel,
            "score": 0.75,
        })

    if el_id and not _is_auto_id(el_id):
        out.append({
            "strategy": "id_css",
            "selector": f"#{el_id}",
            "score": 0.80,
        })

    return out
