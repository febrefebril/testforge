"""Testes para distincao click vs submit vs postback no Recorder.

Usa pagina de teste com padroes ASP classic e ASP.NET.
"""
import json
import os
import tempfile
from unittest.mock import MagicMock, patch

import pytest
from playwright.sync_api import Page


# ---------------------------------------------------------------------------
# Testes puros da funcao JS _tf_isSubmitTrigger (sem precisar de pagina real)
# ---------------------------------------------------------------------------

class TestIsSubmitTriggerJS:
    """Testa _tf_isSubmitTrigger via page.evaluate com elementos criados dinamicamente."""

    @pytest.fixture
    def page_with_overlay(self, page: Page):
        """Inject overlay JS into a blank page so _tf_isSubmitTrigger is available."""
        page.set_content("""
            <html><body>
            <form id="f1" action="/post" method="POST">
                <input type="submit" id="btn-input-submit" value="Submit">
                <input type="image" id="btn-input-image" src="x.png">
                <input type="text" id="txt-name" value="test">
                <button type="submit" id="btn-submit">Submit</button>
                <button type="button" id="btn-button">Button</button>
                <button id="btn-default">Default</button>
                <a href="javascript:__doPostBack('x','y')" id="link-dopostback-href">DPB href</a>
                <a href="javascript:void(0)" id="link-dopostback-onclick"
                   onclick="javascript:__doPostBack('a','b')">DPB onclick</a>
                <a href="javascript:WebForm_DoPostBackWithOptions({})" id="link-webform-href">WF href</a>
                <a href="javascript:void(0)" id="link-webform-onclick"
                   onclick="javascript:WebForm_DoPostBackWithOptions({})">WF onclick</a>
                <a href="javascript:document.forms['f1'].submit()" id="link-asp-href">ASP href</a>
                <a href="javascript:void(0)" id="link-asp-onclick"
                   onclick="javascript:document.forms['f1'].submit()">ASP onclick</a>
                <a href="page2.html" id="link-regular">Regular</a>
                <a href="javascript:void(0)" id="link-void">Void</a>
                <a href="javascript:alert('hi')" id="link-alert">Alert</a>
                <a href="javascript:document.location='page2.html'" id="link-location">Location</a>
                <span id="span-el">Span</span>
                <div id="div-el">Div</div>
            </form>
            </body></html>
        """)
        # Inject overlay JS
        from testforge.recorder.recorder_controller import RecorderController
        page.evaluate(RecorderController._OVERLAY_JS)
        return page

    # ---- Native submit elements ----

    def test_input_submit_is_trigger(self, page_with_overlay):
        result = page_with_overlay.evaluate(
            "() => _tf_isSubmitTrigger(document.getElementById('btn-input-submit'))"
        )
        assert result is True

    def test_input_image_is_trigger(self, page_with_overlay):
        result = page_with_overlay.evaluate(
            "() => _tf_isSubmitTrigger(document.getElementById('btn-input-image'))"
        )
        assert result is True

    def test_input_text_is_not_trigger(self, page_with_overlay):
        result = page_with_overlay.evaluate(
            "() => _tf_isSubmitTrigger(document.getElementById('txt-name'))"
        )
        assert result is False

    def test_button_submit_is_trigger(self, page_with_overlay):
        result = page_with_overlay.evaluate(
            "() => _tf_isSubmitTrigger(document.getElementById('btn-submit'))"
        )
        assert result is True

    def test_button_type_button_is_not_trigger(self, page_with_overlay):
        result = page_with_overlay.evaluate(
            "() => _tf_isSubmitTrigger(document.getElementById('btn-button'))"
        )
        assert result is False

    def test_button_default_type_is_trigger(self, page_with_overlay):
        """button without explicit type defaults to submit."""
        result = page_with_overlay.evaluate(
            "() => _tf_isSubmitTrigger(document.getElementById('btn-default'))"
        )
        assert result is True

    # ---- ASP.NET __doPostBack ----

    def test_dopostback_href_is_trigger(self, page_with_overlay):
        result = page_with_overlay.evaluate(
            "() => _tf_isSubmitTrigger(document.getElementById('link-dopostback-href'))"
        )
        assert result is True

    def test_dopostback_onclick_is_trigger(self, page_with_overlay):
        result = page_with_overlay.evaluate(
            "() => _tf_isSubmitTrigger(document.getElementById('link-dopostback-onclick'))"
        )
        assert result is True

    # ---- ASP.NET WebForm_DoPostBackWithOptions ----

    def test_webform_href_is_trigger(self, page_with_overlay):
        result = page_with_overlay.evaluate(
            "() => _tf_isSubmitTrigger(document.getElementById('link-webform-href'))"
        )
        assert result is True

    def test_webform_onclick_is_trigger(self, page_with_overlay):
        result = page_with_overlay.evaluate(
            "() => _tf_isSubmitTrigger(document.getElementById('link-webform-onclick'))"
        )
        assert result is True

    # ---- ASP classic document.forms[].submit() ----

    def test_asp_classic_href_is_trigger(self, page_with_overlay):
        result = page_with_overlay.evaluate(
            "() => _tf_isSubmitTrigger(document.getElementById('link-asp-href'))"
        )
        assert result is True

    def test_asp_classic_onclick_is_trigger(self, page_with_overlay):
        result = page_with_overlay.evaluate(
            "() => _tf_isSubmitTrigger(document.getElementById('link-asp-onclick'))"
        )
        assert result is True

    # ---- Non-trigger elements ----

    def test_regular_link_is_not_trigger(self, page_with_overlay):
        result = page_with_overlay.evaluate(
            "() => _tf_isSubmitTrigger(document.getElementById('link-regular'))"
        )
        assert result is False

    def test_void_link_is_not_trigger(self, page_with_overlay):
        result = page_with_overlay.evaluate(
            "() => _tf_isSubmitTrigger(document.getElementById('link-void'))"
        )
        assert result is False

    def test_alert_link_is_not_trigger(self, page_with_overlay):
        result = page_with_overlay.evaluate(
            "() => _tf_isSubmitTrigger(document.getElementById('link-alert'))"
        )
        assert result is False

    def test_document_location_is_not_trigger(self, page_with_overlay):
        """document.location is NOT a form submission — it's page navigation."""
        result = page_with_overlay.evaluate(
            "() => _tf_isSubmitTrigger(document.getElementById('link-location'))"
        )
        assert result is False

    def test_span_is_not_trigger(self, page_with_overlay):
        result = page_with_overlay.evaluate(
            "() => _tf_isSubmitTrigger(document.getElementById('span-el'))"
        )
        assert result is False

    def test_div_is_not_trigger(self, page_with_overlay):
        result = page_with_overlay.evaluate(
            "() => _tf_isSubmitTrigger(document.getElementById('div-el'))"
        )
        assert result is False

    def test_null_is_not_trigger(self, page_with_overlay):
        result = page_with_overlay.evaluate("() => _tf_isSubmitTrigger(null)")
        assert result is False


