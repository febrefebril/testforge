# Healing Gaps Baseline

## 2026-07-01

### Fase 1 - Instrumentation Baseline
- Status: partial
- Unit validation:
  - `python -m pytest tests/test_metrics.py -q` -> 25 passed
- Compile smoke test:
  - Command now executes from this workspace/venv.
  - Command attempted:
    - `.venv\\Scripts\\python.exe -m testforge.cli.app compile recordings/test-pos-hotfix27_2`
  - Result:
    - CLI resolved correctly to this repo, but recording path does not exist in this workspace snapshot (`recordings/` contains only `SIOPI/` and `uncategorized/`, without `raw_events.jsonl` fixtures from handoff).

- Additional progress after baseline:
  - Phase 3 resolver retry chain implemented and validated.
  - Phase 4 curator degraded semantics implemented and validated.
- Silent-skip categories currently instrumented:
  - `snapshot_exception`
  - `diagnostic_assess_error`
  - `entry_label_empty`
  - `click_no_candidates`
  - `overlay_detect`
  - `ir_final_state_field_missing`
  - `ir_final_state_field_empty_at_end`
  - `ir_dedupe_empty_key`
  - `ir_dedupe_empty_value`
