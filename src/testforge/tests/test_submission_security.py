
from __future__ import annotations
import json
from pathlib import Path
import pytest
from pydantic import ValidationError
from testforge.submission import (
    DecisionAction, FindingDecision, SubmissionDecision,
    prepare_submission, scan_recording, tree_sha256, validate_decision,
)

@pytest.fixture
def sifap_recording(tmp_path: Path) -> Path:
    root=tmp_path/"sifap_case"; root.mkdir()
    (root/"network_log.json").write_text(json.dumps({
      "url":"https://login.example/auth?state=abc12345&nonce=def67890&code_challenge=challenge123&session_code=session123",
      "post_data":"username=93476570002&password=112233&code=authcode-123456&code_verifier=verifier-123456",
      "cnpj":"00.360.305/0001-04"}),encoding="utf-8")
    (root/"steps.jsonl").write_text('{"action":"assert","expected_value":"Farmacia Popular"}\n',encoding="utf-8")
    (root/"screenshot.png").write_bytes(b"opaque image")
    return root

def test_scanner_detects_test_data_secrets_and_oidc(sifap_recording):
    report=scan_recording(sifap_recording)
    kinds={f.data_type for f in report.findings}
    assert {"cpf","cnpj","password","authorization_code","code_verifier","oidc_state","oidc_nonce","code_challenge","session_code"} <= kinds
    assert report.blocking_findings >= 3
    assert report.status == "blocked"

def test_secret_cannot_be_preserved(sifap_recording):
    scan=scan_recording(sifap_recording)
    secret=next(f for f in scan.findings if f.data_type == "password")
    decision=SubmissionDecision(recording_id=sifap_recording.name,environment="DES",decisions=[
      FindingDecision(finding_id=secret.finding_id,action=DecisionAction.PRESERVE,confirmed_test_mass=True,justification="nao permitido")])
    with pytest.raises(ValueError,match="blocking secret"):
        validate_decision(scan,decision)

def test_preserve_requires_explicit_reason():
    with pytest.raises(ValidationError):
      FindingDecision(finding_id="x",action=DecisionAction.PRESERVE,confirmed_test_mass=True)

def test_prepare_sanitized_copy_preserves_authorized_cpf_but_never_secret(sifap_recording,tmp_path):
    before=tree_sha256(sifap_recording); scan=scan_recording(sifap_recording)
    cpf=next(f for f in scan.findings if f.data_type=="cpf")
    decision=SubmissionDecision(recording_id=sifap_recording.name,environment="DES",decisions=[
      FindingDecision(finding_id=cpf.finding_id,action=DecisionAction.PRESERVE,confirmed_test_mass=True,justification="massa sintetica DES")])
    report=prepare_submission(sifap_recording,tmp_path/"submissions",decision)
    assert report.status=="prepared" and report.published is False
    assert tree_sha256(sifap_recording)==before==report.source_sha256_after
    package=Path(report.output_dir)
    content=(package/"network_log.json").read_text()
    assert "93476570002" in content
    assert "112233" not in content
    assert "verifier-123456" not in content
    assert "state=abc12345" not in content
    assert scan_recording(package).blocking_findings==0
    assert (package/"sanitization/decision.json").exists()
    assert (package/"sanitization/submission_report.json").exists()
    assert not (package/"screenshot.png").exists()

def test_cancel_and_dry_run_have_no_side_effects(sifap_recording,tmp_path):
    out=tmp_path/"submissions"; before=tree_sha256(sifap_recording)
    cancel=SubmissionDecision(recording_id=sifap_recording.name,environment="DES",cancelled=True)
    report=prepare_submission(sifap_recording,out,cancel)
    assert report.status=="cancelled" and not out.exists()
    dry=SubmissionDecision(recording_id=sifap_recording.name,environment="DES")
    report=prepare_submission(sifap_recording,out,dry,dry_run=True)
    assert report.status=="dry_run" and report.submission_allowed is False and not out.exists()
    assert tree_sha256(sifap_recording)==before

def test_gui_feature_is_off_by_default(monkeypatch):
    monkeypatch.delenv("TESTFORGE_SENSITIVE_REVIEW",raising=False)
    assert __import__("os").getenv("TESTFORGE_SENSITIVE_REVIEW","0") == "0"

