"""TestForge — Failure Taxonomy (11 families, 80+ codes).

Keyword matching + regex group fallback + word-boundary verification.
LLM fallback placeholder for future L3 integration.
"""
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


# ── Families ──────────────────────────────────────────────────────────────

class FailureFamily(str, Enum):
    LOCATOR_RESOLUTION = "locator_resolution"
    SYNCHRONIZATION = "synchronization"
    CONTEXT_SCOPE = "context"
    STATE = "state"
    DYNAMIC_DOM = "dynamic_dom"
    INPUT = "input"
    FILE = "file"
    ASSERT = "assert"
    RECORDER = "recorder"
    EXECUTION = "execution"
    BROWSER_LIMITS = "browser_limits"


FAMILY_MAP: dict[str, str] = {
    "locator_resolution": "FAM-01",
    "synchronization": "FAM-02",
    "context": "FAM-03",
    "state": "FAM-04",
    "dynamic_dom": "FAM-05",
    "input": "FAM-06",
    "file": "FAM-07",
    "assert": "FAM-08",
    "recorder": "FAM-09",
    "execution": "FAM-10",
    "browser_limits": "FAM-11",
}

FAMILIES: dict[str, str] = {
    "FAM-01": "locator_resolution",
    "FAM-02": "synchronization",
    "FAM-03": "context",
    "FAM-04": "state",
    "FAM-05": "dynamic_dom",
    "FAM-06": "input",
    "FAM-07": "file",
    "FAM-08": "assert",
    "FAM-09": "recorder",
    "FAM-10": "execution",
    "FAM-11": "browser_limits",
}


# ── Taxonomy Codes ────────────────────────────────────────────────────────

TAXONOMIES: dict[str, list[str]] = {
    "FAM-01": ["SEL-001", "SEL-002", "SEL-003", "SEL-004", "SEL-005",
               "SEL-006", "SEL-007", "SEL-008", "SEL-009", "SEL-010"],
    "FAM-02": ["TIM-001", "TIM-002", "TIM-003", "TIM-004", "TIM-005",
               "TIM-006", "TIM-007"],
    "FAM-03": ["CTX-001", "CTX-002", "CTX-003", "CTX-004", "CTX-005",
               "CTX-006", "CTX-007"],
    "FAM-04": ["STA-001", "STA-002", "STA-003", "STA-004", "STA-005",
               "STA-006"],
    "FAM-05": ["DOM-001", "DOM-002", "DOM-003", "DOM-004", "DOM-005"],
    "FAM-06": ["INP-001", "INP-002", "INP-003", "INP-004", "INP-005",
               "INP-006", "INP-007", "INP-008", "INP-009", "INP-010"],
    "FAM-07": ["FILE-001", "FILE-002", "FILE-003", "FILE-004", "FILE-005",
               "FILE-006"],
    "FAM-08": ["AST-001", "AST-002", "AST-003", "AST-004", "AST-005",
               "AST-006", "AST-007", "AST-008", "AST-009", "AST-010"],
    "FAM-09": ["REC-001", "REC-002", "REC-003", "REC-004", "REC-005",
               "REC-006"],
    "FAM-10": ["OBS-001", "OBS-002", "OBS-003", "OBS-004", "OBS-005",
               "OBS-006"],
    "FAM-11": ["LIM-001", "LIM-002", "LIM-003", "LIM-004", "LIM-005"],
}


# ── Failure Classification ────────────────────────────────────────────────

@dataclass
class FailureClassification:
    family: FailureFamily
    code: str = ""
    taxonomy_id: str = ""
    description: str = ""
    recoverable: bool = True
    suggested_strategy: str = ""
    confidence: float = 0.0
    matched_by: str = ""  # "keyword", "group", "llm", ""

    @property
    def family_code(self) -> str:
        return FAMILY_MAP.get(self.family.value, "")


# ── Known Failures Catalog ────────────────────────────────────────────────

