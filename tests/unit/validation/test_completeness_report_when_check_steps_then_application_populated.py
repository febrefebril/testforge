"""NB-17: check_steps propaga application + base_url ao CompletenessReport."""
import pytest


@pytest.mark.unit
class TestCompletenessReportWhenCheckStepsThenApplicationPopulated:
    def test_application_propagated_when_provided(self):
        from testforge.validation.intent_completeness import IntentCompletenessChecker

        checker = IntentCompletenessChecker()
        report = checker.check_steps(
            steps=[],
            field_values=None,
            recording_id="my_rec",
            application="web",
            base_url="https://tqs.example.com/",
        )
        assert report.application == "web", "NB-17: application must propagate from check_steps arg"
        assert report.base_url == "https://tqs.example.com/", "NB-17: base_url must propagate"
        assert report.recording_id == "my_rec", "NB-17: recording_id must propagate"

    def test_defaults_empty_when_not_provided(self):
        from testforge.validation.intent_completeness import IntentCompletenessChecker

        checker = IntentCompletenessChecker()
        report = checker.check_steps(steps=[], field_values=None)
        assert report.application == ""
        assert report.base_url == ""
        assert report.recording_id == ""