# ---------------------------------------------------------------------------
# Testes de integracao: click vs submit vs postback na pagina FAM-Submit
# ---------------------------------------------------------------------------

class TestClickVsSubmitIntegration:
    """Testa o fluxo completo: clique em elementos gera evento correto."""

    @pytest.fixture
    def submit_page(self, page: Page):
        """Load the fam-submit test page with recorder overlay injected."""
        import os as _os
        page_dir = _os.path.join(
            _os.path.dirname(__file__), "test_pages", "curation", "fam-submit"
        )
        page.goto(f"file://{page_dir}/index.html")
        # Overlay gets injected automatically after page load since we use add_init_script
        # But for direct testing, inject it manually
        from testforge.recorder.recorder_controller import RecorderController
        page.evaluate(RecorderController._OVERLAY_JS)
        page.evaluate("_tf_showOverlay()")
        page.wait_for_timeout(200)
        return page

    def _get_events(self, page: Page) -> list:
        """Read and clear event queue from JS."""
        return page.evaluate("""() => {
            var q = window.__tfEventQueue || [];
            window.__tfEventQueue = [];
            return q;
        }""")

    def test_input_submit_records_as_submit(self, submit_page):
        """Click on input[type=submit] records 'submit' event."""
        submit_page.click("#btn-submit-input")
        submit_page.wait_for_timeout(100)
        events = self._get_events(submit_page)
        assert len(events) >= 1, f"No events captured: {events}"
        event_types = [e["type"] for e in events]
        assert "submit" in event_types, f"Expected 'submit' in {event_types}"

    def test_button_submit_records_as_submit(self, submit_page):
        """Click on button[type=submit] records 'submit' event."""
        submit_page.click("#btn-submit-button")
        submit_page.wait_for_timeout(100)
        events = self._get_events(submit_page)
        event_types = [e["type"] for e in events]
        assert "submit" in event_types, f"Expected 'submit' in {event_types}"

    def test_regular_button_records_as_click(self, submit_page):
        """Click on button[type=button] records 'click' event, NOT submit."""
        submit_page.click("#btn-regular-button")
        submit_page.wait_for_timeout(100)
        events = self._get_events(submit_page)
        event_types = [e["type"] for e in events]
        assert "submit" not in event_types, (
            f"Button type=button should NOT be submit! Got: {event_types}"
        )
        assert "click" in event_types, f"Expected 'click' in {event_types}"

    def test_span_inside_form_records_as_click(self, submit_page):
        """Click on span inside form records 'click', NOT submit."""
        submit_page.click("#span-in-form")
        submit_page.wait_for_timeout(100)
        events = self._get_events(submit_page)
        event_types = [e["type"] for e in events]
        assert "submit" not in event_types, (
            f"Span inside form should NOT be submit! Got: {event_types}"
        )
        assert "click" in event_types, f"Expected 'click' in {event_types}"

    def test_regular_link_records_as_click(self, submit_page):
        """Click on regular link records 'click', NOT submit."""
        submit_page.click("#link-regular")
        submit_page.wait_for_timeout(100)
        events = self._get_events(submit_page)
        event_types = [e["type"] for e in events]
        assert "submit" not in event_types, (
            f"Regular link should NOT be submit! Got: {event_types}"
        )
        assert "click" in event_types, f"Expected 'click' in {event_types}"

    def test_asp_classic_link_records_as_submit(self, submit_page):
        """Click on ASP classic document.forms submit link records 'submit'."""
        submit_page.click("#link-asp-classic-href")
        submit_page.wait_for_timeout(100)
        events = self._get_events(submit_page)
        event_types = [e["type"] for e in events]
        assert "submit" in event_types, (
            f"ASP classic href should be submit! Got: {event_types}"
        )

    def test_dopostback_link_records_as_submit(self, submit_page):
        """Click on __doPostBack link records 'submit'."""
        submit_page.click("#link-postback-href")
        submit_page.wait_for_timeout(100)
        events = self._get_events(submit_page)
        event_types = [e["type"] for e in events]
        assert "submit" in event_types, (
            f"__doPostBack href should be submit! Got: {event_types}"
        )

    def test_dopostback_onclick_records_as_submit(self, submit_page):
        """Click on link with __doPostBack in onclick records 'submit'."""
        submit_page.click("#link-postback-onclick")
        submit_page.wait_for_timeout(100)
        events = self._get_events(submit_page)
        event_types = [e["type"] for e in events]
        assert "submit" in event_types, (
            f"__doPostBack onclick should be submit! Got: {event_types}"
        )

    def test_asp_classic_onclick_records_as_submit(self, submit_page):
        """Click on link with document.forms submit in onclick records 'submit'."""
        submit_page.click("#link-asp-classic-onclick")
        submit_page.wait_for_timeout(100)
        events = self._get_events(submit_page)
        event_types = [e["type"] for e in events]
        assert "submit" in event_types, (
            f"ASP classic onclick should be submit! Got: {event_types}"
        )

    def test_div_inside_form_records_as_click(self, submit_page):
        """Click on div inside form records 'click', NOT submit."""
        submit_page.click("#div-in-form")
        submit_page.wait_for_timeout(100)
        events = self._get_events(submit_page)
        event_types = [e["type"] for e in events]
        assert "submit" not in event_types, (
            f"Div inside form should NOT be submit! Got: {event_types}"
        )
        assert "click" in event_types, f"Expected 'click' in {event_types}"

    def test_link_inside_form_records_as_click_not_submit(self, submit_page):
        """Click on regular link inside a form records 'click', NOT submit."""
        submit_page.click("#link-inside-form")
        submit_page.wait_for_timeout(100)
        events = self._get_events(submit_page)
        event_types = [e["type"] for e in events]
        assert "submit" not in event_types, (
            f"Regular link inside form should be click! Got: {event_types}"
        )
        assert "click" in event_types, f"Expected 'click' in {event_types}"

    def test_alert_link_records_as_click_not_submit(self, submit_page):
        """Click on javascript:alert link records 'click', NOT submit."""
        submit_page.click("#link-alert")
        submit_page.wait_for_timeout(100)
        events = self._get_events(submit_page)
        event_types = [e["type"] for e in events]
        assert "submit" not in event_types, (
            f"Alert link should NOT be submit! Got: {event_types}"
        )
        assert "click" in event_types, f"Expected 'click' in {event_types}"

    def test_void_link_records_as_click_not_submit(self, submit_page):
        """Click on javascript:void(0) link records 'click', NOT submit."""
        submit_page.click("#link-void")
        submit_page.wait_for_timeout(100)
        events = self._get_events(submit_page)
        event_types = [e["type"] for e in events]
        assert "submit" not in event_types, (
            f"Void link should NOT be submit! Got: {event_types}"
        )
        assert "click" in event_types, f"Expected 'click' in {event_types}"

    def test_document_location_link_records_as_click(self, submit_page):
        """Click on document.location link records 'click' (not submit — it navigates, doesn't post)."""
        submit_page.click("#link-doc-location")
        submit_page.wait_for_timeout(100)
        events = self._get_events(submit_page)
        event_types = [e["type"] for e in events]
        assert "submit" not in event_types, (
            f"document.location should NOT be submit! Got: {event_types}"
        )
        assert "click" in event_types, f"Expected 'click' in {event_types}"

    def test_link_records_target_info(self, submit_page):
        """Regular click records target info with tag and text."""
        submit_page.click("#link-regular")
        submit_page.wait_for_timeout(100)
        events = self._get_events(submit_page)
        assert len(events) >= 1
        click_event = events[0]
        assert click_event.get("target") is not None
        assert click_event["target"]["tag"] == "a"
        assert "Regular" in click_event["target"].get("text", "")

    def test_submit_records_target_info(self, submit_page):
        """Submit event records target info with element details."""
        submit_page.click("#btn-submit-input")
        submit_page.wait_for_timeout(100)
        events = self._get_events(submit_page)
        submit_events = [e for e in events if e["type"] == "submit"]
        assert len(submit_events) >= 1, f"No submit events in {events}"
        target = submit_events[0].get("target") or {}
        assert target.get("tag") == "input", f"Expected input tag, got {target}"

    def test_extract_target_captures_onclick(self, submit_page):
        """_tf_extractTarget captures onclick attribute for postback elements."""
        result = submit_page.evaluate("""() => {
            var el = document.getElementById('link-postback-onclick');
            return _tf_extractTarget(el);
        }""")
        assert result is not None
        assert result.get("onclick") is not None
        assert "__doPostBack" in (result.get("onclick") or "")

    def test_extract_target_captures_href(self, submit_page):
        """_tf_extractTarget captures href attribute."""
        result = submit_page.evaluate("""() => {
            var el = document.getElementById('link-postback-href');
            return _tf_extractTarget(el);
        }""")
        assert result is not None
        href = result.get("href") or ""
        assert "__doPostBack" in href


