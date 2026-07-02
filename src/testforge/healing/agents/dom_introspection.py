"""DOM/context helper checks used by specialist healing agents."""


def dom_has_role(payload, role: str) -> bool:
    """True when dom_snapshot contains the requested ARIA role."""
    snap = (getattr(payload, "dom_snapshot", "") or "").lower()
    role_norm = (role or "").strip().lower()
    if not snap or not role_norm:
        return False
    return f'role="{role_norm}"' in snap or f"role='{role_norm}'" in snap


def dom_has_mask_attrs(payload) -> bool:
    """True when dom_snapshot indicates typical mask attributes/libraries."""
    snap = (getattr(payload, "dom_snapshot", "") or "").lower()
    if not snap:
        return False
    for attr in (
        "currencymask",
        "imask",
        "data-mask",
        "ng-currency",
        "mat-input-mask",
        "cleavezone",
    ):
        if attr in snap:
            return True
    return False


def dom_has_dialog_handler(payload) -> bool:
    """True when runtime context says a dialog handler has been registered."""
    page_state = getattr(payload, "page_state", {}) or {}
    return bool(page_state.get("has_dialog_handler"))
