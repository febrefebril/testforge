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
        """Injeta JS do overlay em pagina em branco para disponibilizar _tf_isSubmitTrigger."""
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
        # Injeta JS do overlay
        from testforge.recorder.recorder_controller import RecorderController
        page.evaluate(RecorderController._OVERLAY_JS)
        return page

    # ---- Elementos de submit nativos ----

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
        """button sem type explicito padrao e submit."""
        result = page_with_overlay.evaluate(
            "() => _tf_isSubmitTrigger(document.getElementById('btn-default'))"
        )
        assert result is True

    # ---- __doPostBack do ASP.NET ----

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

    # ---- WebForm_DoPostBackWithOptions do ASP.NET ----

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

    # ---- document.forms[].submit() do ASP classic ----

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

    # ---- Elementos nao-acionadores ----

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
        """document.location NAO e um envio de formulario — e navegacao de pagina."""
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
        """Carrega pagina de teste fam-submit com overlay do recorder injetado via add_init_script.

        Usa add_init_script para o overlay persistir entre navegacoes,
        permitindo deteccao de postback em paginas subsequentes.
        """
        from testforge.recorder.recorder_controller import RecorderController
        page.add_init_script(RecorderController._OVERLAY_JS)
        import os as _os
        page_dir = _os.path.join(
            _os.path.dirname(__file__), "test_pages", "curation", "fam-submit"
        )
        page.goto(f"file://{page_dir}/index.html")
        page.evaluate("_tf_showOverlay()")
        page.wait_for_timeout(200)
        # Limpa eventos iniciais (navegacao + inicializacao do overlay)
        page.evaluate("window.__tfEventQueue = []")
        return page

    def _get_events(self, page: Page) -> list:
        """Le e limpa fila de eventos do JS."""
        return page.evaluate("""() => {
            var q = window.__tfEventQueue || [];
            window.__tfEventQueue = [];
            return q;
        }""")

    def test_input_submit_records_as_submit(self, submit_page):
        """Clique em input[type=submit] registra evento 'submit'."""
        submit_page.click("#btn-submit-input")
        submit_page.wait_for_timeout(100)
        events = self._get_events(submit_page)
        assert len(events) >= 1, f"Nenhum evento capturado: {events}"
        event_types = [e["type"] for e in events]
        assert "submit" in event_types, f"Esperado 'submit' em {event_types}"

    def test_button_submit_records_as_submit(self, submit_page):
        """Clique em button[type=submit] registra evento 'submit'."""
        submit_page.click("#btn-submit-button")
        submit_page.wait_for_timeout(100)
        events = self._get_events(submit_page)
        event_types = [e["type"] for e in events]
        assert "submit" in event_types, f"Esperado 'submit' em {event_types}"

    def test_regular_button_records_as_click(self, submit_page):
        """Clique em button[type=button] registra evento 'click', NAO submit."""
        submit_page.click("#btn-regular-button")
        submit_page.wait_for_timeout(100)
        events = self._get_events(submit_page)
        event_types = [e["type"] for e in events]
        assert "submit" not in event_types, (
            f"Button type=button NAO deveria ser submit! Obtido: {event_types}"
        )
        assert "click" in event_types, f"Esperado 'click' em {event_types}"

    def test_span_inside_form_records_as_click(self, submit_page):
        """Clique em span dentro de form registra 'click', NAO submit."""
        submit_page.click("#span-in-form")
        submit_page.wait_for_timeout(100)
        events = self._get_events(submit_page)
        event_types = [e["type"] for e in events]
        assert "submit" not in event_types, (
            f"Span dentro de form NAO deveria ser submit! Obtido: {event_types}"
        )
        assert "click" in event_types, f"Esperado 'click' em {event_types}"

    def test_asp_classic_link_produces_postback(self, submit_page):
        """Clique no link submit document.forms do ASP classic navega → evento submit sobrevive.

        O evento submit agora e salvo via handler beforeunload no sessionStorage
        e restaurado na nova pagina com metadados de postback (is_postback:true,
        submit_method). O normalizador trata isso como click com contexto is_submit.
        Nenhum evento postback separado e gerado — o evento submit e o registro
        autoritativo da acao do usuario, com postback como metadado.
        """
        submit_page.click("#link-asp-classic-href")
        submit_page.wait_for_timeout(100)
        events = self._get_events(submit_page)
        event_types = [e["type"] for e in events]
        # Evento submit sobrevive a navegacao via beforeunload → sessionStorage.
        # Carrega metadado is_postback:true em vez de um evento postback separado.
        assert "submit" in event_types, (
            f"ASP classic href deveria produzir evento submit (sobreviveu navegacao). Obtido: {event_types}"
        )
        # Verifica se o evento submit restaurado tem metadados de postback
        submit_events = [e for e in events if e["type"] == "submit"]
        assert len(submit_events) == 1, (
            f"Esperado exatamente 1 evento submit, obtido: {events}"
        )
        postback_submit = submit_events[0]
        assert postback_submit.get("is_postback") is True, (
            f"Submit restaurado deveria ter is_postback=true. Obtido: {postback_submit}"
        )
        assert postback_submit.get("submit_method") == "POST", (
            f"Esperado metodo POST, obtido: {postback_submit.get('submit_method')}"
        )

    def test_dopostback_link_records_as_submit(self, submit_page):
        """Clique em link __doPostBack registra 'submit'."""
        submit_page.click("#link-postback-href")
        submit_page.wait_for_timeout(100)
        events = self._get_events(submit_page)
        event_types = [e["type"] for e in events]
        assert "submit" in event_types, (
            f"__doPostBack href deveria ser submit! Obtido: {event_types}"
        )

    def test_dopostback_onclick_records_as_submit(self, submit_page):
        """Clique em link com __doPostBack no onclick registra 'submit'."""
        submit_page.click("#link-postback-onclick")
        submit_page.wait_for_timeout(100)
        events = self._get_events(submit_page)
        event_types = [e["type"] for e in events]
        assert "submit" in event_types, (
            f"__doPostBack onclick deveria ser submit! Obtido: {event_types}"
        )

    def test_asp_classic_onclick_records_as_submit(self, submit_page):
        """Clique em link com document.forms submit no onclick registra 'submit'."""
        submit_page.click("#link-asp-classic-onclick")
        submit_page.wait_for_timeout(100)
        events = self._get_events(submit_page)
        event_types = [e["type"] for e in events]
        assert "submit" in event_types, (
            f"ASP classic onclick deveria ser submit! Obtido: {event_types}"
        )

    def test_div_inside_form_records_as_click(self, submit_page):
        """Clique em div dentro de form registra 'click', NAO submit."""
        submit_page.click("#div-in-form")
        submit_page.wait_for_timeout(100)
        events = self._get_events(submit_page)
        event_types = [e["type"] for e in events]
        assert "submit" not in event_types, (
            f"Div dentro de form NAO deveria ser submit! Obtido: {event_types}"
        )
        assert "click" in event_types, f"Esperado 'click' em {event_types}"

    def test_link_inside_form_records_as_click_not_submit(self, submit_page):
        """Clique em link comum dentro de form registra 'click', NAO submit."""
        submit_page.click("#link-inside-form")
        submit_page.wait_for_timeout(100)
        events = self._get_events(submit_page)
        event_types = [e["type"] for e in events]
        assert "submit" not in event_types, (
            f"Link comum dentro de form deveria ser click! Obtido: {event_types}"
        )
        assert "click" in event_types, f"Esperado 'click' em {event_types}"

    def test_alert_link_records_as_click_not_submit(self, submit_page):
        """Clique em link javascript:alert registra 'click', NAO submit."""
        submit_page.click("#link-alert")
        submit_page.wait_for_timeout(100)
        events = self._get_events(submit_page)
        event_types = [e["type"] for e in events]
        assert "submit" not in event_types, (
            f"Link alert NAO deveria ser submit! Obtido: {event_types}"
        )
        assert "click" in event_types, f"Esperado 'click' em {event_types}"

    def test_void_link_records_as_click_not_submit(self, submit_page):
        """Clique em link javascript:void(0) registra 'click', NAO submit."""
        submit_page.click("#link-void")
        submit_page.wait_for_timeout(100)
        events = self._get_events(submit_page)
        event_types = [e["type"] for e in events]
        assert "submit" not in event_types, (
            f"Link void NAO deveria ser submit! Obtido: {event_types}"
        )
        assert "click" in event_types, f"Esperado 'click' em {event_types}"

    def test_document_location_link_records_as_click(self, submit_page):
        """Clique em link document.location registra 'click' (nao submit — navega, nao posta)."""
        submit_page.click("#link-doc-location")
        submit_page.wait_for_timeout(100)
        events = self._get_events(submit_page)
        event_types = [e["type"] for e in events]
        assert "submit" not in event_types, (
            f"document.location NAO deveria ser submit! Obtido: {event_types}"
        )
        assert "click" in event_types, f"Esperado 'click' em {event_types}"

    def test_link_records_target_info(self, submit_page):
        """Click comum registra info do target com tag e texto."""
        submit_page.click("#link-regular")
        submit_page.wait_for_timeout(100)
        events = self._get_events(submit_page)
        assert len(events) >= 1
        click_event = events[0]
        assert click_event.get("target") is not None
        assert click_event["target"]["tag"] == "a"
        assert "Regular" in click_event["target"].get("text", "")

    def test_submit_records_target_info(self, submit_page):
        """Evento submit registra info do target com detalhes do elemento."""
        submit_page.click("#btn-submit-input")
        submit_page.wait_for_timeout(100)
        events = self._get_events(submit_page)
        submit_events = [e for e in events if e["type"] == "submit"]
        assert len(submit_events) >= 1, f"Nenhum evento submit em {events}"
        target = submit_events[0].get("target") or {}
        assert target.get("tag") == "input", f"Esperado tag input, obtido {target}"

    def test_extract_target_captures_onclick(self, submit_page):
        """_tf_extractTarget captura atributo onclick para elementos postback."""
        result = submit_page.evaluate("""() => {
            var el = document.getElementById('link-postback-onclick');
            return _tf_extractTarget(el);
        }""")
        assert result is not None
        assert result.get("onclick") is not None
        assert "__doPostBack" in (result.get("onclick") or "")

    def test_extract_target_captures_href(self, submit_page):
        """_tf_extractTarget captura atributo href."""
        result = submit_page.evaluate("""() => {
            var el = document.getElementById('link-postback-href');
            return _tf_extractTarget(el);
        }""")
        assert result is not None
        href = result.get("href") or ""
        assert "__doPostBack" in href


