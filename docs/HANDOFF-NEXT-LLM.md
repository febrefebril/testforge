# TestForge — Handoff para próxima LLM implementadora

**Único arquivo que você precisa ler.** Este handoff é auto-contido: contém contexto, plano, ponteiros, memórias-chave da sessão anterior, e instruções passo-a-passo.

**Data do handoff**: 2026-07-02
**Sessão anterior**: audit + planejamento (não implementou código de produção — só docs + diagramas)
**Handoff de**: Claude Opus 4.7 (equipada com memory system)
**Handoff para**: qualquer LLM (Sonnet 4.7, Opus 4.7, GPT, outra)

## Atualização de execução (2026-07-01)

- Fase 3, 4, 5 e 6: concluídas e validadas.
- Fase 7: funcionalmente avançada e formalizada em arquitetura (`docs/ARCHITECTURE-V2.md`, seção Bug Detection During Recording).
- Fase 9: concluída (thresholds de confiança em constantes + `_finalize_target_with_candidates`).
- Fase 2/8: estrutura-base criada (`tests/factories`, `tests/helpers`, `tests/regression`, `tests/integration`, `tests/e2e/pages`) e testes iniciais adicionados.
- Fase 0: README de diagramas criado; regeneração de PNGs bloqueada por ambiente corporativo (sem `plantuml` e download de `plantuml.jar` bloqueado por rede).
- Regressão recente: `44 passed, 1 xfailed` em bateria focada.

## Atualização de execução (2026-07-07) — sessão 7 (Fase 8 completa — JS)

- **Fase 8 completa** (2 commits: `0ecffaf` + `82f3083`):
  - RC-15: `SmartStepRunner._adaptive_wait_for_visible()` — networkidle 5s antes de wait_for_selector(visible).
  - RC-29: `RawRecordingStore.sort_events_by_timestamp()` — sort raw_events.jsonl in-place.
  - RC-16: `__tfFieldSnapshotInterval` diff-only — `__tfLastFieldSnapshotValues` por fingerprint; emit apenas campos que mudaram. Elimina emissão de 90 mutations para 18 fills.
  - RC-19: `_getTextContent(el)` helper — recurse children skipping `<script>`, `<style>`, `<noscript>`. Usado em `_extractTarget` elText para não-select. Fix CADASTRO/GESTAO inline JS vazando em div.text.
  - RC-27: `_pushEvent` defer 100ms quando `element_id` E `role` ausentes — Angular termina render antes de commit. Timestamp capturado imediatamente para preservar ordem.
  - 9 novos testes: `tests/unit/recorder/test_mutation_observer_*`, `test_get_text_content_*`. Update `test_select_textcontent.py`.
- **Sanity**: `pytest -m "unit or contract or regression"` = **346 passed, 1 xfailed** (era 337).
- **Fase 8 DoD**: RC-15 ✅ RC-16 ✅ RC-19 ✅ RC-27 ✅ RC-29 ✅.
- **Próxima fase**: **Fase 9** já foi concluída (thresholds de confiança). Ver `docs/RECORDING-BUGS-FIX-PLAN.md` para próximas fases pendentes.

## Atualização de execução (2026-07-07) — sessão 5 (Fase 7 completa)

- **Fase 7 completa** (2 commits: `6eadede` + `e4c2d9e`):
  - RC-11: `_convert_event()` — fill em `input[type=file]` → `set_input_files`.
  - RC-12: evento `postback` → `wait_for_navigation` (networkidle 8s + url guard).
  - 5.7.6: `_skip_dead_fills()` — fills sem identifier estável → `skip_reason="dead_fill_no_identifier"`.
  - RC-13: `AngularMaterialHandler._dedup_datepicker_sequences()` — quando `picker_echo_fill` E fill tem "/" (DD/MM/YYYY válido) → converte fill em `select_date`, suprime nav clicks com `datepicker_aggregated`. Garbled fills (raw digits) mantêm comportamento antigo.
  - RC-22: `AngularMaterialHandler._aggregate_autocomplete()` — detect fill em input com `aria-autocomplete`/`mat-autocomplete` seguido de `mat-option` click → agrega em `search_and_select`. Executa ANTES de `_skip_dead_fills`.
  - Compiler: `_gen_select_date()` + `_gen_search_and_select()` + dispatch legacy + v2.
  - 12 novos testes em `tests/unit/handlers/`.
