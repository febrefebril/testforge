
"""Prepare a sanitized copy; no Git operation exists in this module."""
from __future__ import annotations
import hashlib, json, os, re, shutil
from pathlib import Path
from .models import DecisionAction, FindingCategory, ScanReport, SubmissionDecision, SubmissionReport
from .scanner import scan_recording, tree_sha256

_REPLACEMENTS = {
 "password":"<SECRET>", "authorization":"<AUTHORIZATION>", "jwt":"<JWT>", "authorization_code":"<AUTH_CODE>",
 "code_verifier":"<CODE_VERIFIER>", "access_token":"<TOKEN>", "session_code":"<SESSION_CODE>",
 "oidc_state":"<OIDC_STATE>", "oidc_nonce":"<OIDC_NONCE>", "code_challenge":"<CODE_CHALLENGE>",
 "cpf":"<CPF_TEST_DATA>", "cnpj":"<CNPJ_TEST_DATA>",
}

def _decision_map(decision: SubmissionDecision): return {d.finding_id:d for d in decision.decisions}

def validate_decision(scan: ScanReport, decision: SubmissionDecision) -> None:
    if decision.recording_id != scan.recording_id: raise ValueError("decision recording_id mismatch")
    if decision.cancelled: return
    by_id=_decision_map(decision)
    for finding in scan.findings:
        selected=by_id.get(finding.finding_id)
        action=selected.action if selected else finding.proposed_action
        if finding.blocking and action == DecisionAction.PRESERVE:
            raise ValueError(f"blocking secret cannot be preserved: {finding.finding_id}")
        if action == DecisionAction.PRESERVE and finding.category != FindingCategory.TEST_DATA:
            raise ValueError(f"only controlled test data can be preserved: {finding.finding_id}")

def prepare_submission(recording_dir, output_root, decision: SubmissionDecision, dry_run=False) -> SubmissionReport:
    source=Path(recording_dir); before=tree_sha256(source); scan=scan_recording(source); validate_decision(scan,decision)
    if decision.cancelled:
        return SubmissionReport(recording_id=source.name,dry_run=dry_run,source_dir=str(source),source_sha256_before=before,
          source_sha256_after=tree_sha256(source),scan_status=scan.status,submission_allowed=False,status="cancelled",message="cancelled; no files or Git changes")
    if dry_run:
        return SubmissionReport(recording_id=source.name,dry_run=True,source_dir=str(source),source_sha256_before=before,
          source_sha256_after=tree_sha256(source),scan_status=scan.status,submission_allowed=False,
          status="dry_run",message="review completed; no files or Git changes")
    target=Path(output_root)/source.name
    if target.exists(): shutil.rmtree(target)
    shutil.copytree(source,target)
    by_id=_decision_map(decision); transformations=[]
    # Binary/opaque evidence cannot be proven safe in this minimal increment.
    # Keep it in the original only; fail closed for the Git-ready copy.
    text_extensions = {".json", ".jsonl", ".md", ".txt", ".feature", ".py", ".html", ".xml", ".yaml", ".yml", ".env", ""}
    for opaque in sorted(p for p in target.rglob("*") if p.is_file() and p.suffix.lower() not in text_extensions):
        rel = opaque.relative_to(target).as_posix()
        opaque.unlink()
        transformations.append({"file_path": rel, "action": "exclude", "reason": "opaque_binary_not_scannable"})
    findings_by_file={}
    for f in scan.findings: findings_by_file.setdefault(f.file_path,[]).append(f)
    for rel,findings in findings_by_file.items():
        path=target/rel
        if not path.is_file(): continue
        text=path.read_text(encoding="utf-8",errors="replace")
        for f in findings:
            selected=by_id.get(f.finding_id); action=selected.action if selected else f.proposed_action
            if action == DecisionAction.PRESERVE: continue
            marker=_REPLACEMENTS[f.data_type]
            # Re-scan targeted type and replace all exact matches matching masked sample location deterministically.
            from .scanner import _PATTERNS
            pattern=next(p for n,_,_,p in _PATTERNS if n==f.data_type)
            text=pattern.sub(lambda m: m.group(0).replace(m.group(m.lastindex or 0),marker),text)
            transformations.append({"finding_id":f.finding_id,"file_path":rel,"action":action.value,"replacement":marker})
        path.write_text(text,encoding="utf-8",newline="\n")
    sec=target/"sanitization"; sec.mkdir(exist_ok=True)
    (sec/"scan_report.json").write_text(scan.model_dump_json(indent=2),encoding="utf-8")
    (sec/"decision.json").write_text(decision.model_dump_json(indent=2),encoding="utf-8")
    (sec/"transformations.json").write_text(json.dumps(transformations,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    final_scan=scan_recording(target)
    if final_scan.blocking_findings:
        shutil.rmtree(target,ignore_errors=True)
        raise RuntimeError("sanitized package still contains blocking secrets; package removed")
    after=tree_sha256(source); package_hash=tree_sha256(target)
    report=SubmissionReport(recording_id=source.name,dry_run=False,source_dir=str(source),output_dir=str(target),
      source_sha256_before=before,source_sha256_after=after,package_sha256=package_hash,scan_status=final_scan.status,
      submission_allowed=True,status="prepared",message="sanitized copy prepared; not published")
    (sec/"submission_report.json").write_text(report.model_dump_json(indent=2),encoding="utf-8")
    return report

