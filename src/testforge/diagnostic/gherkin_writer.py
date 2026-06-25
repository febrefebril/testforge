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


# Phrasing chosen to be friendly to Cucumber/behave/pytest-bdd parsers.
_KIND_PHRASE = {
    "currency_BR": "com valor monetário",
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


def _safe_label(target: dict, fallback: str = "elemento") -> str:
    """Pick the most user-meaningful label, escape quotes."""
    candidates = (
        target.get("accessible_name"),
        target.get("label"),
        target.get("placeholder"),
        target.get("text"),
        target.get("element_id"),
    )
    for c in candidates:
        if isinstance(c, str) and c.strip():
            return c.strip().replace('"', "'")[:80]
    return fallback


class GherkinWriter:
    """Builds scenario.feature live during recording."""

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
        """First navigation seeds Funcionalidade. Subsequent navs become Dado lines."""
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
        """Append one step line for the given action."""
        target = target or {}
        line = self._render(action, target, value)
        if line:
            self._buffer.append(line)
        return line

    def _render(self, action: str, target: dict, value: Optional[str]) -> Optional[str]:
        keyword = self._next_keyword(action)
        label = _safe_label(target)
        if action == "click" or action == "submit":
            return f'  {keyword} clico no botão "{label}"'
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
            return f'  {keyword} vejo o texto "{expected}"'
        if action == "navigation":
            return None
        return f"  # ação não mapeada: {action} {label}"

    def _next_keyword(self, action: str) -> str:
        if action == "assert":
            if not self._then_emitted:
                self._then_emitted = True
                return "Então"
            return "E"
        # interactive action
        if not self._first_action_seen:
            self._first_action_seen = True
            self._then_emitted = False  # reset for next Then
            return "Quando"
        return "E"

    # ------------------------------------------------------------------
    def auto_cenario_from_sequence(self) -> str:
        """C4b — derive Cenário name from the most likely intent."""
        clicks = [l for l in self._buffer if "clico no botão" in l]
        if clicks:
            m = re.search(r'"([^"]+)"', clicks[0])
            if m:
                return f"Fluxo iniciado por '{m.group(1)}'"
        if self._funcionalidade:
            return f"Cenário em {self._funcionalidade[:60]}"
        return "Cenário gravado"

    def auto_funcionalidade(self) -> str:
        return self._funcionalidade or "Funcionalidade gravada"

    def write(
        self,
        funcionalidade_override: str = "",
        cenario_override: str = "",
    ) -> str:
        """Persist scenario.feature. Returns path."""
        func = (funcionalidade_override or self.auto_funcionalidade()).strip()
        cen = (cenario_override or self.auto_cenario_from_sequence()).strip()
        lines: list[str] = []
        if self._lang == "pt":
            lines.append("# language: pt")
        lines.append(f"Funcionalidade: {func}")
        lines.append("")
        lines.append(f"  Cenário: {cen}")
        for nav in self._navigation_lines:
            lines.append(f"    {nav}")
        for step in self._buffer:
            # already indented with 2 spaces — bump to 4
            lines.append("  " + step)
        Path(self._path).write_text("\n".join(lines) + "\n", encoding="utf-8")
        return self._path
