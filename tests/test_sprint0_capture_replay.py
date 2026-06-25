"""Sprint 0 — CaptureQualityTracker + ReplayCheck unit tests."""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from testforge.diagnostic.capture_quality import (
    CaptureQualityTracker,
    detect_value_kind,
)
from testforge.diagnostic.replay_check import ReplayCheck


class TestValueKindDetection:
    @pytest.mark.parametrize("value,expected", [
        ("R$ 1.000,00", "currency_BR"),
        ("R$1.000,00", "currency_BR"),
        ("1000", "numeric"),
        ("12/12/1970", "date_BR"),
        ("2026-06-25", "date_ISO"),
        ("123.456.789-00", "cpf_BR"),
        ("12345678900", "cpf_BR"),
        ("user@example.com", "email"),
        ("(11) 91234-5678", "phone_BR"),
        ("01310-100", "cep_BR"),
        ("Alice da Silva", "alpha"),
        ("", "empty"),
        (None, "missing"),
        ("anything@weird mix", "other"),
    ])
    def test_kinds(self, value, expected):
        assert detect_value_kind(value) == expected


class TestCaptureQuality:
    def test_basic_fill_assessment(self):
        tracker = CaptureQualityTracker()
        ev = {
            "event_id": "evt_001",
            "type": "fill",
            "timestamp": "2026-06-25T00:00:00Z",
            "value": "R$ 1.000,00",
            "target": {
                "tag": "input",
                "role": "textbox",
                "label": "Renda mensal *",
                "placeholder": "R$0,00",
            },
        }
        out = tracker.assess(ev, target_data=ev["target"], candidates=[])
        assert out["action"] == "fill"
        assert out["capture_quality"]["value_kind"] == "currency_BR"
        assert out["capture_quality"]["value_source"] == "fill_event"
        assert out["capture_quality"]["value_len"] == len("R$ 1.000,00")
        assert "typing_not_captured" not in out["blind_spots"]

    def test_typing_not_captured_blind_spot(self):
        tracker = CaptureQualityTracker()
        ev = {
            "event_id": "evt_002", "type": "fill",
            "timestamp": "2026-06-25T00:00:01Z",
            "value": "",
            "target": {"tag": "input", "label": "X"},
        }
        out = tracker.assess(ev, target_data=ev["target"], candidates=[])
        assert "typing_not_captured" in out["blind_spots"]
        assert out["capture_quality"]["value_source"] == "missing"

    def test_long_gap_blind_spot(self):
        tracker = CaptureQualityTracker()
        ev1 = {"event_id": "e1", "type": "click",
               "timestamp": "2026-06-25T00:00:00Z",
               "target": {"tag": "button"}}
        ev2 = {"event_id": "e2", "type": "click",
               "timestamp": "2026-06-25T00:00:30Z",
               "target": {"tag": "button"}}
        tracker.assess(ev1, target_data=ev1["target"], candidates=[])
        out = tracker.assess(ev2, target_data=ev2["target"], candidates=[])
        assert "long_gap" in out["blind_spots"]
        assert out["timing"]["idle_before_ms"] >= 30_000

    def test_custom_ancestor_extracted_from_css_path(self):
        tracker = CaptureQualityTracker()
        ev = {
            "event_id": "e1", "type": "fill",
            "value": "1000",
            "target": {
                "tag": "input", "label": "X",
                "css_path": "app-root > app-calculadora > dsc-input-currency > input",
            },
        }
        out = tracker.assess(ev, target_data=ev["target"], candidates=[])
        assert "dsc-input-currency" in out["framework_signal"]["ancestor_custom_elements"]
        assert "app-root" in out["framework_signal"]["ancestor_custom_elements"]

    def test_overlay_click_noise_flagged(self):
        tracker = CaptureQualityTracker()
        ev = {"event_id": "e1", "type": "click",
              "target": {"tag": "div"}}
        cand = MagicMock(); cand.selector = "div.cdk-overlay-backdrop"
        cand.strategy = "css_path"; cand.score = 0.4
        out = tracker.assess(ev, target_data=ev["target"], candidates=[cand])
        assert out["framework_signal"]["is_inside_cdk_overlay"] is True
        assert "overlay_click_noise" in out["blind_spots"]

    def test_primary_selector_and_top3(self):
        tracker = CaptureQualityTracker()
        ev = {"event_id": "e1", "type": "click",
              "target": {"tag": "button", "role": "button", "accessible_name": "X"}}
        c1 = MagicMock(); c1.strategy = "role"; c1.selector = "role=button[name=X]"; c1.score = 0.9
        c2 = MagicMock(); c2.strategy = "aria_label"; c2.selector = "[aria-label=X]"; c2.score = 0.8
        c3 = MagicMock(); c3.strategy = "text"; c3.selector = "button:has-text(X)"; c3.score = 0.5
        out = tracker.assess(ev, target_data=ev["target"], candidates=[c1, c2, c3])
        assert out["selector_generated"]["primary"] == "role=button[name=X]"
        assert out["selector_generated"]["top3_strategies"] == ["role", "aria_label", "text"]
        assert out["selector_generated"]["stability_score"] == 0.9


