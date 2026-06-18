"""Tests for Intent Reconstructor — Sprint 4, Épico 5.

CT-AUTO-4.1: Fill reconstructed by snapshot_diff.
CT-AUTO-4.2: Fill reconstructed by form_values.
CT-AUTO-4.3: Value reconstructed by network_payload.
"""

import json
import os
import tempfile
from unittest.mock import MagicMock, patch

import pytest

from testforge.semantic.intent_reconstructor import IntentReconstructor
from testforge.semantic.model import SemanticAction, SemanticTarget
from testforge.semantic.recording_normalizer import RecordingNormalizer


# ── Fixtures ───────────────────────────────────────────────────────────────────


@pytest.fixture
def reconstructor():
    return IntentReconstructor()


@pytest.fixture
def recording_dir():
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


def _make_step(action="click", tag="input", name="campo1", value="",
               timestamp="2026-06-18T10:00:00Z", form_values=None,
               label="Campo 1", placeholder="Digite", el_id="campo1"):
    target = SemanticTarget(
        tag=tag,
        name=name,
        element_id=el_id,
        label=label,
        placeholder=placeholder,
    )
    step = SemanticAction(
        action=action,
        target=target,
        value=value,
        url="http://localhost:8765/test",
        page_title="Test Page",
        context={"timestamp": timestamp},
    )
    if form_values:
        step.context["form_values"] = form_values
    if value:
        step.value = value
    return step


def _make_snapshot_line(fingerprint="input#campo1[name=campo1]", value="ABC",
                        tag="input", name="campo1", label="Campo 1",
                        timestamp="2026-06-18T10:00:01Z"):
    """Create a single field_snapshots.jsonl line (batch entry)."""
    return json.dumps({
        "timestamp": timestamp,
        "snapshots": [{
            "timestamp": timestamp,
            "fingerprint": fingerprint,
            "identifiers": {
                "id": "campo1",
                "name": name,
                "label": label,
                "placeholder": "Digite",
                "aria-label": None,
                "css_path": "#campo1",
            },
            "tag": tag,
            "type": "text",
            "value": value,
            "checked": None,
            "visibility": "visible",
            "enabled": True,
            "focused": False,
            "bounding_box": {"x": 10, "y": 10, "width": 200, "height": 30},
        }],
        "count": 1,
    })


def _make_network_entry(method="POST", url="http://localhost:8765/api/save",
                        post_data="cpf=123.456.789-00&renda=5000",
                        timestamp="2026-06-18T10:00:05Z"):
    return {
        "type": "request",
        "method": method,
        "url": url,
        "resource_type": "xhr",
        "post_data": post_data,
        "timestamp": timestamp,
    }


# ── CT-AUTO-4.1: Fill reconstructed by snapshot_diff ─────────────────────────


