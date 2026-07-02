from testforge.healing.curator import (
    AGENT_MIN_CONFIDENCE_NO_RUNNER,
    AGENT_MIN_CONFIDENCE_WITH_EXEC,
)
from testforge.metrics.metrics_repository import MetricsRepository
from testforge.semantic.recording_normalizer import RecordingNormalizer


def test_phase9_confidence_threshold_constants_are_defined():
    assert AGENT_MIN_CONFIDENCE_NO_RUNNER == 0.70
    assert AGENT_MIN_CONFIDENCE_WITH_EXEC == 0.50
    assert AGENT_MIN_CONFIDENCE_NO_RUNNER > AGENT_MIN_CONFIDENCE_WITH_EXEC


def test_finalize_target_when_empty_candidates_and_raw_css_then_synthesizes_fallback():
    MetricsRepository.reset_silent_skip_summary_global()
    normalizer = RecordingNormalizer()

    target = normalizer._build_target({
        "tag": "div",
        "raw_css_selector": "div.main > div.cta",
    })

    assert target is not None
    assert target.candidates
    assert target.candidates[0].strategy == "css_fallback_synth"
    assert target.candidates[0].selector == "div.main > div.cta"

    summary = MetricsRepository.get_silent_skip_summary_global()
    assert summary.get("normalizer.empty_candidates_synth", 0) == 1


def test_finalize_target_when_empty_candidates_and_no_css_then_returns_none():
    MetricsRepository.reset_silent_skip_summary_global()
    normalizer = RecordingNormalizer()

    target = normalizer._build_target({"tag": "div"})

    assert target is None
    summary = MetricsRepository.get_silent_skip_summary_global()
    assert summary.get("normalizer.target_dropped", 0) == 1
