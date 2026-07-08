# Widget regression suite

Integration tests that pipeline synthetic recordings through
`RecordingNormalizer` → `PlaywrightCompiler` and assert the emitted
`SemanticTestCase` and script preserve widget-specific behavior.

**Scope:** catches regressions in framework component handling (Angular
Material, React MUI, PrimeFaces, etc.) at the normalizer/compiler level
before they surface as failing E2E runs.

**Structure:**

- `fixtures/<widget>/` — synthetic `raw_events.jsonl` + `steps.jsonl` per widget
- `test_<widget>_*.py` — pytest cases per widget

**Adding a new regression:**

1. Reproduce the bug end-to-end (e.g. `testforge record ... && run-incremental`).
2. Copy the smallest slice of `raw_events.jsonl` + `steps.jsonl` that
   triggers the bug into `fixtures/<widget>/`.
3. Write a pytest that normalizes+compiles the fixture and asserts the
   fixed behavior (correct `skip_reason`, correct locator, correct step order, …).
4. Run against the buggy commit — should FAIL. Then apply fix — should PASS.
