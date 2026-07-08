"""Fase 4 — Catalogo SQLite indexado por intent + persistencia LocatorResolver."""
from __future__ import annotations

import json
import os
import tempfile
from unittest.mock import MagicMock

import pytest

from testforge.healing.sqlite_intent_catalog import (
    IntentCatalog,
    IntentResolution,
    normalize_url,
)
from testforge.runtime.resolver import LocatorResolver


class TestUrlNormalization:
    def test_collapses_numeric_id(self):
        assert normalize_url("https://app/users/12345/edit") == \
            "host=app path=/users/*/edit"

    def test_strips_query_and_fragment(self):
        assert normalize_url("http://x/path?a=1&b=2#frag") == \
            "host=x path=/path"

    def test_keeps_non_standard_port(self):
        assert normalize_url("http://localhost:8765/") == \
            "host=localhost:8765 path=/"

    def test_collapses_uuid(self):
        url = "https://app/orders/550e8400-e29b-41d4-a716-446655440000/items"
        assert normalize_url(url) == "host=app path=/orders/*/items"

    def test_empty_url_safe(self):
        assert normalize_url("") == "host= path=/"

    def test_malformed_url_safe(self):
        out = normalize_url("not a url")
        assert "host=" in out and "path=" in out


class TestIntentCatalog:
    def _cat(self, tmpdir: str) -> IntentCatalog:
        return IntentCatalog(os.path.join(tmpdir, "test.sqlite"))

    def test_create_table_idempotent(self):
        with tempfile.TemporaryDirectory() as d:
            c1 = self._cat(d)
            c1.close()
            c2 = IntentCatalog(os.path.join(d, "test.sqlite"))
            assert c2.count() == 0
            c2.close()

    def test_record_then_lookup(self):
        with tempfile.TemporaryDirectory() as d:
            cat = self._cat(d)
            cat.record_success(
                intent_text='click button "Save"',
                url="http://app/orders/123/edit",
                action="click",
                resolved_call='get_by_role("button", name="Save")',
                resolved_selector='page.get_by_role("button", name="Save")',
            )
            row = cat.lookup('click button "Save"',
                             "http://app/orders/999/edit", "click")
            assert row is not None
            assert row.resolved_call == 'get_by_role("button", name="Save")'
            assert row.usage_count == 1
            assert row.success_count == 1
            cat.close()

    def test_lookup_returns_none_when_absent(self):
        with tempfile.TemporaryDirectory() as d:
            cat = self._cat(d)
            assert cat.lookup("missing", "http://x/", "click") is None
            cat.close()

    def test_repeat_record_increments_counts(self):
        with tempfile.TemporaryDirectory() as d:
            cat = self._cat(d)
            for _ in range(3):
                cat.record_success(
                    intent_text="x", url="http://a/", action="click",
                    resolved_call='get_by_role("button")',
                )
            row = cat.lookup("x", "http://a/", "click")
            assert row.usage_count == 3
            assert row.success_count == 3
            cat.close()

    def test_record_heal_updates_call(self):
        with tempfile.TemporaryDirectory() as d:
            cat = self._cat(d)
            cat.record_success(intent_text="x", url="http://a/", action="click",
                               resolved_call='get_by_role("button", name="Save")')
            cat.record_heal(intent_text="x", url="http://a/", action="click",
                            new_call='get_by_role("button", name="Salvar")',
                            attributes_at_heal={"aria-label": "Salvar"})
            row = cat.lookup("x", "http://a/", "click")
            assert row.resolved_call == 'get_by_role("button", name="Salvar")'
            assert row.attributes_at_heal == {"aria-label": "Salvar"}
            assert row.confidence < 1.0
            cat.close()

    def test_record_failure_drops_confidence_and_can_stale(self):
        with tempfile.TemporaryDirectory() as d:
            cat = self._cat(d)
            cat.record_success(intent_text="x", url="http://a/", action="click",
                               resolved_call='get_by_role("button")')
            # Cada falha subtrai 0.2 da confianca; comeca em 1.0.
            for _ in range(6):
                cat.record_failure("x", "http://a/", "click")
            row = cat.lookup("x", "http://a/", "click")
            # Entradas obsoletas sao excluidas da consulta
            assert row is None
            cat.close()

    def test_import_legacy_recipes(self):
        with tempfile.TemporaryDirectory() as d:
            jsonl = os.path.join(d, "old.jsonl")
            with open(jsonl, "w") as f:
                f.write(json.dumps({
                    "recipe_id": "abc123", "trigger_family": "locator",
                    "trigger_code": "NOT_FOUND", "trigger_pattern": "not found",
                    "trigger_framework": "angular",
                    "solution_strategy": "fallback_aria",
                    "solution_selector": "[aria-label='{}']",
                    "solution_js": "", "priority": 5,
                    "usage_count": 0, "success_count": 0,
                    "last_used": "", "status": "active",
                    "created_at": "2026-06-13T00:00:00Z",
                }) + "\n")
            cat = self._cat(d)
            n = cat.import_legacy_recipes(jsonl)
            assert n == 1
            cur = cat._conn.execute("SELECT recipe_id FROM legacy_recipes")
            assert cur.fetchone()[0] == "abc123"
            cat.close()

    def test_import_legacy_skips_malformed_lines(self):
        with tempfile.TemporaryDirectory() as d:
            jsonl = os.path.join(d, "mixed.jsonl")
            with open(jsonl, "w") as f:
                f.write("not json\n")
                f.write(json.dumps({"recipe_id": "ok"}) + "\n")
                f.write("\n")
            cat = self._cat(d)
            assert cat.import_legacy_recipes(jsonl) == 1
            cat.close()

    def test_export_jsonl(self):
        with tempfile.TemporaryDirectory() as d:
            cat = self._cat(d)
            cat.record_success(intent_text="x", url="http://a/", action="click",
                               resolved_call='get_by_role("button")')
            out = os.path.join(d, "out.jsonl")
            n = cat.export_jsonl(out)
            assert n == 1
            content = open(out).read()
            assert "get_by_role" in content
            cat.close()


