from __future__ import annotations

from pathlib import Path

import pytest

from testforge.core.healing.collector import EvidenceCollector
from testforge.core.healing.curator import (
    CuradorAutomatico,
    ProgressResult,
    classify_step_result,
)
from testforge.core.healing.llm.healer import MockLLMHealer


TEST_PAGES_DIR = Path(__file__).resolve().parent.parent.parent / "tests" / "test_pages"


FAMILIES = [
    ("fam-01-selector", "FAM-01"),
    ("fam-02-timing", "FAM-02"),
    ("fam-03-context", "FAM-03"),
    ("fam-04-state", "FAM-04"),
    ("fam-05-dom-dinamico", "FAM-05"),
    ("fam-06-fill", "FAM-06"),
    ("fam-07-capture", "FAM-07"),
    ("fam-08-assertion", "FAM-08"),
    ("fam-09-recorder", "FAM-09"),
    ("fam-10-execution", "FAM-10"),
    ("fam-11-browser", "FAM-11"),
]


@pytest.mark.parametrize("fam_folder,fam_code", FAMILIES)
def test_page_serves_without_errors(test_server, fam_folder, fam_code, page):
    errors = []

    def on_console(msg):
        if msg.type == "error":
            errors.append(msg.text)

    page.on("console", on_console)
    url = f"{test_server}/curation/{fam_folder}/"
    page.goto(url, wait_until="domcontentloaded")
    assert page.locator("h1").count() > 0, f"Falha ao carregar {fam_folder}"


def test_evidence_collector_dom_snapshot(test_server, healing_catalog, page):
    """Collector coleta DOM snapshot e screenshot de uma página real."""
    collector = EvidenceCollector(page)
    collector.attach_listeners()
    page.goto(f"{test_server}/curation/fam-01-selector/", wait_until="domcontentloaded")

    step_data = {
        "action": "click",
        "selector": "#btn-salvar",
        "value": "",
        "url": page.url,
        "page_title": page.title(),
        "tag_name": "button",
        "text": "Salvar",
        "intention": "Clicar em Salvar",
    }

    payload = collector.collect(step_data, 0)
    assert payload.is_sufficient
    assert "btn-salvar" in payload.dom_snapshot
    assert payload.screenshot_base64
    assert payload.step_context["action"] == "click"


def test_evidence_collector_insufficient_evidence(test_server, healing_catalog, page):
    """Collector retorna is_sufficient=False se DOM vazio e sem screenshot."""
    collector = EvidenceCollector(page)
    collector.attach_listeners()
    page.goto(f"{test_server}/curation/fam-01-selector/", wait_until="domcontentloaded")
    page.close()

    step_data = {"action": "click", "selector": "#btn-salvar"}
    payload = collector.collect(step_data, 0)
    assert not payload.is_sufficient


def test_classify_step_result():
    assert classify_step_result("erro A", "erro A", False) == ProgressResult.STAGNATED
    assert classify_step_result("erro A", "erro B", False) == ProgressResult.ERROR_CHANGED
    assert classify_step_result("erro A", "", True) == ProgressResult.PASSED_STEP
    assert classify_step_result("erro A", "", False) == ProgressResult.UNRESOLVED


def test_curador_with_mock_healer_passes(test_server, healing_catalog, page):
    """Curador com mock healer: proposta confiante → step executado → PASSED_STEP + learned."""
    curador = CuradorAutomatico(
        catalog=healing_catalog,
        healer=MockLLMHealer(),
        step_runner=lambda sd: None,
    )
    curador._try_execute_step = lambda sd: (True, "")

    collector = EvidenceCollector(page)
    collector.attach_listeners()
    page.goto(f"{test_server}/curation/fam-01-selector/", wait_until="domcontentloaded")

    step_data = {
        "action": "click",
        "selector": "#btn-salvar",
        "value": "",
        "text": "Salvar",
    }

    payload = collector.collect(step_data, 0)
    outcome = curador.cure(step_data, "erro simulado", payload)

    assert outcome.status == ProgressResult.PASSED_STEP
    assert outcome.entry_id
    assert outcome.proposal is not None
    assert outcome.proposal.confidence >= 0.5

    saved = healing_catalog.get(outcome.entry_id)
    assert saved is not None
    assert saved.fix_type == "learned"


