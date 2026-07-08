"""TestForge — Component handler registry."""
from __future__ import annotations
from .component_handler import ComponentHandler
from .cdk_overlay import CDKOverlayHandler
from .angular_material import AngularMaterialHandler
from .primeFaces import PrimeFacesHandler
from .react_mui import ReactMUIHandler

# Order matters: more specific handlers first.
# AngularMaterial before PrimeFaces/MUI — mat-* selectors are unambiguous.
# PrimeFaces before ReactMUI — ui-* class names are PF-specific.
HANDLERS: list[ComponentHandler] = [
    AngularMaterialHandler(),
    PrimeFacesHandler(),
    ReactMUIHandler(),
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
    "ReactMUIHandler",
    "HANDLERS",
    "detect_handler",
]
