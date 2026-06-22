from __future__ import annotations

import logging
import os
import re
from dataclasses import dataclass, field
from typing import Optional

from testforge.core.healing.collector import EvidencePayload
from testforge.core.healing.models import FAMILIES, TAXONOMIES

logger = logging.getLogger("testforge.healing.classifier")


@dataclass
class ClassificationResult:
    taxonomy_id: str = ""
    family: str = ""
    confidence: float = 0.0
    symptom: str = ""
    matched_by: str = ""


KEYWORD_MAP: list[tuple[str, str, str, str]] = [
    ("strict locator", "FAM-01", "SEL-001", "strict locator violation"),
    ("intercepted", "FAM-01", "SEL-002", "click intercepted"),
    ("multiple elements", "FAM-01", "SEL-009", "multiple elements match"),
    ("timeout", "FAM-01", "SEL-004", "element not found timeout"),
    ("loading", "FAM-02", "TIM-001", "page still loading"),
    ("stale element", "FAM-02", "TIM-002", "stale element reference"),
    ("net::ERR", "FAM-02", "TIM-003", "network error"),
    ("wait", "FAM-02", "TIM-005", "wait timeout"),
    ("fill", "FAM-06", "INP-001", "fill operation failed"),
    ("clear", "FAM-06", "INP-002", "clear operation failed"),
    ("editable", "FAM-06", "INP-003", "element not editable"),
    ("masked", "FAM-06", "INP-007", "masked input detection"),
    ("frame", "FAM-03", "CTX-001", "iframe context issue"),
    ("shadow", "FAM-03", "CTX-002", "shadow DOM context issue"),
    ("cross-origin", "FAM-03", "CTX-003", "cross-origin iframe"),
    ("dialog", "FAM-04", "STA-004", "unexpected dialog"),
    ("alert", "FAM-04", "STA-004", "unexpected alert"),
    ("confirm", "FAM-04", "STA-004", "unexpected confirm"),
    ("session", "FAM-04", "STA-005", "session expired"),
    ("overlay", "FAM-04", "STA-006", "overlay blocking element"),
    ("file", "FAM-07", "FILE-001", "file upload issue"),
    ("upload", "FAM-07", "FILE-001", "file upload failed"),
    ("download", "FAM-07", "FILE-004", "file download failed"),
    ("assertionerror", "FAM-08", "AST-001", "assertion failed"),
    ("assert", "FAM-08", "AST-001", "assertion failed"),
    ("expect", "FAM-08", "AST-001", "expect assertion failed"),
    ("not found", "FAM-01", "SEL-004", "element not found"),
    ("404", "FAM-02", "TIM-003", "resource not found"),
    ("500", "FAM-02", "TIM-003", "internal server error"),
]


PATTERN_GROUPS: dict[str, tuple[str, str, str]] = {
    "SEL": ("FAM-01", "SEL-004", "selector error pattern"),
    "TIM": ("FAM-02", "TIM-005", "timing error pattern"),
    "INP": ("FAM-06", "INP-001", "input error pattern"),
    "CTX": ("FAM-03", "CTX-001", "context error pattern"),
    "STA": ("FAM-04", "STA-004", "state error pattern"),
}


