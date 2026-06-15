"""TestForge — Raw Recorded Event model."""
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional


@dataclass
class TargetInfo:
    tag: Optional[str] = None
    text: Optional[str] = None
    role: Optional[str] = None
    accessible_name: Optional[str] = None
    element_id: Optional[str] = None
    name: Optional[str] = None
    test_id: Optional[str] = None
    placeholder: Optional[str] = None
    label: Optional[str] = None
    attributes: dict = field(default_factory=dict)
    class_list: list = field(default_factory=list)
    aria_attrs: dict = field(default_factory=dict)
    data_attrs: dict = field(default_factory=dict)
    parent_text: Optional[str] = None
    bounding_box: Optional[dict] = None
    parent_chain: list = field(default_factory=list)
    sibling_summary: list = field(default_factory=list)
    frame_context: Optional[str] = None
    shadow_context: Optional[str] = None


@dataclass
class RawRecordedEvent:
    event_id: str
    event_type: str  # click, fill, navigation, select, keypress, submit
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    url: Optional[str] = None
    page_title: Optional[str] = None
    target: Optional[TargetInfo] = None
    value: Optional[str] = None
    frame_url: Optional[str] = None
    screenshot_path: Optional[str] = None
    dom_snapshot_path: Optional[str] = None
    ax_snapshot_path: Optional[str] = None

    def to_dict(self) -> dict:
        result = {
            "event_id": self.event_id,
            "type": self.event_type,
            "timestamp": self.timestamp,
            "url": self.url,
            "page_title": self.page_title,
        }
        if self.target:
            result["target"] = {k: v for k, v in self.target.__dict__.items() if v}
        if self.value is not None:
            result["value"] = self.value
        if self.frame_url:
            result["frame_url"] = self.frame_url
        if self.screenshot_path:
            result["screenshot"] = self.screenshot_path
        if self.dom_snapshot_path:
            result["dom_snapshot"] = self.dom_snapshot_path
        if self.ax_snapshot_path:
            result["ax_snapshot"] = self.ax_snapshot_path
        return result