- **Sanity**: `pytest -m "unit or contract or regression"` = **330 passed, 1 xfailed** (era 318).
- **Fase 7 DoD verificado**: RC-11 ✅ RC-12 ✅ RC-13 ✅ RC-22 ✅ dead fill skip ✅.
- **Próxima fase**: **Fase 8** — Timeout adaptativo + MutationObserver diff + textContent filter.
  - Arquivos: `runner/fallback_runner.py` (timeout adaptativo), `recorder/overlay_inject.js` (MutationObserver diff + getTextContent filter + raw_events sort).
  - Ver `docs/RECORDING-BUGS-FIX-PLAN.md` seção "FASE 8".

## Atualização de execução (2026-07-07) — sessão 4 (Fase 7 parcial — RC-11/12/dead-fill)\n\n## Atualização de execução (2026-07-07) — sessão 3 (Fase 6)

- **Fase 6** (5 commits: `4f16a28`→`1f92275`): seletores frágeis + assert generator.
  - RC-9: `_GENERIC_ID_BLACKLIST` demove IDs next/prev/submit/save/cancel para score=0.35.
  - RC-9: `role=menuitem` sem accessible_name demovido para score=0.25 + warning.
  - RC-9: `.mat-button-wrapper` em css_path promovido para `button:has-text()`.
  - RC-9: `nth-of-type` em css_path recebe variante `has_text` ao lado.
  - RC-10: select texto bruto >60 chars pulado (all-options concatenated); bloco geral texto pula `tag==select`.
  - RC-14: `_convert_step()` — assert textual/automatico sem `expected_value` → `skip_reason="assert_missing_expected"`.
  - RC-14: assert em css_path container genérico → warning.
  - RC-14: overlay — aviso soft quando assert alvo não tem accessible_name.
  - 33 novos testes em `unit/recorder/` e `regression/recording/`.
- **Sanity total**: `pytest -m "unit or contract or regression"` = **311 passed, 1 xfailed**.
- **Próxima fase**: **Fase 7** — Handlers específicos (file, postback, calendar, autocomplete).
  - Arquivos: `config/component_patterns.yaml`, `handlers/file_input.py`, `semantic/recording_normalizer.py`.
  - Ver `docs/RECORDING-BUGS-FIX-PLAN.md` seção "FASE 7".

## Atualização de execução (2026-07-07) — sessão 2 (Fases 2-5)

- **Fase 2** (`fd88c5c`): publisher steps.jsonl reconciliation + artifact_counts.
- **Fase 3** (`9eff81c`): overlay blocklist tf-*/`__tf-*` + pilot healing default ON + `--no-healing` opt-out.
- **Fase 4** (`c68f63e`): value_mutation dedup fingerprint stable + placeholder skip (`DD/MM/AAAA`) + currency whitespace strip.
- **Fase 5** (`0b550de`): diagnostic mode — 3 fixes:
  - RC-6: `ReplayCheck.drain()` armazena URL por step + navega antes de probar. Nav failure → `url_context_unavailable`.
  - RC-7: `FrameworkDetector.detect()` retenta `_detect_once()` 3x/500ms quando DOM vazio + primary=unknown. Extraiu `_detect_once()`.
  - RC-8: `_normalize_url_for_compare()` em `step_postcondition.py` — sort query params, mantém fragment. Previne false positive pass por reorder de params.
  - 22 novos testes: `tests/unit/diagnostic/` (2 arquivos) + `tests/unit/runner/` (1 arquivo).
