from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from uuid import uuid4


FAMILIES: dict[str, str] = {
    "FAM-01": "Seletores frágeis",
    "FAM-02": "Timing e assincronismo",
    "FAM-03": "Contexto e escopo",
    "FAM-04": "Estado da aplicação",
    "FAM-05": "DOM dinâmico",
    "FAM-06": "Input e interação especializada",
    "FAM-07": "Upload e download de arquivos",
    "FAM-08": "Asserts e validações",
    "FAM-09": "Recorder, overlay e checkpoints manuais",
    "FAM-10": "Execução, evidência e observabilidade",
    "FAM-11": "Limites técnicos e casos não automatizáveis com segurança",
}

TAXONOMIES: dict[str, list[str]] = {
    "FAM-01": ["SEL-001", "SEL-002", "SEL-003", "SEL-004", "SEL-005",
               "SEL-006", "SEL-007", "SEL-008", "SEL-009", "SEL-010"],
    "FAM-02": ["TIM-001", "TIM-002", "TIM-003", "TIM-004", "TIM-005",
               "TIM-006", "TIM-007"],
    "FAM-03": ["CTX-001", "CTX-002", "CTX-003", "CTX-004", "CTX-005",
               "CTX-006", "CTX-007"],
    "FAM-04": ["STA-001", "STA-002", "STA-003", "STA-004", "STA-005", "STA-006"],
    "FAM-05": ["DOM-001", "DOM-002", "DOM-003", "DOM-004", "DOM-005"],
    "FAM-06": ["INP-001", "INP-002", "INP-003", "INP-004", "INP-005",
               "INP-006", "INP-007", "INP-008", "INP-009", "INP-010"],
    "FAM-07": ["FILE-001", "FILE-002", "FILE-003", "FILE-004", "FILE-005", "FILE-006"],
    "FAM-08": ["AST-001", "AST-002", "AST-003", "AST-004", "AST-005",
               "AST-006", "AST-007", "AST-008", "AST-009", "AST-010"],
    "FAM-09": ["REC-001", "REC-002", "REC-003", "REC-004", "REC-005", "REC-006"],
    "FAM-10": ["OBS-001", "OBS-002", "OBS-003", "OBS-004", "OBS-005", "OBS-006"],
    "FAM-11": ["LIM-001", "LIM-002", "LIM-003", "LIM-004", "LIM-005"],
}


LEGACY_FAMILY_MAP: dict[str, str] = {
    "selector": "FAM-01",
    "capture": "FAM-09",
    "fill": "FAM-06",
    "execution": "FAM-10",
    "script": "FAM-08",
    "browser": "FAM-11",
    "infra": "FAM-11",
    "healing": "FAM-10",
}

LEGACY_TAXONOMY_MAP: dict[str, str] = {
    "label_resolve": "SEL-010",
    "xpath_universal": "SEL-004",
    "wrong_tag_has_text": "SEL-006",
    "duplicate_match": "SEL-009",
    "wrong_priority": "SEL-008",
    "event_duplicate": "REC-002",
    "event_not_fired": "REC-006",
    "fill_as_click": "REC-002",
    "autocomplete_timing": "TIM-006",
    "change_not_fired": "REC-002",
    "placeholder_value": "REC-002",
    "mask_js_detection": "INP-007",
    "autocomplete_value": "TIM-006",
    "fallback_added": "OBS-004",
    "visibility_fix": "STA-002",
    "action_mapping": "REC-004",
    "timeout_adjust": "TIM-005",
    "dialog_handler": "STA-004",
    "import_fix": "AST-003",
    "syntax_fix": "AST-003",
    "assert_type": "AST-008",
    "dialog_accept": "STA-004",
    "locale_config": "LIM-003",
    "arg_adjust": "LIM-003",
    "ci_config": "LIM-005",
    "dependency": "LIM-005",
    "env_config": "STA-006",
    "auto_register": "OBS-004",
    "family_add": "REC-001",
    "taxonomy_add": "REC-001",
}


