"""TestForge — Normalizador de Gravação.

Converte RawRecordedSession (JSONL) em SemanticTestCase (YAML).
Gera múltiplos candidatos de localizador ordenados por score determinístico.
"""
import json
import logging
import os
import re as _re
from datetime import datetime
from typing import Optional
from urllib.parse import urlparse, urlunparse

from .model import LocatorCandidate, SemanticAction, SemanticTarget, SemanticTestCase
from testforge.handlers import HANDLERS

logger = logging.getLogger(__name__)



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
    "check_circle", "check_circle_outline", "radio_button_checked", "radio_button_unchecked",
    "check_box", "check_box_outline_blank", "indeterminate_check_box",
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


def _attr_css_variants(attr_name: str, value: str, tag: str,
                       exact_score: float, reason: str) -> list:
    """Generate CSS attribute variant selectors for locator healing.

    Produces starts-with (^=), ends-with ($=), and contains (*=, case-insensitive)
    variants for a single attribute. These handle minor DOM changes between
    recording and execution: dynamic suffixes, case differences, partial updates.

    Only generates variants when value length is sufficient to avoid
    over-broad matching (min 4 chars for starts-with, 3 for ends-with, 5 for contains).
    Scores degrade progressively from exact_score.
    """
    variants = []
    if not value or len(value) < 3:
        return variants

    _CSS_ATTR_MAP = {
        "test_id": "data-testid",
        "aria_label": "aria-label",
    }
    css_attr = _CSS_ATTR_MAP.get(attr_name, attr_name)

    # Build selector prefix: tag[attr  or just [attr
    if attr_name == "test_id":
        sel_prefix = "[data-testid"
    elif tag and attr_name != "id":
        sel_prefix = f"{tag}[{css_attr}"
    elif attr_name == "id":
        sel_prefix = "[id"
    else:
        sel_prefix = f"[{css_attr}"

    v = value

    # starts-with: tag[attr^="value"]
    if len(v) >= 4:
        # Skip auto-generated angular/react id prefixes
        if attr_name == "id" and (v.startswith("mat-") or v.startswith("ng-")):
            pass
        elif attr_name == "test_id" and len(v) < 6:
            pass  # short test_ids already unique
        else:
            sel = f'{sel_prefix}^="{v}"]'
            score = max(0.20, round(exact_score - 0.15, 2))
            variants.append(LocatorCandidate(
                f"{attr_name}_starts", sel, score, f"{reason} (starts-with)"
            ))

    # ends-with: tag[attr$="value"]
    if len(v) >= 3:
        sel = f'{sel_prefix}$="{v}"]'
        score = max(0.20, round(exact_score - 0.20, 2))
        variants.append(LocatorCandidate(
            f"{attr_name}_ends", sel, score, f"{reason} (ends-with)"
        ))

    # contains (case-insensitive): tag[attr*="value" i]
    if len(v) >= 5:
        sel = f'{sel_prefix}*="{v}" i]'
        score = max(0.20, round(exact_score - 0.25, 2))
        variants.append(LocatorCandidate(
            f"{attr_name}_contains", sel, score, f"{reason} (contains)"
        ))

    return variants


def _compound_candidates(target_data: dict, tag: str) -> list:
    """Generate compound attribute selectors combining 2 attributes.

    Compound selectors (input[placeholder="X"][aria-label="Y"]) have higher
    specificity than single-attribute selectors. Score = min(score1, score2) + 0.05.

    Pairs generated when both attributes exist:
      - placeholder + aria_label  (most common form pattern)
      - placeholder + name
      - aria_label + name
    """
    variants = []
    ph = target_data.get("placeholder") or ""
    name_val = target_data.get("name") or ""

    # Resolve aria-label from multiple possible sources
    aria_label = (target_data.get("accessible_name") or ""
                  or (target_data.get("aria_attrs") or {}).get("aria-label", "")
                  or (target_data.get("all_attributes") or {}).get("aria-label", "")
                  or "")

    if not tag:
        tag = (target_data.get("tag") or "").lower()

    pairs = []
    if ph and aria_label and len(ph) >= 3 and len(aria_label) >= 3:
        pairs.append(("placeholder", ph, "aria-label", aria_label, 0.90))
    if ph and name_val and len(ph) >= 3 and len(name_val) >= 2:
        pairs.append(("placeholder", ph, "name", name_val, 0.75))
    if aria_label and name_val and len(aria_label) >= 3 and len(name_val) >= 2:
        pairs.append(("aria-label", aria_label, "name", name_val, 0.75))

    for attr1, val1, attr2, val2, score in pairs:
        # Build compound selector: tag[attr1="val1"][attr2="val2"]
        if tag:
            sel = f'{tag}[{attr1}="{val1}"][{attr2}="{val2}"]'
        else:
            sel = f'[{attr1}="{val1}"][{attr2}="{val2}"]'
        reason = f"compound {attr1}={val1} + {attr2}={val2}"
        variants.append(LocatorCandidate("compound", sel, score, reason))

    return variants


