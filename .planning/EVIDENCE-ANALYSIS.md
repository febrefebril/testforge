# Evidence Analysis — 11 real recordings, 5 sistemas

Análise das gravações em `evidencias/recordings.zip` (2026-06-24 a 2026-06-26). Cada gravação rodou pipeline completa (record → compile-check → readiness gate / pilot). Cada arquivo `submission_report.json` carrega o veredito final + falhas.

**Sistemas cobertos**: SIOPI (3), SIMAX (4), SISGH (1), SIFAP (1), SIPBS-revendedor (gas-do-povo + sipbs-internet) (2).

> Este arquivo é o resultado da análise pedida em 2026-06-27. Cada bug é numerado **B<N>** e cruzado com REGRESSION-PATTERNS.md / DEBT-INVENTORY.md quando aplicável. Itens com nota `→ ticket` viram entrada nova no backlog.

---

## Resumo por gravação

| # | Recording | Sistema | Status | Verdict | Falhas | Bugs principais |
|---|---|---|---|---|---|---|
| 1 | REC-20260624-133822 | SIOPI | completed_raw | not_evaluated | — | B1, B16 |
| 2 | deve_fazer_upload_sisgh_2 | SISGH | incomplete_intent | fail | 12 | B1, B4, B7, B16 |
| 3 | deve_gerar_relatorio_… | SIPBS-revend. | needs_review | needs_review | 10 + 7 blk | B1, B2, B4, B11 |
| 4 | deve_logar_no_gas_do_povo_3 | SIPBS-revend. | ready_for_team | pass (vazio) | — | B12 (verdict misleading) |
| 5 | deve_logar_no_sifap | SIFAP | incomplete_intent | fail | 20 | B1, B2, B4, B6, B10 |
| 6 | deve_marcar_horario | SIMAX | needs_review | needs_review | 4 | B1, B5, B6, B8, B17 |
| 7 | deve_marcar_horario_2 | SIMAX | needs_review | needs_review | 4 | B14 (duplicata), B17 |
| 8 | verifica_regrecao | SIOPI | incomplete_intent | fail | 3 | B1, B9, B16 |
| 9 | verificar_envio_via_git | SIOPI | completed_raw | not_evaluated | — | B3, B13, B16 |
| 10 | verificar_tela_simax | SIMAX | needs_review | needs_review | 4 | B5, B15, B17 |
| 11 | verificar_tela_simax_2 | SIMAX | needs_review | needs_review | 5 + 1 blk | B5, B17 |

11 gravações: 0 passaram de fato (1 "pass" mas sem step run). 5 fail, 4 needs_review, 2 not_evaluated. **Taxa real de teste resiliente = 0%.**

---

## Bugs identificados

### B1 — `value_mutations.jsonl` vazio em 10/11 gravações

**Sintoma**: 10 das 11 gravações têm 0 entries em `value_mutations.jsonl`. Apenas `verificar_tela_simax` tem 5 entries (todas só `'t'` — picker noise).

**Evidência**: SIOPI REC-20260624 — 11 cliques, 0 fills, 0 value_mutations. Final_state captura `02/02/1993` e ` 1.000,00 `. Recorder vê valor via DOM scan no fim, mas perde keystrokes intermediárias.

**Causa provável**:
- O `_hookValue` em `overlay_inject.js` faz `Object.defineProperty(HTMLInputElement.prototype, 'value', ...)`.
- Angular Material datepicker e currency mask **possivelmente** não usam o setter regular — usam `el.dispatchEvent(new Event('input'))` + atualização indireta, ou redefinem o property descriptor por instância.
- Hotfix 22 já consertou o **reader**. Mas o **writer** (overlay JS) está silenciosamente não emitindo eventos pros campos que mais importam (Material masked).

**Classe**: P2 `silent-default-swallow` (recorder não loga falha de hook).

**Ação**: investigar. Adicionar log de debug no overlay JS quando hook é instalado e contar invocações. Possivelmente trocar pra `MutationObserver` em `input.value` attribute (já existe nesse arquivo para outros campos — line ~300).

→ **Ticket H6**: investigar por que `_hookValue` não dispara em Material currency/date mask.

---

### B2 — CPF fill duplicado (raw + masked) sem deduplicação

