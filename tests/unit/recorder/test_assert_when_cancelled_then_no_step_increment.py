"""NB-06: assert cancel/timeout/Esc não incrementa tf-step-count."""
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
class TestAssertWhenCancelledThenNoStepIncrement:
    def test_cancel_assert_mode_does_not_touch_step_count(self, overlay_source):
        """_cancelAssertMode body must NOT reference tf-step-count."""
        # Find start of function and slice up to matching closing brace via depth counter.
        idx = overlay_source.find("window._tf_cancelAssertMode = function()")
        assert idx >= 0, "NB-06: _tf_cancelAssertMode declaration not found."
        # From opening brace, walk to matching close
        brace_start = overlay_source.find("{", idx)
        assert brace_start >= 0
        depth = 0
        end = brace_start
        for i in range(brace_start, min(len(overlay_source), brace_start + 3000)):
            c = overlay_source[i]
            if c == "{":
                depth += 1
            elif c == "}":
                depth -= 1
                if depth == 0:
                    end = i
                    break
        body = overlay_source[brace_start:end + 1]
        assert "tf-step-count" not in body, (
            "NB-06: cancel path must not increment tf-step-count. "
            f"Body preview: {body[:200]}..."
        )

    def test_esc_key_uses_cancel_not_direct_increment(self, overlay_source):
        """Escape key handler must delegate to _cancelAssertMode, not increment directly."""
        pattern = re.compile(
            r"e\.key\s*===\s*['\"]Escape['\"][\s\S]{0,300}?_tf_cancelAssertMode",
        )
        assert pattern.search(overlay_source), (
            "NB-06: Escape key handler must call _tf_cancelAssertMode."
        )

    def test_assert_timeout_uses_cancel_not_direct_increment(self, overlay_source):
        """30s timeout branch must call _cancelAssertMode, not increment counter."""
        pattern = re.compile(
            r"__tfAssertTimeout\s*=\s*setTimeout\(function\s*\(\)\s*\{([^}]{0,300})\}",
            re.DOTALL,
        )
        match = pattern.search(overlay_source)
        assert match, "NB-06: assert timeout setTimeout not found."
        body = match.group(1)
        assert "tf-step-count" not in body, (
            "NB-06: assert timeout must not increment step counter."
        )
        assert "_cancelAssertMode" in body, (
            "NB-06: assert timeout must delegate to _cancelAssertMode."
        )

    def test_step_count_increment_only_after_addstep_assert(self, overlay_source):
        """The line that increments tf-step-count for assert must come AFTER _addStep('assert', ...)."""
        # Find the button click handler in _showAssertMenu that fires on user selection.
        # Ensures the increment path is gated by _addStep call.
        pattern = re.compile(
            r"_addStep\(['\"]assert['\"],[^)]+\);[\s\S]{0,600}?tf-step-count",
        )
        assert pattern.search(overlay_source), (
            "NB-06: tf-step-count increment must appear only after _addStep('assert', ...) call."
        )