KNOWN_FAILURES: dict[str, FailureClassification] = {
    # FAM-01: Locator Resolution
    "SEL-001": FailureClassification(
        FailureFamily.LOCATOR_RESOLUTION, "SEL-001", "SEL-001",
        "ID JSF/PrimeFaces dinamico (j_idt, indice variavel)",
        recoverable=True, suggested_strategy="semantic_locator_conversion",
    ),
    "SEL-002": FailureClassification(
        FailureFamily.LOCATOR_RESOLUTION, "SEL-002", "SEL-002",
        "ID com indice de tabela — acao aponta para linha errada",
        recoverable=True, suggested_strategy="label_proximity",
    ),
    "SEL-003": FailureClassification(
        FailureFamily.LOCATOR_RESOLUTION, "SEL-003", "SEL-003",
        "widgetVar instavel — PF('x') quebrou",
        recoverable=True, suggested_strategy="primefaces_registry_scan",
    ),
    "SEL-004": FailureClassification(
        FailureFamily.LOCATOR_RESOLUTION, "SEL-004", "SEL-004",
        "XPath absoluto quebrou com mudanca estrutural",
        recoverable=True, suggested_strategy="semantic_locator_conversion",
    ),
    "SEL-005": FailureClassification(
        FailureFamily.LOCATOR_RESOLUTION, "SEL-005", "SEL-005",
        "Classe CSS volatil/hash — elemento nao encontrado",
        recoverable=True, suggested_strategy="aria_role_strategy",
    ),
    "SEL-006": FailureClassification(
        FailureFamily.LOCATOR_RESOLUTION, "SEL-006", "SEL-006",
        "Elemento sem ID/name — locator generico",
        recoverable=True, suggested_strategy="aria_role_strategy",
    ),
    "SEL-007": FailureClassification(
        FailureFamily.LOCATOR_RESOLUTION, "SEL-007", "SEL-007",
        "Elemento fora do formulario — modal/dialog",
        recoverable=True, suggested_strategy="aria_role_strategy",
    ),
    "SEL-008": FailureClassification(
        FailureFamily.LOCATOR_RESOLUTION, "SEL-008", "SEL-008",
        "Locator por posicao (.nth()) quebrou com reordenacao",
        recoverable=True, suggested_strategy="semantic_locator_conversion",
    ),
    "SEL-009": FailureClassification(
        FailureFamily.LOCATOR_RESOLUTION, "SEL-009", "SEL-009",
        "Texto duplicado — multiplos elementos com mesmo texto",
        recoverable=True, suggested_strategy="label_proximity",
    ),
    "SEL-010": FailureClassification(
        FailureFamily.LOCATOR_RESOLUTION, "SEL-010", "SEL-010",
        "Label nao associado via for — campo nao localizado",
        recoverable=True, suggested_strategy="label_proximity",
    ),
    # Legacy aliases (backward compat)
    "LOCATOR_NOT_FOUND": FailureClassification(
        FailureFamily.LOCATOR_RESOLUTION, "LOCATOR_NOT_FOUND", "SEL-004",
        "Elemento nao encontrado com o seletor atual",
        recoverable=True, suggested_strategy="semantic_locator_conversion",
    ),
    "LOCATOR_AMBIGUOUS": FailureClassification(
        FailureFamily.LOCATOR_RESOLUTION, "LOCATOR_AMBIGUOUS", "SEL-009",
        "Multiplos elementos correspondem ao seletor",
        recoverable=True, suggested_strategy="label_proximity",
    ),
    "ID_CHANGED": FailureClassification(
        FailureFamily.LOCATOR_RESOLUTION, "ID_CHANGED", "SEL-001",
        "ID do elemento foi regenerado",
        recoverable=True, suggested_strategy="semantic_locator_conversion",
    ),

    # FAM-02: Synchronization
    "TIM-001": FailureClassification(
        FailureFamily.SYNCHRONIZATION, "TIM-001", "TIM-001",
        "Acao antes do re-render JSF AJAX",
        recoverable=True, suggested_strategy="network_idle_wait",
    ),
    "TIM-002": FailureClassification(
        FailureFamily.SYNCHRONIZATION, "TIM-002", "TIM-002",
        "ViewState invalido — submissao falhou",
        recoverable=True, suggested_strategy="skip_viewstate",
    ),
    "TIM-003": FailureClassification(
        FailureFamily.SYNCHRONIZATION, "TIM-003", "TIM-003",
        "Callback jQuery sem evento DOM claro",
        recoverable=True, suggested_strategy="response_intercept",
    ),
    "TIM-004": FailureClassification(
        FailureFamily.SYNCHRONIZATION, "TIM-004", "TIM-004",
        "Change detection assincrono — assert le valor antigo",
        recoverable=True, suggested_strategy="waitForFunction",
    ),
    "TIM-005": FailureClassification(
        FailureFamily.SYNCHRONIZATION, "TIM-005", "TIM-005",
        "waitForTimeout fixo — script lento/flaky",
        recoverable=True, suggested_strategy="semantic_wait",
    ),
    "TIM-006": FailureClassification(
        FailureFamily.SYNCHRONIZATION, "TIM-006", "TIM-006",
        "Debounce em autocomplete — opcoes nao aparecem",
        recoverable=True, suggested_strategy="wait_for_options",
    ),
    "TIM-007": FailureClassification(
        FailureFamily.SYNCHRONIZATION, "TIM-007", "TIM-007",
        "Navegacao parcial SPA sem page load",
        recoverable=True, suggested_strategy="wait_for_marker",
    ),
    "TIMEOUT": FailureClassification(
        FailureFamily.SYNCHRONIZATION, "TIMEOUT", "TIM-005",
        "Timeout esperando elemento ou acao",
        recoverable=True, suggested_strategy="semantic_wait",
    ),
    "RACE_CONDITION": FailureClassification(
        FailureFamily.SYNCHRONIZATION, "RACE_CONDITION", "TIM-003",
        "Elemento apareceu/destruido durante interacao",
        recoverable=True, suggested_strategy="retry_with_polling",
    ),

    # FAM-03: Context
    "CTX-001": FailureClassification(
        FailureFamily.CONTEXT_SCOPE, "CTX-001", "CTX-001",
        "Elemento em iframe same-origin",
        recoverable=True, suggested_strategy="frame_reacquire",
    ),
    "CTX-002": FailureClassification(
        FailureFamily.CONTEXT_SCOPE, "CTX-002", "CTX-002",
        "Iframe cross-origin inacessivel",
        recoverable=False, suggested_strategy="manual_checkpoint",
    ),
    "CTX-003": FailureClassification(
        FailureFamily.CONTEXT_SCOPE, "CTX-003", "CTX-003",
        "Shadow DOM aberto — elemento nao localizado por CSS",
        recoverable=True, suggested_strategy="shadow_pierce",
    ),
    "CTX-004": FailureClassification(
        FailureFamily.CONTEXT_SCOPE, "CTX-004", "CTX-004",
        "Shadow DOM fechado — elemento inacessivel",
        recoverable=False, suggested_strategy="manual_checkpoint",
    ),
    "CTX-005": FailureClassification(
        FailureFamily.CONTEXT_SCOPE, "CTX-005", "CTX-005",
        "Popup/nova aba — script continua na pagina antiga",
        recoverable=True, suggested_strategy="capture_popup",
    ),
    "CTX-006": FailureClassification(
        FailureFamily.CONTEXT_SCOPE, "CTX-006", "CTX-006",
        "Modal/dialog fora do escopo — botao visivel nao encontrado",
        recoverable=True, suggested_strategy="dialog_scope",
    ),
    "CTX-007": FailureClassification(
        FailureFamily.CONTEXT_SCOPE, "CTX-007", "CTX-007",
        "Frame recarregado — handle antigo falhou",
        recoverable=True, suggested_strategy="frame_reacquire",
    ),

    # FAM-04: State
    "STA-001": FailureClassification(
        FailureFamily.STATE, "STA-001", "STA-001",
        "Sessao expirada — redirecionamento para login",
        recoverable=True, suggested_strategy="re_auth_hook",
    ),
    "STA-002": FailureClassification(
        FailureFamily.STATE, "STA-002", "STA-002",
        "Overlay bloqueando clique",
        recoverable=True, suggested_strategy="overlay_dismiss",
    ),
    "STA-003": FailureClassification(
        FailureFamily.STATE, "STA-003", "STA-003",
        "Dados sujos — pre-condicao nao satisfeita",
        recoverable=True, suggested_strategy="precondition_check",
    ),
    "STA-004": FailureClassification(
        FailureFamily.STATE, "STA-004", "STA-004",
        "Alert/confirm/prompt nativo — execucao travada",
        recoverable=True, suggested_strategy="dialog_handler",
    ),
    "STA-005": FailureClassification(
        FailureFamily.STATE, "STA-005", "STA-005",
        "Permissao insuficiente — botao ausente/acesso negado",
        recoverable=False, suggested_strategy="manual_checkpoint",
    ),
    "STA-006": FailureClassification(
        FailureFamily.STATE, "STA-006", "STA-006",
        "Ambiente indisponivel/intermitente — HTTP 5xx, timeout",
        recoverable=True, suggested_strategy="retry_controlled",
    ),

    # FAM-05: Dynamic DOM
    "DOM-001": FailureClassification(
        FailureFamily.DYNAMIC_DOM, "DOM-001", "DOM-001",
        "Element handle cacheado — detached/stale",
        recoverable=True, suggested_strategy="reacquire_locator",
    ),
    "DOM-002": FailureClassification(
        FailureFamily.DYNAMIC_DOM, "DOM-002", "DOM-002",
        "Lista reordenada — acao em item errado",
        recoverable=True, suggested_strategy="select_by_content",
    ),
    "DOM-003": FailureClassification(
        FailureFamily.DYNAMIC_DOM, "DOM-003", "DOM-003",
        "Re-render substitui no — encontrado antes, falha depois",
        recoverable=True, suggested_strategy="dom_stabilization",
    ),
    "DOM-004": FailureClassification(
        FailureFamily.DYNAMIC_DOM, "DOM-004", "DOM-004",
        "Virtualizacao de lista — item nao esta no DOM ate scroll",
        recoverable=True, suggested_strategy="scroll_controlled",
    ),
    "DOM-005": FailureClassification(
        FailureFamily.DYNAMIC_DOM, "DOM-005", "DOM-005",
        "Lazy loading visual — placeholder/skeleton na tela",
        recoverable=True, suggested_strategy="wait_for_content",
    ),

    # FAM-06: Input
    "INP-001": FailureClassification(
        FailureFamily.INPUT, "INP-001", "INP-001",
        "Upload PrimeFaces — upload gravado nao reproduz",
        recoverable=True, suggested_strategy="upload_payload_binding",
    ),
    "INP-002": FailureClassification(
        FailureFamily.INPUT, "INP-002", "INP-002",
        "Upload HTML padrao — caminho local absoluto invalido",
        recoverable=True, suggested_strategy="file_fixture",
    ),
    "INP-003": FailureClassification(
        FailureFamily.INPUT, "INP-003", "INP-003",
        "Download por clique — arquivo nao validado",
        recoverable=True, suggested_strategy="download_event_capture",
    ),
    "INP-004": FailureClassification(
        FailureFamily.INPUT, "INP-004", "INP-004",
        "Download AJAX/Blob — sem navegacao direta",
        recoverable=True, suggested_strategy="response_intercept",
    ),
    "INP-005": FailureClassification(
        FailureFamily.INPUT, "INP-005", "INP-005",
        "Drag-and-drop — acao gravada nao reproduz",
        recoverable=True, suggested_strategy="simulate_drag",
    ),
    "INP-006": FailureClassification(
        FailureFamily.INPUT, "INP-006", "INP-006",
        "Rich text editor via iframe — texto nao preenchido",
        recoverable=True, suggested_strategy="frame_reacquire",
    ),
    "INP-007": FailureClassification(
        FailureFamily.INPUT, "INP-007", "INP-007",
        "Mascara de input — valor digitado difere do esperado",
        recoverable=True, suggested_strategy="press_sequentially",
    ),
    "INP-008": FailureClassification(
        FailureFamily.INPUT, "INP-008", "INP-008",
        "CAPTCHA — fluxo bloqueado por desafio humano",
        recoverable=False, suggested_strategy="manual_checkpoint",
    ),
    "INP-009": FailureClassification(
        FailureFamily.INPUT, "INP-009", "INP-009",
        "Selecao de data em calendario — nao seleciona por input",
        recoverable=True, suggested_strategy="datepicker_select",
    ),
    "INP-010": FailureClassification(
        FailureFamily.INPUT, "INP-010", "INP-010",
        "Combobox customizado — select HTML nao existe",
        recoverable=True, suggested_strategy="aria_role_strategy",
    ),

    # FAM-07: File
    "FILE-001": FailureClassification(
        FailureFamily.FILE, "FILE-001", "FILE-001",
        "Arquivo local inexistente na execucao — caminho do gravador",
        recoverable=True, suggested_strategy="file_fixture",
    ),
    "FILE-002": FailureClassification(
        FailureFamily.FILE, "FILE-002", "FILE-002",
        "Upload com validacao de extensao — rejeitado",
        recoverable=True, suggested_strategy="valid_fixture",
    ),
    "FILE-003": FailureClassification(
        FailureFamily.FILE, "FILE-003", "FILE-003",
        "Upload com limite de tamanho — rejeicao",
        recoverable=True, suggested_strategy="smaller_fixture",
    ),
    "FILE-004": FailureClassification(
        FailureFamily.FILE, "FILE-004", "FILE-004",
        "Download com nome dinâmico — nome muda a cada execucao",
        recoverable=True, suggested_strategy="flexible_assert",
    ),
    "FILE-005": FailureClassification(
        FailureFamily.FILE, "FILE-005", "FILE-005",
        "Download precisa de autenticacao — link direto falha",
        recoverable=True, suggested_strategy="session_download",
    ),
    "FILE-006": FailureClassification(
        FailureFamily.FILE, "FILE-006", "FILE-006",
        "Download bloqueado por popup/aba",
        recoverable=True, suggested_strategy="capture_popup",
    ),

    # FAM-08: Assert
    "AST-001": FailureClassification(
        FailureFamily.ASSERT, "AST-001", "AST-001",
        "Assert informado antes da gravacao",
        recoverable=True, suggested_strategy="assert_overlay_capture",
    ),
    "AST-002": FailureClassification(
        FailureFamily.ASSERT, "AST-002", "AST-002",
        "Assert informado durante a gravacao",
        recoverable=True, suggested_strategy="assert_overlay_capture",
    ),
    "AST-003": FailureClassification(
        FailureFamily.ASSERT, "AST-003", "AST-003",
        "Assert informado depois da gravacao",
        recoverable=True, suggested_strategy="post_process_assert",
    ),
    "AST-004": FailureClassification(
        FailureFamily.ASSERT, "AST-004", "AST-004",
        "Assert de texto visivel — validar mensagem/resultado",
        recoverable=True, suggested_strategy="text_content_match",
    ),
    "AST-005": FailureClassification(
        FailureFamily.ASSERT, "AST-005", "AST-005",
        "Assert de URL/rota — validar navegacao",
        recoverable=True, suggested_strategy="url_pattern_assert",
    ),
    "AST-006": FailureClassification(
        FailureFamily.ASSERT, "AST-006", "AST-006",
        "Assert de arquivo baixado — validar download",
        recoverable=True, suggested_strategy="download_event_capture",
    ),
    "AST-007": FailureClassification(
        FailureFamily.ASSERT, "AST-007", "AST-007",
        "Assert de estado visual — botao/campo/select",
        recoverable=True, suggested_strategy="role_state_assertion",
    ),
    "AST-008": FailureClassification(
        FailureFamily.ASSERT, "AST-008", "AST-008",
        "Assert ambiguo — 'verificar se deu certo' sem alvo",
        recoverable=False, suggested_strategy="manual_checkpoint",
    ),
    "AST-009": FailureClassification(
        FailureFamily.ASSERT, "AST-009", "AST-009",
        "Assert de tabela/lista — validar presenca de registro",
        recoverable=True, suggested_strategy="row_content_assert",
    ),
    "AST-010": FailureClassification(
        FailureFamily.ASSERT, "AST-010", "AST-010",
        "Assert negativo — validar ausencia de erro/item",
        recoverable=True, suggested_strategy="not_visible_assert",
    ),

    # FAM-09: Recorder
    "REC-001": FailureClassification(
        FailureFamily.RECORDER, "REC-001", "REC-001",
        "Gravacao incompleta — fluxo sem estado final claro",
        recoverable=True, suggested_strategy="partial_checkpoint",
    ),
    "REC-002": FailureClassification(
        FailureFamily.RECORDER, "REC-002", "REC-002",
        "Overlay captura intencao do usuario — anotacao/assert",
        recoverable=True, suggested_strategy="persist_annotation",
    ),
    "REC-003": FailureClassification(
        FailureFamily.RECORDER, "REC-003", "REC-003",
        "Usuario pausa gravacao — intervalo sem eventos",
        recoverable=True, suggested_strategy="ignore_interval",
    ),
    "REC-004": FailureClassification(
        FailureFamily.RECORDER, "REC-004", "REC-004",
        "Navegacao manual fora do fluxo — mudanca sem acao clara",
        recoverable=True, suggested_strategy="manual_transition_step",
    ),
    "REC-005": FailureClassification(
        FailureFamily.RECORDER, "REC-005", "REC-005",
        "Recon/fingerprint inicial — coleta de stack/DOM/ambiente",
        recoverable=True, suggested_strategy="fingerprint_register",
    ),
    "REC-006": FailureClassification(
        FailureFamily.RECORDER, "REC-006", "REC-006",
        "Evento bloqueado por politica do browser/app",
        recoverable=True, suggested_strategy="snapshot_before_after",
    ),

    # FAM-10: Execution
    "OBS-001": FailureClassification(
        FailureFamily.EXECUTION, "OBS-001", "OBS-001",
        "Falha sem screenshot/trace — sem evidencias suficientes",
        recoverable=True, suggested_strategy="collect_artifacts",
    ),
    "OBS-002": FailureClassification(
        FailureFamily.EXECUTION, "OBS-002", "OBS-002",
        "Console error relevante — UI falha por erro JS",
        recoverable=True, suggested_strategy="correlate_console",
    ),
    "OBS-003": FailureClassification(
        FailureFamily.EXECUTION, "OBS-003", "OBS-003",
        "Erro de rede relevante — HTTP 4xx/5xx",
        recoverable=True, suggested_strategy="response_intercept",
    ),
    "OBS-004": FailureClassification(
        FailureFamily.EXECUTION, "OBS-004", "OBS-004",
        "Healing aplicado sem rastreabilidade",
        recoverable=True, suggested_strategy="register_taxonomy_id",
    ),
    "OBS-005": FailureClassification(
        FailureFamily.EXECUTION, "OBS-005", "OBS-005",
        "Rejeicao repetida do mesmo patch",
        recoverable=False, suggested_strategy="mark_unresolved",
    ),
    "OBS-006": FailureClassification(
        FailureFamily.EXECUTION, "OBS-006", "OBS-006",
        "Flakiness nao deterministica — passa/falha alterna",
        recoverable=True, suggested_strategy="clean_runs_before_promote",
    ),

    # FAM-11: Browser Limits
    "LIM-001": FailureClassification(
        FailureFamily.BROWSER_LIMITS, "LIM-001", "LIM-001",
        "CAPTCHA/desafio humano — exige validacao humana",
        recoverable=False, suggested_strategy="manual_checkpoint",
    ),
    "LIM-002": FailureClassification(
        FailureFamily.BROWSER_LIMITS, "LIM-002", "LIM-002",
        "Cross-origin inacessivel — DOM de frame bloqueado",
        recoverable=False, suggested_strategy="manual_checkpoint",
    ),
    "LIM-003": FailureClassification(
        FailureFamily.BROWSER_LIMITS, "LIM-003", "LIM-003",
        "Dado sensivel mascarado — valor nao pode ser persistido",
        recoverable=False, suggested_strategy="mask_tokenize",
    ),
    "LIM-004": FailureClassification(
        FailureFamily.BROWSER_LIMITS, "LIM-004", "LIM-004",
        "Operacao irreversivel — exclusao/envio/contratacao",
        recoverable=False, suggested_strategy="confirmation_checkpoint",
    ),
    "LIM-005": FailureClassification(
        FailureFamily.BROWSER_LIMITS, "LIM-005", "LIM-005",
        "Dependencia externa instavel — sistema de terceiro",
        recoverable=True, suggested_strategy="classify_dependency",
    ),

    # Legacy actionability (mapped to FAM-04)
    "ACTIONABILITY_OBSCURED": FailureClassification(
        FailureFamily.STATE, "ACTIONABILITY_OBSCURED", "STA-002",
        "Elemento coberto por overlay ou outro elemento",
        recoverable=True, suggested_strategy="overlay_dismiss",
    ),
    "ACTIONABILITY_DISABLED": FailureClassification(
        FailureFamily.INPUT, "ACTIONABILITY_DISABLED", "INP-007",
        "Elemento esta desabilitado",
        recoverable=True, suggested_strategy="wait_for_enabled",
    ),
    "ACTIONABILITY_NOT_VISIBLE": FailureClassification(
        FailureFamily.DYNAMIC_DOM, "ACTIONABILITY_NOT_VISIBLE", "DOM-005",
        "Elemento fora do viewport ou hidden",
        recoverable=True, suggested_strategy="scroll_into_view",
    ),
    "ORACLE_FAILED": FailureClassification(
        FailureFamily.ASSERT, "ORACLE_FAILED", "AST-004",
        "Oracle pos-acao falhou — resultado inesperado",
        recoverable=False, suggested_strategy="human_review",
    ),
    "NETWORK_ERROR": FailureClassification(
        FailureFamily.EXECUTION, "NETWORK_ERROR", "OBS-003",
        "Erro de rede ou servidor indisponivel",
        recoverable=True, suggested_strategy="retry",
    ),
}


