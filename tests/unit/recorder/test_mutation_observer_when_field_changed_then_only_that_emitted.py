"""RC-16: field snapshot interval emits diff-only — changed fields only."""
import re
from pathlib import Path

import pytest

OVERLAY_JS = (
    Path(__file__).resolve().parents[3]
    / "src" / "testforge" / "recorder" / "overlay_inject.js"
)


@pytest.fixture(scope="module")
def overlay_source() -> str:
    return OVERLAY_JS.read_text(encoding="utf-8")


@pytest.mark.unit
class TestMutationObserverWhenFieldChangedThenOnlyThatEmitted:

    def test_last_field_snapshot_values_dict_initialized(self, overlay_source):
        """RC-16: dedup dict must exist to track last-seen values per fingerprint."""
        assert "__tfLastFieldSnapshotValues" in overlay_source, (
            "Missing __tfLastFieldSnapshotValues. RC-16: full-form snapshot not suppressed."
        )

    def test_snapshot_interval_diffs_before_push(self, overlay_source):
        """RC-16: interval must compare value against last-known before pushing."""
        pattern = re.compile(
            r"__tfLastFieldSnapshotValues\[_fp\]\s*!==\s*_s\.value",
            re.DOTALL,
        )
        assert pattern.search(overlay_source), (
            "Field snapshot interval must diff by fingerprint (RC-16). "
            "Unchanged siblings (inputSearchNis value='') must not be emitted."
        )

    def test_changed_array_only_pushed(self, overlay_source):
        """RC-16: only the changed slice is pushed to __tfFieldSnapshotQueue."""
        pattern = re.compile(
            r"changed\.push\(_s\).*?if\s*\(changed\.length\)",
            re.DOTALL,
        )
        assert pattern.search(overlay_source), (
            "Snapshot interval must push only the 'changed' subset, not full snaps."
        )

    def test_last_value_updated_after_diff(self, overlay_source):
        """RC-16: last-known value must be updated after emitting a changed field."""
        pattern = re.compile(
            r"__tfLastFieldSnapshotValues\[_fp\]\s*=\s*_s\.value",
            re.DOTALL,
        )
        assert pattern.search(overlay_source), (
            "Last-known value must be updated (RC-16) so the same value isn't re-emitted."
        )
