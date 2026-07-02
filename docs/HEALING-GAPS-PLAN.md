# TestForge — Healing/Recording Gaps Remediation Plan (v2)

**Autor**: Session audit 2026-07-01/02
**Target executor**: Claude Sonnet 4.7 ou Opus 4.7 (LLM implementadora)
**Branch base**: `feature/inline-overlay-prompt` (base `fix/improvements-v0.4.2`)
**Escopo**: 17 gaps críticos+high+med em pipeline capture→normalize→compile→resolve→execute→heal + 1 feature nova (bug detection) + sync diagramas + reorganização testes padrão de mercado
**Custo estimado**: 22-28h total, 9 fases independentes
**Prioridade**: aplicação testa aplicações críticas (bancárias, seguros, saúde) — corretude > velocidade

---

## 1. Sumário executivo

Auditoria dupla revelou 3 problemas convergentes:

**A. 17 gaps de código** — cada camada aceita sinais fracos (existência, keyword-match, non-empty) como validação e silencia falhas com `except: pass` ou `continue`. Cultura "verde = OK" encoded na base. Métrica `assert_hit_rate` reportou 14-64% quando cada teste individual reportava PASS.

**B. 10 gaps em diagramas** — documentação PlantUML espelha bugs (`resolve(intent, candidates, action)` sugere action-aware que não existe; `Locator (or skip)` sugere validação que é apenas `count()`). Próxima LLM ou dev que ler é enganado.

**C. Gap arquitetural em recording de aplicação crítica** — quando QA está gravando aplicação bancária/segura e ela apresenta bug, TestForge grava o comportamento errado como esperado. Não há detecção nem captura do comportamento correto.

Plano corrige (A) via 6 fases ordenadas por risco, (B) via par de diagramas ATUAL/ALVO por gap crítico, (C) via feature Fase 7 com anomaly detector + overlay prompt + pytest.mark.known_bug em código gerado.

Toda implementação segue `docs/TEST-PATTERNS.md` (contrato de teste, obrigatório).

---

## 2. Como usar este plano

**LLM implementadora**:
1. Leia integralmente este plano + `docs/TEST-PATTERNS.md` + `docs/ARCHITECTURE-V2.md` antes de tocar código.
2. Escolha uma fase. Fases são independentes; podem ser feitas em paralelo por múltiplas LLMs desde que branches diferentes.
3. Cada fase tem `Definition of done` explícito no final. Não marque como completo sem cumprir cada bullet.
4. Cada fase produz N commits (não um único). Nomes de commit sugeridos ao final de cada fase.
5. Se encontrar comportamento inesperado no código real que diverge deste plano: **PARE** e reporte. Não invente fix. Discrepância é sinal de mudança post-audit.

**Ordem sugerida de fases** (mais segura):
```
Fase 0 (diagramas) ─┐
                    ├─ Fase 1 (instrumentation)
                    │      │
                    │      └─ Fase 2 (test harness)
                    │             │
                    │             └─ Fase 3 (GAP-01 resolver retry)
                    │                    │
                    │                    ├─ Fase 4 (curator no-runner)
                    │                    ├─ Fase 5 (mask postcondition)
                    │                    └─ Fase 6 (agents DOM-aware)
                    │
Fase 7 (bug detection) — independente, pode paralelizar com 3-6
Fase 8 (test reorg) — pode paralelizar com qualquer, mas melhor após Fase 2
Fase 9 (meds restantes) — última, depende de 1 (instrumentation completa)
```

**Como reportar progresso**: atualizar `.planning/healing-gaps-status.md` (criar se não existir) por fase com:
- Data de início/fim
- Commits produzidos
- Testes que passam / que ainda falham
- Bloqueios encontrados

---

## 3. Contexto crítico

TestForge é gravador self-healing de testes E2E. Fluxo:

```
Browser → raw_events.jsonl → steps.jsonl → SemanticTestCase → test_*.py
```

Healing 4-layer: L0 catalog (JSONL/SQLite) → L1 candidates + smart strategies → L2 specialist agents → L3 LLM. Ver `docs/ARCHITECTURE-V2.md`.

**Cliente-alvo**: times de QA em setores regulados. Testes gerados executam em CI/CD antes de deploy em produção. Falha silenciosa é vazamento de bug para produção.

**Contrato hard [[feedback-no-regrave]]**: NUNCA regravar rec existente para testar fix. Iterar `compile` + `run-incremental` sobre gravações existentes. Regressões viram teste automatizado em `tests/regression/`.

**Rec de regressão base** (usar em Definition of done de várias fases):
- `recordings/test-pos-hotfix27_2/` — Material calendar cascade — `assert_hit_rate` atual 50%
- `recordings/test-pos-hotfix22/` — SIOPI Caixa full flow — `assert_hit_rate` atual 64%
- `recordings/test-pos-hotfix26/` — EGI poder compra — `assert_hit_rate` atual 67%

---

## 4. Root cause diagnóstico

Todos os 17 gaps compartilham **2 antipatterns sistêmicos**:

**Antipattern A — Sinal fraco = decisão forte**
Camadas aceitam:
- Existência (`locator.count() > 0`) como confirmação de que ação executará.
- Keyword no error message (`"dialog" in error_lower`) como diagnóstico de família.
- Non-empty value (`bool(actual.strip())`) como confirmação de que fill foi correto.

Sem probe de estado real, sem verificação de attrs DOM, sem magnitude compare.

**Antipattern B — Falha silenciosa**
Padrões observados:
- `except Exception: pass` engolindo erro.
- `if not X: continue` sem log, sem counter.
- `default fallback` retornando valor neutro que engana caller.
- `logger.debug(...)` para erro que deveria ser INFO/WARNING.

Consequência: métricas verdes, regressão invisível.

**Consequência combinada**: cada camada individualmente "funciona"; end-to-end mente. Bug denominator já corrigido em `2eac52a` — padrão continua.

---

## 5. Padrão de testes obrigatório

Todos os testes desta iteração seguem `docs/TEST-PATTERNS.md`. Resumo do contrato:

- **Nomeação**: `test_<subject>_when_<condition>_then_<outcome>` em arquivo e função.
- **Diretório**: `tests/unit/`, `tests/integration/`, `tests/e2e/`, `tests/regression/`, `tests/contract/`.
- **AAA obrigatório**: comentários `# Arrange`, `# Act`, `# Assert` em toda função > 5 linhas.
- **Factories** em `tests/factories/` — nunca instância inline complexa.
- **Fixtures** por escopo — root → unit → integration → e2e.
- **Parametrize** com `ids=` explícito.
- **Marks obrigatórios**: `unit`, `integration`, `e2e`, `regression`, `critical`, `known_bug`.
- **Anti-padrões**: sem `time.sleep`, sem mocks profundos, sem `test_1`/`test_bug`, sem `try/except` engolindo assert.

Toda fase abaixo referencia `docs/TEST-PATTERNS.md` para detalhes. Não repetir contrato.

---

## 6. Diagramas — pares atual/alvo

Diagramas novos criados nesta iteração (referências durante implementação):

| Fase | Diagrama ATUAL (buggy) | Diagrama ALVO (fix) |
|------|------------------------|---------------------|
| 3 (GAP-01) | `docs/diagramas/sequencia-resolver-ATUAL.puml` | `docs/diagramas/sequencia-resolver-ALVO.puml` |
| 4 (GAP-02, 03) | `docs/diagramas/sequencia-curator-runner-ATUAL.puml` | `docs/diagramas/sequencia-curator-runner-ALVO.puml` |
| 7 (bug detection) | (n/a — feature nova) | `docs/diagramas/sequencia-bug-detection-recording-ALVO.puml` |

Diagramas afetados por edits menores (Fase 0):
- `sequencia-fluxo-completo-v2.puml` — nota ⚠ em `_exists`, retry chain após `locator.click()`, mover `record_success` para depois de execute.
- `fluxograma-pipeline-v2.puml` — decision diamond após execute.
- `sequencia-assert-flow.puml` — assinatura resolve com/sem action.
- `sequencia-handler-delegation.puml` — marcar PrimeFaces/ReactMUI como "skeleton not implemented".
- `sequencia-integracao-cmd-run.puml` — separar legacy cmd_run vs v2 pytest.
- `sequencia-data-driven.puml` — nota clarifica compile-time vs runtime fallback.

---

## 7. Fases

### FASE 0 — Sync diagramas (~1.5h)

**Objetivo**: eliminar diagramas que espelham bugs ou mostram comportamento aspiracional. LLMs futuras leem docs; não podemos deixar mentiras.

**Trabalho**:

**7.0.1 Diagramas já criados** (referenciar do plano, não recriar):
- `sequencia-resolver-ATUAL.puml`, `sequencia-resolver-ALVO.puml` — criados.
- `sequencia-curator-runner-ATUAL.puml`, `sequencia-curator-runner-ALVO.puml` — criados.
- `sequencia-bug-detection-recording-ALVO.puml` — criado.

**7.0.2 Edits em diagramas existentes**:

**A. `docs/diagramas/sequencia-fluxo-completo-v2.puml`**:
- Linha 96 (`STEP -> RES: resolve(intent, candidates, action)`): adicionar nota:
  ```
  note right of RES #FFF3CD
    ⚠ action é usado APENAS como cache key SQLite.
    Não drive de execução. Ver sequencia-resolver-ATUAL/ALVO.
  end note
  ```
- Linhas 107-112 (loop candidates com `Locator (or skip)`):
  - Mudar `DISP --> RES: Locator (or skip)` → `DISP --> RES: Locator IF count()>0`.
  - Adicionar nota `⚠ GAP-01: só existência, não execução. Ver Fase 3.`
