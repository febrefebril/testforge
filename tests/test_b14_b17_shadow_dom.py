"""B14/B17 — navegador shadow DOM + localizador encadeado.

Quando o gravador captura um elemento dentro de uma shadow root aberta,
ele agora registra o descritor do host (`shadow_host`) no alvo. O
normalizador o apresenta como LocatorCandidate de maior prioridade para que o
executor possa fazer `page.locator(host).locator(child)` (Playwright atravessa
roots abertas automaticamente quando recebe um seletor encadeado).

Shadow roots fechadas ainda sao pontos cegos — o gravador nao consegue
entrar nelas de fora.

Este arquivo fixa:
1. SemanticTarget carrega o descritor shadow_host.
2. _build_target insere um candidato shadow_host_chain de alta prioridade.
3. O formato do seletor encadeado e `host >> inner`.
4. Gravacoes sem shadow_host nao recebem candidato extra (sem regressao
   para paginas normais).
"""
from __future__ import annotations

from testforge.semantic.model import SemanticTarget
from testforge.semantic.recording_normalizer import RecordingNormalizer


class TestShadowTargetCarriesHost:
    def test_semantic_target_field_exists(self):
        t = SemanticTarget()
        assert hasattr(t, "shadow_host")
        assert t.shadow_host is None

    def test_field_accepts_dict_descriptor(self):
        t = SemanticTarget(shadow_host={
            "host_selector": "my-component",
            "host_tag": "my-component",
            "host_id": None,
            "mode": "open",
        })
        assert t.shadow_host["host_selector"] == "my-component"


class TestBuildTargetEmitsShadowChain:
    def _n(self) -> RecordingNormalizer:
        return RecordingNormalizer()

    def test_shadow_chain_candidate_inserted_first(self):
        target = self._n()._build_target({
            "tag": "input",
            "accessible_name": "CPF",
            "shadow_host": {
                "host_selector": "x-card#cpf-card",
                "host_tag": "x-card",
                "host_id": "cpf-card",
                "mode": "open",
            },
        })
        assert target.shadow_host is not None
        assert target.shadow_host["host_selector"] == "x-card#cpf-card"
        # O primeiro candidato deve ser a cadeia shadow — Playwright deve
        # testa-lo antes de qualquer caminho CSS simples.
        assert target.candidates, "Esperado ao menos um candidato"
        first = target.candidates[0]
        assert first.strategy == "shadow_host_chain", (
            f"Primeiro candidato deveria ser shadow_host_chain, veio "
            f"{first.strategy} ({first.selector})"
        )
        assert ">>" in first.selector, (
            f"Seletor encadeado deve usar formato '>>', veio {first.selector!r}"
        )
        assert first.selector.startswith("x-card#cpf-card"), (
            f"Cadeia deve comecar com seletor do host, veio {first.selector!r}"
        )

    def test_shadow_chain_prefers_test_id_inner(self):
        target = self._n()._build_target({
            "tag": "input",
            "test_id": "cpf-input",
            "element_id": "x-internal",
            "shadow_host": {"host_selector": "x-card", "host_tag": "x-card", "mode": "open"},
        })
        chain = target.candidates[0].selector
        assert chain == 'x-card >> [data-testid="cpf-input"]'

    def test_shadow_chain_uses_element_id_when_no_test_id(self):
        target = self._n()._build_target({
            "tag": "input",
            "element_id": "internal-input",
            "shadow_host": {"host_selector": "x-card", "host_tag": "x-card", "mode": "open"},
        })
        chain = target.candidates[0].selector
        assert chain == "x-card >> #internal-input"

    def test_shadow_chain_falls_back_to_accessible_name(self):
        target = self._n()._build_target({
            "tag": "input",
            "accessible_name": "Renda mensal",
            "shadow_host": {"host_selector": "x-card", "host_tag": "x-card", "mode": "open"},
        })
        chain = target.candidates[0].selector
        assert chain == 'x-card >> [aria-label="Renda mensal"]'

    def test_no_shadow_host_means_no_chain_candidate(self):
        target = self._n()._build_target({
            "tag": "input",
            "accessible_name": "CPF",
            # nenhuma chave shadow_host
        })
        chains = [c for c in target.candidates if c.strategy == "shadow_host_chain"]
        assert chains == [], (
            "Alvos de arvore documental simples nao devem receber candidato "
            "de cadeia shadow."
        )

    def test_null_shadow_host_means_no_chain_candidate(self):
        # Shadow root fechada → gravador escreve shadow_host=null.
        target = self._n()._build_target({
            "tag": "input",
            "accessible_name": "CPF",
            "shadow_host": None,
        })
        chains = [c for c in target.candidates if c.strategy == "shadow_host_chain"]
        assert chains == []


class TestCaptureSchemaBumped:
    def test_schema_version_at_least_2(self):
        # B14/B17 introduziu v2 (target.shadow_host). H20 entao introduziu
        # v3 (evento scenario_boundary). A versao real pode continuar
        # subindo; o invariante e apenas que houve incremento.
        from testforge.recorder.capture_fingerprint import CAPTURE_SCHEMA_VERSION
        assert CAPTURE_SCHEMA_VERSION >= 2, (
            "B14/B17 adicionou target.shadow_host a saida do gravador. "
            "Incremente CAPTURE_SCHEMA_VERSION quando a forma deste campo mudar."
        )