**Sintoma**: 3 recordings (`deve_gerar_relatorio`, `deve_logar_no_gas_do_povo_3`, `deve_logar_no_sifap`) gravam duas vezes:
```
fill "CPF" = "53986717749"
fill "CPF" = "539.867.177-49"
```

Usuário digita uma vez, mask reformata, recorder vê duas atualizações via input event.

**Causa**: o normalizer hoje colapsa fills consecutivos no MESMO elemento (verifica element_id ou aria-label), mas se element_id está vazio (B16) ou se vem como `name="cpf"` numa hora e sem name na outra, a comparação falha.

**Impacto**: o teste replicado digita primeiro "53986717749" no campo já marcado, mask transforma; depois digita "539.867.177-49" *no topo* — campo recebe lixo. Mesmo padrão que prestação SIOPI.

**Classe**: P1 `code-duplication-drift` (mesma classe de bug que CS-1 atacou no runner, agora aparece no normalizer dedup).

**Ação**: dedup precisa considerar (placeholder canonical + aria-label + selector). Preservar só o último fill na mesma sessão por elemento.

→ **Ticket H7**: normalizer dedup multi-key.

---

### B3 — fill keystroke-by-keystroke vira 6 events separados

**Sintoma**: `verificar_envio_via_git` (SIOPI):
```
fill 000.000.000-00 = '1'
fill 000.000.000-00 = '12'
fill 000.000.000-00 = '123'
fill 000.000.000-00 = '1231'
fill 000.000.000-00 = '123.12'
fill 000.000.000-00 = '123.123'
```

CPF mask emite input event a cada keystroke. Recorder grava todos. No replay, runner digita 6 vezes — concatena no campo.

**Causa**: overlay JS `_pushEvent('fill', el)` em `addEventListener('input', ...)` sem debounce. Cada input event = 1 raw_event.

**Impacto**: hotfix 16/17 do runner fez triple-click clear — então 2ª fill em diante reescreve. Mas ainda é 6 calls ao runner em vez de 1, e o último valor "123.123" é INCOMPLETO (user parou de digitar).

**Classe**: P5 `compile-runtime-divergence` (recorder grava intent partial, runner replay raises).

**Ação**: overlay JS debounce input events com 300ms tail. Normalizer já tem `_compact_events` — verificar se está colapsando fills consecutivos com mesmo target+timestamp_within_500ms.

→ **Ticket H8**: input-debounce no recorder + dedup no normalizer.

---

### B4 — `ERR_CERT_AUTHORITY_INVALID` em URLs Caixa intranet

**Sintoma**: 3 recordings falham em Step 1 (navigation):
```
Step 1 (navigation): failed — Page.goto: net::ERR_CERT_AUTHORITY_INVALID
  at https://sifap-frontend-internet-v2-des.apps.nprd.caixa/
```

Pelo menos 3 sistemas: sifap, sisgh, sipbs-revend.

**Causa**: contexto Playwright sem `ignore_https_errors=True`. Cert intra-Caixa é self-signed/CA interna não confiada pelo Chromium default.

**Impacto**: piloto inteiro inutilizado em apps intranet. **Bloqueia QA piloto na rede Caixa**.

**Ação**: `browser.new_context(ignore_https_errors=True)`. Trivial.

→ **Ticket H9** (CRÍTICO, bloqueia piloto): habilitar `ignore_https_errors` no IncrementalRunner.

---

### B5 — `Element is not an <input>` em SIMAX (mat-select)

**Sintoma**: 3 recordings SIMAX falham em fill step:
```
Step 6 (fill): failed — Page.fill: Error: Element is not an <input>, <textarea> or [contenteditable] element
```

Step 6, 9, 12 são fills nos selects SIMAX (UF, Edifício, etc).

**Causa**: recorder vê `change` event no `<mat-select>` ou `<select>` wrapped por dsc-select. Grava como `fill`. Compiler emite `page.fill(selector, "DF")`. Mas Playwright `fill` exige real input/textarea/contenteditable. Mat-select é `<mat-select>` (custom element).

**Ação**: AngularMaterialHandler já tem `handle_select` — confirmar que `_extractTarget` no overlay JS marca elementos `select` corretamente. No normalizer, ação `select_option` em vez de `fill` para `<select>` / `<mat-select>`.

**Classe**: P5 `compile-runtime-divergence` (compile emite fill, runtime exige select_option).