# ---------------------------------------------------------------------------
# Testes de deteccao de postback (carregamento de pagina apos submit)
# ---------------------------------------------------------------------------

class TestPostbackDetection:
    """Testa deteccao de postback no page load apos submit."""

    @pytest.fixture
    def submit_page(self, page: Page):
        """Carrega pagina fam-submit com add_init_script para overlay persistente."""
        from testforge.recorder.recorder_controller import RecorderController
        page.add_init_script(RecorderController._OVERLAY_JS)
        import os as _os
        page_dir = _os.path.join(
            _os.path.dirname(__file__), "test_pages", "curation", "fam-submit"
        )
        page.goto(f"file://{page_dir}/index.html")
        page.evaluate("_tf_showOverlay()")
        page.wait_for_timeout(200)
        # Limpa eventos iniciais
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
        assert pending_before is None, f"Pending deveria ser None antes do click em submit"

        submit_page.click("#btn-submit-input")
        submit_page.wait_for_timeout(100)

        pending_after = submit_page.evaluate("() => window.__tfPendingSubmit")
        assert pending_after is not None, (
            f"Pending submit deveria ser definido apos click em submit"
        )
        # O form usa POST
        assert pending_after.get("method") in ("POST", ""), (
            f"Esperado metodo POST, obtido: {pending_after}"
        )

    def test_no_pending_submit_on_regular_click(self, submit_page):
        """Clicar em elemento nao-submit NAO deve setar __tfPendingSubmit."""
        submit_page.evaluate("window.__tfPendingSubmit = null")  # garante estado limpo
        submit_page.click("#link-regular")
        submit_page.wait_for_timeout(100)

        pending = submit_page.evaluate("() => window.__tfPendingSubmit")
        assert pending is None, (
            f"Pending submit deveria ser None apos click comum, obtido: {pending}"
        )

    def test_no_pending_submit_on_div_in_form_click(self, submit_page):
        """Clicar em div dentro de form NAO deve setar __tfPendingSubmit."""
        submit_page.evaluate("window.__tfPendingSubmit = null")
        submit_page.click("#div-in-form")
        submit_page.wait_for_timeout(100)

        pending = submit_page.evaluate("() => window.__tfPendingSubmit")
        assert pending is None, (
            f"Pending submit deveria ser None apos click em div-in-form, obtido: {pending}"
        )


