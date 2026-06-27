"""Centralized dangerous-locator filter.

B19/B20 (2026-06-27): the IncrementalRunner had a `_DANGEROUS_LOCATORS`
set + `_is_dangerously_generic` predicate; the legacy `run` path did
not. A SIOPI run produced 26 consecutive L2 heals all resolving to
`a[href="/"]` (the home link), oracle-approved as success because the
link existed on every page. To stop the false-pass cascade we (1)
broaden the deny-list, (2) move it to a single module both runners
import.

Add new patterns by category:
- bare-tag names (`a`, `div`, `button`) — always too generic.
- nav helpers (`a[href="/"]`, `a[href="#"]`, `a[href=""]`) — present
  on every page of a typical SPA.
- role helpers without text (`[role="button"]`, `[role="link"]`).
- CSS-only `nth-child` selectors below ~30 chars — almost never stable.

Future: when we have evidence telemetry, threshold by hit-rate (a
locator is dangerous when it matches >K elements site-wide).
"""
from __future__ import annotations

import re

_BARE_TAGS = {
    "a", "body", "html", "button", "input", "select", "div", "span",
}

_TEXT_SELECTORS = {
    "text=selecione", "text=ok", "text=cancelar", "text=sim",
    "text=nao", "text=continuar", "text=voltar", "text=fechar",
    "text=enviar", "text=salvar", "text=home",
}

# Nav helpers / generic anchors. Match the full normalized selector.
_NAV_PATTERNS = {
    'a[href="/"]', "a[href='/']",
    'a[href="#"]', "a[href='#']",
    'a[href=""]', "a[href='']",
    'a[href="/home"]', "a[href='/home']",
    'a[href="javascript:void(0)"]', "a[href='javascript:void(0)']",
}

# Role-only attribute selectors with no qualifier.
_ROLE_ONLY = {
    '[role="button"]', "[role='button']",
    '[role="link"]', "[role='link']",
    '[role="listitem"]', "[role='listitem']",
    "role=button", "role=link", "role=listitem",
}

DANGEROUS_LOCATORS: frozenset[str] = frozenset(
    _BARE_TAGS | _TEXT_SELECTORS | _NAV_PATTERNS | _ROLE_ONLY
)

# Regex patterns matched against the normalized selector. Keep narrow:
# bare `^/html/` (full XPath from root) is the only pattern broad enough
# to deserve a regex. Specific generic anchors live in the explicit
# DANGEROUS_LOCATORS frozenset above.
_DANGEROUS_PATTERNS: tuple[re.Pattern, ...] = (
    re.compile(r"^/html/"),
    re.compile(r"^xpath=/html/"),
)


def is_dangerously_generic(locator: str) -> bool:
    """Return True when the locator is too generic to trust.

    Empty / None → True (a healer that returns nothing is a failed heal).
    """
    if not locator:
        return True
    n = locator.strip().lower()
    if n in DANGEROUS_LOCATORS:
        return True
    for pat in _DANGEROUS_PATTERNS:
        if pat.search(n):
            return True
    if "nth-child" in n and len(n) < 30:
        return True
    return False
