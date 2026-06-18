"""TestForge — Recording Normalizer.

Converte RawRecordedSession (JSONL) em SemanticTestCase (YAML).
Gera multiplos candidatos de locator ordenados por score deterministico.
"""
import json
import os
import re as _re
from datetime import datetime
from typing import Optional
from urllib.parse import urlparse, urlunparse

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
    "remove", "refresh", "download", "upload", "file_upload", "file_download",
    "share", "favorite", "star", "info", "warning", "error",
    "visibility", "visibility_off", "calendar_today", "table_view",
    "list", "grid_view", "filter_list", "more_vert", "more_horiz",
    "expand_more", "expand_less", "chevron_right", "chevron_left",
    "open_in_new", "launch", "help", "support", "feedback",
    "account_balance", "payment", "shopping_cart", "credit_card",
    "location_on", "place", "phone", "email", "language", "lock",
    "cloud_upload", "cloud_download", "print", "save", "send",
    "keyboard_arrow_down", "keyboard_arrow_up", "keyboard_arrow_right",
    "keyboard_arrow_left", "cancel", "done", "clear",
    "fact_check", "paid", "receipt", "monetization_on",
}


def _clean_text(text: str) -> str:
    """Remove material icon ligatures from text content and truncate."""
    if not text:
        return ""
    # Split by whitespace and filter out material icons
    parts = text.split()
    cleaned = []
    for p in parts:
        pl = p.lower()
        # Exact match: whole word is a material icon
        if pl in _MATERIAL_ICONS:
            continue
        # Prefix match: material icon fused with next word (e.g., "attach_moneyValor")
        stripped = p
        for icon in sorted(_MATERIAL_ICONS, key=len, reverse=True):
            if pl.startswith(icon) and len(pl) > len(icon):
                # Check boundary: icon ends, next char is uppercase (camelCase) or space-equivalent
                next_char = p[len(icon):len(icon)+1]
                if next_char.isupper() or next_char in '_-':
                    stripped = p[len(icon):]
                    break
        cleaned.append(stripped)
    result = " ".join(cleaned).strip()
    # Truncate long text for selector use (no "...": has-text() needs real substring)
    if len(result) > 60:
        result = result[:60]
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
    "download", "upload", "print", "imprimir",
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


# Transient CSS classes that change between recording and playback.
# Angular/Material state classes: focus, form validity, animations.
_TRANSIENT_CLASS_PATTERNS = [
    # Angular CDK focus/blur states
    r'cdk-(mouse-)?focused',
    r'cdk-program-focused',
    r'cdk-keyboard-focused',
    # Angular form control states (ng-untouched/ng-touched, ng-pristine/ng-dirty, ng-valid/ng-invalid)
    r'ng-(un)?touched',
    r'ng-(pristine|dirty)',
    r'ng-(valid|invalid|pending)',
    r'ng-star-inserted',
    # Angular Material animation state
    r'mat-(mdc-)?form-field-animations-enabled',
    r'mat-(mdc-)?form-field--empty',
    r'mat-unthemed',
    # Playwright/Material state attributes (transient identifiers)
    r'mat-ripple-loader-(uninitialized|centered|disabled|class-name)',
    r'mat-mdc-button-ripple',
    r'mat-(mdc-)?form-field--standard',  # variant can change
]


def _strip_transient_classes(css_path: str) -> str:
    """Remove Angular transient state classes from CSS path selector.

    Classes like cdk-focused, ng-untouched, ng-valid change between
    recording and playback. Stripping them makes CSS paths reusable.

    Preserves original CSS selector syntax (space-separated classes,
    special chars like Tailwind ':' in md:p-12).
    """
    if not css_path:
        return css_path

    import re
    _transient_re = re.compile(
        r'^(?:' + '|'.join(_TRANSIENT_CLASS_PATTERNS) + r')$'
    )

    # CSS path: "tag.class1 class2 > tag2.class3 class4 > ..."
    segments = css_path.split(' > ')
    cleaned_segments = []

    for seg in segments:
        # Split into tokens: "tag.class1", "class2", "class3"
        tokens = seg.split()
        if not tokens:
            cleaned_segments.append(seg)
            continue

        # First token: "tag.class1" or just "tag"
        first = tokens[0]
        # Rest: standalone class names
        rest = tokens[1:]

        # Filter transient classes from rest
        kept_rest = [c for c in rest if not _transient_re.match(c)]

        # Also check if first token has transient classes after dot
        if '.' in first:
            dot_parts = first.split('.')
            tag = dot_parts[0]
            tag_classes = dot_parts[1:]
            kept_tag_classes = [c for c in tag_classes if not _transient_re.match(c)]
            if kept_tag_classes:
                first_clean = tag + '.' + '.'.join(kept_tag_classes)
            else:
                first_clean = tag
        else:
            first_clean = first

        # Reconstruct: "tag.class1 class2 class3"
        if kept_rest:
            cleaned_segments.append(first_clean + ' ' + ' '.join(kept_rest))
        else:
            cleaned_segments.append(first_clean)

    return ' > '.join(cleaned_segments)


