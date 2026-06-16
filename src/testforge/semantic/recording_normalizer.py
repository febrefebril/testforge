"""TestForge — Recording Normalizer.

Converte RawRecordedSession (JSONL) em SemanticTestCase (YAML).
Gera multiplos candidatos de locator ordenados por score deterministico.
"""
import json
import os
import re as _re
from datetime import datetime
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


# Generic UI text that produces poor, brittle locators.
# Scored at 0.10 to deprioritize below all structural strategies.
_GENERIC_TEXT_SET = {
    "ok", "cancel", "cancelar", "submit", "enviar", "search", "buscar",
    "select", "selecione", "choose", "escolha", "next", "previous",
    "back", "voltar", "close", "fechar", "save", "salvar", "delete",
    "excluir", "edit", "editar", "add", "adicionar", "remove", "remover",
    "filter", "filtrar", "sort", "ordenar", "reset", "limpar",
    "página inicial", "pagina inicial", "home", "início", "inicio",
    "calculate", "calcular", "download", "upload", "print", "imprimir",
    "refresh", "atualizar", "help", "ajuda", "settings", "configurações",
    "yes", "sim", "no", "não", "nao", "confirm", "confirmar",
    "login", "logout", "sign in", "sign out", "register", "cadastrar",
    "load more", "carregar mais", "show more", "mostrar mais",
    "read more", "saiba mais", "click here", "clique aqui",
}


def _is_generic_text(text: str) -> bool:
    """Check if text is a generic UI label that produces brittle locators.

    Returns True for text like 'OK', 'Cancelar', 'Selecione', etc.
    These are common across many pages and produce non-unique selectors.
    """
    if not text or not text.strip():
        return True
    clean = text.strip().lower()
    # Exact match in generic set
    if clean in _GENERIC_TEXT_SET:
        return True
    # Single character or only digits
    if len(clean) <= 1 or clean.isdigit():
        return True
    return False


