# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Environment Setup

```bash
source activate.sh      # Activates .venv + adds GSD Core / BMAD bins to PATH
pip install -e ".[dev]" # Install package + dev deps (pytest, pytest-playwright)
playwright install chromium
```

## Commands

```bash
# Tests
pytest tests/ -v                                        # all 194 tests
pytest tests/test_sprint3_field_snapshots.py -v         # single suite
pytest tests/ -k "test_name"                            # single test
pytest tests/ -m "not slow"                             # skip slow

# CLI (after source activate.sh)
testforge record http://localhost:8765 --name "test"
testforge compile <recording-name> --data
testforge run semantic_tests/ST-<name>/test_st_<name>.py
testforge run-incremental semantic_tests/ST-<name>/test_st_<name>.py
testforge demo-heal
testforge pilot-report

# Fake bank app (needed for E2E tests)
cd synthetic_lab/fake-react-bank-app && python -m http.server 8765 &
```

CI runs `pytest` (no args) across Python 3.10–3.13 on every push.

## Architecture

TestForge is a self-healing E2E test recorder. The core insight: record *semantic intent* (role, accessible name, visible text) instead of fragile CSS selectors. When a selector breaks at run time, a 4-layer healing pipeline repairs it without human intervention.

### Data Pipeline (4 stages)

```
Browser → raw_events.jsonl       (RecorderController injects JS listeners)
        → steps.jsonl            (user-curated actions, Shift+A for asserts)
        → SemanticTestCase       (RecordingNormalizer, src/testforge/semantic/)
        → test_*.py              (PlaywrightCompiler, executable Playwright script)
```

`SemanticAction` carries `LocatorCandidate[]` (role, label, placeholder, test-id, text, XPath) ranked by score plus compound multi-attribute candidates. The compiled script tries Playwright-native locators (`get_by_role`, `get_by_label`, `get_by_placeholder`, `get_by_test_id`) first, then L0.5 fuzzy `get_by_role` with regex, then CSS fallback, before escalating to healing.

### Healing Layers (L0 → L3)

| Layer | Class | Mechanism | Cost |
|-------|-------|-----------|------|
| L0 | `HealingCatalog` | Exact match against `healing_catalog.jsonl`; auto-learns from successful heals (`record_success`) | <50ms |
| L1 | `FallbackRunner` | Try ranked `LocatorCandidate[]` from MIS | 2-5s |
| L2 | `SpecialistAgents` | 6 deterministic agents by failure family | <100ms |
| L3 | `LLMHealer` | Azure GPT-4.1-mini (or `MockLLMHealer` offline) | ~500 tok |

`SmartStepRunner` (in `runner/fallback_runner.py`) applies 10 run-time strategies before escalating: `visibility_wait`, `press_sequentially`, `overlay_dismiss`, `dialog_handler`, `iframe_switch`, `synthetic_click`, `label_click`, `has_text_fallback`, `semantic_locator_conversion`, `xpath_fallback`.

### Key Modules

| Path | Responsibility |
|------|---------------|
| `src/testforge/cli/app.py` | All CLI commands (argparse) |
| `src/testforge/recorder/recorder_controller.py` | Playwright-based recorder, injects JS hooks |
| `src/testforge/recorder/recording_status.py` | Recording state machine |
| `src/testforge/semantic/recording_normalizer.py` | raw_events → SemanticTestCase; includes intent reconstruction (_ir_* methods: polling, value_mutations, snapshots, form_values, network) |
| `src/testforge/semantic/compiler.py` | SemanticTestCase → Playwright script; native locators + L0.5 fuzzy get_by_role |
| `src/testforge/recorder/overlay_inject.js` | JS injected into browser for event capture (extracted from Python) |
| `src/testforge/validation/readiness_gate.py` | 5-criteria ReadinessGate (READY/REVIEW/FAIL) |
| `src/testforge/validation/incremental_validator.py` | normalize → complete → validate → gate pipeline |
| `src/testforge/healing/healing_catalog.py` | L0 JSONL catalog lookup |
| `src/testforge/healing/agents/` | L2 specialist agents (1 per failure family) |
| `src/testforge/healing/llm_healer.py` | L3 LLM healer (real + mock) |
| `src/testforge/runner/fallback_runner.py` | FallbackRunner + SmartStepRunner |
| `src/testforge/runner/incremental_runner.py` | Step-by-step runner with pre/post conditions |
| `src/testforge/metrics/pilot_metrics.py` | Aggregated pilot metrics + dashboard |
| `src/testforge/taxonomy/` | 11 failure families, 88 codes, 51 keywords |
| `src/testforge/models/pipeline.py` | Pipeline stage enum + manifest |

### Failure Taxonomy

11 families (FAM-01 through FAM-11): SEL (broken selector), TIM (timeout), CTX (iframe), STA (overlay), DOM (stale element), INP (masked input), FILE (upload), AST (assertion), REC (recorder miss), OBS (network/runtime), LIM (CAPTCHA). L2 agents exist for FAM-01 to FAM-07; FAM-08 to FAM-11 escalate directly to L3.

### Storage Layout

```
recordings/<name>/          # Raw recording artifacts
  raw_events.jsonl
  steps.jsonl
  recording_metadata.json   # Includes status_history

semantic_tests/ST-<name>/   # Compiled outputs
  test_st_<name>.py         # Executable Playwright test
  semantic_steps.jsonl
  test_data.json            # Extracted field values (--data flag)
  readiness_report.md       # Gate output

reports/                    # pilot-report outputs
  pilot_readiness_report.json
  pilot_readiness_report.md

healing_catalog.jsonl        # L0 healing entries (root level)
```

### LLM Configuration

No API key needed — `MockLLMHealer` is default. For real healing:

```bash
export AZURE_OPENAI_ENDPOINT="https://your-resource.openai.azure.com/"
export AZURE_OPENAI_KEY="..."
export AZURE_OPENAI_DEPLOYMENT="gpt-4.1-mini"   # or OPENAI_API_KEY for OpenAI
```

Model: GPT-4.1-mini · temp 0.3 · max 500 tokens · 3 retries with backoff.

### Intent Lab

`tests/intent_lab/` covers 14 edge-case HTML pages (mask inputs, contenteditable, shadow DOM, iframes, network-payload-only fields, etc.). Add new lab pages under `tests/intent_lab/pages/` and corresponding tests in `tests/intent_lab/`.

### bug_lab/

`bug_lab/` holds regression fixtures for confirmed bugs. `pytest.ini_options.testpaths` includes it, so `pytest` runs those tests automatically.