- **Sanity total**: `pytest -m "unit or contract or regression"` = **278 passed, 1 xfailed**.
- **Próxima fase**: **Fase 6** — RC-9 (seletores frágeis), RC-10 (select normalizer), RC-14 (assert validation).
  - Arquivos principais: `src/testforge/semantic/recording_normalizer.py` + `src/testforge/recorder/overlay_inject.js`.
  - Ver `docs/RECORDING-BUGS-FIX-PLAN.md` seção "FASE 6" + memory `[[project-fase-5-recording-progress]]`.

## Atualização de execução (2026-07-07) — sessão 1

- Análise 49 recordings CORPORATIVO → 92 bugs REC catalogados + 30 root causes.
  Documento: `.planning/bugs-recording-analysis.md`.
- **Fase 1 RECORDING-BUGS-FIX-PLAN concluída** (5 commits: 24f88f6, 2ce6c78, 97a63cd, ca390be, +fixtures):
  - PII detector observability-only (`src/testforge/security/pii_detector.py`) — patterns CPF/CNPJ/email/phone/matrícula/corp filename/password/PIN/Keycloak/production.
  - Recording scanner (`recording_scanner.py`) percorre todos artifacts.
  - CLI `testforge audit-pii` com --json, --fail-on-critical, --out.
  - `<select>` textContent extraction (placeholder + selected only) — fix BUG-REC-30/69.
  - `FAILED_MARKER.source_dir` path relativo — fix BUG-REC-89.
  - Production domain prompt em `cmd_record` — BUG-REC-59/86.
  - Post-recording auto-scan → `<rec>/sensitive_alerts.json`.
  - 2 recordings âncora fixtures (`r5a_sifap_credentials`, `r7a_siopi_producao`) + goldens.
  - Contract test cross-source: detector NUNCA modifica values ([[feedback-pii-alert-only]]).
  - 44 tests novos (unit + contract + regression).
- **Sanity total**: `pytest -m "unit or contract or regression"` = **234 passed, 1 xfailed**.
- Docs criados: `RECORDING-BUGS-FIX-PLAN.md`, `ANTI-REGRESSION-PLAN.md`.
- Memory criada: `[[project-recording-bugs-2026-07-07]]`, `[[feedback-pii-alert-only]]`, `[[feedback-no-regression]]`, `[[project-fase-1-recording-progress]]`.
- **Contrato hard estabelecido**: dados sensíveis NÃO são mascarados — são massa de teste. Detector é observability-layer apenas.
- Próximas fases (2-9) documentadas em `docs/RECORDING-BUGS-FIX-PLAN.md`. Tasks 29-36 criadas.

## Atualização de execução (2026-07-02)

- Fase 8 avançou com migração real de testes de fase para `tests/unit/phase` e `tests/integration/phase`.
- `tests/conftest.py` agora aplica marcadores por path (`unit`, `integration`, `e2e`, `regression`, `contract`) para suportar a nova taxonomia.
- Validação local da reorganização (rodada atual): `pytest tests/unit/phase -q` => `158 passed, 1 xfailed`; `pytest -m "unit or integration" -q` => `163 passed, 1823 deselected, 1 xfailed`.
- Fase 1 smoke com gravação existente: `compile uncategorized/test-pos-hotfix22 --data` executa e gera script.
- `run-incremental` deixou de encerrar com `Nenhum step encontrado` após ajuste no `IncrementalRunner._find_recording_dir` para lookup recursivo em `recordings/<categoria>/<id>`.
- Regressão adicionada: `tests/test_incremental_recording_lookup.py`.
- Migração da Fase 8 concluída com lote final `test_phase_b_*` movido para `tests/unit/phase` e `tests/integration/phase`, com ajustes para schema atual e descoberta recursiva de recordings.
- Gates finais de marcador verdes:
  - `pytest -m unit -q` -> `189 passed, 1 xfailed`
  - `pytest -m integration -q` -> `13 passed`