- Linha 113 (`record_success` após loop): mover para dentro do bloco de execução (após `STEP -> STEP: locator.click() + wait`), com nota `só após execução real, Fase 3 fix`.
- Adicionar seta pós linha 123 (`STEP -> STEP: locator.click() + wait`):
  ```
  alt click/fill rejeita
    STEP -> RES: retry(exclude=[idx])  ' Fase 3 fix (GAP-01)
    RES --> STEP: next candidate
  end
  ```

**B. `docs/diagramas/fluxograma-pipeline-v2.puml`**:
- Após linha 94 (`locator.click() / fill() / select_option()`), adicionar decisão:
  ```
  if (execute OK?) then (yes)
    :promote candidate idx to cache;
  else (no)
    :add idx to exclude;
    ->_resolver.resolve(intent, candidates, exclude=...);
  endif
  ```
- Adicionar nota lateral referenciando Fase 3 fix.

**C. `docs/diagramas/sequencia-assert-flow.puml`**:
- Linha ~76 (`resolve(intent, candidates, action='assert')`):
  - Verificar assinatura real em `src/testforge/runtime/step.py`. Se assert_text não passa action='assert', mudar diagrama para `resolve(intent, candidates)` OU criar issue "step.py deve passar action='assert' para SQLite lookup segregado".
- Manter behavior atual documentado com nota.

**D. `docs/diagramas/sequencia-handler-delegation.puml`**:
- Linhas 68-72 (PrimeFaces / React MUI handlers): substituir texto por `(skeleton — Phase X not yet implemented)` + nota "handlers concretos aguardando Phase 8".
- Se DIAG-GAP #6 confirmar que ainda são stubs, adicionar `TODO: Phase 8 handler concretization`.

**E. `docs/diagramas/sequencia-integracao-cmd-run.puml`**:
- Adicionar box `== Legacy path (deprecated, ver [[project-run-legacy-decommission]]) ==` envolvendo linhas 51-56 e 68-112.
- Adicionar seção paralela `== V2 pytest path (recommended) ==` mostrando resolver direto → step.fill sem cure() central.

**F. `docs/diagramas/sequencia-data-driven.puml`**:
- Linha ~46 (`_data.get("cpf", "12345678900")`): adicionar nota lateral: `fallback hardcoded at compile-time (compiler.py), não runtime lookup`.

**7.0.3 Regeneração PNGs**:
```bash
cd docs/diagramas/
plantuml *.puml   # regenera todos os PNGs
git add *.png *.puml
```

**Testes**:
Não há testes de código para diagramas. Mas incluir em Definition of done:
- Cada diagrama editado abre sem erro em https://plantuml.com/plantuml.
- PNGs regenerados check no repo.
- README `docs/diagramas/README.md` atualizado com lista dos novos diagramas ATUAL/ALVO/bug-detection.

**Definition of done Fase 0**:
- [ ] 6 diagramas ATUAL/ALVO/bug-detection criados (já feito parcialmente pelo plano).
- [ ] 6 diagramas existentes editados conforme spec 7.0.2 A-F.
- [ ] PNGs regenerados via `plantuml *.puml`.
- [ ] README `docs/diagramas/README.md` atualizado.
- [ ] Commit `docs(diagramas): sync com estado atual e alvo pós-audit`.

**Commits sugeridos**:
1. `docs(diagramas): novos pares resolver/curator ATUAL vs ALVO`
2. `docs(diagramas): edits sequencia-fluxo-completo-v2 + fluxograma-pipeline-v2 refletindo GAP-01`
3. `docs(diagramas): sequencia-bug-detection-recording para Fase 7 feature nova`
4. `docs(diagramas): regenera PNGs após edits`

---

### FASE 1 — Instrumentation only (~2h)

**Objetivo**: tornar cegueira visível antes de corrigir. Não muda comportamento.

**Gaps cobertos**: 04, 05, 10, 11, 13, 14, 15, 17.

**Trabalho**:

**7.1.1 Adicionar contadores em `MetricsRepository`**:

Arquivo: `src/testforge/metrics/pilot_metrics.py` (ou onde MetricsRepository vive — grep `class MetricsRepository`).

Adicionar contadores:
```python
class MetricsRepository:
    def __init__(self):
        # ...existente...
        self._silent_skip_counters: dict[str, int] = defaultdict(int)

    def record_silent_skip(self, category: str):
        """Registra skip/continue que antes era silencioso.
        Categoria: 'overlay_detect', 'ir_dedupe_empty_key',
                   'ir_final_state_empty', 'click_no_candidates',
                   'snapshot_empty_batch', 'snapshot_exception',
                   'entry_label_empty', 'diagnostic_assess_error'.
        """
        self._silent_skip_counters[category] += 1

    def get_silent_skip_summary(self) -> dict[str, int]:
        return dict(self._silent_skip_counters)
```

**7.1.2 Instrumentar cada gap silencioso**:

Para cada gap abaixo, mudança é: adicionar 1 linha `logger.info(...)` + 1 linha `metrics.record_silent_skip("...")` no ponto do skip/continue/except.

**GAP-04** (`overlay_inject.js:1869` — buscar por `setInterval.*snapshotFields`):
```javascript
// Antes:
try { _tf_snapshotFields(); } catch (_e) { }
// Depois:
try {
  _tf_snapshotFields();
} catch (_e) {
  window.__tfSnapshotErrors = (window.__tfSnapshotErrors || 0) + 1;
  window.__tfPendingSnapshotErrors = window.__tfPendingSnapshotErrors || [];
  window.__tfPendingSnapshotErrors.push({
    timestamp: new Date().toISOString(),
    error: _e.message,
    stack: _e.stack ? _e.stack.substring(0, 500) : ''
  });
  if (console.debug) console.debug('tf snapshot error:', _e);
}
```

Em `src/testforge/recorder/recorder_controller.py` — quando `flush_events()` roda, ler `__tfPendingSnapshotErrors` via `page.evaluate("() => window.__tfPendingSnapshotErrors")` e emitir no telemetry + increment `metrics.record_silent_skip("snapshot_exception")`.

**GAP-05** (`overlay_inject.js:510-533` — função `_snapshotFields`):
```javascript
function _snapshotFields() {
  var snapshots = [];
  document.querySelectorAll('input, textarea, select').forEach(function(el) {
    // ...existente...
  });
  document.querySelectorAll('[contenteditable="true"]').forEach(function(el) {
    // ...existente...
  });
  // NOVO: se DOM não tem elementos editáveis, emite marker
  if (snapshots.length === 0) {
    snapshots.push({
      timestamp: new Date().toISOString(),
      dom_state: 'no_editable_elements',
      visibility_unknown: true,
      url: window.location.href
    });
  }
  return snapshots;
}
```

**GAP-10** (`semantic/recording_normalizer.py:2243`):
```python
# Antes:
if not step.target or not step.target.candidates:
    continue
# Depois:
if not step.target or not step.target.candidates:
    logger.info(
        "overlay detect skip",
        extra={
            "step_idx": idx,
            "target_ident": self._target_identifier_summary(step.target) if step.target else None,
            "action": step.action,
        },
    )
    self._metrics.record_silent_skip("overlay_detect")
    continue
```

**GAP-11** (`semantic/recording_normalizer.py:3096-3097`):
```python
dropped = []
for entry in entries:
    key = entry.get("key")
    value = entry.get("value")
    if not key:
        dropped.append({"reason": "empty_key", "entry": entry, "source": entry.get("source")})
        self._metrics.record_silent_skip("ir_dedupe_empty_key")
        continue
    if not value:
        dropped.append({"reason": "empty_value", "entry": entry, "source": entry.get("source")})
        self._metrics.record_silent_skip("ir_dedupe_empty_value")
        continue
    # ...
if dropped:
    logger.info(
        "IR dedupe dropped %d entries",
        len(dropped),
        extra={"dropped_summary": Counter(d["reason"] for d in dropped)},
    )
    self._dropped_ir_entries = dropped  # p/ reportar em summary
```

**GAP-13** (`semantic/recording_normalizer.py:804`):
```python
entry_label = (identifiers.get("label") or value or "").strip().lower()
if not entry_label:
    logger.info("entry_label vazio, marcando unanchored",
                extra={"entry_source": entry.get("source"), "step_idx": step_idx})
    self._metrics.record_silent_skip("entry_label_empty")
    entry["unanchored"] = True
```

**GAP-14** (`semantic/recording_normalizer.py:2941`):
```python
for field_key, value in final_state.items():
    if value is None:
        # separar: não tinha na DOM
        self._metrics.record_silent_skip("ir_final_state_field_missing")
        logger.debug("final_state field missing: %s", field_key)
        continue
    if value == "" or (isinstance(value, str) and not value.strip()):
        # separar: estava mas vazio
        self._metrics.record_silent_skip("ir_final_state_field_empty_at_end")
        logger.info("final_state field empty at end: %s", field_key)
        continue
```

**GAP-15** (`recorder/recorder_controller.py:418-419`):
```python
# Antes:
except Exception as exc:
    logger.debug("Diagnostic assess failed: %s", exc)
# Depois:
except Exception as exc:
    logger.info("Diagnostic assess failed, emitting synthetic entry", exc_info=exc)
    self._metrics.record_silent_skip("diagnostic_assess_error")
    if self._telemetry_store:
        self._telemetry_store.emit({
            "type": "diagnostic_assess_error",
            "timestamp": self._now_iso(),
            "status": "unknown",
            "error": str(exc),
        })
```