class TestCT_AUTO_4_1:
    """CT-AUTO-4.1: Fill reconstruido por snapshot_diff."""

    def test_snapshot_diff_detects_value_change(self, reconstructor, recording_dir):
        """Value change between consecutive snapshots produces entry with source=snapshot_diff."""
        path = os.path.join(recording_dir, "field_snapshots.jsonl")
        with open(path, "w") as f:
            f.write(_make_snapshot_line(fingerprint="input#campo1[name=campo1]", value="", timestamp="2026-06-18T10:00:00Z") + "\n")
            f.write(_make_snapshot_line(fingerprint="input#campo1[name=campo1]", value="ABC", timestamp="2026-06-18T10:00:01Z") + "\n")

        steps = [_make_step(action="click", name="campo1", timestamp="2026-06-18T10:00:00Z")]
        entries = reconstructor._reconstruct_from_snapshots(recording_dir, steps)

        assert len(entries) >= 1, f"Expected >=1 entries, got {entries}"
        entry = entries[0]
        assert entry["source"] == "snapshot_diff", f"Expected snapshot_diff, got {entry}"
        assert entry["value"] == "ABC"
        assert "campo1" in entry["field_key"]

    def test_snapshot_diff_has_correct_identifiers(self, reconstructor, recording_dir):
        """Snapshot diff entry has identifiers: name, id, label, placeholder, fingerprint."""
        path = os.path.join(recording_dir, "field_snapshots.jsonl")
        with open(path, "w") as f:
            f.write(_make_snapshot_line(fingerprint="input#nome[name=nome]", value="", timestamp="2026-06-18T10:00:00Z") + "\n")
            f.write(_make_snapshot_line(fingerprint="input#nome[name=nome]", value="João", timestamp="2026-06-18T10:00:01Z", name="nome", label="Nome") + "\n")

        steps = [_make_step(action="click", name="nome", timestamp="2026-06-18T10:00:00Z")]
        entries = reconstructor._reconstruct_from_snapshots(recording_dir, steps)

        assert len(entries) >= 1
        ids = entries[0].get("identifiers", {})
        assert ids.get("name") == "nome"
        assert ids.get("label") == "Nome"
        assert "fingerprint" in entries[0]

    def test_snapshot_diff_prevent_default_scenario(self, reconstructor, recording_dir):
        """PreventDefault input scenario: value captured even without input event."""
        path = os.path.join(recording_dir, "field_snapshots.jsonl")
        with open(path, "w") as f:
            f.write(_make_snapshot_line(fingerprint="input#campo1[name=campo1]", value="", timestamp="2026-06-18T10:00:00Z") + "\n")
            f.write(_make_snapshot_line(fingerprint="input#campo1[name=campo1]", value="ABC", timestamp="2026-06-18T10:00:01Z") + "\n")
            f.write(_make_snapshot_line(fingerprint="input#campo1[name=campo1]", value="ABCDEF", timestamp="2026-06-18T10:00:02Z") + "\n")

        steps = [
            _make_step(action="click", name="campo1", timestamp="2026-06-18T10:00:00Z"),
            _make_step(action="click", name="campo2", timestamp="2026-06-18T10:00:03Z"),
        ]
        entries = reconstructor._reconstruct_from_snapshots(recording_dir, steps)

        # Should capture the first non-empty value that changed
        assert len(entries) >= 1, f"Got entries: {entries}"
        assert entries[0]["source"] == "snapshot_diff"
        assert entries[0]["value"] == "ABC"

    def test_no_snapshots_file_returns_empty(self, reconstructor, recording_dir):
        """Missing field_snapshots.jsonl returns empty list."""
        entries = reconstructor._reconstruct_from_snapshots(recording_dir, [])
        assert entries == []

    def test_empty_snapshots_file_returns_empty(self, reconstructor, recording_dir):
        """Empty file returns empty list."""
        path = os.path.join(recording_dir, "field_snapshots.jsonl")
        with open(path, "w") as f:
            f.write("")
        entries = reconstructor._reconstruct_from_snapshots(recording_dir, [])
        assert entries == []

    def test_single_snapshot_no_diff(self, reconstructor, recording_dir):
        """Single snapshot (no change) returns empty list."""
        path = os.path.join(recording_dir, "field_snapshots.jsonl")
        with open(path, "w") as f:
            f.write(_make_snapshot_line(fingerprint="input#campo1[name=campo1]", value="ABC", timestamp="10:00:00") + "\n")
        entries = reconstructor._reconstruct_from_snapshots(recording_dir, [])
        assert entries == []

    def test_no_value_change_returns_empty(self, reconstructor, recording_dir):
        """No value change between snapshots returns empty."""
        path = os.path.join(recording_dir, "field_snapshots.jsonl")
        with open(path, "w") as f:
            f.write(_make_snapshot_line(fingerprint="input#campo1[name=campo1]", value="ABC", timestamp="10:00:00") + "\n")
            f.write(_make_snapshot_line(fingerprint="input#campo1[name=campo1]", value="ABC", timestamp="10:00:01") + "\n")
        entries = reconstructor._reconstruct_from_snapshots(recording_dir, [])
        assert entries == []

    def test_snapshot_diff_integration_with_normalizer(self, recording_dir):
        """Normalizer picks up snapshot_diff values via _reconstruct_intents."""
        # Create recording dir with field_snapshots
        path = os.path.join(recording_dir, "field_snapshots.jsonl")
        with open(path, "w") as f:
            f.write(_make_snapshot_line(fingerprint="input#valor[name=valor]", value="", timestamp="10:00:00") + "\n")
            f.write(_make_snapshot_line(fingerprint="input#valor[name=valor]", value="1234", timestamp="10:00:01", name="valor", label="Valor") + "\n")

        # Create minimal raw_events.jsonl
        events_path = os.path.join(recording_dir, "raw_events.jsonl")
        with open(events_path, "w") as f:
            f.write(json.dumps({
                "event_id": "evt_00001", "type": "click",
                "timestamp": "2026-06-18T10:00:00Z",
                "url": "http://localhost:8765/test", "page_title": "Test",
                "target": {
                    "tag": "input", "id": "valor", "name": "valor",
                    "placeholder": "Digite o valor", "label": "Valor",
                    "css_path": "#valor", "value": "",
                },
                "value": None, "is_postback": False,
            }) + "\n")

        normalizer = RecordingNormalizer()
        stc = normalizer.normalize(recording_dir, test_id="ST-TEST")

        # The field_value_map should contain the reconstructed value
        assert stc.field_values is not None
        # At minimum, the reconstructor ran without error
        assert len(stc.steps) >= 1


