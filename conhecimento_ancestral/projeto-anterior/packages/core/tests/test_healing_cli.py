from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone, timedelta
from pathlib import Path

import pytest
from typer.testing import CliRunner

from testforge.core.healing.models import HealingEntry
from testforge.core.healing.storage import HealingCatalog


runner = CliRunner()


@pytest.fixture
def catalog(tmp_path) -> HealingCatalog:
    db_path = tmp_path / "test_healing.jsonl"
    return HealingCatalog(str(db_path))


# ── B.5.5: _backup / _audit ───────────────────────────────────────────

def test_backup_creates_bak_file(catalog):
    entry = HealingEntry(system="sys", symptom="err", root_cause="rc", fix="fx")
    catalog.add(entry)
    catalog._backup()
    bak_path = Path(str(catalog._path) + ".bak")
    assert bak_path.exists()
    assert bak_path.read_text(encoding="utf-8") == catalog._path.read_text(encoding="utf-8")


def test_backup_no_catalog(tmp_path):
    c = HealingCatalog(str(tmp_path / "nonexistent.jsonl"))
    c._backup()


def test_audit_writes_log(catalog):
    catalog._audit("test_op", ["e1", "e2"], details="testing")
    audit_path = catalog._path.parent / "healing-audit.log"
    assert audit_path.exists()
    lines = audit_path.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 1
    record = json.loads(lines[0])
    assert record["operation"] == "test_op"
    assert record["entry_ids"] == ["e1", "e2"]
    assert record["details"] == "testing"
    assert "timestamp" in record
    assert record["user"] == os.environ.get("USER", "unknown")


def test_audit_appends(catalog):
    catalog._audit("op1", ["e1"])
    catalog._audit("op2", ["e2"])
    audit_path = catalog._path.parent / "healing-audit.log"
    lines = audit_path.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 2


# ── B.5.1: find_duplicates ────────────────────────────────────────────

def test_find_duplicates_none(catalog):
    catalog.add(HealingEntry(system="sys1", symptom="erro A", root_cause="rc", fix="fx"))
    catalog.add(HealingEntry(system="sys2", symptom="erro B", root_cause="rc", fix="fx"))
    assert catalog.find_duplicates() == []


def test_find_duplicates_exact(catalog):
    catalog.add(HealingEntry(system="sys", symptom="erro timeout", root_cause="rc", fix="fx1"))
    catalog.add(HealingEntry(system="sys", symptom="erro timeout", root_cause="rc", fix="fx2"))
    dupes = catalog.find_duplicates()
    assert len(dupes) == 1
    assert len(dupes[0]) == 2


def test_find_duplicates_case_insensitive(catalog):
    catalog.add(HealingEntry(system="SYS", symptom="Erro Timeout", root_cause="rc", fix="fx1"))
    catalog.add(HealingEntry(system="sys", symptom="erro timeout", root_cause="rc", fix="fx2"))
    dupes = catalog.find_duplicates()
    assert len(dupes) == 1


def test_find_duplicates_extra_spaces(catalog):
    catalog.add(HealingEntry(system="sys", symptom="erro  timeout", root_cause="rc", fix="fx1"))
    catalog.add(HealingEntry(system="sys", symptom="erro timeout", root_cause="rc", fix="fx2"))
    dupes = catalog.find_duplicates()
    assert len(dupes) == 1


def test_find_duplicates_leading_trailing_spaces(catalog):
    catalog.add(HealingEntry(system="  sys  ", symptom="  erro timeout  ", root_cause="rc", fix="fx1"))
    catalog.add(HealingEntry(system="sys", symptom="erro timeout", root_cause="rc", fix="fx2"))
    dupes = catalog.find_duplicates()
    assert len(dupes) == 1


# ── B.5.2: merge logic ────────────────────────────────────────────────

def test_merge_concatenates_notes_and_sums_failure_count(catalog):
    e1 = HealingEntry(system="sys", symptom="erro", root_cause="rc", fix="fx1",
                       notes="nota1", failure_count=3)
    e2 = HealingEntry(system="sys", symptom="erro", root_cause="rc", fix="fx2",
                       notes="nota2", failure_count=5)
    id1 = catalog.add(e1)
    id2 = catalog.add(e2)

    older, newer = (e1, e2) if e1.created_at <= e2.created_at else (e2, e1)

    catalog._backup()
    merged_notes = " | ".join(filter(None, [older.notes, newer.notes]))
    merged_fix = newer.fix or older.fix
    merged_failure_count = older.failure_count + newer.failure_count
    catalog.update(newer.id, fix=merged_fix, notes=merged_notes, failure_count=merged_failure_count)
    catalog.delete(older.id)
    catalog._audit("merge", [id1, id2], details=f"{older.id}→{newer.id}")

    remaining = catalog.get(newer.id)
    assert remaining is not None
    assert remaining.notes == "nota1 | nota2"
    assert remaining.failure_count == 8
    assert remaining.fix == "fx2"

    assert catalog.get(older.id) is None


