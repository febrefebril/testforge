from __future__ import annotations

from testforge.core.healing.classifier import FailureClassifier, ClassificationResult
from testforge.core.healing.collector import EvidencePayload
from testforge.core.healing.llm.healer import LLMHealingProposal


def make_evidence(**overrides) -> EvidencePayload:
    return EvidencePayload(
        dom_snapshot=overrides.get("dom", "<html><body><button>OK</button></body></html>"),
        step_context={
            "action": overrides.get("action", "click"),
            "selector": overrides.get("selector", "#btn"),
            "value": overrides.get("value", ""),
            "tag_name": overrides.get("tag", "button"),
            "text": overrides.get("text", "OK"),
            "url": "http://example.com",
            "page_title": "Test",
            **overrides.get("step_context", {}),
        },
        console_errors=overrides.get("console", []),
        network_state=overrides.get("network", []),
        page_url="http://example.com",
        failure_signature="test",
        collected_at="2026-01-01T00:00:00",
        step_index=0,
        is_sufficient=True,
        **{k: v for k, v in overrides.items() if k in ("is_sufficient", "insufficiency_reason")},
    )


class TestFailureClassifier:

    def test_classify_empty_error(self):
        classifier = FailureClassifier()
        result = classifier.classify("")
        assert result.family == ""
        assert result.taxonomy_id == ""
        assert result.confidence == 0.0

    def test_classify_strict_locator(self):
        classifier = FailureClassifier()
        result = classifier.classify("strict locator violation")
        assert result.family == "FAM-01"
        assert result.taxonomy_id == "SEL-001"
        assert result.confidence == 0.9
        assert result.matched_by == "regex"

    def test_classify_intercepted(self):
        classifier = FailureClassifier()
        result = classifier.classify("click intercepted")
        assert result.family == "FAM-01"
        assert result.taxonomy_id == "SEL-002"

    def test_classify_multiple_elements(self):
        classifier = FailureClassifier()
        result = classifier.classify("multiple elements found")
        assert result.family == "FAM-01"
        assert result.taxonomy_id == "SEL-009"

    def test_classify_loading(self):
        classifier = FailureClassifier()
        result = classifier.classify("page still loading")
        assert result.family == "FAM-02"
        assert result.taxonomy_id == "TIM-001"

    def test_classify_stale_element(self):
        classifier = FailureClassifier()
        result = classifier.classify("stale element reference")
        assert result.family == "FAM-02"
        assert result.taxonomy_id == "TIM-002"

    def test_classify_network_error(self):
        classifier = FailureClassifier()
        result = classifier.classify("net::ERR_CONNECTION_REFUSED")
        assert result.family == "FAM-02"
        assert result.taxonomy_id == "TIM-003"

    def test_classify_fill_error(self):
        classifier = FailureClassifier()
        result = classifier.classify("fill operation failed")
        assert result.family == "FAM-06"
        assert result.taxonomy_id == "INP-001"

    def test_classify_masked_input(self):
        classifier = FailureClassifier()
        result = classifier.classify("masked input detection")
        assert result.family == "FAM-06"
        assert result.taxonomy_id == "INP-007"

    def test_classify_iframe_context(self):
        classifier = FailureClassifier()
        result = classifier.classify("iframe context issue")
        assert result.family == "FAM-03"
        assert result.taxonomy_id == "CTX-001"

    def test_classify_shadow_dom(self):
        classifier = FailureClassifier()
        result = classifier.classify("shadow DOM context issue")
        assert result.family == "FAM-03"
        assert result.taxonomy_id == "CTX-002"

    def test_classify_dialog(self):
        classifier = FailureClassifier()
        result = classifier.classify("unexpected dialog")
        assert result.family == "FAM-04"
        assert result.taxonomy_id == "STA-004"

    def test_classify_alert(self):
        classifier = FailureClassifier()
        result = classifier.classify("unexpected alert")
        assert result.family == "FAM-04"
        assert result.taxonomy_id == "STA-004"

    def test_classify_session_expired(self):
        classifier = FailureClassifier()
        result = classifier.classify("session expired")
        assert result.family == "FAM-04"
        assert result.taxonomy_id == "STA-005"

    def test_classify_overlay(self):
        classifier = FailureClassifier()
        result = classifier.classify("overlay blocking element")
        assert result.family == "FAM-04"
        assert result.taxonomy_id == "STA-006"

    def test_classify_file_upload(self):
        classifier = FailureClassifier()
        result = classifier.classify("file upload failed")
        assert result.family == "FAM-07"
        assert result.taxonomy_id == "FILE-001"

    def test_classify_assertion(self):
        classifier = FailureClassifier()
        result = classifier.classify("AssertionError: expected true")
        assert result.family == "FAM-08"
        assert result.taxonomy_id == "AST-001"

    def test_classify_404(self):
        classifier = FailureClassifier()
        result = classifier.classify("404 not found")
        assert result.family == "FAM-02"
        assert result.taxonomy_id == "TIM-003"

    def test_classify_unknown_error(self):
        classifier = FailureClassifier()
        result = classifier.classify("some random unknown error")
        assert result.family == ""
        assert result.taxonomy_id == ""
        assert result.confidence == 0.0

    def test_classify_timeout_fallback_group(self):
        classifier = FailureClassifier()
        result = classifier.classify("TimeoutError: waiting for locator")
        assert result.family == "FAM-01"
        assert result.taxonomy_id == "SEL-004"

    def test_classify_wait_fallback_timing(self):
        classifier = FailureClassifier()
        result = classifier.classify("waiting for selector failed")
        assert result.family == "FAM-02"
        assert result.taxonomy_id == "TIM-005"

    def test_classify_with_evidence_sufficient(self):
        classifier = FailureClassifier()
        evidence = make_evidence(action="click")
        result = classifier.classify("strict locator: element not found", evidence)
        assert result.family == "FAM-01"
        assert result.taxonomy_id == "SEL-001"
        assert result.matched_by == "regex"

    def test_classify_llm_fallback_called_when_no_keyword_match(self):
        class MockLLM:
            def heal_or_unresolved(self, payload, error_message, family=""):
                return LLMHealingProposal(
                    taxonomy_id="TIM-005",
                    family="FAM-02",
                    strategy="visibility_wait",
                    new_locator="wait_for_selector(state='visible')",
                    confidence=0.8,
                    rationale="Timing fallback",
                )

        classifier = FailureClassifier(llm_healer=MockLLM())
        evidence = make_evidence(action="click")
        result = classifier.classify("custom bizarre glitch", evidence)
        assert result.family == "FAM-02"
        assert result.taxonomy_id == "TIM-005"
        assert result.matched_by == "llm"

    def test_classify_llm_fallback_invalid_response(self):
        class MockLLM:
            def heal_or_unresolved(self, payload, error_message, family=""):
                return LLMHealingProposal(
                    taxonomy_id="INVALID",
                    family="FAM-XX",
                    confidence=0.8,
                    rationale="Invalid response",
                )

        classifier = FailureClassifier(llm_healer=MockLLM())
        evidence = make_evidence(action="click")
        result = classifier.classify("custom weird error", evidence)
        assert result.family == ""
        assert result.taxonomy_id == ""
        assert result.confidence == 0.0

    def test_classify_llm_fallback_empty_response(self):
        class MockLLM:
            def heal_or_unresolved(self, payload, error_message, family=""):
                return LLMHealingProposal(confidence=0.0, rationale="No response")

        classifier = FailureClassifier(llm_healer=MockLLM())
        evidence = make_evidence(action="click")
        result = classifier.classify("custom weird error", evidence)
        assert result.family == ""
        assert result.taxonomy_id == ""
        assert result.confidence == 0.0

    def test_classify_keyword_case_insensitive(self):
        classifier = FailureClassifier()
        result = classifier.classify("STRICT LOCATOR ERROR")
        assert result.family == "FAM-01"
        assert result.taxonomy_id == "SEL-001"
        assert result.confidence == 0.9

    def test_classify_keyword_not_found_return_empty(self):
        classifier = FailureClassifier()
        result = classifier.classify("browser crashed unexpectedly")
        assert result.family == ""
        assert result.taxonomy_id == ""


