"""TestForge — Actionability Validator.

Pre-action validation: visible, enabled, area > 0.
Rejects elements with bounding box width=height=0.
"""

from .actionability_validator import ActionabilityValidator, ActionabilityResult

__all__ = ["ActionabilityValidator", "ActionabilityResult"]
