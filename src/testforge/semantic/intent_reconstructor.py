"""TestForge — Reconstrutor de Intenção (Sprint 4 + Phase B).

Reconstrói valores de campo ausentes e sintetiza passos de preenchimento a partir
de fontes de evidência capturadas pelo gravador:
1. form_values — valores capturados no tempo de submit
2. setter_hook — value_mutations.jsonl (atribuições .value programáticas)
3. snapshot_diff / checked_transition — field_snapshots.jsonl
4. network_payload — análise de corpo de requisição POST/PUT
5. final_state — final_state_snapshot.json dump do final da sessão

Cada fonte produz entradas FieldValueMap ou contexto de passo semântico
consumido por RecordingNormalizer durante normalize().
"""

import json
import os
import re
from typing import Optional
from urllib.parse import parse_qs, urlparse



class IntentReconstructor:
    """Combina múltiplas fontes de evidência para reconstruir intenções ausentes."""

    # Default weights for source preference ordering
    SOURCE_PRIORITY = {
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

    def reconstruct_all(self, recording_dir: str, steps: list) -> list[dict]:
        """Executa todas as estratégias de reconstrução, retorna entradas FieldValueMap.

        Each entry dict: {field_key, value, intention, identifiers, source, step_index}
        """
        entries = []

        entries.extend(self._reconstruct_from_value_mutations(recording_dir, steps))
        entries.extend(self._reconstruct_from_snapshots(recording_dir, steps))
        entries.extend(self._reconstruct_from_form_values(steps))
        entries.extend(self._reconstruct_from_network(recording_dir, steps))
        entries.extend(self._reconstruct_from_final_state(recording_dir, steps))

        return self._dedupe_entries(entries)

    @staticmethod
    def _dedupe_entries(entries: list[dict]) -> list[dict]:
        """Keep highest-priority entry per field_key."""
        best: dict[str, dict] = {}
        for entry in entries:
            key = entry.get("field_key", "")
            if not key or not entry.get("value"):
                continue
            existing = best.get(key)
            if not existing:
                best[key] = entry
                continue
            old_p = IntentReconstructor.SOURCE_PRIORITY.get(existing.get("source", ""), 0)
            new_p = IntentReconstructor.SOURCE_PRIORITY.get(entry.get("source", ""), 0)
            if new_p > old_p:
                best[key] = entry
            elif new_p == old_p and len(entry.get("value", "")) >= len(existing.get("value", "")):
                best[key] = entry
        return list(best.values())

    # ── Phase B: value_mutations.jsonl (setter hooks) ─────────────────────────

    def _reconstruct_from_value_mutations(self, recording_dir: str, steps: list) -> list[dict]:
        """Read value_mutations.jsonl — programmatic value changes (currency mask, etc.)."""
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

        # Last non-empty value per fingerprint wins
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
            name = mut.get("name") or ""
            el_id = mut.get("id") or ""
            tag = mut.get("tag", "input")
            ts = mut.get("timestamp", "")
            step_idx = self._find_nearest_step_index(steps, ts)

            canonical = self._canonical_key(name or el_id or fp)
            intention = (
                f"fill {name or el_id or fp} with '{value}' "
                f"(reconstructed from setter_hook)"
            )
            entries.append({
                "field_key": canonical,
                "value": value,
                "intention": intention,
                "identifiers": {
                    "name": name,
                    "id": el_id,
                    "fingerprint": fp,
                    "tag": tag,
                },
                "source": "setter_hook",
                "step_index": step_idx,
                "fingerprint": fp,
            })

        return entries

    # ── Story 5.1: Snapshot diff + checked transitions ───────────────────────

    def _reconstruct_from_snapshots(self, recording_dir: str, steps: list) -> list[dict]:
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
                field_type = item.get("type", "") or ""
                name = ids.get("name") or ""
                label = ids.get("label") or ids.get("aria-label") or ""
                placeholder = ids.get("placeholder") or ""
                element_id = ids.get("id") or ""

                if has_prev:
                    entry = None
                    # Checked transition (radio/checkbox)
                    if curr_checked is True and prev_checked is not True:
                        display = label or name or placeholder or fp
                        entry = self._make_snapshot_entry(
                            fp=fp, value=display, ids=ids, tag=tag,
                            name=name, label=label, placeholder=placeholder,
                            element_id=element_id, steps=steps, ts=curr_ts,
                            source="checked_transition",
                            suffix="checked transition",
                        )
                    # Value transition (text inputs, selects, etc.)
                    elif curr_val and curr_val != prev_val:
                        entry = self._make_snapshot_entry(
                            fp=fp, value=curr_val, ids=ids, tag=tag,
                            name=name, label=label, placeholder=placeholder,
                            element_id=element_id, steps=steps, ts=curr_ts,
                            source="snapshot_diff",
                            suffix="snapshot",
                        )

                    if entry:
                        entries.append(entry)

                has_prev = True
                if curr_val:
                    prev_val = curr_val
                if curr_checked is not None:
                    prev_checked = curr_checked

        # Keep last transition per field_key (most complete value for currency masks)
        by_key: dict[str, dict] = {}
        for entry in entries:
            by_key[entry["field_key"]] = entry
        return list(by_key.values())

    def _make_snapshot_entry(
        self, fp, value, ids, tag, name, label, placeholder, element_id,
        steps, ts, source, suffix,
    ) -> dict:
        step_idx = self._find_nearest_step_index(steps, ts)
        canonical = self._canonical_key(name or label or placeholder or fp)
        display = label or name or placeholder or fp
        return {
            "field_key": canonical,
            "value": value,
            "intention": f"fill {display} with '{value}' (reconstructed from {suffix})",
            "identifiers": {
                "name": name,
                "id": element_id,
                "label": label,
                "placeholder": placeholder,
                "aria_label": ids.get("aria-label") or "",
                "fingerprint": fp,
                "tag": tag,
            },
            "source": source,
            "step_index": step_idx,
            "fingerprint": fp,
        }

    # ── Phase B: final_state_snapshot.json ───────────────────────────────────

    def _reconstruct_from_final_state(self, recording_dir: str, steps: list) -> list[dict]:
        """Read final_state_snapshot.json as fallback for unresolved fields."""
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
        step_idx = self._find_nearest_step_index(steps, ts) if ts else max(0, len(steps) - 1)

        entries = []
        for field in fields:
            ids = field.get("identifiers", {})
            tag = field.get("tag", "")
            field_type = field.get("type", "") or ""
            name = ids.get("name") or ""
            label = ids.get("label") or ids.get("aria-label") or ""
            placeholder = ids.get("placeholder") or ""
            element_id = ids.get("id") or ""
            fp = field.get("fingerprint", "")
            checked = field.get("checked")
            value = (field.get("value") or "").strip()

            if checked is True and field_type in ("radio", "checkbox"):
                value = label or name or "true"
            elif checked is False:
                continue
            if not value:
                continue

            canonical = self._canonical_key(name or label or placeholder or fp)
            display = label or name or placeholder or fp
            entries.append({
                "field_key": canonical,
                "value": value,
                "intention": f"fill {display} with '{value}' (from final_state)",
                "identifiers": {
                    "name": name,
                    "id": element_id,
                    "label": label,
                    "placeholder": placeholder,
                    "aria_label": ids.get("aria-label") or "",
                    "fingerprint": fp,
                    "tag": tag,
                },
                "source": "final_state",
                "step_index": step_idx,
                "fingerprint": fp,
            })

        return entries

    # ── Story 5.2: Form values reconstruction ──────────────────────────────────

    def _reconstruct_from_form_values(self, steps: list) -> list[dict]:
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
                canonical = self._canonical_key(fname)
                entries.append({
                    "field_key": canonical,
                    "value": fval,
                    "intention": f"fill {fname} with '{fval}' (from submit payload)",
                    "identifiers": {"form_name": fname},
                    "source": "form_values",
                    "step_index": i,
                })

        return entries

    # ── Story 5.3: Network payload reconstruction ──────────────────────────────

    def _reconstruct_from_network(self, recording_dir: str, steps: list) -> list[dict]:
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

            parsed = self._parse_payload(post_data, entry.get("url", ""))
            if parsed:
                payloads.append({
                    "url": entry.get("url", ""),
                    "method": method,
                    "timestamp": entry.get("timestamp", ""),
                    "fields": parsed,
                })

        if not payloads:
            return []

        field_identifiers = self._build_field_identifiers(steps)

        entries = []
        for payload in payloads:
            for key, value in payload["fields"].items():
                if not value:
                    continue
                step_idx = self._correlate_payload_key(
                    key, value, payload, steps, field_identifiers,
                )
                canonical = self._canonical_key(key)
                entries.append({
                    "field_key": canonical,
                    "value": str(value),
                    "intention": f"fill '{key}' with '{value}' (from network payload)",
                    "identifiers": {
                        "network_key": key,
                        "payload_url": payload["url"],
                        "payload_method": payload["method"],
                    },
                    "source": "network_payload",
                    "step_index": step_idx,
                    "evidence": {
                        "url": payload["url"],
                        "method": payload["method"],
                        "payload_key": key,
                    },
                })

        return entries

    # ── Helpers ────────────────────────────────────────────────────────────────

    @staticmethod
    def _find_nearest_step_index(steps: list, timestamp: str) -> int:
        """Find the step index closest to the given timestamp."""
        if not timestamp or not steps:
            return 0

        try:
            from datetime import datetime
            target = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))

            best_idx = 0
            best_diff = float("inf")

            for i, step in enumerate(steps):
                ctx = getattr(step, "context", {}) or {}
                ts = ctx.get("timestamp", "")
                if ts:
                    try:
                        step_ts = datetime.fromisoformat(ts.replace("Z", "+00:00"))
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
    def _parse_payload(post_data: str, url: str) -> dict:
        """Parse POST body as form-urlencoded or JSON, return field dict."""
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
            parsed = parse_qs(post_data)
            return {k: v[0] if v else "" for k, v in parsed.items()}
        except Exception:
            pass

        return {}

    @staticmethod
    def _build_field_identifiers(steps: list) -> dict:
        """Build a map of all field identifiers from steps for key correlation."""
        ids = {}
        for step in steps:
            if not step.target:
                continue
            name = step.target.name
            el_id = step.target.element_id
            label = step.target.label
            placeholder = step.target.placeholder
            text = step.target.text

            for key in [name, el_id, label, placeholder, text]:
                if key:
                    canonical = key.strip().lower().replace(" ", "_").replace("-", "_")
                    ids[canonical] = {
                        "name": name,
                        "id": el_id,
                        "label": label,
                        "placeholder": placeholder,
                    }
        return ids

    @staticmethod
    def _correlate_payload_key(key: str, value: str, payload: dict,
                                steps: list, field_identifiers: dict) -> int:
        """Find the step index most likely associated with a payload field."""
        canonical_key = key.strip().lower().replace(" ", "_").replace("-", "_")

        if canonical_key in field_identifiers:
            for i, step in enumerate(steps):
                if not step.target:
                    continue
                if step.target.name and step.target.name.lower() == canonical_key:
                    return i
                if step.target.element_id and step.target.element_id.lower() == canonical_key:
                    return i

        for i, step in enumerate(steps):
            step_url = getattr(step, "url", "") or ""
            if step_url and payload.get("url", ""):
                if step_url == payload["url"] or step_url.rstrip("/") == payload["url"].rstrip("/"):
                    return i

        return 0

    @staticmethod
    def _canonical_key(key: str) -> str:
        """Normalize a field key to canonical form."""
        if not key:
            return "unknown"
        k = key.strip().lower()
        k = re.sub(r'^(input|field|txt|inp)[-_]?', '', k)
        k = re.sub(r'[-_\s]+', '_', k)
        return k.strip('_')
