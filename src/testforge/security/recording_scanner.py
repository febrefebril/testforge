"""Recording scanner — apply PII detector across all recording artifacts.

Walks recording directory, reads raw_events, steps.jsonl, value_mutations,
suggested_assertions, field_snapshots, submission_report, test_data, metadata.
Emits aggregated PiiHit list per source. Values are preserved verbatim.
"""
from __future__ import annotations

import json
import os
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, Optional

from .pii_detector import (
    PiiHit,
    PiiPattern,
    Severity,
    detect,
    is_production_domain,
    url_scan,
)


@dataclass
class ScanReport:
    recording_id: str
    recording_dir: str
    hits_by_source: dict[str, list[PiiHit]] = field(default_factory=dict)
    base_url: str = ""
    production_hit: Optional[PiiHit] = None

    @property
    def total_hits(self) -> int:
        return sum(len(v) for v in self.hits_by_source.values())

    @property
    def all_hits(self) -> list[PiiHit]:
        out: list[PiiHit] = []
        for hits in self.hits_by_source.values():
            out.extend(hits)
        if self.production_hit:
            out.append(self.production_hit)
        return out

    def by_pattern(self) -> Counter:
        return Counter(h.pattern.value for h in self.all_hits)

    def by_severity(self) -> Counter:
        return Counter(h.severity.value for h in self.all_hits)

    def critical_count(self) -> int:
        return sum(
            1 for h in self.all_hits if h.severity == Severity.CRITICAL
        )

    def as_dict(self) -> dict:
        return {
            "policy": "alert_only",
            "masking_applied": False,
            "recording_id": self.recording_id,
            "recording_dir": self.recording_dir,
            "base_url": self.base_url,
            "totals": {
                "hits": self.total_hits,
                "by_pattern": dict(self.by_pattern()),
                "by_severity": dict(self.by_severity()),
                "critical": self.critical_count(),
            },
            "production_domain_detected": self.production_hit is not None,
            "hits_by_source": {
                src: [h.as_alert_entry() | {
                    "value_full": h.value,
                    "match_start": h.match_start,
                    "match_end": h.match_end,
                } for h in hits]
                for src, hits in self.hits_by_source.items()
            },
        }


def scan_recording(rec_dir: str | Path) -> ScanReport:
    """Scan a recording directory. Returns ScanReport with hits per source."""
    rec_path = Path(rec_dir)
    if not rec_path.is_dir():
        raise FileNotFoundError(f"recording dir not found: {rec_dir}")

    rec_id = rec_path.name
    report = ScanReport(recording_id=rec_id, recording_dir=str(rec_path))

    # Metadata: check base_url for production
    meta_path = rec_path / "recording_metadata.json"
    if meta_path.exists():
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            base_url = meta.get("base_url", "")
            report.base_url = base_url
            prod_hit = is_production_domain(base_url)
            if prod_hit:
                report.production_hit = prod_hit
        except Exception:
            pass

    # raw_events.jsonl
    _scan_jsonl_lines(
        rec_path / "raw_events.jsonl",
        report,
        source_prefix="raw_events",
        handler=_handle_raw_event,
    )

    # steps.jsonl
    _scan_jsonl_lines(
        rec_path / "steps.jsonl",
        report,
        source_prefix="steps",
        handler=_handle_step,
    )

    # value_mutations.jsonl
    _scan_jsonl_lines(
        rec_path / "value_mutations.jsonl",
        report,
        source_prefix="value_mutations",
        handler=_handle_value_mutation,
    )

    # field_snapshots.jsonl
    _scan_jsonl_lines(
        rec_path / "field_snapshots.jsonl",
        report,
        source_prefix="field_snapshots",
        handler=_handle_field_snapshot,
    )

    # suggested_assertions.jsonl
    _scan_jsonl_lines(
        rec_path / "suggested_assertions.jsonl",
        report,
        source_prefix="suggested_assertions",
        handler=_handle_suggested_assertion,
    )

    # final_state_snapshot.json
    final_path = rec_path / "final_state_snapshot.json"
    if final_path.exists():
        try:
            final = json.loads(final_path.read_text(encoding="utf-8"))
            _handle_final_state(final, report)
        except Exception:
            pass

    # test_data.json + field_value_map.json
    for fname, prefix in (
        ("test_data.json", "test_data"),
        ("field_value_map.json", "field_value_map"),
    ):
        p = rec_path / fname
        if p.exists():
            try:
                data = json.loads(p.read_text(encoding="utf-8"))
                _scan_dict_recursive(data, report, prefix)
            except Exception:
                pass

    return report


def _scan_jsonl_lines(path: Path, report: ScanReport, source_prefix: str, handler):
    if not path.exists():
        return
    try:
        with path.open("r", encoding="utf-8") as f:
            for idx, line in enumerate(f, start=1):
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except Exception:
                    continue
                handler(obj, idx, report, source_prefix)
    except Exception:
        pass


