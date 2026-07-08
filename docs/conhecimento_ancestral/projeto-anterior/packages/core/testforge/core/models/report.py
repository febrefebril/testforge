from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from testforge.core.models.step import StepResult


@dataclass
class ExecutionSummary:
    total: int = 0
    passed: int = 0
    failed: int = 0
    warnings: int = 0
    executive: str = ""


@dataclass
class CurationRecord:
    attempted: bool = False
    success: bool = False
    new_script: str = ""
    diff: str = ""
    evidence: list[str] = field(default_factory=list)
    taxonomy_id: str = ""
    family: str = ""
    classification_layer: str = ""
    layer_used: str = ""


@dataclass
class LayersUsed:
    layer1_catalog: bool = False
    layer2_agents: bool = False
    layer3_healer: bool = False


@dataclass
class HealingSummary:
    curation_record: CurationRecord = field(default_factory=CurationRecord)
    layers_used: LayersUsed = field(default_factory=LayersUsed)
    attempted: bool = False
    success: bool = False


@dataclass
class Report:
    version: str = "1.0"
    test_name: str = ""
    test_path: str = ""
    env: str = ""
    started_at: str = ""
    duration_ms: int = 0
    status: str = ""
    browser: str = ""
    mode: str = ""
    report_dir: str = ""
    trace_path: str = ""
    steps: list[StepResult] = field(default_factory=list)
    curation: CurationRecord = field(default_factory=CurationRecord)
    healing: HealingSummary = field(default_factory=HealingSummary)
    summary: ExecutionSummary = field(default_factory=ExecutionSummary)

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "test_name": self.test_name,
            "test_path": self.test_path,
            "env": self.env,
            "started_at": self.started_at,
            "duration_ms": self.duration_ms,
            "status": self.status,
            "browser": self.browser,
            "mode": self.mode,
            "report_dir": self.report_dir,
            "trace_path": self.trace_path,
            "steps": [asdict(s) for s in self.steps],
            "curation": asdict(self.curation),
            "healing": asdict(self.healing),
            "summary": asdict(self.summary),
        }

    def save(self, path: str) -> str:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, ensure_ascii=False, indent=2)
        return str(path)

    @staticmethod
    def load(path: str) -> Report:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        steps = [StepResult(**s) for s in data.get("steps", [])]
        summary = ExecutionSummary(**data.get("summary", {}))
        return Report(
            version=data.get("version", "1.0"),
            test_name=data.get("test_name", ""),
            test_path=data.get("test_path", ""),
            env=data.get("env", ""),
            started_at=data.get("started_at", ""),
            duration_ms=data.get("duration_ms", 0),
            status=data.get("status", ""),
            browser=data.get("browser", ""),
            mode=data.get("mode", ""),
            report_dir=data.get("report_dir", ""),
            trace_path=data.get("trace_path", ""),
            steps=steps,
            summary=summary,
        )
