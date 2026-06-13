import os
import pytest

from testforge.core.config.loader import load_llm_config
from testforge.core.config.schema import LLMConfig
from testforge.core.healing.llm.healer import LLMHealer, MockLLMHealer, LLMHealingProposal
from testforge.core.healing.collector import EvidencePayload


pytestmark = pytest.mark.llm_real


def has_llm_env() -> bool:
    return bool(os.environ.get("AZURE_OPENAI_KEY") and os.environ.get("AZURE_OPENAI_ENDPOINT"))


def make_evidence(
    dom: str = "",
    page_url: str = "",
    error_sig: str = "",
    step_ctx: dict | None = None,
) -> EvidencePayload:
    return EvidencePayload(
        dom_snapshot=dom,
        page_url=page_url,
        failure_signature=error_sig,
        step_context=step_ctx or {},
    )


@pytest.mark.skipif(not has_llm_env(), reason="AZURE_OPENAI_KEY e AZURE_OPENAI_ENDPOINT não definidos")
class TestLLMHealerReal:
    def test_load_llm_config(self):
        config = load_llm_config()
        assert config is not None
        assert config.api_key == os.environ["AZURE_OPENAI_KEY"]
        assert config.azure_endpoint == os.environ["AZURE_OPENAI_ENDPOINT"]
        assert config.model == os.environ.get("AZURE_OPENAI_MODEL", "gpt-4.1-mini")

    def test_llm_healer_from_config(self):
        config = load_llm_config()
        assert config is not None
        healer = LLMHealer(config=config)
        assert healer._model == config.model

    def test_llm_healer_from_kwargs(self):
        healer = LLMHealer(
            api_key=os.environ["AZURE_OPENAI_KEY"],
            azure_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
        )
        assert healer._model == "gpt-4.1-mini"

    def test_heal_basic(self):
        config = load_llm_config()
        assert config is not None
        healer = LLMHealer(config=config)
        evidence = make_evidence(
            dom="<button class=\"btn\">Enviar</button>",
            page_url="https://example.com",
            error_sig="locator.click: Timeout 30000ms exceeded",
        )
        result = healer.heal(evidence, "Timeout ao clicar em botão")
        assert isinstance(result, LLMHealingProposal)
        assert 0 <= result.confidence <= 1
        assert isinstance(result.new_locator, str)
        assert isinstance(result.strategy, str)

    def test_heal_with_family_selector(self):
        config = load_llm_config()
        assert config is not None
        healer = LLMHealer(config=config)
        evidence = make_evidence(
            dom="<div><button data-testid=\"submit-btn\">OK</button></div>",
            page_url="https://example.com",
            error_sig="Timeout",
        )
        result = healer.heal(evidence, "Timeout", family="FAM-01")
        assert isinstance(result, LLMHealingProposal)
        assert result.confidence > 0

    def test_heal_with_family_timing(self):
        config = load_llm_config()
        assert config is not None
        healer = LLMHealer(config=config)
        evidence = make_evidence(
            dom="<div class=\"loading\">Carregando...</div>",
            page_url="https://example.com",
            error_sig="Timeout waiting for selector",
        )
        result = healer.heal(evidence, "Timeout waiting for selector", family="FAM-02")
        assert isinstance(result, LLMHealingProposal)
        assert result.confidence > 0

    def test_heal_or_unresolved_low_confidence(self):
        config = load_llm_config()
        assert config is not None
        healer = LLMHealer(config=config)
        evidence = make_evidence(dom="", error_sig="Erro genérico sem contexto")
        result = healer.heal_or_unresolved(evidence, "Erro genérico")
        assert isinstance(result, LLMHealingProposal)

    def test_heal_stale_element(self):
        config = load_llm_config()
        assert config is not None
        healer = LLMHealer(config=config)
        evidence = make_evidence(
            dom="<ul><li class=\"item active\">Opção 3</li></ul>",
            page_url="https://example.com",
            error_sig="locator.click: Element is not attached to the DOM",
        )
        result = healer.heal(evidence, "Stale element reference", family="FAM-05")
        assert isinstance(result, LLMHealingProposal)
        assert result.confidence > 0


class TestLLMHealerMock:
    def test_mock_instantiation(self):
        healer = MockLLMHealer()
        assert healer is not None

    def test_mock_heal_returns_proposal(self):
        healer = MockLLMHealer()
        evidence = make_evidence(dom="<button>OK</button>")
        result = healer.heal(evidence, "Timeout")
        assert isinstance(result, LLMHealingProposal)
        assert result.confidence == 0.85

    def test_mock_heal_accepts_family(self):
        healer = MockLLMHealer()
        evidence = make_evidence(dom="<button>OK</button>")
        result = healer.heal(evidence, "Timeout", family="FAM-01")
        assert isinstance(result, LLMHealingProposal)
        assert result.family == "FAM-01"

    def test_mock_empty_evidence(self):
        healer = MockLLMHealer()
        evidence = make_evidence()
        result = healer.heal(evidence, "")
        assert isinstance(result, LLMHealingProposal)

    def test_mock_heal_or_unresolved(self):
        healer = MockLLMHealer()
        evidence = make_evidence(dom="<span>teste</span>")
        result = healer.heal_or_unresolved(evidence, "erro")
        assert isinstance(result, LLMHealingProposal)


def test_load_llm_config_no_env(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("AZURE_OPENAI_KEY", raising=False)
    monkeypatch.delenv("AZURE_OPENAI_ENDPOINT", raising=False)
    config = load_llm_config()
    assert config is None


def test_load_llm_config_only_key(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("AZURE_OPENAI_KEY", "test-key")
    monkeypatch.delenv("AZURE_OPENAI_ENDPOINT", raising=False)
    config = load_llm_config()
    assert config is not None
    assert config.api_key == "test-key"
    assert config.azure_endpoint == ""
    assert config.model == "gpt-4.1-mini"


def test_load_llm_config_custom_model(monkeypatch):
    monkeypatch.setenv("AZURE_OPENAI_KEY", "k")
    monkeypatch.setenv("AZURE_OPENAI_ENDPOINT", "https://test.openai.azure.com/")
    monkeypatch.setenv("AZURE_OPENAI_MODEL", "gpt-4")
    config = load_llm_config()
    assert config is not None
    assert config.model == "gpt-4"
