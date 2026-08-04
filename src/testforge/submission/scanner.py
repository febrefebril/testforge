
"""Offline, deterministic scanner. It never changes the source recording."""
from __future__ import annotations
import hashlib, re
from pathlib import Path
from .models import DecisionAction, FindingCategory, ScanReport, SensitiveFinding

_TEXT_EXTENSIONS = {".json", ".jsonl", ".md", ".txt", ".feature", ".py", ".html", ".xml", ".yaml", ".yml", ".env", ""}
_PATTERNS = [
    ("password", FindingCategory.SECRET, True, re.compile(r'(?i)(?:password|senha|pwd)(?:["\']?\s*[:=]\s*["\']?)([^&\s,"\'}]+)')),
    ("authorization", FindingCategory.SECRET, True, re.compile(r'(?i)(?:authorization|bearer)\s*[:= ]\s*([^&\s,"\'}]+)')),
    ("jwt", FindingCategory.SECRET, True, re.compile(r'\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}(?:\.[A-Za-z0-9_-]{5,})?\b')),
    ("authorization_code", FindingCategory.SECRET, True, re.compile(r'(?i)(?:^|[?&#"\s])code=([^&\s"\']{8,})')),
    ("code_verifier", FindingCategory.SECRET, True, re.compile(r'(?i)code_verifier=([^&\s"\']+)')),
    ("access_token", FindingCategory.SECRET, True, re.compile(r'(?i)(?:access_token|refresh_token|id_token)["\']?\s*[:=]\s*["\']?([^&\s,"\'}]+)')),
    ("session_code", FindingCategory.SESSION_TRANSIENT, False, re.compile(r'(?i)session_code=([^&\s"\']+)')),
    ("oidc_state", FindingCategory.SESSION_TRANSIENT, False, re.compile(r'(?i)(?:[?&#]|\b)state=([^&\s"\']+)')),
    ("oidc_nonce", FindingCategory.SESSION_TRANSIENT, False, re.compile(r'(?i)(?:[?&#]|\b)nonce=([^&\s"\']+)')),
    ("code_challenge", FindingCategory.SESSION_TRANSIENT, False, re.compile(r'(?i)code_challenge=([^&\s"\']+)')),
    ("cpf", FindingCategory.TEST_DATA, False, re.compile(r'(?<!\d)(\d{3}\.?\d{3}\.?\d{3}-?\d{2})(?!\d)')),
    ("cnpj", FindingCategory.TEST_DATA, False, re.compile(r'(?<!\d)(\d{2}\.?\d{3}\.?\d{3}/?\d{4}-?\d{2})(?!\d)')),
]

def _mask(value: str) -> str:
    value = value.strip()
    if len(value) <= 4: return "*" * len(value)
    return value[:3] + "***" + value[-2:]

def tree_sha256(root: str | Path) -> str:
    root = Path(root); h = hashlib.sha256()
    for path in sorted(p for p in root.rglob("*") if p.is_file()):
        rel = path.relative_to(root).as_posix().encode(); h.update(len(rel).to_bytes(8,"big")); h.update(rel)
        with path.open("rb") as f:
            for chunk in iter(lambda: f.read(1024*1024), b""): h.update(chunk)
    return h.hexdigest()

def scan_recording(recording_dir: str | Path) -> ScanReport:
    root = Path(recording_dir)
    if not root.is_dir(): raise FileNotFoundError(root)
    findings=[]; seen=set()
    for path in sorted(p for p in root.rglob("*") if p.is_file() and p.suffix.lower() in _TEXT_EXTENSIONS):
        rel=path.relative_to(root).as_posix()
        try: lines=path.read_text(encoding="utf-8",errors="replace").splitlines()
        except OSError: continue
        for line_no,line in enumerate(lines,1):
            for dtype,category,blocking,pattern in _PATTERNS:
                for match in pattern.finditer(line):
                    value=match.group(match.lastindex or 0)
                    if value.startswith("<") and value.endswith(">"):
                        continue
                    key=(rel,line_no,dtype,value)
                    if key in seen: continue
                    seen.add(key)
                    fid=hashlib.sha256(f"{rel}:{line_no}:{dtype}:{value}".encode()).hexdigest()[:16]
                    findings.append(SensitiveFinding(
                        finding_id=fid,file_path=rel,line=line_no,data_type=dtype,category=category,
                        masked_sample=_mask(value),proposed_action=DecisionAction.BLOCK if blocking else DecisionAction.SANITIZE,
                        blocking=blocking,reason="secret must never be committed" if blocking else "review or sanitize before Git"))
    blocking=sum(f.blocking for f in findings)
    return ScanReport(recording_id=root.name,source_sha256=tree_sha256(root),findings=findings,
                      blocking_findings=blocking,status="blocked" if blocking else ("review_required" if findings else "clean"))