# ── Keyword Patterns (ordered longest-first, word-boundary) ───────────────

def _wboundary(msg: str, pos: int, end: int) -> bool:
    """True se o match esta em fronteira de palavra."""
    if pos > 0 and msg[pos - 1].isalnum():
        return False
    if end < len(msg) and msg[end].isalnum():
        return False
    return True


KEYWORD_PATTERNS: list[tuple[str, str, str]] = [
    # (keyword, family_code, taxonomy_id) — ordered by decreasing length
    ("strict mode violation", "FAM-01", "SEL-004"),
    ("locator resolved to", "FAM-01", "SEL-004"),
    ("iframe element not found", "FAM-03", "CTX-001"),
    ("multiple elements found", "FAM-01", "SEL-009"),
    ("element not found", "FAM-01", "SEL-004"),
    ("not found", "FAM-01", "SEL-004"),
    ("element is not visible", "FAM-05", "DOM-005"),
    ("element is outside of the viewport", "FAM-05", "DOM-005"),
    ("element is not enabled", "FAM-04", "STA-002"),
    ("element is disabled", "FAM-04", "STA-002"),
    ("intercepts pointer events", "FAM-04", "STA-002"),
    ("is not clickable at point", "FAM-04", "STA-002"),
    ("detached from dom", "FAM-05", "DOM-001"),
    ("stale element reference", "FAM-05", "DOM-001"),
    ("is not attached to the dom", "FAM-05", "DOM-003"),
    ("waiting for selector", "FAM-02", "TIM-005"),
    ("waiting until", "FAM-02", "TIM-005"),
    ("navigation timeout", "FAM-02", "TIM-007"),
    ("timeout exceeded", "FAM-02", "TIM-005"),
    ("net::err", "FAM-02", "TIM-003"),
    ("connection refused", "FAM-10", "OBS-003"),
    ("session expired", "FAM-04", "STA-001"),
    ("access denied", "FAM-04", "STA-005"),
    ("403 forbidden", "FAM-04", "STA-005"),
    ("401 unauthorized", "FAM-04", "STA-001"),
    ("500 internal server error", "FAM-04", "STA-006"),
    ("502 bad gateway", "FAM-04", "STA-006"),
    ("503 service unavailable", "FAM-04", "STA-006"),
    ("dialog", "FAM-04", "STA-004"),
    ("iframe element", "FAM-03", "CTX-001"),
    ("file chooser", "FAM-07", "FILE-001"),
    ("file upload", "FAM-07", "FILE-001"),
    ("recorder overlay", "FAM-09", "REC-002"),
    ("assertionerror", "FAM-08", "AST-004"),
    ("expected", "FAM-08", "AST-004"),
    ("alert", "FAM-04", "STA-004"),
    ("confirm", "FAM-04", "STA-004"),
    ("iframe", "FAM-03", "CTX-001"),
    ("frame", "FAM-03", "CTX-001"),
    ("shadow root", "FAM-03", "CTX-003"),
    ("shadow dom", "FAM-03", "CTX-003"),
    ("cross-origin", "FAM-03", "CTX-002"),
    ("popup", "FAM-03", "CTX-005"),
    ("new tab", "FAM-03", "CTX-005"),
    ("new page", "FAM-03", "CTX-005"),
    ("overlay", "FAM-04", "STA-002"),
    ("obscured", "FAM-04", "STA-002"),
    ("fill", "FAM-06", "INP-007"),
    ("clear", "FAM-06", "INP-007"),
    ("not editable", "FAM-06", "INP-007"),
    ("readonly", "FAM-06", "INP-007"),
    ("masked", "FAM-06", "INP-007"),
    ("upload", "FAM-07", "FILE-001"),
    ("download", "FAM-07", "FILE-001"),
    ("file chooser", "FAM-07", "FILE-001"),
    ("assertion", "FAM-08", "AST-004"),
    ("expect", "FAM-08", "AST-004"),
    ("captcha", "FAM-11", "LIM-001"),
    ("ssl", "FAM-11", "LIM-002"),
    ("certificate", "FAM-11", "LIM-002"),
    ("tab crashed", "FAM-11", "LIM-005"),
    ("browser has been closed", "FAM-10", "OBS-001"),
    ("target closed", "FAM-10", "OBS-001"),
]


