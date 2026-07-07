"""PII detector — observability layer.

Detects sensitive data patterns in recorded values without modifying them.
Returns PiiHit list for reporting. Values are preserved as-is.

Contract: feedback-pii-alert-only. Never mask, never redact.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Iterable, Optional
from urllib.parse import parse_qsl, urlparse


class Severity(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class PiiPattern(str, Enum):
    CPF = "cpf"
    CNPJ = "cnpj"
    EMAIL = "email"
    PHONE_BR = "phone_br"
    MATRICULA_CAIXA = "matricula_caixa"
    FULL_NAME = "full_name"
    CORP_FILENAME = "corp_filename"
    PASSWORD = "password"
    PIN = "pin"
    KEYCLOAK_SESSION = "keycloak_session"
    PRODUCTION_DOMAIN = "production_domain"


@dataclass
class PiiHit:
    pattern: PiiPattern
    value: str  # preserved verbatim (NEVER masked)
    severity: Severity
    context: str = ""
    match_start: int = -1
    match_end: int = -1

    def as_alert_entry(self) -> dict:
        """Format for evidence_collector.add_sensitive_alert (dict-based)."""
        return {
            "pattern": self.pattern.value,
            "severity": self.severity.value,
            "context": self.context,
            "value_preview": self._preview(),
            "policy": "alert_only",
            "masking_applied": False,
        }

    def _preview(self) -> str:
        """Preview for logs/reports — first N chars. Full value stays in artifact."""
        if len(self.value) <= 32:
            return self.value
        return self.value[:29] + "..."


# Compiled patterns (module-level for perf)
_CPF_RE = re.compile(r"(?<!\d)\d{3}\.?\d{3}\.?\d{3}-?\d{2}(?!\d)")
# CNPJ: match anywhere. Concatenated CNPJs (from <select> textContent bug)
# are handled by re-scanning after each hit.
_CNPJ_RE = re.compile(r"(?<!\d)\d{2}\.?\d{3}\.?\d{3}/?\d{4}-?\d{2}")
_EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
_PHONE_BR_RE = re.compile(
    # Only match when phone has explicit separator: parens, hyphen, or space.
    # Prevents 11-digit CPFs unformatted from matching.
    r"(?:\(\d{2}\)|\d{2})[\s-]?\d{4,5}[\s-]\d{4}"
)
_MATRICULA_CAIXA_RE = re.compile(r"\bc\d{5,7}\b", re.IGNORECASE)
# Corporate filename: e.g. CNT.EMP.MZ.BMX0.PRONAMPE.D260625.R4
_CORP_FILENAME_RE = re.compile(
    r"\b[A-Z]{2,}(?:\.[A-Z0-9]+){2,}\.D\d{6,8}(?:\.[A-Z0-9]+)?\b"
)
# Full name: 2+ words, each with initial cap (heuristic — reports LOW severity)
_FULL_NAME_RE = re.compile(
    r"\b[A-ZÀ-Ú][a-zà-ú]+(?:\s+[A-ZÀ-Ú][a-zà-ú]+){1,4}\b"
)
# Keycloak SSO sensitive params
_KEYCLOAK_PARAMS = {
    "state",
    "nonce",
    "code",
    "code_challenge",
    "session_state",
    "execution",
    "session_code",
}
# Production domains: caixa.gov.br sem sufixo -des/-tqs/-hom
_PROD_DOMAIN_RE = re.compile(
    r"^(?!.*-(?:des|tqs|hom|dev|homolog)).*\.caixa\.gov\.br(?:/|$)"
)
# Weak password heuristics (dictionary + digits)
_WEAK_PW_HINTS = (
    "senha",
    "password",
    "pass",
    "pwd",
    "pin",
    "matricula",
    "matrícula",
)


def detect(
    value: Any,
    context: str = "",
    field_metadata: Optional[dict] = None,
) -> list[PiiHit]:
    """Detect PII patterns in `value` without modifying it.

    Args:
        value: value to scan. Non-str coerced via str().
        context: source location (e.g. "raw_events.evt_00005", "steps.step_0003").
        field_metadata: optional dict with hints — type, name, placeholder, label,
                        paste (bool), aria_label, etc. Used for password detection.

    Returns:
        List of PiiHit. Empty if nothing detected.
    """
    if value is None:
        return []
    s = value if isinstance(value, str) else str(value)
    if not s:
        return []

    hits: list[PiiHit] = []
    md = field_metadata or {}

    # Password field (metadata-driven — content itself not scanned for structure)
    if _is_password_field(md):
        hits.append(
            PiiHit(
                pattern=PiiPattern.PASSWORD,
                value=s,
                severity=Severity.CRITICAL,
                context=context,
            )
        )

    # PIN heuristic: numeric-only, 4-8 chars, in field labeled password/pin
    if s.isdigit() and 4 <= len(s) <= 8 and _mentions_pw_hint(md):
        hits.append(
            PiiHit(
                pattern=PiiPattern.PIN,
                value=s,
                severity=Severity.CRITICAL,
                context=context,
            )
        )

    # Structural patterns (regex over value)
    for match in _CPF_RE.finditer(s):
        hits.append(
            PiiHit(
                pattern=PiiPattern.CPF,
                value=match.group(0),
                severity=Severity.HIGH,
                context=context,
                match_start=match.start(),
                match_end=match.end(),
            )
        )
    # CNPJ: iterate manually to handle concatenated CNPJs from <select> bug
    pos = 0
    while pos < len(s):
        m = _CNPJ_RE.search(s, pos)
        if not m:
            break
        # Skip if overlaps with existing CPF hit
        if not any(h.match_start <= m.start() < h.match_end for h in hits):
            hits.append(
                PiiHit(
                    pattern=PiiPattern.CNPJ,
                    value=m.group(0),
                    severity=Severity.HIGH,
                    context=context,
                    match_start=m.start(),
                    match_end=m.end(),
                )
            )
        pos = m.end()  # advance past this match; allow next match to start
        # from adjacent digit (concatenated CNPJs)
        # Override the (?<!\d) restriction by NOT using search from pos.
        # Use manual advance: check if next char is start of another CNPJ
        # by looking for lookahead of CNPJ pattern without (?<!\d) constraint.
        if pos < len(s) and s[pos].isdigit():
            # Try to match starting exactly at pos (adjacent CNPJ case)
            _adj_re = re.compile(r"\d{2}\.?\d{3}\.?\d{3}/?\d{4}-?\d{2}")
            m2 = _adj_re.match(s, pos)
            if m2:
                if not any(h.match_start <= m2.start() < h.match_end for h in hits):
                    hits.append(
                        PiiHit(
                            pattern=PiiPattern.CNPJ,
                            value=m2.group(0),
                            severity=Severity.HIGH,
                            context=context,
                            match_start=m2.start(),
                            match_end=m2.end(),
                        )
                    )
                pos = m2.end()
    for match in _EMAIL_RE.finditer(s):
        hits.append(
            PiiHit(
                pattern=PiiPattern.EMAIL,
                value=match.group(0),
                severity=Severity.MEDIUM,
                context=context,
                match_start=match.start(),
                match_end=match.end(),
            )
        )
    for match in _PHONE_BR_RE.finditer(s):
        # Skip if overlaps with CPF/CNPJ hit (11-digit CPFs can look like phones)
        if any(
            h.match_start <= match.start() < h.match_end
            for h in hits
            if h.pattern in (PiiPattern.CPF, PiiPattern.CNPJ)
        ):
            continue
        hits.append(
            PiiHit(
                pattern=PiiPattern.PHONE_BR,
                value=match.group(0),
                severity=Severity.MEDIUM,
                context=context,
                match_start=match.start(),
                match_end=match.end(),
            )
        )
    for match in _MATRICULA_CAIXA_RE.finditer(s):
        hits.append(
            PiiHit(
                pattern=PiiPattern.MATRICULA_CAIXA,
                value=match.group(0),
                severity=Severity.HIGH,
                context=context,
                match_start=match.start(),
                match_end=match.end(),
            )
        )
    for match in _CORP_FILENAME_RE.finditer(s):
        hits.append(
            PiiHit(
                pattern=PiiPattern.CORP_FILENAME,
                value=match.group(0),
                severity=Severity.HIGH,
                context=context,
                match_start=match.start(),
                match_end=match.end(),
            )
        )

    return hits


def url_scan(url: str, context: str = "") -> list[PiiHit]:
    """Scan URL for sensitive query params (Keycloak SSO tokens).

    Returns hits without modifying the URL.
    """
    if not url:
        return []
    hits: list[PiiHit] = []
    try:
        parsed = urlparse(url)
        for key, val in parse_qsl(parsed.query, keep_blank_values=True):
            if key.lower() in _KEYCLOAK_PARAMS and val:
                hits.append(
                    PiiHit(
                        pattern=PiiPattern.KEYCLOAK_SESSION,
                        value=f"{key}={val}",
                        severity=Severity.HIGH,
                        context=context,
                    )
                )
    except Exception:
        pass
    return hits


def is_production_domain(url: str) -> Optional[PiiHit]:
    """Detect production CAIXA domain.

    Returns PiiHit(severity=CRITICAL) if URL points to production
    (caixa.gov.br without -des/-tqs/-hom suffix). None otherwise.
    """
    if not url:
        return None
    try:
        host = urlparse(url).hostname or ""
        if _PROD_DOMAIN_RE.match(f"{host}/"):
            return PiiHit(
                pattern=PiiPattern.PRODUCTION_DOMAIN,
                value=host,
                severity=Severity.CRITICAL,
                context="base_url",
            )
    except Exception:
        pass
    return None


def _is_password_field(md: dict) -> bool:
    if md.get("type") == "password":
        return True
    if md.get("paste") is True and _mentions_pw_hint(md):
        return True
    return False


def _mentions_pw_hint(md: dict) -> bool:
    if not md:
        return False
    haystack = " ".join(
        str(md.get(k, "")).lower()
        for k in ("placeholder", "label", "name", "aria_label", "element_id")
    )
    return any(hint in haystack for hint in _WEAK_PW_HINTS)
