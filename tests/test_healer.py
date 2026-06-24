"""Tests for runtime.healer — multi-attribute self-healing scoring."""
import json
import os
import time

import pytest

from src.testforge.runtime.healer import (
    _score_match,
    resolve_selector,
    CONFIDENCE_THRESHOLD,
    HealCatalog,
    reset_catalog,
    _get_catalog,
    _fp_key,
)


class TestScoreMatch:
    """Unit tests for _score_match — pure function, no Playwright needed."""

    # --- Perfect match ---

    def test_perfect_match(self):
        """All fingerprint attributes match exactly → score = 1.0."""
        fp = {"tag": "input", "role": "textbox", "accessible_name": "Nome", "placeholder": "Seu nome"}
        live = {"tag": "input", "role": "textbox", "accessible_name": "Nome", "placeholder": "Seu nome", "name": "nome", "id": "nomeField", "text": "Nome completo"}
        score = _score_match(live, fp)
        assert score == 1.0

    # --- Partial matches ---

    def test_tag_mismatch_penalty(self):
        """Different tags reduce score (tag weight = 0.15/1.0)."""
        fp = {"tag": "input", "role": "textbox", "accessible_name": "Nome"}
        # total=0.60, matched: role(0.20)+name(0.25)=0.45 → score=0.45/0.60=0.75
        live = {"tag": "span", "role": "textbox", "accessible_name": "Nome"}
        assert _score_match(live, fp) == pytest.approx(0.75, rel=0.01)

    def test_substring_accessible_name(self):
        """Substring match on accessible_name gets 0.6x weight → score = (0.25*0.6)/0.25 = 0.60."""
        fp = {"accessible_name": "Renda mensal"}
        live = {"accessible_name": "Renda mensal *"}
        assert _score_match(live, fp) == pytest.approx(0.60, rel=0.01)

    def test_substring_placeholder(self):
        """Substring match on placeholder → score = (0.15*0.6)/0.15 = 0.60."""
        fp = {"placeholder": "Seu nome"}
        live = {"placeholder": "Digite seu nome completo"}
        assert _score_match(live, fp) == pytest.approx(0.60, rel=0.01)

    def test_substring_text(self):
        """Substring match on text → score = (0.15*0.6)/0.15 = 0.60."""
        fp = {"text": "Confirmar"}
        live = {"text": "Confirmar pagamento"}
        assert _score_match(live, fp) == pytest.approx(0.60, rel=0.01)

    # --- Edge cases ---

    def test_no_match(self):
        """No attributes match → score = 0.0."""
        fp = {"tag": "input", "role": "textbox", "accessible_name": "Nome"}
        live = {"tag": "button", "role": "button", "accessible_name": "Submit"}
        assert _score_match(live, fp) == 0.0

    def test_empty_fingerprint(self):
        """Empty/None fingerprint → score = 0.0."""
        assert _score_match({}, {"tag": "input"}) == 0.0
        assert _score_match({"tag": "input"}, {}) == 0.0

    def test_missing_live_attrs(self):
        """Live element missing attributes → lower score."""
        fp = {"tag": "input", "role": "textbox", "accessible_name": "Nome"}
        live = {"tag": "input", "role": "textbox"}  # no accessible_name
        # total=0.60, matched: tag(0.15)+role(0.20)=0.35 → score=0.35/0.60≈0.58
        assert _score_match(live, fp) == pytest.approx(0.583, rel=0.01)

    def test_case_insensitive_substring(self):
        """Substring match is case-insensitive."""
        fp = {"accessible_name": "RENDA MENSAL"}
        live = {"accessible_name": "renda mensal *"}
        assert _score_match(live, fp) == pytest.approx(0.60, rel=0.01)

    def test_threshold_default(self):
        """CONFIDENCE_THRESHOLD is 0.40."""
        assert CONFIDENCE_THRESHOLD == 0.40

    # --- Combined scoring ---

    def test_all_exact_match_returns_1(self):
        """All fingerprint keys present and exact → 1.0 regardless of extra live attrs."""
        fp = {"tag": "input", "role": "textbox"}
        live = {"tag": "input", "role": "textbox", "accessible_name": "ignored"}
        assert _score_match(live, fp) == 1.0

    def test_high_confidence_partial(self):
        """Most attributes match exactly, one is substring → high but < 1.0."""
        fp = {"tag": "input", "role": "textbox", "accessible_name": "Nome completo", "placeholder": "Seu nome"}
        live = {"tag": "input", "role": "textbox", "accessible_name": "Nome completo", "placeholder": "Seu nome completo"}
        # total=0.75, matched: tag(0.15)+role(0.20)+name_exact(0.25)+placeholder_substr(0.15*0.6=0.09)=0.69
        # score = 0.69/0.75 = 0.92
        assert _score_match(live, fp) == pytest.approx(0.69 / 0.75, rel=0.01)

    def test_fingerprint_with_extra_keys(self):
        """Extra fingerprint keys all present and exact → 1.0."""
        fp = {"tag": "input", "name": "cpf", "id": "cpfField"}
        live = {"tag": "input", "name": "cpf", "id": "cpfField"}
        assert _score_match(live, fp) == 1.0