**GAP-17** (`semantic/recording_normalizer.py:1535-1536`):
```python
if event_type == "click" and not target.candidates:
    logger.info(
        "click event dropped, no candidates identified",
        extra={"raw_event_ts": event.get("timestamp"),
               "target_summary": self._raw_target_summary(event)},
    )
    self._metrics.record_silent_skip("click_no_candidates")
    self._blind_spots.append({
        "type": "click_no_candidates",
        "raw_event": event,
    })
    return None
```

**7.1.3 Reportar summary no CLI**:

Em `src/testforge/cli/app.py`, no final de `testforge compile` e `testforge run-incremental`, após execução:
```python
silent_skips = metrics.get_silent_skip_summary()
if silent_skips:
    print("\n[TestForge] Silent skips summary:")
    for category, count in sorted(silent_skips.items(), key=lambda x: -x[1]):
        print(f"  {category}: {count}")
    print(f"  Total: {sum(silent_skips.values())}")
```

**Testes obrigatórios** (padrão `docs/TEST-PATTERNS.md`):

Estrutura:
```
tests/unit/metrics/
  test_silent_skip_counter_when_recorded_then_increments.py
tests/unit/semantic/
  test_normalizer_when_overlay_detect_skip_then_logs_and_counts.py
  test_normalizer_when_ir_dedupe_empty_key_then_logs_dropped.py
  test_normalizer_when_click_lacks_candidates_then_records_blind_spot.py
tests/unit/recorder/
  test_overlay_snapshot_when_dom_has_no_editable_then_emits_marker.py
  test_overlay_snapshot_when_function_throws_then_pushes_error_queue.py
tests/contract/
  test_metrics_repository_silent_skip_categories_are_documented.py
```

Exemplo (padrão AAA + factory + parametrize):
```python
# tests/unit/semantic/test_normalizer_when_overlay_detect_skip_then_logs_and_counts.py
import logging
import pytest
from testforge.semantic.recording_normalizer import RecordingNormalizer
from tests.factories.semantic_action import make_semantic_action
from tests.helpers.mock_metrics import MockMetricsRepository


@pytest.mark.unit
@pytest.mark.regression
class TestNormalizerOverlayDetectSkip:
    def test_when_step_target_has_no_candidates_then_logs_info_and_counts(
        self, caplog
    ):
        # Arrange
        caplog.set_level(logging.INFO)
        metrics = MockMetricsRepository()
        normalizer = RecordingNormalizer(metrics=metrics)
        step_without_candidates = make_semantic_action(
            action="click",
            target_candidates=[],  # simula overlay não detectado
        )

        # Act
        normalizer._process_overlay_detection([step_without_candidates])

        # Assert
        assert "overlay detect skip" in caplog.text
        assert metrics.get_silent_skip_count("overlay_detect") == 1
```

**Definition of done Fase 1**:
- [ ] `MetricsRepository.record_silent_skip` + `get_silent_skip_summary` implementados com testes unit.
- [ ] 8 gaps instrumentados (04, 05, 10, 11, 13, 14, 15, 17) — cada um com log INFO + counter.
- [ ] Summary de silent_skips exibido ao final de `testforge compile` e `testforge run-incremental`.
- [ ] 7+ testes unit criados em `tests/unit/*` seguindo `docs/TEST-PATTERNS.md`.
- [ ] Rodar `pytest -m unit` — todos passam.
- [ ] Rodar `testforge compile recordings/test-pos-hotfix27_2` — summary exibe contadores > 0.
- [ ] Salvar summary em `.planning/healing-gaps-baseline.md` (comparação pós-fix).

**Commits sugeridos**:
1. `feat(metrics): silent_skip_counter em MetricsRepository`
2. `chore(observability): instrumenta GAP-04+05 overlay snapshot exceptions/empty`
3. `chore(observability): instrumenta GAP-10 overlay detect skip`
4. `chore(observability): instrumenta GAP-11 IR dedupe dropped entries`
5. `chore(observability): instrumenta GAP-13+14+17 normalizer silent skips`
6. `chore(observability): instrumenta GAP-15 diagnostic assess error`
7. `feat(cli): exibe silent_skip summary após compile e run-incremental`

---

### FASE 2 — Test harness integração + regressão (~2h)

**Objetivo**: criar suite que **força** o cenário "existe mas ação rejeita" antes de fixar. Sem esse harness, fixes cegos.

**Trabalho**:

**7.2.1 Setup estrutural**:
- Criar diretórios `tests/regression/resolver/`, `tests/regression/curator/`, `tests/integration/pipeline/`, `tests/e2e/pages/`.
- Criar `tests/factories/__init__.py`, `tests/factories/locator_candidate.py`, `tests/factories/semantic_action.py`, `tests/factories/curator_outcome.py`, `tests/factories/raw_event.py`.
- Criar `tests/helpers/mock_page.py` com `MockPageBuilder` (fluent API para montar page com candidates em estados variados).
- Criar `tests/helpers/mock_metrics.py`.
- Criar `tests/conftest.py` root (se não existir) com fixtures `tmp_recording_dir`, `sample_semantic_test_case`.

**7.2.2 MockPageBuilder** (`tests/helpers/mock_page.py`):
```python
from dataclasses import dataclass, field
from enum import Enum
from unittest.mock import MagicMock


class CandidateState(Enum):
    EXISTS_AND_ACCEPTS = "exists_ok"
    EXISTS_BUT_REJECTS_FILL = "exists_reject_fill"
    EXISTS_BUT_REJECTS_CLICK = "exists_reject_click"
    EXISTS_BUT_INTERCEPTED = "exists_intercepted"
    NOT_EXISTS = "absent"


@dataclass
class MockPageBuilder:
    """Fluent builder para MagicMock de playwright.sync_api.Page com candidates
    em estados controlados. Cada candidate mapeia strategy → locator mock com
    behavior específico. Uso:

        page = (MockPageBuilder()
            .with_candidate("role", CandidateState.EXISTS_BUT_REJECTS_FILL)
            .with_candidate("label", CandidateState.EXISTS_AND_ACCEPTS)
            .build())
    """
    _candidates: dict = field(default_factory=dict)

    def with_candidate(self, strategy: str, state: CandidateState) -> "MockPageBuilder":
        self._candidates[strategy] = state
        return self

    def build(self) -> MagicMock:
        page = MagicMock()
        strategies_map = {
            "role": "get_by_role",
            "label": "get_by_label",
            "placeholder": "get_by_placeholder",
            "test_id": "get_by_test_id",
            "text": "get_by_text",
        }
        for strategy, state in self._candidates.items():
            locator = self._make_locator(state)
            method = strategies_map.get(strategy, "locator")
            setattr(page, method, MagicMock(return_value=locator))
        return page

    def _make_locator(self, state: CandidateState) -> MagicMock:
        locator = MagicMock()
        if state == CandidateState.NOT_EXISTS:
            locator.count.return_value = 0
        else:
            locator.count.return_value = 1
        if state == CandidateState.EXISTS_BUT_REJECTS_FILL:
            from playwright.sync_api import TimeoutError
            locator.fill.side_effect = TimeoutError("fill timeout — mock")
        elif state == CandidateState.EXISTS_BUT_REJECTS_CLICK:
            from playwright.sync_api import Error as PWError
            locator.click.side_effect = PWError("element is not clickable")
        elif state == CandidateState.EXISTS_BUT_INTERCEPTED:
            from playwright.sync_api import Error as PWError
            locator.click.side_effect = PWError("element intercepts pointer events")
        return locator
```

**7.2.3 Regressão GAP-01** (falha pré-fix, passa pós-fix):
```python
# tests/regression/resolver/test_gap01_first_candidate_exists_but_fill_fails.py

import pytest
from testforge.runtime import LocatorResolver
from tests.factories.locator_candidate import make_candidate
from tests.helpers.mock_page import MockPageBuilder, CandidateState


@pytest.mark.regression
@pytest.mark.critical
class TestGap01ResolverRetryChain:
    """GAP-01: pré-fix, resolver retorna primeiro candidate que EXISTE mesmo
    quando fill/click rejeita. Executor escala direto para healing, perdendo
    candidates 1..N que teriam funcionado.

    Bug histórico: SIOPI 15b-e, hotfix22 — assert_hit_rate 14-64%.
    """

    def test_when_first_candidate_fill_raises_then_executor_tries_next(self):
        # Arrange
        page = (MockPageBuilder()
                .with_candidate("role", CandidateState.EXISTS_BUT_REJECTS_FILL)
                .with_candidate("label", CandidateState.EXISTS_AND_ACCEPTS)
                .build())
        resolver = LocatorResolver(page)
        candidates = [
            make_candidate(strategy="role", score=0.9,
                           playwright_call='get_by_role("textbox", name="Renda")'),
            make_candidate(strategy="label", score=0.85,
                           playwright_call='get_by_label("Renda")'),
        ]
        from testforge.runner.step_executor import StepExecutor
        executor = StepExecutor(resolver)

        # Act
        result = executor.fill(
            intent="Renda mensal",
            candidates=candidates,
            value="R$ 1.000,00",
        )

        # Assert
        assert result.status == "passed", (
            "Pré-fix: resolver retornava candidate[0] que existe, executor "
            "chamava fill que raise TimeoutError, escalava para healing. "
            "Fase 3 fix: retry candidate[1] antes de escalar."
        )
        assert result.winning_candidate_idx == 1
        assert result.attempted_indices == [0, 1]
        # cache promove candidate vencedor
        assert resolver._winning_idx_cache["Renda mensal"] == 1
```

**7.2.4 Testes adicionais harness** (esqueleto):