- Plano marcado como concluído nesta execução, com única exceção autorizada pelo usuário: não regenerar PNG dos diagramas.

---

## 0. Comece por aqui — leitura obrigatória, nesta ordem

1. **Este arquivo** (`docs/HANDOFF-NEXT-LLM.md`) — 100% agora.
2. **`docs/HEALING-GAPS-PLAN.md`** — plano executável de 9 fases. É o que você vai executar.
3. **`docs/TEST-PATTERNS.md`** — contrato obrigatório de testes. Toda linha de teste que você escrever segue esse arquivo.
4. **`CLAUDE.md`** (raiz do repo) — visão geral arquitetura + comandos.
5. **`docs/ARCHITECTURE-V2.md`** — arquitetura v2 (Phases 1-7 já shipadas).

Diagramas de referência (abrir enquanto lê o plano):
- `docs/diagramas/sequencia-resolver-ATUAL.puml` + `sequencia-resolver-ALVO.puml` — GAP-01 (fase 3)
- `docs/diagramas/sequencia-curator-runner-ATUAL.puml` + `sequencia-curator-runner-ALVO.puml` — GAP-02/03 (fase 4)
- `docs/diagramas/sequencia-bug-detection-recording-ALVO.puml` — Fase 7 feature nova

Diagramas existentes referenciados: `docs/diagramas/sequencia-fluxo-completo-v2.puml`, `fluxograma-pipeline-v2.puml`, `sequencia-assert-flow.puml`, `sequencia-curadoria-l0-l3.puml`.

---

## 1. TL;DR do trabalho

**Contexto**: TestForge grava testes E2E semânticos com self-healing 4-layer. Cliente-alvo: QA em setores regulados (bancos, seguros, saúde, gov). Falha silenciosa = bug vaza para produção.

**Descoberta da sessão anterior**: 17 gaps de código + 10 gaps em diagramas + 1 feature ausente (bug detection during recording). Todos os gaps compartilham 2 antipatterns:
- **Sinal fraco = decisão forte** (existence, keyword, non-empty tratados como validação).
- **Falha silenciosa** (`except: pass`, `continue` sem log, default fallback).

Métrica `assert_hit_rate` real está 14-64% quando cada teste individual reporta PASS.

**Seu job**: implementar 9 fases descritas em `docs/HEALING-GAPS-PLAN.md`. Cada fase é independente. Ordem sugerida: 0 → 1 → 2 → 3 → 4-6 (paralelo) → 7 (paralelo com 3-6) → 8 → 9.

**Não regravar**: contrato hard — não crie recordings novos para testar fixes. Iterar `compile` + `run-incremental` sobre recordings existentes em `recordings/`. Ver Seção 5 abaixo.

---

## 2. Estado do repo neste ponto

- **Branch**: `feature/inline-overlay-prompt` (base `fix/improvements-v0.1.0`).
- **Remote**: `git@github.com:febrefebril/testforge.git`.
- **Ultimo commit da sessão anterior de código**: `b9474f6 revert(handler): direct-fill mode Material datepicker`.
- **Docs criados nesta sessão** (o que você vai ver a mais):
  - `docs/HANDOFF-NEXT-LLM.md` (este arquivo)
  - `docs/HEALING-GAPS-PLAN.md`
  - `docs/TEST-PATTERNS.md`
  - `docs/diagramas/sequencia-resolver-ATUAL.puml`
  - `docs/diagramas/sequencia-resolver-ALVO.puml`
  - `docs/diagramas/sequencia-curator-runner-ATUAL.puml`
  - `docs/diagramas/sequencia-curator-runner-ALVO.puml`
  - `docs/diagramas/sequencia-bug-detection-recording-ALVO.puml`
- **Nenhum código de produção foi tocado nesta sessão.** Apenas docs.

---

## 3. Memórias-chave da sessão anterior (inline aqui — você não terá memory system)

### 3.1 Contrato `no-regrave` (feedback do usuário — hard rule)