def test_merge_preserves_newer_fix_when_older_has_no_fix(catalog):
    e1 = HealingEntry(system="sys", symptom="erro", root_cause="rc", fix="", notes="a")
    e2 = HealingEntry(system="sys", symptom="erro", root_cause="rc", fix="fx_ok", notes="b")
    id1 = catalog.add(e1)
    id2 = catalog.add(e2)

    older, newer = (e1, e2) if e1.created_at <= e2.created_at else (e2, e1)
    merged_fix = newer.fix or older.fix
    assert merged_fix == "fx_ok"

    catalog.update(newer.id, fix=merged_fix)
    assert catalog.get(newer.id).fix == "fx_ok"


# ── B.5.3: promote logic ──────────────────────────────────────────────

def test_promote_changes_fix_type_to_reviewed(catalog):
    entry = HealingEntry(system="sys", symptom="erro", root_cause="rc", fix="fx",
                          fix_type="learned")
    eid = catalog.add(entry)
    catalog._backup()
    now = datetime.now(timezone.utc).isoformat()
    catalog.update(eid, fix_type="reviewed", last_used_at=now)
    catalog._audit("promote", [eid])

    updated = catalog.get(eid)
    assert updated is not None
    assert updated.fix_type == "reviewed"
    assert updated.last_used_at == now


def test_promote_updates_last_used_at(catalog):
    entry = HealingEntry(system="sys", symptom="erro", root_cause="rc", fix="fx",
                          fix_type="unresolved")
    eid = catalog.add(entry)
    now = datetime.now(timezone.utc).isoformat()
    catalog.update(eid, fix_type="reviewed", last_used_at=now)
    updated = catalog.get(eid)
    assert updated.last_used_at == now


# ── B.5.4: delete with backup ─────────────────────────────────────────

def test_delete_with_backup(catalog):
    entry = HealingEntry(system="sys", symptom="erro", root_cause="rc", fix="fx")
    eid = catalog.add(entry)
    catalog._backup()
    bak_path = Path(str(catalog._path) + ".bak")
    assert bak_path.exists()

    catalog.delete(eid)
    assert catalog.get(eid) is None


def test_delete_nonexistent(catalog):
    assert catalog.delete("nonexistent") is False


# ── B.5.1: stale detection ────────────────────────────────────────────

def test_stale_entries_detected(catalog):
    old = HealingEntry(
        system="sys", symptom="old error", root_cause="rc", fix="fx",
        last_used_at=(datetime.now(timezone.utc) - timedelta(days=91)).isoformat(),
    )
    fresh = HealingEntry(
        system="sys", symptom="fresh error", root_cause="rc", fix="fx",
        last_used_at=datetime.now(timezone.utc).isoformat(),
    )
    catalog.add(old)
    catalog.add(fresh)

    now = datetime.now(timezone.utc)
    stale = []
    for entry in catalog.list(limit=100):
        if entry.last_used_at:
            try:
                last = datetime.fromisoformat(entry.last_used_at)
                if (now - last) > timedelta(days=90):
                    stale.append(entry)
            except (ValueError, TypeError):
                continue

    assert len(stale) == 1
    assert stale[0].id == old.id


def test_stale_entries_empty_last_used_at(catalog):
    entry = HealingEntry(system="sys", symptom="err", root_cause="rc", fix="fx")
    catalog.add(entry)
    now = datetime.now(timezone.utc)
    stale = []
    for e in catalog.list(limit=100):
        if e.last_used_at:
            try:
                last = datetime.fromisoformat(e.last_used_at)
                if (now - last) > timedelta(days=90):
                    stale.append(e)
            except (ValueError, TypeError):
                continue
    assert len(stale) == 0


# ── CLI integration: review ────────────────────────────────────────────

