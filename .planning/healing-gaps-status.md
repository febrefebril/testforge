# Healing Gaps Status

## 2026-07-01

### Fase 1 - Instrumentation
- Status: done
- Scope started:
  - Global silent skip counter in MetricsRepository
  - Instrumented normalizer gaps: 10, 11, 13, 14, 17
  - Instrumented recorder gap: 15
  - Overlay periodic snapshot error queue + no-editable marker (gaps 04/05 groundwork)
  - CLI summary for compile and run-incremental
- Pending in this phase:
  - none

- Validation delta:
  - `python -m pytest tests/test_metrics.py -q` -> 25 passed
  - `python -m pytest tests/unit/phase/test_phase1_silent_skip_instrumentation.py -q` -> 7 passed
  - `python -m pytest tests/test_metrics.py tests/unit/phase/test_phase1_silent_skip_instrumentation.py -q` -> 32 passed
  - `python -m testforge.cli.app compile uncategorized/test-pos-hotfix22 --data` -> OK (78 steps, script/data gerados)
  - `python -m testforge.cli.app run-incremental semantic_tests/ST-uncategorized_test-pos-hotfix22/test_st-uncategorized_test-pos-hotfix22.py --timeout 20 --no-healing --headless` -> steps carregados (`total=2`, `passed=1`, `failed=1`)
  - fix aplicado em `IncrementalRunner._find_recording_dir`: agora busca recordings em subpastas por categoria (ex.: `recordings/uncategorized/<id>`)
  - regressao adicionada em `tests/test_incremental_recording_lookup.py` -> `2 passed`
  - `python -m pytest -m unit -q` -> `189 passed, 1797 deselected, 1 xfailed`
  - Baseline created in `.planning/healing-gaps-baseline.md`

## 2026-07-01 (continuação)

### Fase 3 - Resolver retry chain
- Status: done
- Implemented:
  - `LocatorResolver.resolve(..., exclude_indices=...)`
  - in-memory `winning_idx_cache` + `promote_winning_candidate`
  - cache invalidation when excluded index is selected
  - runtime `step.click/fill/select` retry with next candidate on action failure
- Validation:
  - `python -m pytest tests/test_phase3_runtime_resolver.py -q` (venv) -> 25 passed

### Fase 4 - Curator no-runner degradation
- Status: done
- Implemented:
  - `ProgressResult.DEGRADED`
  - L0/L2 paths in curator now return `DEGRADED` with `reason="no_step_runner"` when no runner exists
  - `CurationOutcome.reason` field
- Validation:
  - `python -m pytest tests/test_phase4_curator_degraded_no_runner.py -q` (venv) -> passed
  - regression updates in B23/B33 tests -> passed

### Fase 5 - Mask postcondition correctness
- Status: done
- Implemented:
  - Added robust masked fill checks in `StepPostconditionValidator`:
    - currency magnitude compare via canonical parsing
    - date normalization compare (`DD/MM/YYYY` vs `YYYY-MM-DD`)
    - fallback non-empty only when value cannot be parsed as amount/date
  - Hardened mask-attribute detection to avoid false mask positives from non-string/mock values
- Validation:
  - `python -m pytest tests/test_step_postcondition.py -q` (venv) -> passed

### Fase 6 - Agents DOM-aware
- Status: done
- Implemented:
  - New helper module: `healing/agents/dom_introspection.py`
    - `dom_has_role`
    - `dom_has_mask_attrs`
    - `dom_has_dialog_handler`
  - `StateAgent` now downgrades `dialog_handler` proposal confidence to `0.4` when DOM/context lacks dialog evidence
  - `InputAgent` now downgrades mask strategy confidence to `0.35` when DOM lacks mask attrs
  - `EvidencePayload` extended with `page_state`
  - `EvidenceCollector` now populates `page_state.has_dialog_handler`
  - `FallbackRunner` now tags page state when dialog handler is registered
  - Added focused tests: `tests/test_phase6_agents_dom_aware.py`