class TestClassificationResultDataclass:
    def test_default_values(self):
        r = ClassificationResult()
        assert r.taxonomy_id == ""
        assert r.family == ""
        assert r.confidence == 0.0
        assert r.symptom == ""
        assert r.matched_by == ""

    def test_custom_values(self):
        r = ClassificationResult(
            taxonomy_id="SEL-001",
            family="FAM-01",
            confidence=0.9,
            symptom="strict locator",
            matched_by="regex",
        )
        assert r.taxonomy_id == "SEL-001"
        assert r.family == "FAM-01"
        assert r.confidence == 0.9


class TestFailureCountInCatalog:
    def test_increment_and_get_failure_count(self, healing_catalog):
        assert healing_catalog.get_failure_count("SEL-001") == 0
        healing_catalog.increment_failure_count("SEL-001")
        assert healing_catalog.get_failure_count("SEL-001") == 1
        healing_catalog.increment_failure_count("SEL-001")
        assert healing_catalog.get_failure_count("SEL-001") == 2

    def test_reset_failure_count(self, healing_catalog):
        healing_catalog.increment_failure_count("SEL-001")
        healing_catalog.increment_failure_count("SEL-001")
        assert healing_catalog.get_failure_count("SEL-001") == 2
        healing_catalog.reset_failure_count("SEL-001")
        assert healing_catalog.get_failure_count("SEL-001") == 0

    def test_different_taxonomies_independent(self, healing_catalog):
        healing_catalog.increment_failure_count("SEL-001")
        healing_catalog.increment_failure_count("TIM-002")
        healing_catalog.increment_failure_count("SEL-001")
        assert healing_catalog.get_failure_count("SEL-001") == 2
        assert healing_catalog.get_failure_count("TIM-002") == 1
        assert healing_catalog.get_failure_count("INP-001") == 0

    def test_persists_across_catalog_instances(self, healing_catalog, tmp_path):
        healing_catalog.increment_failure_count("SEL-001")
        healing_catalog2 = type(healing_catalog)(str(healing_catalog._path))
        assert healing_catalog2.get_failure_count("SEL-001") == 1