**Regra**: NUNCA regravar uma recording existente para testar um fix. Iterar sempre com `testforge compile` + `testforge run-incremental` sobre gravações que já existem em `recordings/`. Regressões viram teste automatizado em `tests/regression/` ou fixture em `bug_lab/`.

**Motivo**: o usuário perdeu tempo em sessões anteriores refazendo gravações caras (SIMULADOR banco, forms Angular Material com 30+ steps) só para descobrir que o fix não pegou. Ele quer contrato: uma vez gravado, use até morrer.

**Como aplicar**: quando avaliar fix, rode `testforge run-incremental semantic_tests/ST-test-pos-hotfix27_2/test_st_test_pos_hotfix27_2.py` (ou outra rec existente). Se o fix precisa de recording nova, isso é sinal de que o fix mira o lugar errado.

### 3.2 Métrica `run` legacy mente

O comando `testforge run` (legacy, sem `-incremental`) reporta 100% de sucesso mesmo quando o real é 0%. Não confie nele.

**Use SEMPRE `testforge run-incremental`** — esse tem o denominator correto (denominator = asserts no script compilado, não asserts executados) e `assert_hit_rate` real.

Há um trabalho paralelo de decommission do `testforge run` legacy — não o toque nesta rodada.

### 3.3 Rodadas SIMULADOR 15b-e — 14-64% assert_hit_rate

Rodadas em banco/SIMULADOR (banco brasileiro, forms Angular Material com currencymask, datepicker Material, radio shadow DOM) revelaram cascade failure:

- `test-pos-hotfix22` — 7/11 asserts (64%). Blocker: dedup key collision em campos Material.
- `test-pos-hotfix26` — 4/6 asserts (67%). Poder de compra results REJ em fields calc-egi.
- `test-pos-hotfix27_2` — 3/6 asserts (50%). Calendar Material cascade — click posicional errado quando range difere.

Todas as três batem em pelo menos um dos 17 gaps do plano. Especialmente GAP-01 (resolver retorna primeiro que existe, não primeiro que funciona).

### 3.4 Bugs de recorder de sessão anterior (2026-06-30)

Corrigidos, mas contextualizam a base:

- Bug 1: `field_snapshots.jsonl` nunca emitido — setInterval retornava array mas não empilhava. **Fixado.** Test em `tests/test_field_snapshot_emission_fix.py`.
- Bug 2: `asserts_total` contava só executados. **Fixado.** Denominator agora `len(self.steps)`.
- Bug 3: `--complete` reporta COMPLETA com valor mask intermediário (0,20 em vez de R$ 200k). **Ainda aberto** — coberto por GAP-14 do novo plano.
- Bug 4: cdk-overlay clicks todos skipped sem detect. **Ainda aberto** — coberto por GAP-10.

### 3.5 Hotfix22 session — o que ficou

13 commits no dia 2026-07-01. Últimos:
- `b9474f6` REVERT direct-fill Material datepicker (input rejeita fill direto).
- `c2fcbc6` calendar cells text score boost 0.9 > css 0.6.
- `6f07769` trust Playwright: `_validate_fill` para masks só valida non-empty (isso é o **GAP-08** do plano — o "trust Playwright" agora precisa ser complementado com magnitude compare).

**Backtrack architecture** (proposta do usuário): quando healing detecta cascade failure (3+ REJs após click X), fazer `page.storage_state()` restore + retry X com estratégia alternativa. NÃO implementado. Não faz parte deste plano — trabalho separado.

### 3.6 Diagramas versionados (14 PlantUML)

Todos os `.puml` devem ter PNG correspondente regenerado após edit. Comando: `plantuml docs/diagramas/*.puml`. Instalar `plantuml` no sistema se ainda não tem.

### 3.7 User profile