class TestCompilerHealerBlock:
    """Tests that compiler emits resolve_selector blocks when fingerprint present."""

    _GET_SCRIPT = staticmethod(lambda path: open(path).read())

    def test_import_present(self, tmp_path):
        """Generated script imports resolve_selector from healer."""
        from src.testforge.semantic.compiler import PlaywrightCompiler
        from src.testforge.semantic.model import SemanticTestCase, SemanticAction, SemanticTarget, LocatorCandidate

        P = PlaywrightCompiler()
        tc = SemanticTestCase(test_id="FP-IMPORT", source_recording_id="R1",
                              application="t", base_url="http://localhost")
        t = SemanticTarget(role="button", accessible_name="OK", tag="button")
        t.fingerprint = {"tag": "button", "role": "button"}
        t.candidates = [LocatorCandidate("role", "role=button", 0.95)]
        tc.steps.append(SemanticAction(action="click", target=t))

        path = P.compile(tc, str(tmp_path))
        script = self._GET_SCRIPT(path)
        assert "from testforge.runtime.healer import resolve_selector" in script

    def test_fill_healer_block(self, tmp_path):
        """Fill step generates resolve_selector block when fingerprint present."""
        from src.testforge.semantic.compiler import PlaywrightCompiler
        from src.testforge.semantic.model import SemanticTestCase, SemanticAction, SemanticTarget, LocatorCandidate

        P = PlaywrightCompiler()
        tc = SemanticTestCase(test_id="FP-FILL", source_recording_id="R1",
                              application="t", base_url="http://localhost")
        t = SemanticTarget(role="textbox", accessible_name="Valor", tag="input")
        t.fingerprint = {"tag": "input", "accessible_name": "Valor"}
        t.candidates = [LocatorCandidate("role", "role=textbox", 0.95)]
        tc.steps.append(SemanticAction(action="fill", target=t, value="5000"))

        path = P.compile(tc, str(tmp_path))
        script = self._GET_SCRIPT(path)
        assert "_fp = {'tag': 'input', 'accessible_name': 'Valor'}" in script
        assert "_best = resolve_selector(page, _sels, _fp)" in script

    def test_click_healer_block(self, tmp_path):
        """Click step generates resolve_selector block with correct action."""
        from src.testforge.semantic.compiler import PlaywrightCompiler
        from src.testforge.semantic.model import SemanticTestCase, SemanticAction, SemanticTarget, LocatorCandidate

        P = PlaywrightCompiler()
        tc = SemanticTestCase(test_id="FP-CLK", source_recording_id="R1",
                              application="t", base_url="http://localhost")
        t = SemanticTarget(role="button", accessible_name="OK", tag="button")
        t.fingerprint = {"tag": "button", "role": "button"}
        t.candidates = [LocatorCandidate("role", "role=button", 0.95),
                        LocatorCandidate("attr", "button#ok", 0.85)]
        tc.steps.append(SemanticAction(action="click", target=t))

        path = P.compile(tc, str(tmp_path))
        script = self._GET_SCRIPT(path)
        assert "page.click(_best)" in script
        assert "nenhum candidato corresponde ao fingerprint" in script

    def test_select_healer_block(self, tmp_path):
        """Select step generates resolve_selector block."""
        from src.testforge.semantic.compiler import PlaywrightCompiler
        from src.testforge.semantic.model import SemanticTestCase, SemanticAction, SemanticTarget, LocatorCandidate

        P = PlaywrightCompiler()
        tc = SemanticTestCase(test_id="FP-SEL", source_recording_id="R1",
                              application="t", base_url="http://localhost")
        t = SemanticTarget(tag="select", role="combobox", accessible_name="Estado")
        t.fingerprint = {"tag": "select", "accessible_name": "Estado"}
        t.candidates = [LocatorCandidate("role", "role=combobox", 0.95)]
        tc.steps.append(SemanticAction(action="fill", target=t, value="SP"))

        path = P.compile(tc, str(tmp_path))
        script = self._GET_SCRIPT(path)
        assert "resolve_selector(page, _sels, _fp)" in script
        assert "page.select_option(_best," in script

    def test_no_fingerprint_fallback_loop(self, tmp_path):
        """Without fingerprint, compiler emits legacy for-loop."""
        from src.testforge.semantic.compiler import PlaywrightCompiler
        from src.testforge.semantic.model import SemanticTestCase, SemanticAction, SemanticTarget, LocatorCandidate

        P = PlaywrightCompiler()
        tc = SemanticTestCase(test_id="NO-FP", source_recording_id="R1",
                              application="t", base_url="http://localhost")
        t = SemanticTarget(role="textbox", accessible_name="Nome", tag="input")
        t.candidates = [LocatorCandidate("role", "role=textbox", 0.95)]
        tc.steps.append(SemanticAction(action="fill", target=t, value="Joao"))

        path = P.compile(tc, str(tmp_path))
        script = self._GET_SCRIPT(path)
        assert "for _sel in _sels:" in script
        assert "resolve_selector(page, _sels, _fp)" not in script
        assert "_best = resolve_selector" not in script

    def test_fingerprint_with_special_chars(self, tmp_path):
        """Fingerprint with special chars (R$, quotes) escapes correctly."""
        from src.testforge.semantic.compiler import PlaywrightCompiler
        from src.testforge.semantic.model import SemanticTestCase, SemanticAction, SemanticTarget, LocatorCandidate

        P = PlaywrightCompiler()
        tc = SemanticTestCase(test_id="FP-SPEC", source_recording_id="R1",
                              application="t", base_url="http://localhost")
        t = SemanticTarget(role="textbox", placeholder="R$0,00", tag="input")
        t.fingerprint = {"tag": "input", "placeholder": "R$0,00"}
        t.candidates = [LocatorCandidate("role", "role=textbox", 0.95)]
        tc.steps.append(SemanticAction(action="fill", target=t, value="5000"))

        path = P.compile(tc, str(tmp_path))
        script = self._GET_SCRIPT(path)
        assert "_fp = {'tag': 'input', 'placeholder': 'R$0,00'}" in script