```python
# tests/regression/resolver/test_gap01_all_candidates_fail_escalates_healing.py
# tests/regression/resolver/test_gap01_cache_invalidates_on_url_change.py
# tests/regression/curator/test_gap02_l0_no_runner_falls_through.py
# tests/regression/curator/test_gap03_l2_no_runner_falls_through.py
# tests/integration/pipeline/test_resolve_execute_retry_full_flow.py
# tests/integration/pipeline/test_normalize_compile_execute_pipeline.py
```

**7.2.5 Fixture HTML e2e** (`tests/e2e/pages/material_hidden_after_render.html`):
```html
<!DOCTYPE html>
<html>
<head>
  <title>Material hidden input regression</title>
  <style>
    input[hidden-until-click] { display: none; }
  </style>
</head>
<body>
  <label for="renda">Renda mensal</label>
  <input id="renda" name="renda" hidden-until-click type="text" />
  <script>
    document.querySelector('label').addEventListener('click', () => {
      document.querySelector('input').removeAttribute('hidden-until-click');
    });
  </script>
</body>
</html>
```

**Definition of done Fase 2**:
- [ ] Estrutura `tests/factories/`, `tests/helpers/`, `tests/regression/`, `tests/integration/`, `tests/e2e/pages/` criada.
- [ ] `MockPageBuilder` + `CandidateState` enum implementados com self-tests.
- [ ] Factories `make_candidate`, `make_semantic_action`, `make_curation_outcome`, `make_raw_event` implementados.
- [ ] Teste `test_gap01_first_candidate_exists_but_fill_fails.py` FALHA contra `main` atual (comportamento GAP-01 confirmado).
- [ ] Fixtures HTML criados em `tests/e2e/pages/`.
- [ ] `pytest tests/regression/ -v -m regression` roda (com xfail marks apropriados p/ testes que ainda falham).

**Commits sugeridos**:
1. `test: cria estrutura tests/{unit,integration,e2e,regression,contract,factories,helpers}`
2. `test(helpers): MockPageBuilder com CandidateState enum`
3. `test(factories): make_candidate/semantic_action/curator_outcome/raw_event`
4. `test(regression): GAP-01 harness — first candidate fill fails`
5. `test(regression): GAP-01 harness — all candidates fail escalates`
6. `test(regression): GAP-02/03 curator no-runner falls through`
7. `test(integration): resolve-execute-retry pipeline flow`
8. `test(e2e): fixture material_hidden_after_render.html`

---

### FASE 3 — GAP-01 fix retry + cache (~2h)

**Objetivo**: resolver a cascata principal — quando fill/click falha, tentar próximo candidate antes de escalar.

**Escolha**: Opção B (retry-with-next-candidate no executor) + cache in-memory. Opção A (action-aware resolve) fica para v3.

**Trabalho**:

**7.3.1 Estender `LocatorResolver.resolve()` com `exclude_indices`**:

Arquivo: `src/testforge/runtime/resolver.py`.

```python
def resolve(
    self,
    intent: str,
    candidates: list[dict],
    action: str = "click",
    exclude_indices: set[int] | None = None,
) -> ResolveResult:
    """Tenta cache L0 (memoria depois SQLite), depois candidatos em ordem.

    exclude_indices: candidatos previamente falhos em execução — pulados
    tanto no cache L0a (invalidando cache se aponta para excluded) quanto
    no walk L1.
    """
    exclude_indices = exclude_indices or set()
    # ... resto da lógica
```

Modificações internas em `_resolve_impl`:
- L0a: se `self._cache.get(intent)` aponta para candidate com idx em `exclude_indices`, invalidar cache e continuar.
- L1 walk: `for idx, c in enumerate(candidates): if idx in exclude_indices: continue`.
- Adicionar `winning_idx_cache: dict[str, int]` no `__init__`. Populado em success.

**7.3.2 Criar `StepExecutor` wrapper** (novo):

Arquivo: `src/testforge/runner/step_executor.py` (existe? verificar — se sim, estender; senão criar).

```python
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional
import logging

from playwright.sync_api import Page, TimeoutError, Error as PWError
from ..runtime.resolver import LocatorResolver
from ..runtime.errors import LocatorNotFoundError

logger = logging.getLogger(__name__)


class StepResultStatus(Enum):
    PASSED = "passed"
    FAILED = "failed"
    UNRESOLVED = "unresolved"


@dataclass
class StepResult:
    status: StepResultStatus
    winning_candidate_idx: Optional[int] = None
    attempted_indices: list[int] = field(default_factory=list)
    error: Optional[str] = None


class StepExecutor:
    """Wrapper que resolve + executa + retry-with-next-candidate em caso de
    action failure. Cache promove candidate vencedor para próximas resoluções
    do mesmo intent.
    """

    RETRYABLE_ERRORS = (TimeoutError, PWError)

    def __init__(self, resolver: LocatorResolver, max_retries: int = 5):
        self._resolver = resolver
        self._max_retries = max_retries

    def fill(self, intent: str, candidates: list[dict], value: str,
             timeout: int = 1500) -> StepResult:
        return self._execute(
            intent, candidates, action="fill",
            action_fn=lambda locator: locator.fill(value, timeout=timeout),
        )

    def click(self, intent: str, candidates: list[dict],
              timeout: int = 1500) -> StepResult:
        return self._execute(
            intent, candidates, action="click",
            action_fn=lambda locator: locator.click(timeout=timeout),
        )

    def _execute(self, intent: str, candidates: list[dict], action: str,
                 action_fn) -> StepResult:
        exclude: set[int] = set()
        attempted: list[int] = []
        last_error: Optional[str] = None

        for attempt in range(self._max_retries):
            try:
                result = self._resolver.resolve(
                    intent, candidates, action=action, exclude_indices=exclude,
                )
            except LocatorNotFoundError as exc:
                return StepResult(
                    status=StepResultStatus.UNRESOLVED,
                    attempted_indices=attempted,
                    error=str(exc),
                )

            idx = result.candidate_index or 0
            attempted.append(idx)
            try:
                action_fn(result.locator)
                # SUCCESS — promove no cache
                self._resolver.promote_winning_candidate(intent, idx)
                return StepResult(
                    status=StepResultStatus.PASSED,
                    winning_candidate_idx=idx,
                    attempted_indices=attempted,
                )
            except self.RETRYABLE_ERRORS as exc:
                last_error = str(exc)
                logger.info(
                    "action failed on candidate idx=%d, retrying next",
                    idx, extra={"intent": intent, "action": action, "error": last_error},
                )
                exclude.add(idx)
                continue

        return StepResult(
            status=StepResultStatus.FAILED,
            attempted_indices=attempted,
            error=last_error,
        )
```

Adicionar em `LocatorResolver`:
```python
def promote_winning_candidate(self, intent: str, idx: int) -> None:
    self._winning_idx_cache[intent] = idx
```

**7.3.3 Integrar em `runtime/step.py`**:

Localizar `step.fill()`, `step.click()`, `step.assert_text()`. Substituir chamada direta a `resolver.resolve()` + `locator.fill()` por `StepExecutor.fill()`.

Backward compat: se caller ainda passar candidatos inline e não `StepExecutor`, manter comportamento legacy até refactor completo. Deprecation warning em `logger.warning`.

**7.3.4 Testes**:

Tests já criados em Fase 2 (`test_gap01_*.py`) devem passar.

Novos testes específicos:
```python
# tests/unit/runtime/test_resolver_when_exclude_indices_then_skips.py
# tests/unit/runtime/test_resolver_promote_winning_candidate.py
# tests/unit/runner/test_step_executor_when_action_raises_then_retries.py
# tests/unit/runner/test_step_executor_when_all_candidates_fail_then_unresolved.py
# tests/unit/runner/test_step_executor_cache_promotes_winning_idx.py
# tests/integration/pipeline/test_resolve_execute_retry_end_to_end.py
```

**Definition of done Fase 3**:
- [ ] `LocatorResolver.resolve()` aceita `exclude_indices: set[int] | None = None` — backward compat preservado.
- [ ] `LocatorResolver.promote_winning_candidate(intent, idx)` implementado.
- [ ] `_winning_idx_cache: dict[str, int]` populado em success.
- [ ] `StepExecutor` classe implementada com retry chain.
- [ ] `runtime/step.py` usa `StepExecutor`; código legacy tem deprecation warning.
- [ ] `tests/regression/resolver/test_gap01_first_candidate_exists_but_fill_fails.py` PASSA.
- [ ] `pytest -m "unit or regression" -v` — todos passam.
- [ ] Rodar `testforge run-incremental semantic_tests/ST-test-pos-hotfix27_2/` — `assert_hit_rate ≥ 80%` (era 50%).
- [ ] Rodar `testforge run-incremental semantic_tests/ST-test-pos-hotfix22/` — `assert_hit_rate ≥ 90%` (era 64%).

**Commits sugeridos**:
1. `feat(resolver): exclude_indices param + winning_idx_cache`
2. `feat(runner): StepExecutor com retry-with-next-candidate`
3. `refactor(runtime/step): usa StepExecutor com deprecation legacy`
4. `test(unit): cobertura resolver.exclude_indices e promote_winning`
5. `test(integration): pipeline resolve-execute-retry end-to-end`

---

### FASE 4 — Curator no-runner morre (~1.5h)

**Objetivo**: eliminar `PASSED_STEP` fake quando runner ausente.

**Gaps cobertos**: GAP-02, GAP-03.

**Trabalho**:

**7.4.1 Adicionar novo status `DEGRADED`**:

Arquivo: `src/testforge/models/pipeline.py` (ou onde ProgressResult enum vive):
```python
class ProgressResult(Enum):
    PASSED_STEP = "passed_step"
    UNRESOLVED = "unresolved"
    DEGRADED = "degraded"  # NOVO: cura possível mas não validada por execução
```

**7.4.2 Alterar Curator**:

Arquivo: `src/testforge/healing/curator.py`.

Antes (linhas 235-244):
```python
if not self._step_runner:
    self._catalog.record_usage(best.recipe_id)
    return CurationOutcome(
        status=ProgressResult.PASSED_STEP,
        entry_id=best.recipe_id,
        layer_used="L0",
        family=family,
        proposal=_proposal_from_recipe(),
    )
```

Depois:
```python
if not self._step_runner:
    logger.warning(
        "curator L0 hit but no step_runner — degrading (não fake-PASSED)",
        extra={"recipe_id": best.recipe_id, "family": family},
    )
    self._metrics.record("curator.no_runner_degrade_L0")
    return CurationOutcome(
        status=ProgressResult.DEGRADED,
        entry_id=best.recipe_id,
        layer_used="L0",
        family=family,
        proposal=_proposal_from_recipe(),
        reason="no_step_runner",
    )
```

Idêntico para linhas 333-342 (L2):
```python
if not self._step_runner:
    logger.warning(
        "curator L2 agent proposal but no step_runner — degrading",
        extra={"agent_family": family, "confidence": proposal.confidence},
    )
    self._metrics.record("curator.no_runner_degrade_L2")
    return CurationOutcome(
        status=ProgressResult.DEGRADED,
        proposal=proposal,
        evidence=evidence,
        layer_used="L2",
        family=family,
        taxonomy_id=proposal.taxonomy_id,
        reason="no_step_runner",
    )
```

**7.4.3 Atualizar callers**:

Grep `PASSED_STEP` em `src/testforge/` — cada caller precisa decidir como tratar `DEGRADED`:
- Runner CI/gate: tratar como falha (não considerar step curado sem validação).
- Shadow mode dashboard: mostrar contagem separada `degraded_no_runner`.

**7.4.4 Testes**:

```python
# tests/unit/healing/test_curator_l0_when_runner_missing_then_falls_through.py

@pytest.mark.unit
@pytest.mark.regression
class TestCuratorL0NoRunnerDegrades:
    def test_when_step_runner_is_none_then_returns_degraded_not_passed(self):
        # Arrange
        catalog = MockHealingCatalog(returns_recipe_for=("SEL-001",))
        curator = Curator(catalog=catalog, step_runner=None)
        step_data = make_step_data(taxonomy_id="SEL-001")

        # Act
        outcome = curator.cure(step_data, error="element not found",
                               evidence=make_evidence_payload())

        # Assert
        assert outcome.status == ProgressResult.DEGRADED
        assert outcome.layer_used == "L0"
        assert outcome.reason == "no_step_runner"

    def test_when_step_runner_is_none_then_logs_warning_and_counts_metric(
        self, caplog
    ):
        # Arrange
        caplog.set_level("WARNING")
        curator = Curator(catalog=MockHealingCatalog(), step_runner=None,
                          metrics=MockMetricsRepository())

        # Act
        curator.cure(make_step_data(), error="...", evidence=make_evidence_payload())

        # Assert
        assert "curator L0 hit but no step_runner" in caplog.text
        assert curator._metrics.get_count("curator.no_runner_degrade_L0") == 1
```

Similar para L2:
```python
# tests/unit/healing/test_curator_l2_when_runner_missing_then_falls_through.py
```

Integração:
```python
# tests/integration/pipeline/test_shadow_mode_returns_degraded_not_passed.py
```

**Definition of done Fase 4**:
- [ ] `ProgressResult.DEGRADED` adicionado ao enum.
- [ ] Curator L0 e L2 no-runner path retorna `DEGRADED` com log WARNING + counter.
- [ ] Callers que tratavam `PASSED_STEP` atualizados para distinguir `DEGRADED`.
- [ ] Testes unit + integration passam.
- [ ] Shadow mode dashboard reflete `degraded_count` separado.
- [ ] Documentar breaking change em `docs/ARCHITECTURE-V2.md` seção Healing.

**Commits sugeridos**:
1. `feat(healing): ProgressResult.DEGRADED para no-runner path`
2. `fix(curator): L0 no-runner retorna DEGRADED em vez de PASSED_STEP fake`
3. `fix(curator): L2 no-runner retorna DEGRADED em vez de PASSED_STEP fake`
4. `test(unit): curator no-runner degradation em L0 e L2`
5. `docs: seção Healing atualizada com DEGRADED status`

---

### FASE 5 — Mask postcondition correto (~1.5h)

**Objetivo**: `expected=1000, actual='R$ 1,00'` deve REJEITAR.

**Gap coberto**: GAP-08.

**Trabalho**:

**7.5.1 Alterar `step_postcondition.py:112-119`**:

```python
if is_masked:
    # Detecta subfamilia da mask
    if self._looks_like_currency(actual) or self._looks_like_currency(expected):
        stripped_expected = self._strip_currency(expected)
        stripped_actual = self._strip_currency(actual)
        if stripped_expected and stripped_actual:
            magnitude_match = self._magnitude_close(stripped_expected, stripped_actual)
            return PostconditionResult(
                passed=magnitude_match,
                checks={"mask_currency_magnitude": magnitude_match,
                        "actual_value_present": bool(actual)},
                failures=[] if magnitude_match else ["currency_magnitude_mismatch"],
                message=f"[currency] esperado={stripped_expected} obtido={stripped_actual}",
            )
    if self._looks_like_date(actual) or self._looks_like_date(expected):
        norm_expected = self._normalize_date(expected)
        norm_actual = self._normalize_date(actual)
        if norm_expected and norm_actual:
            date_match = (norm_expected == norm_actual)
            return PostconditionResult(
                passed=date_match,
                checks={"mask_date_match": date_match},
                failures=[] if date_match else ["date_mismatch"],
                message=f"[date] esperado={norm_expected} obtido={norm_actual}",
            )
    # Fallback: non-empty, mas com warning
    non_empty = bool((actual or "").strip())
    logger.warning(
        "mask postcondition soft-pass (non-empty only)",
        extra={"expected": expected[:80], "actual": actual[:80]},
    )
    self._metrics.record("postcondition.mask_soft_pass")
    return PostconditionResult(
        passed=non_empty,
        checks={"mask_input_non_empty": non_empty},
        failures=[] if non_empty else ["mask_input_empty"],
        message=f"[mask soft] esperado='{expected}' obtido='{actual}'",
    )
```

**7.5.2 Helpers novos**:

```python
def _looks_like_currency(self, v: str) -> bool:
    if not v: return False
    return bool(re.match(r'^\s*(R\$|US\$|\$|€)\s*[\d.,]+', v)) \
        or bool(re.match(r'^\s*[\d]{1,3}(\.\d{3})*,\d{2}\s*$', v))

def _looks_like_date(self, v: str) -> bool:
    if not v: return False
    return bool(re.match(r'^\s*\d{1,2}[-/]\d{1,2}[-/]\d{2,4}\s*$', v)) \
        or bool(re.match(r'^\s*\d{4}-\d{1,2}-\d{1,2}\s*$', v))

def _magnitude_close(self, a: str, b: str, tolerance: float = 0.01) -> bool:
    try:
        fa, fb = float(a), float(b)
        if fa == 0 and fb == 0: return True
        return abs(fa - fb) / max(abs(fa), abs(fb)) < tolerance
    except ValueError:
        return False

def _normalize_date(self, v: str) -> str:
    """Converte para ISO YYYY-MM-DD ou retorna string vazia."""
    if not v: return ""
    # DD/MM/YYYY ou DD-MM-YYYY
    m = re.match(r'^\s*(\d{1,2})[-/](\d{1,2})[-/](\d{2,4})\s*$', v)
    if m:
        d, mo, y = m.groups()
        if len(y) == 2: y = "19" + y if int(y) > 30 else "20" + y  # heurística
        return f"{y}-{int(mo):02d}-{int(d):02d}"
    # YYYY-MM-DD
    m = re.match(r'^\s*(\d{4})-(\d{1,2})-(\d{1,2})\s*$', v)
    if m:
        y, mo, d = m.groups()
        return f"{y}-{int(mo):02d}-{int(d):02d}"
    return ""
```

**7.5.3 Testes**:

Parametrize amplo:
```python
# tests/unit/runner/test_step_postcondition_when_mask_currency_then_compares_magnitude.py

@pytest.mark.unit
@pytest.mark.parametrize(
    "expected,actual,should_pass",
    [
        ("1000", "R$ 1.000,00", True),   # magnitude match
        ("1000", "R$ 1,00", False),      # magnitude 1000x menor — REJEITA (era PASS antes)
        ("1000", "R$ 999,50", True),    # dentro da tolerância 1%
        ("1000", "R$ 950,00", False),   # 5% fora
        ("1000", "", False),
        ("R$ 1.000,00", "R$ 1.000,00", True),
    ],
    ids=[
        "brl_thousand_match",
        "gap08_regression_thousand_mistyped_as_one",
        "brl_within_tolerance",
        "brl_outside_tolerance",
        "empty_rejects",
        "brl_format_identity",
    ],
)
def test_when_masked_currency_then_compares_magnitude(expected, actual, should_pass):
    # Arrange
    post = StepPostcondition(metrics=MockMetricsRepository())
    # Act
    result = post.evaluate_fill(expected=expected, actual=actual, is_masked=True)
    # Assert
    assert result.passed == should_pass
```

E similar para date:
```python
# tests/unit/runner/test_step_postcondition_when_mask_date_then_normalizes_iso.py
```

