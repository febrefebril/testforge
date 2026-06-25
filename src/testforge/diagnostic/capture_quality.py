"""Sprint 0 commit 2 — CaptureQualityTracker.

Per-step assessment of what the recorder actually captured. Answers:
- Did we get a value, and from where? (event, setter hook, snapshot,
  final_state, network payload, or missing)
- What kind of value was it? (currency_BR, date, cpf, numeric, alpha)
- How long did the user type? Was there an idle gap before?
- Was the target inside a mat-form-field, cdk-overlay, or custom
  component?
- What is the stability of the generated primary selector?

The tracker is pure analysis — does not mutate raw events or steps.
Called from RecorderController after each `_persist_raw_event` when
the recorder is in `--diagnostic-mode`.
"""
from __future__ import annotations

import logging
import re
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)


# Value-kind regexes evaluated in order; first match wins.
_VALUE_KINDS = [
    ("empty", re.compile(r"^\s*$")),
    # Require either R$ prefix OR ",dd" decimal to avoid swallowing bare integers.
    ("currency_BR", re.compile(r"^(?:R?\$\s?[\d.]+(?:,\d{2})?|[\d.]+,\d{2})$")),
    ("date_BR", re.compile(r"^\d{2}/\d{2}/\d{4}$")),
    ("date_ISO", re.compile(r"^\d{4}-\d{2}-\d{2}")),
    ("cpf_BR", re.compile(r"^\d{3}\.\d{3}\.\d{3}-\d{2}$|^\d{11}$")),
    ("cnpj_BR", re.compile(r"^\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}$|^\d{14}$")),
    ("phone_BR", re.compile(r"^\(?\d{2}\)?\s?\d{4,5}-?\d{4}$")),
    ("cep_BR", re.compile(r"^\d{5}-?\d{3}$")),
    ("email", re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")),
    ("numeric", re.compile(r"^-?\d+(?:\.\d+)?$")),
    ("alpha", re.compile(r"^[A-Za-zÀ-ÿ ]+$")),
]

_CUSTOM_TAG_RE = re.compile(r"^[a-z][a-z0-9]*-[a-z0-9-]+$")


def detect_value_kind(value: Optional[str]) -> str:
    if value is None:
        return "missing"
    for kind, regex in _VALUE_KINDS:
        if regex.match(value):
            return kind
    return "other"


class CaptureQualityTracker:
    """Per-step quality assessment."""

    def __init__(self) -> None:
        self._last_ts: Optional[float] = None

    def assess(
        self,
        raw_event: dict,
        target_data: Optional[dict] = None,
        candidates: Optional[list] = None,
        framework: Optional[dict] = None,
        value_source_hint: Optional[str] = None,
    ) -> dict:
        """Build the steps.jsonl-friendly payload for one event."""
        target = target_data or raw_event.get("target") or {}
        value = raw_event.get("value")
        action = raw_event.get("type") or raw_event.get("action") or "unknown"
        ts_str = raw_event.get("timestamp") or ""
        ts = self._parse_iso(ts_str)
        idle_before = 0
        if ts is not None and self._last_ts is not None:
            idle_before = max(0, int((ts - self._last_ts) * 1000))
        if ts is not None:
            self._last_ts = ts

        ancestor_custom = self._custom_ancestors(target)
        is_mat = any(a.startswith("mat-") for a in ancestor_custom) or \
                 (target.get("tag") or "").lower().startswith("mat-")
        is_cdk_overlay = any("cdk-overlay" in (s or "") for s in self._selector_strings(candidates))

        candidate_count = len(candidates) if candidates else 0
        top3 = [getattr(c, "strategy", None) or c.get("strategy")
                for c in (candidates or [])[:3]]
        primary_selector = None
        primary_stability = None
        if candidates:
            first = candidates[0]
            primary_selector = getattr(first, "selector", None) or first.get("selector")
            primary_stability = getattr(first, "score", None) or first.get("score")

        value_kind = detect_value_kind(value)
        value_len = len(value) if isinstance(value, str) else 0
        value_source = value_source_hint or self._guess_source(raw_event, value)

        blind_spots: list[str] = []
        if action in ("fill", "input") and not value:
            blind_spots.append("typing_not_captured")
        if idle_before > 10_000:
            blind_spots.append("long_gap")
        if is_cdk_overlay and action == "click":
            blind_spots.append("overlay_click_noise")
        if not primary_selector:
            blind_spots.append("no_primary_selector")

        return {
            "step_id": raw_event.get("event_id") or raw_event.get("step_id"),
            "ts": ts_str,
            "action": action,
            "intent_text": self._intent_text(action, target, value),
            "capture_quality": {
                "value_captured_at_event": value is not None and value != "",
                "value_source": value_source,
                "value_kind": value_kind,
                "value_len": value_len,
                "value_pii_scrubbed": False,  # Sprint 0: F=skip
            },
            "selector_generated": {
                "primary": primary_selector,
                "candidates_count": candidate_count,
                "top3_strategies": top3,
                "stability_score": primary_stability,
            },
            "framework_signal": {
                "is_inside_mat_form_field": is_mat,
                "is_inside_cdk_overlay": is_cdk_overlay,
                "ancestor_custom_elements": ancestor_custom[:5],
                "primary_framework": (framework or {}).get("primary"),
            },
            "blind_spots": blind_spots,
            "timing": {"idle_before_ms": idle_before},
        }

    # ------------------------------------------------------------------
    @staticmethod
    def _selector_strings(candidates) -> list[str]:
        if not candidates:
            return []
        return [getattr(c, "selector", None) or c.get("selector", "")
                for c in candidates]

    @staticmethod
    def _custom_ancestors(target: dict) -> list[str]:
        # Walk a few hints we already extract — parent_chain, css_path
        out: list[str] = []
        css_path = target.get("css_path") or ""
        for token in re.findall(r"[a-z][a-z0-9-]+", css_path):
            if _CUSTOM_TAG_RE.match(token) and token not in out:
                out.append(token)
        for token in target.get("parent_chain") or []:
            if isinstance(token, str) and _CUSTOM_TAG_RE.match(token) and token not in out:
                out.append(token)
        return out

    @staticmethod
    def _guess_source(raw_event: dict, value) -> str:
        if value is None or value == "":
            return "missing"
        et = raw_event.get("type", "")
        if et == "fill" or et == "input":
            return "fill_event"
        if et == "select_option":
            return "select_event"
        if raw_event.get("form_values"):
            return "submit_form_values"
        return "raw_event"

    @staticmethod
    def _intent_text(action: str, target: dict, value) -> str:
        from ..semantic.locator.intent import normalize_intent
        return normalize_intent(
            action=action,
            role=target.get("role"),
            accessible_name=target.get("accessible_name"),
            label=target.get("label"),
            placeholder=target.get("placeholder"),
            text=target.get("text"),
            value=value if isinstance(value, str) else None,
        )

    @staticmethod
    def _parse_iso(ts: str) -> Optional[float]:
        if not ts:
            return None
        try:
            if ts.endswith("Z"):
                ts = ts[:-1] + "+00:00"
            return datetime.fromisoformat(ts).timestamp()
        except Exception:
            return None
