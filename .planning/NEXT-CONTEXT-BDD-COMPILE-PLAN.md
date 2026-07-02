# Next Context Plan - BDD Compile Extension

Date: 2026-07-02
Status: planned (not implemented in this context)

## Goal
Add a new final step to `compile` that generates a readable, Gherkin-like automated test package while preserving self-healing behavior and test automation best practices.

## Explicit Requirements from User
1. Do not implement now; only preserve plan for next context.
2. Add the new generation at the end of `compile` (no extra manual pipeline steps for user).
3. Final generated script must keep self-healing capability.
4. Test data must remain separated from test logic.
5. Final folder structure and committed artifacts must follow automated testing best practices.

## Proposed Deliverable (Next Context)
When `compile` completes successfully, also generate a BDD package per test under semantic output, for example:
- `semantic_tests/ST-<id>/bdd/scenario.feature`
- `semantic_tests/ST-<id>/bdd/steps_steps.py`
- `semantic_tests/ST-<id>/bdd/test_bdd_runner.py`
- `semantic_tests/ST-<id>/bdd/test_data.json` (or link to existing generated data file)
- `semantic_tests/ST-<id>/bdd/README.md`

## Technical Direction
1. Keep current Playwright compile output unchanged for backward compatibility.
2. Reuse `SemanticTestCase` + `semantic_steps.jsonl` as source of truth.
3. Reuse/align language heuristics from diagnostic Gherkin writer.
4. Keep deterministic generation as baseline.
5. Add optional Azure LLM refinement pass for readability only (never for core correctness).
6. If LLM unavailable/fails, fallback to deterministic output.

## Self-Healing Guarantee
1. BDD runner should call existing runtime step API (`testforge.runtime.step`) so resolver and healing chain remain active.
2. Avoid plain hardcoded locator calls in generated BDD runner.
3. Keep candidate artifacts and intent text wiring compatible with current resolver flow.

## Data Separation Rule
1. Never hardcode sensitive values into `.feature`.
2. Use placeholders in feature steps.
3. Resolve values from external data fixture (`test_data.json` / scenarios map) in step definitions.

## Quality Gates (Next Context)
1. Unit tests for mapping `SemanticAction -> Gherkin sentence`.
2. Integration tests for `compile` producing BDD artifacts from real recordings.
3. Smoke execution to verify generated BDD runner still supports self-healing path.
4. Syntax checks on generated Python artifacts.

## Out of Scope in This Context
- No code implementation.
- No migration of existing generated tests.
- No behavior changes to run-incremental beyond preserving current flow.
