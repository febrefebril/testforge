"""Testes do EvidencePayload e integracao com EvidenceCollector."""
import pytest
from playwright.sync_api import Page

from testforge.healing import EvidencePayload
from testforge.evidence import EvidenceCollector


class TestEvidencePayloadValidation:
    def test_sufficient_with_dom_and_console(self):
        p = EvidencePayload(
            step_context={"action": "click"},
            dom_snapshot="<html><body>" + "x" * 100 + "</body></html>",
            console_errors=[{"text": "error", "level": "error", "timestamp": "2026-01-01"}],
        )
        p.validate()
        assert p.is_sufficient is True
        assert p.insufficiency_reason == ""

    def test_sufficient_with_dom_and_network(self):
        p = EvidencePayload(
            step_context={"action": "fill"},
            dom_snapshot="<html><body>" + "y" * 100 + "</body></html>",
            network_state=[{"method": "GET", "url": "http://localhost", "status": 200, "timing_ms": 100}],
        )
        p.validate()
        assert p.is_sufficient is True

    def test_sufficient_with_dom_and_screenshot(self):
        p = EvidencePayload(
            step_context={"action": "click"},
            dom_snapshot="<html><body>" + "z" * 100 + "</body></html>",
            screenshot_b64="fake-base64-data",
        )
        p.validate()
        assert p.is_sufficient is True

    def test_insufficient_no_dom(self):
        p = EvidencePayload(
            step_context={"action": "click"},
            dom_snapshot="",
            console_errors=[{"text": "err"}],
        )
        p.validate()
        assert p.is_sufficient is False
        assert "missing" in p.insufficiency_reason.lower()

    def test_insufficient_dom_too_short(self):
        p = EvidencePayload(
            step_context={"action": "click"},
            dom_snapshot="<html></html>",  # too short (<100 chars)
            console_errors=[{"text": "err"}],
        )
        p.validate()
        assert p.is_sufficient is False

    def test_insufficient_dom_only_no_context(self):
        p = EvidencePayload(
            step_context={"action": "click"},
            dom_snapshot="<html><body>" + "a" * 100 + "</body></html>",
        )
        p.validate()
        # DOM-only is now sufficient (bonus context is optional)
        assert p.is_sufficient is True
        assert "bonus context missing" in p.insufficiency_reason.lower()


class TestEvidencePayloadSanitize:
    def test_strips_script_tags(self):
        dirty = '<html><head><script>alert("xss")</script></head><body><p>Hello</p></body></html>'
        clean = EvidencePayload.sanitize_dom(dirty)
        assert "<script>" not in clean.lower()
        assert "alert" not in clean.lower()
        assert "Hello" in clean

    def test_strips_style_tags(self):
        dirty = '<html><head><style>.x{color:red}</style></head><body><p>World</p></body></html>'
        clean = EvidencePayload.sanitize_dom(dirty)
        assert "<style>" not in clean.lower()
        assert "World" in clean

    def test_strips_inline_event_handlers(self):
        dirty = '<html><body><button onclick="doStuff()" id="btn">Click</button></body></html>'
        clean = EvidencePayload.sanitize_dom(dirty)
        assert "onclick" not in clean.lower()
        assert "Click" in clean

    def test_truncates_large_html(self):
        big = "<html><body>" + ("<p>content</p>" * 2000) + "</body></html>"
        clean = EvidencePayload.sanitize_dom(big)
        assert len(clean) <= 3000
        assert "TRUNCATED" in clean

    def test_small_html_unchanged(self):
        small = "<html><body><p>Hello World</p></body></html>"
        clean = EvidencePayload.sanitize_dom(small)
        assert "Hello World" in clean
        assert len(clean) <= len(small) + 10  # may add whitespace collapse

    def test_empty_html(self):
        assert EvidencePayload.sanitize_dom("") == ""
        assert EvidencePayload.sanitize_dom(None) == ""


class TestEvidencePayloadTruncateUrl:
    def test_short_url_unchanged(self):
        url = "http://localhost:8765/api"
        assert EvidencePayload.truncate_url(url) == url

    def test_long_url_truncated(self):
        url = "https://example.com/" + ("x" * 200) + "/path"
        short = EvidencePayload.truncate_url(url)
        assert len(short) <= 120
        assert "..." in short

    def test_custom_max(self):
        url = "https://a" + ("b" * 100)
        short = EvidencePayload.truncate_url(url, max_chars=20)
        assert len(short) <= 20


