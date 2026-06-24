"""TestForge — Phase 1: CDP-based snapshots (AX tree + pierced DOM).

Replaces ad-hoc JS-side _extractTarget/_snapshotFields with direct CDP calls:

- `Accessibility.getFullAXTree`   — full accessibility tree (role, name, state,
   backendNodeId per node). Stable across shadow DOM and same-origin iframes.
- `DOM.getDocument(pierce=True)`  — full DOM including shadow roots.

This yields a Playwright MCP-style YAML AX snapshot per event that future
phases (extractor, LLM healer) can consume directly.

We do NOT remove the JS overlay path here. Phase 1 runs both in parallel
under a feature flag; Phase 2 removes the duplicated extraction code from
the overlay JS.
"""
from __future__ import annotations

import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)


class CDPSnapshotter:
    """Wraps a CDPSession for AX-tree + pierced-DOM snapshots.

    One snapshotter per page. Re-uses a single CDP session for the life
    of the recording. Cheaper than spinning a session per event.
    """

    def __init__(self, page) -> None:
        self._page = page
        self._session = None
        self._enabled = False

    def attach(self) -> bool:
        """Create the CDP session and enable required domains. Idempotent."""
        if self._enabled:
            return True
        try:
            ctx = self._page.context
            self._session = ctx.new_cdp_session(self._page)
            self._session.send("DOM.enable")
            self._session.send("Accessibility.enable")
            self._enabled = True
            logger.info("CDP session attached and AX/DOM domains enabled")
            return True
        except Exception as exc:
            logger.warning("CDPSnapshotter.attach failed: %s", exc)
            self._session = None
            self._enabled = False
            return False

    def detach(self) -> None:
        if not self._enabled or not self._session:
            return
        try:
            self._session.detach()
        except Exception:
            pass
        self._enabled = False
        self._session = None

    def get_full_ax_tree(self) -> Optional[dict]:
        """Return the full accessibility tree as a CDP-shaped dict.

        Shape (CDP `Accessibility.getFullAXTree`):
            { "nodes": [ { "nodeId", "role": {"value": "..."}, "name": {"value": "..."},
                           "backendDOMNodeId", "parentId", "childIds", "properties": [...] }, ... ] }
        """
        if not self._enabled or not self._session:
            return None
        try:
            result = self._session.send("Accessibility.getFullAXTree")
            return result
        except Exception as exc:
            logger.debug("getFullAXTree failed: %s", exc)
            return None

    def get_pierced_dom(self, depth: int = -1) -> Optional[dict]:
        """Return full DOM including shadow roots. Heavy — use sparingly."""
        if not self._enabled or not self._session:
            return None
        try:
            return self._session.send("DOM.getDocument", {"pierce": True, "depth": depth})
        except Exception as exc:
            logger.debug("DOM.getDocument failed: %s", exc)
            return None

    def serialize_ax_yaml(self, ax_tree: dict) -> str:
        """Render the AX tree as Playwright MCP-style YAML with [ref=eN].

        This is the format the L3 LLM healer consumes directly in Phase 2.
        Skips ignored nodes and uses 2-space indentation.
        """
        if not ax_tree or "nodes" not in ax_tree:
            return ""
        nodes = ax_tree["nodes"]
        by_id = {n.get("nodeId"): n for n in nodes if n.get("nodeId")}
        roots = [n for n in nodes if not n.get("parentId")]
        ref_counter = {"n": 0}
        lines: list[str] = []

        def next_ref() -> str:
            ref_counter["n"] += 1
            return f"e{ref_counter['n']}"

        def emit(node: dict, indent: int) -> None:
            if node.get("ignored"):
                # walk children of ignored nodes (transparent)
                for cid in node.get("childIds", []) or []:
                    child = by_id.get(cid)
                    if child:
                        emit(child, indent)
                return
            role_obj = node.get("role") or {}
            name_obj = node.get("name") or {}
            role = role_obj.get("value", "?")
            name = name_obj.get("value", "")
            ref = next_ref()
            label = f'- {role} [ref={ref}]'
            if name:
                clean = name.replace("\n", " ").strip()[:120]
                if clean:
                    label += f' "{clean}"'
            lines.append("  " * indent + label)
            for cid in node.get("childIds", []) or []:
                child = by_id.get(cid)
                if child:
                    emit(child, indent + 1)

        for root in roots:
            emit(root, 0)
        return "\n".join(lines)

    def find_node_by_backend_id(self, ax_tree: dict, backend_node_id: int) -> Optional[dict]:
        """Locate an AX node by its CDP backendDOMNodeId."""
        if not ax_tree or "nodes" not in ax_tree:
            return None
        for n in ax_tree["nodes"]:
            if n.get("backendDOMNodeId") == backend_node_id:
                return n
        return None

    def ancestor_roles(self, ax_tree: dict, node_id: str, limit: int = 5) -> list[str]:
        """Return list of ancestor roles (closest first) for an AX node."""
        if not ax_tree or "nodes" not in ax_tree:
            return []
        by_id = {n.get("nodeId"): n for n in ax_tree["nodes"]}
        out: list[str] = []
        cur = by_id.get(node_id)
        steps = 0
        while cur and steps < limit:
            parent_id = cur.get("parentId")
            if not parent_id:
                break
            parent = by_id.get(parent_id)
            if not parent:
                break
            role_obj = parent.get("role") or {}
            role = role_obj.get("value")
            if role:
                out.append(role)
            cur = parent
            steps += 1
        return out
