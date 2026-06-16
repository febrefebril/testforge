"""TestForge — Recording Normalizer.

Converte RawRecordedSession (JSONL) em SemanticTestCase (YAML).
Gera multiplos candidatos de locator ordenados por score deterministico.
"""
import json
import os
import re as _re
from typing import Optional

from .model import LocatorCandidate, SemanticAction, SemanticTarget, SemanticTestCase


def _is_hash_class(cls: str) -> bool:
    """Detect CSS classes that look like auto-generated hashes (e.g., 'css-1a2b3c4')."""
    if not cls:
        return True
    # Hashes usually have numbers mixed with letters and hyphens
    if _re.match(r'^[a-z]+-\d+[a-z0-9-]*$', cls):
        return True
    # Very short classes
    if len(cls) <= 1:
        return True
    # Namespaced hash-like: ng-star-inserted, mat-focus-indicator, etc.
    if _re.match(r'^(ng|mat|cdk|agm|leaflet|gm)-', cls):
        return False  # Framework classes are stable
    return False


# Material icon ligatures that appear in text content but are not real text
_MATERIAL_ICONS = {
    "home", "search", "calculate", "calculate_outline", "attach_money",
    "trending_up", "schedule", "arrow_forward", "arrow_back", "check",
    "close", "menu", "settings", "person", "delete", "edit", "add",
    "remove", "refresh", "download", "upload", "share", "favorite",
    "star", "info", "warning", "error", "visibility", "visibility_off",
    "calendar_today", "table_view", "list", "grid_view", "filter_list",
    "more_vert", "more_horiz", "expand_more", "expand_less", "chevron_right",
    "chevron_left", "open_in_new", "launch", "help", "support", "feedback",
    "account_balance", "payment", "shopping_cart", "credit_card",
    "location_on", "place", "phone", "email", "language", "lock",
    "cloud_upload", "cloud_download", "print", "save", "send",
    "keyboard_arrow_down", "keyboard_arrow_up", "keyboard_arrow_right",
    "keyboard_arrow_left", "cancel", "done", "clear",
}


def _clean_text(text: str) -> str:
    """Remove material icon ligatures from text content and truncate."""
    if not text:
        return ""
    # Split by whitespace and filter out material icons
    parts = text.split()
    cleaned = [p for p in parts if p.lower().replace("_", "") not in _MATERIAL_ICONS]
    result = " ".join(cleaned).strip()
    # Truncate long text for selector use
    if len(result) > 60:
        result = result[:57] + "..."
    return result


