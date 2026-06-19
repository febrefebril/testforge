"""TestForge — Interactive Completion Prompt.

Sprint 2: Prompts user for missing field values after recording,
saves responses to field_value_map and test_data.
"""

import json
import os
import sys
from datetime import datetime, timezone
from typing import Optional

from testforge.recorder.recording_status import RecordingStatus
from testforge.validation.intent_completeness import (
    CompletenessReport,
    FieldCompleteness,
    IntentCompletenessChecker,
    save_completeness_report,
)


def prompt_missing_fields(
    rec_dir: str,
    recording_id: str,
    report: CompletenessReport,
    normalizer=None,
    stc=None,
) -> bool:
    """Prompt user for each pending field value interactively.

    Args:
        rec_dir: Recording directory path.
        recording_id: Recording ID.
        report: CompletenessReport with pending fields.
        normalizer: Optional RecordingNormalizer instance (for re-check).
        stc: Optional SemanticTestCase (for re-check).

    Returns:
        True if all fields resolved, False if any remain pending.
    """
    if not report.pending_fields:
        print("[TestForge] ✓ Nenhum campo pendente — intencao completa")
        _update_recording_metadata(rec_dir, RecordingStatus.intent_complete)
        return True

    print(f"\n[TestForge] 🔍 Intencao INCOMPLETA — {len(report.pending_fields)} campo(s) pendente(s)")
    print()

    values_provided = {}
    for field in report.pending_fields:
        label = field.label or field.field_key
        reason = field.reason or "campo sem valor capturado"
        selector_hint = field.selector or ""

        print(f"  ── Campo #{field.step_index}: {label} ──")
        print(f"     Motivo: {reason}")
        if selector_hint:
            print(f"     Seletor: {selector_hint}")
        if field.placeholder:
            print(f"     Placeholder: {field.placeholder}")

        try:
            val = input(f"  Valor para '{label}' (Enter=vazio/pular): ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            val = ""

        if val:
            values_provided[field.field_key] = {
                "field_key": field.field_key,
                "value": val,
                "intention": f"fill {label} with '{val}' (user supplied)",
                "identifiers": {
                    "name": field.name,
                    "id": field.element_id,
                    "label": field.label,
                    "placeholder": field.placeholder,
                },
                "source": "user_supplied_cli",
                "confidence": 1.0,
                "step_index": field.step_index,
            }
            print(f"     ✓ Valor registrado: '{val}'")
        else:
            print(f"     - Pulado (sem valor)")

        print()

    # Save provided values to field_value_map.json
    _save_field_value_map(rec_dir, values_provided)

    # Save to test_data.json
    test_data_path = _save_test_data(rec_dir, values_provided, recording_id)

    # Re-run normalizer + completeness checker with new values
    if normalizer is None:
        from testforge.semantic import RecordingNormalizer
        normalizer = RecordingNormalizer()
    try:
        # Infer app/base_url from recording metadata if available
        meta_path = os.path.join(rec_dir, "recording_metadata.json")
        meta = {}
        if os.path.exists(meta_path):
            with open(meta_path) as f:
                meta = json.load(f)
        app = meta.get("application", "web")
        base_url = meta.get("base_url", "http://localhost")

        new_stc = normalizer.normalize(rec_dir, f"ST-{recording_id}", app, base_url)
        checker = IntentCompletenessChecker()
        new_report = checker.check_steps(new_stc.steps, new_stc.field_values)

        report_dir = os.path.join(rec_dir, "completeness")
        json_path, md_path = save_completeness_report(new_report, report_dir, recording_id)

        if new_report.is_complete:
            print(f"[TestForge] ✓ Todos os campos resolvidos — intencao COMPLETA")
            _update_recording_metadata(rec_dir, RecordingStatus.intent_complete)
        else:
            print(f"[TestForge] ⚠ {new_report.missing_count} campo(s) ainda pendente(s)")
            print(f"  Relatorio: {md_path}")
            print(f"  Para completar: testforge compile --check {recording_id}")
            _update_recording_metadata(rec_dir, RecordingStatus.incomplete_intent)
        return new_report.is_complete
    except Exception as e:
        print(f"[TestForge] ⚠ Erro ao re-verificar completude: {e}")
        # Fallback: simple count-based check
        resolved = len(values_provided)
        pending = len(report.pending_fields) - resolved
        if pending == 0:
            print(f"[TestForge] ✓ Todos os {resolved} campos resolvidos via CLI")
            _update_recording_metadata(rec_dir, RecordingStatus.intent_complete)
            return True
        else:
            print(f"[TestForge] ⚠ {pending} campo(s) ainda pendente(s) (contagem simples)")
            print(f"  Dados salvos: {test_data_path}")
            _update_recording_metadata(rec_dir, RecordingStatus.incomplete_intent)
            return False


def create_data_template(
    rec_dir: str,
    recording_id: str,
    report: CompletenessReport,
) -> str:
    """Create test_data.template.json for non-interactive mode.

    Args:
        rec_dir: Recording directory path.
        recording_id: Recording ID.
        report: CompletenessReport with pending fields.

    Returns:
        Path to generated template file.
    """
    template = {
        "metadata": {
            "recording_id": recording_id,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "mode": "template",
            "status": "incomplete_intent",
        },
        "fields": {},
    }

    for field in report.pending_fields:
        label = field.label or field.field_key
        template["fields"][field.field_key] = {
            "label": label,
            "placeholder": field.placeholder or "",
            "type": "pending",
            "reason": field.reason or "",
            "step_index": field.step_index,
            "source": "template_pending",
        }

    # Include resolved fields too
    for field in report.fields:
        if field.completeness in (FieldCompleteness.resolved,
                                   FieldCompleteness.resolved_with_warning):
            label = field.label or field.field_key
            template["fields"][field.field_key] = {
                "label": label,
                "value": field.value,
                "source": field.source,
                "completeness": field.completeness.value,
            }

    template_path = os.path.join(rec_dir, "test_data.template.json")
    with open(template_path, "w", encoding="utf-8") as f:
        json.dump(template, f, indent=2, ensure_ascii=False)

    return template_path


def _save_field_value_map(rec_dir: str, values: dict) -> str:
    """Append user-supplied values to field_value_map.json.

    Args:
        rec_dir: Recording directory.
        values: Dict of field_key -> value info.

    Returns:
        Path to field_value_map.json.
    """
    path = os.path.join(rec_dir, "field_value_map.json")

    existing = {}
    if os.path.exists(path):
        with open(path) as f:
            existing = json.load(f)

    if "fields" not in existing:
        existing["fields"] = {}
    if "entries" not in existing:
        existing["entries"] = []

    for key, info in values.items():
        existing["fields"][key] = info["value"]
        entry = {
            "field_key": key,
            "value": info["value"],
            "intention": info.get("intention", ""),
            "identifiers": info.get("identifiers", {}),
            "source": "user_supplied_cli",
            "confidence": info.get("confidence", 1.0),
            "step_index": info.get("step_index", -1),
        }
        existing["entries"].append(entry)

    # Also update metadata
    existing["_meta"] = existing.get("_meta", {})
    existing["_meta"]["updated_at"] = datetime.now(timezone.utc).isoformat()
    existing["_meta"]["sources"] = list(set(
        existing["_meta"].get("sources", []) + ["user_supplied_cli"]
    ))

    with open(path, "w") as f:
        json.dump(existing, f, indent=2, ensure_ascii=False)

    return path


def _save_test_data(rec_dir: str, values: dict, recording_id: str) -> str:
    """Update test_data.json with user-supplied values.

    Args:
        rec_dir: Recording directory.
        values: Dict of field_key -> value info.
        recording_id: Recording ID.

    Returns:
        Path to test_data.json.
    """
    path = os.path.join(rec_dir, "test_data.json")

    existing = {
        "recording_id": recording_id,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "fields": {},
        "metadata": {},
    }
    if os.path.exists(path):
        with open(path) as f:
            existing = json.load(f)

    for key, info in values.items():
        existing["fields"][key] = {
            "value": info["value"],
            "source": "user_supplied_cli",
            "confidence": info.get("confidence", 1.0),
            "step_index": info.get("step_index", -1),
        }
        if "metadata" not in existing:
            existing["metadata"] = {}
        existing["metadata"][key] = {
            "source": "user_supplied_cli",
            "recorded_at": datetime.now(timezone.utc).isoformat(),
        }

    # Sensitive data alert (not auto-masking)
    _sensitive_patterns = [
        r"(?i)cpf|senha|password|cartao|card|credit|token",
    ]
    import re
    for key in values:
        for pattern in _sensitive_patterns:
            if re.search(pattern, key):
                print(f"  ⚠ ALERTA: Campo sensivel '{key}' teve valor informado via CLI")
                print(f"    Revise antes de versionar os artefatos")
                if "sensitive_alerts" not in existing:
                    existing["sensitive_alerts"] = []
                existing["sensitive_alerts"].append({
                    "field": key,
                    "reason": "Valor informado via CLI pode conter dados sensiveis",
                    "policy": "alert_only",
                    "masking_applied": False,
                })
                break

    with open(path, "w") as f:
        json.dump(existing, f, indent=2, ensure_ascii=False)

    return path


def _update_recording_metadata(rec_dir: str, status: RecordingStatus) -> bool:
    """Update recording_metadata.json with new status."""
    meta_path = os.path.join(rec_dir, "recording_metadata.json")
    if not os.path.exists(meta_path):
        return False
    try:
        with open(meta_path) as f:
            meta = json.load(f)
        if "status_history" not in meta:
            meta["status_history"] = []

        meta["status_history"].append({
            "status": status.value,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "reason": f"interactive_completion: {status.value}",
            "metadata": {},
        })
        meta["recording_status"] = status.value
        meta["status"] = status.value
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(meta, f, indent=2, default=str)
        return True
    except Exception:
        return False