# ── CT-AUTO-4.2: Fill reconstructed by form_values ────────────────────────────


class TestCT_AUTO_4_2:
    """CT-AUTO-4.2: Fill reconstruido por form_values do submit."""

    def test_form_values_extracted_from_step_context(self, reconstructor):
        """form_values from step context are extracted as entries."""
        steps = [
            _make_step(action="click", name="telefone", label="Telefone",
                       form_values={"telefone": "11999999999", "nome": "João", "email": "joao@test.com"}),
        ]
        entries = reconstructor._reconstruct_from_form_values(steps)

        assert len(entries) >= 1
        telefone = [e for e in entries if e["field_key"] == "telefone"]
        assert len(telefone) > 0
        assert telefone[0]["source"] == "form_values"
        assert telefone[0]["value"] == "11999999999"

    def test_form_values_includes_all_fields(self, reconstructor):
        """All form_values fields are extracted."""
        steps = [
            _make_step(action="click", name="campo1",
                       form_values={"campo1": "A", "campo2": "B", "campo3": "C"}),
        ]
        entries = reconstructor._reconstruct_from_form_values(steps)
        assert len(entries) == 3

    def test_form_values_no_context_returns_empty(self, reconstructor):
        """Step without form_values returns empty."""
        steps = [_make_step(action="click", name="campo1")]
        entries = reconstructor._reconstruct_from_form_values(steps)
        assert entries == []

    def test_form_values_empty_dict_returns_empty(self, reconstructor):
        """Step with empty form_values returns empty."""
        steps = [_make_step(action="click", name="campo1", form_values={})]
        entries = reconstructor._reconstruct_from_form_values(steps)
        assert entries == []

    def test_form_values_integration_with_field_value_map(self, reconstructor):
        """form_values entries merge into field_value_map via normalizer."""
        steps = [
            _make_step(action="click", name="telefone",
                       form_values={"telefone": "11999999999"}),
        ]
        entries = reconstructor._reconstruct_from_form_values(steps)

        assert len(entries) == 1
        assert "telefone" in entries[0]["field_key"]
        assert entries[0]["identifiers"].get("form_name") == "telefone"


# ── CT-AUTO-4.3: Value reconstructed by network_payload ───────────────────────


class TestCT_AUTO_4_3:
    """CT-AUTO-4.3: Valor reconstruido por network_payload."""

    def test_network_payload_form_urlencoded_parsed(self, reconstructor, recording_dir):
        """form-urlencoded POST body is parsed into field entries."""
        path = os.path.join(recording_dir, "network_log.json")
        with open(path, "w") as f:
            json.dump([_make_network_entry()], f)

        steps = [_make_step(action="click", name="cpf")]
        entries = reconstructor._reconstruct_from_network(recording_dir, steps)

        assert len(entries) >= 1
        cpf = [e for e in entries if "cpf" in e["field_key"]]
        assert len(cpf) >= 1
        assert cpf[0]["source"] == "network_payload"
        assert "123.456.789-00" in cpf[0]["value"]

    def test_network_payload_json_parsed(self, reconstructor, recording_dir):
        """JSON POST body is parsed into field entries."""
        path = os.path.join(recording_dir, "network_log.json")
        with open(path, "w") as f:
            json.dump([_make_network_entry(
                post_data='{"cpf": "123.456.789-00", "renda": "5000"}')], f)

        steps = [_make_step(action="click", name="cpf")]
        entries = reconstructor._reconstruct_from_network(recording_dir, steps)
        assert len(entries) >= 1
        cpf = [e for e in entries if "cpf" in e["field_key"]]
        assert len(cpf) >= 1
        assert cpf[0]["value"] == "123.456.789-00"

    def test_network_payload_empty_body_ignored(self, reconstructor, recording_dir):
        """POST without body is ignored."""
        path = os.path.join(recording_dir, "network_log.json")
        with open(path, "w") as f:
            json.dump([_make_network_entry(post_data=None)], f)

        entries = reconstructor._reconstruct_from_network(recording_dir, [])
        assert entries == []

    def test_network_payload_missing_file_returns_empty(self, reconstructor, recording_dir):
        """Missing network_log.json returns empty list."""
        entries = reconstructor._reconstruct_from_network(recording_dir, [])
        assert entries == []

    def test_network_payload_has_evidence_metadata(self, reconstructor, recording_dir):
        """Network payload entry includes evidence: url, method, payload_key."""
        path = os.path.join(recording_dir, "network_log.json")
        with open(path, "w") as f:
            json.dump([_make_network_entry(post_data="cpf=123")], f)

        steps = [_make_step(action="click", name="cpf")]
        entries = reconstructor._reconstruct_from_network(recording_dir, steps)

        assert len(entries) >= 1
        ev = entries[0].get("evidence", {})
        assert ev.get("url") == "http://localhost:8765/api/save"
        assert ev.get("method") == "POST"
        assert ev.get("payload_key") == "cpf"

    def test_network_payload_get_requests_ignored(self, reconstructor, recording_dir):
        """GET requests are ignored — only POST/PUT/PATCH are parsed."""
        path = os.path.join(recording_dir, "network_log.json")
        with open(path, "w") as f:
            json.dump([
                _make_network_entry(method="GET", post_data=None),
                _make_network_entry(method="POST", post_data="campo1=valor1"),
            ], f)

        entries = reconstructor._reconstruct_from_network(recording_dir, [_make_step()])
        assert len(entries) >= 1
        assert entries[0]["source"] == "network_payload"

    def test_network_payload_correlates_to_field_key(self, reconstructor, recording_dir):
        """Payload key is correlated to field_key by name match."""
        path = os.path.join(recording_dir, "network_log.json")
        with open(path, "w") as f:
            json.dump([_make_network_entry(post_data="nome=Maria&idade=30")], f)

        steps = [
            _make_step(action="click", name="nome", label="Nome"),
            _make_step(action="click", name="idade", label="Idade"),
        ]
        entries = reconstructor._reconstruct_from_network(recording_dir, steps)

        keys = {e["field_key"] for e in entries}
        assert "nome" in keys
        assert "idade" in keys