def test_curador_with_mock_healer_unresolved(test_server, healing_catalog, page):
    """Curador: confianca baixa → UNRESOLVED."""
    class LowConfHealer(MockLLMHealer):
        def heal(self, payload, error_message="", family=""):
            from testforge.core.healing.llm.healer import LLMHealingProposal
            return LLMHealingProposal(
                taxonomy_id="SEL-999",
                family="FAM-01",
                strategy="xpath_fallback",
                new_locator="//*[@id='x']",
                confidence=0.3,
                rationale="Mock: confianca baixa",
            )

    curador = CuradorAutomatico(
        catalog=healing_catalog,
        healer=LowConfHealer(),
        step_runner=lambda sd: None,
    )

    step_data = {"action": "click", "selector": "#btn-salvar"}
    collector = EvidenceCollector(page)
    page.goto(f"{test_server}/curation/fam-01-selector/", wait_until="domcontentloaded")
    payload = collector.collect(step_data, 0)

    outcome = curador.cure(step_data, "erro", payload)
    assert outcome.status == ProgressResult.UNRESOLVED


def test_curador_regressed_rollback(test_server, healing_catalog, page):
    """Curador: step falha com mesmo erro → rollback + UNRESOLVED."""
    class AlwaysFailHealer(MockLLMHealer):
        def heal(self, payload, error_message="", family=""):
            from testforge.core.healing.llm.healer import LLMHealingProposal
            return LLMHealingProposal(
                taxonomy_id="SEL-004",
                family="FAM-01",
                strategy="semantic_locator_conversion",
                new_locator="#elemento-inexistente",
                confidence=0.9,
                rationale="Mock: sempre falha",
            )

    curador = CuradorAutomatico(
        catalog=healing_catalog,
        healer=AlwaysFailHealer(),
        step_runner=lambda sd: (_ for _ in ()).throw(Exception("mesmo erro")),
    )

    step_data = {"action": "click", "selector": "#btn-salvar"}
    collector = EvidenceCollector(page)
    page.goto(f"{test_server}/curation/fam-01-selector/", wait_until="domcontentloaded")
    payload = collector.collect(step_data, 0)

    outcome = curador.cure(step_data, "mesmo erro", payload)
    assert outcome.status == ProgressResult.UNRESOLVED
    assert outcome.rollback_applied


def test_curador_error_changed_reclassify(test_server, healing_catalog, page):
    """Curador: erro mudou → reclassifica e retenta (max 1x)."""
    call_count = [0]

    class ErrorChangeHealer(MockLLMHealer):
        def heal(self, payload, error_message="", family=""):
            from testforge.core.healing.llm.healer import LLMHealingProposal
            call_count[0] += 1
            return LLMHealingProposal(
                taxonomy_id="SEL-004",
                family="FAM-01",
                strategy="semantic_locator_conversion",
                new_locator="#outro-seletor",
                confidence=0.9,
                rationale="Mock: erro mudou",
            )

    step_results = [
        (False, "erro DIFERENTE DO ORIGINAL"),
    ]
    result_idx = [0]

    def step_runner(sd):
        idx = result_idx[0]
        result_idx[0] += 1
        if idx < len(step_results):
            passed, err = step_results[idx]
            if not passed:
                raise Exception(err)

    curador = CuradorAutomatico(
        catalog=healing_catalog,
        healer=ErrorChangeHealer(),
        step_runner=step_runner,
    )

    step_data = {"action": "click", "selector": "#btn"}
    collector = EvidenceCollector(page)
    page.goto(f"{test_server}/curation/fam-01-selector/", wait_until="domcontentloaded")
    payload = collector.collect(step_data, 0)

    outcome = curador.cure(step_data, "erro original", payload)
    assert outcome.reclassification_used
    assert call_count[0] >= 1


def test_evidence_payload_structure(test_server, page):
    """EvidencePayload contém todos os campos esperados."""
    collector = EvidenceCollector(page)
    collector.attach_listeners()
    page.goto(f"{test_server}/curation/fam-01-selector/", wait_until="domcontentloaded")
    page.evaluate("console.error('erro teste')")
    page.wait_for_timeout(200)

    step_data = {"action": "click", "selector": "#btn-salvar", "url": page.url}
    payload = collector.collect(step_data, 0)

    assert payload.dom_snapshot
    assert payload.screenshot_base64
    assert payload.console_errors
    assert any("erro teste" in c.get("text", "") for c in payload.console_errors)
    assert payload.step_context["action"] == "click"
    assert payload.failure_signature
    assert payload.collected_at
    assert payload.step_index == 0


def test_sanitize_dom_removes_script_and_style():
    from testforge.core.healing.collector import sanitize_dom
    html = "<html><head><script>alert(1)</script><style>.x{color:red}</style></head><body>ok</body></html>"
    cleaned = sanitize_dom(html)
    assert "<script>" not in cleaned
    assert "<style>" not in cleaned
    assert "ok" in cleaned


def test_sanitize_dom_removes_input_value():
    from testforge.core.healing.collector import sanitize_dom
    html = '<input type="text" value="senha123" name="senha">'
    cleaned = sanitize_dom(html)
    assert 'value="senha123"' not in cleaned