# ---------------------------------------------------------------------------
# Testes de beforeunload: eventos sobrevivem a navegacao
# ---------------------------------------------------------------------------

class TestBeforeunloadEventPersistence:
    """Testa que eventos sao persistidos via beforeunload e restaurados na nova pagina."""

    @pytest.fixture
    def submit_page(self, page: Page):
        """Carrega pagina fam-submit com add_init_script para overlay persistente."""
        from testforge.recorder.recorder_controller import RecorderController
        page.add_init_script(RecorderController._OVERLAY_JS)
        import os as _os
        page_dir = _os.path.join(
            _os.path.dirname(__file__), "test_pages", "curation", "fam-submit"
        )
        page.goto(f"file://{page_dir}/index.html")
        page.evaluate("_tf_showOverlay()")
        page.wait_for_timeout(200)
        page.evaluate("window.__tfEventQueue = []")
        return page

    def _get_events(self, page: Page) -> list:
        return page.evaluate("""() => {
            var q = window.__tfEventQueue || [];
            window.__tfEventQueue = [];
            return q;
        }""")

    def test_beforeunload_persists_events_to_session_storage(self, submit_page):
        """beforeunload handler salva eventos no sessionStorage antes de navegar."""
        # Adiciona um evento conhecido
        submit_page.evaluate("""() => {
            window.__tfEventQueue.push({
                event_id: 'evt_test',
                type: 'click',
                timestamp: new Date().toISOString(),
                url: window.location.href,
                page_title: document.title,
                target: {tag: 'a', text: 'Test'}
            });
            // Simulate beforeunload
            sessionStorage.setItem('__tfUnflushedEvents', JSON.stringify(window.__tfEventQueue));
        }""")
        stored = submit_page.evaluate("() => sessionStorage.getItem('__tfUnflushedEvents')")
        assert stored is not None, "beforeunload deveria persistir eventos no sessionStorage"
        parsed = __import__("json").loads(stored)
        assert len(parsed) == 1
        assert parsed[0]["type"] == "click"

    def test_restored_submit_event_has_postback_metadata(self, submit_page):
        """Evento submit restaurado do sessionStorage tem is_postback e submit_method."""
        submit_page.evaluate("""() => {
            sessionStorage.setItem('__tfPendingSubmit', JSON.stringify({
                url: 'page2.html', method: 'POST', timestamp: Date.now()
            }));
            sessionStorage.setItem('__tfUnflushedEvents', JSON.stringify([{
                event_id: 'evt_restored',
                type: 'submit',
                timestamp: new Date().toISOString(),
                url: window.location.href,
                page_title: document.title,
                target: {tag: 'input', text: 'Submit', id: 'btn1'},
                value: null
            }]));
        }""")
        # Recarrega para acionar restauracao do bloco init
        submit_page.reload()
        submit_page.wait_for_timeout(300)
        events = self._get_events(submit_page)
        submit_events = [e for e in events if e["type"] == "submit"]
        assert len(submit_events) >= 1, (
            f"Deveria ter restaurado evento submit. Obtido: {events}"
        )
        restored = submit_events[0]
        assert restored.get("is_postback") is True, (
            f"Submit restaurado deveria ter is_postback=true. Chaves obtidas: {list(restored.keys())}"
        )
        assert restored.get("submit_method") == "POST"

    def test_restored_submit_event_has_target_info(self, submit_page):
        """Evento submit restaurado preserva informacoes do target."""
        submit_page.evaluate("""() => {
            sessionStorage.setItem('__tfPendingSubmit', JSON.stringify({
                url: 'page2.html', method: 'GET', timestamp: Date.now()
            }));
            sessionStorage.setItem('__tfUnflushedEvents', JSON.stringify([{
                event_id: 'evt_target_test',
                type: 'submit',
                timestamp: new Date().toISOString(),
                url: window.location.href,
                page_title: document.title,
                target: {tag: 'button', text: 'Save', id: 'btn-save', role: 'button'},
                value: null
            }]));
        }""")
        submit_page.reload()
        submit_page.wait_for_timeout(300)
        events = self._get_events(submit_page)
        submit_events = [e for e in events if e["type"] == "submit"]
        assert len(submit_events) >= 1
        target = submit_events[0].get("target") or {}
        assert target.get("tag") == "button"
        assert target.get("text") == "Save"
        assert target.get("id") == "btn-save"

    def test_regular_navigation_does_not_get_postback_metadata(self, submit_page):
        """Navegacao comum (click em link nao-submit) NAO deveria obter is_postback."""
        # Navega para page2 via link comum
        submit_page.evaluate("window.__tfEventQueue = []")
        submit_page.click("#link-regular")
        submit_page.wait_for_timeout(300)
        # Verifica limpeza do sessionStorage na nova pagina
        pending = submit_page.evaluate("() => sessionStorage.getItem('__tfPendingSubmit')")
        assert pending is None, "Navegacao comum nao deveria deixar pending submit"


