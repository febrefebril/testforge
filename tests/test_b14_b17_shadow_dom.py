"""B14/B17 — shadow DOM walker + chain locator.

When the recorder captures an element living inside an open shadow root,
it now records the host descriptor (`shadow_host`) on the target. The
normalizer surfaces it as the highest-priority LocatorCandidate so the
runner can do `page.locator(host).locator(child)` (Playwright pierces
open roots automatically when given a chained selector).

Closed shadow roots are still blind spots — the recorder cannot walk
into them from outside.

This file pins:
1. SemanticTarget carries the shadow_host descriptor.
2. _build_target inserts a high-priority shadow_host_chain candidate.
3. The chain selector format is `host >> inner`.
4. Recordings without shadow_host get no extra candidate (no regression
   for normal pages).
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
        # The first candidate must be the shadow chain — Playwright should
        # try it before any naive CSS path.
        assert target.candidates, "Expected at least one candidate"
        first = target.candidates[0]
        assert first.strategy == "shadow_host_chain", (
            f"First candidate should be shadow_host_chain, got "
            f"{first.strategy} ({first.selector})"
        )
        assert ">>" in first.selector, (
            f"Chain selector must use '>>' format, got {first.selector!r}"
        )
        assert first.selector.startswith("x-card#cpf-card"), (
            f"Chain must start with host selector, got {first.selector!r}"
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
            # no shadow_host key at all
        })
        chains = [c for c in target.candidates if c.strategy == "shadow_host_chain"]
        assert chains == [], (
            "Plain document-tree targets must not get a shadow chain "
            "candidate."
        )

    def test_null_shadow_host_means_no_chain_candidate(self):
        # Closed shadow root → recorder writes shadow_host=null.
        target = self._n()._build_target({
            "tag": "input",
            "accessible_name": "CPF",
            "shadow_host": None,
        })
        chains = [c for c in target.candidates if c.strategy == "shadow_host_chain"]
        assert chains == []


class TestCaptureSchemaBumped:
    def test_schema_version_at_least_2(self):
        # B14/B17 introduced v2 (target.shadow_host). H20 then introduced
        # v3 (scenario_boundary event). The actual version may keep
        # climbing; the invariant is only that we did bump.
        from testforge.recorder.capture_fingerprint import CAPTURE_SCHEMA_VERSION
        assert CAPTURE_SCHEMA_VERSION >= 2, (
            "B14/B17 added target.shadow_host to the recorder output. "
            "Bump CAPTURE_SCHEMA_VERSION when this field shape changes."
        )
