
"""P0.2-S schemas for sensitive-data review and submission preparation."""
from __future__ import annotations
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from pydantic import BaseModel, ConfigDict, Field, model_validator

class FindingCategory(str, Enum):
    TEST_DATA = "test_data"
    PERSONAL_DATA = "personal_data"
    SECRET = "secret"
    SESSION_TRANSIENT = "session_transient"
    UNKNOWN = "unknown"

class DecisionAction(str, Enum):
    PRESERVE = "preserve"
    SANITIZE = "sanitize"
    EXCLUDE = "exclude"
    BLOCK = "block"
    CANCEL = "cancel"

class SensitiveFinding(BaseModel):
    model_config = ConfigDict(extra="forbid")
    finding_id: str
    file_path: str
    line: int | None = None
    data_type: str
    category: FindingCategory
    masked_sample: str
    proposed_action: DecisionAction
    blocking: bool
    reason: str

class FindingDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")
    finding_id: str
    action: DecisionAction
    confirmed_test_mass: bool = False
    justification: str | None = None

    @model_validator(mode="after")
    def validate_preserve(self):
        if self.action == DecisionAction.PRESERVE:
            if not self.confirmed_test_mass or not (self.justification or "").strip():
                raise ValueError("preserve requires confirmed_test_mass and justification")
        return self

class ScanReport(BaseModel):
    model_config = ConfigDict(extra="forbid")
    schema_version: int = 1
    recording_id: str
    scanned_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    source_sha256: str
    findings: list[SensitiveFinding] = Field(default_factory=list)
    blocking_findings: int = 0
    status: str = "clean"

class SubmissionDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")
    schema_version: int = 1
    recording_id: str
    environment: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    cancelled: bool = False
    decisions: list[FindingDecision] = Field(default_factory=list)
    requested_by: str | None = None

class SubmissionReport(BaseModel):
    model_config = ConfigDict(extra="forbid")
    schema_version: int = 1
    recording_id: str
    dry_run: bool
    source_dir: str
    output_dir: str | None = None
    source_sha256_before: str
    source_sha256_after: str
    package_sha256: str | None = None
    scan_status: str
    submission_allowed: bool
    published: bool = False
    status: str
    message: str

