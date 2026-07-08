"""Phase 7: YAML-driven ComponentResolver.

Reads `config/component_patterns.yaml` and dispatches step detection
to the first matching backend handler. Adding a new framework becomes
a YAML change instead of a new Python class — the existing handler
files stay only as execution backends for complex flows.

The legacy `handlers.detect_handler()` and `HANDLERS` registry remain
unchanged so the rest of the codebase keeps working. Opt in to the
YAML-driven path by constructing a ComponentResolver and calling its
`find_handler(step)` method.
"""
from __future__ import annotations

import importlib
import logging
import os
from pathlib import Path
from typing import Any, Optional

import yaml

from .component_handler import ComponentHandler

logger = logging.getLogger(__name__)


_DEFAULT_YAML = (
    Path(__file__).resolve().parent.parent / "config" / "component_patterns.yaml"
)


class ComponentPattern:
    """One detection block read from YAML."""

    __slots__ = ("name", "handler_class", "detect", "_handler_instance")

    def __init__(self, name: str, handler_class: str, detect: dict) -> None:
        self.name = name
        self.handler_class = handler_class
        self.detect = detect or {}
        self._handler_instance: Optional[ComponentHandler] = None

    def matches(self, candidates: list[str], element_id: str, tag: str) -> bool:
        """Apply the detection rules. Returns True at the first hit."""
        tag_low = (tag or "").lower()
        eid = element_id or ""
        eid_low = eid.lower()

        # Per-candidate exclusion: drop any selector that matches.
        skip = self.detect.get("selector_skip_if_contains") or []
        if skip:
            candidates = [s for s in candidates
                          if not any(token in s for token in skip)]

        # ANY-of: a hit on any rule fires the pattern.
        tag_in = self.detect.get("tag_in") or []
        if tag_in and tag_low in {t.lower() for t in tag_in}:
            return True

        id_starts = self.detect.get("element_id_starts_with") or []
        if id_starts and any(eid_low.startswith(p.lower()) for p in id_starts):
            return True

        id_contains = self.detect.get("element_id_contains_any") or []
        if id_contains and any(p.lower() in eid_low for p in id_contains):
            return True

        sel_any = self.detect.get("selector_contains_any") or []
        if sel_any:
            for sel in candidates:
                if any(token in sel for token in sel_any):
                    return True

        sel_any_lower = self.detect.get("selector_contains_any_lower") or []
        if sel_any_lower:
            for sel in candidates:
                sel_l = sel.lower()
                if any(token in sel_l for token in sel_any_lower):
                    return True

        return False

    def get_handler(self) -> ComponentHandler:
        """Lazily import the backend handler class and cache an instance."""
        if self._handler_instance is not None:
            return self._handler_instance
        module_path, _, class_name = self.handler_class.partition(":")
        if not module_path or not class_name:
            raise ValueError(
                f"pattern {self.name!r}: handler_class must be 'module:Class'"
            )
        module = importlib.import_module(module_path)
        cls = getattr(module, class_name)
        self._handler_instance = cls()
        return self._handler_instance


class ComponentResolver:
    """Loads YAML patterns and selects the handler that owns a step."""

    def __init__(self, yaml_path: Optional[os.PathLike] = None) -> None:
        path = Path(yaml_path) if yaml_path else _DEFAULT_YAML
        self._yaml_path = path
        self._patterns: list[ComponentPattern] = []
        self._load()

    def _load(self) -> None:
        if not self._yaml_path.exists():
            logger.warning("component_patterns.yaml not found at %s", self._yaml_path)
            return
        with open(self._yaml_path, encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        for raw in data.get("patterns", []) or []:
            try:
                self._patterns.append(ComponentPattern(
                    name=str(raw["name"]),
                    handler_class=str(raw["handler_class"]),
                    detect=raw.get("detect") or {},
                ))
            except KeyError as exc:
                logger.error("Skipping malformed pattern: missing %s in %r",
                              exc, raw)
        logger.info("ComponentResolver loaded %d patterns from %s",
                     len(self._patterns), self._yaml_path)

    @property
    def pattern_names(self) -> list[str]:
        return [p.name for p in self._patterns]

    def find_handler(self, step) -> Optional[ComponentHandler]:
        """Return the first handler claiming ownership of step's target."""
        if not getattr(step, "target", None):
            return None
        cands = getattr(step.target, "candidates", None) or []
        candidates = [getattr(c, "selector", "") for c in cands
                      if getattr(c, "selector", "")]
        element_id = getattr(step.target, "element_id", "") or ""
        tag = getattr(step.target, "tag", "") or ""
        for pattern in self._patterns:
            if pattern.matches(candidates, element_id, tag):
                return pattern.get_handler()
        return None

    def detect_pattern(self, candidates: list[str], element_id: str, tag: str) -> Optional[str]:
        """Lower-level: return the matching pattern name (for tests / telemetry)."""
        for pattern in self._patterns:
            if pattern.matches(candidates, element_id, tag):
                return pattern.name
        return None