# ── Group Fallback Patterns ───────────────────────────────────────────────

GROUP_PATTERNS: list[tuple[str, str, str]] = [
    # (regex pattern, family_code, taxonomy_id)
    (r"timeout.*selector|selector.*timeout|strict.*locator|locator.*resolved|"
     r"multiple elements|element.*not.*found|no element matching",
     "FAM-01", "SEL-004"),
    (r"loading|stale element|net::err_|timeout|waiting|navigation|"
     r"debounce|autocomplete",
     "FAM-02", "TIM-005"),
    (r"iframe|frame|shadow.root|shadow.dom|cross.origin|popup|new.tab|new.page|"
     r"modal.*scope|dialog.*scope",
     "FAM-03", "CTX-001"),
    (r"dialog|alert|confirm|session|overlay|disabled|obscured|intercept|"
     r"expired|unauthorized|forbidden|permission|state",
     "FAM-04", "STA-002"),
    (r"detached|stale|re.render|re.order|virtual|lazy.load|not.visible|"
     r"viewport|hidden",
     "FAM-05", "DOM-001"),
    (r"fill|clear|editable|masked|readonly|input|type|textarea|drag|drop|"
     r"select|datepicker|calendar|combobox|autocomplete|pressSequentially",
     "FAM-06", "INP-007"),
    (r"upload|download|file|chooser|extension",
     "FAM-07", "FILE-001"),
    (r"assert|expect|assertion|oracle|validate|check",
     "FAM-08", "AST-004"),
    (r"record|overlay|pause|resume|capture|fingerprint|listener",
     "FAM-09", "REC-002"),
    (r"crash|browser.*closed|target.*closed|flaky|rejection|trace|console|"
     r"network|artifact|evidence",
     "FAM-10", "OBS-001"),
    (r"captcha|challenge|cross.origin|cross_origin|ssl|https|security|"
     r"irreversible|sensitive|masked|external.depend",
     "FAM-11", "LIM-001"),
]


