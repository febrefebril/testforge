from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class RecordingFingerprint:
    page_technology: str = ""
    page_url: str = ""
    page_title: str = ""
    viewport: str = ""
    selector_used: str = ""
    tag_name: str = ""
    text_content: str = ""
    dom_snapshot: str = ""


@dataclass
class StorageFingerprint:
    recorded_steps: list[RecordingFingerprint] = field(default_factory=list)
    fallbacks_per_step: list[list[str]] = field(default_factory=list)
    intentions: list[str] = field(default_factory=list)
    technology_detected: str = ""
    total_steps: int = 0


@dataclass
class CurationFingerprint:
    stored: StorageFingerprint = field(default_factory=StorageFingerprint)
    current_dom_snapshot: str = ""
    failure_context: str = ""
    error_message: str = ""
    failed_step_index: int = -1
    evidence_paths: list[str] = field(default_factory=list)


@dataclass
class Fingerprint:
    recording: RecordingFingerprint = field(default_factory=RecordingFingerprint)
    storage: StorageFingerprint = field(default_factory=StorageFingerprint)
    curation: CurationFingerprint = field(default_factory=CurationFingerprint)