# ---------------------------------------------------------------------------
# Testes de postback detection (page load after submit)
# ---------------------------------------------------------------------------

class TestPostbackDetection:
    """Testa deteccao de postback no page load apos submit."""

    @pytest.fixture
    def submit_page(self, page: Page):
        """Load fam-submit page with overlay."""
        import os as _os
        page_dir = _os.path.join(
            _os.path.dirname(__file__), "test_pages", "curation", "fam-submit"
        )
        page.goto(f"file://{page_dir}/index.html")
        from testforge.recorder.recorder_controller import RecorderController
        page.evaluate(RecorderController._OVERLAY_JS)
        page.evaluate("_tf_showOverlay()")
        page.wait_for_timeout(200)
        # Clear initial events
        page.evaluate("window.__tfEventQueue = []")
        return page

    def _get_events(self, page: Page) -> list:
        return page.evaluate("""() => {
            var q = window.__tfEventQueue || [];
            window.__tfEventQueue = [];
            return q;
        }""")

    def test_pending_submit_flag_set_on_submit_click(self, submit_page):
        """Apos clicar em submit, __tfPendingSubmit deve ser setado."""
        pending_before = submit_page.evaluate("() => window.__tfPendingSubmit")
        assert pending_before is None, f"Pending should be None before submit click"

        submit_page.click("#btn-submit-input")
        submit_page.wait_for_timeout(100)

        pending_after = submit_page.evaluate("() => window.__tfPendingSubmit")
        assert pending_after is not None, (
            f"Pending submit should be set after submit click"
        )
        # The form uses POST
        assert pending_after.get("method") in ("POST", ""), (
            f"Expected POST method, got: {pending_after}"
        )

    def test_no_pending_submit_on_regular_click(self, submit_page):
        """Clicar em elemento nao-submit NAO deve setar __tfPendingSubmit."""
        submit_page.evaluate("window.__tfPendingSubmit = null")  # ensure clean
        submit_page.click("#link-regular")
        submit_page.wait_for_timeout(100)

        pending = submit_page.evaluate("() => window.__tfPendingSubmit")
        assert pending is None, (
            f"Pending submit should be None after regular click, got: {pending}"
        )

    def test_no_pending_submit_on_div_in_form_click(self, submit_page):
        """Clicar em div dentro de form NAO deve setar __tfPendingSubmit."""
        submit_page.evaluate("window.__tfPendingSubmit = null")
        submit_page.click("#div-in-form")
        submit_page.wait_for_timeout(100)

        pending = submit_page.evaluate("() => window.__tfPendingSubmit")
        assert pending is None, (
            f"Pending submit should be None after div-in-form click, got: {pending}"
        )