- Desenvolvedor experiente Python/TestForge.
- Prefere respostas terse.
- Aversão a comentários no código (só WHY não-óbvio, nunca WHAT).
- Não regravar recordings.
- Quer transparência sobre progresso — atualizar `.planning/healing-gaps-status.md` a cada fase.
- Quer testes seguindo padrão de mercado. Ver `docs/TEST-PATTERNS.md`.
- Escreve em português. Códigos + commits em inglês. Comentários em código raramente e em inglês.

---

## 4. Fluxo de trabalho recomendado

### 4.1 Setup inicial

```bash
git clone git@github.com:febrefebril/testforge.git
cd testforge
git checkout feature/inline-overlay-prompt
git pull

# Ambiente Python
source activate.sh  # cria .venv + adiciona bins
pip install -e ".[dev]"
playwright install chromium

# Sanity: rodar suite atual
pytest tests/ -v
# Deve passar. Se algo falhar, PARE e reporte antes de qualquer edit.

# Sanity: verificar plano
ls docs/HEALING-GAPS-PLAN.md docs/TEST-PATTERNS.md
ls docs/diagramas/sequencia-*ATUAL.puml docs/diagramas/sequencia-*ALVO.puml
```

### 4.2 Ordem de execução

Siga a ordem sugerida no plano (Seção 2 do HEALING-GAPS-PLAN):

1. **Fase 0** (~1.5h) — sync diagramas restantes (já criei 5, restam edits em 6 outros).
2. **Fase 1** (~2h) — instrumentation (log + counter em cada silent skip).
3. **Fase 2** (~2h) — test harness + factories + MockPageBuilder.
4. **Fase 3** (~2h) — GAP-01 retry-with-next-candidate + cache.
5. **Fase 4** (~1.5h) — curator no-runner → DEGRADED.
6. **Fase 5** (~1.5h) — mask postcondition magnitude/ISO.
7. **Fase 6** (~3h) — agents DOM-aware.
8. **Fase 7** (~6-8h) — bug detection during recording (feature nova).
9. **Fase 8** (~4h) — reorganize tests padrão mercado.
10. **Fase 9** (~1.5h) — meds restantes.

Fase 3 tem regressão-gate obrigatória (Fase 2 harness). Fases 4-6 podem paralelizar entre si em branches separados. Fase 7 é independente.

### 4.3 Por fase — checklist

Antes de começar fase N:
- [ ] Ler seção "FASE N" completa em `HEALING-GAPS-PLAN.md`.
- [ ] Ler diagramas ATUAL/ALVO relacionados (Fase 3 → resolver, Fase 4 → curator, Fase 7 → bug-detection).
- [ ] Ler `TEST-PATTERNS.md` seções relevantes (sempre relevante: 3, 4, 6, 7, 10).
- [ ] Criar branch `feat/gap-<NN>-<slug>` (ou trabalhar direto em `feature/inline-overlay-prompt` se o user preferir — perguntar).

Durante:
- [ ] Um commit por conceito lógico. Commits sugeridos estão listados em cada fase do plano.
- [ ] Teste antes do fix (regression teste que falha) → fix → teste passa.
- [ ] Rodar `pytest -m "unit or contract"` frequentemente. Deve ficar verde.

Após:
- [ ] `pytest -m "unit or integration or regression"` passa.
- [ ] `pytest -m e2e -m critical` passa (se aplicável à fase).
- [ ] Rodar rec de regressão específicas da fase (definidas em Definition of done).
- [ ] Atualizar `.planning/healing-gaps-status.md` com resultado da fase.
- [ ] Marcar Definition of done bullets como completos.

### 4.4 Rodadas de regressão obrigatórias

Comandos para validar cada fase:
```bash
# rodar contra rec existente sem regravar
testforge run-incremental semantic_tests/ST-test-pos-hotfix27_2/test_st_test_pos_hotfix27_2.py
testforge run-incremental semantic_tests/ST-test-pos-hotfix22/test_st_test_pos_hotfix22.py
testforge run-incremental semantic_tests/ST-test-pos-hotfix26/test_st_test_pos_hotfix26.py
```