- Validation:
  - `python -m pytest tests/test_phase6_agents_dom_aware.py tests/test_step_postcondition.py tests/test_phase4_curator_degraded_no_runner.py tests/test_phase3_runtime_resolver.py -q` (venv) -> 40 passed

### Fase 7 - Bug detection during recording
- Status: done
- Slice entregue (base funcional):
  - Novo modelo de dados em `src/testforge/models/bug_report.py`:
    - `BugSeverity`, `BugSource`, `BugSignal`, `BugReport`
    - serializacao `to_jsonl_line()`
  - Novo detector em `src/testforge/recorder/anomaly_detector.py`:
    - listeners para `console`, `pageerror`, `crash`, `response`
    - emissao de sinais `console_error`, `page_error`, `page_crash`, `network_4xx/5xx`
  - Integracao inicial em `RecorderController`:
    - flag `bug_detection_enabled` no `start()`
    - fila de sinais e processamento de respostas de bug (`__tfBugResponses`)
    - persistencia em `bug_report.jsonl`
  - Overlay estendido com API `window.__tfShowBugDetectionModal` e fila `window.__tfBugResponses`
- Testes adicionados:
  - `tests/unit/phase/test_phase7_bug_report_model.py`
  - `tests/unit/phase/test_phase7_anomaly_detector.py`
  - `tests/integration/phase/test_phase7_recorder_bug_response.py`
- Validation:
  - `python -m pytest tests/test_phase7_bug_report_model.py tests/test_phase7_anomaly_detector.py tests/test_phase7_recorder_bug_response.py tests/test_phase6_agents_dom_aware.py tests/test_step_postcondition.py -q` (venv) -> 17 passed
  - `python -m pytest tests/test_phase7_bug_report_model.py tests/test_phase7_anomaly_detector.py tests/test_phase7_recorder_bug_response.py tests/test_phase7_known_bug_marker_hook.py tests/test_browser.py -q` (venv) -> 25 passed, 1 xfailed

- Slice adicional entregue:
  - Compiler emite `@pytest.mark.known_bug(...)` quando segmento possui `step.context.has_bug_ref`
  - `known_bug` marker registrado em `pyproject.toml`
  - Hook pytest global (`tests/conftest.py`) aplica `xfail(strict=True)` para testes marcados como `known_bug`
  - Teste de cobertura do marker/hook em `tests/test_phase7_known_bug_marker_hook.py`

- Slice adicional (compile/report):
  - `cmd_compile` agora gera docs legiveis em `docs/bugs/BUG-*.md` a partir de `recordings/<id>/bug_report.jsonl`
  - `compile_semantic_steps` passa a serializar `has_bug_ref` quando presente no `step.context`
  - Cobertura adicionada:
    - `tests/integration/phase/test_phase7_compile_bug_docs.py`
    - `tests/unit/phase/test_phase7_semantic_steps_bug_ref.py`
- Validation adicional:
  - `python -m pytest tests/test_phase7_compile_bug_docs.py tests/test_phase7_semantic_steps_bug_ref.py tests/test_phase7_bug_report_model.py tests/test_phase7_anomaly_detector.py tests/test_phase7_recorder_bug_response.py tests/test_phase7_known_bug_marker_hook.py -q` (venv) -> 7 passed, 1 xfailed

- Slice adicional (auto amarracao bug -> semantic):
  - `RecordingNormalizer` agora le `bug_report.jsonl` automaticamente e anexa `step.context.has_bug_ref`
  - Mapeamento usa `step_idx` do bug report para timeline semantica (desconsiderando `navigation`)
  - Em conflitos no mesmo step, seleciona bug de maior severidade
  - Cobertura adicionada em `tests/integration/phase/test_phase7_normalizer_bug_ref_auto.py`