# ---------------------------------------------------------------------------
# Testes do normalizador: postback skipped, submit → click
# ---------------------------------------------------------------------------

class TestPostbackNormalization:
    """Testa que o RecordingNormalizer trata postback e submit corretamente."""

    def test_postback_event_is_skipped(self):
        """postback events devem ser ignorados pelo normalizador."""
        from testforge.semantic.recording_normalizer import RecordingNormalizer

        normalizer = RecordingNormalizer()
        result = normalizer._convert_event({
            "type": "postback",
            "url": "http://localhost/page2",
            "page_title": "Page 2",
            "is_postback": True,
            "submit_method": "POST",
        })
        assert result is None, "postback events should be skipped"

    def test_submit_event_converts_to_click_action(self):
        """submit events sao convertidos para action='click'."""
        from testforge.semantic.recording_normalizer import RecordingNormalizer

        normalizer = RecordingNormalizer()
        result = normalizer._convert_event({
            "type": "submit",
            "url": "http://localhost/form",
            "page_title": "Form",
            "target": {"tag": "input", "text": "Submit", "id": "btn1"},
            "value": None,
            "submit_method": "POST",
        })
        assert result is not None, "submit event should produce an action"
        assert result.action == "click", f"Expected 'click', got '{result.action}'"
        assert result.context.get("is_submit") is True
        assert result.context.get("submit_method") == "POST"

    def test_click_event_passes_through(self):
        """click events normais passam sem alteracao."""
        from testforge.semantic.recording_normalizer import RecordingNormalizer

        normalizer = RecordingNormalizer()
        result = normalizer._convert_event({
            "type": "click",
            "url": "http://localhost/page",
            "page_title": "Page",
            "target": {"tag": "a", "text": "Link"},
            "value": None,
        })
        assert result is not None
        assert result.action == "click"
        assert not result.context.get("is_submit")