class RecordingNormalizer:
    """Converte raw events em SemanticTestCase."""

    def normalize(self, recording_dir: str, test_id: str = "",
                  application: str = "", base_url: str = "") -> SemanticTestCase:
        events_path = os.path.join(recording_dir, "raw_events.jsonl")
        if not os.path.exists(events_path):
            raise FileNotFoundError(f"raw_events.jsonl nao encontrado em {recording_dir}")

        with open(events_path) as f:
            raw_events = [json.loads(line) for line in f if line.strip()]

        recording_id = os.path.basename(recording_dir)
        stc = SemanticTestCase(
            test_id=test_id or f"ST-{recording_id}",
            source_recording_id=recording_id,
            application=application,
            base_url=base_url,
        )

        for raw in raw_events:
            action = self._convert_event(raw)
            if action:
                stc.steps.append(action)

        # Carrega steps (asserts) se existirem
        steps_path = os.path.join(recording_dir, "steps.jsonl")
        if os.path.exists(steps_path):
            with open(steps_path) as f:
                for line in f:
                    step = json.loads(line)
                    stc.steps.append(self._convert_step(step))

        return stc

    def _convert_event(self, raw: dict) -> Optional[SemanticAction]:
        event_type = raw.get("type", "")
        target_data = raw.get("target") or {}

        if event_type == "navigation":
            return SemanticAction(
                action="navigation",
                url=raw.get("url"),
                page_title=raw.get("page_title"),
            )

        target = self._build_target(target_data)

        action_map = {
            "click": "click",
            "fill": "fill",
            "keypress": "fill",
        }
        action = action_map.get(event_type)
        if not action:
            return None

        return SemanticAction(
            action=action,
            target=target,
            value=raw.get("value"),
            url=raw.get("url"),
            page_title=raw.get("page_title"),
        )

    def _convert_step(self, step: dict) -> Optional[SemanticAction]:
        step_action = step.get("action", "")
        if step_action == "assert":
            target_data = {
                "tag": step.get("tagName", ""),
                "text": step.get("text", ""),
                "id": step.get("selector", "").lstrip("#"),
            }
            target = self._build_target(target_data)
            assert_type = step.get("assert_type", "textual")
            assert_state = step.get("assert_state", "")
            return SemanticAction(
                action="assert",
                target=target,
                value=step.get("expected_value", ""),
                context={"assert_type": assert_type, "assert_state": assert_state},
            )
        return None

    def _build_target(self, target_data: dict) -> SemanticTarget:
        candidates = []
        text = target_data.get("text") or ""
        tag = (target_data.get("tag") or "").lower()

        # 0. data-testid (most stable)
        if target_data.get("test_id"):
            tid = target_data["test_id"]
            candidates.append(LocatorCandidate("test_id", f"[data-testid=\"{tid}\"]", 0.80, f"test_id={tid}"))

        # 0.1 data-* attributes (generic)
        data_attrs = target_data.get("data_attrs") or {}
        for attr_name, attr_value in data_attrs.items():
            if attr_name.startswith("data-") and attr_value and len(attr_value) < 60:
                sel = f"[{attr_name}='{attr_value}']"
                candidates.append(LocatorCandidate("data_attr", sel, 0.65, f"{attr_name}={attr_value}"))

        # For <select> elements: prefer name/id, NEVER use label + input
        if tag == "select":
            if target_data.get("name"):
                sel = f"select[name='{target_data['name']}']"
                candidates.append(LocatorCandidate("name", sel, 0.93, f"select name={target_data['name']}"))
            if target_data.get("id"):
                candidates.append(LocatorCandidate("id", f"#{target_data['id']}", 0.90, f"select id={target_data['id']}"))
            if target_data.get("label"):
                candidates.append(LocatorCandidate("label", f"select[aria-label='{target_data['label']}']", 0.75, f"select aria-label={target_data['label']}"))
            # Fallback: text content (options text)
            if text:
                candidates.append(LocatorCandidate("text", f"select:has-text('{_clean_text(text)[:40]}')", 0.35, f"select containing text"))

        # Prioridade de estrategias (score deterministico)
        if target_data.get("role"):
            role = target_data["role"]
            name = target_data.get("accessible_name") or _clean_text(target_data.get("text") or "")
            selector = f"role={role}"
            if name and len(name) <= 40:
                selector += f"[name=\"{name}\"]"
            candidates.append(LocatorCandidate("role", selector, 0.95 if name else 0.70, "role + accessible name"))

        if target_data.get("label") and target_data.get("id"):
            label = target_data["label"]
            el_id = target_data["id"]
            candidates.append(LocatorCandidate("label", f"label[for=\"{el_id}\"]", 0.90, f"label for={el_id}"))
        elif target_data.get("label"):
            label = target_data["label"]
            candidates.append(LocatorCandidate("label", f"label:has-text(\"{label}\") + input", 0.85, f"label adjacent={label}"))

        if target_data.get("placeholder"):
            ph = target_data["placeholder"]
            candidates.append(LocatorCandidate("placeholder", f"[placeholder=\"{ph}\"]", 0.85, f"placeholder={ph}"))

        if target_data.get("id") and target_data["id"] != "mat-input-0" and target_data["id"] != "mat-input-1":
            el_id = target_data["id"]
            candidates.append(LocatorCandidate("id", f"#{el_id}", 0.75, f"id={el_id}"))

        if target_data.get("name"):
            name = target_data["name"]
            candidates.append(LocatorCandidate("name", f"[name=\"{name}\"]", 0.70, f"name={name}"))

        if target_data.get("text"):
            text = _clean_text(target_data["text"])
            if text:
                # Use :has-text (substring match, more robust) instead of text= (exact match)
                candidates.append(LocatorCandidate("text", f":has-text(\"{text}\")", 0.55, f"visible text"))

        # Fallback: CSS classes (stable, non-hash, non-generic)
        class_list = target_data.get("class_list") or []
        # Exclude generic framework classes that match too broadly
        _generic_classes = {"mat-focus-indicator", "mat-ripple", "mat-button-focus-overlay",
                           "cdk-focused", "cdk-program-focused", "ng-star-inserted", "ng-untouched",
                           "ng-pristine", "ng-valid", "mat-form-field", "mat-form-field-flex"}
        stable_classes = [c for c in class_list
                         if not _is_hash_class(c) and len(c) >= 2
                         and c not in _generic_classes]
        if stable_classes and not candidates:
            cls_sel = ".".join(stable_classes[:3])
            candidates.append(LocatorCandidate("class", f".{cls_sel}", 0.35, f"CSS classes: {cls_sel}"))

        # Fallback: parent text for context
        parent_text = target_data.get("parent_text") or ""
        if parent_text and not candidates:
            candidates.append(LocatorCandidate("parent_text", f"text={parent_text[:60]}", 0.25, "parent text context"))

        # Fallback: aria attributes
        aria_attrs = target_data.get("aria_attrs") or {}
        for attr_name, attr_value in aria_attrs.items():
            if attr_value and len(attr_value) < 80 and attr_name != "aria-label":
                sel = f"[{attr_name}='{attr_value}']"
                candidates.append(LocatorCandidate("aria_attr", sel, 0.30, f"{attr_name}={attr_value}"))

        # Sort candidates by score (descending) for deterministic ordering
        candidates.sort(key=lambda c: c.score, reverse=True)

        return SemanticTarget(
            role=target_data.get("role"),
            accessible_name=target_data.get("accessible_name"),
            label=target_data.get("label"),
            placeholder=target_data.get("placeholder"),
            test_id=target_data.get("test_id"),
            text=target_data.get("text"),
            tag=target_data.get("tag"),
            element_id=target_data.get("id"),
            name=target_data.get("name"),
            candidates=candidates,
        )