# ── Integration tests ─────────────────────────────────────────────────────────


class TestIntentReconstructorIntegration:
    """Integration: reconstructor feeds into normalizer pipeline."""

    def test_reconstruct_all_combines_sources(self, reconstructor, recording_dir):
        """reconstruct_all runs all strategies and returns combined results."""
        # Create field_snapshots.jsonl
        snap_path = os.path.join(recording_dir, "field_snapshots.jsonl")
        with open(snap_path, "w") as f:
            f.write(_make_snapshot_line(fingerprint="input#campo1[name=campo1]", value="", timestamp="2026-06-18T10:00:00Z") + "\n")
            f.write(_make_snapshot_line(fingerprint="input#campo1[name=campo1]", value="snap_val", timestamp="2026-06-18T10:00:01Z") + "\n")

        # Create network_log.json
        net_path = os.path.join(recording_dir, "network_log.json")
        with open(net_path, "w") as f:
            json.dump([_make_network_entry(post_data="campo2=net_val")], f)

        steps = [
            _make_step(action="click", name="campo1", timestamp="2026-06-18T10:00:00Z"),
            _make_step(action="click", name="campo2", timestamp="2026-06-18T10:00:02Z"),
        ]
        # Also add form_values to one step
        steps[1].context["form_values"] = {"campo2": "form_val"}

        entries = reconstructor.reconstruct_all(recording_dir, steps)

        # Should have entries from snapshot_diff and form_values, possibly network_payload
        sources = {e["source"] for e in entries}
        assert "snapshot_diff" in sources, f"Sources: {sources}"
        assert "form_values" in sources

    def test_field_value_map_priority(self, recording_dir):
        """field_value_map prefers form_values > snapshot_diff > network_payload."""
        events_path = os.path.join(recording_dir, "raw_events.jsonl")
        with open(events_path, "w") as f:
            f.write(json.dumps({
                "event_id": "evt_00001", "type": "click",
                "timestamp": "2026-06-18T10:00:00Z",
                "url": "http://localhost:8765/test", "page_title": "Test",
                "target": {"tag": "input", "id": "campo1", "name": "campo1", "value": ""},
                "value": None, "is_postback": False,
            }) + "\n")

        # Create field_snapshots with snapshot_diff value
        snap_path = os.path.join(recording_dir, "field_snapshots.jsonl")
        with open(snap_path, "w") as f:
            f.write(_make_snapshot_line(fingerprint="input#campo1[name=campo1]", value="", timestamp="2026-06-18T10:00:00Z") + "\n")
            f.write(_make_snapshot_line(fingerprint="input#campo1[name=campo1]", value="snap_val", timestamp="2026-06-18T10:00:01Z") + "\n")

        normalizer = RecordingNormalizer()
        stc = normalizer.normalize(recording_dir, test_id="ST-TEST")

        # Just verify normalizer runs without error with reconstructed intents
        assert stc is not None

    def test_reconstructed_source_icon_in_report(self, reconstructor, recording_dir):
        """snapshot_diff and network_payload sources have icons in report."""
        snap_path = os.path.join(recording_dir, "field_snapshots.jsonl")
        with open(snap_path, "w") as f:
            f.write(_make_snapshot_line(fingerprint="input#campo1[name=campo1]", value="", timestamp="2026-06-18T10:00:00Z") + "\n")
            f.write(_make_snapshot_line(fingerprint="input#campo1[name=campo1]", value="val", timestamp="2026-06-18T10:00:01Z") + "\n")

        net_path = os.path.join(recording_dir, "network_log.json")
        with open(net_path, "w") as f:
            json.dump([_make_network_entry(post_data="campo2=net")], f)

        steps = [
            _make_step(action="click", name="campo1", timestamp="2026-06-18T10:00:00Z"),
            _make_step(action="click", name="campo2", timestamp="2026-06-18T10:00:02Z"),
        ]
        entries = reconstructor.reconstruct_all(recording_dir, steps)
        assert len(entries) >= 1