**Definition of done Fase 5**:
- [ ] Helpers `_looks_like_currency`, `_looks_like_date`, `_magnitude_close`, `_normalize_date` implementados.
- [ ] `if is_masked` branch usa magnitude/normalização antes de non-empty soft.
- [ ] Fallback non-empty registra `postcondition.mask_soft_pass` counter + WARNING.
- [ ] Parametrize test cobre 6+ casos moeda + 6+ casos data.
- [ ] Rec test-pos-hotfix22 rerun mostra REJ em fills mal-preenchidos (não mais PASS silencioso).

**Commits sugeridos**:
1. `fix(postcondition): magnitude compare para currency masks`
2. `fix(postcondition): normaliza date para ISO antes de comparar`
3. `feat(metrics): counter postcondition.mask_soft_pass para fallback`
4. `test(unit): parametrize cobertura mask currency e date`

---

### FASE 6 — Agents DOM-aware (~3h)

**Objetivo**: confidence alta requer evidência real, não keyword-match.

**Gaps cobertos**: GAP-06 (StateAgent), GAP-07 (InputAgent).

**Trabalho**:

**7.6.1 Helpers de introspeção DOM em `evidence.py`**:

```python
# src/testforge/healing/agents/dom_introspection.py (novo)
def dom_has_role(payload, role: str) -> bool:
    """True se dom_snapshot menciona role=X visível."""
    snap = payload.get("dom_snapshot", "")
    if not snap: return False
    return f'role="{role}"' in snap.lower() or f"role='{role}'" in snap.lower()

def dom_has_mask_attrs(payload) -> bool:
    """True se dom_snapshot menciona attrs típicos de input com mask."""
    snap = (payload.get("dom_snapshot") or "").lower()
    for attr in ("currencymask", "imask", "data-mask", "ng-currency",
                 "mat-input-mask", "cleavezone"):
        if attr in snap: return True
    return False

def dom_has_dialog_handler(payload) -> bool:
    """True se page tinha dialog handler registrado (via page.on)."""
    return bool(payload.get("page_state", {}).get("has_dialog_handler"))
```

**7.6.2 StateAgent (GAP-06)**:

Arquivo: `src/testforge/healing/agents/state_agent.py`.

Antes da linha ~40 (proposal criada):
```python
proposal_confidence = 0.85  # existente
# NOVO: validação DOM/context
if not (dom_has_dialog_handler(evidence.payload) or dom_has_role(evidence.payload, "dialog")):
    logger.info(
        "state_agent dialog proposal downgraded — no dom evidence",
        extra={"error": error_message[:200]},
    )
    proposal_confidence = 0.4  # abaixo do threshold em curator.py:325
```

**7.6.3 InputAgent (GAP-07)**:

Arquivo: `src/testforge/healing/agents/input_agent.py`.

```python
proposal_confidence = 0.82  # existente
if not dom_has_mask_attrs(evidence.payload):
    logger.info(
        "input_agent mask proposal downgraded — no mask attrs in dom",
        extra={"error": error_message[:200]},
    )
    proposal_confidence = 0.35
```

**7.6.4 Alterar `EvidencePayload`** (se necessário):

Verificar se `page_state.has_dialog_handler` existe. Se não, adicionar em `evidence.py` — deve ser populado em `recorder_controller` quando `page.on("dialog", ...)` é registrado.

**7.6.5 Testes**:

```python
# tests/unit/healing/test_state_agent_when_dom_lacks_dialog_then_returns_none.py
# tests/unit/healing/test_state_agent_when_dom_has_dialog_role_then_returns_proposal.py
# tests/unit/healing/test_input_agent_when_dom_lacks_mask_attrs_then_returns_none.py
# tests/unit/healing/test_input_agent_when_dom_has_currencymask_then_returns_proposal.py
```

Parametrize adversarial:
```python
@pytest.mark.parametrize(
    "error_msg,dom_snapshot,expected_none",
    [
        ("dialog blocked", "", True),               # "dialog" no error mas DOM sem
        ("dialog is open", '<div role="dialog">', False),
        ("network dialog broken", "", True),        # keyword-noise
        ("timeout waiting for element", '<div role="dialog">', True),  # sem "dialog" no error
    ],
    ids=[
        "gap06_keyword_only_no_dom_returns_none",
        "keyword_and_dom_returns_proposal",
        "gap06_network_dialog_noise_returns_none",
        "no_error_keyword_returns_none",
    ],
)
def test_state_agent_requires_dom_evidence(error_msg, dom_snapshot, expected_none):
    ...
```

**Definition of done Fase 6**:
- [ ] `dom_introspection.py` com helpers `dom_has_role`, `dom_has_mask_attrs`, `dom_has_dialog_handler`.
- [ ] StateAgent downgrada confidence quando DOM sem evidência.
- [ ] InputAgent downgrada confidence quando DOM sem mask attrs.
- [ ] `EvidencePayload.page_state.has_dialog_handler` populado em recorder.
- [ ] Parametrize tests cobrem 8+ casos (agents × cenários).
- [ ] Rec test-pos-hotfix22 rerun — nenhuma cura falso-positiva emitida por StateAgent/InputAgent.

**Commits sugeridos**:
1. `feat(healing): dom_introspection helpers`
2. `fix(state_agent): downgrade confidence sem dom_has_dialog`
3. `fix(input_agent): downgrade confidence sem mask attrs no DOM`
4. `feat(evidence): populate page_state.has_dialog_handler`
5. `test(unit): agents DOM-aware parametrize adversarial`

---

### FASE 7 — Bug detection during recording (nova feature) (~6-8h)

**Objetivo**: quando QA está gravando aplicação crítica e ela apresenta bug, TestForge detecta automaticamente e captura comportamento esperado. Diferencia bug da aplicação vs bug do TestForge vs comportamento esperado.

**Diagrama de referência**: `docs/diagramas/sequencia-bug-detection-recording-ALVO.puml`.

**Trabalho**:

**7.7.1 Modelo de dados** — `src/testforge/models/bug_report.py`:

```python
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


class BugSeverity(Enum):
    CRITICAL = "critical"    # bloqueia fluxo do usuário
    HIGH = "high"            # afeta dado / cálculo / persistência
    MEDIUM = "medium"        # UI/UX degradada
    LOW = "low"              # cosmético


class BugSource(Enum):
    APPLICATION = "application_under_test"
    TESTFORGE = "testforge"
    UNKNOWN = "unknown"


@dataclass
class BugSignal:
    """Um sinal individual capturado por AnomalyDetector."""
    type: str  # "console_error", "network_4xx", "network_5xx", "page_error", "page_crash", "dom_diff"
    timestamp: str
    payload: dict


@dataclass
class BugReport:
    bug_id: str  # BUG-<domain>-<YYYY-MM-DD>-<hash>
    timestamp: str
    recording_id: str
    step_idx: int
    signals: list[BugSignal]

    observed_behavior: str  # o que aconteceu
    user_expected_behavior: str  # o que QA disse que deveria acontecer
    source: BugSource
    severity: BugSeverity

    screenshot_path: Optional[str] = None
    network_trace_path: Optional[str] = None
    console_trace_path: Optional[str] = None

    def to_jsonl_line(self) -> str:
        import json
        return json.dumps({
            "bug_id": self.bug_id,
            "timestamp": self.timestamp,
            "recording_id": self.recording_id,
            "step_idx": self.step_idx,
            "signals": [{"type": s.type, "ts": s.timestamp, "payload": s.payload} for s in self.signals],
            "observed_behavior": self.observed_behavior,
            "user_expected_behavior": self.user_expected_behavior,
            "source": self.source.value,
            "severity": self.severity.value,
            "screenshot_path": self.screenshot_path,
            "network_trace_path": self.network_trace_path,
            "console_trace_path": self.console_trace_path,
        }, ensure_ascii=False)
```

**7.7.2 AnomalyDetector** — `src/testforge/recorder/anomaly_detector.py`:

Componente novo que subscreve a page events e agrega sinais.

```python
import logging
from datetime import datetime
from typing import Callable, Optional

from playwright.sync_api import Page, ConsoleMessage, Request, Response

from ..models.bug_report import BugSignal

logger = logging.getLogger(__name__)


class AnomalyDetector:
    """Subscribe Page events e emite bug_signal via callback quando anomalia
    detectada. Bug detectado != bug confirmado — QA confirma via overlay.

    Sinais monitorados:
    - console_error: mensagem console severity >= error
    - network_4xx / 5xx: response com status ≥ 400 originado de action recente
    - page_error: uncaught JS exception
    - page_crash: tab crashou
    - dom_diff: elemento esperado ausente após ação
      (ex: click em botão com text "Salvar" sem novo role="dialog" em 3s)
    """

    def __init__(self, page: Page, on_signal: Callable[[BugSignal], None]):
        self._page = page
        self._on_signal = on_signal
        self._last_action_ts: Optional[datetime] = None
        self._last_action_target: Optional[str] = None
        self._register_listeners()

    def _register_listeners(self):
        self._page.on("console", self._on_console)
        self._page.on("pageerror", self._on_page_error)
        self._page.on("crash", self._on_page_crash)
        self._page.on("response", self._on_response)

    def _on_console(self, msg: ConsoleMessage):
        if msg.type in ("error", "assert"):
            self._emit(BugSignal(
                type="console_error",
                timestamp=self._now_iso(),
                payload={"level": msg.type, "text": msg.text, "location": str(msg.location)},
            ))

    def _on_page_error(self, exception):
        self._emit(BugSignal(
            type="page_error",
            timestamp=self._now_iso(),
            payload={"error": str(exception)},
        ))

    def _on_page_crash(self):
        self._emit(BugSignal(
            type="page_crash",
            timestamp=self._now_iso(),
            payload={},
        ))

    def _on_response(self, response: Response):
        if response.status >= 400:
            self._emit(BugSignal(
                type=f"network_{response.status // 100}xx",
                timestamp=self._now_iso(),
                payload={
                    "url": response.url,
                    "status": response.status,
                    "method": response.request.method,
                    "body_snippet": self._safe_body_snippet(response),
                },
            ))

    def notify_action(self, target_desc: str):
        """Chamado por RecorderController quando ação de usuário é capturada.
        Permite detector correlacionar sinais com ação recente."""
        self._last_action_ts = datetime.utcnow()
        self._last_action_target = target_desc

    def check_dom_expectation(self, expected: dict, timeout_ms: int = 3000):
        """Verifica se DOM tem elementos esperados N ms após action.
        expected: {"role": "dialog"} ou {"h1_text_contains": "Sucesso"}."""
        # ... implementação usando page.wait_for_selector com timeout curto
        pass

    def _emit(self, signal: BugSignal):
        logger.info("anomaly signal: %s", signal.type, extra={"signal": signal.__dict__})
        self._on_signal(signal)

    def _safe_body_snippet(self, response: Response) -> str:
        try:
            body = response.body() or b""
            return body[:500].decode("utf-8", errors="ignore")
        except Exception:
            return ""

    def _now_iso(self) -> str:
        return datetime.utcnow().isoformat() + "Z"
```