def _handle_raw_event(obj: dict, line_no: int, report: ScanReport, prefix: str):
    evt_id = obj.get("event_id", f"line_{line_no}")
    ctx_base = f"{prefix}.{evt_id}"
    # URL scan
    _add_hits(report, prefix, url_scan(obj.get("url", ""), f"{ctx_base}.url"))
    # Value scan (with field metadata)
    value = obj.get("value")
    if value is not None:
        target = obj.get("target", {})
        md = {
            "type": (target.get("attributes", {}) or {}).get("type"),
            "name": target.get("name"),
            "element_id": target.get("element_id"),
            "placeholder": target.get("placeholder"),
            "label": target.get("label"),
            "aria_label": target.get("accessible_name"),
            "paste": obj.get("paste") is True,
        }
        _add_hits(report, prefix, detect(value, f"{ctx_base}.value", md))
    # Target.text scan (may contain concatenated CNPJs/names)
    tgt = obj.get("target") or {}
    text = tgt.get("text")
    if text:
        _add_hits(report, prefix, detect(text, f"{ctx_base}.target.text"))


def _handle_step(obj: dict, line_no: int, report: ScanReport, prefix: str):
    step_id = obj.get("step_id", f"line_{line_no}")
    ctx_base = f"{prefix}.{step_id}"
    _add_hits(report, prefix, url_scan(obj.get("url", ""), f"{ctx_base}.url"))
    for field_name in ("value", "expected_value", "text"):
        val = obj.get(field_name)
        if val:
            _add_hits(report, prefix, detect(val, f"{ctx_base}.{field_name}"))


def _handle_value_mutation(obj: dict, line_no: int, report: ScanReport, prefix: str):
    ctx = f"{prefix}.line_{line_no}"
    val = obj.get("value")
    fp = obj.get("fingerprint", "")
    # Heuristic metadata from fingerprint
    md = {}
    fp_lower = fp.lower()
    if "password" in fp_lower:
        md["type"] = "password"
    if val:
        _add_hits(report, prefix, detect(val, ctx, md))


def _handle_field_snapshot(batch: dict, line_no: int, report: ScanReport, prefix: str):
    ctx_base = f"{prefix}.line_{line_no}"
    snapshots = batch.get("snapshots", []) if isinstance(batch, dict) else []
    for snap in snapshots:
        if not isinstance(snap, dict):
            continue
        val = snap.get("value")
        raw_val = snap.get("raw_value")
        md = {
            "type": snap.get("type"),
            "name": (snap.get("identifiers") or {}).get("name"),
            "placeholder": (snap.get("identifiers") or {}).get("placeholder"),
            "label": (snap.get("identifiers") or {}).get("label"),
            "aria_label": (snap.get("identifiers") or {}).get("aria-label"),
        }
        fp = snap.get("fingerprint", "")
        ctx = f"{ctx_base}.{fp}"
        if val:
            _add_hits(report, prefix, detect(val, ctx, md))
        if raw_val and raw_val != val:
            _add_hits(report, prefix, detect(raw_val, f"{ctx}.raw", md))


def _handle_suggested_assertion(obj: dict, line_no: int, report: ScanReport, prefix: str):
    ctx_base = f"{prefix}.line_{line_no}"
    _add_hits(report, prefix, url_scan(obj.get("before_url", ""), f"{ctx_base}.before_url"))
    _add_hits(report, prefix, url_scan(obj.get("after_url", ""), f"{ctx_base}.after_url"))
    for change in obj.get("changes", []) or []:
        val = change.get("value")
        if val:
            _add_hits(report, prefix, detect(val, f"{ctx_base}.change.value"))


def _handle_final_state(obj: dict, report: ScanReport):
    _scan_dict_recursive(obj, report, "final_state_snapshot")


def _scan_dict_recursive(obj, report: ScanReport, prefix: str, path: str = ""):
    if isinstance(obj, dict):
        for k, v in obj.items():
            new_path = f"{path}.{k}" if path else k
            _scan_dict_recursive(v, report, prefix, new_path)
    elif isinstance(obj, list):
        for i, item in enumerate(obj):
            new_path = f"{path}[{i}]" if path else f"[{i}]"
            _scan_dict_recursive(item, report, prefix, new_path)
    elif isinstance(obj, str) and obj:
        ctx = f"{prefix}.{path}" if path else prefix
        _add_hits(report, prefix, detect(obj, ctx))


def _add_hits(report: ScanReport, source: str, hits: list[PiiHit]):
    if not hits:
        return
    report.hits_by_source.setdefault(source, []).extend(hits)


def write_report(report: ScanReport, out_path: str | Path) -> str:
    """Write scan report as JSON. Returns absolute path written."""
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(report.as_dict(), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return str(out.resolve())
