"""TestForge — Component handler registry."""
from __future__ import annotations
from .component_handler import ComponentHandler
from .cdk_overlay import CDKOverlayHandler
from .angular_material import AngularMaterialHandler
from .primeFaces import PrimeFacesHandler

# Order matters: more specific handlers first.
# AngularMaterial before PrimeFaces — both may match generic role/class patterns.
HANDLERS: list[ComponentHandler] = [
    AngularMaterialHandler(),
    PrimeFacesHandler(),
]


def detect_handler(step) -> "ComponentHandler | None":
    """Return the first registered handler that claims ownership of step's target."""
    if not step.target:
        return None
    cands = getattr(step.target, "candidates", None) or []
    candidates = [c.selector for c in cands if getattr(c, "selector", "")]
    element_id = getattr(step.target, "element_id", "") or ""
    tag = getattr(step.target, "tag", "") or ""
    for handler in HANDLERS:
        if handler.detect(candidates, element_id, tag):
            return handler
    return None


__all__ = [
    "ComponentHandler",
    "CDKOverlayHandler",
    "AngularMaterialHandler",
    "PrimeFacesHandler",
    "HANDLERS",
    "detect_handler",
]
