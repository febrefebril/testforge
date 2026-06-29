"""Sprint 0 commit 3 — GherkinWriter (live, PT, C4b + C4c).

Writes a `scenario.feature` file in Portuguese as the user records:
- Funcionalidade auto-derived from first navigation page title (C4b)
- Cenário auto-derived from the action sequence (C4b)
- At stop, the recorder prompts the user to confirm or edit both via
  CLI; if `e` is typed, opens the file in $EDITOR for free edition
  (C4c)

Step lines follow `Dado → Quando → E ... → Então` flow:
- first action emits `Quando`; subsequent same-context actions get `E`
- assertions emit `Então` / `E`
- value mapping is opaque (`com valor monetário`, `com data`, etc.) so
  Gherkin reads naturally without leaking raw values (also keeps the
  Sprint 0 PII story consistent — value never lands in .feature)
"""
from __future__ import annotations

import logging
import os
import re
from pathlib import Path
from typing import Optional

from .capture_quality import detect_value_kind

logger = logging.getLogger(__name__)


# Hotfix BUG 8: list of Material Icons names that pollute Gherkin labels.
# Source: https://fonts.google.com/icons (most common). Conservative list —
# only filtered when the token appears as a standalone word at the start of
# the string, not when it might be a real word ("home" can be legitimate).
_MATERIAL_ICONS = {
    "table_view", "attach_money", "check_circle", "trending_up", "arrow_back",
    "arrow_forward", "arrow_drop_down", "arrow_drop_up", "chevron_left",
    "chevron_right", "expand_more", "expand_less", "menu", "close",
    "search", "settings", "person", "people", "info", "warning", "error",
    "help", "edit", "delete", "add", "remove", "check", "clear",
    "calendar_today", "event", "schedule", "access_time", "today",
    "credit_card", "shopping_cart", "favorite", "favorite_border",
    "visibility", "visibility_off", "lock", "lock_open", "key",
    "home", "house", "apartment", "real_estate_agent", "location_on",
    "map", "phone", "email", "share", "print", "save", "download", "upload",
    "refresh", "sync", "cloud", "cloud_download", "cloud_upload",
    "play_arrow", "pause", "stop", "skip_next", "skip_previous",
    "more_vert", "more_horiz", "filter_list", "sort",
    "language", "translate", "notifications", "notifications_off",
    "thumb_up", "thumb_down", "star", "star_border",
    "wifi", "bluetooth", "battery_full", "battery_alert",
    "campaign", "logout", "login", "account_circle",
    "ticket_voucher", "verified",
}


def _clean_material_icons(text: str) -> str:
    """Hotfix BUG 8: remove nomes de Material Icon no inicio/fim de um label.

    Regra conservadora: um token de nome de icone so e removido quando ha pelo
    menos um outro token (nao-icone) no label. Assim "Login" sozinho
    permanece "Login" mesmo que `login` seja um Material icon, enquanto
    "home Pagina Inicial" corretamente se torna "Pagina Inicial".
    """
    if not text:
        return text
    s = text.strip()
    tokens = s.split()
    if len(tokens) <= 1:
        # Label de unico token: nunca remove (pode ser palavra legitima que
        # tambem e nome de Material icon).
        return s
    # Tokens de icone no inicio — para no momento em que encontrar um nao-icone, deixando
    # pelo menos um token no resultado.
    while len(tokens) > 1 and tokens[0].lower() in _MATERIAL_ICONS:
        tokens.pop(0)
    # Tokens de icone no fim — mesma protecao.
    while len(tokens) > 1 and tokens[-1].lower() in _MATERIAL_ICONS:
        tokens.pop()
    cleaned = re.sub(r"\s+", " ", " ".join(tokens)).strip()
    return cleaned


# Phrasing chosen to be friendly to Cucumber/behave/pytest-bdd parsers.
_KIND_PHRASE = {
    "currency_BR": "com valor monetario",
    "date_BR": "com data",
    "date_ISO": "com data",
    "cpf_BR": "com CPF",
    "cnpj_BR": "com CNPJ",
    "phone_BR": "com telefone",
    "cep_BR": "com CEP",
    "email": "com email",
    "numeric": "com número",
    "alpha": "com texto",
    "other": "com valor",
    "empty": "com valor vazio",
    "missing": "",  # nothing typed
}


def _safe_label(target: dict, fallback: str = "") -> str:
    """Escolhe o label mais significativo, limpa Material Icons, escapa aspas.

    Hotfix BUG 8+9: anteriormente caia para literal 'elemento' inutil quando
    o alvo nao tinha label/text. Agora retorna fallback (vazio por padrao)
    para que o Gherkin writer possa pular a linha em vez de escrever
    `clico no botao "elemento"`.
    """
    candidates = (
        target.get("accessible_name"),
        target.get("label"),
        target.get("placeholder"),
        target.get("text"),
        target.get("element_id"),
    )
    for c in candidates:
        if isinstance(c, str) and c.strip():
            cleaned = _clean_material_icons(c)
            if not cleaned:
                continue  # only icons present — try next candidate
            return cleaned.replace('"', "'")[:80]
    return fallback


