"""Phase 2: Emit Playwright-native locator calls.

Implements the same priority chain Playwright codegen uses (see
https://playwright.dev/docs/best-practices):

    1. get_by_role(role, name=...)        — role + accessible name
    2. get_by_label(text)                 — form controls with <label>
    3. get_by_placeholder(text)           — inputs with placeholder only
    4. get_by_alt_text(text)              — images
    5. get_by_title(text)                 — elements with title
    6. get_by_test_id(value)              — data-testid
    7. CSS / XPath fallback                — last resort

This module produces strings ready to interpolate into compiled tests
(Phase 3 will move the actual call execution to runtime). The strings
are also used by the runtime resolver to call the equivalent Playwright
locator API.
"""
from __future__ import annotations

import re
from typing import Optional

_PY_STR_RE = re.compile(r'(["\\])')


def _py_repr(value: str) -> str:
    """Render a string as a Python double-quoted literal, escaping safely."""
    if value is None:
        return '""'
    return '"' + _PY_STR_RE.sub(r"\\\1", str(value)) + '"'


def emit_get_by_role(role: str, name: Optional[str] = None, exact: bool = False) -> str:
    base = f"get_by_role({_py_repr(role)}"
    if name:
        base += f", name={_py_repr(name)}"
        if exact:
            base += ", exact=True"
    return base + ")"


def emit_get_by_label(text: str, exact: bool = False) -> str:
    s = f"get_by_label({_py_repr(text)}"
    if exact:
        s += ", exact=True"
    return s + ")"


def emit_get_by_placeholder(text: str) -> str:
    return f"get_by_placeholder({_py_repr(text)})"


def emit_get_by_test_id(value: str) -> str:
    return f"get_by_test_id({_py_repr(value)})"


def emit_get_by_text(text: str, exact: bool = False) -> str:
    s = f"get_by_text({_py_repr(text)}"
    if exact:
        s += ", exact=True"
    return s + ")"


def emit_get_by_title(text: str) -> str:
    return f"get_by_title({_py_repr(text)})"


def emit_get_by_alt_text(text: str) -> str:
    return f"get_by_alt_text({_py_repr(text)})"


def emit_playwright_call(target_data: dict) -> Optional[str]:
    """Pick the highest-priority Playwright-native call for this target.

    Returns None when no native call applies (caller falls back to CSS).
    The returned string is a method call without the receiver, e.g.
    `get_by_role("button", name="Salvar")` — caller prefixes with
    `page.` or `page.get_by_role("dialog").` for ancestor scoping.
    """
    test_id = target_data.get("test_id")
    role = target_data.get("role")
    name = (target_data.get("accessible_name")
            or target_data.get("label")
            or "")
    label = target_data.get("label")
    placeholder = target_data.get("placeholder")
    text = (target_data.get("text") or "").strip()
    title = (target_data.get("all_attributes") or {}).get("title")
    alt = (target_data.get("all_attributes") or {}).get("alt")

    if role:
        if name and len(name) <= 80:
            return emit_get_by_role(role, name)
        return emit_get_by_role(role)
    if label:
        return emit_get_by_label(label)
    if placeholder:
        return emit_get_by_placeholder(placeholder)
    if alt:
        return emit_get_by_alt_text(alt)
    if title:
        return emit_get_by_title(title)
    if test_id:
        return emit_get_by_test_id(test_id)
    if text and len(text) <= 60:
        return emit_get_by_text(text)
    return None


def emit_ancestor_scoped(parent_role: str, child_call: str) -> str:
    """Wrap a child call with an ancestor scope: parent.child().

    Used when the AX tree reveals the target lives inside a dialog,
    tablist, etc. Example output:
        get_by_role("dialog").get_by_role("button", name="Salvar")
    """
    return f"{emit_get_by_role(parent_role)}.{child_call}"