def test_sanitize_dom_keeps_data_testid():
    from testforge.core.healing.collector import sanitize_dom
    html = '<button data-testid="btn-salvar">Salvar</button>'
    cleaned = sanitize_dom(html)
    assert 'data-testid="btn-salvar"' in cleaned


def test_evidence_payload_has_network_state_key(test_server, page):
    collector = EvidenceCollector(page)
    collector.attach_listeners()
    page.goto(f"{test_server}/curation/fam-01-selector/", wait_until="domcontentloaded")
    payload = collector.collect({"action": "click"}, 0)
    assert hasattr(payload, "network_state")
    assert not hasattr(payload, "network_requests")


def test_evidence_payload_has_metadata(test_server, page):
    collector = EvidenceCollector(page)
    page.goto(f"{test_server}/curation/fam-01-selector/", wait_until="domcontentloaded")
    payload = collector.collect({"action": "click"}, 0)
    assert payload.metadata is not None
    assert "all_steps_count" in payload.metadata


def test_curador_taxonomia_invalida_unresolved(test_server, healing_catalog, page):
    """Curador: taxonomy_id invalido → UNRESOLVED."""
    class InvalidTaxHealer(MockLLMHealer):
        def heal(self, payload, error_message="", family=""):
            from testforge.core.healing.llm.healer import LLMHealingProposal
            return LLMHealingProposal(
                taxonomy_id="INVALIDO-999",
                family="FAM-XX",
                strategy="xpath_fallback",
                new_locator="//*[@id='x']",
                confidence=0.9,
                rationale="Mock: taxonomia invalida",
            )

    curador = CuradorAutomatico(
        catalog=healing_catalog,
        healer=InvalidTaxHealer(),
        step_runner=lambda sd: None,
    )

    step_data = {"action": "click", "selector": "#btn"}
    collector = EvidenceCollector(page)
    page.goto(f"{test_server}/curation/fam-01-selector/", wait_until="domcontentloaded")
    payload = collector.collect(step_data, 0)

    outcome = curador.cure(step_data, "erro", payload)
    assert outcome.status == ProgressResult.UNRESOLVED


def test_curador_depth_limit(test_server, healing_catalog, page):
    """Curador: depth limit excedido → UNRESOLVED."""
    class CyclingHealer(MockLLMHealer):
        def heal(self, payload, error_message="", family=""):
            from testforge.core.healing.llm.healer import LLMHealingProposal
            return LLMHealingProposal(
                taxonomy_id="SEL-004",
                family="FAM-01",
                strategy="semantic_locator_conversion",
                new_locator="#ciclo",
                confidence=0.9,
                rationale="Mock: cycling",
            )

    call_count = [0]
    def step_runner(sd):
        call_count[0] += 1
        raise Exception(f"erro diferente {call_count[0]}")

    curador = CuradorAutomatico(
        catalog=healing_catalog,
        healer=CyclingHealer(),
        step_runner=step_runner,
    )

    step_data = {"action": "click", "selector": "#btn"}
    collector = EvidenceCollector(page)
    page.goto(f"{test_server}/curation/fam-01-selector/", wait_until="domcontentloaded")
    payload = collector.collect(step_data, 0)

    outcome = curador.cure(step_data, "erro original", payload)
    assert outcome.status == ProgressResult.UNRESOLVED


def test_curador_stale_detection(test_server, healing_catalog):
    """Curador: stale detection marca entries antigas."""
    from datetime import datetime, timezone, timedelta
    from testforge.core.healing.models import HealingEntry
    from testforge.core.healing.storage import HealingCatalog
    from testforge.core.healing.curator import STALE_DAYS

    old_entry = HealingEntry(
        system="learned",
        symptom="teste stale",
        root_cause="teste",
        fix="teste",
        family="FAM-01",
        taxonomy="SEL-001",
        fix_type="learned",
        last_used_at=(datetime.now(timezone.utc) - timedelta(days=STALE_DAYS + 10)).isoformat(),
    )
    healing_catalog.add(old_entry)

    fresh_entry = HealingEntry(
        system="learned",
        symptom="teste fresh",
        root_cause="teste",
        fix="teste",
        family="FAM-01",
        taxonomy="SEL-001",
        fix_type="learned",
        last_used_at=datetime.now(timezone.utc).isoformat(),
    )
    healing_catalog.add(fresh_entry)

    curador = CuradorAutomatico(catalog=healing_catalog)
    marked = curador.stale_detection()
    assert marked >= 1

    updated = healing_catalog.get(old_entry.id)
    assert updated is not None
    assert "stale" in (updated.notes or "")