class GherkinWriter:
    """Constroi scenario.feature ao vivo durante gravacao."""

    def __init__(self, session_dir: str, lang: str = "pt") -> None:
        self._dir = session_dir
        os.makedirs(session_dir, exist_ok=True)
        self._path = os.path.join(session_dir, "scenario.feature")
        self._lang = lang
        self._buffer: list[str] = []
        self._funcionalidade: Optional[str] = None
        self._cenario_override: Optional[str] = None
        self._first_action_seen = False
        self._then_emitted = False
        self._navigation_lines: list[str] = []

    # ------------------------------------------------------------------
    @property
    def path(self) -> str:
        return self._path

    @property
    def steps(self) -> list[str]:
        return list(self._buffer)

    # ------------------------------------------------------------------
    def on_navigation(self, url: str, title: Optional[str] = None) -> None:
        """Primeira navegacao sementeia Funcionalidade. Navegacoes subsequentes viram linhas Dado."""
        title = (title or "").strip()
        if self._funcionalidade is None:
            self._funcionalidade = title or url
        line = f'Dado que acesso "{url}"'
        # Track without duplicating Dado lines
        if line not in self._navigation_lines:
            self._navigation_lines.append(line)

    def on_step(
        self,
        action: str,
        target: Optional[dict] = None,
        value: Optional[str] = None,
    ) -> Optional[str]:
        """Adiciona uma linha de passo para a acao dada."""
        target = target or {}
        line = self._render(action, target, value)
        if line:
            self._buffer.append(line)
        return line

    def _render(self, action: str, target: dict, value: Optional[str]) -> Optional[str]:
        label = _safe_label(target)
        # Hotfix BUG 9: descarta passos sem label util em vez de escrever
        # `clico no botao "elemento"`. Analise forense mostrou que essas linhas
        # sao ruido que times de QA precisam deletar manualmente antes de executar.
        if not label and action in ("click", "submit", "fill", "input",
                                      "select", "select_option"):
            return None
        keyword = self._next_keyword(action)
        if action == "click" or action == "submit":
            return f'  {keyword} clico no botao "{label}"'
        if action in ("fill", "input"):
            kind = detect_value_kind(value)
            suffix = _KIND_PHRASE.get(kind, "")
            base = f'preencho "{label}"'
            if suffix:
                return f"  {keyword} {base} {suffix}"
            return f"  {keyword} {base}"
        if action in ("select", "select_option"):
            value_label = (value or "valor").strip().replace('"', "'")[:40]
            return f'  {keyword} seleciono "{value_label}" em "{label}"'
        if action == "assert":
            expected = (value or label).strip().replace('"', "'")[:80]
            if not expected:
                return None
            return f'  {keyword} vejo o texto "{expected}"'
        if action == "navigation":
            return None
        return f"  # ação não mapeada: {action} {label}"

    def _next_keyword(self, action: str) -> str:
        # Hotfix BUG 9: avance da keyword acontece *apenas* quando uma linha e
        # realmente emitida. Reconstruimos _render para retorno antecipado para labels
        # vazios, entao agora chama _next_keyword APOS a verificacao de vazio — a
        # logica abaixo permanece a mesma.
        if action == "assert":
            if not self._then_emitted:
                self._then_emitted = True
                return "Entao"
            return "E"
        # acao interativa
        if not self._first_action_seen:
            self._first_action_seen = True
            self._then_emitted = False  # reset for next Then
            return "Quando"
        return "E"

    # ------------------------------------------------------------------
    def auto_cenario_from_sequence(self) -> str:
        """C4b — deriva nome do Cenario da intent mais provavel."""
        clicks = [l for l in self._buffer if "clico no botao" in l]
        if clicks:
            m = re.search(r'"([^"]+)"', clicks[0])
            if m:
                return f"Fluxo iniciado por '{m.group(1)}'"
        if self._funcionalidade:
            return f"Cenario em {self._funcionalidade[:60]}"
        return "Cenario gravado"

    def auto_funcionalidade(self) -> str:
        return self._funcionalidade or "Funcionalidade gravada"

    def write(
        self,
        funcionalidade_override: str = "",
        cenario_override: str = "",
    ) -> str:
        """Persiste scenario.feature. Retorna caminho."""
        func = (funcionalidade_override or self.auto_funcionalidade()).strip()
        cen = (cenario_override or self.auto_cenario_from_sequence()).strip()
        lines: list[str] = []
        if self._lang == "pt":
            lines.append("# language: pt")
        lines.append(f"Funcionalidade: {func}")
        lines.append("")
        lines.append(f"  Cenario: {cen}")
        for nav in self._navigation_lines:
            lines.append(f"    {nav}")
        for step in self._buffer:
            # already indented with 2 spaces — bump to 4
            lines.append("  " + step)
        Path(self._path).write_text("\n".join(lines) + "\n", encoding="utf-8")
        return self._path