class RecordingNormalizer:
    """Converte raw events em SemanticTestCase.

    Phase 2: optional `use_v2_locator` flag enables the modern
    super-selector extractor (`semantic.locator.LocatorExtractor`)
    in parallel with the legacy `_build_target` heuristics. When on,
    v2 candidates are appended after legacy candidates; downstream
    code that ignores the new fields keeps working unchanged.
    """

    def __init__(self, use_v2_locator: bool = False) -> None:
        self._use_v2 = bool(use_v2_locator)
        self._v2_extractor = None
        if self._use_v2:
            from .locator import LocatorExtractor
            self._v2_extractor = LocatorExtractor()

    def normalize(self, recording_dir: str, test_id: str = "",
                  application: str = "", base_url: str = "") -> SemanticTestCase:
        events_path = os.path.join(recording_dir, "raw_events.jsonl")
        if not os.path.exists(events_path):
            raise FileNotFoundError(f"raw_events.jsonl nao encontrado em {recording_dir}")

        with open(events_path) as f:
            raw_events = [json.loads(line) for line in f if line.strip()]

        logger.info("Normalizing recording_dir=%s raw_events=%d",
                     os.path.basename(recording_dir), len(raw_events))
        # Log per-type breakdown before dedup
        type_counts = {}
        for ev in raw_events:
            et = ev.get("type", "unknown")
            type_counts[et] = type_counts.get(et, 0) + 1
        logger.debug("Raw event types: %s", type_counts)

        # Run dedup BEFORE compaction: removes periodic DOM snapshot cycles
        # (e.g. radio button spam) so consecutive fills on the same field
        # become adjacent and get properly collapsed.
        pre_dedup = len(raw_events)
        raw_events = self._remove_snapshot_duplicates(raw_events)
        after_dedup = len(raw_events)
        logger.debug("After _remove_snapshot_duplicates: %d → %d (-%d)",
                      pre_dedup, after_dedup, pre_dedup - after_dedup)
        # Collapse individual-key keypress sequences before fill compaction.
        # mat-autocomplete may emit one keypress per character instead of
        # accumulated fill events — rebuild the full typed string first.
        raw_events = self._compact_keypress_sequences(raw_events)
        raw_events = self._compact_fill_events(raw_events)
        after_compact = len(raw_events)
        logger.info("After compaction: %d events (reduced %d%%)",
                     after_compact,
                     int((1 - after_compact / max(pre_dedup, 1)) * 100))

        recording_id = os.path.basename(recording_dir)
        stc = SemanticTestCase(
            test_id=test_id or f"ST-{recording_id}",
            source_recording_id=recording_id,
            application=application,
            base_url=base_url,
        )

        converted = 0
        for raw in raw_events:
            try:
                action = self._convert_event(raw)
                if action:
                    stc.steps.append(action)
                    converted += 1
            except Exception as exc:
                logger.error("Failed to convert event id=%s: %s",
                              raw.get("event_id", "?"), exc, exc_info=True)

        logger.debug("Converted %d/%d raw events to semantic actions", converted, after_compact)

        # Carrega steps (asserts) se existirem
        steps_path = os.path.join(recording_dir, "steps.jsonl")
        if os.path.exists(steps_path):
            with open(steps_path) as f:
                steps_count = 0
                for line in f:
                    step = json.loads(line)
                    stc.steps.append(self._convert_step(step))
                    steps_count += 1
                logger.debug("Loaded %d steps (asserts) from steps.jsonl", steps_count)

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
        # Phase B semantic dedup: component handlers + prefill clicks
        for handler in HANDLERS:
            handler.normalize(stc.steps)
        self._eliminate_prefill_clicks(stc.steps)
        self._audit_blind_spots(stc)

        # Log final step breakdown
        action_types = {}
        skipped = 0
        for s in stc.steps:
            action_types[s.action] = action_types.get(s.action, 0) + 1
            if s.skip_reason:
                skipped += 1
        logger.info("Normalization complete: %d steps actions=%s skipped=%d",
                     len(stc.steps), action_types, skipped)
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
            if nxt is None or nxt.action not in ("fill", "select_option"):
                continue
            curr_tag = (curr.target.tag or "").lower() if curr.target else ""
            if nxt.action == "select_option" and curr_tag != "select":
                continue
            if nxt.action == "fill" and curr_tag not in ("input", "textarea"):
                continue
            # Same element: prefer element_id, then accessible_name, then selector.
            # Selector alone is ambiguous when two distinct fields share the same
            # placeholder (e.g. two "R$0,00" inputs on one form).
            curr_id = (curr.target.element_id or "") if curr.target else ""
            nxt_id = (nxt.target.element_id or "") if nxt.target else ""
            curr_name = (curr.target.accessible_name or "") if curr.target else ""
            nxt_name = (nxt.target.accessible_name or "") if nxt.target else ""
            curr_sel = curr.target.candidates[0].selector if curr.target and curr.target.candidates else ""
            nxt_sel = nxt.target.candidates[0].selector if nxt.target and nxt.target.candidates else ""
            if curr_id and nxt_id:
                same = curr_id == nxt_id
            elif curr_name and nxt_name:
                same = curr_name == nxt_name
            else:
                same = bool(curr_sel) and curr_sel == nxt_sel
            if same:
                curr.skip_reason = "prefill_click_noise"

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
            print(f"[TestForge] [WARN] {len(blind_spots)} blind spot(s) detectado(s):", file=sys.stderr)
            for bs in blind_spots:
                print(f"  Step {bs['step']}: {bs['pattern']} ({bs.get('label', bs.get('gap_seconds', ''))}) → {bs['resolution']}", file=sys.stderr)

    def _reconstruct_intents(self, stc, recording_dir: str) -> None:
        """Reconstruct fill intents from evidence sources (inline IntentReconstructor).

        Sources: value_mutations, snapshots, form_values, network, final_state, polling.
        """
        entries = self._ir_all(recording_dir, stc.steps)

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
        # Track loser→winner pairs so we can merge identifiers after deciding
        merge_pairs: list[tuple[str, str]] = []  # (loser_key, winner_key)
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
                    merge_pairs.append((existing_canonical, canonical))
                    el_id_to_key[el_id] = canonical
                else:
                    keys_to_drop.add(canonical)
                    merge_pairs.append((canonical, existing_canonical))
        # Merge identifiers from dropped entries into their winners so that
        # _resolve_field_value can still find fields by aria_label/label/placeholder
        # even when the winner only has element_id in its identifiers.
        for loser_key, winner_key in merge_pairs:
            loser = fill_registry.get(loser_key) or {}
            winner = fill_registry.get(winner_key)
            if winner is None:
                continue
            for id_k, id_v in (loser.get("identifiers") or {}).items():
                if id_v and not winner["identifiers"].get(id_k):
                    winner["identifiers"][id_k] = id_v
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
                "form_values": "✓", "fill_event": "○", "missing_fill": "[WARN]",
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

    def _compact_keypress_sequences(self, raw_events: list) -> list:
        """Convert sequences of single-char keypress events into one accumulated fill event.

        Some recorders emit individual key events (value = single char or empty, key = single
        char) rather than accumulated fill events. This method detects such sequences and
        rebuilds the full value by concatenating individual keys.

        - Backspace: removes last accumulated character.
        - Enter / Tab: terminates the sequence (creates the fill then stops).
        - Accumulated fill events (value length > 1): passed through unchanged so that
          _compact_fill_events can handle them normally.

        Must run BEFORE _compact_fill_events.
        """
        if not raw_events:
            return raw_events

        def _is_individual_keypress(event: dict) -> bool:
            if event.get("type") != "keypress":
                return False
            value = event.get("value") or ""
            key = event.get("key") or ""
            # Accumulated fill: value > 1 char — not an individual keypress
            if len(value) > 1:
                return False
            return True

        def _target_key(t) -> tuple:
            if not t:
                return ("__none__",)
            return (
                t.get("tag", ""),
                t.get("id", "") or (t.get("all_attributes") or {}).get("id", ""),
                t.get("name", ""),
                t.get("placeholder", ""),
                t.get("accessible_name", ""),
            )

        result: list = []
        i = 0
        while i < len(raw_events):
            event = raw_events[i]

            if not _is_individual_keypress(event):
                result.append(event)
                i += 1
                continue

            current_target = _target_key(event.get("target"))
            accumulated = ""
            j = i
            last_event = event

            while j < len(raw_events):
                ev = raw_events[j]
                if not _is_individual_keypress(ev):
                    break
                if _target_key(ev.get("target")) != current_target:
                    break

                value = ev.get("value") or ""
                key = ev.get("key") or ""
                char = value if value else key

                if char in ("Backspace", "\b"):
                    accumulated = accumulated[:-1]
                elif char in ("Enter", "Tab", "\r", "\n", "\t"):
                    last_event = ev
                    j += 1
                    break
                elif len(char) == 1:
                    accumulated += char

                last_event = ev
                j += 1

            # Only synthesize a fill event when 2+ events were consumed AND
            # we built a non-empty string. Otherwise pass through unchanged.
            if j > i + 1 and accumulated:
                synthetic = dict(last_event)
                synthetic["type"] = "fill"
                synthetic["value"] = accumulated
                result.append(synthetic)
                i = j
            else:
                result.append(event)
                i += 1

        return result

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

        FILL_TYPES = {"fill", "keypress", "select_option"}

        def _target_key(target: dict | None) -> tuple:
            """Derive stable key from target to identify same element."""
            if not target:
                return ("__none__",)
            return (
                target.get("tag", ""),
                target.get("id", "") or (target.get("all_attributes") or {}).get("id", ""),
                target.get("name", ""),
                target.get("test_id", ""),
                target.get("placeholder", ""),
                target.get("accessible_name", ""),
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
                    # Allow a same-element click (focus) to pass through without breaking
                    if next_type == "click" and _target_key(next_event.get("target")) == current_key:
                        j += 1
                        continue
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

        FILL_TYPES = {"fill", "keypress", "select_option"}
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
            "select_option": "select_option",
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
            attrs = step.get("attrs", {})
            expected = _clean_text(step.get("expected_value", ""), max_len=200)
            target_data = {
                "tag": step.get("tag_name", "") or step.get("tagName", ""),
                # Use cleaned expected_value as text so has-text candidate is clean
                "text": expected or step.get("accessible_name", "") or step.get("text", ""),
                "id": step.get("element_id", ""),
                "accessible_name": step.get("aria_label", "") or step.get("accessible_name", "") or attrs.get("aria-label", ""),
                "role": step.get("role", "") or attrs.get("role", ""),
                "css_path": step.get("css_path", "") or step.get("selector", ""),
            }
            target = self._build_target(target_data)
            assert_type = step.get("assert_type", "textual")
            assert_state = step.get("assert_state", "")
            return SemanticAction(
                action="assert",
                target=target,
                value=expected,
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
            candidates.extend(_attr_css_variants("test_id", tid, tag, 0.80, "test_id"))

        # 0.1 data-* attributes (generic)
        data_attrs = target_data.get("data_attrs") or {}
        for attr_name, attr_value in data_attrs.items():
            if attr_name.startswith("data-") and attr_value and len(attr_value) < 60:
                sel = f"[{attr_name}='{attr_value}']"
                candidates.append(LocatorCandidate("data_attr", sel, 0.65, f"{attr_name}={attr_value}"))

        # 0.2 <a href="..."> — route-based locator stable across Tailwind class changes
        if tag == "a":
            _href = (target_data.get("all_attributes") or {}).get("href") or ""
            if _href and not _href.startswith("javascript:") and not _href.startswith("#") and len(_href) < 200:
                _href_score = 0.87 if (_href.startswith("/") or _href.startswith("http")) else 0.65
                candidates.append(LocatorCandidate("href", f'a[href="{_href}"]', _href_score, f"href={_href}"))
                candidates.extend(_attr_css_variants("href", _href, "a", _href_score, "href"))

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
            ptag = (target_data.get("tag") or "").lower()
            # Prefer input[placeholder] over bare [placeholder] — Angular wrappers
            # (dsc-input-currency) share placeholders with native inputs, causing
            # strict mode violations and fill() failures on non-input elements.
            if ptag in ("input", "textarea", "select"):
                sel = f"{ptag}[placeholder=\"{ph}\"]"
            else:
                sel = f"[placeholder=\"{ph}\"]"
            candidates.append(LocatorCandidate("placeholder", sel, 0.85, f"placeholder={ph}"))
            candidates.extend(_attr_css_variants("placeholder", ph, ptag, 0.85, "placeholder"))

        if target_data.get("id") and target_data["id"] not in ("mat-input-0", "mat-input-1"):
            el_id = target_data["id"]
            candidates.append(LocatorCandidate("id", f"#{el_id}", 0.75, f"id={el_id}"))
            candidates.extend(_attr_css_variants("id", el_id, tag, 0.75, "id"))

        if target_data.get("name"):
            name_val = target_data["name"]
            candidates.append(LocatorCandidate("name", f"[name=\"{name_val}\"]", 0.70, f"name={name_val}"))
            candidates.extend(_attr_css_variants("name", name_val, tag, 0.70, "name"))

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


        # -- Contenteditable detection (GT-08) --
        # When the element has contenteditable=true and no stable locator was found,
        # generate a direct attribute selector. Playwright supports fill() on [contenteditable].
        # Must check key EXISTENCE before checking value: .get("contenteditable", "") returns ""
        # for elements that lack the attribute entirely, making "" in ("true","") → True for all
        # elements (false positive). Only fire when the key is actually present in the DOM.
        _attrs_dict = target_data.get("attributes") or {}
        _all_attrs_dict = target_data.get("all_attributes") or {}
        if "contenteditable" in _attrs_dict:
            _contenteditable_attrs = _attrs_dict["contenteditable"] or ""
        elif "contenteditable" in _all_attrs_dict:
            _contenteditable_attrs = _all_attrs_dict["contenteditable"] or ""
        else:
            _contenteditable_attrs = None  # attribute absent — do not generate CE candidate
        if _contenteditable_attrs is not None and _contenteditable_attrs in ("true", "") and tag:
            # Buttons with contenteditable="" are an Angular Material quirk (ripple layer).
            # For buttons, contenteditable selector is unreliable — generate at low score
            # so that button:has-text() candidates ranked above it take precedence.
            _is_button_like = tag in ("button", "a", "summary")
            _ce_base_score = 0.25 if _is_button_like else 0.50
            _ce_text_score = 0.30 if _is_button_like else 0.60
            contenteditable_sel = f'{tag}[contenteditable="{_contenteditable_attrs}"]'
            candidates.append(LocatorCandidate("contenteditable", contenteditable_sel, _ce_base_score, "contenteditable element"))
            # Also add text-based variant if text is available for disambiguation
            ce_text = _clean_text(target_data.get("text") or target_data.get("accessible_name") or "")
            if ce_text and len(ce_text) <= 40 and not _is_generic_text(ce_text):
                candidates.append(LocatorCandidate(
                    "contenteditable", f'{tag}[contenteditable="{_contenteditable_attrs}"]:has-text("{ce_text}")',
                    _ce_text_score, f"contenteditable with text: {ce_text}"
                ))

        # Structural CSS path fallback — stable relative path in DOM tree
        css_path = target_data.get("css_path") or ""
        if css_path and len(css_path) > 4 and ">" in css_path:
            candidates.append(LocatorCandidate("css_path", css_path, 0.60, "css_path"))

        # nth-child for disambiguation — always add when available so healing
        # can use positional fallback for sibling buttons/tabs with similar text
        nth = target_data.get("nth_child") or 0
        tag = target_data.get("tag") or ""
        if nth > 0 and tag:
            candidates.append(LocatorCandidate("nth_child", f"{tag}:nth-child({nth})", 0.35, "nth-child position"))

        # aria-label for input/textarea when role not available
        if not target_data.get("role"):
            aria_label = (target_data.get("aria_attrs", {}).get("aria-label", "") or
                         (target_data.get("all_attributes") or {}).get("aria-label", "") or
                         target_data.get("accessible_name", "") or "")
            if aria_label and len(aria_label) < 60:
                al_tag = (target_data.get("tag") or "").lower()
                if al_tag in ("input", "textarea"):
                    sel = f'{al_tag}[aria-label="{aria_label}"]'
                    candidates.append(LocatorCandidate("aria_label", sel, 0.90, f"{al_tag} aria-label={aria_label}"))
                    candidates.extend(_attr_css_variants("aria_label", aria_label, al_tag, 0.90, "aria-label"))

        # Compound selectors: combine 2 attributes for higher specificity
        candidates.extend(_compound_candidates(target_data, tag))

        # Build fingerprint: flat dict of all available attributes for runtime healing
        _nth = target_data.get("nth_child", 0) or 0
        _class_list = target_data.get("class_list") or []
        _parent_tag = target_data.get("parent_tag") or ""
        fingerprint = {
            "tag": target_data.get("tag", ""),
            "role": target_data.get("role", ""),
            "accessible_name": target_data.get("accessible_name", ""),
            "placeholder": target_data.get("placeholder", ""),
            "label": target_data.get("label", ""),
            "name": target_data.get("name", ""),
            "test_id": target_data.get("test_id", ""),
            "id": target_data.get("id", ""),
            "text": target_data.get("text", ""),
            "nth_child": _nth,
            "class_list": _class_list[:5],
            "parent_tag": _parent_tag,
            "href": (target_data.get("all_attributes") or {}).get("href", "")
                     or target_data.get("href", ""),
        }
        # Remove empty values to keep fingerprint compact
        fingerprint = {k: v for k, v in fingerprint.items() if v}

        # Sort candidates by score (descending) for deterministic ordering
        candidates.sort(key=lambda c: c.score, reverse=True)

        # Phase 2: append v2 super-selector candidates when enabled.
        # v2 candidates carry intent_text + per-attribute stability;
        # legacy candidates remain first to preserve current selection.
        intent_text = None
        if self._use_v2 and self._v2_extractor is not None:
            try:
                v2 = self._v2_extractor.extract(target_data)
                candidates.extend(v2)
                if v2 and v2[0].intent_text:
                    intent_text = v2[0].intent_text
            except Exception as exc:
                logger.warning("v2 locator extractor failed: %s", exc)

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
            fingerprint=fingerprint,
            intent_text=intent_text,
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

    # ── IntentReconstruction (merged from intent_reconstructor.py) ──────────

    IR_SOURCE_PRIORITY = {
        "form_values": 100,
        "fill_event": 80,
        "setter_hook": 78,
        "checked_transition": 72,
        "snapshot_diff": 70,
        "network_payload": 60,
        "final_state": 55,
        "polling": 50,
        "missing_fill": 10,
    }

    def _ir_all(self, recording_dir: str, steps: list) -> list[dict]:
        """Run all IR strategies, return deduped FieldValueMap entries."""
        entries = []
        entries.extend(self._ir_value_mutations(recording_dir, steps))
        entries.extend(self._ir_snapshots(recording_dir, steps))
        entries.extend(self._ir_form_values(steps))
        entries.extend(self._ir_network(recording_dir, steps))
        entries.extend(self._ir_final_state(recording_dir, steps))
        entries.extend(self._ir_polling(recording_dir, steps))
        return self._ir_dedupe_entries(entries)

    # ── Polling ──────────────────────────────────────────────────────────────

    def _ir_polling(self, recording_dir: str, steps: list) -> list[dict]:
        """Extract values from field_snapshots.jsonl with source=polling."""
        snapshots_path = os.path.join(recording_dir, "field_snapshots.jsonl")
        if not os.path.exists(snapshots_path):
            return []
        polling_entries = []
        with open(snapshots_path) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    continue
                source = entry.get("source", "")
                interval_ms = entry.get("interval_ms", 0) or 0
                is_polling = source == "polling" or interval_ms > 0
                if not is_polling:
                    for snap in entry.get("snapshots", []):
                        snap_source = snap.get("source", "")
                        snap_interval = snap.get("interval_ms", 0) or 0
                        if snap_source == "polling" or snap_interval > 0:
                            snap["_batch_ts"] = entry.get("timestamp", "")
                            polling_entries.append(snap)
                    continue
                if "snapshots" in entry and isinstance(entry["snapshots"], list):
                    for snap in entry["snapshots"]:
                        snap["_batch_ts"] = entry.get("timestamp", "")
                        polling_entries.append(snap)
                else:
                    polling_entries.append(entry)
        if not polling_entries:
            return []
        by_fp: dict[str, dict] = {}
        for snap in polling_entries:
            fp = snap.get("fingerprint") or snap.get("identifiers", {}).get("css_path", "")
            value = (snap.get("value") or "").strip()
            if not fp or not value:
                continue
            by_fp[fp] = snap
        entries = []
        for fp, snap in by_fp.items():
            value = (snap.get("value") or "").strip()
            if not value:
                continue
            ids = snap.get("identifiers", {})
            tag = snap.get("tag", "input")
            name = ids.get("name") or ""
            label = ids.get("label") or ids.get("aria-label") or ""
            placeholder = ids.get("placeholder") or ""
            element_id = ids.get("id") or ""
            ts = snap.get("timestamp") or snap.get("_batch_ts", "")
            step_idx = self._ir_find_nearest_step_index(steps, ts)
            canonical = self._canonical_field_key(name or label or placeholder or fp)
            display = label or name or placeholder or fp
            entries.append({
                "field_key": canonical, "value": value,
                "intention": f"fill {display} with '{value}' (reconstructed from polling)",
                "identifiers": {"name": name, "id": element_id, "label": label,
                                "placeholder": placeholder, "aria_label": ids.get("aria-label") or "",
                                "fingerprint": fp, "tag": tag},
                "source": "polling", "step_index": step_idx, "fingerprint": fp,
            })
        return entries

    # ── Value mutations (setter hooks) ──────────────────────────────────────

    def _ir_value_mutations(self, recording_dir: str, steps: list) -> list[dict]:
        """Read value_mutations.jsonl — programmatic value changes."""
        path = os.path.join(recording_dir, "value_mutations.jsonl")
        if not os.path.exists(path):
            return []
        mutations = []
        with open(path) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    mutations.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
        if not mutations:
            return []
        by_fp: dict[str, dict] = {}
        for mut in mutations:
            mut_type = mut.get("type", "value_mutation")
            if mut_type == "content_edit":
                value = (mut.get("value") or "").strip()
                fp = mut.get("fingerprint", "")
            else:
                value = (mut.get("new_value") or "").strip()
                fp = mut.get("fingerprint") or (
                    f"{mut.get('tag', 'input')}#{mut.get('id', '')}[name={mut.get('name', '')}]"
                )
            if not value or not fp:
                continue
            by_fp[fp] = {**mut, "_resolved_value": value, "_fingerprint": fp}
        entries = []
        for fp, mut in by_fp.items():
            value = mut["_resolved_value"]
            raw_value = (mut.get("old_value") or mut.get("raw_value") or "").strip()
            name = mut.get("name") or ""
            el_id = mut.get("id") or ""
            tag = mut.get("tag", "input")
            ts = mut.get("timestamp", "")
            step_idx = self._ir_find_nearest_step_index(steps, ts)
            is_masked = self._ir_detect_masked_field(value, raw_value)
            canonical = self._canonical_field_key(name or el_id or fp)
            entries.append({
                "field_key": canonical, "value": value,
                "intention": f"fill {name or el_id or fp} with '{value}' (reconstructed from setter_hook)",
                "identifiers": {"name": name, "id": el_id, "fingerprint": fp,
                                "tag": tag, "is_masked": is_masked},
                "source": "setter_hook", "step_index": step_idx,
                "fingerprint": fp, "is_masked": is_masked,
            })
        return entries

    # ── Snapshot diff + checked transitions ─────────────────────────────────

    def _ir_snapshots(self, recording_dir: str, steps: list) -> list[dict]:
        """Detect value/checked changes between field snapshots."""
        snapshots_path = os.path.join(recording_dir, "field_snapshots.jsonl")
        if not os.path.exists(snapshots_path):
            return []
        snapshots = []
        with open(snapshots_path) as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        snapshots.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
        if not snapshots:
            return []
        all_individual = []
        for entry in snapshots:
            if "snapshots" in entry and isinstance(entry["snapshots"], list):
                for s in entry["snapshots"]:
                    s["_batch_ts"] = entry.get("timestamp", "")
                    all_individual.append(s)
            else:
                all_individual.append(entry)
        if len(all_individual) < 2:
            return []
        all_individual.sort(key=lambda s: s.get("timestamp") or s.get("_batch_ts", ""))
        groups: dict[str, list[dict]] = {}
        for s in all_individual:
            fp = s.get("fingerprint") or s.get("identifiers", {}).get("css_path", "unknown")
            groups.setdefault(fp, []).append(s)
        entries = []
        for fp, items in groups.items():
            prev_val = ""
            prev_checked = None
            has_prev = False
            for item in items:
                curr_val = item.get("value", "") or ""
                curr_checked = item.get("checked")
                curr_ts = item.get("timestamp") or item.get("_batch_ts", "")
                ids = item.get("identifiers", {})
                tag = item.get("tag", "")
                name = ids.get("name") or ""
                label = ids.get("label") or ids.get("aria-label") or ""
                placeholder = ids.get("placeholder") or ""
                element_id = ids.get("id") or ""
                if has_prev:
                    entry = None
                    if curr_checked is True and prev_checked is not True:
                        display = label or name or placeholder or fp
                        entry = self._ir_make_snapshot_entry(
                            fp, display, ids, tag, name, label, placeholder,
                            element_id, steps, curr_ts, "checked_transition", "checked transition")
                    elif curr_val and curr_val != prev_val:
                        entry = self._ir_make_snapshot_entry(
                            fp, curr_val, ids, tag, name, label, placeholder,
                            element_id, steps, curr_ts, "snapshot_diff", "snapshot")
                    if entry:
                        entries.append(entry)
                has_prev = True
                if curr_val:
                    prev_val = curr_val
                if curr_checked is not None:
                    prev_checked = curr_checked
        by_key: dict[str, dict] = {}
        for entry in entries:
            by_key[entry["field_key"]] = entry
        return list(by_key.values())

    def _ir_make_snapshot_entry(
        self, fp, value, ids, tag, name, label, placeholder, element_id,
        steps, ts, source, suffix,
    ) -> dict:
        step_idx = self._ir_find_nearest_step_index(steps, ts)
        canonical = self._canonical_field_key(name or label or placeholder or fp)
        display = label or name or placeholder or fp
        return {
            "field_key": canonical, "value": value,
            "intention": f"fill {display} with '{value}' (reconstructed from {suffix})",
            "identifiers": {"name": name, "id": element_id, "label": label,
                            "placeholder": placeholder, "aria_label": ids.get("aria-label") or "",
                            "fingerprint": fp, "tag": tag},
            "source": source, "step_index": step_idx, "fingerprint": fp,
        }

    # ── Final state snapshot ────────────────────────────────────────────────

    def _ir_final_state(self, recording_dir: str, steps: list) -> list[dict]:
        """Read final_state_snapshot.json as fallback."""
        path = os.path.join(recording_dir, "final_state_snapshot.json")
        if not os.path.exists(path):
            return []
        try:
            with open(path) as f:
                data = json.load(f)
        except (json.JSONDecodeError, ValueError):
            return []
        fields = data.get("fields") or []
        if not fields:
            return []
        ts = data.get("timestamp", "")
        step_idx = self._ir_find_nearest_step_index(steps, ts) if ts else max(0, len(steps) - 1)
        entries = []
        for field in fields:
            ids = field.get("identifiers", {})
            tag = field.get("tag", "")
            name = ids.get("name") or ""
            label = ids.get("label") or ids.get("aria-label") or ""
            placeholder = ids.get("placeholder") or ""
            element_id = ids.get("id") or ""
            fp = field.get("fingerprint", "")
            checked = field.get("checked")
            value = (field.get("value") or "").strip()
            if checked is True and field.get("type") in ("radio", "checkbox"):
                value = label or name or "true"
            elif checked is False:
                continue
            if not value:
                continue
            canonical = self._canonical_field_key(name or label or placeholder or fp)
            display = label or name or placeholder or fp
            entries.append({
                "field_key": canonical, "value": value,
                "intention": f"fill {display} with '{value}' (from final_state)",
                "identifiers": {"name": name, "id": element_id, "label": label,
                                "placeholder": placeholder, "aria_label": ids.get("aria-label") or "",
                                "fingerprint": fp, "tag": tag},
                "source": "final_state", "step_index": step_idx, "fingerprint": fp,
            })
        return entries

    # ── Form values ─────────────────────────────────────────────────────────

    def _ir_form_values(self, steps: list) -> list[dict]:
        """Extract form_values from submit step contexts."""
        entries = []
        for i, step in enumerate(steps):
            ctx = getattr(step, "context", {}) or {}
            form_vals = ctx.get("form_values") or {}
            if not form_vals:
                continue
            for fname, fval in form_vals.items():
                if not fval:
                    continue
                canonical = self._canonical_field_key(fname)
                entries.append({
                    "field_key": canonical, "value": fval,
                    "intention": f"fill {fname} with '{fval}' (from submit payload)",
                    "identifiers": {"form_name": fname},
                    "source": "form_values", "step_index": i,
                })
        return entries

    # ── Network payload ─────────────────────────────────────────────────────

    def _ir_network(self, recording_dir: str, steps: list) -> list[dict]:
        """Parse POST/PUT request payloads for form field values."""
        network_path = os.path.join(recording_dir, "network_log.json")
        if not os.path.exists(network_path):
            return []
        with open(network_path) as f:
            try:
                network_entries = json.load(f)
            except (json.JSONDecodeError, ValueError):
                return []
        payloads = []
        for entry in network_entries:
            if entry.get("type") != "request":
                continue
            method = entry.get("method", "").upper()
            if method not in ("POST", "PUT", "PATCH"):
                continue
            post_data = entry.get("post_data")
            if not post_data:
                continue
            parsed = self._ir_parse_payload(post_data, entry.get("url", ""))
            if parsed:
                payloads.append({
                    "url": entry.get("url", ""),
                    "method": method,
                    "timestamp": entry.get("timestamp", ""),
                    "fields": parsed,
                })
        if not payloads:
            return []
        field_ids = RecordingNormalizer._ir_build_field_identifiers(steps)
        entries = []
        for payload in payloads:
            for key, value in payload["fields"].items():
                if not value:
                    continue
                step_idx, confidence = RecordingNormalizer._ir_correlate_payload_key(
                    key, value, payload, steps, field_ids)
                if confidence == 0.0:
                    continue
                canonical = self._canonical_field_key(key)
                entries.append({
                    "field_key": canonical, "value": str(value),
                    "intention": f"fill '{key}' with '{value}' (from network payload)",
                    "identifiers": {"network_key": key, "payload_url": payload["url"],
                                    "payload_method": payload["method"], "confidence": confidence},
                    "source": "network_payload", "step_index": step_idx,
                    "evidence": {"url": payload["url"], "method": payload["method"], "payload_key": key},
                })
        return entries

    # ── IR helpers ──────────────────────────────────────────────────────────

    @staticmethod
    def _ir_detect_masked_field(value: str, raw_value: str = "") -> bool:
        if not value:
            return False
        MASK_PATTERN = _re.compile(r'^[\d\s.,/\-()]+$')
        if not MASK_PATTERN.match(value):
            return False
        has_separator = bool(_re.search(r'[.,/\-]', value))
        if not has_separator:
            return False
        if raw_value and raw_value != value:
            return True
        KNOWN_MASKS = [
            _re.compile(r'^\d{1,3}(\.\d{3})+(,\d{2})?$'),
            _re.compile(r'^\d{3}\.\d{3}\.\d{3}-\d{2}$'),
            _re.compile(r'^\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}$'),
            _re.compile(r'^\(?\d{2}\)?\s?\d{4,5}-?\d{4}$'),
            _re.compile(r'^\d{2}/\d{2}/\d{4}$'),
        ]
        return any(p.match(value) for p in KNOWN_MASKS)

    @staticmethod
    def _ir_dedupe_entries(entries: list[dict]) -> list[dict]:
        best: dict[str, dict] = {}
        for entry in entries:
            key = entry.get("field_key", "")
            if not key or not entry.get("value"):
                continue
            existing = best.get(key)
            if not existing:
                best[key] = entry
                continue
            old_p = RecordingNormalizer.IR_SOURCE_PRIORITY.get(existing.get("source", ""), 0)
            new_p = RecordingNormalizer.IR_SOURCE_PRIORITY.get(entry.get("source", ""), 0)
            if new_p > old_p:
                best[key] = entry
            elif new_p == old_p and len(entry.get("value", "")) >= len(existing.get("value", "")):
                best[key] = entry
        return list(best.values())

    @staticmethod
    def _ir_find_nearest_step_index(steps: list, timestamp: str) -> int:
        if not timestamp or not steps:
            return 0
        try:
            from datetime import datetime as dt_dt
            target = dt_dt.fromisoformat(timestamp.replace("Z", "+00:00"))
            best_idx = 0
            best_diff = float("inf")
            for i, step in enumerate(steps):
                ctx = getattr(step, "context", {}) or {}
                ts = ctx.get("timestamp", "")
                if ts:
                    try:
                        step_ts = dt_dt.fromisoformat(ts.replace("Z", "+00:00"))
                        diff = abs((step_ts - target).total_seconds())
                        if diff < best_diff:
                            best_diff = diff
                            best_idx = i
                    except (ValueError, TypeError):
                        continue
            return best_idx
        except (ValueError, TypeError):
            return 0

    @staticmethod
    def _ir_parse_payload(post_data: str, url: str) -> dict:
        if not post_data:
            return {}
        post_data = post_data.strip()
        if post_data.startswith("{") or post_data.startswith("["):
            try:
                data = json.loads(post_data)
                if isinstance(data, dict):
                    return {k: str(v) for k, v in data.items() if not isinstance(v, (dict, list))}
                return {}
            except json.JSONDecodeError:
                pass
        try:
            from urllib.parse import parse_qs
            parsed = parse_qs(post_data)
            return {k: v[0] if v else "" for k, v in parsed.items()}
        except Exception:
            pass
        return {}

    @staticmethod
    def _ir_build_field_identifiers(steps: list) -> dict:
        ids = {}
        for step in steps:
            if not step.target:
                continue
            for key in [step.target.name, step.target.element_id,
                        step.target.label, step.target.placeholder, step.target.text]:
                if key:
                    canonical = key.strip().lower().replace(" ", "_").replace("-", "_")
                    ids[canonical] = {
                        "name": step.target.name,
                        "id": step.target.element_id,
                        "label": step.target.label,
                        "placeholder": step.target.placeholder,
                    }
        return ids

    @staticmethod
    def _ir_match_by_url(payload_url: str, steps: list) -> int:
        if not payload_url:
            return -1
        for i, step in enumerate(steps):
            step_url = getattr(step, "url", "") or ""
            if not step_url:
                continue
            if step_url == payload_url or step_url.rstrip("/") == payload_url.rstrip("/"):
                return i
        return -1

    @staticmethod
    def _ir_correlate_payload_key(
        key: str, value: str, payload: dict,
        steps: list, field_identifiers: dict,
    ) -> tuple[int, float]:
        canonical_key = key.strip().lower().replace(" ", "_").replace("-", "_")
        if canonical_key in field_identifiers:
            for i, step in enumerate(steps):
                if not step.target:
                    continue
                if step.target.name and step.target.name.lower() == canonical_key:
                    return i, 1.0
                if step.target.element_id and step.target.element_id.lower() == canonical_key:
                    return i, 1.0
        payload_url = payload.get("url", "")
        url_match = RecordingNormalizer._ir_match_by_url(payload_url, steps)
        if url_match >= 0:
            return url_match, 0.7
        return 0, 0.0
