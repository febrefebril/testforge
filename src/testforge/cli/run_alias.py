
"""Alias seguro e reversivel para o comando legado ``testforge run``."""
from __future__ import annotations
import getpass, hashlib, json, logging, os, platform
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Literal
from pydantic import BaseModel, ConfigDict, Field

logger = logging.getLogger(__name__)
REMOVAL_TARGET = date(2026, 8, 12)
MIGRATION_COMMAND = "testforge run-incremental <script>"
REDIRECT_FLAG = "TESTFORGE_RUN_REDIRECT_ENABLED"

class RunAliasTelemetry(BaseModel):
    """Evento estruturado de uso do alias depreciado."""
    model_config = ConfigDict(extra="forbid", frozen=True)
    schema_version: Literal["1.0"] = "1.0"
    event: Literal["deprecated_command_invoked"] = "deprecated_command_invoked"
    command: Literal["run"] = "run"
    delegated_to: Literal["run-incremental"] = "run-incremental"
    reason: str
    removal_target: date
    migration_command: str
    occurred_at: datetime
    consumer_hash: str = Field(min_length=16, max_length=16)
    invocation_count: int = Field(ge=1)

def _consumer_hash() -> str:
    raw = f"{platform.node()}|{getpass.getuser()}"
    return hashlib.sha256(raw.encode("utf-8", errors="replace")).hexdigest()[:16]

def _telemetry_path() -> Path:
    configured = os.getenv("TESTFORGE_TELEMETRY_FILE", "").strip()
    return Path(configured) if configured else Path.cwd()/".testforge"/"run_alias_usage.jsonl"

def _existing_count(path: Path) -> int:
    if not path.exists(): return 0
    count=0
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            try: count += json.loads(line).get("event") == "deprecated_command_invoked"
            except (json.JSONDecodeError, AttributeError): pass
    except OSError: return 0
    return count

def record_alias_usage() -> RunAliasTelemetry:
    path=_telemetry_path()
    event=RunAliasTelemetry(reason="legacy_verdict_can_report_false_success", removal_target=REMOVAL_TARGET,
        migration_command=MIGRATION_COMMAND, occurred_at=datetime.now(timezone.utc),
        consumer_hash=_consumer_hash(), invocation_count=_existing_count(path)+1)
    try:
        path.parent.mkdir(parents=True,exist_ok=True)
        with path.open("a",encoding="utf-8",newline="\n") as handle: handle.write(event.model_dump_json()+"\n")
    except OSError as exc: logger.warning("run_alias_telemetry_write_failed path=%s error=%s",path,exc)
    return event

def emit_deprecation(event: RunAliasTelemetry) -> None:
    payload=event.model_dump(mode="json")
    print("[TestForge] [DEPRECATED] `testforge run` foi redirecionado para `testforge run-incremental` "
          f"porque o veredito legado pode produzir falso sucesso. Remocao prevista: {event.removal_target.isoformat()}. "
          f"Migre para: {event.migration_command}.",flush=True)
    logger.warning("run_alias_deprecated %s",json.dumps(payload,ensure_ascii=False,sort_keys=True))

def _redirect_enabled() -> bool:
    return os.getenv(REDIRECT_FLAG,"1").strip().lower() not in {"0","false","no","off"}

def _with_incremental_defaults(args: Any) -> Any:
    defaults={"stop_on_failure":True,"interactive":False,"no_healing":False,"shadow":False,
              "capture":True,"strict_asserts":True,"debug_healing":False,"verify_ssl":False}
    for key,value in defaults.items():
        if not hasattr(args,key): setattr(args,key,value)
    return args

def run_legacy_alias(args: Any) -> None:
    event=record_alias_usage(); emit_deprecation(event)
    if not _redirect_enabled():
        logger.error("run_alias_redirect_disabled verdict=indeterminate")
        print(f"[TestForge] [INDETERMINADO] Redirecionamento desabilitado por {REDIRECT_FLAG}; o motor legado inseguro nao sera executado.",flush=True)
        raise SystemExit(2)
    if getattr(args,"save_output",False): logger.warning("run_alias_option_ignored option=--save-output")
    from testforge.cli._run_incremental_patch import cmd_run_incremental
    return cmd_run_incremental(_with_incremental_defaults(args))