def migrate_family(family: str) -> str:
    return LEGACY_FAMILY_MAP.get(family, family)


def migrate_taxonomy(taxonomy: str) -> str:
    return LEGACY_TAXONOMY_MAP.get(taxonomy, taxonomy)


RECIPE_OPS = [
    "pre_action",       # runs BEFORE the action (e.g., focus, clear)
    "post_action",      # runs AFTER the action (e.g., dispatch blur)
    "validate",         # validation check, must return boolean
    "retry_strategy",   # alternative approach if standard fails
]


@dataclass
class HealingRecipe:
    trigger_action: str = ""          # "fill", "click", "select"
    trigger_framework: str = ""       # "angular", "primefaces", "jquery", "generic"
    trigger_symptom: str = ""         # "aria_invalid", "element_gone", "value_set_but_invalid"
    trigger_selector_pattern: str = ""  # regex for selector matching (optional)
    trigger_prev_action: str = ""     # previous step's action to disambiguate (e.g., "fill")
    priority: int = 100               # higher = tried first
    pre_action_eval: str = ""         # JS eval before action (empty = none)
    post_action_eval: str = ""        # JS eval after action (e.g., "el.dispatchEvent(new Event('blur',{bubbles:true}))")
    post_action_wait_selector: str = ""  # CSS selector to wait for after action
    post_action_wait_eval: str = ""      # JS expression for page.wait_for_function() — waits until truthy
    post_action_wait_timeout: int = 10000  # ms to wait for post_action_wait_selector/eval
    validate_eval: str = ""           # JS eval returning boolean (empty = skip)
    fail_eval: str = ""              # JS eval to run when validation fails (e.g., "el.focus()")
    success_count: int = 0
    fail_count: int = 0
    notes: str = ""
    framework: str = ""
    id: str = field(default_factory=lambda: uuid4().hex[:12])
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    last_used_at: str = ""

    def to_dict(self) -> dict[str, object]:
        return asdict(self)

    @staticmethod
    def from_dict(data: dict[str, object]) -> HealingRecipe:
        return HealingRecipe(**{k: v for k, v in data.items() if k in HealingRecipe.__dataclass_fields__})

    def to_entry(self) -> HealingEntry:
        return HealingEntry(
            system=f"recipe:{self.id}",
            symptom=f"[recipe] {self.trigger_action}/{self.trigger_framework}: {self.trigger_symptom}",
            root_cause=f"Triggered by {self.trigger_action} on {self.trigger_framework} with symptom {self.trigger_symptom}",
            fix=f"Recipe {self.id}: pre_action={bool(self.pre_action_eval)} post_action={bool(self.post_action_eval)} validate={bool(self.validate_eval)}",
            family=migrate_family(self.trigger_action),
            taxonomy="OBS-004",
            fix_type="llm_recipe",
            notes=self.notes,
            confidence=min(1.0, max(0.0, self.success_count / max(1, self.success_count + self.fail_count))),
        )


@dataclass
class HealingEntry:
    system: str
    symptom: str
    root_cause: str
    fix: str
    family: str = ""
    taxonomy: str = ""
    fix_type: str = ""
    files_changed: list[str] = field(default_factory=list)
    url: str = ""
    action: str = ""
    selector: str = ""
    tag: str = ""
    input_type: str = ""
    notes: str = ""
    confidence: float = 0.0
    failure_count: int = 0
    last_used_at: str = ""
    id: str = field(default_factory=lambda: uuid4().hex[:12])
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict[str, object]:
        return asdict(self)

    @staticmethod
    def from_dict(data: dict[str, object]) -> HealingEntry:
        files = data.get("files_changed", []) or []
        clean_data = {k: v for k, v in data.items() if k != "files_changed"}
        entry = HealingEntry(**clean_data)
        entry.files_changed = [f for f in files if f]
        return entry