class TestResolverSqlitePersistence:
    def test_resolve_persists_to_sqlite(self):
        page = MagicMock()
        page.url = "http://localhost:8765/credit/123/sim"
        loc = MagicMock(); loc.count.return_value = 1
        page.get_by_role.return_value = loc
        with tempfile.TemporaryDirectory() as d:
            cat = IntentCatalog(os.path.join(d, "c.sqlite"))
            resolver = LocatorResolver(page, sqlite_catalog=cat)
            cand = {"strategy": "playwright_native",
                    "playwright_call": 'get_by_role("button", name="Salvar")',
                    "selector": 'page.get_by_role("button", name="Salvar")',
                    "score": 0.95}
            resolver.resolve('click button "Salvar"', [cand], action="click")
            row = cat.lookup('click button "Salvar"',
                             "http://localhost:8765/credit/999/sim", "click")
            assert row is not None
            assert row.resolved_call == 'get_by_role("button", name="Salvar")'
            cat.close()

    def test_l0_sqlite_hit_skips_candidate_walk(self):
        page = MagicMock()
        page.url = "http://app/page"
        loc = MagicMock(); loc.count.return_value = 1
        page.get_by_role.return_value = loc
        with tempfile.TemporaryDirectory() as d:
            cat = IntentCatalog(os.path.join(d, "c.sqlite"))
            cat.record_success(intent_text="c1", url="http://app/page",
                               action="click",
                               resolved_call='get_by_role("button", name="X")',
                               resolved_selector='page.get_by_role("button", name="X")')
            # Resolver novo (sem cache em memoria); deve atingir SQLite L0
            resolver = LocatorResolver(page, sqlite_catalog=cat)
            result = resolver.resolve("c1", [], action="click")
            assert result.level == "L0_cache"
            assert result.strategy == "sqlite_cached"
            cat.close()

    def test_no_sqlite_argument_still_works(self):
        page = MagicMock()
        page.url = "http://x/"
        loc = MagicMock(); loc.count.return_value = 1
        page.get_by_role.return_value = loc
        resolver = LocatorResolver(page)  # no sqlite
        cand = {"strategy": "r", "playwright_call": 'get_by_role("button")',
                "selector": 'page.get_by_role("button")', "score": 0.9}
        result = resolver.resolve("c", [cand], action="click")
        assert result.level == "L1_candidate"
