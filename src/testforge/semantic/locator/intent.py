"""Phase 2: Intent text normalization for L0 cache keying.

Stagehand-style intent text: a stable, human-readable string that
identifies *what the user wanted to do*, not *where the element lives*.
Used as the cache key for the L0 healing catalog so the same intent
heals across DOM mutations and similar pages.

Examples:
    click button "Salvar" in dialog
    fill textbox "Email" placeholder "you@example.com"
    select combobox "Estado" option "São Paulo"
"""
from __future__ import annotations

import re
from typing import Iterable, Optional


_WHITESPACE = re.compile(r"\s+")
_GENERIC_CONTAINER_ROLES = {"WebArea", "generic", "main", "navigation", "region",
                            "group", "section", "list", "listitem"}


def _clean(value: Optional[str], limit: int = 60) -> str:
    if not value:
        return ""
    v = _WHITESPACE.sub(" ", str(value)).strip()
    return v[:limit]


def _disambiguating_ancestor(ancestor_roles: Iterable[str]) -> Optional[str]:
    """Pick the closest meaningful ancestor role for disambiguation.

    Skips generic containers (WebArea, generic) — keep dialog, tablist,
    menu, dialog-like roles that change UX scope.
    """
    for role in ancestor_roles:
        if role and role not in _GENERIC_CONTAINER_ROLES:
            return role
    return None


def normalize_intent(
    action: str,
    role: Optional[str] = None,
    accessible_name: Optional[str] = None,
    label: Optional[str] = None,
    placeholder: Optional[str] = None,
    text: Optional[str] = None,
    value: Optional[str] = None,
    ancestor_roles: Optional[list] = None,
) -> str:
    """Build a stable intent string from action + target attributes.

    Pattern: `<action> <role> "<name>" [in <ancestor>]`
    Falls through to placeholder / text / label when no role+name pair
    is available.
    """
    a = (action or "").strip().lower() or "interact"
    role_n = _clean(role)
    name = _clean(accessible_name) or _clean(label) or _clean(text)
    placeholder_n = _clean(placeholder, limit=40)

    parts: list[str] = [a]
    if role_n:
        parts.append(role_n)
        if name:
            parts.append(f'"{name}"')
        elif placeholder_n:
            parts.append(f'placeholder "{placeholder_n}"')
    elif name:
        parts.append(f'"{name}"')
    elif placeholder_n:
        parts.append(f'placeholder "{placeholder_n}"')

    if a == "select" and value:
        v = _clean(value, limit=40)
        if v:
            parts.append(f'option "{v}"')

    ancestor = _disambiguating_ancestor(ancestor_roles or [])
    if ancestor:
        parts.append(f"in {ancestor}")
    return " ".join(parts)
