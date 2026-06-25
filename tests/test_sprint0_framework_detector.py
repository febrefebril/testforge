"""Sprint 0 — FrameworkDetector unit tests."""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from testforge.diagnostic.framework_detector import FrameworkDetector


def _page_with_eval(result: dict):
    page = MagicMock()
    page.evaluate = MagicMock(return_value=result)
    page.url = "http://example/"
    return page


class TestBundleAnalysis:
    def test_angular_bundle_detected_with_version(self):
        page = _page_with_eval({"evidence": [], "custom_components": []})
        det = FrameworkDetector(page, cdp_session=None)
        det._bundles_seen = ["https://app/runtime.angular-16.2.0.js"]
        out = det.detect()
        assert out["angular_version"] == "16.2.0"
        assert any("bundle[angular]" in e for e in out["evidence"])

    def test_primefaces_bundle(self):
        page = _page_with_eval({"evidence": [], "custom_components": []})
        det = FrameworkDetector(page, cdp_session=None)
        det._bundles_seen = ["https://app/primefaces/javax.faces.resource/primefaces.js"]
        out = det.detect()
        assert out["primefaces"] is True

    def test_mui_bundle(self):
        page = _page_with_eval({"evidence": [], "custom_components": []})
        det = FrameworkDetector(page, cdp_session=None)
        det._bundles_seen = ["https://cdn.com/@mui/material@5.14.0/index.js"]
        out = det.detect()
        assert out["mui"] is True


class TestPageEvalAggregation:
    def test_angular_material_from_dom(self):
        page = _page_with_eval({
            "angular": True,
            "angular_version": "16.2.0",
            "angular_material": True,
            "zone_js": True,
            "custom_components": ["dsc-input-currency", "dsc-button"],
            "shadow_dom_count": 14,
            "iframe_count": 0,
            "dom_size": 12450,
            "max_depth": 22,
            "interactive_elements": 87,
            "form_count": 3,
            "evidence": [
                "window.ng present",
                "[ng-version=16.2.0]",
                "Angular Material markers x12",
            ],
        })
        det = FrameworkDetector(page, cdp_session=None)
        out = det.detect()
        assert out["primary"] == "angular-material"
        assert out["angular_version"] == "16.2.0"
        assert out["zone_js"] is True
        assert "dsc-input-currency" in out["custom_components"]
        assert out["shadow_dom_count"] == 14
        assert any("ng-version" in e for e in out["evidence"])

    def test_primefaces_picked_over_unknown(self):
        page = _page_with_eval({
            "primefaces": True,
            "custom_components": [],
            "evidence": ["PrimeFaces ui-widget x42"],
            "shadow_dom_count": 0, "iframe_count": 0, "dom_size": 100,
            "max_depth": 5, "interactive_elements": 5, "form_count": 1,
        })
        det = FrameworkDetector(page, cdp_session=None)
        assert det.detect()["primary"] == "primefaces"

    def test_unknown_when_nothing_matches(self):
        page = _page_with_eval({
            "custom_components": [], "evidence": [],
            "shadow_dom_count": 0, "iframe_count": 0, "dom_size": 10,
            "max_depth": 3, "interactive_elements": 0, "form_count": 0,
        })
        det = FrameworkDetector(page, cdp_session=None)
        assert det.detect()["primary"] == "unknown"

    def test_custom_falls_through(self):
        page = _page_with_eval({
            "custom_components": ["my-app", "x-widget"],
            "evidence": ["custom elements"],
            "shadow_dom_count": 0, "iframe_count": 0, "dom_size": 10,
            "max_depth": 3, "interactive_elements": 0, "form_count": 0,
        })
        det = FrameworkDetector(page, cdp_session=None)
        assert det.detect()["primary"] == "custom"


class TestCDPAttach:
    def test_attach_safe_without_cdp(self):
        page = _page_with_eval({"evidence": [], "custom_components": []})
        det = FrameworkDetector(page, cdp_session=None)
        det.attach()  # must not raise
        det.detach()

    def test_attach_subscribes_when_cdp_present(self):
        page = _page_with_eval({"evidence": [], "custom_components": []})
        cdp = MagicMock()
        det = FrameworkDetector(page, cdp_session=cdp)
        det.attach()
        cdp.send.assert_any_call("Network.enable")
        cdp.on.assert_called_once()
        assert cdp.on.call_args.args[0] == "Network.responseReceived"

    def test_response_handler_records_bundles(self):
        page = _page_with_eval({"evidence": [], "custom_components": []})
        cdp = MagicMock()
        det = FrameworkDetector(page, cdp_session=cdp)
        det.attach()
        # Simulate CDP event
        det._on_response({"response": {"url": "https://app/runtime.angular-16.2.0.js"}})
        det._on_response({"response": {"url": "https://app/styles.css"}})
        assert len(det._bundles_seen) == 2

    def test_response_handler_tolerates_bad_payload(self):
        page = _page_with_eval({"evidence": [], "custom_components": []})
        det = FrameworkDetector(page, cdp_session=MagicMock())
        det._on_response({})        # no response key
        det._on_response({"response": {}})   # no url
        det._on_response({"response": {"url": None}})
        assert det._bundles_seen == []  # everything skipped silently


class TestSessionSkeleton:
    def test_diagnostic_session_writes_session_json(self, tmp_path):
        from testforge.diagnostic import DiagnosticSession
        page = _page_with_eval({
            "evidence": ["window.ng present"], "custom_components": ["my-x"],
            "angular": True, "angular_version": "16.0.0", "angular_material": False,
            "zone_js": True, "shadow_dom_count": 0, "iframe_count": 0,
            "dom_size": 100, "max_depth": 5, "interactive_elements": 3,
            "form_count": 1,
        })
        sess = DiagnosticSession(page=page, cdp_session=None,
                                  session_dir=str(tmp_path))
        sess.start()
        payload = sess.finalize()
        assert payload["framework_detection"]["primary"] == "angular"
        assert (tmp_path / "session.json").exists()
        import json
        on_disk = json.loads((tmp_path / "session.json").read_text())
        assert on_disk["session_id"]
        assert on_disk["tester_hash"]
