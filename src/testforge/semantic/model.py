"""TestForge — Semantic Intermediate Model (MIS)."""
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class LocatorCandidate:
    strategy: str
    selector: str
    score: float
    reason: str = ""


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
    field_values: dict = field(default_factory=dict)  # key -> FieldValueMap

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
                if step.target.candidates:
                    t["candidates"] = [
                        {"strategy": c.strategy, "selector": c.selector, "score": c.score, "reason": c.reason}
                        for c in step.target.candidates
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