# ---------------------------------------------------------------------------
# Testes do RawRecordedEvent com campos de postback
# ---------------------------------------------------------------------------

class TestRawEventPostbackFields:
    """Testa que RawRecordedEvent serializa is_postback e submit_method."""

    def test_postback_event_to_dict(self):
        from testforge.recorder.raw_event import RawRecordedEvent

        evt = RawRecordedEvent(
            event_id="evt_00100",
            event_type="postback",
            url="http://localhost/page2",
            page_title="Page 2",
            is_postback=True,
            submit_method="POST",
        )
        d = evt.to_dict()
        assert d["type"] == "postback"
        assert d["is_postback"] is True
        assert d["submit_method"] == "POST"

    def test_submit_event_stores_method(self):
        from testforge.recorder.raw_event import RawRecordedEvent

        evt = RawRecordedEvent(
            event_id="evt_00001",
            event_type="submit",
            submit_method="GET",
        )
        d = evt.to_dict()
        assert d["submit_method"] == "GET"
        # is_postback should default to False for submit events
        assert d.get("is_postback") is not True

    def test_regular_click_omits_postback_fields(self):
        from testforge.recorder.raw_event import RawRecordedEvent

        evt = RawRecordedEvent(
            event_id="evt_00001",
            event_type="click",
        )
        d = evt.to_dict()
        assert "is_postback" not in d  # False is omitted
        assert "submit_method" not in d  # None is omitted
