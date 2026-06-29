"""Filtro centralizado de locator perigoso.

B19/B20 (2026-06-27): o IncrementalRunner tinha um conjunto `_DANGEROUS_LOCATORS`
+ predicado `_is_dangerously_generic`; o caminho legado `run` nao tinha.
Uma execucao SIOPI produziu 26 curas L2 consecutivas todas resolvendo para
`a[href="/"]` (o link home), aprovadas pelo oracle como sucesso porque o
link existia em toda pagina. Para parar a cascata de falso-positivo nos (1)
ampliamos a lista de negacao, (2) movemos para um modulo unico que ambos
os runners importam.

Adicione novos padroes por categoria:
- nomes de tag simples (`a`, `div`, `button`) — sempre muito genericos.
- nav helpers (`a[href="/"]`, `a[href="#"]`, `a[href=""]`) — presentes
  em toda pagina de um SPA tipico.
- role helpers sem texto (`[role="button"]`, `[role="link"]`).
- seletores CSS-only `nth-child` abaixo de ~30 chars — quase nunca estaveis.

Futuro: quando tivermos telemetria de evidencia, threshold por taxa-de-acerto (um
locator e perigoso quando corresponde a >K elementos no site todo).
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
    """Retorna True quando o locator e muito generico para ser confiavel.

    Vazio / None → True (um healer que retorna nada e uma cura falha).
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