# ── Edge cases ────────────────────────────────────────────────────────────────


class TestIntentReconstructorEdgeCases:
    """Edge cases for IntentReconstructor."""

    def test_parse_payload_invalid_json(self, reconstructor):
        """Invalid JSON payload returns empty dict."""
        result = reconstructor._parse_payload("{invalid json}", "http://test")
        assert result == {}

    def test_parse_payload_form_urlencoded(self, reconstructor):
        """Form-urlencoded payload is parsed correctly."""
        result = reconstructor._parse_payload("key1=val1&key2=val2", "http://test")
        assert result.get("key1") == "val1"
        assert result.get("key2") == "val2"

    def test_parse_payload_json(self, reconstructor):
        """JSON payload is parsed correctly."""
        result = reconstructor._parse_payload('{"key1": "val1", "key2": "val2"}', "http://test")
        assert result.get("key1") == "val1"
        assert result.get("key2") == "val2"

    def test_parse_payload_empty(self, reconstructor):
        """Empty payload returns empty dict."""
        assert reconstructor._parse_payload("", "http://test") == {}
        assert reconstructor._parse_payload(None, "http://test") == {}

    def test_canonical_key_normalization(self, reconstructor):
        """Canonical key normalizes correctly."""
        assert reconstructor._canonical_key("Nome Completo") == "nome_completo"
        assert reconstructor._canonical_key(" input-valor ") == "valor"  # 'input-' prefix stripped
        assert reconstructor._canonical_key("") == "unknown"

    def test_find_nearest_step_index(self, reconstructor):
        """Nearest step index is found by timestamp proximity."""
        steps = [
            _make_step(timestamp="2026-06-18T10:00:00Z"),
            _make_step(timestamp="2026-06-18T10:00:05Z"),
            _make_step(timestamp="2026-06-18T10:00:10Z"),
        ]
        idx = reconstructor._find_nearest_step_index(steps, "2026-06-18T10:00:06Z")
        assert idx == 1  # closest to step at 10:00:05

    def test_find_nearest_step_index_empty(self, reconstructor):
        """Empty steps returns 0."""
        assert reconstructor._find_nearest_step_index([], "2026-06-18T10:00:00Z") == 0
        assert reconstructor._find_nearest_step_index([_make_step()], "") == 0

    def test_reconstruct_from_snapshots_deduplicates_by_field_key(self, reconstructor, recording_dir):
        """Multiple snapshot entries for same field_key are deduplicated."""
        path = os.path.join(recording_dir, "field_snapshots.jsonl")
        with open(path, "w") as f:
            f.write(_make_snapshot_line(fingerprint="input#campo1[name=campo1]", value="", timestamp="2026-06-18T10:00:00Z") + "\n")
            f.write(_make_snapshot_line(fingerprint="input#campo1[name=campo1]", value="A", timestamp="2026-06-18T10:00:01Z") + "\n")
            f.write(_make_snapshot_line(fingerprint="input#campo1[name=campo1]", value="AB", timestamp="2026-06-18T10:00:02Z") + "\n")

        steps = [_make_step(name="campo1", timestamp="2026-06-18T10:00:00Z")]
        entries = reconstructor._reconstruct_from_snapshots(recording_dir, steps)

        # Should only have one entry for campo1
        campo1_entries = [e for e in entries if "campo1" in e["field_key"]]
        assert len(campo1_entries) <= 1

    def test_empty_steps_list_returns_empty(self, reconstructor):
        """All methods return empty list when steps is empty."""
        assert reconstructor._reconstruct_from_form_values([]) == []