def test_cli_review_all_shows_sections(tmp_path):
    from testforge.core.cli.healing import healing_app
    db = tmp_path / "test.jsonl"
    cat = HealingCatalog(str(db))
    cat.add(HealingEntry(system="sys", symptom="erro A", root_cause="rc", fix="fx"))
    cat.add(HealingEntry(system="sys", symptom="erro A", root_cause="rc", fix="fx2"))
    cat.add(HealingEntry(system="sys", symptom="erro B", root_cause="rc", fix="fx",
                          fix_type="unresolved"))
    result = runner.invoke(healing_app, ["review", "--all", "--db", str(db)])
    assert result.exit_code == 0
    assert "Duplicados" in result.stdout or "duplicados" in result.stdout
    assert "Não Resolvidas" in result.stdout
    assert "Stale" in result.stdout or "stale" in result.stdout


def test_cli_review_no_flags_prints_hint(tmp_path):
    from testforge.core.cli.healing import healing_app
    db = tmp_path / "test.jsonl"
    result = runner.invoke(healing_app, ["review", "--db", str(db)])
    assert result.exit_code == 0
    assert "--stale" in result.stdout or "--duplicates" in result.stdout


# ── CLI integration: merge ─────────────────────────────────────────────

def test_cli_merge_different_group_rejected(tmp_path):
    from testforge.core.cli.healing import healing_app
    db = tmp_path / "test.jsonl"
    cat = HealingCatalog(str(db))
    id1 = cat.add(HealingEntry(system="sys1", symptom="erro A", root_cause="rc", fix="fx"))
    id2 = cat.add(HealingEntry(system="sys2", symptom="erro B", root_cause="rc", fix="fx2"))
    result = runner.invoke(healing_app, ["merge", id1, id2, "--db", str(db)], input="y\n")
    assert result.exit_code != 0


def test_cli_merge_nonexistent_entry(tmp_path):
    from testforge.core.cli.healing import healing_app
    db = tmp_path / "test.jsonl"
    result = runner.invoke(healing_app, ["merge", "invalid1", "invalid2", "--db", str(db)])
    assert result.exit_code != 0


# ── CLI integration: promote ───────────────────────────────────────────

def test_cli_promote_changes_fix_type(tmp_path):
    from testforge.core.cli.healing import healing_app
    db = tmp_path / "test.jsonl"
    cat = HealingCatalog(str(db))
    eid = cat.add(HealingEntry(system="sys", symptom="err", root_cause="rc", fix="fx",
                                fix_type="learned"))
    result = runner.invoke(healing_app, ["promote", eid, "--db", str(db)], input="y\n")
    assert result.exit_code == 0
    assert "promovida" in result.stdout.lower()

    updated = cat.get(eid)
    assert updated is not None
    assert updated.fix_type == "reviewed"
    assert updated.last_used_at != ""


def test_cli_promote_nonexistent(tmp_path):
    from testforge.core.cli.healing import healing_app
    result = runner.invoke(healing_app, ["promote", "invalid", "--db", str(tmp_path / "x.jsonl")])
    assert result.exit_code != 0


# ── CLI integration: delete ─────────────────────────────────────────────

def test_cli_delete_with_confirmation(tmp_path):
    from testforge.core.cli.healing import healing_app
    db = tmp_path / "test.jsonl"
    cat = HealingCatalog(str(db))
    eid = cat.add(HealingEntry(system="sys", symptom="err", root_cause="rc", fix="fx"))
    result = runner.invoke(healing_app, ["delete", eid, "--db", str(db)], input="y\n")
    assert result.exit_code == 0
    assert "removida" in result.stdout.lower()
    assert cat.get(eid) is None


def test_cli_delete_cancelled(tmp_path):
    from testforge.core.cli.healing import healing_app
    db = tmp_path / "test.jsonl"
    cat = HealingCatalog(str(db))
    eid = cat.add(HealingEntry(system="sys", symptom="err", root_cause="rc", fix="fx"))
    result = runner.invoke(healing_app, ["delete", eid, "--db", str(db)], input="n\n")
    assert "Cancelado" in result.stdout
    assert cat.get(eid) is not None


def test_cli_delete_creates_backup(tmp_path):
    from testforge.core.cli.healing import healing_app
    db = tmp_path / "test.jsonl"
    cat = HealingCatalog(str(db))
    eid = cat.add(HealingEntry(system="sys", symptom="err", root_cause="rc", fix="fx"))
    runner.invoke(healing_app, ["delete", eid, "--db", str(db)], input="y\n")
    bak = tmp_path / "test.jsonl.bak"
    assert bak.exists()
    assert "err" in bak.read_text(encoding="utf-8")
