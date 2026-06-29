"""Fase 2 — v2 LocatorExtractor + scorer + intent + Playwright codegen.

Testes unitarios para o pipeline de localizacao super-selector v2. Verifica que
candidatos v2 carregam intent_text, attribute_stability e
playwright_call, e que o hook normalizador esta sob feature flag
(desligado por padrao, ligado quando `use_v2_locator=True`).
"""
from __future__ import annotations

from testforge.semantic.locator import (
    LocatorExtractor,
    attribute_stability,
    emit_playwright_call,
    normalize_intent,
)
from testforge.semantic.locator.playwright_codegen import (
    emit_ancestor_scoped,
    emit_get_by_label,
    emit_get_by_role,
    emit_get_by_test_id,
)
from testforge.semantic.model import LocatorCandidate, SemanticTarget
from testforge.semantic.recording_normalizer import RecordingNormalizer


class TestIntent:
    def test_role_plus_name(self):
        i = normalize_intent("click", role="button", accessible_name="Salvar")
        assert i == 'click button "Salvar"'

    def test_falls_back_to_placeholder(self):
        i = normalize_intent("fill", role="textbox", placeholder="Email")
        assert 'placeholder "Email"' in i

    def test_ancestor_disambiguation_dialog(self):
        i = normalize_intent("click", role="button", accessible_name="Salvar",
                             ancestor_roles=["group", "dialog", "WebArea"])
        assert i == 'click button "Salvar" in dialog'

    def test_skips_generic_containers(self):
        i = normalize_intent("click", role="link", accessible_name="Home",
                             ancestor_roles=["generic", "WebArea"])
        assert "in" not in i.split('"')[-1]

    def test_select_includes_option_value(self):
        i = normalize_intent("select", role="combobox",
                             accessible_name="Estado", value="São Paulo")
        assert 'option "São Paulo"' in i

    def test_normalizes_whitespace(self):
        i = normalize_intent("click", role="button",
                             accessible_name="  Salvar\nagora  ")
        assert i == 'click button "Salvar agora"'


class TestScorer:
    def test_test_id_highest(self):
        s = attribute_stability({"test_id": "save-btn"})
        assert s["test_id"] == 0.95

    def test_role_with_name_vs_alone(self):
        with_name = attribute_stability({"role": "button", "accessible_name": "Salvar"})
        alone = attribute_stability({"role": "button"})
        assert with_name["role"] > alone["role"]
        assert with_name["role"] == 0.95
        assert alone["role"] == 0.50

    def test_auto_id_penalized(self):
        s = attribute_stability({"id": "mat-input-42"})
        assert s["id"] == 0.20

    def test_semantic_id_high(self):
        s = attribute_stability({"id": "user-email"})
        assert s["id"] == 0.80

    def test_generic_text_low(self):
        s = attribute_stability({"text": "OK"})
        assert s["text"] == 0.10

    def test_long_text_penalty(self):
        long_text = "Lorem ipsum dolor sit amet consectetur adipiscing elit sed"
        s = attribute_stability({"text": long_text})
        assert s["text"] < 0.55

    def test_placeholder_present(self):
        s = attribute_stability({"placeholder": "you@example.com"})
        assert s["placeholder"] == 0.70

    def test_xpath_lowest(self):
        s = attribute_stability({"xpath": "/html/body/div[2]/form/input[1]"})
        assert s["xpath"] == 0.15


class TestPlaywrightCodegen:
    def test_role_with_name(self):
        assert emit_get_by_role("button", "Salvar") == 'get_by_role("button", name="Salvar")'

    def test_role_with_name_exact(self):
        assert emit_get_by_role("button", "Salvar", exact=True) == \
            'get_by_role("button", name="Salvar", exact=True)'

    def test_label(self):
        assert emit_get_by_label("Email") == 'get_by_label("Email")'

    def test_test_id(self):
        assert emit_get_by_test_id("save-btn") == 'get_by_test_id("save-btn")'

    def test_emit_picks_native_role(self):
        c = emit_playwright_call({"role": "button", "accessible_name": "Salvar"})
        assert c == 'get_by_role("button", name="Salvar")'

    def test_emit_falls_back_to_label(self):
        c = emit_playwright_call({"label": "Email"})
        assert c == 'get_by_label("Email")'

    def test_emit_falls_back_to_placeholder(self):
        c = emit_playwright_call({"placeholder": "search..."})
        assert c == 'get_by_placeholder("search...")'

    def test_emit_test_id_after_native(self):
        c = emit_playwright_call({"test_id": "user-row"})
        assert c == 'get_by_test_id("user-row")'

    def test_emit_returns_none_when_no_attrs(self):
        c = emit_playwright_call({"tag": "div"})
        assert c is None

    def test_emit_escapes_quotes_in_name(self):
        c = emit_playwright_call({"role": "button", "accessible_name": 'click "here"'})
        assert '\\"' in c

    def test_ancestor_scoped(self):
        child = emit_get_by_role("button", "Salvar")
        out = emit_ancestor_scoped("dialog", child)
        assert out == 'get_by_role("dialog").get_by_role("button", name="Salvar")'


