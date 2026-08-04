
"""Regenera snapshots golden de forma explicita e auditavel.

Uso consciente (na raiz do repositorio):
    python tests/golden/regenerate_snapshots.py

Revise o diff completo antes de commit. Este comando nunca e chamado
automaticamente pelo teste de regressao.
"""
from __future__ import annotations

import dataclasses
import copy
import json
import shutil
import sys
import tempfile
import types
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
# Garante que src/ aparece antes no path (layout src/)
_src = str(REPO_ROOT / "src")
if _src not in sys.path:
    sys.path.insert(0, _src)

# O normalizador importa capture_fingerprint por um pacote cujo __init__ carrega
# pytest-playwright. Golden tests nao abrem navegador; o stub mantem o harness
# estritamente offline quando o extra opcional nao estiver instalado.
if "pytest_playwright.pytest_playwright" not in sys.modules:
    package = types.ModuleType("pytest_playwright")
    module = types.ModuleType("pytest_playwright.pytest_playwright")
    module.page = None
    sys.modules.setdefault("pytest_playwright", package)
    sys.modules.setdefault("pytest_playwright.pytest_playwright", module)

from testforge.semantic.compiler import PlaywrightCompiler
from testforge.semantic.recording_normalizer import RecordingNormalizer
from testforge.semantic.stages import (
    AuditStage,
    CompactStage,
    DedupStage,
    LoadStage,
    NormalizationContext,
)

GOLDEN_ROOT = Path(__file__).resolve().parent
SNAPSHOT_NAMES = ("load", "dedup", "compact", "audit", "compile_v2")


def _jsonable(value):
    if dataclasses.is_dataclass(value):
        return {k: _jsonable(v) for k, v in dataclasses.asdict(value).items()}
    if isinstance(value, dict):
        return {str(k): _jsonable(v) for k, v in sorted(value.items())}
    if isinstance(value, (list, tuple)):
        return [_jsonable(v) for v in value]
    if isinstance(value, Path):
        return value.as_posix()
    return value


def _write_json(path: Path, payload) -> None:
    path.write_text(
        json.dumps(_jsonable(payload), ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def discover_cases() -> list[Path]:
    return sorted(path.parent for path in GOLDEN_ROOT.glob("*/case.json"))


def build_actual(case_dir: Path) -> dict[str, object]:
    config = json.loads((case_dir / "case.json").read_text(encoding="utf-8"))
    normalizer = RecordingNormalizer(use_pipeline=True)
    ctx = NormalizationContext(recording_dir=str(case_dir), **config)

    ctx = LoadStage().run(ctx)
    load = {"raw_events": copy.deepcopy(ctx.raw_events), "stats": copy.deepcopy(ctx.stats)}
    ctx = DedupStage(normalizer).run(ctx)
    dedup = {"raw_events": copy.deepcopy(ctx.raw_events), "stats": copy.deepcopy(ctx.stats)}
    ctx = CompactStage(normalizer).run(ctx)
    compact = {"raw_events": copy.deepcopy(ctx.raw_events), "stats": copy.deepcopy(ctx.stats)}

    test_case = normalizer.normalize(str(case_dir), **config)
    audit_ctx = NormalizationContext(
        recording_dir=str(case_dir), test_id=config["test_id"], test_case=test_case
    )
    audit_ctx = AuditStage(normalizer).run(audit_ctx)
    audit = {
        "test_case": test_case,
        "blind_spots": audit_ctx.blind_spots,
        "stats": audit_ctx.stats,
    }

    with tempfile.TemporaryDirectory(prefix="testforge-golden-") as tmp:
        output = Path(tmp)
        script_path = Path(PlaywrightCompiler().compile_v2(test_case, str(output)))
        candidates = {}
        candidate_dir = output / "candidates"
        if candidate_dir.exists():
            for candidate in sorted(candidate_dir.glob("*.json")):
                candidates[candidate.name] = json.loads(candidate.read_text(encoding="utf-8"))
        compile_v2 = {
            "script_name": script_path.name,
            "script": script_path.read_text(encoding="utf-8").replace("\r\n", "\n"),
            "candidates": candidates,
        }

    return {
        "load": load,
        "dedup": dedup,
        "compact": compact,
        "audit": audit,
        "compile_v2": compile_v2,
    }


def regenerate(case_dirs: list[Path] | None = None) -> None:
    for case_dir in case_dirs or discover_cases():
        actual = build_actual(case_dir)
        snapshot_dir = case_dir / "snapshots"
        snapshot_dir.mkdir(exist_ok=True)
        for name in SNAPSHOT_NAMES:
            _write_json(snapshot_dir / f"{name}.json", actual[name])
        print(f"snapshots regenerados: {case_dir.name}")


if __name__ == "__main__":
    regenerate()