# ---------------------------------------------------------------------------
# Testes do normalizador: postback ignorado, submit → click, submit restaurado
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
        assert result is None, "eventos postback devem ser ignorados"

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
        assert result is not None, "evento submit deveria produzir uma acao"
        assert result.action == "click", f"Esperado 'click', obtido '{result.action}'"
        assert result.context.get("is_submit") is True
        assert result.context.get("submit_method") == "POST"

    def test_restored_submit_event_with_postback_metadata(self):
        """Submit event restaurado apos navegacao (is_postback:true) converte para click com contexto completo."""
        from testforge.semantic.recording_normalizer import RecordingNormalizer

        normalizer = RecordingNormalizer()
        result = normalizer._convert_event({
            "type": "submit",
            "url": "http://localhost/form",
            "page_title": "Page 2",
            "target": {"tag": "a", "text": "Submit Form", "id": "link1"},
            "value": None,
            "is_postback": True,
            "submit_method": "POST",
            "postback_url": "http://localhost/page2",
        })
        assert result is not None, "submit restaurado deveria produzir uma acao"
        assert result.action == "click"
        assert result.context.get("is_submit") is True
        assert result.context.get("is_postback") is True
        assert result.context.get("submit_method") == "POST"
        assert result.context.get("postback_url") == "http://localhost/page2"

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
        # is_postback deve padrao ser False para eventos submit
        assert d.get("is_postback") is not True

    def test_restored_submit_event_has_postback_fields(self):
        """Submit event restaurado apos navegacao carrega is_postback e submit_method."""
        from testforge.recorder.raw_event import RawRecordedEvent

        evt = RawRecordedEvent(
            event_id="evt_00042",
            event_type="submit",
            url="http://localhost/page2",
            page_title="Page 2",
            is_postback=True,
            submit_method="POST",
        )
        d = evt.to_dict()
        assert d["type"] == "submit"
        assert d["is_postback"] is True
        assert d["submit_method"] == "POST"

    def test_regular_click_omits_postback_fields(self):
        from testforge.recorder.raw_event import RawRecordedEvent

        evt = RawRecordedEvent(
            event_id="evt_00001",
            event_type="click",
        )
        d = evt.to_dict()
        assert "is_postback" not in d  # False e omitido
        assert "submit_method" not in d  # None e omitido