def _is_dynamic_aria_attr(attr_name: str, attr_value: str) -> bool:
    """Check if an aria attribute value contains dynamic/Angular-generated IDs.

    Angular Material generates IDs like 'mat-mdc-hint-1', 'numeric-field-desc-abc123'
    that change on every page load. These are useless as selectors.
    """
    if attr_name == "aria-describedby":
        # Angular Material hint IDs: mat-mdc-hint-N
        if "mat-mdc-hint-" in attr_value:
            return True
        # Random-suffix field descriptions: numeric-field-desc-<random>
        if "field-desc-" in attr_value and len(attr_value) > 25:
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
        # Detect overlays FIRST — deduplication excludes overlay steps
        self._detect_overlay_steps(stc.steps)
        self._deduplicate_steps(stc.steps)
        self._mark_non_actionable(stc.steps)
        self._detect_step_dependencies(stc.steps)
        self._detect_navigation_clicks(stc.steps)

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
            name = (_clean_text(target_data.get("accessible_name") or "")
                    or _clean_text(target_data.get("text") or "")
                    or _clean_text((target_data.get("all_attributes") or {}).get("aria-label", "")))
            selector = f"role={role}"
            has_name = bool(name and len(name) <= 40)
            if has_name:
                selector += f"[name=\"{name}\"]"
            # Bare role (no accessible name in selector) is ambiguous — deprioritize below text-based selectors.
            # On pages with multiple role=button elements, bare role clicks wrong element.
            candidates.append(LocatorCandidate("role", selector, 0.95 if has_name else 0.45, "role + accessible name"))

        if target_data.get("label") and target_data.get("id"):
            label = target_data["label"]
            el_id = target_data["id"]
            candidates.append(LocatorCandidate("label", f"label[for=\"{el_id}\"]", 0.90, f"label for={el_id}"))
        elif target_data.get("label"):
            label = target_data["label"]
            candidates.append(LocatorCandidate("label", f"label:has-text(\"{label}\") + input", 0.85, f"label adjacent={label}"))

        if target_data.get("placeholder"):
            ph = target_data["placeholder"]
            tag = (target_data.get("tag") or "").lower()
            # Prefer input[placeholder] over bare [placeholder] — Angular wrappers
            # (dsc-input-currency) share placeholders with native inputs, causing
            # strict mode violations and fill() failures on non-input elements.
            if tag in ("input", "textarea", "select"):
                sel = f"{tag}[placeholder=\"{ph}\"]"
            else:
                sel = f"[placeholder=\"{ph}\"]"
            candidates.append(LocatorCandidate("placeholder", sel, 0.85, f"placeholder={ph}"))

        if target_data.get("id") and target_data["id"] != "mat-input-0" and target_data["id"] != "mat-input-1":
            el_id = target_data["id"]
            candidates.append(LocatorCandidate("id", f"#{el_id}", 0.75, f"id={el_id}"))

        if target_data.get("name"):
            name = target_data["name"]
            candidates.append(LocatorCandidate("name", f"[name=\"{name}\"]", 0.70, f"name={name}"))

        if target_data.get("text"):
            text = _clean_text(target_data["text"])
            if text:
                # Penalize generic text like "OK", "Cancelar", "Selecione" — brittle locators
                text_score = 0.10 if _is_generic_text(text) else 0.55
                # Always include tag when available — bare :has-text() clicks on child elements
                # instead of the link/button itself, breaking SPA navigation.
                tag = (target_data.get("tag") or "").lower()
                if tag:
                    candidates.append(LocatorCandidate("text", f"{tag}:has-text(\"{text}\")", text_score, f"text in {tag}"))
                else:
                    candidates.append(LocatorCandidate("text", f":has-text(\"{text}\")", text_score, "visible text"))
        elif target_data.get("inner_html"):
            # Fallback: use inner HTML as text source (for elements like datepicker spans)
            inner = _clean_text(target_data["inner_html"])
            if inner:
                tag = (target_data.get("tag") or "").lower()
                sel = f"{tag}:has-text(\"{inner}\")" if tag else f":has-text(\"{inner}\")"
                candidates.append(LocatorCandidate("inner_html", sel, 0.45, "inner HTML text"))

        # Fallback: CSS path
        css_path = target_data.get("css_path") or ""
        if css_path and not candidates:
            css_clean = _strip_transient_classes(css_path)
            candidates.append(LocatorCandidate("css_path", css_clean, 0.20, "CSS path fallback"))

            # Heuristic: Angular Material datepicker toggle — target is often
            # <span.mat-mdc-button-touch-target> inside <button> inside <mat-datepicker-toggle>.
            # Generate a reliable fallback selector.
            if "mat-datepicker-toggle" in css_path:
                candidates.append(LocatorCandidate(
                    "material_touch_target", "mat-datepicker-toggle button",
                    0.50, "Material datepicker toggle button"
                ))

            # Heuristic: Calendar overlay navigation buttons.
            # Target is <span.mat-focus-indicator> inside <button.mat-calendar-*-button>.
            if "mat-calendar-previous-button" in css_path:
                candidates.append(LocatorCandidate(
                    "material_nav", "button.mat-calendar-previous-button",
                    0.50, "Material calendar previous month button"
                ))
            if "mat-calendar-next-button" in css_path:
                candidates.append(LocatorCandidate(
                    "material_nav", "button.mat-calendar-next-button",
                    0.50, "Material calendar next month button"
                ))
            if "mat-calendar-period-button" in css_path:
                candidates.append(LocatorCandidate(
                    "material_nav", "button.mat-calendar-period-button",
                    0.50, "Material calendar period button"
                ))

            # Heuristic: Calendar cell clicks — target is <span> inside <button.mat-calendar-body-cell>.
            # Clicking the span doesn't trigger the button's handler. Generate button:has-text() instead.
            if tag == "span" and "mat-calendar-body-cell" in css_path and target_data.get("text"):
                cell_text = _clean_text(target_data["text"])
                if cell_text:
                    candidates.append(LocatorCandidate(
                        "material_cell", f"button.mat-calendar-body-cell:has-text(\"{cell_text}\")",
                        0.50, f"Material calendar cell: {cell_text}"
                    ))

            # Heuristic: Material button touch targets — <span.mat-mdc-button-touch-target>
            # inside <button>. Click the button, not the transparent touch overlay.
            if tag == "span" and "mat-mdc-button-touch-target" in css_path and "button" in css_path:
                # Try to extract button text from CSS path context
                parent_text = target_data.get("parent_text") or ""
                if parent_text:
                    clean_parent = _clean_text(parent_text)
                    if clean_parent and not _is_generic_text(clean_parent):
                        candidates.append(LocatorCandidate(
                            "material_btn", f"button:has-text(\"{clean_parent}\")",
                            0.50, f"Material button by text: {clean_parent}"
                        ))

        # Fallback: XPath (lowest priority)
        xpath = target_data.get("xpath") or ""
        if xpath and not candidates:
            candidates.append(LocatorCandidate("xpath", xpath, 0.10, "XPath fallback"))

        # Fallback: nth-child for disambiguation
        nth = target_data.get("nth_child") or 0
        tag = target_data.get("tag") or ""
        if nth > 0 and tag and not candidates:
            candidates.append(LocatorCandidate("nth_child", f"{tag}:nth-child({nth})", 0.15, f"nth-child position"))

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
                # Skip dynamic Angular Material IDs that change every page load
                if _is_dynamic_aria_attr(attr_name, attr_value):
                    continue
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

        Does NOT deduplicate overlay steps (calendar, modal, dialog) where
        repeated clicks are intentional incremental navigation (e.g., clicking
        previous-month multiple times to reach a distant year).
        """
        for i in range(1, len(steps)):
            prev = steps[i - 1]
            curr = steps[i]
            if (not prev.skip_reason and not curr.skip_reason
                    and self._steps_identical(prev, curr)):
                # Skip deduplication for overlay steps — repeated clicks are intentional
                if curr.context.get("overlay_step") or prev.context.get("overlay_step"):
                    continue
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

    def _detect_overlay_steps(self, steps: list) -> None:
        """Detect steps inside overlay containers (calendar, modal, dialog)."""
        OVERLAY_PATTERNS = ['cdk-overlay', 'mat-calendar', 'mat-datepicker', 'modal', 'dialog']

        for i, step in enumerate(steps):
            if not step.target or not step.target.candidates:
                continue
            # Check if any candidate selector targets an overlay element
            is_overlay = any(
                any(p in c.selector for p in OVERLAY_PATTERNS)
                for c in step.target.candidates
            )
            if is_overlay:
                step.context["overlay_step"] = True
                # Mark the step BEFORE as the overlay trigger
                if i > 0 and steps[i-1].action == "click" and not steps[i-1].context.get("overlay_step"):
                    steps[i-1].context["overlay_trigger"] = True

    def _detect_navigation_clicks(self, steps: list) -> None:
        """Detect clicks that cause URL changes (SPA navigation).

        Compares consecutive non-navigation steps: if the URL changes between
        step A and step B, marks step A with causes_navigation=True so the
        compiler injects wait_for_load_state('networkidle') after the click.
        """
        # Build list of (index, step) for non-navigation steps
        actionable = [(i, s) for i, s in enumerate(steps)
                      if s.action != "navigation" and not s.skip_reason]

        for ai in range(len(actionable) - 1):
            i_prev, s_prev = actionable[ai]
            i_next, s_next = actionable[ai + 1]

            prev_url = self._normalize_url(s_prev.url or "")
            next_url = self._normalize_url(s_next.url or "")

            if prev_url and next_url and prev_url != next_url:
                s_prev.context["causes_navigation"] = True

    @staticmethod
    def _normalize_url(url: str) -> str:
        """Strip trailing slash and query params for URL comparison."""
        if not url:
            return ""
        parsed = urlparse(url)
        # Reconstruct without query, fragment, trailing slash
        path = parsed.path.rstrip("/")
        return urlunparse((parsed.scheme, parsed.netloc, path, "", "", ""))