**7.7.3 Extensão overlay_inject.js** — modal bug detection:

Adicionar UI para modal em `overlay_inject.js`:

```javascript
// ==== Bug Detection Modal ====
function _tfShowBugDetectionModal(signals) {
  var modal = document.createElement('div');
  modal.className = '__tf-bug-modal';
  modal.style.cssText = 'position: fixed; top: 20%; left: 25%; width: 50%; ' +
    'background: white; border: 3px solid #dc2626; z-index: 999999; padding: 20px; ' +
    'font-family: system-ui; box-shadow: 0 4px 12px rgba(0,0,0,0.3);';
  modal.innerHTML = '<h2 style="color: #dc2626">🚨 Possível bug detectado</h2>' +
    '<pre style="max-height: 200px; overflow: auto; background: #f9f9f9; padding: 8px;">' +
    JSON.stringify(signals, null, 2) + '</pre>' +
    '<p><strong>Este comportamento é esperado?</strong></p>' +
    '<button id="__tf-bug-expected">Sim, é o comportamento correto</button> ' +
    '<button id="__tf-bug-app">Não, é BUG da aplicação testada</button> ' +
    '<button id="__tf-bug-testforge">Bug do TestForge (falso positivo)</button>';
  document.body.appendChild(modal);

  document.getElementById('__tf-bug-expected').onclick = function() {
    window.__tfBugResponses.push({verdict: "expected", signals: signals, timestamp: new Date().toISOString()});
    modal.remove();
  };
  document.getElementById('__tf-bug-app').onclick = function() {
    var expected = window.prompt("Qual seria o comportamento correto?");
    window.__tfBugResponses.push({
      verdict: "application_bug",
      user_expected_behavior: expected,
      signals: signals,
      timestamp: new Date().toISOString()
    });
    modal.remove();
  };
  document.getElementById('__tf-bug-testforge').onclick = function() {
    window.__tfBugResponses.push({verdict: "testforge_bug", signals: signals, timestamp: new Date().toISOString()});
    modal.remove();
  };
}

window.__tfBugResponses = window.__tfBugResponses || [];
window.__tfShowBugDetectionModal = _tfShowBugDetectionModal;
```

Trigger: `RecorderController` chama `page.evaluate("window.__tfShowBugDetectionModal(...)", signals)` quando `AnomalyDetector` emite sinal significativo.

**7.7.4 Integração RecorderController**:

```python
# src/testforge/recorder/recorder_controller.py

class RecorderController:
    def __init__(self, ...):
        # ...existente...
        self._anomaly_detector: Optional[AnomalyDetector] = None
        self._pending_bug_signals: list[BugSignal] = []
        self._bug_reports: list[BugReport] = []

    def start(self):
        # ...existente...
        if self._config.bug_detection_enabled:
            self._anomaly_detector = AnomalyDetector(
                self._page, on_signal=self._on_bug_signal,
            )

    def _on_bug_signal(self, signal: BugSignal):
        self._pending_bug_signals.append(signal)
        # Batch: quando acumula 1+ sinal crítico, mostra modal
        if signal.type in ("network_5xx", "page_error", "page_crash"):
            self._page.evaluate(
                f"window.__tfShowBugDetectionModal({json.dumps([s.__dict__ for s in self._pending_bug_signals])})"
            )

    def flush_events(self):
        # ...existente...
        # Colhe respostas do modal
        responses = self._page.evaluate("() => (window.__tfBugResponses || []).splice(0)")
        for resp in responses:
            self._process_bug_response(resp)

    def _process_bug_response(self, resp: dict):
        if resp["verdict"] == "expected":
            return  # não faz nada — próxima gravação também não flaggeará
        if resp["verdict"] == "testforge_bug":
            self._telemetry_store.emit({"type": "testforge_bug_report", **resp})
            return
        # application_bug — cria BugReport
        bug_id = self._generate_bug_id(resp)
        report = BugReport(
            bug_id=bug_id,
            timestamp=resp["timestamp"],
            recording_id=self._recording_id,
            step_idx=self._current_step_idx,
            signals=[BugSignal(**s) for s in resp["signals"]],
            observed_behavior=self._summarize_signals(resp["signals"]),
            user_expected_behavior=resp.get("user_expected_behavior", ""),
            source=BugSource.APPLICATION,
            severity=self._infer_severity(resp["signals"]),
            screenshot_path=self._capture_screenshot(),
        )
        self._bug_reports.append(report)
        self._append_to_bug_report_jsonl(report)
```

**7.7.5 Compiler emit `@pytest.mark.known_bug`**:

Arquivo: `src/testforge/semantic/compiler.py`.

Quando step tem `has_bug_ref`, emitir mark:

```python
def _emit_test_method(self, step, output_lines):
    if step.metadata.get("has_bug_ref"):
        bug_ref = step.metadata["has_bug_ref"]
        output_lines.append(
            f'    @pytest.mark.known_bug(\n'
            f'        bug_id="{bug_ref["bug_id"]}",\n'
            f'        detected_during_recording=True,\n'
            f'        user_expected={bug_ref["user_expected_behavior"]!r},\n'
            f'        observed={bug_ref["observed_behavior"]!r},\n'
            f'    )'
        )
    # ... rest of emission
```

Adicionar em `pytest.ini` markers:
```ini
markers =
    known_bug: teste documenta bug conhecido na aplicação testada (xfail com reason)
```

Implementar `conftest.py` hook para tornar `known_bug` mark efetivo (xfail com reason estruturado).

**7.7.6 Report human-readable**:

Novo arquivo `docs/bugs/BUG-<...>.md` emitido por `testforge compile`:
```markdown
# BUG-BANK-2026-07-01-a3f2

**Detectado durante gravação**: 2026-07-01 14:23 UTC
**Recording**: recordings/simulacao-completa/
**Step**: 12 — click "Salvar"

## Comportamento observado
- POST /api/simulate → 500 Internal Server Error
- Botão não desabilita após click
- Dialog "Simulação salva" nunca aparece

## Comportamento esperado (segundo QA)
Ao clicar Salvar deveria abrir dialog 'Simulação salva com sucesso' e limpar formulário.

## Severidade
CRITICAL — bloqueia fluxo principal

## Sinais capturados
- console_error @ 14:23:15: "TypeError: Cannot read property 'success' of undefined"
- network_5xx @ 14:23:14: POST /api/simulate → 500 (body: "InternalServerError")

## Referência no teste gerado
semantic_tests/ST-simulacao-completa/test_st_simulacao_completa.py::TestSimulacaoCompleta::test_clica_calcular
```

**7.7.7 Testes**:

```python
# tests/unit/models/test_bug_report_serialization.py
# tests/unit/recorder/test_anomaly_detector_when_console_error_then_emits_signal.py
# tests/unit/recorder/test_anomaly_detector_when_5xx_response_then_emits_signal.py
# tests/unit/recorder/test_recorder_controller_when_bug_confirmed_then_writes_jsonl.py
# tests/integration/test_bug_detection_flow_end_to_end.py
# tests/e2e/test_bug_detection_flags_500_response_during_recording.py
```

E2E fixture `tests/e2e/pages/broken_submit.html`:
```html
<!DOCTYPE html>
<html>
<body>
  <button id="submit">Salvar</button>
  <script>
    document.getElementById('submit').addEventListener('click', () => {
      // Simula bug: dialog não aparece, promise rejeita
      fetch('/api/broken', {method: 'POST'}).then(r => {
        if (!r.ok) throw new Error("500 InternalServerError");
      }).catch(e => {
        console.error("Falha simulada:", e.message);
      });
    });
  </script>
</body>
</html>
```

Servidor local mock retorna 500 em `/api/broken`.

**Definition of done Fase 7**:
- [ ] `models/bug_report.py` com `BugReport`, `BugSignal`, `BugSeverity`, `BugSource`.
- [ ] `recorder/anomaly_detector.py` com listeners page.on * .
- [ ] `overlay_inject.js` estendido com `__tfShowBugDetectionModal`.
- [ ] `RecorderController` integra AnomalyDetector + processa `__tfBugResponses`.
- [ ] `bug_report.jsonl` emitido em recording dir com sinais + verdict do QA.
- [ ] Compiler emit `@pytest.mark.known_bug` em test gerado.
- [ ] `pytest.ini` `known_bug` mark registrado com xfail hook.
- [ ] `docs/bugs/BUG-*.md` emitido por `testforge compile`.
- [ ] Diagrama `sequencia-bug-detection-recording-ALVO.puml` renderizado.
- [ ] Testes unit + integration + e2e passam. E2E fixture broken_submit.html.
- [ ] Documentação em `docs/ARCHITECTURE-V2.md` seção nova "Bug Detection".