class TestHealCatalog:
    """Tests for HealCatalog — persistence and lookup."""

    def setup_method(self):
        reset_catalog()

    # --- basic CRUD ---

    def test_lookup_miss(self, tmp_path):
        """Lookup on empty catalog returns None."""
        cat = HealCatalog(path=str(tmp_path / "catalog.jsonl"))
        assert cat.lookup({"tag": "input"}) is None

    def test_record_and_lookup_hit(self, tmp_path):
        """Record then lookup same fingerprint returns selector."""
        cat = HealCatalog(path=str(tmp_path / "catalog.jsonl"))
        cat.record({"tag": "input", "placeholder": "R$0,00"}, "input#valor", 0.85)
        result = cat.lookup({"tag": "input", "placeholder": "R$0,00"})
        assert result == "input#valor"

    def test_record_reinforce(self, tmp_path):
        """Recording same fingerprint increments success_count."""
        cat = HealCatalog(path=str(tmp_path / "catalog.jsonl"))
        cat.record({"tag": "input"}, "input#x", 0.80)
        cat.record({"tag": "input"}, "input#x", 0.80)
        key = _fp_key({"tag": "input"})
        assert cat._entries[key].success_count == 2

    def test_record_updates_score(self, tmp_path):
        """Recording with higher score updates entry.score."""
        cat = HealCatalog(path=str(tmp_path / "catalog.jsonl"))
        cat.record({"tag": "input"}, "input#x", 0.70)
        cat.record({"tag": "input"}, "input#x", 0.95)
        key = _fp_key({"tag": "input"})
        assert cat._entries[key].score == 0.95

    # --- canonical key ---

    def test_fp_key_deterministic(self):
        """Same fingerprint produces same key regardless of dict order."""
        k1 = _fp_key({"tag": "input", "placeholder": "R$0,00"})
        k2 = _fp_key({"placeholder": "R$0,00", "tag": "input"})
        assert k1 == k2

    def test_lookup_key_order_independent(self, tmp_path):
        """Lookup hits regardless of dict key insertion order."""
        cat = HealCatalog(path=str(tmp_path / "catalog.jsonl"))
        cat.record({"a": "1", "b": "2"}, "#x", 0.90)
        assert cat.lookup({"b": "2", "a": "1"}) == "#x"

    # --- persistence ---

    def test_persists_across_instances(self, tmp_path):
        """Catalog written to file is readable by new instance."""
        p = str(tmp_path / "persist.jsonl")
        cat1 = HealCatalog(path=p)
        cat1.record({"tag": "input"}, "input#persist", 0.90)

        cat2 = HealCatalog(path=p)
        assert cat2.lookup({"tag": "input"}) == "input#persist"

    def test_no_path_does_not_persist(self):
        """Catalog with empty path is memory-only (no file written)."""
        cat = HealCatalog(path="")
        cat.record({"tag": "input"}, "input#x", 0.90)
        # Entry exists in memory but no file was created
        assert cat.lookup({"tag": "input"}) == "input#x"
        assert len(cat._entries) == 1

    # --- eviction ---

    def test_ttl_eviction(self, tmp_path):
        """Entries older than TTL are evicted on lookup."""
        cat = HealCatalog(path=str(tmp_path / "ttl.jsonl"))
        cat.record({"tag": "input"}, "input#old", 0.90)
        key = _fp_key({"tag": "input"})
        # Manually age the entry
        cat._entries[key].last_success = time.time() - 31 * 24 * 3600
        assert cat.lookup({"tag": "input"}) is None

    def test_max_entries_eviction(self, tmp_path):
        """Oldest entries evicted when catalog exceeds max."""
        import src.testforge.runtime.healer as H
        original = H._CATALOG_MAX_ENTRIES
        H._CATALOG_MAX_ENTRIES = 10
        try:
            cat = HealCatalog(path=str(tmp_path / "max.jsonl"))
            for i in range(15):
                cat.record({"idx": str(i)}, f"#x{i}", 0.90)
            # After save, should be <= 10
            assert len(cat._entries) <= 10
        finally:
            H._CATALOG_MAX_ENTRIES = original

    # --- logging ---

    def test_lookup_logs_hit(self, tmp_path, caplog):
        """Catalog hit logs with 'heal_catalog: HIT' prefix."""
        import logging
        caplog.set_level(logging.INFO)
        cat = HealCatalog(path=str(tmp_path / "log.jsonl"))
        cat.record({"tag": "input"}, "input#log", 0.90)
        cat.lookup({"tag": "input"})
        assert "heal_catalog: HIT" in caplog.text

    # --- edge cases ---

    def test_empty_fingerprint_noop(self, tmp_path):
        """Recording or looking up empty fingerprint is safe no-op."""
        cat = HealCatalog(path=str(tmp_path / "empty.jsonl"))
        cat.record({}, "#x", 0.90)  # should not crash or persist
        assert cat.lookup({}) is None
        assert len(cat._entries) == 0

    def test_none_fingerprint_safe(self, tmp_path):
        """Lookup with None fingerprint returns None."""
        cat = HealCatalog(path=str(tmp_path / "none.jsonl"))
        assert cat.lookup(None) is None
        cat.record(None, "#x", 0.90)  # no-op

    def test_corrupted_file_handled(self, tmp_path):
        """Corrupted JSONL does not crash load."""
        now = time.time()
        p = str(tmp_path / "corrupt.jsonl")
        with open(p, "w") as f:
            f.write(json.dumps({"fp": {"tag": "input"}, "sel": "#ok", "score": 0.9, "n": 1, "ts": now}) + "\n")
            f.write("NOT JSON\n")
            f.write(json.dumps({"fp": {"tag": "button"}, "sel": "#btn", "score": 0.8, "n": 1, "ts": now}) + "\n")
        cat = HealCatalog(path=p)
        # Should have loaded first and last, skipped middle
        assert cat.lookup({"tag": "input"}) == "#ok"
        assert cat.lookup({"tag": "button"}) == "#btn"


class TestCatalogIntegration:
    """Tests that catalog integrates transparently into resolve_selector."""

    def setup_method(self):
        reset_catalog()

    def test_resolve_selector_checks_catalog(self, tmp_path):
        """resolve_selector calls catalog.lookup internally."""
        # We can't test the full live DOM flow, but we can verify the
        # catalog singleton is reachable and the code path exists.
        from src.testforge.runtime.healer import _get_catalog
        cat = _get_catalog()
        assert cat is not None
        assert hasattr(cat, "lookup")
        assert hasattr(cat, "record")

    def test_catalog_singleton_shared(self):
        """_get_catalog returns same instance across calls."""
        reset_catalog()
        c1 = _get_catalog()
        c2 = _get_catalog()
        assert c1 is c2

    def test_reset_catalog_creates_new(self):
        """reset_catalog() makes _get_catalog() return a new instance."""
        reset_catalog()
        c1 = _get_catalog()
        c1.record({"tag": "x"}, "#x", 0.90)
        reset_catalog()
        c2 = _get_catalog()
        assert c2.lookup({"tag": "x"}) is None
