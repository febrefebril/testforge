"""TestForge — Modelo Intermediario Semantico (MIS).

Fase 2: LocatorCandidate estendido com campos de super-seletores
(backend_node_id, role, accessible_name, ax_path, attributes,
ancestor_roles, attribute_stability, playwright_call). Todos opcionais —
codigo existente que constroi `LocatorCandidate(strategy, selector, score, reason)`
continua funcionando inalterado. Novos campos populados pelo
extrator v2 em `semantic.locator.extractor` quando dados da arvore AX
(produzidos pelo gravador CDR da Fase 1) estao disponiveis.
"""
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class LocatorCandidate:
    strategy: str
    selector: str
    score: float
    reason: str = ""
    # Enriquecimento de super-seletor Fase 2 (opcional, populado pelo extrator v2).
    backend_node_id: Optional[int] = None
    role: Optional[str] = None
    accessible_name: Optional[str] = None
    ax_path: list = field(default_factory=list)
    attributes: dict = field(default_factory=dict)
    ancestor_roles: list = field(default_factory=list)
    attribute_stability: dict = field(default_factory=dict)
    playwright_call: Optional[str] = None
    intent_text: Optional[str] = None


@dataclass
class SemanticTarget:
    role: Optional[str] = None
    accessible_name: Optional[str] = None
    label: Optional[str] = None
    placeholder: Optional[str] = None
    test_id: Optional[str] = None
    text: Optional[str] = None
    tag: Optional[str] = None
    element_id: Optional[str] = None
    name: Optional[str] = None
    candidates: list = field(default_factory=list)
    fingerprint: dict = field(default_factory=dict)
    # Fase 2: contexto da arvore AX para desambiguacao em runtime + chave de cache L0.
    ax_path: list = field(default_factory=list)
    ancestor_roles: list = field(default_factory=list)
    intent_text: Optional[str] = None
    # B14/B17: descritor de host shadow-root aberto, quando o elemento
    # capturado vive dentro de uma arvore shadow. Formato:
    #   {host_selector, host_tag, host_id, mode}
    # None quando na arvore do documento ou dentro de shadow root fechado.
    shadow_host: Optional[dict] = None
    # Sprint J (2026-06-30): texto do mat-label dentro do mat-form-field
    # ancestral, quando aplicavel. Usado pelo compiler para emitir locator
    # `mat-form-field:has(mat-label:has-text("X")) input`, imune a
    # renumeracao de mat-input-N + aria-label volatil dos forms SIOPI.
    material_field_label: Optional[str] = None


@dataclass
class SemanticAction:
    action: str
    target: Optional[SemanticTarget] = None
    value: Optional[str] = None
    url: Optional[str] = None
    page_title: Optional[str] = None
    context: dict = field(default_factory=dict)
    skip_reason: str = ""
    blocking: bool = False
    depends_on: str = ""


@dataclass
class FieldValueMap:
    """Mapeia um campo de formulário para seu valor capturado/fornecido com intenção.

    Construído durante normalização por referência cruzada de form_values (submit),
    dados de polling, e eventos de fill. Usado durante execução para corresponder
    chaves do arquivo de dados a campos e fornecer contexto de intenção para fallback.
    """
    field_key: str
    value: str = ""
    intention: str = ""
    identifiers: dict = field(default_factory=dict)
    source: str = ""  # form_values | fill_event | setter_hook | checked_transition | snapshot_diff | final_state | missing_fill
    step_index: int = -1


@dataclass
class SemanticTestCase:
    test_id: str
    source_recording_id: str
    application: str = ""
    base_url: str = ""
    preconditions: list = field(default_factory=list)
    steps: list = field(default_factory=list)
    blind_spots: list = field(default_factory=list)
    field_values: dict = field(default_factory=dict)  # chave -> FieldValueMap
    # H20: particoes de cenario marcadas pelo usuario. Cada entrada eh
    # {start_step, end_step_exclusive, name} indexando em `steps`.
    # Quando Shift+N nao foi pressionado, ha exatamente um segmento que
    # abrange todos os passos.
    scenario_segments: list = field(default_factory=list)

    def to_dict(self) -> dict:
        result = {
            "semantic_test_case": {
                "metadata": {
                    "test_id": self.test_id,
                    "source_recording_id": self.source_recording_id,
                    "application": self.application,
                    "base_url": self.base_url,
                },
                "preconditions": self.preconditions,
                "steps": [],
            }
        }
        if self.field_values:
            result["semantic_test_case"]["field_values"] = {
                k: {
                    "field_key": v.field_key,
                    "value": v.value,
                    "intention": v.intention,
                    "identifiers": v.identifiers,
                    "source": v.source,
                    "step_index": v.step_index,
                }
                for k, v in self.field_values.items()
            }
        for step in self.steps:
            s = {"action": step.action}
            if step.target:
                t = {}
                if step.target.role: t["role"] = step.target.role
                if step.target.accessible_name: t["accessible_name"] = step.target.accessible_name
                if step.target.label: t["label"] = step.target.label
                if step.target.placeholder: t["placeholder"] = step.target.placeholder
                if step.target.test_id: t["test_id"] = step.target.test_id
                if step.target.text: t["text"] = step.target.text
                if step.target.tag: t["tag"] = step.target.tag
                if step.target.element_id: t["id"] = step.target.element_id
                if step.target.name: t["name"] = step.target.name
                if step.target.fingerprint:
                    t["fingerprint"] = step.target.fingerprint
                if step.target.ax_path:
                    t["ax_path"] = step.target.ax_path
                if step.target.ancestor_roles:
                    t["ancestor_roles"] = step.target.ancestor_roles
                if step.target.intent_text:
                    t["intent_text"] = step.target.intent_text
                if step.target.candidates:
                    t["candidates"] = [
                        self._candidate_dict(c) for c in step.target.candidates
                    ]
                s["target"] = t
            if step.value: s["value"] = step.value
            if step.url: s["url"] = step.url
            if step.page_title: s["page_title"] = step.page_title
            if step.context: s["context"] = step.context
            if step.skip_reason: s["skip_reason"] = step.skip_reason
            if step.blocking: s["blocking"] = True
            if step.depends_on: s["depends_on"] = step.depends_on
            result["semantic_test_case"]["steps"].append(s)
        return result

    @staticmethod
    def _candidate_dict(c) -> dict:
        """Serializa um LocatorCandidate; emite campos v2 apenas quando populados."""
        out = {
            "strategy": c.strategy,
            "selector": c.selector,
            "score": c.score,
            "reason": c.reason,
        }
        if getattr(c, "playwright_call", None):
            out["playwright_call"] = c.playwright_call
        if getattr(c, "intent_text", None):
            out["intent_text"] = c.intent_text
        if getattr(c, "ancestor_roles", None):
            out["ancestor_roles"] = c.ancestor_roles
        if getattr(c, "attribute_stability", None):
            out["attribute_stability"] = c.attribute_stability
        if getattr(c, "backend_node_id", None) is not None:
            out["backend_node_id"] = c.backend_node_id
        return out