Metas por rec:
- `test-pos-hotfix27_2`: era 50% (3/6). Após Fase 3, alvo ≥ 80%.
- `test-pos-hotfix22`: era 64% (7/11). Após Fase 3, alvo ≥ 90%.
- `test-pos-hotfix26`: era 67% (4/6). Após Fase 5, alvo ≥ 90%.

Se após uma fase a métrica NÃO melhorar como esperado — investigue antes de seguir. Provavelmente o fix não pegou o caminho certo do código.

---

## 5. Comandos essenciais

```bash
# Setup
source activate.sh
pip install -e ".[dev]"
playwright install chromium

# Testes por categoria
pytest -m unit                     # <30s
pytest -m "unit or integration"   # <3min
pytest -m e2e                     # slow, use com CI
pytest -m regression              # regression suite
pytest -m critical                # blocker suite

# Recording (novos — só se ausolutamente necessário)
testforge record http://localhost:8765 --name "test"

# Compile + run-incremental (o que você vai usar 90% do tempo)
testforge compile <recording-name> --data
testforge run-incremental semantic_tests/ST-<name>/test_st_<name>.py

# Diagramas
plantuml docs/diagramas/*.puml  # regen PNGs

# Fake bank app (necessário p/ alguns testes e2e)
cd synthetic_lab/fake-react-bank-app && python -m http.server 8765 &

# CLI helpers
testforge demo-heal
testforge pilot-report
```

---

## 6. Arquivos e paths críticos

Estrutura do repo:
```
testforge/
├── src/testforge/
│   ├── cli/app.py                      # todos os CLI commands
│   ├── recorder/
│   │   ├── recorder_controller.py      # Fase 1 GAP-15, Fase 7 anomaly integration
│   │   └── overlay_inject.js           # Fase 1 GAP-04/05, Fase 7 modal
│   ├── semantic/
│   │   ├── recording_normalizer.py     # Fase 1 GAP-10/11/13/14/17, Fase 9 GAP-09/16
│   │   └── compiler.py                 # Fase 7 emit @pytest.mark.known_bug
│   ├── runtime/
│   │   ├── resolver.py                 # Fase 3 GAP-01
│   │   └── step.py                     # Fase 3 integração StepExecutor
│   ├── runner/
│   │   ├── step_executor.py            # Fase 3 (criar ou estender)
│   │   ├── step_postcondition.py       # Fase 5 GAP-08
│   │   └── fallback_runner.py          # não tocar salvo se necessário
│   ├── healing/
│   │   ├── curator.py                  # Fase 4 GAP-02/03, Fase 9 GAP-12
│   │   ├── healing_catalog.py          # não tocar
│   │   └── agents/
│   │       ├── state_agent.py          # Fase 6 GAP-06
│   │       └── input_agent.py          # Fase 6 GAP-07
│   ├── models/
│   │   ├── pipeline.py                 # Fase 4 add ProgressResult.DEGRADED
│   │   └── bug_report.py               # Fase 7 CRIAR
│   └── metrics/
│       └── pilot_metrics.py            # Fase 1 add silent_skip_counter
├── docs/
│   ├── HANDOFF-NEXT-LLM.md             # este arquivo
│   ├── HEALING-GAPS-PLAN.md            # plano executável 9 fases
│   ├── TEST-PATTERNS.md                # contrato de testes
│   ├── ARCHITECTURE-V2.md              # arquitetura v2
│   └── diagramas/                      # 20+ PlantUML
├── tests/                              # 108+ arquivos atualmente flat
│   ├── (Fase 8 reorganiza em unit/integration/e2e/regression/contract/factories/helpers/)
│   └── ...
├── recordings/                         # NÃO CRIAR novas — usar existentes
├── semantic_tests/                     # NÃO REGRAVAR — só compilar sobre recordings/
├── bug_lab/                            # regressions históricas
├── CLAUDE.md                           # instruções projeto
└── pytest.ini / pyproject.toml         # setup
```

---

## 7. Se você encontrar algo inesperado