class TestExtractor:
    def test_basic_role_button(self):
        ex = LocatorExtractor()
        cands = ex.extract({"role": "button", "accessible_name": "Salvar",
                            "tag": "button"})
        assert len(cands) > 0
        top = cands[0]
        assert top.strategy.startswith("playwright_native")
        assert top.playwright_call.startswith("get_by_role")
        assert top.intent_text == 'click button "Salvar"'
        assert top.score > 0.85

    def test_test_id_first_when_role_absent(self):
        ex = LocatorExtractor()
        cands = ex.extract({"test_id": "save-btn", "tag": "button"})
        # Native get_by_test_id fica em primeiro
        assert any(c.strategy == "playwright_native" and "test_id" in (c.playwright_call or "")
                   for c in cands)

    def test_includes_attribute_stability(self):
        ex = LocatorExtractor()
        cands = ex.extract({"role": "button", "accessible_name": "Salvar"})
        assert cands[0].attribute_stability != {}
        assert "role" in cands[0].attribute_stability

    def test_ancestor_scoped_when_dialog(self):
        ex = LocatorExtractor(ancestor_roles=["group", "dialog", "WebArea"])
        cands = ex.extract({"role": "button", "accessible_name": "Salvar"})
        scoped = [c for c in cands if c.strategy == "playwright_native_scoped"]
        assert scoped, "expected scoped candidate when dialog is an ancestor"
        assert scoped[0].playwright_call.startswith('get_by_role("dialog")')

    def test_no_native_falls_through_to_css(self):
        ex = LocatorExtractor()
        cands = ex.extract({"id": "user-row", "tag": "tr"})
        strategies = {c.strategy for c in cands}
        assert "id_css" in strategies

    def test_sorted_descending_by_score(self):
        ex = LocatorExtractor()
        cands = ex.extract({
            "role": "button", "accessible_name": "Salvar",
            "id": "save-btn", "tag": "button",
        })
        scores = [c.score for c in cands]
        assert scores == sorted(scores, reverse=True)

    def test_intent_text_propagated_to_all_candidates(self):
        ex = LocatorExtractor()
        cands = ex.extract({"role": "button", "accessible_name": "Salvar"})
        intents = {c.intent_text for c in cands}
        assert intents == {'click button "Salvar"'}

    def test_backend_node_id_carried(self):
        ex = LocatorExtractor(backend_node_id=42)
        cands = ex.extract({"role": "button", "accessible_name": "Save"})
        assert all(c.backend_node_id == 42 for c in cands)

    def test_auto_id_scored_below_semantic_id(self):
        ex = LocatorExtractor()
        auto = ex.extract({"id": "mat-input-0", "tag": "input"})
        semantic = ex.extract({"id": "user-email", "tag": "input"})
        auto_id = next(c for c in auto if c.strategy == "id_css")
        sem_id = next(c for c in semantic if c.strategy == "id_css")
        assert auto_id.score < sem_id.score


class TestNormalizerHook:
    def test_flag_off_no_v2_candidates(self):
        n = RecordingNormalizer()  # default off
        target_data = {"role": "button", "accessible_name": "Salvar", "tag": "button"}
        target = n._build_target(target_data)
        # Apenas candidatos legados; nenhum deve carregar intent_text.
        assert target.intent_text is None
        assert all(c.intent_text is None for c in target.candidates)

    def test_flag_on_appends_v2(self):
        n = RecordingNormalizer(use_v2_locator=True)
        target_data = {"role": "button", "accessible_name": "Salvar", "tag": "button"}
        target = n._build_target(target_data)
        v2 = [c for c in target.candidates if c.intent_text]
        assert v2, "expected at least one v2 candidate when flag enabled"
        assert target.intent_text == 'click button "Salvar"'

    def test_legacy_candidates_still_present_when_flag_on(self):
        n = RecordingNormalizer(use_v2_locator=True)
        target_data = {"role": "button", "accessible_name": "Salvar", "tag": "button"}
        target = n._build_target(target_data)
        # Candidato legado com estrategia 'role' ainda deve estar presente
        assert any(c.strategy == "role" for c in target.candidates)

    def test_to_dict_serializes_v2_fields(self):
        from testforge.semantic.model import SemanticTestCase, SemanticAction, SemanticTarget
        cand = LocatorCandidate(
            strategy="playwright_native", selector='page.get_by_role("button", name="Salvar")',
            score=0.95, reason="native",
            playwright_call='get_by_role("button", name="Salvar")',
            intent_text='click button "Salvar"',
            attribute_stability={"role": 0.95},
        )
        tgt = SemanticTarget(role="button", accessible_name="Salvar",
                             candidates=[cand], intent_text='click button "Salvar"')
        step = SemanticAction(action="click", target=tgt)
        tc = SemanticTestCase(test_id="ST-x", source_recording_id="r")
        tc.steps.append(step)
        out = tc.to_dict()
        c0 = out["semantic_test_case"]["steps"][0]["target"]["candidates"][0]
        assert c0["playwright_call"] == 'get_by_role("button", name="Salvar")'
        assert c0["intent_text"] == 'click button "Salvar"'
        assert c0["attribute_stability"] == {"role": 0.95}
        assert out["semantic_test_case"]["steps"][0]["target"]["intent_text"] == \
            'click button "Salvar"'