class TestReplayCheckImmediate:
    def _page_finds(self):
        page = MagicMock(); page.url = "http://x/"
        loc = MagicMock(); loc.count.return_value = 1
        page.locator.return_value = loc
        return page

    def _page_misses(self):
        page = MagicMock(); page.url = "http://x/"
        loc = MagicMock(); loc.count.return_value = 0
        page.locator.return_value = loc
        return page

    def test_immediate_records_resolved(self):
        page = self._page_finds()
        rc = ReplayCheck(page, mode="immediate")
        cand = {"strategy": "css", "selector": "#foo", "score": 0.6}
        out = rc.check("step_001", [cand])
        assert out is not None
        assert out["resolved"] is True
        assert out["selector_attempted"] == "#foo"
        assert out["elapsed_ms"] >= 0

    def test_immediate_records_unresolved(self):
        page = self._page_misses()
        rc = ReplayCheck(page, mode="immediate")
        cand = {"strategy": "css", "selector": "#nope", "score": 0.2}
        out = rc.check("step_002", [cand])
        assert out["resolved"] is False
        assert out["selector_attempted"] == "#nope"

    def test_batched_defers_until_drain(self):
        page = self._page_finds()
        rc = ReplayCheck(page, mode="batched")
        assert rc.check("step_001", [{"strategy": "css", "selector": "#a", "score": 0.5}]) is None
        assert rc.check("step_002", [{"strategy": "css", "selector": "#b", "score": 0.5}]) is None
        drained = rc.drain()
        assert len(drained) == 2
        assert all(r["resolved"] for r in drained)
        assert rc.drain() == []

    def test_records_property_accumulates(self):
        page = self._page_finds()
        rc = ReplayCheck(page, mode="immediate")
        rc.check("s1", [{"strategy": "x", "selector": "#a", "score": 0.5}])
        rc.check("s2", [{"strategy": "x", "selector": "#b", "score": 0.5}])
        assert len(rc.records) == 2

    def test_first_candidate_failing_fallback_succeeds_records_fallback(self):
        page = MagicMock(); page.url = "http://x/"
        first = MagicMock(); first.count.return_value = 0
        second = MagicMock(); second.count.return_value = 1
        # First call returns missing locator; second returns hit
        page.locator.side_effect = [first, second]
        rc = ReplayCheck(page, mode="immediate")
        out = rc.check("s1", [
            {"strategy": "css1", "selector": "#a", "score": 0.5},
            {"strategy": "css2", "selector": "#b", "score": 0.4},
        ])
        assert out["resolved"] is True
        assert out["fallback_resolved_at_index"] == 1
        assert out["fallback_strategy"] == "css2"
        assert out["fallback_selector"] == "#b"