class FailureClassifier:
    def __init__(self, llm_healer=None):
        self._llm_healer = llm_healer

    def classify(
        self,
        error_message: str,
        evidence: Optional[EvidencePayload] = None,
    ) -> ClassificationResult:
        if not error_message:
            return ClassificationResult(
                taxonomy_id="",
                family="",
                confidence=0.0,
                symptom="empty error message",
                matched_by="",
            )

        result = self._classify_by_keyword(error_message)
        if result is not None:
            return result

        result = self._classify_by_group(error_message)
        if result is not None:
            return result

        result = self._classify_llm(error_message, evidence)
        if result is not None:
            return result

        return ClassificationResult(
            taxonomy_id="",
            family="",
            confidence=0.0,
            symptom=f"unclassified: {error_message[:200]}",
            matched_by="",
        )

    def _classify_by_keyword(self, error_message: str) -> Optional[ClassificationResult]:
        msg_lower = error_message.lower()
        best: Optional[tuple[int, str, str, str, str, int]] = None
        sorted_kw = sorted(KEYWORD_MAP, key=lambda x: len(x[0]), reverse=True)
        for keyword, family, tid, symptom in sorted_kw:
            kw_lower = keyword.lower()
            pos = msg_lower.find(kw_lower)
            if pos < 0:
                continue
            if pos > 0 and msg_lower[pos - 1].isalnum():
                continue
            end = pos + len(kw_lower)
            if end < len(msg_lower) and msg_lower[end].isalnum():
                continue
            length = len(kw_lower)
            if best is None or pos < best[0] or (pos == best[0] and length > best[5]):
                best = (pos, family, tid, symptom, keyword, length)
        if best is not None:
            _, family, tid, symptom, keyword, _ = best
            return ClassificationResult(
                taxonomy_id=tid,
                family=family,
                confidence=0.9,
                symptom=symptom,
                matched_by="regex",
            )
        return None

    def _classify_by_group(self, error_message: str) -> Optional[ClassificationResult]:
        for prefix, (family, tid, symptom) in PATTERN_GROUPS.items():
            pattern = self._build_group_pattern(prefix)
            if re.search(pattern, error_message, re.IGNORECASE):
                return ClassificationResult(
                    taxonomy_id=tid,
                    family=family,
                    confidence=0.7,
                    symptom=symptom,
                    matched_by="regex",
                )
        return None

    def _build_group_pattern(self, prefix: str) -> str:
        if prefix == "SEL":
            return r"(timeout.*locator|strict locator|intercepted|multiple elements)"
        if prefix == "TIM":
            return r"(loading|stale element|net::ERR_|timeout|wait)"
        if prefix == "INP":
            return r"(fill|clear|editable|masked)"
        if prefix == "CTX":
            return r"(frame|shadow|cross-origin)"
        if prefix == "STA":
            return r"(dialog|alert|confirm|session|overlay)"
        return r"(.*)"

    def _build_llm_fallback_prompt(
        self,
        error_message: str,
        evidence: Optional[EvidencePayload],
    ) -> str:
        dom_snippet = ""
        if evidence and evidence.dom_snapshot:
            dom_snippet = evidence.dom_snapshot[:500]

        action = ""
        selector = ""
        if evidence and evidence.step_context:
            action = evidence.step_context.get("action", "")
            selector = evidence.step_context.get("selector", "")

        families_str = ", ".join(f"{k}={v}" for k, v in sorted(FAMILIES.items()))
        lines = [
            "Classifique esta falha de teste em um ID taxonômico.",
            "Responda JSON: {\"family\": \"FAM-XX\", \"taxonomy_id\": \"XXX-000\", \"confidence\": 0.X}",
            "",
            f"Erro: {error_message[:300]}",
        ]
        if dom_snippet:
            lines.append(f"DOM: {dom_snippet}")
        if action:
            lines.append(f"Ação: {action} | Seletor: {selector}")
        lines.append(f"Famílias: {families_str}")
        return "\n".join(lines)

    def _classify_llm(
        self,
        error_message: str,
        evidence: Optional[EvidencePayload],
    ) -> Optional[ClassificationResult]:
        if not self._llm_healer:
            return None
        if not evidence:
            return None
        try:
            proposal = self._llm_healer.heal_or_unresolved(evidence, error_message)
            if proposal.confidence < 0.5:
                return None
            if proposal.family in FAMILIES and proposal.taxonomy_id in TAXONOMIES.get(proposal.family, []):
                return ClassificationResult(
                    taxonomy_id=proposal.taxonomy_id,
                    family=proposal.family,
                    confidence=proposal.confidence,
                    symptom=f"LLM fallback: {error_message[:100]}",
                    matched_by="llm",
                )
        except Exception as e:
            logger.debug("LLM classification fallback failed: %s", e)
        return None