# ── Failure Classifier ────────────────────────────────────────────────────

class FailureClassifier:
    """Classifica falhas com keyword matching → group fallback → unknown.

    Keyword matching usa word-boundary e longest-match-first.
    Group fallback usa regex por prefixo de family.
    """

    def classify(self, error_message: str, element_info: dict = None) -> FailureClassification:
        msg_lower = error_message.lower()
        element_info = element_info or {}

        # 1. Keyword matching (longest-first, word-boundary)
        for keyword, fam_code, tax_id in KEYWORD_PATTERNS:
            idx = msg_lower.find(keyword)
            if idx >= 0 and _wboundary(msg_lower, idx, idx + len(keyword)):
                family = self._family_from_code(fam_code)
                known = KNOWN_FAILURES.get(tax_id)
                fc = FailureClassification(
                    family=family,
                    code=tax_id,
                    taxonomy_id=tax_id,
                    description=f"Keyword match: '{keyword}'",
                    recoverable=known.recoverable if known else True,
                    suggested_strategy=known.suggested_strategy if known else self._strategy_for(tax_id),
                    confidence=0.9,
                    matched_by="keyword",
                )
                return fc

        # 2. Group fallback (regex with word-boundary)
        msg_clean = re.sub(r'\s+', ' ', msg_lower)
        for pattern, fam_code, tax_id in GROUP_PATTERNS:
            # Wrap pattern with word-boundary for clean matching
            bounded = r'(?<![a-z])(' + pattern + r')(?![a-z])'
            if re.search(bounded, msg_clean, re.IGNORECASE):
                family = self._family_from_code(fam_code)
                known = KNOWN_FAILURES.get(tax_id)
                fc = FailureClassification(
                    family=family,
                    code=tax_id,
                    taxonomy_id=tax_id,
                    description=f"Group fallback: {fam_code}",
                    recoverable=known.recoverable if known else True,
                    suggested_strategy=known.suggested_strategy if known else self._strategy_for(tax_id),
                    confidence=0.7,
                    matched_by="group",
                )
                return fc

        # 3. Unknown — LLM fallback placeholder
        return FailureClassification(
            FailureFamily.EXECUTION,
            code="OBS-001",
            taxonomy_id="OBS-001",
            description=f"Unclassified: {error_message[:120]}",
            recoverable=True,
            suggested_strategy="llm_fallback",
            confidence=0.0,
            matched_by="",
        )

    def classify_full(self, error_message: str, element_info: dict = None
                      ) -> FailureClassification:
        """Alias for classify(). Returns full FailureClassification."""
        return self.classify(error_message, element_info)

    @staticmethod
    def _family_from_code(fam_code: str) -> FailureFamily:
        """Converte FAM-XX → FailureFamily."""
        family_value = FAMILIES.get(fam_code, "execution")
        try:
            return FailureFamily(family_value)
        except ValueError:
            return FailureFamily.EXECUTION

    @staticmethod
    def _strategy_for(taxonomy_id: str) -> str:
        """Retorna estrategia sugerida para um taxonomy_id conhecido."""
        if taxonomy_id in KNOWN_FAILURES:
            return KNOWN_FAILURES[taxonomy_id].suggested_strategy
        return "llm_fallback"
