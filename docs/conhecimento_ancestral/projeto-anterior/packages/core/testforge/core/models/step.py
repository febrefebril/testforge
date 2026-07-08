from __future__ import annotations
from dataclasses import dataclass, field


@dataclass
class StepMetadata:
    timeout: int = 30000
    intention: str = ""
    retry_on_failure: bool = True
    screenshot_on_fail: bool = True


@dataclass
class RecordedStep:
    step_id: str
    timestamp: str
    action: str
    selector_used: str
    raw_selector: str = ""
    fallbacks: list[str] = field(default_factory=list)
    strategies: list[dict] = field(default_factory=list)
    tag_name: str = ""
    text: str = ""
    value: str = ""
    url: str = ""
    page_title: str = ""
    page_technology: str = ""
    dom_snapshot: str = ""
    intention: str = ""
    assert_type: str = ""
    assert_state: str = ""
    expected_value: str = ""
    attrs: dict = field(default_factory=dict)


@dataclass
class StepResult:
    name: str
    status: str
    duration_ms: int = 0
    intention: str = ""
    error_message: str = ""
    selector_used: str = ""
    recoverable: bool = False
    screenshot_path: str = ""