class RecordingNormalizer:
    """Converte raw events em SemanticTestCase."""

    def normalize(self, recording_dir: str, test_id: str = "",
                  application: str = "", base_url: str = "") -> SemanticTestCase:
        events_path = os.path.join(recording_dir, "raw_events.jsonl")
        if not os.path.exists(events_path):
            raise FileNotFoundError(f"raw_events.jsonl nao encontrado em {recording_dir}")

        with open(events_path) as f:
            raw_events = [json.loads(line) for line in f if line.strip()]

        raw_events = self._compact_fill_events(raw_events)

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

        # Post-process: detect and mark skipped steps
        self._deduplicate_steps(stc.steps)
        self._mark_non_actionable(stc.steps)
        self._detect_step_dependencies(stc.steps)

        return stc

    def _compact_fill_events(self, raw_events: list) -> list:
        """Compact sequential fill events on same element within 500ms window.

        When user types into a field, the recorder captures each keystroke as a
        separate fill/keypress event. Consecutive events on the same target
        within 500ms of each other are collapsed — only the final event (which
        holds the complete value) is kept.
        """
        if not raw_events:
            return raw_events

        FILL_TYPES = {"fill", "keypress"}

        def _target_key(target: dict | None) -> tuple:
            """Derive stable key from target to identify same element."""
            if not target:
                return ("__none__",)
            return (
                target.get("tag", ""),
                target.get("id", ""),
                target.get("name", ""),
                target.get("test_id", ""),
                target.get("placeholder", ""),
            )

        def _parse_ts(ts: str) -> float:
            try:
                dt = datetime.fromisoformat(ts)
                return dt.timestamp()
            except (ValueError, TypeError):
                return 0.0

        compacted: list = []
        i = 0
        while i < len(raw_events):
            event = raw_events[i]
            event_type = event.get("type", "")

            if event_type not in FILL_TYPES:
                compacted.append(event)
                i += 1
                continue

            # Start of a potential fill group on the same target
            current_key = _target_key(event.get("target"))
            current_ts = _parse_ts(event.get("timestamp", ""))
            group_end = i

            j = i + 1
            while j < len(raw_events):
                next_event = raw_events[j]
                next_type = next_event.get("type", "")

                if next_type not in FILL_TYPES:
                    break

                next_key = _target_key(next_event.get("target"))
                next_ts = _parse_ts(next_event.get("timestamp", ""))

                if next_key != current_key:
                    break

                if (next_ts - current_ts) > 0.5:  # 500ms sliding window
                    break

                group_end = j
                current_ts = next_ts
                j += 1

            # Keep only the final event (holds the complete typed value)
            compacted.append(raw_events[group_end])
            i = j

        return compacted

    def _convert_event(self, raw: dict) -> Optional[SemanticAction]:
        event_type = raw.get("type", "")
        target_data = raw.get("target") or {}

        if event_type == "navigation":
            return SemanticAction(
                action="navigation",
                url=raw.get("url"),
                page_title=raw.get("page_title"),
            )

        # postback events are server-side page reloads after form submission.
        # They are not separate user actions — the submit already implies navigation.
        # Skip them to avoid page reload flicker in recorded tests.
        if event_type == "postback":
            return None

        target = self._build_target(target_data)

        action_map = {
            "click": "click",
            "fill": "fill",
            "keypress": "fill",
            "submit": "click",  # submit is a click on a submit button
        }
        action = action_map.get(event_type)
        if not action:
            return None

        is_submit = event_type == "submit"
        context = {}
        if is_submit:
            context["is_submit"] = True
            if raw.get("submit_method"):
                context["submit_method"] = raw["submit_method"]
            # If the submit event was restored from sessionStorage after navigation,
            # it carries the postback URL (the page we landed on). Preserve it for
            # the compiler to generate proper wait_for_load_state or URL assertion.
            if raw.get("postback_url"):
                context["postback_url"] = raw["postback_url"]
            if raw.get("is_postback"):
                context["is_postback"] = True
        return SemanticAction(
            action=action,
            target=target,
            value=raw.get("value"),
            url=raw.get("url"),
            page_title=raw.get("page_title"),
            context=context,
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
        # Non-assert curated steps (fill, click, select_option, etc.)
        if step_action in ("fill", "click", "select_option", "navigation"):
            target_data = {
                "tag": step.get("tagName", ""),
                "text": step.get("text", ""),
                "id": step.get("selector", "").lstrip("#"),
                "role": step.get("role", ""),
                "accessible_name": step.get("accessible_name", ""),
                "label": step.get("label", ""),
                "placeholder": step.get("placeholder", ""),
                "name": step.get("name", ""),
                "test_id": step.get("test_id", ""),
            }
            target = self._build_target(target_data)
            return SemanticAction(
                action=step_action,
                target=target,
                value=step.get("value", ""),
                url=step.get("url", ""),
                page_title=step.get("page_title", ""),
                context=step.get("context", {}),
                blocking=step.get("blocking", False),
                depends_on=step.get("depends_on", ""),
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
                select_text = _clean_text(text)[:40]
                select_score = 0.10 if _is_generic_text(select_text) else 0.35
                candidates.append(LocatorCandidate("text", f"select:has-text('{select_text}')", select_score, "select containing text"))

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
                # Penalize generic text like "OK", "Cancelar", "Selecione" — brittle locators
                text_score = 0.10 if _is_generic_text(text) else 0.55
                candidates.append(LocatorCandidate("text", f":has-text(\"{text}\")", text_score, "visible text"))

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

    def _steps_identical(self, a: SemanticAction, b: SemanticAction) -> bool:
        """Check if two steps are identical (same action, value, target candidates)."""
        if a.action != b.action:
            return False
        if (a.value or "") != (b.value or ""):
            return False
        # Compare target candidates (selectors and scores)
        a_cands = a.target.candidates if a.target else []
        b_cands = b.target.candidates if b.target else []
        if len(a_cands) != len(b_cands):
            return False
        for ac, bc in zip(a_cands, b_cands):
            if ac.selector != bc.selector or ac.score != bc.score:
                return False
        return True

    def _deduplicate_steps(self, steps: list) -> None:
        """Mark consecutive duplicate steps with skip_reason.

        Consecutive steps with identical action, value, and target candidates
        are flagged as duplicates. Only the first occurrence is kept active;
        subsequent ones get skip_reason = 'Step N: skipped — duplicate'.
        """
        for i in range(1, len(steps)):
            prev = steps[i - 1]
            curr = steps[i]
            if (not prev.skip_reason and not curr.skip_reason
                    and self._steps_identical(prev, curr)):
                curr.skip_reason = f"Step {i + 1}: skipped — duplicate"

    def _mark_non_actionable(self, steps: list) -> None:
        """Mark steps with no actionable target as skipped.

        Steps with action in (click, fill) that have a target but zero
        locator candidates cannot be executed reliably. Mark them with
        skip_reason = 'non-actionable target'.
        """
        ACTIONABLE_ACTIONS = {"click", "fill"}
        for i, step in enumerate(steps):
            if step.skip_reason:
                continue
            if step.action not in ACTIONABLE_ACTIONS:
                continue
            if step.target and len(step.target.candidates) == 0:
                step.skip_reason = "non-actionable target"

    def _detect_step_dependencies(self, steps: list) -> None:
        """Detect step dependencies for cascading failure prevention.

        When consecutive data-entry actions (fill, click, select_option)
        occur on the same page with at least one <select> element involved,
        they are likely dependent: the first select populates the next
        dropdown (e.g., UF → Edifício → Data on SIMAX).

        The first step in the chain is marked `blocking: True`. Subsequent
        steps get `depends_on` referencing the blocking step by its 1-based
        index (e.g., 'step_0003').

        Steps that already have explicit `depends_on` or `blocking` set
        (via curated steps.jsonl) are preserved and not auto-detected.
        """
        # Find groups of consecutive data-entry steps between navigation
        # boundaries. Only create dependency when at least one <select>
        # element is involved (SIMAX pattern: UF → Edifício → Data).
        DEPENDENT_ACTIONS = {"select_option", "fill", "click"}

        i = 0
        while i < len(steps):
            step = steps[i]
            # Skip steps that already have explicit dependency annotations
            if step.depends_on or step.blocking:
                i += 1
                continue
            if step.action not in DEPENDENT_ACTIONS:
                i += 1
                continue
            if step.skip_reason:
                i += 1
                continue

            # Find the end of this dependent chain (stops at navigation or assert)
            chain_start = i
            j = i + 1
            while j < len(steps):
                next_step = steps[j]
                if next_step.action == "navigation":
                    break
                if next_step.action == "assert":
                    break
                if next_step.skip_reason:
                    break
                if next_step.depends_on or next_step.blocking:
                    break
                if next_step.action not in DEPENDENT_ACTIONS:
                    j += 1
                    continue
                j += 1

            chain_end = j
            chain_length = chain_end - chain_start

            # Only create dependency if chain has 2+ steps AND at least one
            # involves a <select> element (the SIMAX cascading dropdown pattern).
            if chain_length >= 2:
                has_select = any(
                    steps[k].target and (steps[k].target.tag or "").lower() == "select"
                    for k in range(chain_start, chain_end)
                )
                if has_select:
                    # First step in chain is blocking
                    steps[chain_start].blocking = True
                    # Subsequent steps depend on the first
                    for k in range(chain_start + 1, chain_end):
                        step_num = chain_start + 1  # 1-based index
                        steps[k].depends_on = f"step_{step_num:04d}"

            i = chain_end
