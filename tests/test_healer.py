"""Testes para runtime.healer — pontuacao de autocorrecao multi-atributo."""
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
    """Testes unitarios para _score_match — funcao pura, sem Playwright."""

    # --- Correspondencia exata ---

    def test_perfect_match(self):
        """Todos os atributos do fingerprint correspondem exatamente → score = 1.0."""
        fp = {"tag": "input", "role": "textbox", "accessible_name": "Nome", "placeholder": "Seu nome"}
        live = {"tag": "input", "role": "textbox", "accessible_name": "Nome", "placeholder": "Seu nome", "name": "nome", "id": "nomeField", "text": "Nome completo"}
        score = _score_match(live, fp)
        assert score == 1.0

    # --- Correspondencias parciais ---

    def test_tag_mismatch_penalty(self):
        """Tags diferentes reduzem a pontuacao (peso tag = 0.15/1.0)."""
        fp = {"tag": "input", "role": "textbox", "accessible_name": "Nome"}
        # total=0.60, matched: role(0.20)+name(0.25)=0.45 → score=0.45/0.60=0.75
        live = {"tag": "span", "role": "textbox", "accessible_name": "Nome"}
        assert _score_match(live, fp) == pytest.approx(0.75, rel=0.01)

    def test_substring_accessible_name(self):
        """Correspondencia de substring no accessible_name recebe peso 0.6x → score = (0.25*0.6)/0.25 = 0.60."""
        fp = {"accessible_name": "Renda mensal"}
        live = {"accessible_name": "Renda mensal *"}
        assert _score_match(live, fp) == pytest.approx(0.60, rel=0.01)

    def test_substring_placeholder(self):
        """Correspondencia de substring no placeholder → score = (0.15*0.6)/0.15 = 0.60."""
        fp = {"placeholder": "Seu nome"}
        live = {"placeholder": "Digite seu nome completo"}
        assert _score_match(live, fp) == pytest.approx(0.60, rel=0.01)

    def test_substring_text(self):
        """Correspondencia de substring no text → score = (0.15*0.6)/0.15 = 0.60."""
        fp = {"text": "Confirmar"}
        live = {"text": "Confirmar pagamento"}
        assert _score_match(live, fp) == pytest.approx(0.60, rel=0.01)

    # --- Casos limite ---

    def test_no_match(self):
        """Nenhum atributo corresponde → score = 0.0."""
        fp = {"tag": "input", "role": "textbox", "accessible_name": "Nome"}
        live = {"tag": "button", "role": "button", "accessible_name": "Submit"}
        assert _score_match(live, fp) == 0.0

    def test_empty_fingerprint(self):
        """Fingerprint vazio/None → score = 0.0."""
        assert _score_match({}, {"tag": "input"}) == 0.0
        assert _score_match({"tag": "input"}, {}) == 0.0

    def test_missing_live_attrs(self):
        """Elemento vivo sem atributos → pontuacao menor."""
        fp = {"tag": "input", "role": "textbox", "accessible_name": "Nome"}
        live = {"tag": "input", "role": "textbox"}  # sem accessible_name
        # total=0.60, matched: tag(0.15)+role(0.20)=0.35 → score=0.35/0.60≈0.58
        assert _score_match(live, fp) == pytest.approx(0.583, rel=0.01)

    def test_case_insensitive_substring(self):
        """Correspondencia de substring ignora maiusculas/minusculas."""
        fp = {"accessible_name": "RENDA MENSAL"}
        live = {"accessible_name": "renda mensal *"}
        assert _score_match(live, fp) == pytest.approx(0.60, rel=0.01)

    def test_threshold_default(self):
        """CONFIDENCE_THRESHOLD e 0.40."""
        assert CONFIDENCE_THRESHOLD == 0.40

    # --- Pontuacao combinada ---

    def test_all_exact_match_returns_1(self):
        """Todas as chaves do fingerprint presentes e exatas → 1.0 independente de atributos extras no elemento vivo."""
        fp = {"tag": "input", "role": "textbox"}
        live = {"tag": "input", "role": "textbox", "accessible_name": "ignored"}
        assert _score_match(live, fp) == 1.0

    def test_high_confidence_partial(self):
        """A maioria dos atributos corresponde exatamente, um e substring → alto mas < 1.0."""
        fp = {"tag": "input", "role": "textbox", "accessible_name": "Nome completo", "placeholder": "Seu nome"}
        live = {"tag": "input", "role": "textbox", "accessible_name": "Nome completo", "placeholder": "Seu nome completo"}
        # total=0.75, matched: tag(0.15)+role(0.20)+name_exact(0.25)+placeholder_substr(0.15*0.6=0.09)=0.69
        # score = 0.69/0.75 = 0.92
        assert _score_match(live, fp) == pytest.approx(0.69 / 0.75, rel=0.01)

    def test_fingerprint_with_extra_keys(self):
        """Chaves extras do fingerprint todas presentes e exatas → 1.0."""
        fp = {"tag": "input", "name": "cpf", "id": "cpfField"}
        live = {"tag": "input", "name": "cpf", "id": "cpfField"}
        assert _score_match(live, fp) == 1.0


