"""TestForge — Normalizador de Gravação.

Converte RawRecordedSession (JSONL) em SemanticTestCase (YAML).
Gera múltiplos candidatos de localizador ordenados por score determinístico.
"""
import json
import os
import re as _re
from datetime import datetime
from typing import Optional
from urllib.parse import urlparse, urlunparse

from .model import LocatorCandidate, SemanticAction, SemanticTarget, SemanticTestCase


def _is_hash_class(cls: str) -> bool:
    """Detecta classes CSS que parecem hashes gerados automaticamente (ex: 'css-1a2b3c4')."""
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


def _clean_text(text: str, max_len: int = 60) -> str:
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
    if len(result) > max_len:
        result = result[:max_len]
    return result


# Generic UI text that produces poor, brittle locators.
# Scored at 0.10 to deprioritize below all structural strategies.
# Angular Material auto-generates IDs like mat-mdc-error-1, mat-input-3, mat-hint-0.
# These change between runs when the number of form fields changes.
_ANGULAR_AUTOID_RE = _re.compile(r'^mat-[\w]+-[\w]+-\d+$|^mat-[\w]+-\d+$')

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

        # Run dedup BEFORE compaction: removes periodic DOM snapshot cycles
        # (e.g. radio button spam) so consecutive fills on the same field
        # become adjacent and get properly collapsed.
        raw_events = self._remove_snapshot_duplicates(raw_events)
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
        # Phase B: reconstruct from evidence BEFORE missing_fill heuristics
        self._reconstruct_intents(stc, recording_dir)
        self._detect_missing_fills(stc.steps)
        self._build_field_value_map(stc)
        # Phase B semantic dedup: collapse datepicker nav + prefill clicks
        self._dedup_datepicker_sequences(stc.steps)
        self._eliminate_prefill_clicks(stc.steps)
        self._audit_blind_spots(stc)
        return stc

    def _eliminate_prefill_clicks(self, steps: list) -> None:
        """Mark click steps that are immediately followed by fill on same element as skipped.

        Angular Material inputs require a click to focus before fill, but Playwright's
        fill() already handles focus internally. Recording both click + fill on the same
        element produces a healed click step every run — eliminate the noise.
        """
        for i in range(len(steps) - 1):
            curr = steps[i]
            if curr.skip_reason or curr.action != "click":
                continue
            # Find next non-skipped step
            nxt = None
            for k in range(i + 1, min(i + 4, len(steps))):
                if not steps[k].skip_reason:
                    nxt = steps[k]
                    break
            if nxt is None or nxt.action != "fill":
                continue
            curr_tag = (curr.target.tag or "").lower() if curr.target else ""
            if curr_tag not in ("input", "textarea"):
                continue
            # Same element: match by element_id or first candidate selector
            curr_id = (curr.target.element_id or "") if curr.target else ""
            nxt_id = (nxt.target.element_id or "") if nxt.target else ""
            curr_sel = curr.target.candidates[0].selector if curr.target and curr.target.candidates else ""
            nxt_sel = nxt.target.candidates[0].selector if nxt.target and nxt.target.candidates else ""
            same = (curr_id and curr_id == nxt_id) or (curr_sel and curr_sel == nxt_sel)
            if same:
                curr.skip_reason = "prefill_click_noise"

    def _dedup_datepicker_sequences(self, steps: list) -> None:
        """Collapse Angular Material datepicker calendar navigation into the text fill.

        Pattern: (open toggle) + (calendar nav clicks) + (fill on text input with date)
        The text fill is the canonical intent. Calendar navigation is fragile because it
        depends on which month the calendar opens at (current date changes between runs).
        Keep only the fill, mark calendar steps as skipped.
        """
        DATEPICKER_SELECTORS = {
            "mat-datepicker-toggle button",
            "button.mat-calendar-previous-button",
            "button.mat-calendar-next-button",
            "button.mat-calendar-period-button",
        }

        i = 0
        while i < len(steps):
            step = steps[i]
            if step.skip_reason or step.action != "click":
                i += 1
                continue
            sel = step.target.candidates[0].selector if step.target and step.target.candidates else ""
            css_path = step.target.id if step.target else ""  # css_path stored in target.id

            # Detect datepicker toggle open — check both primary selector AND css_path (css_path contains
            # mat-datepicker-toggle / mat-calendar even when candidates[0] is generic span[contenteditable])
            _DP_MARKERS = ("mat-datepicker-toggle", "mat-calendar", "cdk-overlay")
            has_dp_marker_sel = any(m in sel for m in _DP_MARKERS)
            has_dp_marker_path = any(m in css_path for m in _DP_MARKERS)
            if not has_dp_marker_sel and not has_dp_marker_path:
                i += 1
                continue

            # Scan forward for the fill step that closes the sequence
            seq_start = i
            seq_end = i
            found_fill = -1
            j = i + 1
            while j < len(steps) and j < i + 15:
                s = steps[j]
                s_sel = s.target.candidates[0].selector if s.target and s.target.candidates else ""
                if s.action == "fill" and s.target and (s.target.tag or "").lower() in ("input", "textarea"):
                    # Fill closes the datepicker sequence
                    found_fill = j
                    seq_end = j - 1
                    break
                if s.action == "navigation":
                    break
                j += 1

            if found_fill > seq_start:
                # Mark all calendar steps as skipped
                for k in range(seq_start, seq_end + 1):
                    if not steps[k].skip_reason:
                        steps[k].skip_reason = "datepicker_dedup"
                i = found_fill + 1
            else:
                i += 1

    def _audit_blind_spots(self, stc) -> None:
        """Detect patterns where user intent was likely missed by the recorder.

        Blind spots are systematic, not random. After Phase B reconstruction,
        fields resolved via evidence (setter_hook, snapshot_diff, etc.) are
        excluded from the report.
        """
        steps = stc.steps
        blind_spots = []
        resolved_keys = {
            k for k, v in (stc.field_values or {}).items()
            if v.value and v.source != "missing_fill"
        }
        from datetime import datetime

        actionable = [(i, s) for i, s in enumerate(steps)
                      if s.action != "navigation" and not s.skip_reason]

        for ai in range(len(actionable) - 1):
            i_curr, s_curr = actionable[ai]
            i_next, s_next = actionable[ai + 1]
            gap_s = 0
            try:
                t1_str = s_curr.context.get("timestamp", "")
                t2_str = s_next.context.get("timestamp", "")
                if t1_str and t2_str:
                    t1 = datetime.fromisoformat(t1_str.replace("Z", "+00:00"))
                    t2 = datetime.fromisoformat(t2_str.replace("Z", "+00:00"))
                    gap_s = (t2 - t1).total_seconds()
            except ValueError:
                pass

            tag = (s_curr.target.tag or "").lower() if s_curr.target else ""
            ctx = getattr(s_curr, "context", {}) or {}

            # Skip if evidence reconstruction already resolved this step
            if ctx.get("_has_reconstructed_values") or (s_curr.value or "").strip():
                continue
            field_key = self._canonical_field_key(
                ctx.get("fill_label")
                or (s_curr.target.accessible_name if s_curr.target else "")
                or (s_curr.target.label if s_curr.target else "")
                or (s_curr.target.placeholder if s_curr.target else "")
                or (s_curr.target.text if s_curr.target else "")
            )
            if field_key in resolved_keys:
                continue

            # Pattern: click on input with gap, no fill event between
            if s_curr.action == "click" and tag in ("input", "textarea"):
                if s_next.action != "fill" and gap_s > 2.0:
                    label = (s_curr.target.accessible_name
                             or s_curr.target.label
                             or s_curr.target.placeholder or "")
                    blind_spots.append({
                        "step": i_curr + 1,
                        "pattern": "typing_not_captured",
                        "element": tag,
                        "label": label,
                        "gap_seconds": round(gap_s, 1),
                        "resolution": "data-file or submit_form_values",
                    })

            # Pattern: click on label (radio/checkbox) without reconstructed value
            if s_curr.action == "click" and tag == "label":
                label_text = (s_curr.target.text or s_curr.target.label or "").strip()
                if label_text and self._canonical_field_key(label_text) not in resolved_keys:
                    if s_next.action != "fill" and gap_s > 2.0:
                        blind_spots.append({
                            "step": i_curr + 1,
                            "pattern": "typing_not_captured",
                            "element": "label",
                            "label": label_text,
                            "gap_seconds": round(gap_s, 1),
                            "resolution": "checked_transition or data-file",
                        })

            # Pattern: click on select, no select_option event
            if s_curr.action == "click" and tag == "select":
                if s_next.action != "select_option":
                    blind_spots.append({
                        "step": i_curr + 1,
                        "pattern": "select_not_captured",
                        "resolution": "data-file",
                    })

            # Pattern: long gap between any two clicks (likely complex interaction)
            if gap_s > 10.0:
                blind_spots.append({
                    "step": i_curr + 1,
                    "pattern": "long_gap",
                    "gap_seconds": round(gap_s, 1),
                    "resolution": "review manually",
                })

            # GT-01: Shadow DOM closed mode — custom element (tag with hyphen)
            # is a potential shadow host. The recorder captures clicks on the host
            # but fill events inside closed shadow root are invisible.
            if s_curr.action in ("click", "fill") and tag and "-" in tag:
                # Custom element names contain at least one hyphen per HTML spec.
                # If there's no fill event following this step, the internal
                # field might be inside closed shadow DOM.
                if s_next.action != "fill" and gap_s > 1.0:
                    blind_spots.append({
                        "step": i_curr + 1,
                        "pattern": "shadow_dom_closed",
                        "element": tag,
                        "label": (s_curr.target.accessible_name
                                  or s_curr.target.label
                                  or s_curr.target.text or ""),
                        "gap_seconds": round(gap_s, 1),
                        "resolution": "shadow-root agent or data-file",
                    })

            # GT-02: Iframe element click — recorder cannot inject JS inside
            # cross-origin iframes. Events inside are invisible.
            if s_curr.action == "click" and tag == "iframe":
                blind_spots.append({
                    "step": i_curr + 1,
                    "pattern": "iframe_cross_origin",
                    "element": "iframe",
                    "label": s_curr.target.text or s_curr.target.name or "",
                    "resolution": "manual curation in steps.jsonl or same-origin required",
                })

        # GT-01 (cont.): Also scan all steps for custom elements with fill actions
        # that might indicate shadow DOM field interaction
        for i, step in enumerate(steps):
            if step.skip_reason:
                continue
            tag = (step.target.tag or "").lower() if step.target else ""
            if tag and "-" in tag and step.action == "fill":
                # Custom element being filled — check if value was captured
                if not (step.value or "").strip():
                    ctx = getattr(step, "context", {}) or {}
                    if not ctx.get("_has_reconstructed_values"):
                        blind_spots.append({
                            "step": i + 1,
                            "pattern": "shadow_dom_fill_missed",
                            "element": tag,
                            "label": (step.target.accessible_name
                                      or step.target.label
                                      or step.target.text or ""),
                            "resolution": "final_state or data-file",
                        })

        stc.blind_spots = blind_spots
        if blind_spots:
            import sys
            print(f"[TestForge] ⚠ {len(blind_spots)} blind spot(s) detectado(s):", file=sys.stderr)
            for bs in blind_spots:
                print(f"  Step {bs['step']}: {bs['pattern']} ({bs.get('label', bs.get('gap_seconds', ''))}) → {bs['resolution']}", file=sys.stderr)

    def _reconstruct_intents(self, stc, recording_dir: str) -> None:
        """Run IntentReconstructor to synthesize fill steps and field values.

        Phase B: reconstructs from value_mutations, snapshots (incl. checked),
        form_values, network_payload, and final_state_snapshot.
        """
        from .intent_reconstructor import IntentReconstructor

        reconstructor = IntentReconstructor()
        entries = reconstructor.reconstruct_all(recording_dir, stc.steps)

        for entry in entries:
            source = entry.get("source", "")
            value = entry.get("value", "")
            field_key = entry.get("field_key", "")
            step_idx = entry.get("step_index", 0)
            intention = entry.get("intention", "")
            identifiers = entry.get("identifiers", {})

            target_indices = {step_idx}
            # Also match label/radio clicks by text similarity
            entry_label = (identifiers.get("label") or value or "").strip().lower()
            for i, step in enumerate(stc.steps):
                if step.action != "click" or not step.target:
                    continue
                step_text = (step.target.text or step.target.label or "").strip().lower()
                if entry_label and step_text and (
                    entry_label in step_text or step_text in entry_label
                ):
                    target_indices.add(i)

            for idx in target_indices:
                if not (0 <= idx < len(stc.steps)):
                    continue
                step = stc.steps[idx]
                ctx = getattr(step, "context", {}) or {}
                if "_reconstructed_values" not in ctx:
                    ctx["_reconstructed_values"] = []
                ctx["_reconstructed_values"].append({
                    "field_key": field_key,
                    "value": value,
                    "source": source,
                    "intention": intention,
                    "identifiers": identifiers,
                })
                ctx["_has_reconstructed_values"] = True
                step.context = ctx

                tag = (step.target.tag or "").lower() if step.target else ""
                if step.action in ("click",) and tag in ("input", "textarea", "select", "label"):
                    step.value = value
                    step.context["reconstructed_source"] = source
                    step.context.pop("missing_fill", None)

        if entries:
            import sys
            sources = {}
            for e in entries:
                src = e.get("source", "unknown")
                sources[src] = sources.get(src, 0) + 1
            src_desc = ", ".join(f"{k}={v}" for k, v in sources.items())
            print(f"[TestForge] 🔄 IntentReconstructor: {len(entries)} campo(s) reconstituido(s) ({src_desc})", file=sys.stderr)

    def _build_field_value_map(self, stc) -> None:
        """Build field_value_map linking field identifiers, values, and intentions.

        Each step that involves a form field (input/textarea/select) contributes
        to the map. Sources in priority:
        1. form_values: captured at submit time (most reliable)
        2. fill events: recorded values (polling or native input)
        3. missing_fill: detected gap, value from form_values or empty (needs data_file)

        The map is stored in stc.field_values: canonical_key → FieldValueMap.
        """
        from .model import FieldValueMap

        # First pass: collect fill events with their identifiers
        fill_registry = {}  # canonical_key -> {identifiers, value, step_index}
        for i, step in enumerate(stc.steps):
            if step.action not in ("fill", "click"):
                continue
            if step.action == "click":
                tag = (step.target.tag or "").lower() if step.target else ""
                if tag not in ("input", "textarea"):
                    continue
                # Check if this click has form_values (propagated from submit)
                ctx = getattr(step, "context", {}) or {}
                if ctx.get("form_values"):
                    # Convert form_values into FieldValueMap entries
                    for fname, fval in ctx["form_values"].items():
                        canonical = self._canonical_field_key(fname)
                        # Build identifiers from the step target
                        ids = {}
                        if step.target:
                            if step.target.name: ids["name"] = step.target.name
                            if step.target.accessible_name: ids["aria_label"] = step.target.accessible_name
                            if step.target.placeholder: ids["placeholder"] = step.target.placeholder
                            if step.target.element_id: ids["id"] = step.target.element_id
                            if step.target.label: ids["label"] = step.target.label
                        # Include the form_values key itself
                        ids.setdefault("form_name", fname)
                        intention = self._build_fill_intention(step, fname, fval, i)
                        if canonical not in fill_registry:
                            fill_registry[canonical] = {
                                "value": fval,
                                "intention": intention,
                                "identifiers": ids,
                                "source": "form_values",
                                "step_index": i,
                            }
                        elif fill_registry[canonical]["source"] != "form_values":
                            # Prefer form_values over other sources
                            fill_registry[canonical] = {
                                "value": fval,
                                "intention": intention,
                                "identifiers": ids,
                                "source": "form_values",
                                "step_index": i,
                            }
                    continue

                # Check missing_fill
                if ctx.get("missing_fill"):
                    fill_label = ctx.get("fill_label", "") or ""
                    canonical = self._canonical_field_key(fill_label)
                    if canonical not in fill_registry:
                        ids = {}
                        if step.target:
                            if step.target.name: ids["name"] = step.target.name
                            if step.target.accessible_name: ids["aria_label"] = step.target.accessible_name
                            if step.target.placeholder: ids["placeholder"] = step.target.placeholder
                            if step.target.element_id: ids["id"] = step.target.element_id
                            if step.target.label: ids["label"] = step.target.label
                        fill_registry[canonical] = {
                            "value": "",
                            "intention": self._build_fill_intention(step, fill_label, "", i),
                            "identifiers": ids,
                            "source": "missing_fill",
                            "step_index": i,
                        }
                    continue

            # Recorded fill events
            if step.action == "fill" and step.target:
                val = (step.value or "").strip()
                if not val:
                    continue
                # Build identifiers from target
                ids = {}
                if step.target.name: ids["name"] = step.target.name
                if step.target.accessible_name: ids["aria_label"] = step.target.accessible_name
                if step.target.placeholder: ids["placeholder"] = step.target.placeholder
                if step.target.element_id: ids["id"] = step.target.element_id
                if step.target.label: ids["label"] = step.target.label
                if step.target.text: ids["text"] = step.target.text

                # Determine canonical key from best identifier
                canonical = (
                    step.target.name
                    or step.target.accessible_name
                    or step.target.placeholder
                    or step.target.element_id
                    or step.target.label
                    or f"step_{i+1}"
                )
                canonical = self._canonical_field_key(canonical)
                intention = self._build_fill_intention(step, canonical, val, i)
                if canonical not in fill_registry:
                    fill_registry[canonical] = {
                        "value": val,
                        "intention": intention,
                        "identifiers": ids,
                        "source": "fill_event",
                        "step_index": i,
                    }
                else:
                    # Update value if we only had missing_fill placeholder
                    existing = fill_registry[canonical]
                    if existing["source"] == "missing_fill" or not existing["value"]:
                        existing["value"] = val
                        existing["source"] = "fill_event"
                        existing["step_index"] = i

        # Also check if form_values were captured outside input click context
        # (some submit events carry form_values without preceding input clicks)
        for i, step in enumerate(stc.steps):
            ctx = getattr(step, "context", {}) or {}
            form_vals = ctx.get("form_values") or {}
            if not form_vals:
                continue
            for fname, fval in form_vals.items():
                canonical = self._canonical_field_key(fname)
                if canonical not in fill_registry:
                    fill_registry[canonical] = {
                        "value": fval,
                        "intention": f"fill field '{fname}'",
                        "identifiers": {"form_name": fname},
                        "source": "form_values",
                        "step_index": i,
                    }

        # Sprint 4: incorporate reconstructed values (snapshot_diff, network_payload)
        # These come from _reconstruct_intents() stored in step.context["_reconstructed_values"]
        for i, step in enumerate(stc.steps):
            ctx = getattr(step, "context", {}) or {}
            rec_vals = ctx.get("_reconstructed_values") or []
            if not rec_vals:
                continue
            for rv in rec_vals:
                canonical = self._canonical_field_key(rv.get("field_key", ""))
                source = rv.get("source", "unknown")
                value = rv.get("value", "")
                intention = rv.get("intention", "")
                identifiers = rv.get("identifiers", {})
                if canonical and value:
                    if canonical not in fill_registry:
                        fill_registry[canonical] = {
                            "value": value,
                            "intention": intention,
                            "identifiers": identifiers,
                            "source": source,
                            "step_index": i,
                        }
                    else:
                        existing = fill_registry[canonical]
                        # Only replace if existing is lower priority or empty
                        _source_priority = {
                            "form_values": 100, "fill_event": 80, "setter_hook": 78,
                            "checked_transition": 72, "snapshot_diff": 70,
                            "network_payload": 60, "final_state": 55,
                            "polling": 50, "missing_fill": 10,
                        }
                        existing_priority = _source_priority.get(existing["source"], 0)
                        new_priority = _source_priority.get(source, 0)
                        if new_priority > existing_priority or not existing["value"]:
                            existing["value"] = value
                            existing["intention"] = intention
                            existing["identifiers"] = identifiers
                            existing["source"] = source
                            existing["step_index"] = i

        # Secondary dedup: same physical field with different canonical keys (by element_id).
        # fill_event keys by placeholder, setter_hook keys by element_id — same element, two entries.
        _source_priority_map = {
            "form_values": 100, "fill_event": 80, "setter_hook": 78,
            "checked_transition": 72, "snapshot_diff": 70,
            "network_payload": 60, "final_state": 55,
            "polling": 50, "missing_fill": 10,
        }
        el_id_to_key: dict[str, str] = {}
        keys_to_drop: set = set()
        for canonical, entry in fill_registry.items():
            el_id = (entry.get("identifiers") or {}).get("id", "").strip()
            if not el_id:
                continue
            existing_canonical = el_id_to_key.get(el_id)
            if existing_canonical is None:
                el_id_to_key[el_id] = canonical
            else:
                existing_entry = fill_registry[existing_canonical]
                old_p = _source_priority_map.get(existing_entry["source"], 0)
                new_p = _source_priority_map.get(entry["source"], 0)
                if new_p > old_p or (new_p == old_p and len(entry.get("value", "")) > len(existing_entry.get("value", ""))):
                    keys_to_drop.add(existing_canonical)
                    el_id_to_key[el_id] = canonical
                else:
                    keys_to_drop.add(canonical)
        for k in keys_to_drop:
            fill_registry.pop(k, None)

        # Convert to FieldValueMap and store in stc
        stc.field_values = {}
        for key, entry in fill_registry.items():
            if entry["value"] or entry["source"] == "missing_fill":
                stc.field_values[key] = FieldValueMap(
                    field_key=key,
                    value=entry["value"],
                    intention=entry["intention"],
                    identifiers=entry["identifiers"],
                    source=entry["source"],
                    step_index=entry["step_index"],
                )

        # Report
        if stc.field_values:
            import sys
            source_icons = {
                "form_values": "✓", "fill_event": "○", "missing_fill": "⚠",
                "setter_hook": "⚡", "checked_transition": "◈",
                "snapshot_diff": "◉", "network_payload": "◎", "final_state": "◇",
            }
            print(f"[TestForge] 📋 {len(stc.field_values)} campo(s) mapeado(s):", file=sys.stderr)
            for key, fvm in stc.field_values.items():
                icon = source_icons.get(fvm.source, "?")
                val_display = fvm.value if fvm.value else "<pendente>"
                print(f"  {icon} {key}: {val_display} ({fvm.source})", file=sys.stderr)
            missing = [k for k, v in stc.field_values.items() if not v.value]
            if missing:
                print(f"  💡 {len(missing)} campo(s) sem valor — usar --data data.json", file=sys.stderr)

    @staticmethod
    def _canonical_field_key(key: str) -> str:
        """Normalize field identifier to canonical key for matching."""
        if not key:
            return "unknown"
        k = key.strip().lower()
        # Remove common prefixes/suffixes
        k = _re.sub(r'^(input|field|txt|inp)[-_]?', '', k)
        k = _re.sub(r'[-_\s]+', '_', k)
        return k.strip('_')

    @staticmethod
    def _build_fill_intention(step, field_key: str, value: str, step_index: int) -> str:
        """Build human-readable intention string for a field fill action."""
        tag = (step.target.tag or "").lower() if step.target else ""
        label = (
            (step.target.accessible_name or "")
            or (step.target.label or "")
            or (step.target.placeholder or "")
            or field_key
        )
        parts = [f"fill {label}"]
        if value:
            parts.append(f"with '{value}'")
        if tag:
            parts.append(f"on {tag}")
        parts.append(f"step {step_index + 1}")
        return " ".join(parts)

    def _compact_fill_events(self, raw_events: list) -> list:
        """Compact sequential fill events on same element.

        When user types into a field, the recorder captures each keystroke as a
        separate fill/keypress event. Consecutive events on the same target
        are collapsed — only the final event (which holds the complete typed
        value) is kept.

        Note: time-based grouping (500ms window) was REMOVED because slow
        typists produce keystroke gaps exceeding 500ms. Using the same-target
        heuristic is safer: if the next event targets the same element, it's
        part of the same typing sequence, regardless of time gap.
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
            group_end = i

            j = i + 1
            while j < len(raw_events):
                next_event = raw_events[j]
                next_type = next_event.get("type", "")

                if next_type not in FILL_TYPES:
                    break

                next_key = _target_key(next_event.get("target"))

                if next_key != current_key:
                    break

                group_end = j
                j += 1

            # Keep only the final event (holds the complete typed value)
            compacted.append(raw_events[group_end])
            i = j

        return compacted

    def _remove_snapshot_duplicates(self, raw_events: list) -> list:
        """Remove periodic DOM snapshot fill events (duplicate cycles).

        The recorder captures periodic snapshots of ALL visible form fields.
        These produce duplicate fill events for the same element with the
        same value, cycling through fields in a predictable pattern.
        Keep only the first occurrence of each (element, value) pair.

        Field re-fills with different values (e.g. currency: 10000 → 100000)
        are preserved because the value differs. Only true duplicates
        (same element, same value) are removed.
        """
        if not raw_events:
            return raw_events

        FILL_TYPES = {"fill", "keypress"}
        seen: set = set()
        result: list = []

        for event in raw_events:
            event_type = event.get("type", "")
            target = event.get("target") or {}

            if event_type in FILL_TYPES:
                key = (
                    target.get("id", ""),
                    target.get("name", ""),
                    event.get("value", "") or "",
                )
                if key in seen:
                    continue
                seen.add(key)

            result.append(event)

        return result

    def _convert_event(self, raw: dict) -> Optional[SemanticAction]:
        event_type = raw.get("type", "")
        target_data = raw.get("target") or {}

        # Normalize target_data field names from recorder format to
        # _build_target() expected format.
        # Recorder stores element_id + attributes dict; _build_target
        # expects flat fields: id, name, placeholder, label, etc.
        if target_data:
            if "element_id" in target_data and "id" not in target_data:
                target_data["id"] = target_data["element_id"]
            attrs = target_data.get("attributes") or {}
            all_attrs = target_data.get("all_attributes") or {}
            for flat_key in ("name", "placeholder", "type"):
                if flat_key not in target_data:
                    val = attrs.get(flat_key) or all_attrs.get(flat_key) or ""
                    if val:
                        target_data[flat_key] = val

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

        # Skip click events with no target candidates — recording artifacts
        # (clicks outside any recognizable element, e.g. background/whitespace).
        if event_type == "click" and not target.candidates:
            return None

        # Radio and checkbox inputs: Playwright fill() does not support
        # these element types. Convert to click action — the target
        # selector (label:has-text or name-based) will find the element
        # and clicking the label propagates to the native radio/checkbox.
        attrs = target_data.get("attributes") or {}
        if event_type == "fill" and attrs.get("type") in ("radio", "checkbox"):
            event_type = "click"

        action_map = {
            "click": "click",
            "fill": "fill",
            "keypress": "fill",
            "contenteditable": "fill",  # contenteditable div changes mapped to fill
            "submit": "click",  # submit is a click on a submit button
        }
        action = action_map.get(event_type)
        if not action:
            return None

        is_submit = event_type == "submit"
        context = {}
        if raw.get("timestamp"):
            context["timestamp"] = raw["timestamp"]
        if is_submit:
            context["is_submit"] = True
            if raw.get("submit_method"):
                context["submit_method"] = raw["submit_method"]
            if raw.get("postback_url"):
                context["postback_url"] = raw["postback_url"]
            if raw.get("is_postback"):
                context["is_postback"] = True
            # Carry form field values captured at submit time
            if raw.get("form_values"):
                context["form_values"] = raw["form_values"]
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
                value=_clean_text(step.get("expected_value", ""), max_len=200),
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
            if el_id.startswith("mat-radio-"):
                candidates.insert(0, LocatorCandidate(
                    "angular_material", f"mat-radio-button:has-text(\"{label}\")",
                    0.92, f"Angular Material radio by label={label}",
                ))
                candidates.append(LocatorCandidate("label", f"label[for=\"{el_id}\"]", 0.30, f"label for={el_id} (mat-radio degraded)"))
            else:
                candidates.append(LocatorCandidate("label", f"label[for=\"{el_id}\"]", 0.90, f"label for={el_id}"))
        elif target_data.get("label"):
            label = target_data["label"]
            # Adjacent sibling: <label>Text</label> + <input> (most HTML forms)
            candidates.append(LocatorCandidate("label", f"label:has-text(\"{label}\") + input", 0.85, f"label adjacent={label}"))
            # JUST the label element itself — clicking label fires native input events.
            # Catches Material Design where input is nested INSIDE the label:
            #   <label>Text <input type="radio"></label>
            # Also catches cases where label click propagates correctly.
            candidates.append(LocatorCandidate("label", f"label:has-text(\"{label}\")", 0.80, f"label click={label}"))

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

        if target_data.get("id") and target_data["id"] not in ("mat-input-0", "mat-input-1"):
            el_id = target_data["id"]
            # Angular Material auto-generated IDs are fragile — deprioritize them
            id_score = 0.15 if _ANGULAR_AUTOID_RE.match(el_id) else 0.75
            candidates.append(LocatorCandidate("id", f"#{el_id}", id_score, f"id={el_id}"))

        if target_data.get("name"):
            name = target_data["name"]
            candidates.append(LocatorCandidate("name", f"[name=\"{name}\"]", 0.70, f"name={name}"))

        if target_data.get("text"):
            text = _clean_text(target_data["text"])
            if text:
                # Penalize generic text like "OK", "Cancelar", "Selecione" — brittle locators
                text_score = 0.10 if _is_generic_text(text) else 0.55
                # Length penalty: long has-text() is fragile (truncated text, partial matches)
                # 0-20 chars: 0, 20-40: -0.05, 40-60: -0.10
                if len(text) > 40:
                    text_score -= 0.10
                elif len(text) > 20:
                    text_score -= 0.05
                # Always include tag when available — bare :has-text() clicks on child elements
                # instead of the link/button itself, breaking SPA navigation.
                # When element has an interactive role, add role constraint: parent containers
                # also have-text the same string, so div:has-text() matches them and clicks
                # the wrong sibling (e.g. center card of 3). div[role="button"]:has-text()
                # is unambiguous because containers do not carry role="button".
                tag = (target_data.get("tag") or "").lower()
                elem_role = (target_data.get("role") or "").lower()
                _interactive_roles = {"button", "listitem", "option", "menuitem", "tab", "radio", "checkbox", "link", "menuitemcheckbox", "menuitemradio"}
                if tag and elem_role and elem_role in _interactive_roles:
                    candidates.append(LocatorCandidate("text", f'{tag}[role="{elem_role}"]:has-text("{text}")', text_score + 0.10, f"role+text in {tag}[role={elem_role}]"))
                elif tag:
                    candidates.append(LocatorCandidate("text", f"{tag}:has-text(\"{text}\")", text_score, f"text in {tag}"))
                else:
                    candidates.append(LocatorCandidate("text", f":has-text(\"{text}\")", text_score, "visible text"))
        elif target_data.get("inner_html"):
            # Fallback: use inner HTML as text source (for elements like datepicker spans)
            inner = _clean_text(target_data["inner_html"])
            if inner:
                tag = (target_data.get("tag") or "").lower()
                # Skip SVG elements — their "inner text" is path/geometry data,
                # not meaningful text content. SVG icons are decorative.
                # Without this filter, <svg><polygon points="0,0 5,5..."></svg>
                # generates svg:has-text("<polygon points=...">") which never matches.
                if tag in ("svg", "path", "polygon", "circle", "line", "g"):
                    pass  # fall through to CSS path / class fallbacks
                else:
                    sel = f"{tag}:has-text(\"{inner}\")" if tag else f":has-text(\"{inner}\")"
                    candidates.append(LocatorCandidate("inner_html", sel, 0.45, "inner HTML text"))

        # -- Contenteditable detection (GT-08) --
        # When the element has contenteditable=true and no stable locator was found,
        # generate a direct attribute selector. Playwright supports fill() on [contenteditable].
        _contenteditable_attrs = (
            (target_data.get("attributes") or {}).get("contenteditable", "") or
            (target_data.get("all_attributes") or {}).get("contenteditable", "")
        )
        if _contenteditable_attrs in ("true", "") and tag:
            contenteditable_sel = f'{tag}[contenteditable="{_contenteditable_attrs}"]'
            candidates.append(LocatorCandidate("contenteditable", contenteditable_sel, 0.50, "contenteditable element"))
            # Also add text-based variant if text is available for disambiguation
            ce_text = _clean_text(target_data.get("text") or target_data.get("accessible_name") or "")
            if ce_text and len(ce_text) <= 40 and not _is_generic_text(ce_text):
                candidates.append(LocatorCandidate(
                    "contenteditable", f'{tag}[contenteditable="{_contenteditable_attrs}"]:has-text("{ce_text}")',
                    0.60, f"contenteditable with text: {ce_text}"
                ))

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

            # -- Select2 / combobox heuristic (GT-07) --
            # Select2 plugin renders a div.select2-selection[role="combobox"].
            # The native <select> is hidden (display:none) and value is set via JS.
            # Generate a reliable selector for the combobox div.
            if tag == "div" and "select2-selection" in css_path:
                # aria-label on the combobox
                aria_label = target_data.get("aria_attrs", {}).get("aria-label", "")
                if aria_label:
                    candidates.append(LocatorCandidate(
                        "select2", f'div[role="combobox"][aria-label="{aria_label}"]',
                        0.60, f"Select2 combobox by aria-label: {aria_label}"
                    ))
                # Text-based fallback
                ce_text = _clean_text(target_data.get("text", ""))[:40]
                if ce_text and not _is_generic_text(ce_text):
                    candidates.append(LocatorCandidate(
                        "select2", f'div.select2-selection:has-text("{ce_text}")',
                        0.55, f"Select2 combobox by text: {ce_text}"
                    ))

        # Fallback: XPath (lowest priority)
        xpath = target_data.get("xpath") or ""
        if xpath and not candidates:
            candidates.append(LocatorCandidate("xpath", xpath, 0.10, "XPath fallback"))

        # nth-child for disambiguation — always add when available so healing
        # can use positional fallback for sibling buttons/tabs with similar text
        nth = target_data.get("nth_child") or 0
        tag = target_data.get("tag") or ""
        if nth > 0 and tag:
            candidates.append(LocatorCandidate("nth_child", f"{tag}:nth-child({nth})", 0.35, "nth-child position"))

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

        # aria-label como seletor para input/textarea quando role nao disponivel.
        # Role-based selector (acima) é preferivel mas exige target_data["role"].
        # Sem role, o aria-label nunca vira seletor (excluido do loop acima).
        if not target_data.get("role"):
            aria_label = (aria_attrs.get("aria-label", "") or
                         (target_data.get("all_attributes") or {}).get("aria-label", "") or
                         target_data.get("accessible_name", "") or "")
            if aria_label and len(aria_label) < 60:
                tag = (target_data.get("tag") or "").lower()
                if tag in ("input", "textarea"):
                    sel = f'{tag}[aria-label="{aria_label}"]'
                    candidates.append(LocatorCandidate("aria_label", sel, 0.85, f"{tag} aria-label={aria_label}"))

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

    def _detect_missing_fills(self, steps: list) -> None:
        """Detect clicks on inputs lacking fill events (currency-masked fields).

        Phase B: runs AFTER _reconstruct_intents. Skips steps already resolved
        by evidence (setter_hook, snapshot_diff, checked_transition, etc.).
        """
        from datetime import datetime

        # First: propagate form_values from submit events to preceding input clicks
        for i, step in enumerate(steps):
            ctx = getattr(step, "context", {}) or {}
            form_vals = ctx.get("form_values") or {}
            if form_vals:
                for j in range(i - 1, -1, -1):
                    prev = steps[j]
                    prev_tag = (prev.target.tag or "").lower() if prev.target else ""
                    if prev_tag in ("input", "textarea") and prev.action == "click":
                        prev_ctx = getattr(prev, "context", {})
                        prev_ctx["form_values"] = form_vals
                        prev.context = prev_ctx

        actionable = [(i, s) for i, s in enumerate(steps)
                      if s.action != "navigation" and not s.skip_reason]

        for ai in range(len(actionable) - 1):
            i_curr, s_curr = actionable[ai]
            i_next, s_next = actionable[ai + 1]

            if s_curr.action != "click":
                continue
            tag = (s_curr.target.tag or "").lower() if s_curr.target else ""
            if tag not in ("input", "textarea"):
                continue
            if s_next.action == "fill":
                continue

            ctx = getattr(s_curr, "context", {}) or {}
            if ctx.get("form_values"):
                continue
            if ctx.get("_has_reconstructed_values") or (s_curr.value or "").strip():
                continue

            t1_str = ctx.get("timestamp", "")
            t2_str = s_next.context.get("timestamp", "")
            if not t1_str or not t2_str:
                continue
            try:
                t1 = datetime.fromisoformat(t1_str.replace("Z", "+00:00"))
                t2 = datetime.fromisoformat(t2_str.replace("Z", "+00:00"))
                gap_s = (t2 - t1).total_seconds()
            except ValueError:
                continue

            if gap_s > 2.0:
                s_curr.context["missing_fill"] = True
                if s_curr.target:
                    s_curr.context["fill_label"] = (
                        s_curr.target.accessible_name
                        or s_curr.target.label
                        or s_curr.target.placeholder
                        or ""
                    )