→ **Ticket H10**: SIMAX mat-select detection (recorder + normalizer).

---

### B6 — `Locator.fill: Timeout 3000ms exceeded` (elemento não visível)

**Sintoma**: múltiplas gravações, especialmente sifap (steps 4, 7, 10, 15, 31, 34):
```
Step 4 (fill): failed — Locator.wait_for: Timeout 3000ms exceeded.
  - waiting for locator("input[aria-label=\"CPF\"]").first to be visible
```

**Causa**: 
- (a) Após cert error (B4), página não carrega → input nunca aparece.
- (b) Mesmo sem cert error, alguns inputs estão dentro de `*ngIf` ou tab inativa → 3s timeout muito curto.

**Ação**: aumentar wait_for timeout pra 8-10s default em fills. Adicionar wait-for-visible explicit antes do fill (já existe — só timeout curto). Implementar pre-condition que aguarda networkidle antes de tentar fill.

**Classe**: P5 (timing).

→ **Ticket H11**: configurable timeout + networkidle gate pre-fill.

---

### B7 — File upload `C:\fakepath\` (já no backlog)

**Sintoma**: `deve_fazer_upload_sisgh_2` grava `fill = 'C:\\fakepath\\CNT.EMP.MZ.BMX0.PRONAMPE.D26'`.

**Status**: já mapeado em H5 (BACKLOG.md). Reconfirma necessidade. Bloqueia piloto SISGH.

---

### B8 — Submit/postback detection inconsistente

**Sintoma**: SIMAX (3 recordings) faz 3 POST/PUT/PATCH XHRs mas grava 0 submits, 0 postbacks. SIPBS (3 recordings) grava 1+1 corretamente.

**Causa**: SIMAX provavelmente faz fetch sem disparar `submit` event nem `__doPostBack` URL pattern. Hotfix 7+12 pseudo_submit deveria pegar via XHR POST + recent_clicks tail. Mas `pseudo_submit_tagged=0` em TODAS as gravações — incluindo as que TÊM postbacks gravados.

**Classe**: P4 `feature-flag-rot` — hotfix 7+12 shipped mas não está sendo invocado nessas gravações antigas (foram gravadas antes da feature).

**Ação**: re-gravar SIMAX num teste novo, validar que pseudo_submit_tagged sai >0. Se ainda 0, debug por que `_recent_clicks` não atinge `_mark_pseudo_submit`.

→ **Ticket H12**: validar hotfix 12 em SIMAX produção.

---

### B9 — SIOPI step 3 click sem mudança de URL = `failed`

**Sintoma**: `verifica_regrecao`:
```
Step 3 (click): failed — url before='https://simuladorhabitacao.caixa.gov.br/home' after='https://simuladorhabitacao.caixa.gov.br/home'
```

Step 3 é click na "Calculadora poder de compra". Oracle de pos-condição espera URL change. Mas SPA Angular pode demorar pra trocar URL após click (router lazy load).

**Causa**: post-condition assertion `url_change_after_click` com timeout curto. Por outro lado, hotfix 14 SIOPI #4 passou step 3 (`page.wait_for_timeout(3000)` no compile). Talvez aqui não emitiu o wait.

**Ação**: confirmar que compiler emite `wait_for_timeout(3000)` pra todo click marcado `causes_navigation`. Adicionar `wait_for_load_state('networkidle')` como pos-condição.

→ **Ticket H13**: networkidle wait + retry no oracle de navigation.

---

### B10 — Assert no fim falha "Nenhum seletor encontrou o elemento"

**Sintoma**: `deve_logar_no_sifap` step 39 assert:
```
Step 39 (assert): failed — Nenhum seletor encontrou o elemento (2 tentativas)
```

Login completo + form fill + submit + redirect. Assert final em elemento da página resultado. Página ainda não renderizou quando assert testou.

**Causa**: assert sem wait-for-network. Após submit, runner não espera próxima página carregar antes de assertar.

**Ação**: pre-condition do assert deve aguardar URL change OU networkidle se URL não mudou. Compiler emite `page.wait_for_load_state('networkidle')` antes de cada assert.

→ **Ticket H14**: pre-condition de espera antes de assert.

---

### B11 — Cascading block (step block leva 7 outros pra blocked)

**Sintoma**: `deve_gerar_relatorio_*`: total=23, pass=1, fail=10, skip=5, **blocked=7**.

