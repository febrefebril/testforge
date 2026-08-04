
from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from tests.golden.regenerate_snapshots import SNAPSHOT_NAMES, build_actual, discover_cases

_SECRET_PATTERNS = [
    re.compile(r"(?i)(password|senha)\s*[=:]\s*(?!<)[^&\s\"']+"),
    re.compile(r"(?i)(access_token|refresh_token|id_token)\s*[=:]\s*(?!<)[^&\s\"']+"),
    re.compile(r"(?i)(state|nonce|code_verifier|code_challenge)=[^<&\s\"']+"),
    re.compile(r"(?<!\d)\d{11}(?!\d)"),
]


@pytest.mark.parametrize("case_dir", discover_cases(), ids=lambda p: p.name)
def test_golden_pipeline_regression(case_dir: Path) -> None:
    actual = build_actual(case_dir)
    for stage in SNAPSHOT_NAMES:
        snapshot_path = case_dir / "snapshots" / f"{stage}.json"
        assert snapshot_path.exists(), (
            f"Snapshot ausente: {snapshot_path}. "
            "Regeneracao e deliberada: python tests/golden/regenerate_snapshots.py"
        )
        expected = json.loads(snapshot_path.read_text(encoding="utf-8"))
        normalized_actual = json.loads(json.dumps(actual[stage], default=_json_default, sort_keys=True))
        assert normalized_actual == expected, (
            f"Regressao no estagio {stage} do caso {case_dir.name}. "
            "Nao atualize automaticamente: revise a mudanca semantica e, somente se esperada, "
            "execute python tests/golden/regenerate_snapshots.py e revise o diff."
        )


@pytest.mark.parametrize("case_dir", discover_cases(), ids=lambda p: p.name)
def test_golden_fixtures_do_not_contain_apparent_secrets(case_dir: Path) -> None:
    fixture_text = "\n".join(
        path.read_text(encoding="utf-8", errors="replace")
        for path in sorted(case_dir.rglob("*"))
        if path.is_file() and "snapshots" not in path.parts
    )
    findings = [pattern.pattern for pattern in _SECRET_PATTERNS if pattern.search(fixture_text)]
    assert not findings, f"Possivel segredo/PII em {case_dir.name}: {findings}"


def test_assertions_are_preserved_as_oracles_not_healed() -> None:
    case_dir = next(p for p in discover_cases() if p.name == "assertion_immutable")
    audit = build_actual(case_dir)["audit"]
    test_case = audit["test_case"]
    asserts = [step for step in test_case.steps if step.action == "assert"]
    assert [step.value for step in asserts] == ["R$ 3.333,33", "enabled"]
    assert all("healing" not in step.context for step in asserts)


def _json_default(value):
    import dataclasses
    if dataclasses.is_dataclass(value):
        return dataclasses.asdict(value)
    if isinstance(value, Path):
        return value.as_posix()
    raise TypeError(type(value).__name__)