- **Código não bate com o plano**: STOP. Reporte. Não invente fix. Discrepância pode ser trabalho paralelo do user desde o handoff.
- **Teste que já existia falha após seu edit**: revert seu edit imediatamente. Não avance sem entender.
- **Bug novo descoberto**: adicione entry em `.planning/healing-gaps-status.md` com título "Bug adicional descoberto" antes de continuar.
- **Diagrama diverge de código real**: prefira código; edite diagrama para refletir.
- **Comando `testforge` falha**: `source activate.sh` de novo. Se persistir, reporte.

---

## 8. Contato & handoff reverso

Ao terminar (ou pausar), atualize:
1. `.planning/healing-gaps-status.md` — status atual por fase.
2. Commit final com mensagem: `docs(handoff): sessão N+1 encerrada, fase X completada, pendências Y`.
3. Push para origin.
4. Se houve dúvida crítica não resolvida, adicione seção "OPEN QUESTIONS" no fim deste arquivo antes de commitar.

---

## 9. Resumo dos 17 gaps (referência rápida)

| # | Sev | Path:Line | Sintoma | Fase |
|---|-----|-----------|---------|------|
| 01 | crit | resolver.py:167 | Existência ≠ execução | 3 |
| 02 | crit | curator.py:235 | L0 fake PASSED sem runner | 4 |
| 03 | crit | curator.py:333 | L2 fake PASSED sem runner | 4 |
| 04 | crit | overlay_inject.js:1869 | try/catch engole exception | 1 |
| 05 | crit | overlay_inject.js:512 | Empty batch enfileirado | 1 |
| 06 | high | state_agent.py:30 | Confidence só por substring "dialog" | 6 |
| 07 | high | input_agent.py:31 | Mask detect só por keyword | 6 |
| 08 | high | step_postcondition.py:112 | Mask aceita non-empty (bug canônico) | 5 |
| 09 | high | recording_normalizer.py:1986 | SemanticTarget candidates=[] silent | 9 |
| 10 | high | recording_normalizer.py:2243 | Overlay skip sem audit | 1 |
| 11 | high | recording_normalizer.py:3096 | IR dedupe drop sem log | 1 |
| 12 | med | curator.py:324 | Confidence 0.5 arbitrário | 9 |
| 13 | med | recording_normalizer.py:804 | entry_label fallback vazio aceito | 1 |
| 14 | med | recording_normalizer.py:2941 | _ir_final_state skip falsy silent | 1 |
| 15 | med | recorder_controller.py:418 | Diagnostic exception debug-only | 1 |
| 16 | med | recording_normalizer.py:534 | _build_target não valida candidates | 9 |
| 17 | med | recording_normalizer.py:1535 | Click sem candidates silent | 1 |

Todos os detalhes ("o que acontece hoje", "impact", "fix orientation", "testes obrigatórios") estão em `docs/HEALING-GAPS-PLAN.md`. Não duplico aqui.

---

## 10. Padrão de teste em 30 segundos

Do `docs/TEST-PATTERNS.md` — se ler só isso, mínimo aceitável:

- Nome arquivo: `test_<subject>_when_<condition>_then_<outcome>.py`.
- Nome função: `def test_<verb>_when_<condition>_then_<outcome>():`
- Blocos AAA obrigatórios com comentários `# Arrange`, `# Act`, `# Assert`.
- Fixtures em conftest hierárquico. Factories em `tests/factories/`.
- `@pytest.mark.unit|integration|e2e|regression|critical|known_bug`.
- Parametrize com `ids=` explícito.
- Sem `time.sleep`, sem `except: pass`, sem `test_1`.
- Docstring cita gap ou bug: "GAP-01 regression: pré-fix, X. Fase Y fix: Z."

---

## 11. Bom trabalho.

O plano detalha tudo. Se algo estiver ambíguo no plano, este handoff diz o que fazer (Seção 7: STOP + reporte).

Boa iteração.
