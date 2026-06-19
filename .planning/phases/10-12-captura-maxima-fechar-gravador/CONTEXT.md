# Phase 10 Context — Captura Máxima: Fechar Gravador

## Goal
Estabilizar o gravador de intenção (recorder) para distribuição ao time de testers. Após essa fase, o gravador congela — time grava, envia `recordings/{id}/`, e a equipe de engenharia itera apenas nos módulos downstream (normalizer, reconstructor, compiler, runner).

## Scope

### O que já foi feito (Fase A — congelado)
- Fix 1: Readiness gate com `step_results=[]` → PASS quando completeness=true (`readiness_gate.py`)
- Fix 2: Dedup cross-source por element_id no normalizer + completeness checker
- Fix 3: Overlay JS rejeita `document.body` como alvo de assert
- Fix 4: `_eliminate_prefill_clicks` — click antes de fill no mesmo elemento → skipped
- Fix 5: `_dedup_datepicker_sequences` — nav de calendário + fill → só o fill fica ativo
- Fix 6: Compiler filtra assert `#body` gerando comentário em vez de código executável

### O que FALTA implementar (itens do backlog desta fase)

#### B1 — Assert `#body` ainda falha no runner
O compiler gera comentário em vez de `expect(...)`, mas o `run-incremental` executa a partir de `semantic_steps.jsonl`, não do Python compilado.
- Localização: `src/testforge/runner/incremental_runner.py` — precisa pular steps com `skip_reason` ou cujo selector seja body/html
- **Critério de aceite:** Step 24 no `simulador-credito6` passa como SKIP em vez de healing_rejected

#### B2 — Radio buttons ainda healam (steps 3, 4, 21, 22)
Selector `label[for="mat-radio-1-input"]` não bate no Angular Material DOM porque o Angular Material não renderiza o atributo `for` nos radio buttons — usa `mat-radio-button` com evento próprio.
- O normalizer gera `label[for="mat-radio-N-input"]` a partir do `step.target.label` + `step.target.element_id`
- Deveria gerar `label[for="mat-radio-N-input"]` OU como fallback `mat-radio-button:has-text("label text")` com score maior
- Localização: `src/testforge/semantic/recording_normalizer.py` → `_build_target()` — estratégia de seletor para radio buttons Angular Material
- **Critério de aceite:** Steps 3, 4, 21, 22 passam como [OK] sem healing

#### C1 — `--pilot-mode` executa incremental headless automaticamente
Atualmente `--pilot-mode` na gravação não roda o incremental. O gate de readiness é chamado com `step_results=[]` (fixado para PASS com warning, mas não valida execução).
- Implementar em `src/testforge/cli/app.py` → `_run_post_recording_validation()`:
  1. Compilar o script (já existe `compile` no CLI)
  2. Rodar `run-incremental` em modo headless com timeout
  3. Coletar `step_results` reais
  4. Passar para `RecordingReadinessGate.evaluate()`
- **Critério de aceite:** `testforge record --pilot-mode URL --name X` produz relatório de readiness com contagem real de steps passed/healed/failed

#### C2 — Metrics gate (Fase C piloto)
Implementar métrica: `% de campos resolvidos sem --data` e `% sem intervenção humana`.
- `src/testforge/metrics/pilot_metrics.py` já existe — verificar se precisa de wiring
- **Critério de aceite:** `testforge compile --check recordings/X/` imprime "% campos auto-resolvidos: N%"

#### D1 — Guia para testers (1 página)
Arquivo `docs/GUIA_TESTER.md` com:
- Como instalar (`pip install testforge` ou equivalente)
- Como gravar: `testforge record --app CAIXA URL --name nome`
- Atalhos: Shift+S parar, Shift+A assert, Shift+P pausar
- Como enviar: zip de `recordings/{nome}/` completo
- O que NÃO fazer (não editar arquivos da gravação)

## Arquivos-chave
- `src/testforge/runner/incremental_runner.py` — B1
- `src/testforge/semantic/recording_normalizer.py` → `_build_target()` — B2
- `src/testforge/cli/app.py` → `_run_post_recording_validation()` — C1
- `src/testforge/metrics/pilot_metrics.py` — C2
- `docs/GUIA_TESTER.md` — D1

## Gravação de referência
`recordings/simulador-credito6/` — app CAIXA Simulador Habitação Angular Material

## Estado atual do run-incremental (pré-fase)
```
total: 24
passed: 8
healed_validated: 4  (steps 3,4,21,22 — radio buttons)
healing_rejected: 1  (step 24 — assert #body)
skipped: 11
```

## Meta pós-fase
```
total: 24
passed: 12
healed_validated: 0
healing_rejected: 0
skipped: 12
```

## Constraints
- NÃO modificar overlay JS do recorder (congelado após Fase A)
- NÃO modificar estrutura de arquivos das gravações
- Downstream only: normalizer, compiler, runner, metrics, docs