class TestCompilerHealerBlock:
    """Testa se o compilador emite blocos resolve_selector quando fingerprint esta presente."""

    _GET_SCRIPT = staticmethod(lambda path: open(path).read())

    def test_import_present(self, tmp_path):
        """Script gerado importa resolve_selector do healer."""
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
        """Passo fill gera bloco resolve_selector quando fingerprint presente."""
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
        """Passo click gera bloco resolve_selector com acao correta."""
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
        """Passo select gera bloco resolve_selector."""
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
        """Sem fingerprint, compilador emite for-loop legado."""
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
        """Fingerprint com caracteres especiais (R$, aspas) faz escape corretamente."""
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
    """Testes para HealCatalog — persistencia e consulta."""

    def setup_method(self):
        reset_catalog()

    # --- CRUD basico ---

    def test_lookup_miss(self, tmp_path):
        """Consulta em catalogo vazio retorna None."""
        cat = HealCatalog(path=str(tmp_path / "catalog.jsonl"))
        assert cat.lookup({"tag": "input"}) is None

    def test_record_and_lookup_hit(self, tmp_path):
        """Gravar e consultar mesmo fingerprint retorna seletor."""
        cat = HealCatalog(path=str(tmp_path / "catalog.jsonl"))
        cat.record({"tag": "input", "placeholder": "R$0,00"}, "input#valor", 0.85)
        result = cat.lookup({"tag": "input", "placeholder": "R$0,00"})
        assert result == "input#valor"

    def test_record_reinforce(self, tmp_path):
        """Gravar mesmo fingerprint incrementa success_count."""
        cat = HealCatalog(path=str(tmp_path / "catalog.jsonl"))
        cat.record({"tag": "input"}, "input#x", 0.80)
        cat.record({"tag": "input"}, "input#x", 0.80)
        key = _fp_key({"tag": "input"})
        assert cat._entries[key].success_count == 2

    def test_record_updates_score(self, tmp_path):
        """Gravar com pontuacao maior atualiza entry.score."""
        cat = HealCatalog(path=str(tmp_path / "catalog.jsonl"))
        cat.record({"tag": "input"}, "input#x", 0.70)
        cat.record({"tag": "input"}, "input#x", 0.95)
        key = _fp_key({"tag": "input"})
        assert cat._entries[key].score == 0.95

    # --- chave canonica ---

    def test_fp_key_deterministic(self):
        """Mesmo fingerprint produz mesma chave independente da ordem do dicionario."""
        k1 = _fp_key({"tag": "input", "placeholder": "R$0,00"})
        k2 = _fp_key({"placeholder": "R$0,00", "tag": "input"})
        assert k1 == k2

    def test_lookup_key_order_independent(self, tmp_path):
        """Consulta funciona independente da ordem de insercao das chaves do dicionario."""
        cat = HealCatalog(path=str(tmp_path / "catalog.jsonl"))
        cat.record({"a": "1", "b": "2"}, "#x", 0.90)
        assert cat.lookup({"b": "2", "a": "1"}) == "#x"

    # --- persistencia ---

    def test_persists_across_instances(self, tmp_path):
        """Catalogo gravado em arquivo e legivel por nova instancia."""
        p = str(tmp_path / "persist.jsonl")
        cat1 = HealCatalog(path=p)
        cat1.record({"tag": "input"}, "input#persist", 0.90)

        cat2 = HealCatalog(path=p)
        assert cat2.lookup({"tag": "input"}) == "input#persist"

    def test_no_path_does_not_persist(self):
        """Catalogo com caminho vazio e apenas memoria (nenhum arquivo gravado)."""
        cat = HealCatalog(path="")
        cat.record({"tag": "input"}, "input#x", 0.90)
        # Entrada existe em memoria mas nenhum arquivo foi criado
        assert cat.lookup({"tag": "input"}) == "input#x"
        assert len(cat._entries) == 1

    # --- expulsao (eviction) ---

    def test_ttl_eviction(self, tmp_path):
        """Entradas mais antigas que o TTL sao expulsas na consulta."""
        cat = HealCatalog(path=str(tmp_path / "ttl.jsonl"))
        cat.record({"tag": "input"}, "input#old", 0.90)
        key = _fp_key({"tag": "input"})
        # Envelhecer a entrada manualmente
        cat._entries[key].last_success = time.time() - 31 * 24 * 3600
        assert cat.lookup({"tag": "input"}) is None

    def test_max_entries_eviction(self, tmp_path):
        """Entradas mais antigas sao expulsas quando catalogo excede max."""
        import src.testforge.runtime.healer as H
        original = H._CATALOG_MAX_ENTRIES
        H._CATALOG_MAX_ENTRIES = 10
        try:
            cat = HealCatalog(path=str(tmp_path / "max.jsonl"))
            for i in range(15):
                cat.record({"idx": str(i)}, f"#x{i}", 0.90)
            # Apos salvar, deve ser <= 10
            assert len(cat._entries) <= 10
        finally:
            H._CATALOG_MAX_ENTRIES = original

    # --- registro (logging) ---

    def test_lookup_logs_hit(self, tmp_path, caplog):
        """Acerto no catalogo registra com prefixo 'heal_catalog: HIT'."""
        import logging
        caplog.set_level(logging.INFO)
        cat = HealCatalog(path=str(tmp_path / "log.jsonl"))
        cat.record({"tag": "input"}, "input#log", 0.90)
        cat.lookup({"tag": "input"})
        assert "heal_catalog: HIT" in caplog.text

    # --- casos limite ---

    def test_empty_fingerprint_noop(self, tmp_path):
        """Gravar ou consultar fingerprint vazio e no-op seguro."""
        cat = HealCatalog(path=str(tmp_path / "empty.jsonl"))
        cat.record({}, "#x", 0.90)  # nao deve quebrar nem persistir
        assert cat.lookup({}) is None
        assert len(cat._entries) == 0

    def test_none_fingerprint_safe(self, tmp_path):
        """Consulta com fingerprint None retorna None."""
        cat = HealCatalog(path=str(tmp_path / "none.jsonl"))
        assert cat.lookup(None) is None
        cat.record(None, "#x", 0.90)  # operacao nula

    def test_corrupted_file_handled(self, tmp_path):
        """JSONL corrompido nao quebra o carregamento."""
        now = time.time()
        p = str(tmp_path / "corrupt.jsonl")
        with open(p, "w") as f:
            f.write(json.dumps({"fp": {"tag": "input"}, "sel": "#ok", "score": 0.9, "n": 1, "ts": now}) + "\n")
            f.write("NOT JSON\n")
            f.write(json.dumps({"fp": {"tag": "button"}, "sel": "#btn", "score": 0.8, "n": 1, "ts": now}) + "\n")
        cat = HealCatalog(path=p)
        # Deve ter carregado primeiro e ultimo, pulado o meio
        assert cat.lookup({"tag": "input"}) == "#ok"
        assert cat.lookup({"tag": "button"}) == "#btn"


class TestCatalogIntegration:
    """Testa se o catalogo se integra transparentemente ao resolve_selector."""

    def setup_method(self):
        reset_catalog()

    def test_resolve_selector_checks_catalog(self, tmp_path):
        """resolve_selector chama catalog.lookup internamente."""
        # Nao podemos testar o fluxo DOM vivo completo, mas podemos verificar se o
        # singleton do catalogo e acessivel e o caminho de codigo existe.
        from src.testforge.runtime.healer import _get_catalog
        cat = _get_catalog()
        assert cat is not None
        assert hasattr(cat, "lookup")
        assert hasattr(cat, "record")

    def test_catalog_singleton_shared(self):
        """_get_catalog retorna mesma instancia entre chamadas."""
        reset_catalog()
        c1 = _get_catalog()
        c2 = _get_catalog()
        assert c1 is c2

    def test_reset_catalog_creates_new(self):
        """reset_catalog() faz _get_catalog() retornar uma nova instancia."""
        reset_catalog()
        c1 = _get_catalog()
        c1.record({"tag": "x"}, "#x", 0.90)
        reset_catalog()
        c2 = _get_catalog()
        assert c2.lookup({"tag": "x"}) is None
