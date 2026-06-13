"""TestForge — Recording Normalizer.

Converte RawRecordedSession (JSONL) em SemanticTestCase (YAML).
Gera multiplos candidatos de locator ordenados por score deterministico.
"""
import json
import os
from typing import Optional

from .model import LocatorCandidate, SemanticAction, SemanticTarget, SemanticTestCase


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

        # Prioridade de estrategias (score deterministico)
        if target_data.get("role"):
            role = target_data["role"]
            name = target_data.get("accessible_name") or target_data.get("text") or ""
            selector = f"role={role}"
            if name:
                selector += f"[name=\"{name}\"]"
            candidates.append(LocatorCandidate("role", selector, 0.95, "role + accessible name"))

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

        if target_data.get("test_id"):
            tid = target_data["test_id"]
            candidates.append(LocatorCandidate("test_id", f"[data-testid=\"{tid}\"]", 0.80, f"test_id={tid}"))

        if target_data.get("id"):
            el_id = target_data["id"]
            candidates.append(LocatorCandidate("id", f"#{el_id}", 0.75, f"id={el_id}"))

        if target_data.get("name"):
            name = target_data["name"]
            candidates.append(LocatorCandidate("name", f"[name=\"{name}\"]", 0.70, f"name={name}"))

        if target_data.get("text"):
            text = target_data["text"][:50]
            candidates.append(LocatorCandidate("text", f"text={text}", 0.60, f"visible text"))

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