**Causa**: `step_dependency_graph` marca step N+M como bloqueado quando step N falha. Stop_on_failure desligado, mas dependent steps blocked.

**Análise**: comportamento correto. Mas reporting confunde — verdict=needs_review com 7 blocked sugere TestForge falhou, quando na verdade o teste-base falhou no step 1 e cascateou.

**Ação**: distinguir "test failed because of TestForge" vs "test failed because the SUT broke". Verdict mais semântico: `sut_unreachable` quando step 1 nav falha → cascading skip não conta como fail.

→ **Ticket H15**: granular verdict por classe de falha.

---

### B12 — `verdict=pass` com 0 steps executados (misleading)

**Sintoma**: `deve_logar_no_gas_do_povo_3`: `verdict=pass crit_pass=5/5 steps=0`.

**Causa**: 5 critérios passaram (compile OK, intent complete, asserts present, etc.) mas IncrementalRunner não rodou. Verdict "pass" não significa que o teste PASSOU em execução real — só passou nos gates.

**Impacto**: dashboards de QA vão reportar "verde" sem teste real. Falso positivo crítico.

**Ação**: verdict "pass" exige `steps.passed > 0` E `steps.failed + healing_rejected == 0`. Senão usar `gated` ou `not_executed`.

→ **Ticket H16**: verdict semantics (CRÍTICO confiança piloto).

---

### B13 — `verdict=not_evaluated` quando pipeline parou em raw

**Sintoma**: 2 recordings (`REC-20260624`, `verificar_envio_via_git`): submission_report tem `verdict=not_evaluated crit_pass=0/5`.

**Causa**: pipeline parou em "completed_raw" (gravação OK, mas compile não rodou). Pode ser usuário cancelando `--complete` prompt ou erro silencioso.

**Ação**: distinguir abandoned vs failed. Talvez não escrever submission_report se nada rodou.

→ **Ticket H17**: not_evaluated → não publicar submission_report.

---

### B14 — Gravações idênticas (deve_marcar_horario vs _2)

**Sintoma**: dois diretórios com mesmo conteúdo (15 events, 5 nav, 7 click, 3 fill, mesmas labels, mesmas falhas).

**Causa provável**:
- (a) Usuário re-gravou esquecendo de mudar o `--name`.
- (b) Auto-publisher rodou 2x produzindo cópias (bug).

**Ação**: publisher rejeita duplicata por hash do raw_events.jsonl. Loga warning.

→ **Ticket H18**: dedup publisher.

---

### B15 — fingerprint `input#[name=]` (input sem id, sem name) gera ruído

**Sintoma**: `verificar_tela_simax` value_mutations.jsonl tem 5 entries com fingerprint `input#[name=]` e valor `t`.

**Causa**: input sem id e sem name (campo SIMAX desconhecido). Hook captura mas fingerprint colide. Valor `t` parece ser uma tecla acidental.

**Ação**: fingerprint precisa incluir XPath ou índice ordinal quando id+name vazios. Já tinha apontado em A4 (DEBT-INVENTORY).

→ Cobrir em **R-A4** do REFACTOR-SPRINT.

---

### B16 — `final_state_snapshot.fields[*].label = "?"` (anônimos)

**Sintoma**: TODAS as 11 gravações: campos do final_state aparecem com label vazio na análise.

**Causa**: Schema do snapshot armazena `{value: '...'}` sem aria-label / placeholder / name. Reader não consegue correlate.

**Impacto**: final_state RECUPERA valor (último estado da página), mas o resolver runtime não casa porque field_value_map gera chave canonical de label vazio.

**Classe**: P3 `unanchored-state`. **5ª ocorrência**. Mesmo padrão das outras 4 (writer/reader mismatch).

**Ação**: 
1. Atualizar `final_state_snapshot` writer para incluir aria-label/placeholder/name por field.
2. Atualizar reader `_ir_final_state` para usar essas labels.
3. Round-trip test em test_invariants.

→ **Ticket H19**: final_state schema com labels (mesmo shape de value_mutations pós hotfix 22).

**Esta é a 5ª ocorrência de P3. Frequência sugere que a defesa estática precisa ser mais forte**: implementar dataclass `RecorderArtifact` com versão de schema, validar em compile-time.

---

### B17 — SIMAX 4 recordings, todas needs_review

