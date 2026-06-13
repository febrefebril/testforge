"""TestForge — Failure Taxonomy."""
from dataclasses import dataclass
from enum import Enum


class FailureFamily(str, Enum):
    LOCATOR_RESOLUTION = "locator_resolution"
    ACTIONABILITY = "actionability"
    SYNCHRONIZATION = "synchronization"
    ORACLE = "oracle"
    ENVIRONMENT = "environment"
    CONTEXT = "context"


@dataclass
class FailureClassification:
    family: FailureFamily
    code: str
    description: str = ""
    recoverable: bool = True
    suggested_strategy: str = ""


# Catalogo de falhas conhecidas
KNOWN_FAILURES = {
    # Locator
    "LOCATOR_NOT_FOUND": FailureClassification(
        FailureFamily.LOCATOR_RESOLUTION, "LOCATOR_NOT_FOUND",
        "Elemento nao encontrado com o seletor atual",
        recoverable=True, suggested_strategy="fallback_candidates"
    ),
    "LOCATOR_AMBIGUOUS": FailureClassification(
        FailureFamily.LOCATOR_RESOLUTION, "LOCATOR_AMBIGUOUS",
        "Multiplos elementos correspondem ao seletor",
        recoverable=True, suggested_strategy="contextual_disambiguation"
    ),
    "ID_CHANGED": FailureClassification(
        FailureFamily.LOCATOR_RESOLUTION, "ID_CHANGED",
        "ID do elemento foi regenerado",
        recoverable=True, suggested_strategy="fallback_role_or_text"
    ),
    # Actionability
    "ACTIONABILITY_OBSCURED": FailureClassification(
        FailureFamily.ACTIONABILITY, "ACTIONABILITY_OBSCURED",
        "Elemento coberto por overlay ou outro elemento",
        recoverable=True, suggested_strategy="wait_and_retry"
    ),
    "ACTIONABILITY_DISABLED": FailureClassification(
        FailureFamily.ACTIONABILITY, "ACTIONABILITY_DISABLED",
        "Elemento esta desabilitado",
        recoverable=True, suggested_strategy="wait_for_enabled"
    ),
    "ACTIONABILITY_NOT_VISIBLE": FailureClassification(
        FailureFamily.ACTIONABILITY, "ACTIONABILITY_NOT_VISIBLE",
        "Elemento fora do viewport ou hidden",
        recoverable=True, suggested_strategy="scroll_into_view"
    ),
    # Timing
    "TIMEOUT": FailureClassification(
        FailureFamily.SYNCHRONIZATION, "TIMEOUT",
        "Timeout esperando elemento ou acao",
        recoverable=True, suggested_strategy="increase_wait"
    ),
    "RACE_CONDITION": FailureClassification(
        FailureFamily.SYNCHRONIZATION, "RACE_CONDITION",
        "Elemento apareceu/destruido durante interacao",
        recoverable=True, suggested_strategy="retry_with_polling"
    ),
    # Oracle
    "ORACLE_FAILED": FailureClassification(
        FailureFamily.ORACLE, "ORACLE_FAILED",
        "Oracle pos-acao falhou — resultado inesperado",
        recoverable=False, suggested_strategy="human_review"
    ),
    # Environment
    "NETWORK_ERROR": FailureClassification(
        FailureFamily.ENVIRONMENT, "NETWORK_ERROR",
        "Erro de rede ou servidor indisponivel",
        recoverable=True, suggested_strategy="retry"
    ),
}


class FailureClassifier:
    """Classifica falhas de execucao na taxonomia."""

    def classify(self, error_message: str, element_info: dict = None) -> FailureClassification:
        msg_lower = error_message.lower()
        element_info = element_info or {}

        if "not found" in msg_lower or "locator" in msg_lower:
            if element_info.get("count", 0) == 0:
                return KNOWN_FAILURES["LOCATOR_NOT_FOUND"]
            if element_info.get("count", 0) > 1:
                return KNOWN_FAILURES["LOCATOR_AMBIGUOUS"]
            if "id" in msg_lower:
                return KNOWN_FAILURES["ID_CHANGED"]
            return KNOWN_FAILURES["LOCATOR_NOT_FOUND"]

        if "overlay" in msg_lower or "obscured" in msg_lower or "intercept" in msg_lower:
            return KNOWN_FAILURES["ACTIONABILITY_OBSCURED"]

        if "disabled" in msg_lower or "not enabled" in msg_lower:
            return KNOWN_FAILURES["ACTIONABILITY_DISABLED"]

        if "not visible" in msg_lower or "viewport" in msg_lower:
            return KNOWN_FAILURES["ACTIONABILITY_NOT_VISIBLE"]

        if "timeout" in msg_lower:
            return KNOWN_FAILURES["TIMEOUT"]

        if "race" in msg_lower or "stale" in msg_lower:
            return KNOWN_FAILURES["RACE_CONDITION"]

        if "oracle" in msg_lower or "assertion" in msg_lower:
            return KNOWN_FAILURES["ORACLE_FAILED"]

        if "network" in msg_lower or "connection" in msg_lower or "refused" in msg_lower:
            return KNOWN_FAILURES["NETWORK_ERROR"]

        return FailureClassification(
            FailureFamily.CONTEXT, "UNKNOWN",
            f"Falha nao classificada: {error_message[:100]}",
            recoverable=True, suggested_strategy="llm_fallback"
        )