**Commits sugeridos**:
1. `feat(models): BugReport, BugSignal, BugSeverity, BugSource`
2. `feat(recorder): AnomalyDetector com listeners page events`
3. `feat(recorder): overlay bug detection modal em overlay_inject.js`
4. `feat(recorder): RecorderController integra AnomalyDetector`
5. `feat(compiler): emit @pytest.mark.known_bug em código gerado`
6. `feat(cli): emit docs/bugs/BUG-*.md em compile`
7. `test(unit,integration,e2e): coverage bug detection flow`
8. `docs: seção Bug Detection em ARCHITECTURE-V2.md`

---

### FASE 8 — Test organization padrão de mercado (~4h)

**Objetivo**: reorganizar `tests/` seguindo `docs/TEST-PATTERNS.md`.

**Trabalho**:

**7.8.1 Migração progressiva** (não big-bang):

1. Criar diretórios novos: `tests/unit/`, `tests/integration/`, `tests/e2e/`, `tests/regression/`, `tests/contract/`, `tests/factories/`, `tests/helpers/`.
2. Migrar arquivos em grupos coerentes:
   - **Batch A**: tests de resolver/runtime → `tests/unit/runtime/`.
   - **Batch B**: tests de healing → `tests/unit/healing/`.
   - **Batch C**: tests de recorder → `tests/unit/recorder/`.
   - **Batch D**: tests de normalizer → `tests/unit/semantic/`.
   - **Batch E**: e2e recording flows → `tests/e2e/`.
   - **Batch F**: bug_lab/ + widget_regression/ → `tests/regression/`.
   - **Batch G**: intent_lab → `tests/e2e/intent_lab/`.
3. Cada batch: 1 commit, mv arquivos, ajustar imports.

**7.8.2 pytest.ini atualizado**:
```ini
[pytest]
testpaths = tests
markers =
    unit: fast (<10ms), no I/O, no browser
    integration: multi-component real objects, no browser
    e2e: browser real
    regression: cobre bug conhecido
    slow: >1s
    critical: bloqueia release
    known_bug: teste documenta bug ainda-não-corrigido
    generated: teste gerado por TestForge (para app cliente)
addopts = --strict-markers -ra
```

**7.8.3 Renomeações agressivas** (só onde nome atual é indecifrável):

Exemplos:
- `test_hotfix22_dedup_key_collision.py` → `tests/regression/normalizer/test_dedup_key_when_material_currencymask_id_empty_then_uses_placeholder.py`
- `test_bug_fix_encoding.py` → `tests/regression/recorder/test_utf8_encoding_when_portuguese_labels_then_preserves_diacritics.py`

Não faça big-bang. Um arquivo por commit. Manter git blame legível.

**7.8.4 conftest.py hierárquico**:
- `tests/conftest.py` — fixtures globais.
- `tests/unit/conftest.py` — mocks pontuais.
- `tests/integration/conftest.py` — real objects.
- `tests/e2e/conftest.py` — browser + serve_fixture_html.

**Definition of done Fase 8**:
- [ ] Diretórios `tests/{unit,integration,e2e,regression,contract,factories,helpers}/` existem com `__init__.py`.
- [ ] `pytest.ini` atualizado com markers documentados.
- [ ] Batch A-G migrados (pode ser em PR separado por batch).
- [ ] Arquivos com nomes desligados (`test_hotfix22_dedup_key_collision.py`) renomeados.
- [ ] Todos testes ainda passam após migração.
- [ ] CI pipeline atualizado para rodar por mark: `pytest -m unit`, depois `-m integration`, etc.

---

### FASE 9 — Meds restantes (~1.5h)

**Objetivo**: fechar gaps 09, 12, 16 (11 e 13, 14, 17 já cobertos em Fase 1 via instrumentation + potencialmente Fase 8).

**Gaps cobertos**: GAP-09 (empty candidates SemanticTarget), GAP-12 (confidence threshold), GAP-16 (build_target validation).

**Trabalho**:

**7.9.1 Consolidação GAP-09 + GAP-16** — helper `_finalize_target_with_candidates`:

```python
# src/testforge/semantic/recording_normalizer.py

def _finalize_target_with_candidates(
    self, target: SemanticTarget, candidates: list[LocatorCandidate],
    context: dict,
) -> Optional[SemanticTarget]:
    """Contrato de saída: SemanticTarget SEMPRE tem >= 1 candidate ou é None."""
    if not candidates:
        # Tentar synthesizar CSS fallback do raw selector
        raw_css = context.get("raw_css_selector")
        if raw_css:
            candidates.append(LocatorCandidate(
                strategy="css_fallback_synth",
                selector=raw_css,
                score=0.2,
                playwright_call=f'locator("{raw_css}")',
            ))
            logger.info("target sem candidates — synthesized CSS fallback",
                        extra={"raw_css": raw_css})
            self._metrics.record("normalizer.empty_candidates_synth")
        else:
            logger.info("target sem candidates E sem raw_css — retornando None",
                        extra={"context": context})
            self._metrics.record("normalizer.target_dropped")
            return None
    target.candidates = candidates
    return target
```

Substituir chamadas em `_build_target` (linha 534) e no outro ponto (linha 1986).

**7.9.2 GAP-12** — constantes de confidence:

Arquivo: `src/testforge/healing/curator.py`, no topo:
```python
AGENT_MIN_CONFIDENCE_NO_RUNNER = 0.70   # quando não pode validar por execução
AGENT_MIN_CONFIDENCE_WITH_EXEC = 0.50   # quando execução valida na sequência
```

Usar em vez do hardcoded `0.5`.

**7.9.3 Testes**:
```python
# tests/unit/semantic/test_normalizer_when_target_empty_candidates_then_synthesizes_css.py
# tests/unit/semantic/test_normalizer_when_target_no_raw_selector_then_returns_none.py
# tests/unit/healing/test_curator_confidence_threshold_constants.py
```

**Definition of done Fase 9**:
- [ ] `_finalize_target_with_candidates` implementado + usado nos 2 pontos.
- [ ] Constantes `AGENT_MIN_CONFIDENCE_*` documentadas + usadas.
- [ ] Testes unit passam.

---

## 8. Critérios sucesso globais

**Antes de PR de qualquer fase**:
- [ ] `pytest -m "unit or contract or regression"` passa 100%.
- [ ] `pytest -m integration` passa 100%.
- [ ] `pytest -m e2e -m critical` passa 100%.
- [ ] Rec `test-pos-hotfix27_2` re-executada: `assert_hit_rate ≥ 80%` (era 50%).
- [ ] Rec `test-pos-hotfix22` re-executada: `assert_hit_rate ≥ 90%` (era 64%).
- [ ] Summary counters de Fase 1 mostram redução de skips silenciosos.
- [ ] Nenhuma regressão nas suites `regression/` existentes.

**Preferência de merge**: 9 PRs pequenos (um por fase). Se contexto pedir PR único, seção "Test Plan" no body listando cada rec + assert_hit_rate esperado/obtido.

---

## 9. Diretrizes execução

**Branch base**: partir de `feature/inline-overlay-prompt`. Não misturar com trabalho de calendar backtrack.

**Commits**: 1 conceito lógico por commit. Formato `<type>(<scope>): <descrição>`.

**Não regravar**: contrato hard [[feedback-no-regrave]]. Iterar `compile`+`run-incremental` sobre recordings existentes.

**Não fazer**:
- Não implementar Opção A (action-aware resolve) — v3 futuro.
- Não tocar em `testforge run` legacy (decommission em [[project-run-legacy-decommission]]).
- Não adicionar comments explicando WHAT do código — só WHY não-óbvio.
- Não remover teste que já passa. Migrar/renomear é OK, deletar precisa justificativa.

**Ferramentas**:
- `pytest tests/ -v` — full suite.
- `pytest -m <mark>` — por categoria.
- `testforge run-incremental <path>` — regression rec.
- `plantuml docs/diagramas/*.puml` — regen diagramas.

**Handoff**:
- Atualizar `.planning/healing-gaps-status.md` (criar) por fase.
- Update memory `[[project-hotfix22-session-2026-07-01]]` com resultado por fase.

---

## 10. Anti-padrões (rejeitados em code review)

- ❌ Fase implementada sem novo teste. Cada gap tem teste antes do fix.
- ❌ `except: pass` em novo código.
- ❌ `time.sleep(N)` em teste.
- ❌ Comentário `# fix bug` sem link para o gap.
- ❌ Mudança que ativa modo verde silencioso (`return True` como default).
- ❌ Feature nova sem entry em `docs/ARCHITECTURE-V2.md`.
- ❌ Novo teste que não segue `docs/TEST-PATTERNS.md`.

---

## 11. Referências

- Padrão testes: `docs/TEST-PATTERNS.md` (contrato obrigatório).
- Arquitetura: `docs/ARCHITECTURE-V2.md`.
- Diagramas ATUAL/ALVO/bug-detection: `docs/diagramas/*.puml` (criados nesta iteração).
- Contrato no-regrave: `[[feedback-no-regrave]]`.
- Sessão-mãe: `[[project-hotfix22-session-2026-07-01]]`.
- Análise SIOPI 15b-e: `[[project-siopi-15-run-analysis]]`.
- Bugs anteriores: `[[project-recorder-critical-bugs-2026-06-30]]`.
- Run legacy decommission: `[[project-run-legacy-decommission]]`.
- Diagramas versioning: `[[project-diagrams]]`.