class TestEvidencePayloadScreenshot:
    def test_screenshot_to_b64(self):
        b64 = EvidencePayload.screenshot_to_b64(b"fake-png-data-here")
        assert len(b64) > 0
        assert isinstance(b64, str)

    def test_screenshot_empty_bytes(self):
        b64 = EvidencePayload.screenshot_to_b64(b"")
        assert b64 == ""

    def test_screenshot_none(self):
        b64 = EvidencePayload.screenshot_to_b64(None)
        assert b64 == ""


class TestEvidencePayloadFactory:
    def test_from_collector(self):
        p = EvidencePayload.from_collector(
            step_context={"action": "fill", "selector": "input"},
            dom_html="<html><body>" + "x" * 100 + "</body></html>",
            console_entries=[{"text": "warn", "level": "warning", "timestamp": "2026"}],
            network_entries=[{"method": "GET", "url": "http://localhost/api", "status": 200, "timing_ms": 150}],
        )
        assert p.is_sufficient is True
        assert len(p.dom_snapshot) > 0
        assert len(p.console_errors) == 1

    def test_from_collector_minimal(self):
        p = EvidencePayload.from_collector(
            step_context={"action": "click"},
            dom_html="<html><body>" + "x" * 100 + "</body></html>",
        )
        # DOM-only is now sufficient (bonus context optional)
        assert p.is_sufficient is True


class TestEvidenceCollectorLLMPayload:
    def test_build_llm_payload_no_page(self):
        """Without a Playwright page, payload should be insufficient."""
        ec = EvidenceCollector(None)
        ec.start("test-run")
        p = ec.build_llm_payload({"action": "click", "selector": "#btn"})
        assert p.is_sufficient is False
        assert "DOM snapshot missing" in p.insufficiency_reason

    def test_build_llm_payload_with_page(self, page: Page):
        """With a Playwright page, payload should capture DOM."""
        page.set_content('<html><body><button id="btn">Click Me Now Please For Minimum Length Test</button><p>Some additional text content here to make sure the DOM is long enough for validation</p></body></html>')

        ec = EvidenceCollector(page)
        ec.start("test-live")
        page.wait_for_timeout(100)

        p = ec.build_llm_payload({"action": "click", "selector": "#btn"})
        assert "btn" in p.dom_snapshot
        assert len(p.dom_snapshot) >= 100

    def test_build_llm_payload_with_screenshot(self, page: Page):
        """With include_screenshot=True, screenshot should be in payload."""
        page.set_content('<html><body>' + ("<p>content for minimum length requirement to pass validation check</p>" * 5) + '</body></html>')

        ec = EvidenceCollector(page)
        ec.start("test-screenshot")

        p = ec.build_llm_payload(
            {"action": "click", "selector": "#btn"},
            include_screenshot=True,
        )
        assert len(p.screenshot_b64) > 0

    def test_console_buffer_captures_errors(self, page: Page):
        """Console errors during execution should be captured."""
        page.set_content('<html><body>' + ("<p>filler content for minimum dom length requirement test validation</p>" * 3) + '</body></html>')

        ec = EvidenceCollector(page)
        ec.start("test-console")

        # Trigger a console error
        page.evaluate("console.error('test error message for buffer')")
        page.wait_for_timeout(100)

        p = ec.build_llm_payload({"action": "click"})
        assert len(p.console_errors) > 0

    def test_clear_buffers(self, page: Page):
        """clear_buffers() should reset console and network buffers."""
        page.set_content('<html><body>' + ("<p>minimum dom length content for validation test check purposes here</p>" * 3) + '</body></html>')

        ec = EvidenceCollector(page)
        ec.start("test-clear")
        page.evaluate("console.warn('test warning')")
        page.wait_for_timeout(100)

        # Should have entries
        p1 = ec.build_llm_payload({"action": "click"})
        assert len(p1.console_errors) > 0

        # Clear and verify empty
        ec.clear_buffers()
        p2 = ec.build_llm_payload({"action": "click"})
        assert len(p2.console_errors) == 0