class TestCuradorPipelineWithClassifier:
    def test_cure_classifies_before_l1(self, healing_catalog):
        from testforge.core.healing.curator import CuradorAutomatico

        curador = CuradorAutomatico(catalog=healing_catalog)
        evidence = make_evidence(action="click", selector="#btn-salvar")
        outcome = curador.cure(
            {"action": "click", "selector": "#btn-salvar"},
            "strict locator timeout",
            evidence,
        )
        assert outcome.classification_layer == "regex"
        assert outcome.classification_confidence == 0.9
        assert outcome.family == "FAM-01"

    def test_cure_passes_classification_to_outcome(self, healing_catalog):
        from testforge.core.healing.curator import CuradorAutomatico

        curador = CuradorAutomatico(catalog=healing_catalog)
        evidence = make_evidence(action="click")
        outcome = curador.cure(
            {"action": "click", "selector": "#x"},
            "",
            evidence,
        )
        assert outcome.classification_layer == ""
        assert outcome.classification_confidence == 0.0
        assert outcome.family == ""

    def test_cure_increments_failure_count_on_unresolved(self, healing_catalog):
        from testforge.core.healing.curator import CuradorAutomatico

        curador = CuradorAutomatico(catalog=healing_catalog)
        evidence = make_evidence(action="click")
        curador.cure(
            {"action": "click", "selector": "#x"},
            "strict locator timeout",
            evidence,
        )
        assert healing_catalog.get_failure_count("SEL-001") >= 1

    def test_cure_resets_failure_count_on_success(self, healing_catalog):
        from testforge.core.healing.curator import CuradorAutomatico

        healing_catalog.increment_failure_count("SEL-001")
        healing_catalog.increment_failure_count("SEL-001")

        curador = CuradorAutomatico(catalog=healing_catalog, step_runner=lambda sd: None)
        evidence = make_evidence(action="click", selector="#btn-salvar", text="Salvar")
        outcome = curador.cure(
            {"action": "click", "selector": "#btn-salvar", "text": "Salvar"},
            "strict locator timeout",
            evidence,
        )
        assert healing_catalog.get_failure_count("SEL-001") == 0
