"""Phase 6 — zero-dep tracer + static dashboard.

Verifies:
- Tracer writes JSONL spans with OTel-compatible attrs
- Disabled tracer is a no-op
- Span nesting carries trace_id forward and sets parent_span_id
- LocatorResolver emits a 'resolve' span with level/strategy/score
- Dashboard renders HTML from spans + catalog without errors
"""
from __future__ import annotations

import json
import os
import tempfile
from unittest.mock import MagicMock

import pytest

from testforge.metrics import telemetry
from testforge.metrics.dashboard import (
    _compute_resolve_metrics,
    _hist_buckets,
    generate_html,
    write_dashboard,
)
from testforge.metrics.telemetry import Tracer, get_tracer, reset_tracer
from testforge.runtime.resolver import LocatorResolver


@pytest.fixture(autouse=True)
def _reset_tracer():
    reset_tracer()
    yield
    reset_tracer()


class TestTracer:
    def test_writes_jsonl_span(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "spans.jsonl")
            t = Tracer(spans_path=path)
            with t.start_span("test") as span:
                span.set_attribute("intent_text", "click X")
                span.set_attribute("level", "L1_candidate")
            assert os.path.exists(path)
            data = json.loads(open(path).read().strip())
            assert data["name"] == "test"
            assert data["attributes"]["intent_text"] == "click X"
            assert data["attributes"]["level"] == "L1_candidate"
            assert data["duration_ms"] >= 0
            assert data["status"] == "ok"
            assert data["trace_id"]
            assert data["span_id"]
            assert data["parent_span_id"] is None

    def test_disabled_writes_nothing(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "spans.jsonl")
            t = Tracer(spans_path=path, enabled=False)
            with t.start_span("x") as span:
                span.set_attribute("k", "v")
            assert not os.path.exists(path)

    def test_nested_spans_share_trace_id(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "spans.jsonl")
            t = Tracer(spans_path=path)
            with t.start_span("parent"):
                with t.start_span("child"):
                    pass
            lines = [json.loads(l) for l in open(path) if l.strip()]
            assert len(lines) == 2
            child, parent = lines  # child ends first → written first
            assert child["name"] == "child"
            assert parent["name"] == "parent"
            assert child["trace_id"] == parent["trace_id"]
            assert child["parent_span_id"] == parent["span_id"]

    def test_exception_sets_error_status(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "spans.jsonl")
            t = Tracer(spans_path=path)
            with pytest.raises(RuntimeError):
                with t.start_span("boom"):
                    raise RuntimeError("oops")
            data = json.loads(open(path).read().strip())
            assert data["status"] == "error"
            assert "oops" in data["attributes"]["error.message"]

    def test_env_var_disables(self, monkeypatch):
        monkeypatch.setenv("TESTFORGE_TRACING", "0")
        reset_tracer()
        with tempfile.TemporaryDirectory() as d:
            t = get_tracer(os.path.join(d, "x.jsonl"))
            assert not t.enabled


class TestResolverTracing:
    def test_resolve_emits_span(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "spans.jsonl")
            telemetry._tracer = Tracer(spans_path=path)
            page = MagicMock()
            page.url = "http://x/"
            loc = MagicMock(); loc.count.return_value = 1
            page.get_by_role.return_value = loc
            resolver = LocatorResolver(page)
            resolver.resolve(
                'click button "X"',
                [{"strategy": "r", "playwright_call": 'get_by_role("button")',
                  "selector": 'page.get_by_role("button")', "score": 0.9}],
                action="click",
            )
            spans = [json.loads(l) for l in open(path) if l.strip()]
            assert any(s["name"] == "resolve" for s in spans)
            resolve_span = next(s for s in spans if s["name"] == "resolve")
            assert resolve_span["attributes"]["intent_text"] == 'click button "X"'
            assert resolve_span["attributes"]["level"] == "L1_candidate"
            assert resolve_span["attributes"]["action"] == "click"


class TestDashboardComputations:
    def test_hist_buckets(self):
        edges = [0, 5, 20, 100]
        counts = _hist_buckets([1, 3, 15, 50, 200, 4], edges)
        # buckets: [0,5), [5,20), >=100
        assert counts == [3, 1, 2]

    def test_compute_metrics_filters_non_resolve(self):
        spans = [
            {"name": "resolve", "attributes": {"level": "L0_cache",
             "strategy": "sqlite_cached", "intent_text": "i1"},
             "duration_ms": 1.5},
            {"name": "step.click", "attributes": {}, "duration_ms": 5.0},
            {"name": "resolve", "attributes": {"level": "L1_candidate",
             "strategy": "role", "intent_text": "i2"},
             "duration_ms": 30.0},
        ]
        m = _compute_resolve_metrics(spans)
        assert m["total_resolves"] == 2
        assert m["level_counts"] == {"L0_cache": 1, "L1_candidate": 1}
        assert m["strategy_counts"] == {"sqlite_cached": 1, "role": 1}


class TestDashboardHTML:
    def test_generate_html_no_files_safe(self):
        with tempfile.TemporaryDirectory() as d:
            html_str = generate_html(
                spans_path=os.path.join(d, "no.jsonl"),
                db_path=os.path.join(d, "no.sqlite"),
            )
        assert "<!doctype html>" in html_str
        assert "TestForge Dashboard" in html_str
        assert "chart.js" in html_str

    def test_write_dashboard_creates_file(self):
        with tempfile.TemporaryDirectory() as d:
            out = os.path.join(d, "sub/dash.html")
            written = write_dashboard(
                output_path=out,
                spans_path=os.path.join(d, "no.jsonl"),
                db_path=os.path.join(d, "no.sqlite"),
            )
            assert written == out
            assert os.path.exists(out)

    def test_dashboard_reflects_spans(self):
        with tempfile.TemporaryDirectory() as d:
            spans = os.path.join(d, "spans.jsonl")
            with open(spans, "w") as f:
                f.write(json.dumps({
                    "name": "resolve",
                    "attributes": {"level": "L0_cache",
                                   "strategy": "sqlite_cached",
                                   "intent_text": "click X"},
                    "duration_ms": 1.2,
                }) + "\n")
            html_str = generate_html(
                spans_path=spans, db_path=os.path.join(d, "no.sqlite"),
            )
            assert "L0_cache" in html_str
            assert "sqlite_cached" in html_str
            assert "click X" in html_str
