"""TestForge security observability layer.

Detects sensitive data (PII, credentials, corporate identifiers, SSO tokens)
in recording artifacts. **Detection-only** — values are NEVER masked or
redacted. Sensitive data IS the test payload; masking would break replay.

Policy default: alert_only (see .testforge/pii_policy.yaml).
Contract: [[feedback-pii-alert-only]].
"""
from .pii_detector import PiiHit, PiiPattern, detect, url_scan, is_production_domain

__all__ = ["PiiHit", "PiiPattern", "detect", "url_scan", "is_production_domain"]