**Sintoma**: 4 gravações SIMAX (marcar_horario, marcar_horario_2, verificar_tela_simax, verificar_tela_simax_2). Todas needs_review. Todas falham em steps fill com B5 ou B6.

**Causa raiz**: SIMAX usa Angular Material extensivamente — mat-select, mat-form-field, mat-datepicker. Hotfix 5 (CDK overlay wait) cobriu CDK overlay. Hotfix 20 (datepicker click-only). Mas `mat-select` ainda falha (B5).

**Ação**: handler completo de mat-select. Já tem skeleton em `handlers/angular_material.py` (Sprint 1 do M12). Verificar se está sendo invocado.

→ **Ticket H10** (cruza com B5).

---

## Cross-pattern observations

### Padrão dominante: P3 — writer/reader mismatch

Já tem **5 ocorrências** registradas em REGRESSION-PATTERNS.md após esta análise:

1. hotfix 8 — run-incremental path
2. hotfix 15 — recording_root anchor
3. CS-4a — field_value_map
4. hotfix 22a — value_mutations
5. hotfix 22b — element_id vs id
6. **B16** (esta análise) — final_state labels

A defesa estática atual cobre apenas (3) e (4). (5) está parcial. (6) descoberta agora.

**Recomendação**: implementar dataclass `RecorderArtifact` versionado para CADA artefato em disco. Schema em src/testforge/recorder/artifacts.py. Writer e reader importam do mesmo módulo. Lint rule rejeita acesso por chave string.

### Padrão B12 — verdict "pass" falso positivo

Critério atual: 5 gates → pass. Não exige replay bem-sucedido.

Esta é a maior fragilidade do piloto: dashboard verde sem teste real. Antes de liberar QA, **B12 é blocker** — verdict deve exigir `steps.passed > 0 AND failed + healing_rejected == 0`.

### B4 + B6 + B9 + B10 — sequência típica em ambiente intranet Caixa

1. Cert error em step 1 (B4) → todos os steps subsequentes timeout (B6) → eventual assert falha (B10) → cascateia blocked (B11).

A consequência prática: **ANTES de liberar QA piloto, B4 (HTTPS errors) deve ser corrigido**. Sem isso, 0% dos testes intranet rodam.

---

## Lista priorizada de tickets

| # | Ticket | Severidade | Bloqueia piloto? |
|---|---|---|---|
| H9 | `ignore_https_errors=True` no runner | crítica | **SIM** |
| H16 | verdict semantics (não dar "pass" sem replay) | crítica | **SIM** |
| H6 | `_hookValue` não dispara em Material masked | alta | parcialmente (workaround = final_state) |
| H10 | SIMAX mat-select handler | alta | SIMAX bloqueado |
| H7 | Normalizer dedup multi-key (B2) | alta | login flows |
| H11 | Timeout configurável + networkidle pre-fill | média | reduz flakiness |
| H8 | Input debounce no recorder | média | qualidade gravação |
| H13 | networkidle wait pós-click navigation | média | SPA |
| H14 | wait pre-assert | média | qualidade assert |
| H19 | final_state schema com labels (P3 #5) | média | menos --complete |
| H15 | verdict por classe de falha | baixa | reporting |
| H17 | not_evaluated → no submission_report | baixa | ruído |
| H18 | publisher dedup | baixa | armazenamento |
| H12 | Validar hotfix 12 em SIMAX | baixa | sintoma | 

H5 / B7 (file upload): já no backlog.

---

## Próximo passo

Recomendo:

1. Executar **H9** + **H16** imediatamente (1-2h) — destrava QA em ambiente intranet com verdict confiável.
2. Re-rodar as 4 gravações que falharam em cert (B4) com `ignore_https_errors=True`. Esperar verdict real.
3. **H6** (overlay _hookValue) requer investigação real — abrir browser em SIOPI com instrumentação JS, ver por que hook não dispara em Material currency.
4. **H10** (mat-select handler) — investigar se Sprint 1 handler está sendo invocado.
5. Resto entra em **REFACTOR-SPRINT** ou backlog.

**Sobre o questionamento "aprendizado não fixa"**: padrão P3 chegou a 5 ocorrências. A defesa estática precisa ser **mais forte** — não só round-trip de UM artefato, mas validação automática de **todos** os artefatos em disco. Isso vira ticket próprio antes do refactor sprint.