- Validation adicional:
  - `python -m pytest tests/test_phase7_normalizer_bug_ref_auto.py tests/test_phase7_semantic_steps_bug_ref.py tests/test_phase7_compile_bug_docs.py tests/test_phase7_bug_report_model.py tests/test_phase7_anomaly_detector.py tests/test_phase7_recorder_bug_response.py tests/test_phase7_known_bug_marker_hook.py -q` (venv) -> 9 passed, 1 xfailed
  - regressao ampliada com browser/fase5/fase6/fase7 -> `42 passed, 1 xfailed`
  - arquitetura atualizada com secao dedicada "Bug Detection During Recording" em `docs/ARCHITECTURE-V2.md`

### Fase 9 - Medium gaps restantes
- Status: done
- Implemented:
  - `AGENT_MIN_CONFIDENCE_NO_RUNNER=0.70` e `AGENT_MIN_CONFIDENCE_WITH_EXEC=0.50` em `healing/curator.py`
  - gates de confidence do Curator migrados para constantes
  - helper `_finalize_target_with_candidates(...)` no normalizer
  - synth de fallback CSS quando alvo vem sem candidatos e possui `raw_css_selector/css_path`
  - drop explicito (`None`) quando alvo nao possui candidatos nem CSS de fallback
- Validation:
  - cobertura adicionada em `tests/unit/phase/test_phase9_target_finalize_and_confidence.py`

### Fase 8 - Reorganizacao da suite de testes
- Status: done
- Slice entregue:
  - Migrados testes de fase para estrutura por categoria:
    - `tests/unit/phase/`: fase 1, 3, 4, 6, 7, 9
    - `tests/integration/phase/`: fase 7 (compile/normalizer/recorder)
  - `tests/conftest.py` agora aplica markers automaticamente por path:
    - `tests/unit/` -> `@pytest.mark.unit`
    - `tests/integration/` -> `@pytest.mark.integration`
    - `tests/e2e/` -> `@pytest.mark.e2e`
    - `tests/regression/` -> `@pytest.mark.regression`
    - `tests/contract/` -> `@pytest.mark.contract`
  - Novo lote migrado para `tests/unit/phase/`:
    - `test_phase1_tracing_cdp.py`
    - `test_phase2_locator_v2.py`
    - `test_phase4_sqlite_intent_catalog.py`
    - `test_phase5_pipeline_stages.py`
    - `test_phase6_telemetry_dashboard.py`
    - `test_phase7_component_resolver.py`
    - `test_phase7_known_bug_marker_hook.py`
- Validation:
  - `python -m pytest tests/unit/phase -q` -> 158 passed, 1 xfailed
  - `python -m pytest -m "unit or integration" -q` -> 163 passed, 1823 deselected, 1 xfailed
  - migracao final `tests/test_phase_b_*.py` para `tests/unit/phase` e `tests/integration/phase`
  - ajustes de compatibilidade para schema atual (`value_mutations.value`) e descoberta recursiva de recordings (ignorando `capture_runs` e `raw_events` vazios)
  - `python -m pytest tests/unit/phase/test_phase_b_evidence.py tests/unit/phase/test_phase_b_pr3_polling_masked.py -q` -> 31 passed
  - `python -m pytest tests/integration/phase/test_phase_b_e2e_validation.py tests/integration/phase/test_phase_b_compiler_e2e.py -q` -> 8 passed
  - `python -m pytest -m integration -q` -> 13 passed, 1974 deselected
- Pending:
  - none

### Fase 0 - Diagramas
- Status: done (com exclusao explicita de PNG)
- Implemented:
  - README de diagramas criado em `docs/DIAGRAMAS/README.md`
  - checklist de regeneracao de PNG documentado
- Pending:
  - regenerar PNGs e validar render de todos os `.puml` (EXCLUIDO por instrucao explicita do usuario nesta execucao)

## Quality gate notes
- `python -m pytest -m unit -q` esta verde: `189 passed, 1797 deselected, 1 xfailed`.
- `python -m pytest -m integration -q` esta verde: `13 passed, 1974 deselected`.
- Plano executado ate conclusao com excecao autorizada: regeneracao de PNG dos diagramas.
