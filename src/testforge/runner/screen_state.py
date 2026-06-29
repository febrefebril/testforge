"""TestForge — ScreenStateTracker.

Snapshot {url, title, top_roles} antes/depois de cada step.
Detecta drift quando state-before do step N nao bate com state-after do step N-1
(ex: cura clicou em link que mandou app pra home e steps seguintes rodam na tela errada).

MVP Sprint 1: observa apenas. Bloqueio + escalation pra LLM ficam em Sprint 2.
"""
from __future__ import annotations
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Optional


_TOP_ROLES_JS = """
() => {
  const ROLES = ['button', 'link', 'textbox', 'combobox', 'checkbox', 'radio',
                 'tab', 'menuitem', 'heading', 'dialog'];
  function accessibleName(el) {
    const aria = el.getAttribute && el.getAttribute('aria-label');
    if (aria) return aria.trim().slice(0, 80);
    const labelledby = el.getAttribute && el.getAttribute('aria-labelledby');
    if (labelledby) {
      const ref = document.getElementById(labelledby);
      if (ref) return (ref.textContent || '').trim().slice(0, 80);
    }
    const txt = (el.textContent || el.value || el.placeholder || '').trim();
    return txt.slice(0, 80);
  }
  function impliedRole(el) {
    const tag = el.tagName.toLowerCase();
    if (tag === 'button') return 'button';
    if (tag === 'a' && el.href) return 'link';
    if (tag === 'input') {
      const t = (el.type || 'text').toLowerCase();
      if (t === 'checkbox') return 'checkbox';
      if (t === 'radio') return 'radio';
      if (t === 'submit' || t === 'button') return 'button';
      return 'textbox';
    }
    if (tag === 'select') return 'combobox';
    if (tag === 'textarea') return 'textbox';
    if (/^h[1-6]$/.test(tag)) return 'heading';
    return el.getAttribute('role') || '';
  }
  const out = [];
  const seen = new Set();
  const els = document.querySelectorAll('button,a,input,select,textarea,[role],h1,h2,h3');
  for (const el of els) {
    if (out.length >= 25) break;
    const role = (el.getAttribute('role') || impliedRole(el) || '').toLowerCase();
    if (!ROLES.includes(role)) continue;
    const rect = el.getBoundingClientRect();
    if (rect.width === 0 || rect.height === 0) continue;
    if (rect.top > window.innerHeight + 200 || rect.bottom < -200) continue;
    const name = accessibleName(el);
    const key = role + '|' + name;
    if (seen.has(key)) continue;
    seen.add(key);
    out.push({ role: role, name: name });
  }
  return out;
}
"""


@dataclass
class ScreenState:
    url: str = ""
    title: str = ""
    top_roles: list = field(default_factory=list)
    timestamp: str = ""

    def to_dict(self) -> dict:
        return asdict(self)

    def signature(self) -> str:
        """Hashable summary for cheap equality checks."""
        roles_sig = "|".join(f"{r.get('role','')}:{r.get('name','')}" for r in self.top_roles)
        return f"{self.url}::{self.title}::{roles_sig}"


@dataclass
class ScreenStateDiff:
    matched: bool = True
    url_changed: bool = False
    title_changed: bool = False
    role_overlap: float = 1.0
    reason: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


def capture_screen_state(page) -> ScreenState:
    """Snapshot {url, title, top_roles} via Playwright. Best-effort: returns empty on error."""
    state = ScreenState(timestamp=datetime.now(timezone.utc).isoformat())
    try:
        state.url = page.url or ""
    except Exception:
        state.url = ""
    try:
        state.title = (page.title() or "")[:200]
    except Exception:
        state.title = ""
    try:
        roles = page.evaluate(_TOP_ROLES_JS) or []
        state.top_roles = [
            {"role": r.get("role", ""), "name": r.get("name", "")}
            for r in roles if isinstance(r, dict)
        ]
    except Exception:
        state.top_roles = []
    return state


def compare(prev: Optional[ScreenState], curr: Optional[ScreenState]) -> ScreenStateDiff:
    """Compare two screen states. None on either side = matched (no info to compare).

    Match criteria:
      - URL equal (ignoring query string + fragment)
      - Title equal
      - >=60% overlap of (role, name) pairs

    Mismatch reason is human-readable to feed into healer context later.
    """
    if prev is None or curr is None:
        return ScreenStateDiff(matched=True, reason="no_baseline")

    diff = ScreenStateDiff()
    prev_url = (prev.url or "").split("?")[0].split("#")[0]
    curr_url = (curr.url or "").split("?")[0].split("#")[0]
    diff.url_changed = prev_url != curr_url
    diff.title_changed = (prev.title or "") != (curr.title or "")

    prev_keys = {(r.get("role", ""), r.get("name", "")) for r in prev.top_roles}
    curr_keys = {(r.get("role", ""), r.get("name", "")) for r in curr.top_roles}
    if not prev_keys and not curr_keys:
        diff.role_overlap = 1.0
    elif not prev_keys or not curr_keys:
        diff.role_overlap = 0.0
    else:
        diff.role_overlap = len(prev_keys & curr_keys) / max(len(prev_keys | curr_keys), 1)

    reasons = []
    if diff.url_changed:
        reasons.append(f"url:{prev_url}->{curr_url}")
    if diff.title_changed:
        reasons.append(f"title:{prev.title!r}->{curr.title!r}")
    if diff.role_overlap < 0.6:
        reasons.append(f"role_overlap:{diff.role_overlap:.2f}")

    diff.matched = not reasons
    diff.reason = "; ".join(reasons) if reasons else "match"
    return diff
