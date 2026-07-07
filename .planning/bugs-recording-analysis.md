# Bugs — Análise de Recordings (MASSA_DE_TESTE, MASSA_DE_TESTE_01, PLATAFORMA DES)

**Data análise**: 2026-07-07
**Base de referência**: `.planning/ARCHIVE/BUGS.md` (data 2026-06-15, catalogou BUG-001..BUG-018)
**Escopo**: análise de gravações reais Portal de Massa CAIXA + Plataforma DES CAIXA
**Objetivo**: catalogar bugs de recorder/normalizer/compiler/publisher/runner descobertos em rodadas reais. Não corrigir agora — priorizar depois.

Formato por bug:
```
BUG-REC-NN — <sev: crit|high|med|low>: <título curto>
  Encontrado em: <recording>
  Sintoma: <o que se vê>
  Evidência: <artefato + linha/campo>
  Causa provável: <hipótese>
  Impact: <o que quebra downstream>
  Prioridade: <ordem sugerida>
```

---

## Recordings analisados

### R1 — MASSA_DE_TESTE / SOLICITACAO / solicitar_massa_no_siiso
- Path: `src/testforge/MASSA_DE_TESTE/SOLICITACAO/Deve filtrar por periodo o numero de vendas de uma loja credenciada no programa gas do povo/solicitar_massa_no_siiso/`
- URL: `sinop-portaldemassa-frontend-des.apps.nprd.caixa`
- Framework detectado: Angular 16.2.12 + ngx-ui-loader
- Duração: 45s
- Status: `intent_complete`, verdict `not_evaluated` (compile não rodado)
- Raw events: 26 (7 navigation, 9 click, 9 fill, 1 assert)
- steps.jsonl: **1** (só assert final)
- Diagnostic steps: 19
- selectors_immediate_ok/fail: **0 / 9**

### R2 — MASSA_DE_TESTE_01 / CRIAR_SOLICITACAO_TEST / deve_criar_uma_solicitacao_siiso
- Path: `src/testforge/MASSA_DE_TESTE_01/CRIAR_SOLICITACAO_TEST/deve_criar_uma_solicitacao_siiso/`
- URL: `plataforma-des.caixa/`
- Framework detectado: **null** (falhou detectar apesar de ser Angular)
- Duração: 22 min (12:25→12:48)
- Status: `incomplete_intent`, verdict `fail`
- Steps totais: 22 (6 passed, 11 failed, 5 skipped)
- Assert hit rate: **0.0** (0/2 asserts)
- Raw events: 27 (5 nav, 9 click, 8 fill, 3 submit, 2 assert)
- steps.jsonl: **2** (só asserts)
- Diagnostic steps: 22
- selectors_immediate_ok/fail: **0 / 20**
- blind_spots: 4
- Healing: DESATIVADO (run-incremental sem --enable-healing)

### R4a — Portal de Massa / Relatorio / Deve filtrar por periodo... (Programa Gás do Povo)
- Path: `src/testforge/Portal de Massa/Relatorio/.../REC-20260702-150145/`
- URL: `sipbs-internet-revendedor-frontend-des.apps.nprd.caixa/home` (**subsistema Gás do Povo**, revendedores)
- Rec ID: `REC-20260702-150145` (schema antigo YYYYMMDD-HHMMSS)
- Data recording: **2026-07-02** (4 dias antes do bundle fix)
- Duração: 1m44s
- Status: `intent_complete`, verdict `not_evaluated` (compile não rodado)
- Raw events: **43** (7 nav, 23 click, 7 fill, 1 postback, **3 select_option**, 1 submit, 1 assert)
- steps.jsonl: **1** (só assert — MESMO padrão que R1/R2/R3)
- value_mutations: 31
- **Não tem**: keystroke_buffer, suggested_assertions, ax_snapshots, diagnostic, completeness, readiness, _pilot_runs — schema **anterior** ao bundle fix
- Contém: CPF pessoal `539.867.177-49` (username), password `134679` (6-dígito PIN), múltiplos CNPJs revendedores

### R11 — recordings_failed/ (3 recordings SIMAX auto-movidos por `incomplete_intent`)
- Path: `recordings_failed/`
- 3 recordings: `as_de_sexta_20260703-202821`, `massageria_20260703-204921`, `nova_massagem_20260703-210034`
- Cada um tem `FAILED_MARKER.json`:
  ```
  {"recording_id": "as_de_sexta",
   "reason": "incomplete_intent",
   "source_dir": "C:\\Desenvolvimento\\AUTOMATA-PRIMUS\\recordings\\as_de_sexta",
   "failed_at": "2026-07-03T20:28:22Z"}
  ```
- Mesma taxonomy que SIMAX/suite exploratoria/todas as massagens/{as_de_sexta,massageria,nova_massagem}
- Todos raw=18 vm=5 steps=1 (padrão SIMAX consolidado)
- Sem submission_report (compile não chegou a rodar)
- Contém pastas completas: ax_snapshots, completeness, diagnostic, dom_snapshots, readiness, _pilot_runs, _pilot_tmp

### R10 — uncategorized / 12 recordings PIONEIROS (2026-06-24 a 26)
- Path base: `src/testforge/uncategorized/`
- **12 recordings iniciais** ANTES da taxonomia system/suite/test_case existir
- Contém sistemas variados: SIOPI (`simuladorhabitacao.caixa.gov.br`), SIMAX (`simax.caixa/simax/`), SISGH (`sisgh-web-tqs`), Portal de Massa Gás do Povo (`sipbs-internet-revendedor`), SIFAP (`sifap-frontend-internet-v2-des`)
- Schema: **null** (schema versioning ainda não existia)
- Metadata só tem `recording_id`, `application`, `base_url`, `status` — sem `system/suite/test_case`
- Statuses variados: `completed`, `needs_review`, `incomplete_intent`, `ready_for_team` (statuses deprecated)
- Test cases meta: `teste_inicial` (prova conceito 1ª rec), `verifica_regrecao`, `verificar_envio_via_git`, `verificar_tela_simax` (+ `_2`), `REC-20260624-133822` (rec sem nome)
- Test cases regravados depois: `deve_logar_no_sifap` (repetido em SIFAP/R5a), `deve_fazer_upload_sisgh_2` (repetido em SISGH/R8), `deve_marcar_horario` (+ `_2`) (repetido em SIMAX/R9)

### R9 — SIMAX / 20 recordings (agendamento de massagem terapêutica corporativa)
- Path base: `src/testforge/simax/`
- URL: `simax.caixa/simax/`
- Sistema: **SIMAX** (Sistema de Marcação/Agendamento) — massagem terapêutica interna CAIXA
- Contagem: **20 recordings distintos** (11 em 2026-07-02 schema antigo, 9 em 2026-07-03 schema novo)
- Suites: `marcação de consulta`, `pesquisa de vagas`, `suite exploratoria`, `testar todas os agendamentos`, `teste de massagem`, `testes aleatorios`, `testes de agendamento`
- Test cases: `agendar_na_quarta`, `agendar_na_terc_a`, `busca_de_massagem_em_brasilia` (+ `_2`, `_2_2`), `busca_de_vaga_na_matriz_2/3/4`, `deve_ter_hor_rio_as_13_na_quinta`, `deve_ter_hor_rio_as_16_na_quista` (typo QA), `existe_horario_as_14h/15`, `segunda`, `sexta`, `segunda_feira_sem_massagem`, `ter_a_tamb_m_n_o_tem_massagem`, `massageria` (+ `nova_massagem`, `as_de_sexta`, `massageria_20260703-204921`)
- Padrão comum: ~18 raw events (fill autocomplete "t" + 3-5 select_option per select), 5 value_mutations, steps.jsonl=1-2 asserts
- **CONFIRMAÇÃO**: SIMAX é sistema referência **BUG-001 ARCHIVE** (`<select>` handling)

### R8 — SISGH / UPLOAD_ARQUIVO / deve_fazer_upload_sisgh
- Path: `src/testforge/SISGH/UPLOAD_ARQUIVO/deve_fazer_upload_sisgh/deve_fazer_upload_sisgh_3/`
- URL: `sisgh-web-tqs.apps.nprd.caixa` (TQS)
- Sistema real page_title: **"Sistema de Gestão de Honras"** (não Habitação como sugere sigla). Metadata `system: SISGH` mas page_title diz **SGH**.
- Data recording: 2026-07-02 (schema antigo, sem diagnostic/completeness/keystroke)
- Duração: 1m30s
- Status: `incomplete_intent`, verdict `fail`
- Steps: 18 (8 passed, 5 failed, 5 skipped) — criteria 4/5
- Raw: 19 (7 nav, 7 click, 3 fill, 1 submit, 1 assert)
- steps.jsonl: **1** assert
- Contém: matrícula `c892018` (4ª QA diferente), password `01Bola01` (paste=true), nome arquivo real `CNT.EMP.MZ.BMX0.PRONAMPE.D260625.R4`

### R7a — SIOPI / suite exploratoria / testar todos os calculos / calculadora1
- Path: `src/testforge/SIOPI/suite exploratoria/testar todos os calculos/calculadora1/`
- URL: **`simuladorhabitacao.caixa.gov.br/home`** — **PRODUÇÃO REAL CAIXA** (não DES/TQS)
- Sistema: Simulador Habitação — referência memory `[[project-hotfix22-session-2026-07-01]]`
- Data recording: 2026-07-02
- Duração: 1m17s
- Status: `intent_complete`, verdict `not_evaluated`
- Raw: 17 (2 nav, 11 click, 2 fill, 1 submit, 1 assert)
- steps.jsonl: **1** assert
- value_mutations: 25 (currency mask + calendar navigation)
- Sem diagnostic/completeness/keystroke/pilot (schema antigo)

### R7b — SIOPI / Todas as calculadoras / testar todas as calculadoas em sequencia
- Path: `src/testforge/SIOPI/Todas as calculadoras/testar todas as calculadoas em sequencia/executar_todas_as_calculadoras_e_pegar_todos_os_asserts/`
- URL: `simuladorhabitacao.caixa.gov.br/home` (produção)
- Duração: 1m13s
- Raw: 29 (2 nav, 17 click, 7 fill, 3 assert) — **3 calculadoras testadas em sequência**
- steps.jsonl: **3** asserts (`R$ 33.333,33`, `R$ 383.646,67`, `R$ 640.839,97`)
- value_mutations: **85** (~13x amplification currency)

### R6a — SIFEC / TEST LOGIN / LOGIN USER / LOGIN_PLATAFORMA
- Path: `src/testforge/SIFEC/TEST LOGIN/LOGIN USER/LOGIN_PLATAFORMA/`
- URL: `plataforma-des.caixa/`
- Data recording: **2026-07-06** (pós bundle fix)
- Duração: 59s
- Status: `incomplete_intent`, verdict `fail`
- Steps: **13** (6 passed, 4 failed, 3 skipped) — criteria 4/5
- Raw: 20 (4 nav, 2 click, 10 fill, 3 submit, 1 assert)
- steps.jsonl: **1** assert
- Diagnostic: 16 steps, 12/16 value_captured, selectors_immediate_ok/fail **0/14**, blind_spots 3

### R6b — SIFEC / TEST LOGIN / LOGIN USER / LOGIN_PLATAFORMA_2
- Path: `src/testforge/SIFEC/TEST LOGIN/LOGIN USER/LOGIN_PLATAFORMA_2/`
- Duração: 1m30s
- Steps: **26 (8 passed, 15 failed, 3 skipped)** — pior SIFEC
- Raw: 28 (7 nav, 9 click, 5 fill, 4 submit, 3 assert)
- steps.jsonl: **3** asserts
- Contém: matrícula `c891000`, password `Caixa123` (dicionário + dígitos)
- Falhas incluem: 5x `#next` reused, 3x `#tf-btn-*` overlay contamination, 3x role=button com nome concatenado (`RecolhidoMFEs em desenv. (SICCR)`, `Portabilidade INSS`, `Crédito Consignado`)

### R6c — SIFEC / TEST LOGIN / LOGIN USER / PLATAFORMA-DES-_Usu_rio_gerente_-_teste_MFE
- Path: `src/testforge/SIFEC/TEST LOGIN/LOGIN USER/PLATAFORMA-DES-_Usu_rio_gerente_-_teste_MFE/`
- Nome recording SANITIZADO — original tinha acento em "Usuário" + hífen + espaços → substituído por `_`
- Duração: 1m15s
- Steps: 17 (7 passed, 6 failed, 4 skipped)
- steps.jsonl: **1** assert
- Failures: URL drift, `#next`, `#btnBuscaAvancada`, 2x `#tf-btn-*`

### R6d — SIFEC / TEST LOGIN / LOGIN USER / TEST_1
- Path: `src/testforge/SIFEC/TEST LOGIN/LOGIN USER/TEST_1/`
- Data recording: **2026-07-03** (schema 4, mais antigo)
- URL: `login.des.caixa/auth/.../auth?response_type=code&client_id=cli-web-fec` (Keycloak SSO OIDC completa em base_url)
- Duração: 2m03s
- Status: `intent_complete`, verdict `not_evaluated` (compile não rodado)
- Raw: 23 (3 nav, 5 click, 10 fill, 4 submit, 1 assert)
- steps.jsonl: **1** assert
- Contém: password **6 tentativas com typos**: `Lpais0`, `Lpais03`, `Lpais03` (click 2x), `Lapsi`, `Lapsi3` — QA digitou senha errada 3+ vezes até acertar
- Assert final: `span "Nome de usuário ou senha inválida." visible` — QA testou LOGIN INVÁLIDO

### R5a — SIFAP / Autenticação / Deve logar no SIFAP com perfil de internet
- Path: `src/testforge/SIFAP/Autenticação/Deve logar no SIFAP com perfil de internet/REC-20260702-144218/`
- URL: `sifap-frontend-internet-v2-des.apps.nprd.caixa/`
- Sistema: **Programa Farmácia Popular CAIXA** (SIFAP)
- Data recording: **2026-07-02**
- Duração: 27s
- Status: `intent_complete`, verdict `not_evaluated`
- Raw events: 17 (6 nav, 4 click, 4 fill, **1 postback**, 1 submit, 1 assert)
- steps.jsonl: **1** assert
- value_mutations: 5
- Contém: CPF pessoal QA `934.765.700-02` como username, password `112233` (6 dígitos sequenciais)

### R5b — SIFAP / Autenticação / Deve logar no SIFAP com perfil de intranet (Gestor)
- Path: `src/testforge/SIFAP/Autenticação/Deve logar no SIFAP com perfil de intranet (Gestor)/REC-20260702-144459/`
- URL: `sifap-front-v2-tqs.apps.nprd.caixa/` (ambiente TQS diferente do R5a que é DES)
- Duração: 21s
- Raw events: 11 (4 nav, 4 click, 2 fill, 1 assert)
- steps.jsonl: **1** assert
- value_mutations: 2
- Contém: matrícula `c891011` (mesmo QA de R1/R4b), password `Sifap101` (mesmo)
- Assert target: `div.container-fluid` — captura container inteiro da página (título + labels + selects)

### R4b — Portal de Massa / Solicitações / Deve realizar uma solicitação de massa ao sistema SIISO
- Path: `src/testforge/Portal de Massa/Solicitações/.../REC-20260702-145924/`
- URL: `sinop-portaldemassa-frontend-des.apps.nprd.caixa/` (mesmo domínio R1)
- Rec ID: `REC-20260702-145924`
- Duração: 39s
- Status: `intent_complete`, verdict `not_evaluated`
- Raw events: **28** (7 nav, 9 click, 10 fill, 1 submit, 1 assert)
- steps.jsonl: **1** (só assert)
- value_mutations: 9
- Contém: username `c891011\t ` (com tab literal), password `Sifap101` (mesmo QA que R1)

### R3 — PLATAFORMA DES / Cliente conta CEF crédito do benefício / CPF com zero a esquerda / Valida_zeros_a_esquerda
- Path: `src/testforge/PLATAFORMA DES/Cliente conta CEF crédito do benefício/CPF com zero a esquerda/Valida_zeros_a_esquerda/`
- URL: `plataforma-des.caixa/` (mesmo domínio da R2)
- Framework detectado: **null** (idem R2)
- Duração: 2m32s (18:11→18:14)
- Status: `incomplete_intent`, verdict `fail`
- Steps totais: **39 (9 passed, 25 failed, 5 skipped)** — pior recording da série
- Assert hit rate: **0.1667** (1/6 asserts)
- Raw events: 49 (8 nav, 9 click, 18 fill, 8 submit, 6 assert)
- **value_mutations: 90** (~5x amplification vs 18 fills)
- steps.jsonl: **6** (só asserts)
- Diagnostic steps: 41
- selectors_immediate_ok/fail: **0 / 37**
- blind_spots: 5
- Healing: DESATIVADO
- Contém dados sensíveis reais: CPF `019.493.184-60`, nome `MANUEL M PINTO`, endereço, email, telefone (BUG-REC-23)

---

## Bugs encontrados

### BUG-REC-01 — crit: `steps.jsonl` publica apenas asserts, não clicks/fills
- **Encontrado em**: R1 e R2 (ambos)
- **Sintoma**: R1 tem 26 raw_events mas `steps.jsonl` tem 1 linha. R2 tem 27 raw_events mas `steps.jsonl` tem 2 linhas. Em ambos, todas as linhas são `action=assert`.
- **Evidência**:
  ```
  R1: wc -l steps.jsonl → 1; jq -r .action steps.jsonl → assert
  R2: wc -l steps.jsonl → 2; jq -r .action steps.jsonl → assert,assert
  R1: diagnostic/steps.jsonl → 19 linhas
  R2: diagnostic/steps.jsonl → 22 linhas
  ```
- **Causa provável**: publisher/normalizer/overlay grava apenas eventos marcados manualmente via Shift+A (assert) em `steps.jsonl`. Clicks/fills automáticos ficam só em raw_events e diagnostic. Compile principal lê `steps.jsonl` → recebe só asserts isolados sem contexto.
- **Impact**: compile gera teste vazio (só assert final). Todo trabalho de captura vira 1 linha executável. Impossível ter run-incremental útil.
- **Prioridade**: **P0** — blocker pra compile funcionar em qualquer recording real que não seja assert-only.

### BUG-REC-02 — crit: overlay do próprio TestForge sendo gravado como step do usuário
- **Encontrado em**: R2
- **Sintoma**: Steps 17, 19, 22 clicam em `#tf-btn-assert` e `#tf-btn-stop`. Isso são botões do OVERLAY do TestForge — não da aplicação testada. Recorder capturando próprio UI como se fosse ação do QA.
- **Evidência**:
  ```
  Step 17: click #tf-btn-assert — não encontrado no DOM (obviamente — só existe durante gravação)
  Step 19: click #tf-btn-assert
  Step 22: click #tf-btn-stop
  submission_report.failures inclui essas 3 falhas
  ```
- **Causa provável**: `overlay_inject.js` injeta elementos com id `tf-*` no DOM. Event listener global captura clicks nesses elementos. Precisa filtro para ignorar elementos com prefix `tf-` / classe `__tf-*` / dentro do container do overlay.
- **Impact**: (a) recording contamina com steps inutilizáveis; (b) run reporta falso-positivo — 3 failures que não são bugs da aplicação; (c) confunde QA que vê "erro" quando na verdade foi ação sobre próprio TestForge.
- **Prioridade**: **P0** — corrompe recording independente do sistema testado.

### BUG-REC-03 — crit: healing desabilitado por default em run-incremental
- **Encontrado em**: R2
- **Sintoma**: 11 failures reportam "Healing desativado". `total_healings: 0`. `healings_tentados: 0`.
- **Evidência**:
  ```
  submission_report.failures:
    "Step 2 (click): failed — Healing desativado. Erro: ..."
    "Step 11 (click): failed — Healing desativado. Erro: ..."
    (11 ocorrências)
  metrics.json: total_healings: 0, healings_tentados: 0
  ```
- **Causa provável**: run-incremental exige flag `--enable-healing`. Default OFF. Fere propósito do produto — self-healing é o diferencial.
- **Impact**: user rodou vezes achando que healing tá quebrado, mas nem foi tentado. Métricas de assert_hit_rate ficam artificialmente baixas — não reflete capacidade real.
- **Prioridade**: **P0** — default deve ser healing ON. Flag para desativar (`--no-healing`), não pra ativar.

### BUG-REC-04 — crit: `selectors_immediate_fail: 20/20` (R2), 9/9 (R1)
- **Encontrado em**: R1 e R2
- **Sintoma**: Diagnostic gera N selectors, todos falham no replay check batched. R1: 9/9 fail. R2: 20/20 fail.
- **Evidência**:
  ```
  R1: diagnostic/session.json totals: selectors_immediate_ok: 0, selectors_immediate_fail: 9
  R2: diagnostic/session.json totals: selectors_immediate_ok: 0, selectors_immediate_fail: 20
  ```
- **Causa provável**: replay batched testa selectors contra DOM final (última URL). Selectors foram gerados para elementos que existiam em telas intermediárias (páginas anteriores, modais fechados). DOM final não tem esses elementos. Batched-at-end perde contexto por step.
- **Impact**: diagnostic report sempre reporta zero cobertura. Métrica de "immediate_ok" inútil como sinal. Não valida qualidade dos selectors capturados durante gravação.
- **Prioridade**: **P0** — invalida diagnostic mode. Precisa replay step-by-step com URL do momento da captura, não batched final.

### BUG-REC-05 — crit: framework detection retorna null em site Angular óbvio (R2)
- **Encontrado em**: R2 (plataforma-des.caixa)
- **Sintoma**: `framework_detection.angular_version: null`, `primary: null`, `dom_size: null`. R1 detecta Angular 16.2.12 corretamente. Ambos são apps Angular.
- **Evidência**:
  ```
  R2: diagnostic/session.json framework_detection = {"angular_version": null, "angular_material": false, "primefaces": false, "mui": false, ..., "primary": null, "dom_size": null, "custom_components": null}
  R1: diagnostic/session.json framework_detection = {"angular_version": "16.2.12", "primary": "angular", "dom_size": 185}
  ```
- **Causa provável**: `framework_detector.py` roda em timing errado — talvez antes de Angular bootstrapear na R2 (login SSO redirect + delay). Ou snapshot capturado em tela intermediária vazia. R1 gravou tela `/listar-massa` populated; R2 gravou muito rápido antes do Angular carregar.
- **Impact**: sem framework detection, diagnostic não escolhe estratégias específicas (Material, Angular directives, ngx components). Blind spot no downstream.
- **Prioridade**: **P0** — precisa retry framework detection quando DOM population atinge threshold. Ou detect defer + retry.

### BUG-REC-06 — high: credenciais + CPF plaintext em raw_events e test_data.json sem mascaramento
- **Encontrado em**: R1 e R2
- **Sintoma R1**: `raw_events.jsonl` contém fill username `c891011` (matrícula) e password `Sifap101` (senha plaintext).
- **Sintoma R2**: `test_data.json` contém CPF `31702667804` com `sensitive_alerts` marcado mas `masking_applied: false`, policy `alert_only`. Password `c897998` em raw_events.
- **Evidência**:
  ```
  R1 raw_events.jsonl evt_00004: fill input#username value="c891011"
  R1 raw_events.jsonl evt_00006: fill input#password value="Sifap101"
  R2 raw_events.jsonl evt_00005-07: fill username "c89","c8979","c897998" (3 events)
  R2 raw_events.jsonl evt_00009-11: fill password "c89","c8979","c897998" (mesma senha que user!)
  R2 test_data.json: inputsearchcpfcnpj: "31702667804" policy=alert_only masking_applied=false
  R2 test_data.json sensitive_alerts marcado mas masking_applied FALSE
  ```
- **Causa provável**: (a) recorder não detecta `type=password` → não mascara em raw_events. (b) matrícula `c\d+` padrão CAIXA não reconhecido como sensível. (c) `alert_only` policy não faz nada além de flag — ignora policy.
- **Impact**: **compliance crítico**. Recording exportado (bundle, zip, git push) vaza credenciais reais de QA. Sistema testa aplicações bancárias — não pode vazar. LGPD + política interna CAIXA violada.
- **Prioridade**: **P0** — bug de segurança. Mascarar antes de escrever em disco. Nunca gravar plaintext em raw_events.jsonl para type=password.

### BUG-REC-07 — high: fill event emitido por cada burst de typing em vez de valor final
- **Encontrado em**: R2
- **Sintoma**: `fill username`: 3 events com values `c89`, `c8979`, `c897998`. Mesma coisa `password`. Deveria ser 1 fill final por campo.
- **Evidência**:
  ```
  R2 evt_00005: fill input#username value="c89"
  R2 evt_00006: fill input#username value="c8979"
  R2 evt_00007: fill input#username value="c897998"
  ```
- **Causa provável**: recorder emit fill em cada `input` event (JS) ou snapshot periódico sem debounce por fingerprint. Fase 6 (Sprint Q attribute) devia ter debounce 800ms — não pegou aqui, ou reset a cada snapshot.
- **Impact**: (a) infla raw_events; (b) IR precisa dedupar depois; (c) qualquer downstream que usa "último fill" precisa cuidar; (d) telemetry inflacionada.
- **Prioridade**: **P1** — dedup deveria ter pego. Precisa audit no pipeline emit fill.

### BUG-REC-08 — high: URL drift false-positive quando URLs são idênticas
- **Encontrado em**: R2 (Step 2)
- **Sintoma**: Failure message mostra `url before='<X>' after='<X>'` com strings **idênticas** mas reporta drift.
- **Evidência**:
  ```
  R2 Step 2 (click): failed — Healing desativado. Erro:
    url before='https://login.des.caixa/auth/...cli-web-pnc...code_challenge_method=S256'
    after='https://login.des.caixa/auth/...cli-web-pnc...code_challenge_method=S256'
  ```
- **Causa provável**: drift checker compara URL objects/normalized paths de maneiras diferentes, ou compara `page.url` post-click vs recorded_url mas ambos foram capturados no mesmo estado sem diff real. Bug lógico.
- **Impact**: false-positive drift → healing desperdiça ciclos, ou (como no R2) falha por drift que não existe.
- **Prioridade**: **P1** — corrige lógica compare. Deve normalizar antes de comparar.

### BUG-REC-09 — high: `#next` como seletor genérico reused em wizard multi-step
- **Encontrado em**: R2
- **Sintoma**: Steps 11, 14, 16, 21 todos usam seletor `#next`. Cada um é botão "Próximo" em página diferente do wizard. ID é volátil/genérico — recorder trata como primary.
- **Evidência**:
  ```
  R2 submission_report.failures:
    "Step 11 (click): Elemento '#next' nao encontrado no DOM"
    "Step 14 (click): Elemento '#next' nao encontrado no DOM"
    "Step 16 (click): Elemento '#next' nao encontrado no DOM"
    "Step 21 (click): Elemento '#next' nao encontrado no DOM"
  ```
- **Causa provável**: compiler emitiu `#next` como seletor primary. Angular reusa mesmo ID em múltiplas rotas. Recorder captura ID como stable identifier — deveria demote IDs reusados/genéricos (semelhante a `mat-input-N` já implementado).
- **Impact**: sem healing, todo `#next` falha em replay. Com healing, healing precisa curar 4 vezes mesmo seletor.
- **Prioridade**: **P1** — extensão do padrão demote de IDs voláteis. Adicionar `#next`, `#submit`, `#save`, `#continue`, `#cancel` a blacklist de "IDs genéricos".

### BUG-REC-10 — high: Assert sem valor esperado aceito pelo overlay (Step 20 R2)
- **Encontrado em**: R2
- **Sintoma**: Step 20 é assert com target=input vazio, sem expected_value. Falha em runtime com "assert sem valor esperado".
- **Evidência**:
  ```
  R2 evt_00025: assert target=input, expected_value="" ou null
  R2 submission_report.failures:
    "Step 20 (assert): failed — assert sem valor esperado"
  ```
- **Causa provável**: overlay accept Shift+A em qualquer elemento sem validar. Deveria: se elemento é input sem value visível, mostrar prompt "Qual o valor esperado?" ao invés de gravar assert vazio.
- **Impact**: recording com asserts inválidos que sempre falham. Métrica assert_hit_rate zero por asserts mal-formados.
- **Prioridade**: **P1** — overlay validation antes de aceitar assert.

### BUG-REC-11 — high: gherkin/scenario.feature confunde placeholder/label com nome de botão
- **Encontrado em**: R1
- **Sintoma**: `scenario.feature` gera:
  ```
  E clico no botao "c999999"                            # c999999 é PLACEHOLDER do input username
  E preencho "c999999" com valor                        # perde valor real
  E clico no botao "Em qual Projeto ou Demanda..."      # pergunta virou botão
  E preencho "Atenção: Essa massa de testes..." com valor  # heading virou input target
  ```
- **Causa provável**: `gherkin_writer.py` extrai `target.text` ou `target.placeholder` sem checar tag. Confunde `input.placeholder` com nome amigável. "Com valor" genérico esconde valor real ao invés de mostrar.
- **Impact**: cenário BDD ilegível. Impossível user validar intent. Impossível expert dev derivar spec da gravação.
- **Prioridade**: **P1** — reescrita gherkin writer com semântica por tag. Mostrar valor concreto quando disponível.

### BUG-REC-12 — med: value_mutation dedup vaza com `name=""` vazio
- **Encontrado em**: R1
- **Sintoma**: `input#[name=]  value=t` aparece 3x no `value_mutations.jsonl` (fingerprint idêntico).
- **Evidência**:
  ```
  R1 value_mutations.jsonl:
    {"fingerprint":"input#[name=]","value":"t"} (3x)
    {"fingerprint":"input#[name=]","value":""} (1x)
  ```
- **Causa provável**: hotfix22 dedup key collision (commit `fd4dbd9`) inclui placeholder + accessible_name pra distinguir. Aqui `name=""` E provavelmente placeholder ausente E accessible_name vazio → colide.
- **Impact**: value_mutations infla, IR precisa dedupar posteriormente, valores autocomplete perdidos.
- **Prioridade**: **P2** — extensão do dedup incluir tag path + parent element hint quando outros fields vazios.

### BUG-REC-13 — med: confidence heurística instável em suggested_assertions
- **Encontrado em**: R1
- **Sintoma**: `evt_00011` modal aparecendo tem confidence 0.2 (subestimado). `evt_00006` password appeared 0.2 (correto, senha em DOM não é intent). Regra não pesa semântica de key.
- **Evidência**:
  ```
  R1 suggested_assertions.jsonl:
    evt_00006 changes=[{appeared, INPUT:password, "Sifap101"}] confidence=0.2 (OK)
    evt_00010 changes=[15+ cards apareceram] confidence=1.0 (OK)
    evt_00011 changes=[{appeared, h3#modal-title:Inclusão de Pessoa Física...}] confidence=0.2 (subestimado — modal é intent forte)
    evt_00012 confidence 1.0 (16+ appeared, tela nova)
    evt_00025 confidence 1.0 (result page)
  ```
- **Causa provável**: heurística conta N de `appeared/disappeared` sem semântica. Não sabe que `h3#modal-title` é forte marker. Bag-of-elements em vez de rule-based.
- **Impact**: assertions sugeridas com baixa confidence perdidas ou não promovidas. QA ignora sugestão que era boa.
- **Prioridade**: **P2** — enrich confidence com rule-based semantic weights (`role=dialog`, `[modal-title]`, `[success-message]`, URL delta forte).

### BUG-REC-14 — med: autocomplete Angular quebrado em 2 events desconexos
- **Encontrado em**: R1 (evt_00010/00011) e R2 (evt_00002, evt_00014)
- **Sintoma**: user digita `t` em input search, resultados aparecem, user clica card. Recorder emit `fill t` + `click card`. Intent real é "buscar por 't' e escolher X" — 2 events perdem esse acoplamento.
- **Evidência**:
  ```
  R1 evt_00010: fill input value="t" (buscar)
  R1 evt_00011: click article "Pessoa/Cliente SICLI/SIISO..." (escolher resultado)
  R2 evt_00002 e evt_00014: fill input value="t" em 2 URLs diferentes
  ```
- **Causa provável**: recorder não tem detector de "search result selection". Compile gera 2 steps independentes. Replay executa fill+click sem esperar dropdown popular.
- **Impact**: replay flaky — click em card antes de resultado renderizar. Handler específico Autocomplete Angular ausente.
- **Prioridade**: **P2** — precisa handler pattern `search+select` no `component_patterns.yaml`. Detecta fill em campo com role=combobox/search + click em resultado dropdown → group.

### BUG-REC-15 — med: healing_report.md vazio quando run tem 0 healings
- **Encontrado em**: R2
- **Sintoma**: healing_report.md contém apenas:
  ```
  # TestForge Healing Report
  - Validados: 0
  - Rejeitados: 0
  ```
- **Causa provável**: quando healing off ou 0 tentativas, template gera relatório mínimo sem diagnóstico do porque não healed.
- **Impact**: user sem contexto pra entender "por que 11 falhas mas 0 healings tentados". Deveria mostrar "Healing desativado (flag `--enable-healing` ausente)" no report.
- **Prioridade**: **P3** — output verboso quando healing off. Mostrar razão + comando pra ativar.

### BUG-REC-16 — med: submission_report.steps.total=22, mas raw_events só tem 27 e steps.jsonl só 2
- **Encontrado em**: R2
- **Sintoma**: `submission_report.steps: {total: 22, passed: 6, healed: 0, failed: 11, blocked: 0, skipped: 5}`. Number "22" veio do compile — não bate com o que `steps.jsonl` mostra (2).
- **Evidência**: consistência entre report e steps.jsonl não existe.
- **Causa provável**: compile lê de `diagnostic/steps.jsonl` (22) ou reconstrói de raw_events. Report reflete compile output. `steps.jsonl` principal é dead artifact ou usado por compile diferente. Confuso qual fonte de verdade.
- **Impact**: dev não sabe qual arquivo confiar. Bug hunting fica cego pela ambiguidade.
- **Prioridade**: **P3** — clarificar pipeline: doc oficial de "quem escreve steps.jsonl principal" + garantir compile alinha com ele.

### BUG-REC-17 — low: `Portal de Massa.zip` no repo sem análise
- **Encontrado em**: raiz `src/testforge/`
- **Sintoma**: arquivo `Portal de Massa.zip` sem extração/análise. Terceiro bundle não processado.
- **Prioridade**: **P4** — deve extrair e analisar para completar cobertura CAIXA (3 recordings, não 2).

### BUG-REC-19 — crit: máscara CPF gera value_mutation por char + duplicata 3-4x mesmo timestamp
- **Encontrado em**: R3
- **Sintoma**: usuário digitou CPF `019.493.184-60`. Value_mutations tem 90 linhas para 18 fills (~5x amplification). Cada value aparece 3-4x com timestamp idêntico.
- **Evidência**:
  ```
  R3 value_mutations.jsonl (timestamp 18:12:33.368Z 3 ocorrências idênticas):
    {fp: "input#inputSearchCpfCnpj[name=]", value: "0"} (3x)
    {fp: "input#inputSearchCpfCnpj[name=]", value: "0"} (mais 1x, +0.001s)
  
  Sequência para "01":
    ts 18:12:34.036Z x4 (3 duplicatas exatas + 1 relacionado NIS)
  
  Sequência para "019.4" mostra confusão:
    "019.4", "0194" (não formatado), "019.4" alternando
  ```
- **Causa provável**: MutationObserver ou input event listener dispara múltiplas vezes por keystroke — capture-phase, bubble-phase, framework Angular double-emit via ngModel/formControl, e possivelmente listeners duplicados de sessão anterior. Máscara Angular re-formata → gera 2ª mutation → segunda leitura formatada vs não formatada.
- **Impact**: (a) infla artifacts 5-10x; (b) IR precisa dedupar; (c) telemetry inflada; (d) máscara timing bug pode causar picking valor não formatado.
- **Prioridade**: **P0** — mais grave que BUG-REC-07 (fill burst), pois é CADA char digitado, e o campo é CPF/mask input crítico.

### BUG-REC-20 — high: assert com valor genérico "visible" ao invés de conteúdo esperado
- **Encontrado em**: R3
- **Sintoma**: 4 asserts com `value = "visible"`:
  ```
  R3 evt_00020: assert label "CPF / CNPJ" value=visible
  R3 evt_00023: assert a "Next" value=visible
  R3 evt_00038: assert button "Consultar" value=visible
  R3 evt_00048: assert div "MANUEL M PINTO..." value=visible
  ```
- **Causa provável**: overlay assert flow — usuário escolheu tipo "state" ou "visible" mas overlay grava literal string "visible" em vez de definir `expected_state: visible` estruturado.
- **Impact**: compile gera `expect(loc).to_have_text("visible")` — óbvio falso. Deveria emitir `expect(loc).to_be_visible()`.
- **Prioridade**: **P1** — quebra semântica de asserts. Overlay assert flow precisa saída estruturada.

### BUG-REC-21 — high: value_mutation snapshot pega state completo do form (campos não digitados)
- **Encontrado em**: R3
- **Sintoma**: cada mutation em `inputSearchCpfCnpj` traz junto `inputSearchNis` com value="" — 2 fingerprints emitidos por tick, mesmo que só um mudou.
- **Evidência**:
  ```
  R3 value_mutations pattern:
    {fp: "input#inputSearchCpfCnpj[name=]", v: "0"}
    {fp: "input#inputSearchNis[name=]", v: ""}  ← nunca digitou aqui
  (par se repete a cada mutation do CPF)
  ```
- **Causa provável**: value_mutation collector emit snapshot de TODO o formulário a cada tick em vez de diff. Não usa MutationObserver.attributeFilter ou similar. Ou inspeção periódica de queryselectorall.
- **Impact**: NIS field sempre vazio mas emit N vezes. Falso sinal de "campo alterado". IR precisa filtrar. Perf hit.
- **Prioridade**: **P1** — value_mutation deveria ser diff, não snapshot total.

### BUG-REC-22 — med: metadata suite/test_case não bate com hierarquia do path
- **Encontrado em**: R3
- **Sintoma**: 
  ```
  Path físico: PLATAFORMA DES / Cliente conta CEF crédito do benefício / CPF com zero a esquerda / Valida_zeros_a_esquerda
  Metadata JSON: system="PLATAFORMA DES", suite="Cliente conta CEF crédito do benefício", test_case="CPF com zero a esquerda"
  ```
  Path tem 4 níveis, metadata usa 3. Nível "Valida_zeros_a_esquerda" (folder do recording) não aparece em metadata como field próprio.
- **Causa provável**: pipeline de captura de taxonomy suporta 3 níveis (system/suite/test_case) mas usuário organizou em 4 (system/subsystem/suite/test). Falta suporte a subsystem ou test_scenario.
- **Impact**: relatórios agrupam errado. Test cases distintos "CPF com zero a esquerda" em suites diferentes viram um só se metadata só olha 3 níveis.
- **Prioridade**: **P2** — adicionar `scenario` ou `test_scenario` field opcional, ou detectar profundidade real do path.

### BUG-REC-23 — crit: PII de cliente real (CPF, nome, endereço, email) em plaintext nos asserts
- **Encontrado em**: R3
- **Sintoma**: `steps.jsonl` e `raw_events.jsonl` contêm dados reais de cliente CAIXA:
  ```
  R3 evt_00035 assert value="019.493.184-60"  (CPF real do titular)
  R3 evt_00044 fill "R 36, S/N -  - NORTE AGUAS CLARAS - BRAS"  (endereço)
  R3 evt_00045 fill "email@gmail.com"  (email)
  R3 evt_00046 fill "(61)99623-9901"  (telefone)
  R3 evt_00048 assert value="MANUEL M PINTO CPF: 019.493.184-60 NIS: 000.00000..."  (nome + CPF + NIS)
  ```
- **Causa provável**: recorder não detecta padrões PII no valor de fills nem em texto de assert target. Nenhuma anonimização.
- **Impact**: **compliance BLOCKER**. Sistema testa aplicações bancárias reais com CPF, nome e endereço em produção-espelho DES. Recording exportável (bundle, zip, git) vaza dados de cliente. LGPD violation. Reg BCB violation.
- **Prioridade**: **P0** — MAIS URGENTE. Detector PII obrigatório antes de escrever qualquer artifact. Mask CPF (`###.###.###-##`), telefones (`(##)#####-####`), nomes (mais complexo — heurística tabela dominio DOM).

### BUG-REC-24 — crit: password fraca `Lapis03` (dicionário + 2 dígitos) do QA em plaintext (R3)
- **Encontrado em**: R3
- **Sintoma**: password `Lapis03` capturado em raw_events evt_00009-11 (typing burst: `L`, `Lapis`, `Lapis03`). Fraca por design + plaintext.
- **Prioridade**: **P0** — reforço BUG-REC-06 (credenciais plaintext). Password em campo `type=password` deveria ser SEMPRE masked em raw_events.

### BUG-REC-25 — high: timeout `wait_for` 3000ms fixo causa 5 falhas em cascata (R3)
- **Encontrado em**: R3
- **Sintoma**: Steps 20, 22, 34, 35, 36 falham com `Locator.wait_for: Timeout 3000ms exceeded`. Selectors `[formcontrolname="cpfCnpj"]` (2x) e `input[aria-label="elemento input somente leitura"]` (3x).
- **Causa provável**: (a) timeout hardcoded 3s no runner — Angular formcontrol carrega em tempo variável; (b) selector `[aria-label="elemento input somente leitura"]` genérico e provavelmente aria-label reused em N campos.
- **Impact**: recording com formulário Angular sempre flaky em run. 3s não suficiente pra hydration.
- **Prioridade**: **P1** — timeout adaptativo (`wait_for(load_state)` primeiro, depois `wait_for(visible)`), ou timeout config por sistema.

### BUG-REC-26 — high: `#next` reused em 6 steps (R3, mais grave que R2 que era 4)
- **Encontrado em**: R3
- **Sintoma**: Steps 13, 16, 21, 23, 26, 29 = 6 clicks em botões `#next` distintos em wizard multi-step, todos falham. Reforço BUG-REC-09.
- **Causa provável**: wizards com botão "Próximo" reusam `id="next"` em cada tela. Angular router mantém DOM mas ID sempre igual. IDs voláteis não detectados.
- **Impact**: qualquer wizard multi-step CAIXA quebra. Provavelmente pattern em MUITOS sistemas testados.
- **Prioridade**: **P1** — blacklist de IDs genéricos (`next`, `prev`, `back`, `submit`, `save`, `cancel`, `continue`) com demote automático.

### BUG-REC-27 — high: reforço `assert sem valor esperado` (R3 Step 25 idem R2)
- **Encontrado em**: R3
- **Sintoma**: idem BUG-REC-10. Overlay aceita Shift+A em qualquer elemento sem exigir expected_value.
- **Impact**: idem.
- **Prioridade**: **P1** — reforço, mesma correção.

### BUG-REC-28 — low: intent "verificar botão + clicar" gera 2 events desconexos
- **Encontrado em**: R3
- **Sintoma**: evt_00038 = `assert button "Consultar" visible` + evt_00041 = `submit button "Consultar"`. Usuário verifica se botão está visível antes de clicar. Recorder emite 2 events sem relacionar.
- **Causa provável**: sem detector "wait-then-act" ou "check-then-action" pattern.
- **Impact**: compile pode gerar 2 steps redundantes: assert + click. Ideal seria wait_visible + click atômico.
- **Prioridade**: **P3** — melhoria de intent aggregation.

### BUG-REC-29 — crit: CPF pessoal do QA digitado como matrícula/username, plaintext
- **Encontrado em**: R4a
- **Sintoma**: campo `username` de login CAIXA aceita CPF. QA digitou próprio CPF `539.867.177-49`. Capturado plaintext em raw_events.
- **Evidência**:
  ```
  R4a evt_00005: fill input#username value="539.867.177-49"
  ```
- **Causa provável**: field `type=text` sem detecção CPF regex, sem masking. BUG-REC-06 cobria password/matrícula c\d+; CPF do QA em login é fronteira nova.
- **Impact**: **compliance blocker duplo** — CPF do QA + credencial. Recording exportável vaza identidade real do usuário.
- **Prioridade**: **P0** — reforço compliance. CPF regex `\d{3}\.?\d{3}\.?\d{3}-?\d{2}` deve mascar em qualquer campo, especialmente `username`.

### BUG-REC-30 — crit: múltiplos CNPJs de terceiros vazando via `<select>` textContent
- **Encontrado em**: R4a
- **Sintoma**: `select#txtCnpj` (dropdown "Selecione o CNPJ") tem 13+ options com CNPJs distintos. Recorder captura `target.text` como concat de TODOS options: `"Selecione o CNPJ42.097.365/0001-2660.846.100/0001-6561.484.627/0001-5062.465.907/0001-8357.698.137/0001-8914.301.068/0001-1535.833.255/0001-1055.551.912/0001-4359.589.286/0001-3546.524.094/0001-0759.5..."`
- **Evidência**: R4a evt_00019/20/21 select_option target.text — 13 CNPJs de revendedores parceiros CAIXA em plaintext.
- **Causa provável**: recorder faz `element.textContent` no `<select>`. Native DOM API concatena texto de todos `<option>` filhos. Deveria capturar APENAS texto da option selecionada + placeholder da select.
- **Impact**: **compliance BLOCKER** — CNPJ de N empresas parceiras vazando por gravação. Dados de terceiros. Não é dado do QA — é dado corporativo protegido.
- **Prioridade**: **P0** — `target.text` de `<select>` deve ser apenas option selecionada, não `textContent` completo.

### BUG-REC-31 — high: URLs Keycloak com session/state/nonce em plaintext em raw_events + submission_report
- **Encontrado em**: R4a (postback), R2/R3 (failures)
- **Sintoma**: URLs Keycloak SSO contêm `execution`, `state`, `nonce`, `code_challenge`, `session_state`, `code` parameters — todos capturados plaintext.
- **Evidência**:
  ```
  R4a evt_00009 postback url: "https://logindes.caixa.gov.br/auth/realms/internet/login-actions/authenticate?execution=939b3be6-f791-489f-a749-a2a9dfcdaecd&client_id=cli-web-pbs&tab_id=18H0-IWSvPI"
  R2 Step 2 failure: URL com state, nonce, code_challenge
  R3 Step 2 failure: idem
  ```
- **Causa provável**: recorder captura `window.location.href` sem strip de query params sensíveis. Session state em URL Keycloak = OIDC auth flow marker.
- **Impact**: recording com Keycloak execution ID válido pode ser reused pra hijack se dentro da janela de expiração (~10 min). Vaza session state.
- **Prioridade**: **P1** — redact query params conhecidos Keycloak (`state`, `nonce`, `code`, `code_challenge`, `session_state`, `execution`) antes de escrever URL em qualquer artifact.

### BUG-REC-32 — crit: fill corrigido gera 2 fills consecutivos com valores diferentes
- **Encontrado em**: R4b
- **Sintoma**: QA colou URL por engano no campo `username`, depois clicou e digitou matrícula real. Recorder emit 2 fills:
  ```
  R4b evt_00004: fill input#username value="https://sinop-portaldemassa-frontend-des..." (colado por engano)
  R4b evt_00005: click input#username (limpou)
  R4b evt_00006: fill input#username value="c891011\t " (matrícula real + Tab autoblur)
  ```
- **Causa provável**: sem detecção "user backtracked" — fill em campo já preenchido deveria substituir, não append. Ou: value final é sempre `c891011\t `; mas value intermediário `https://...` foi capturado antes do clear.
- **Impact**: compile emit `page.fill(username, url)` seguido de `page.fill(username, matricula)` — no replay, primeiro fill quebra a lógica (input rejeita ou submit prematuro).
- **Prioridade**: **P0** — dedup fills sequenciais no MESMO campo mantendo apenas o último valor final. Ou: normalizer detecta "value diverge, latest wins".

### BUG-REC-33 — high: `postback` event type sem handler downstream
- **Encontrado em**: R4a
- **Sintoma**: raw_events tem `type=postback` (Keycloak form POST). Recorder detecta corretamente. Nenhum step semântico gerado.
- **Evidência**: R4a evt_00009 `{"type":"postback", "is_postback":true, "submit_method":"POST"}` — sem correspondente em steps.jsonl.
- **Causa provável**: schema 4 adicionou `postback` type no recorder. Publisher/normalizer não sabe traduzir para semantic action. Compile pula.
- **Impact**: transição SSO (login → app) perdida. Replay não emula postback → estado pós-login não reproduzível.
- **Prioridade**: **P1** — handler `postback` no normalizer: emit step `wait_for_navigation()` ou `expect(page).to_have_url(after_url)`.

### BUG-REC-34 — high: 15 clicks em setinhas de calendar sem detecção pattern
- **Encontrado em**: R4a
- **Sintoma**: user navegou calendar `‹` (prev) 7x, `›` (next) 6x, click `1` e `30` para range de datas. Gerou 15 clicks distintos em raw_events. Sem intent aggregation.
- **Evidência**:
  ```
  R4a evt_00023-00038: 6x click "›", 7x click "‹", 2x click span dia
  ```
- **Causa provável**: sem detector "calendar interaction" pattern. Cada click vira step. Padrão hotfix22 conhecido de calendar Material cascade — mesmo problema aqui em calendar customizado.
- **Impact**: 15 steps fragile. Um erro de posicionamento no replay = 15 clicks divergentes. Compile emit script inviável.
- **Prioridade**: **P1** — handler pattern `date_range_picker` → aggregate multi-click em intent único `select_date_range(start, end)`.

### BUG-REC-35 — crit: password `134679` (PIN 6 dígitos, só numérico) plaintext R4a
- **Encontrado em**: R4a
- **Sintoma**: `fill input#password value="134679"` — PIN 6 dígitos numéricos. Provavelmente token de segundo fator ou senha de sistema legado interno.
- **Prioridade**: **P0** — reforço BUG-REC-06/24. Todo `type=password` mascarado independente de content, mas PIN em plaintext = risco imediato.

### BUG-REC-37 — crit: 2º CPF pessoal de QA diferente vazando plaintext
- **Encontrado em**: R5a
- **Sintoma**: username `934.765.700-02` (CPF diferente do R4a `539.867.177-49`). QA distinto.
- **Evidência**: R5a evt_00005 fill input#username value="934.765.700-02"
- **Impact**: reforça BUG-REC-29 — múltiplos QAs vazando CPFs pessoais. **Padrão sistemático**, não caso isolado.
- **Prioridade**: **P0** (reforço).

### BUG-REC-38 — crit: password `112233` (6 dígitos sequenciais, weak) plaintext R5a
- **Encontrado em**: R5a
- **Sintoma**: `fill input#password value="112233"` — password extremamente fraca (dígitos sequenciais).
- **Impact**: reforço BUG-REC-06/24/35. Vazando password que provavelmente é reused em ambiente DES corporativo. Bruteforce trivial se leaked.
- **Prioridade**: **P0** (reforço).

### BUG-REC-39 — high: Keycloak `execution` ID **idêntico** entre 2 recordings distintos
- **Encontrado em**: R4a + R5a
- **Sintoma**: postback URL contém `execution=939b3be6-f791-489f-a749-a2a9dfcdaecd` em ambos recordings:
  ```
  R4a evt_00009 (17:53:07Z) execution=939b3be6-f791-489f-a749-a2a9dfcdaecd&client_id=cli-web-pbs
  R5a evt_00010 (17:42:27Z) execution=939b3be6-f791-489f-a749-a2a9dfcdaecd&client_id=cli-web-fap
  ```
  Mesmo GUID em recordings em sistemas diferentes (Portal de Massa vs SIFAP). Timestamps distintos.
- **Causa confirmada**: grep `939b3be6` em `src/testforge/` retornou **zero** hits (só aparece nos recordings capturados + DOM snapshots gravados). Portanto é hipótese (c): **Keycloak DES CAIXA reusa `execution` GUID** entre sessions/clients. Não é bug TestForge.
- **Reclassificação**: **NÃO É BUG TESTFORGE** — é config bug do ambiente Keycloak DES CAIXA. Reportar separado para time infra CAIXA.
- **Ação recomendada**: (a) reportar Keycloak DES para time infra; (b) TestForge deveria detectar `execution` param e alertar QA ("Keycloak reusing execution IDs — session risk").
- **Prioridade**: **P4** (não é bug TestForge) — mas serve como sinal de que TestForge deveria ter **detector de padrões suspeitos em URL** (session ID reused, execution repeated, etc).

### BUG-REC-40 — high: assert captura container inteiro da página (`div.container-fluid`)
- **Encontrado em**: R5b, R5a
- **Sintoma**: assert target `div.container-fluid` com text=`"Farmácia Popular Consultar farmácia por: CNPJ Situação Lista recolhida Selecione a situação desejadaUnidade Federativa (UF) Lista recolhida Selecione a UF desejada"`. Texto vira concatenação de TODO o conteúdo do container (títulos, labels, placeholders de selects).
- **Evidência**: R5b steps.jsonl step_0001 css_path=`.container-fluid`, expected_value inclui título + 3 seções.
- **Causa provável**: overlay assert flow — usuário clicou pra assertar Shift+A perto do topo, pegou o container wrapper. `.textContent` propaga tudo dentro.
- **Impact**: assert extremamente fragile — qualquer mudança em label/placeholder do form quebra. Reforço direto do **BUG-014 ARCHIVE** ("Assertions finais frágeis e acopladas ao DOM completo") — ainda ocorre 3 semanas após catalogação.
- **Prioridade**: **P1** — overlay deveria (a) sugerir elemento mais específico quando target é container genérico (h1, label, botão); (b) alertar QA "assert em container = frágil" antes de aceitar.

### BUG-REC-41 — med: value_mutation vazio duplicado mesmo timestamp (padrão persistente)
- **Encontrado em**: R5a e R5b
- **Sintoma**: 
  ```
  R5a value_mutations: {ts:"17:42:30.606Z", fp:"input#[name=]", v:""} 2x idênticos
  R5b value_mutations: {ts:"17:45:08.677Z", fp:"input#[name=]", v:""} 2x idênticos
  ```
- **Causa provável**: reforço BUG-REC-19/21 — snapshot polling + Angular double-emit + name="" collision. Aparece em CADA recording analisado.
- **Prioridade**: **P2** — mesma correção BUG-REC-19.

### BUG-REC-42 — high: password `paste: true` flag detectado mas ainda plaintext
- **Encontrado em**: R4a
- **Sintoma**: `raw_events evt_00012` password fill tem `paste: true` (recorder detecta que valor foi COLADO via clipboard, não digitado). Value `134679` capturado plaintext apesar disso.
- **Evidência**: R4a evt_00012 target: `{tag:"input", type:"password", inputmode:"numeric", maxlength:"8"}` value=`"134679"` paste=`true`.
- **Causa provável**: recorder detecta paste event mas não usa flag para redação. `paste=true` deveria ser sinal FORTE pra masking, especialmente em `type=password`.
- **Impact**: reforço BUG-REC-06 mas com sinal explícito ignorado. Recorder sabe que é sensível, mas não masca.
- **Prioridade**: **P0** — se `type=password` OR `paste=true` OR `inputmode=numeric` + maxlength <=8 → masking imediato.

### BUG-REC-88 — high: recordings com `incomplete_intent` movidos automaticamente para `recordings_failed/` sem alerta claro ao QA
- **Encontrado em**: R11
- **Sintoma**: quando compile detecta `status: incomplete_intent`, recording é movido de `recordings/<id>` → `recordings_failed/<id>_<timestamp>`. FAILED_MARKER.json indica origem.
- **Causa provável**: pipeline automatizado tenta manter `recordings/` limpo. Move pra failed. Cria versão nova timestamp.
- **Impact**: 
  - (a) QA regrava do zero em vez de iterar sobre failed (viola `no-regrave`)
  - (b) recordings_failed acumula → confusão sobre "qual é o canonical"
  - (c) sem CLI `testforge recover-failed <id>` óbvia
- **Prioridade**: **P1** — precisa fluxo: (1) move para failed; (2) mostrar mensagem "recording X incomplete — para retomar: `testforge fix-recording <path>`"; (3) `fix-recording` deveria permitir iteração (adicionar assert, curar step, etc) sem gravar de novo.

### BUG-REC-89 — high: FAILED_MARKER vaza Windows local path `C:\Desenvolvimento\AUTOMATA-PRIMUS\...`
- **Encontrado em**: R11 (todos 3)
- **Sintoma**: 
  ```
  "source_dir": "C:\\Desenvolvimento\\AUTOMATA-PRIMUS\\recordings\\as_de_sexta"
  ```
  Path Windows absoluto. Revela:
  - QA usa Windows
  - Projeto interno CAIXA chamado **AUTOMATA-PRIMUS** (parent do TestForge?)
  - Estrutura de dev local
- **Impact**: 
  - (a) compliance: leak nome projeto interno
  - (b) cross-platform break: JSON tem backslash literal (reforço REC-36)
  - (c) sanitizar: relative path baseado em recording dir ao invés de absolute
- **Prioridade**: **P1** — FAILED_MARKER deveria armazenar apenas nome relativo do recording, não absolute path.

### BUG-REC-90 — high: **duplicação entre recordings_failed E simax.zip** (mesmo recording_id)
- **Encontrado em**: R11 + R9
- **Sintoma**: 
  ```
  recordings_failed/as_de_sexta_20260703-202821 (failed 2026-07-03)
    ↔ simax/suite exploratoria/todas as massagens/as_de_sexta (ok, exported to zip)
  
  Similar para massageria e nova_massagem.
  ```
  Ambos com mesma taxonomy `system=simax, suite=suite exploratoria, test_case=todas as massagens`.
- **Causa provável**: user gravou → falhou (moved to failed com timestamp) → gravou de novo (persisted em recordings) → exported to simax.zip.
- **Impact**: análise conta 2x o mesmo teste. Storage duplicado. Sem link entre versões.
- **Prioridade**: **P2** — recording metadata deveria ter `previous_attempt_id` linkando pra failed anterior. Analytics agregada por `test_case_hash`.

### BUG-REC-91 — med: recordings_failed sem README/docs orientando QA
- **Encontrado em**: R11
- **Sintoma**: pasta `recordings_failed/` só contém as gravações movidas + FAILED_MARKER.json. Sem README explicando: "por que estes recordings estão aqui?", "como recuperar?", "como iterar?", "posso deletar?".
- **Impact**: user encontra pasta e não sabe o que fazer.
- **Prioridade**: **P3** — criar `recordings_failed/README.md` explicando fluxo + CLI comandos.

### BUG-REC-92 — med: recordings movidos mantêm todos artifacts (ax_snapshots, dom_snapshots, _pilot_runs) — storage bloat
- **Encontrado em**: R11
- **Sintoma**: cada recording_failed mantém pastas completas (ax_snapshots, dom_snapshots, _pilot_runs, _pilot_tmp). Se pipeline falhou cedo, alguns pastas podem estar vazias, mas outros com centenas de arquivos.
- **Causa provável**: move recursive sem prune.
- **Impact**: storage cresce; git commit desses arquivos = repo bloat.
- **Prioridade**: **P3** — antes de move, prune artifacts derivados (dom_snapshots pesados). Manter apenas raw_events + steps + metadata para debugging.

### BUG-REC-79 — crit: 12 recordings SEM taxonomy (system/suite/test_case ausentes)
- **Encontrado em**: R10 (uncategorized)
- **Sintoma**: metadata destas gravações antigas tem apenas `recording_id`, `application`, `base_url`, `status`. Faltam `system`, `suite`, `test_case`.
- **Causa provável**: schema evoluiu 2026-06-27+ adicionando taxonomy fields. Recordings anteriores ficaram órfãos.
- **Impact**: 12 recordings valiosos (dados reais, sistemas variados) fora do reporting/agregação por taxonomy. QA não achou → viraram "uncategorized".
- **Prioridade**: **P0** — migração retroativa: script analisa `base_url` + `recording_id` → sugere `system/suite/test_case`. Alerta user pra revisar antes de commit.

### BUG-REC-80 — high: `application` field ambíguo (às vezes "web", às vezes nome do sistema)
- **Encontrado em**: R10
- **Sintoma**: 
  ```
  teste_inicial: application="web"
  verifica_regrecao: application="SIOPI"
  deve_logar_no_sifap: application="web"
  ```
- **Causa provável**: no schema antigo `application` era pro tipo (web/mobile). User confundiu e escreveu nome do sistema em algumas gravações.
- **Impact**: parsing/aggregation não pode confiar no field. Precisa fallback pra outros signals.
- **Prioridade**: **P2** — depreciar `application` ou renomear pra `application_type`, com validation enum.

### BUG-REC-81 — high: statuses deprecated (`needs_review`, `ready_for_team`, `completed`) sem doc
- **Encontrado em**: R10
- **Sintoma**: schema antigo tinha statuses ricos:
  - `completed`, `completed_raw`, `intent_complete` — success variantes
  - `needs_review`, `ready_for_team` — human-in-loop
  - `incomplete_intent` — failure
- Statuses novos (schema 4): `intent_complete`, `incomplete_intent` só. Perda semântica.
- **Impact**: recording `needs_review` era gate manual — QA marcava "preciso revisar". Perdemos essa signal.
- **Prioridade**: **P2** — decidir: (a) restaurar `needs_review` como opcional; (b) documentar depreciação; (c) migrar recordings antigos para statuses novos.

### BUG-REC-82 — high: **regravações refinadas** violando `no-regrave` (padrão sistêmico)
- **Encontrado em**: R10 → R5a, R8, R9
- **Sintoma**: user regravou os mesmos testes com melhor taxonomia:
  ```
  uncategorized/deve_logar_no_sifap (raw=45, 20 failures) 
    → SIFAP/Autenticação/R5a (raw=17, muito mais limpo)
  uncategorized/deve_fazer_upload_sisgh_2
    → SISGH/UPLOAD_ARQUIVO/deve_fazer_upload_sisgh_3 (R8)
  uncategorized/deve_marcar_horario (+ _2)
    → SIMAX/marcação de consulta (R9)
  ```
- **Análise dupla**: (a) **positivo**: user iterou convergindo pra recording melhor; (b) **negativo**: viola contrato `[[feedback-no-regrave]]`. Falta ferramenta que promova iteração via `compile + run` sobre existing.
- **Prioridade**: **P1** — CLI `testforge migrate <old_rec> <new_taxonomy>` deveria facilitar migração de metadata sem regravar. Alternativa: `testforge re-record <old_rec> --resume-from=step_N` pra re-gravar só o step problemático.

### BUG-REC-83 — crit: `deve_logar_no_sifap` (uncategorized, 2026-06-26): **20 failed / 39 steps**
- **Encontrado em**: R10 deve_logar_no_sifap
- **Sintoma**: submission_report:
  ```
  steps: {total: 39, passed: 1, failed: 20, blocked: 0, skipped: 18}
  ```
  1 passed, 20 failed. Login flow desintegrado.
- **Comparação**: mesmo teste regravado em R5a (2026-07-02) resultou em 17 raw events + verdict `not_evaluated`. Sistema melhorou 2.6x em 6 dias — mas old recording ainda sofrendo.
- **Impact**: **user vê old recording e conclui "produto ruim"**. Sem alerta "recording gerado por versão obsoleta — regravar recomendado".
- **Prioridade**: **P1** — quando run detecta rec com schema=null, banner: "Este recording foi criado antes de fixes X/Y/Z. Considere regravar (link para docs)".

### BUG-REC-84 — med: criteria_passed `3/5` recorrente em failures
- **Encontrado em**: R10 (deve_logar_no_sifap, verifica_regrecao)
- **Sintoma**: `verdict: fail` mas `criteria_passed: 3/5`. Quais 2 critérios falharam?
- **Causa provável**: 5-criteria ReadinessGate documentado em `CLAUDE.md`. Uncategorized recordings falharam em 2 critérios específicos (provavelmente "sem asserts" + "sem taxonomy"). Submission não detalha quais.
- **Impact**: user não sabe o que corrigir. Verdict binário sem breakdown.
- **Prioridade**: **P2** — submission_report deve incluir `criteria: {gate_name: passed/failed/skipped}` detalhado.

### BUG-REC-85 — med: schema=null (sem versionamento) impossibilita migração automática
- **Encontrado em**: R10 (todas 12)
- **Sintoma**: `fingerprint.capture_schema_version: null`.
- **Impact**: reader não pode fazer branch por versão. Bugs corrigidos assumindo schema 4 podem quebrar em schema null (KeyError silencioso).
- **Prioridade**: **P2** — treat `null` como schema 0. Adicionar migration reader que popula fields ausentes com defaults sensatos.

### BUG-REC-86 — high: `verifica_regrecao` gravado em **PRODUÇÃO SIOPI** com `application: SIOPI`
- **Encontrado em**: R10 verifica_regrecao
- **Sintoma**: `base_url: simuladorhabitacao.caixa.gov.br/home` — **PRODUÇÃO REAL** (idem R7a/b).
- Reforço BUG-REC-59: recording em produção sem alerta.
- Também: `application: SIOPI` (não "web") — user tinha noção que era sistema SIOPI mas gravou em prod.
- **Prioridade**: **P1** (reforço REC-59).

### BUG-REC-87 — low: `recording_id` (schema antigo) vs `test_case` (schema novo) — nomenclatura mudou
- **Encontrado em**: R10 vs outros
- **Sintoma**: schema antigo persiste `recording_id` como slug. Schema novo usa `system/suite/test_case` triplet.
- **Impact**: código legacy que lê `recording_id` quebra em schema 4 (ou vira `test_case`).
- **Prioridade**: **P3** — alias reader que mapeia `recording_id` → `test_case` em backward compat.

### BUG-REC-69 — high: **BUG-001 ARCHIVE parcialmente shipped** — `select_option` type OK mas text concatena all options
- **Encontrado em**: R9 SIMAX (20 recordings)
- **Sintoma**:
  ```
  R9 evt_00006: {type:"select_option", target.tag:"select", element_id:"lstUf", 
                  target.label:"UF",
                  target.text:"Selecione AL AM CE DF ES GO MA MG MS MT PA PB PE P...",
                  value:"0"}
  R9 evt_00007: {type:"select_option", ..., value:"DF"}
  R9 evt_00010: {..., element_id:"lstEdificio", 
                  target.text:"Selecione CNP BRASIL - BRASILIA/DF (17º andar - Al..."}
  R9 evt_00014: {..., element_id:"lstData",
                  target.text:"Selecione 03/07/2026 (sexta-feira) 06/07/2026 (seg..."}
  ```
- **Status memory**: `2b151d5 fix(select): bugs 11-16 — SELECT recording and playback`. Recorder AGORA emite `type=select_option` corretamente. **Fix parcial** — captura tipo mas `target.text` ainda concatena todas options (REC-30 family).
- **Impact**: (a) locator estratégias que usam `has-text` pegam texto poluído; (b) recording com 20 selects vaza N opções (edifícios internos, datas disponíveis, UFs) — dados operacionais.
- **Prioridade**: **P1 (REGRESSÃO parcial BUG-001)** — extração `target.text` para `<select>` deve ser: apenas placeholder + option selecionada.

### BUG-REC-70 — high: 3-5 `select_option` events consecutivos por 1 escolha do usuário
- **Encontrado em**: R9 SIMAX
- **Sintoma**: 
  ```
  segunda evt_00006-08: select_option lstUf value=0, DF, DF (3 events)
  deve_ter evt_00006-10: select_option lstUf value=0, DF, DF, DF, DF (5 events!)
  ```
  User escolhe "DF" uma vez → recorder emit 3-5 events.
- **Causa provável**: 3 events do change lifecycle: mousedown=0 (default) → mouseup=DF → change=DF. 5 events em deve_ter sugere Angular ngModel + formControl double emit.
- **Impact**: value_mutations e select_options infladas. Compile pode emit `select_option()` 3-5 vezes para o mesmo select. Se runner respeita, tempo x3-x5.
- **Prioridade**: **P1** — dedup select_option consecutivos no mesmo element com mesmo value final. Keep last-with-value only.

### BUG-REC-71 — high: recordings duplicados "segunda" e "sexta" com raw/vm counts idênticos
- **Encontrado em**: R9 SIMAX (segunda, sexta, busca_de_massagem_em_brasilia + `_2` + `_2_2`, busca_de_vaga_na_matriz_2/3/4, massageria + nova_massagem + as_de_sexta + massageria_20260703-204921)
- **Sintoma**: 20 recordings SIMAX quase todos raw=18 vm=5. User regravou 3-4x o mesmo teste (BUG-005 ARCHIVE relacionado).
- **Causa provável**: user grava, testa, quebra, regrava. Falta detector "esse teste é igual ao existente — deseja substituir?". User accumula gravações redundantes.
- **Impact**: N recordings quase idênticos, storage/git bloat, análise mais difícil.
- **Prioridade**: **P2** — recorder pode calcular hash de sequence de raw events + oferecer merge/replace/skip ao QA.

### BUG-REC-72 — high: mesmo botão `Novo agendamento` capturado com/sem element_id em recordings diferentes
- **Encontrado em**: R9 SIMAX
- **Sintoma**: 
  ```
  segunda evt_00004: click button element_id="btnNovoAgendamento" text="Novo agendamento"
  deve_ter evt_00004: click button text="Novo agendamento"  (SEM element_id)
  ```
- **Causa provável**: recorder inconsistent — timing/state dependent. DOM podia estar em transição em uma captura vs outra.
- **Impact**: compile gera selectors diferentes para mesmo botão em recordings diferentes → healing precisa curar mesmo caso 2x.
- **Prioridade**: **P2** — recorder deveria retry pequeno se atributos ausentes na 1ª leitura. Sanity check "id ou role obrigatório antes de commit event".

### BUG-REC-73 — med: `fill input value="t"` sem target identifier em TODOS 20 recordings SIMAX
- **Encontrado em**: R9 SIMAX (todos 20)
- **Sintoma**: evt_00002 (após 1ª navigation) sempre é `fill input value="t"` sem name/id.
- **Causa provável**: user hábito de digitar "t" em search após load da tela. OU auto-typing pattern em app. Preserved em TODAS recordings.
- **Impact**: **dead fill** — não corresponde a intent útil. Compile emit fill sem target válido → falha ou timing bug.
- **Prioridade**: **P3** — normalizer detecta "fill sem target identifier" em posição inicial pós-load → skip como noise ou promote a `search` intent.

### BUG-REC-74 — high: assert em `tr:nth-of-type(N) > td:nth-of-type(M)` com N alto (14, 17, 21)
- **Encontrado em**: R9 SIMAX
- **Sintoma**: 
  ```
  segunda: css_path="tr:nth-of-type(17) > td:nth-of-type(3)" expected="Reservado"
  segunda_feira_sem_massagem: "tr:nth-of-type(21) > td:nth-of-type(2)" expected="Reservado"
  deve_ter: "tr:nth-of-type(14) > td:nth-of-type(1)" expected="14:20"
  ```
  Assert em linha 14/17/21 de tabela sem identificador temporal (data, hora).
- **Causa provável**: user clicou pra assertar valor em célula de tabela de horários. Overlay generator não achou id/aria melhor.
- **Impact**: se linha add/remove (novo horário disponível/reservado), N muda, assert quebra. Reforço direto BUG-012 ARCHIVE + REC-57.
- **Prioridade**: **P1** — assert generator deveria buscar row-level identifier (data-time, [data-datetime]) OR usar `has_text` do valor esperado como filter.

### BUG-REC-75 — med: 3+ recordings duplicados (regravações incrementais `_2`, `_3`, `_4`, `_2_2`)
- **Encontrado em**: R9 SIMAX
- **Sintoma**: `busca_de_massagem_em_brasilia`, `_2`, `_2_2` — 3 recordings mesmo teste. `busca_de_vaga_na_matriz_2`, `_3`, `_4` — 3 recordings. `massageria`, `nova_massagem`, `as_de_sexta`, `massageria_20260703-204921` — 4 variantes.
- **Causa provável**: BUG-005 ARCHIVE ("sessões anexadas") aparentemente foi shipped, mas mudou pra "criar sufixo incremental". User tem hábito de regravar em vez de iterar sobre existente (viola contrato `no-regrave`).
- **Impact**: acumula recordings redundantes. Difícil saber qual é canonical.
- **Prioridade**: **P3** — offer "you have 3 recordings for this test_case, delete old?" ao criar novo.

### BUG-REC-76 — med: 2 padrões de sufixo diferentes (`_2` vs `_YYYYMMDD-HHMMSS`)
- **Encontrado em**: R9 SIMAX
- **Sintoma**: 
  - `busca_de_massagem_em_brasilia_2` (sufixo incremental)
  - `massageria_20260703-204921` (sufixo timestamp)
  Dois padrões conflitantes usados no mesmo sistema/suite.
- **Causa provável**: 2 code paths distintos criando IDs de recording. Ou versões de recorder que mudaram convention.
- **Impact**: parsing/sorting recordings vira ad-hoc.
- **Prioridade**: **P3** — unificar convention. Sugerido: sempre `<name>_<YYYYMMDD-HHMMSS>` para gravações do mesmo teste, ou sempre `_2/_3/_N`.

### BUG-REC-77 — med: caracteres especiais em test_case sanitizados agressivamente (perda info)
- **Encontrado em**: R9 SIMAX
- **Sintoma**: 
  ```
  "terça" → ter_a  (em ter_a_tamb_m_n_o_tem_massagem)
  "terça" → terc_a (em agendar_na_terc_a)
  "horário" → hor_rio (em deve_ter_hor_rio_as_13_na_quinta)
  "quinta" → quista (typo QA preservado!)
  ```
  **Duas convenções diferentes** de sanitize para "ç": `_a` e `c_a`. Typos do QA preservados sem alertar.
- **Impact**: nomes ilegíveis, perda de contexto. Taxonomy fragmenta (mesmo teste em 2 nomes se sanitizado differentemente).
- **Prioridade**: **P3** — normalizar: `ç → c`, `á → a`, `ã → a`, `õ → o`. Rejeitar typo/nome suspeito com pergunta "test_case '{name}' parece typo — confirmar?".

### BUG-REC-78 — low: assert `Reservar visible` (button) mistura ação com estado
- **Encontrado em**: R9 SIMAX deve_ter step_0002
- **Sintoma**: `assert button "Reservar" value="visible"` — reforço direto REC-20 (assert value="visible" literal).
- **Prioridade**: **P1** (reforço REC-20).

### BUG-REC-60 — crit: file input capturado como `fill` com valor `C:\fakepath\...` (browser security prefix)
- **Encontrado em**: R8 (SISGH)
- **Sintoma**: 
  ```
  R8 evt_00017 fill target: {tag:"input", element_id:"files", type:"file"}
     value: "C:\\fakepath\\CNT.EMP.MZ.BMX0.PRONAMPE.D260625.R4"
     file_upload: [{name: "CNT.EMP.MZ.BMX0.PRONAMPE.D260625.R4", size: 546, type: ""}]
  ```
- **Causa provável**: browser retorna literal `C:\fakepath\<filename>` como `.value` em `input[type=file]` por segurança. Recorder captura como fill event normal.
- **Impact**: compile emit `page.fill(loc, "C:\\fakepath\\...")` — Playwright REJEITA fill em file inputs. Correto seria `page.set_input_files(loc, path)`.
- **Metadata correta existe**: `file_upload: [{name, size, type}]` — recorder sabe que é file input, mas compile ignora.
- **Prioridade**: **P0** — normalizer detecta `type=file` OR presença de `file_upload` metadata → emit `set_input_files` step ao invés de fill.

### BUG-REC-61 — high: nome de arquivo real corporativo vazando (naming convention interna)
- **Encontrado em**: R8
- **Sintoma**: filename `CNT.EMP.MZ.BMX0.PRONAMPE.D260625.R4` — formato COBOL-era CAIXA:
  - `CNT.EMP` = Contrato Empresa
  - `MZ.BMX0` = ambiente/tipo
  - `PRONAMPE` = programa governo (Pequenas Empresas)
  - `D260625` = data 26/06/2025
- **Impact**: leak revela: (a) naming convention interna; (b) programas ativos (PRONAMPE); (c) datas de arquivos reais; (d) estrutura de deploy da CAIXA. Reforço BUG-REC-23 (PII) mas para dados corporativos.
- **Prioridade**: **P1** — sanitizar filenames em recordings? Trade-off vs. reprodutibilidade. Mínimo: alertar QA "arquivo com nome real capturado" durante compile.

### BUG-REC-62 — crit: password `01Bola01` (dicionário + palíndromo dígitos) + `paste=true` ignorado (reforço REC-42)
- **Encontrado em**: R8
- **Sintoma**: `fill password value="01Bola01" paste=true`. Senha weak + flag paste detectada.
- **Prioridade**: **P0** (reforço REC-06/42).

### BUG-REC-63 — crit: **4ª matrícula QA distinta** (c892018) vazando plaintext
- **Encontrado em**: R8
- **Sintoma**: matrícula `c892018` em fill username. Combinado com recordings anteriores:
  ```
  QA #1: c891011  (R1, R4b, R5b)
  QA #2: c891000  (R6b)
  QA #3: c897998  (R2)
  QA #4: c892018  (R8)
  QA #5+: CPFs pessoais 934.765.700-02 (R5a), 539.867.177-49 (R4a)
  ```
- **Impact**: **6 identidades distintas** vazando em 14 recordings. Mapeamento QA → atividade → sistema testável é trivial. Timeline reconstruível.
- **Prioridade**: **P0** (reforço REC-06/24/29/37).

### BUG-REC-64 — med: metadata `system: SISGH` diverge de `page_title: Sistema de Gestão de Honras`
- **Encontrado em**: R8
- **Sintoma**: taxonomy usa `SISGH` mas app oficial `Sistema de Gestão de Honras` = **SGH**. Confusão user naming.
- **Impact**: baixo — só bagunça reporting. Diferentes recordings do mesmo sistema real podem cair em taxonomies diferentes.
- **Prioridade**: **P3** — cross-check metadata.system com page_title primeiro run e alertar divergência.

### BUG-REC-65 — high: **REFORÇO** — `<script>` como target.text de div (2ª ocorrência)
- **Encontrado em**: R8 (SISGH) + R6d (SIFEC)
- **Sintoma**: 
  ```
  R8 evt_00005 click div text="Login TQS - INTRANET var onSubmit = function(){ do..."
  R6d evt_00013 click div text="Login DES - INTRANET SIFEC var onSubmit = function"
  ```
  Ambos em páginas de login CAIXA legacy (DES + TQS). Ambos capturam `<script>` inline como parte de div.text.
- **Causa dupla**:
  - **Bug de app CAIXA**: legacy login pages têm `<script>` visível/não filtrado do textContent
  - **Bug de recorder**: `.textContent` DOM API inclui children `<script>`. Deveria filtrar.
- **Prioridade**: **P1** — recorder deveria strip `<script>`/`<style>` children ao computar target.text. Fix single-source (recorder side).

### BUG-REC-66 — high: label do file input não visible causa timeout 3000ms
- **Encontrado em**: R8
- **Sintoma**: `Step 16 (fill): Locator.wait_for: Timeout 3000ms exceeded. Call log: waiting for locator("label[for=\"files\"]").first to be visible`
- **Causa provável**: pattern Angular Material comum — `<input type=file id="files" hidden>` + `<label for="files">` styled como botão. Recorder capturou click no LABEL. Runner tenta `wait_for visible` no label. Se label tem CSS display específico, timeout.
- **Impact**: file upload UI patterns sempre quebram no replay.
- **Prioridade**: **P1** — handler `file_upload` component pattern deveria usar `page.set_input_files(input#files, path)` diretamente, ignorando o label.

### BUG-REC-67 — med: `role=menuitem` inferido incorretamente
- **Encontrado em**: R8 Step 13
- **Sintoma**: selector gerado `role=menuitem[name="Explorador"]` mas elemento não existe no DOM.
- **Causa provável**: elemento é `<a>` ou `<button>` num dropdown/menu, recorder assumiu role=menuitem por contexto (dentro de nav?). Sem verificação real ARIA.
- **Impact**: false positive role inference. Selector inválido.
- **Prioridade**: **P2** — role inference deveria consultar computed role (via ax_snapshot), não estrutura.

### BUG-REC-68 — low: seletores mirando `.mat-button-wrapper` interno (posicional fragile)
- **Encontrado em**: R8 Steps 12, 17
- **Sintoma**: `button:nth-of-type(2) > .mat-button-wrapper` e `.botao > .mat-button-wrapper`. Mira span interno do Angular Material button.
- **Causa provável**: recorder pegou child ao invés do button pai. Material button estrutura: `<button class="mat-button"><span class="mat-button-wrapper">TEXT</span></button>`.
- **Impact**: selector frágil — se Material rebuild interno, quebra.
- **Prioridade**: **P3** — normalizer detecta `.mat-button-wrapper` filho e promove pro `<button>` ancestral.

### BUG-REC-51 — crit: currency mask R$ typing gera 13+ mutations pra 1 valor
- **Encontrado em**: R7a, R7b (SIOPI)
- **Sintoma**: user digita `1000` no campo currency. Value_mutations sequence:
  ```
  R7a mat-input-1: " 0,00 " → " 0,00 1" → " 0,01 " → " 0,010 " → " 0,10 " → " 0,100 " → 
                   " 1,00 " → " 1,000 " → " 10,00 " → " 10,000 " → " 100,00 " → 
                   " 100,000 " → " 1.000,00 "
  ```
  **13 mutations pra 1 valor final**. Máscara reformata a cada tick. Cada char digitado gera 2 emits (raw + reformatted).
- **Impact**: value_mutations gigante (85 linhas R7b vs 29 raw events — ~3x). Storage bloat + IR precisa dedupar. **Pior amplification já visto** (13x > REC-19 CPF 5x).
- **Prioridade**: **P0** — mesma família REC-07/19/48. Currency mask é worst case.

### BUG-REC-52 — crit: `mat-input-N` fingerprint reused entre calculadoras (memory hotfix22 regressão)
- **Encontrado em**: R7a, R7b
- **Sintoma**: value_mutations usa `input#mat-input-0[name=]` e `input#mat-input-1[name=]` como fingerprint principal. Em R7b (3 calculadoras diferentes), mesmos IDs reused.
- **Referência memory**: `[[project-hotfix22-session-2026-07-01]]` cita commit `966f3bc` para "demote mat-input-N dynamic ids". Fix aparentemente shipped mas ainda usado como primary fingerprint.
- **Evidência**: `wc -l` value_mutations R7b = 85 linhas, sempre `mat-input-N`. Não há promotion pra placeholder/accessible_name.
- **Prioridade**: **P0 (regressão)** — verificar se `966f3bc` afetou fingerprint fill ou value_mutation. Value_mutation collector precisa mesma demote logic.

### BUG-REC-53 — crit: currency value com espaços leading/trailing em fill event
- **Encontrado em**: R7a, R7b
- **Sintoma**: fill values incluem espaços:
  ```
  R7a evt_00014: fill value=" 1.000,00 "
  R7b evt_00013: fill value=" 10.000,00 "
  R7b evt_00018: fill value=" 0,15 "
  R7b evt_00027: fill value=" 1.000.000,00 "
  ```
- **Causa provável**: máscara Angular currency emit `" 1.000,00 "` com padding. Recorder captura `.value` direto sem strip.
- **Impact**: compile emit `page.fill(loc, " 1.000,00 ")` com espaços. Máscara pode rejeitar (parser não aceita leading space) → replay quebra.
- **Prioridade**: **P0** — `.strip()` em currency values antes de escrever raw_events + steps. Mesmo tratamento para date masks.

### BUG-REC-54 — crit: **REGRESSÃO CONFIRMADA** — `DD/MM/AAAA` placeholder capturado como value
- **Encontrado em**: R7a, R7b
- **Sintoma**: value_mutations linha 6 R7a:
  ```
  {fp: "input#mat-input-0[name=]", v: "DD/MM/AAAA"}
  ```
  `DD/MM/AAAA` é placeholder do date input Material, capturado como value real.
- **Referência memory**: `[[project-hotfix22-session-2026-07-01]]` cita commit `f1c1881 fix(overlay): Angular date input mask detection — skip placeholder DD/MM/AAAA`.
- **Conclusão**: fix `f1c1881` corrigiu **fill events** mas value_mutations collector ainda captura placeholder. **REGRESSÃO PARCIAL** — mesmo bug, path incompleto.
- **Prioridade**: **P0** — aplicar mesma skip logic em value_mutation collector.

### BUG-REC-55 — high: calendar Material navigation — 7 clicks span/button sem selector confiável
- **Encontrado em**: R7a evt_00005-11, R7b evt_00005-10
- **Sintoma**: user navegou date picker Material:
  ```
  R7a: click span → click button "JUL 2026" → click span → click span → click span "1984" → click span "JAN" → click span "3"
  R7b: click span → click button "JUL 2026" → click span → click span "1996" → click span "JAN" → click span "1"
  ```
  Maior parte `<span>` sem name/id/text. Recorder captura tag+text mas não gera selector confiável.
- **Referência memory**: `[[project-hotfix22-session-2026-07-01]]` documenta calendar cascade — text-first já implementado mas year_selector state ainda quebra em runtime.
- **Impact**: compile emit `page.locator("span").click()` = wildcard, quebra. Ou fallback nth-of-type = frágil ao rebuilding.
- **Prioridade**: **P1** — handler específico `mat_datepicker` component pattern: aggregate 7 clicks em `page.get_by_role('button', name='...').click()` + `fill_date(date_string)` atômico.

### BUG-REC-56 — high: currency fill precedido de click redundante no mesmo input
- **Encontrado em**: R7a, R7b (5 ocorrências)
- **Sintoma**: pattern `click input` → `fill input value` no mesmo elemento:
  ```
  R7a evt_00013 click input → evt_00014 fill " 1.000,00 "
  R7b evt_00012 click input → evt_00013 fill " 10.000,00 "
  R7b evt_00017 click input → evt_00018 fill " 0,15 "
  R7b evt_00023 click input → evt_00024 fill " 0,25 "
  R7b evt_00026 click input → evt_00027 fill " 1.000.000,00 "
  ```
- **Causa provável**: user clicou pra focus antes de digitar. Recorder emit ambos. Sem detector "focus-then-type" pattern.
- **Impact**: compile gera click + fill redundantes. Playwright `fill()` já foca automaticamente — click extra pode causar race condition ou re-trigger mask events.
- **Prioridade**: **P1** — normalizer detecta click sem action seguido de fill mesmo target = dedup pra fill only.

### BUG-REC-57 — high: assert css_path posicional `nth-of-type` idêntico para 2 asserts diferentes
- **Encontrado em**: R7b
- **Sintoma**: 
  ```
  R7b step_0001: expected=R$ 33.333,33  css_path="div:nth-of-type(1) > .text-size-smaller"
  R7b step_0002: expected=R$ 383.646,67 css_path="div:nth-of-type(3) > .text-size-smaller"
  R7b step_0003: expected=R$ 640.839,97 css_path="div:nth-of-type(3) > .text-size-smaller" ← MESMO PATH!
  ```
  step_0002 e step_0003 têm CSS idêntico mas valores diferentes. Impossível replay diferenciar.
- **Causa provável**: 3 calculadoras diferentes reusam mesmo template `.text-size-smaller`. Posição `nth-of-type` muda com scroll/rebuild. Sem identificador único (role, aria-label, id).
- **Referência ARCHIVE**: BUG-012 "Assertions frágeis por CSS estrutural" — ainda ocorre.
- **Impact**: replay assert #3 vai bater assert #2 primeiro (mesmo path) e usar valor errado. Test não distingue.
- **Prioridade**: **P1** — assert generator precisa fallback strategies: (a) accessible_name, (b) has_text ancestor, (c) role + text, (d) nth-of-type só se nada mais existir.

### BUG-REC-58 — med: `mat-icon` sem accessible_name gerado
- **Encontrado em**: R7b
- **Sintoma**: `evt_00022 click mat-icon text="home"` — Material icon com text "home".
- **Causa provável**: recorder captura tag+text OK, mas `<mat-icon>` sem `aria-label` = accessible_name vazio. Compile precisa emit `page.locator("mat-icon").filter(has_text="home")`.
- **Impact**: selector fragile (múltiplos mat-icon "home" possíveis).
- **Prioridade**: **P2** — handler `mat-icon` pattern com aria-label check.

### BUG-REC-59 — high: gravação em ambiente de **PRODUÇÃO** CAIXA (compliance blocker)
- **Encontrado em**: R7a, R7b
- **Sintoma**: base_url `simuladorhabitacao.caixa.gov.br/home` — **PRODUÇÃO REAL CAIXA GOV BR**, não DES/TQS/HOM.
- **Contraste**: outros 11 recordings usam ambientes internos (`-des.apps.nprd.caixa`, `plataforma-des.caixa`, `sinop-portaldemassa-frontend-des`).
- **Impact**: 
  - (a) qualquer dado real (cliente cadastrado, cotação real, taxa real) vaza em recording exportável;
  - (b) neste caso é simulação sem login → PII baixa, mas **policy** deve bloquear;
  - (c) recording contra prod pode gerar carga real na infra ou triggerar auditoria interna.
- **Prioridade**: **P1** — recorder deveria detectar domínios de produção conhecidos (`caixa.gov.br` sem sufixo `-des/-tqs`) e alertar: "Você está gravando em PRODUÇÃO — recomenda usar ambiente DES/TQS. Continuar?". Config `production_domains` blocklist.

### BUG-REC-44 — crit: password typing hell — 6 tentativas de senha (typos) todas plaintext
- **Encontrado em**: R6d (SIFEC TEST_1)
- **Sintoma**: QA digitou senha errada 3+ vezes antes de acertar. Recorder capturou TODAS as tentativas:
  ```
  R6d evt_00009: fill password value="Lpais0"      # typo
  R6d evt_00010: fill password value="Lpais03"     # typo
  R6d evt_00011: click password value="Lpais03"    # click (não fill)
  R6d evt_00012: click password value="Lpais03"    # click novamente
  R6d evt_00013: click div text="Login DES - INTRANET SIFEC var onSubmit..."
  R6d evt_00014: fill password value="Lapsi"       # backtrack completo
  R6d evt_00015: fill password value="Lapsi3"      # tentativa nova
  ```
- **Causa provável**: (a) recorder não detecta que field foi cleared entre attempts; (b) sem detecção "failed login retry" pattern; (c) sem sanity check "senha field digitada N vezes = pattern suspeito".
- **Impact**: **compliance catastrófico**. Senha correta E variações (typos que são padrões de dicionário) TODAS em plaintext. Se atacante tem recording, pode reconstruir senha real E testar variações típicas de digitação. Password `Lapsi3` E `Lpais03` são candidatos.
- **Prioridade**: **P0** — reforço BUG-REC-06 mas 10x pior. Qualquer `type=password` fill = mask total, sempre.

### BUG-REC-45 — crit: password `Caixa123` (dicionário CAIXA + dígitos) plaintext
- **Encontrado em**: R6b
- **Sintoma**: `fill input#password value="Caixa123"` — nome empresa + 123.
- **Impact**: reforço BUG-REC-06 + análise pattern. `Caixa123` = literal empresa. Se leaked, atacante testa `Caixa1`, `Caixa2024`, `caixa123`, etc. Padrão previsível.
- **Prioridade**: **P0** (reforço).

### BUG-REC-46 — high: recorder captura JavaScript source code como text de div
- **Encontrado em**: R6d
- **Sintoma**: `evt_00013 click target: div text="Login DES - INTRANET SIFEC var onSubmit = function..."` — user clicou em um div que continha `<script>` tag. Recorder capturou source JS como target.text.
- **Causa provável**: página SIFEC login DES tem `<script>` inline não escondido (bug da app **OU** recorder pegou `.textContent` que inclui script). Provavelmente combinação: app com CSP frouxo + recorder incluindo scripts em text.
- **Evidência adicional**: `dom_snapshots/evt_00013.html` provavelmente tem `<script>` visível.
- **Impact**: (a) se app: reportar time SIFEC; (b) se recorder: `target.text` deveria excluir children `<script>`/`<style>`. Recording tem JS source como parte de intent — compile pode gerar assert com JS code = quebra.
- **Prioridade**: **P1** — filtrar `<script>` e `<style>` em textContent extract. Reportar SIFEC se app tem script visível.

### BUG-REC-47 — high: role=button com nome concatenado (label + placeholder + text)
- **Encontrado em**: R6b
- **Sintoma**: 3 selectors falharam:
  ```
  R6b Step 12: role=button[name="RecolhidoMFEs em desenv. (SICCR)"]
  R6b Step 20: role=button[name="Portabilidade INSS"]
  R6b Step 22: role=button[name="Crédito Consignado"]
  ```
  Primeiro tem "Recolhido" (placeholder de select) + "MFEs em desenv. (SICCR)" (option text) concatenados como se fosse ONE button name.
- **Causa provável**: recorder gera role locator com `accessible_name` computed. Para `<select>` collapsed, accessible_name pega placeholder + selected option. Como no BUG-REC-30 (`<select>` textContent), mas com role.
- **Impact**: playwright `get_by_role('button', name=...)` não acha porque nome no DOM não bate. Selector inválido gerado.
- **Prioridade**: **P1** — mesma família BUG-REC-30. Sanitizar `accessible_name` computation pra `<select>`/`<button>` com dropdown.

### BUG-REC-48 — crit: username typing burst 6-7 fills para valor final "C89001" (R6d)
- **Encontrado em**: R6d
- **Sintoma**: 
  ```
  R6d evt_00004: fill username value="C"
  R6d evt_00005: fill username value="C899"   # typo (2 chars extras)
  R6d evt_00006: fill username value="C8"     # backspace apagou
  R6d evt_00007: fill username value="C890"
  R6d evt_00008: fill username value="C89001"
  R6d evt_00020: fill username value="C89001" # re-digitou após erro
  ```
  6 fills para 6 chars = 100% amplification.
- **Causa provável**: reforço BUG-REC-07 mas mais grave. Cada tecla emit fill event, sem debounce final por field.
- **Prioridade**: **P0** (reforço).

### BUG-REC-49 — high: assert em erro de app (mensagem de senha inválida) sem contexto
- **Encontrado em**: R6d
- **Sintoma**: `evt_00022 assert span "Nome de usuário ou senha inválida." value=visible` — QA gravou login inválido e assertou mensagem de erro.
- **Causa provável**: intent legítimo (testar "senha errada não loga") mas overlay não distingue "assert positivo (sucesso)" vs "assert negativo (erro)". Compile pode gerar teste com nome ambíguo.
- **Impact**: teste gerado sem clareza semântica. Também: mensagem "Nome de usuário ou senha inválida." é sinal que pode revelar existência de user (username enumeration).
- **Prioridade**: **P1** — overlay deveria classificar assert type: expected_success | expected_error | expected_state. Ajuda downstream compile.

### BUG-REC-50 — high: value_captured baixo mesmo com muitos fills (typing burst inflaciona missing)
- **Encontrado em**: R6a-d
- **Sintoma**: diagnostic totals:
  ```
  R6a: 12/16 = 75%
  R6b: 8/21 = 38%   ← pior
  R6c: 8/14 = 57%
  R6d: 14/20 = 70%
  ```
  R6b tem 21 diagnostic steps mas só 8 values captured. Typing burst gera N fills mas IR captura só último → outros ficam "missing".
- **Causa provável**: consequência combinada BUG-REC-07 (fill burst) + BUG-REC-19 (dedup vazando). Diagnostic conta cada fill como step; IR reconstrói apenas 1. Discrepância N vs 1.
- **Impact**: completeness reporting mostra "value_missing" quando na verdade valor foi capturado, só que dedup rejected.
- **Prioridade**: **P1** — align diagnostic value_captured com IR final (última wins).

### BUG-REC-43 — med: DOM snapshots com session_code diferentes entre eventos do mesmo login
- **Encontrado em**: R4a (via DOM snapshots)
- **Sintoma**: evt_00003 form action tem `session_code=dzZ92Z...`, evt_00012 tem `session_code=u9D5lvd...`. `execution` GUID mesmo, `session_code` diferente.
- **Impact**: cada snapshot HTML carrega credenciais de sessão Keycloak diferentes. Recording exportado tem N tokens de sessão vazando. Combinado com BUG-REC-31 (URLs plaintext), superfície de risco compliance.
- **Prioridade**: **P2** — sanitizer DOM snapshot deveria stripar `session_code`, `execution`, `session_state` de qualquer HTML antes de escrever.

### BUG-REC-36 — med: paths com backslash Windows em `dom_snapshot`/`ax_snapshot` fields
- **Encontrado em**: R4a
- **Sintoma**: `"dom_snapshot":"dom_snapshots\\evt_00019.html"`, `"ax_snapshot":"ax_snapshots\\evt_00019.json"` — backslash literal em JSON.
- **Causa provável**: `os.path.join` em Windows. Publisher escreveu paths com `\`. Cross-platform bug — Linux/macOS não conseguem `Read` esses paths (esperam `/`).
- **Impact**: reproduzir Windows recording em Linux/CI quebra Read de snapshot. Análise cross-platform impossível.
- **Prioridade**: **P2** — sempre `pathlib.PurePosixPath` ou `.replace('\\', '/')` antes de serializar para JSON.

### BUG-REC-18 — low: raw_events.jsonl mistura ordem cronológica (R2)
- **Encontrado em**: R2
- **Sintoma**: evt_00013 (navigation) → evt_00015 (navigation) → evt_00014 (fill). Ordem lexicográfica não bate com timestamp real.
- **Evidência**: raw_events lista evt_00013, 00015, 00014 nessa ordem.
- **Causa provável**: raw_events.jsonl ordenado por append order (async publish), não timestamp. commit `2eac52a` corrigiu isso pra normalizer mas raw_events ainda desordenado.
- **Impact**: análise manual do arquivo confusa. Consumers precisam re-ordenar.
- **Prioridade**: **P4** — sort by timestamp no flush final do recorder.

---

## Padrões sistêmicos observados

**A. Overlay TestForge auto-contamina recordings** (BUG-REC-02): elementos `tf-*` capturados como clicks do user. Precisa allowlist/blocklist de elementos próprios.

**B. Publisher/Steps.jsonl desacoplado do diagnostic** (BUG-REC-01, BUG-REC-16): fonte de verdade ambígua. `steps.jsonl` só assert; `diagnostic/steps.jsonl` tem tudo. Ambiguidade estrutural.

**C. Zero replay success em batched mode** (BUG-REC-04): 0/9 e 0/20. Modo inteiro inútil. Replay precisa contexto por step, não batched at end.

**D. Segurança de dados sensíveis fraca** (BUG-REC-06): raw_events plaintext + `alert_only` policy que não masca. Blocker compliance.

**E. Framework detection frágil em timing** (BUG-REC-05): mesmo domínio (CAIXA Angular) detecta em R1, não em R2. Falta retry/defer.

**F. Fill events sem debounce por fingerprint** (BUG-REC-07): typing burst gera N events em vez de 1 fill final.

**G. Assert overlay não valida antes de aceitar** (BUG-REC-10): Shift+A em qualquer elemento sem expected_value.

---

## Cross-check contra `.planning/ARCHIVE/BUGS.md` (BUG-001..BUG-018 catalogados em 2026-06-15)

**Mapeamento REC → ARCHIVE + status via git log**:

| REC | ARCHIVE relacionado | Commit fix conhecido | Status observado agora (2026-07-07) |
|---|---|---|---|
| REC-01 (steps.jsonl só assert) | BUG-003 (contagem divergente) | — | **PARCIAL/REGRESSÃO**: critério aceite era "CLI mostra separado" mas steps.jsonl principal ainda tem só asserts em R1/R2/R3 |
| REC-02 (overlay tf-* auto-injection) | novo em ARCHIVE | — | **NÃO CATALOGADO ANTES** — provavelmente introduzido com Fase 7 bug detection modal + botões overlay |
| REC-03 (healing default OFF) | novo em ARCHIVE | — | **NÃO CATALOGADO** — mudança de default provavelmente propositada mas custo alto |
| REC-04 (batched replay 0%) | BUG-011 (métricas healing) parcial | — | **AINDA ABERTO** — diagnostic mode ainda reporta 0% em todos 3 recordings |
| REC-05 (framework detection null R2/R3) | novo em ARCHIVE | — | **NÃO CATALOGADO** — apenas R1 detecta Angular; R2 e R3 (mesmo domínio) falham |
| REC-06 (credenciais plaintext) | novo em ARCHIVE | — | **NÃO CATALOGADO** — blocker compliance |
| REC-07 (fill burst) | **BUG-008** (digitação vira dezenas de fills) | `2796c80 fix(Bug9): fill dedup — DOM-indexed fallback` | **REGRESSÃO/FIX INCOMPLETO** — critério aceite era "único fill final por debounce". Ainda ocorre em R2 (`c89→c8979→c897998`) e R3 (`L→Lapis→Lapis03`, `019.4→0194→019.4` etc) |
| REC-08 (URL drift false-positive) | novo em ARCHIVE | — | **NÃO CATALOGADO** |
| REC-09 (#next seletor genérico) | BUG-010 (healer genéricos) relacionado | — | **AINDA ABERTO** — 4 ocorrências R2, **6 ocorrências R3** |
| REC-10 (assert sem valor esperado) | novo em ARCHIVE | — | **NÃO CATALOGADO** — overlay assert flow lack validation |
| REC-11 (gherkin confuso) | novo em ARCHIVE | — | **NÃO CATALOGADO** |
| REC-12 (dedup vaza `name=""`) | BUG-008 relacionado | fd4dbd9 `fix: dedup key collision inclui placeholder+accessible_name` | **PARCIAL** — quando placeholder E accessible_name vazios, ainda colide |
| REC-13 (confidence heurística) | BUG-011 parcial | — | **AINDA ABERTO** |
| REC-14 (autocomplete Angular quebrado) | novo em ARCHIVE | — | **NÃO CATALOGADO** |
| REC-15 (healing_report vazio) | BUG-011 parcial | — | **AINDA ABERTO** |
| REC-16 (steps.jsonl vs report ambiguity) | BUG-003 parcial | — | **AINDA ABERTO** |
| REC-17 (Portal Massa zip pending) | — | — | tarefa 24 |
| REC-18 (raw_events order) | BUG-004 (event_id reinicia) parcial | — | **PARCIAL** — commit `2eac52a` corrigiu ordem para normalizer, raw_events.jsonl ainda desordenado |
| REC-19 (máscara CPF 5x amplification) | BUG-008 (mesma família) | 2796c80 (Bug9 dedup) | **REGRESSÃO GRAVE** — pior caso ainda observado; 3-4x duplicata mesmo timestamp |
| REC-20 (assert value="visible" literal) | novo em ARCHIVE | — | **NÃO CATALOGADO** — overlay grava string literal em vez de state estruturado |
| REC-21 (value_mutation pega form completo) | novo em ARCHIVE | — | **NÃO CATALOGADO** |
| REC-22 (metadata suite/test_case vs path) | novo em ARCHIVE | — | **NÃO CATALOGADO** |
| REC-23 (PII cliente real plaintext) | novo em ARCHIVE | — | **COMPLIANCE BLOCKER** — não catalogado |
| REC-24 (password fraca plaintext R3) | reforço REC-06 | — | reforço |
| REC-25 (timeout 3000ms fixo) | novo em ARCHIVE | — | **NÃO CATALOGADO** |
| REC-26 (`#next` 6x R3) | reforço REC-09 | — | reforço mais grave |
| REC-27 (assert sem valor R3) | reforço REC-10 | — | reforço |
| REC-28 (verificar+clicar 2 events) | novo em ARCHIVE | — | **NÃO CATALOGADO** |

**BUGs ARCHIVE não observados agora** (provavelmente ainda fixados corretamente):
- BUG-001 (`<select>` vira input) — commit `2b151d5 fix(select): bugs 11-16` — não observado em R1/R2/R3 (não tinha `<select>` nessas telas)
- BUG-002 (DOM snapshots 0 bytes) — não testado; verificar `dom_snapshots/*.html` size em R1/R2/R3
- BUG-006 (browser bloqueado sem fallback) — não observado (browser abriu OK)
- BUG-007 (tela pisca no SIMAX) — não aplicável (nenhum sistema é SIMAX aqui)
- BUG-014 (httpx ausente) — sem sinal
- BUG-015 (URL com & no PowerShell) — sem sinal (usados no linux, não PowerShell)
- BUG-016 (logs truncados) — sem análise
- BUG-018 (compile sem artefato semântico) — sem análise (compile não rodado)

**Sinal principal**: **BUG-008 (fill burst / debounce) apareceu shipped mas ainda ocorre em 2 recordings novos**. Fix não pegou; provável causa: patch em uma fonte (`_fill_input`) mas não em outras (value_mutation collector, mask reformat, framework double-emit). BUG-REC-19 mostra pior caso — 5x amplification em CPF.

---

## Priorização inicial

**P0 (blockers — compliance + core pipeline)**:
1. **BUG-REC-30** — CNPJs de terceiros vazando via `<select>` textContent — **compliance BLOCKER (dados corporativos)**
2. **BUG-REC-23** — PII cliente real (CPF, nome, endereço) plaintext — **compliance BLOCKER**
3. **BUG-REC-29 + REC-37** — CPF pessoal do QA como username plaintext (múltiplos QAs)
4. BUG-REC-06 + REC-24 + REC-35 + REC-38 — credenciais/password/PIN plaintext (múltiplos padrões weak)
5. **BUG-REC-42** — recorder detecta `paste: true` em password field mas não masca (sinal ignorado)
5. BUG-REC-32 — fill corrigido gera 2 fills consecutivos (URL colada + matrícula)
6. BUG-REC-19 — máscara CPF 5x amplification (regressão BUG-008)
7. BUG-REC-01 — steps.jsonl publica só asserts → compile inútil (**5 recordings**)
8. BUG-REC-02 — overlay TestForge contamina recording (`tf-btn-*` capturado)
9. BUG-REC-03 — healing default OFF
10. BUG-REC-04 — replay batched 0% success (3/3 recordings)
11. BUG-REC-05 — framework detection null em R2/R3 (Angular óbvio)

**P1 (high)**:
12. BUG-REC-07 — fill events sem debounce (regressão BUG-008)
13. BUG-REC-08 — URL drift false-positive
14. BUG-REC-09 + REC-26 — `#next` seletor genérico reused (até 6 ocorrências R3)
15. BUG-REC-10 + REC-27 — assert sem valor esperado aceito
16. BUG-REC-11 — gherkin confunde placeholder com botão
17. BUG-REC-20 — assert value="visible" literal em vez de state estruturado
18. BUG-REC-21 — value_mutation snapshot form completo (não diff)
19. BUG-REC-25 — timeout 3000ms fixo causa cascata
20. **BUG-REC-31** — Keycloak session/nonce/state em URLs plaintext
21. **BUG-REC-33** — `postback` event sem handler downstream (transição SSO perdida)
22. **BUG-REC-34** — calendar 15 clicks sem detecção pattern (repro fragile)
23. **BUG-REC-40** — assert em container `.container-fluid` frágil (reforço BUG-014 ARCHIVE)

**P2 (med)**:
24. BUG-REC-12 — value_mutation dedup vaza com name vazio (parcial BUG-008)
25. BUG-REC-13 — confidence heurística instável
26. BUG-REC-14 — autocomplete Angular quebrado em 2 events
27. BUG-REC-22 — metadata suite/test_case não bate com hierarquia path
28. **BUG-REC-36** — backslash Windows paths em dom_snapshot/ax_snapshot fields (cross-platform break)
29. **BUG-REC-41** — value_mutation vazio duplicado mesmo timestamp (padrão persistente em TODOS recordings)
30. **BUG-REC-43** — DOM snapshots vazam session_code Keycloak (sanitizer ausente)

**P3 (med baixo)**:
31. BUG-REC-15 — healing_report vazio quando healing off
32. BUG-REC-16 — steps.jsonl vs submission_report inconsistente
33. BUG-REC-28 — verificar-então-clicar em 2 events desconexos

**P4 (low / não-bug TestForge)**:
34. BUG-REC-17 — 5 zips restantes (SIFEC, SIOPI, SISGH, simax, uncategorized) não processados
35. BUG-REC-18 — raw_events ordem cronológica quebrada
36. BUG-REC-39 — Keycloak DES reusa `execution` GUID (**config bug ambiente CAIXA**, não TestForge — reportar infra)

---

## Próximas análises pendentes

- [x] Extrair e analisar `src/testforge/Portal de Massa.zip` — R4a e R4b analisados (BUGs REC-29..36)
- [x] Analisar `src/testforge/SIFAP.zip` — R5a e R5b (BUGs REC-37..43)
- [x] Analisar `src/testforge/SIFEC.zip` — R6a/b/c/d (BUGs REC-44..50)
- [x] Analisar `src/testforge/SIOPI.zip` — R7a/b (BUGs REC-51..59)
- [x] Analisar `src/testforge/SISGH.zip` — R8 (BUGs REC-60..68)
- [x] Analisar `src/testforge/simax.zip` — R9 (20 recordings) (BUGs REC-69..78)
- [x] Analisar `src/testforge/uncategorized.zip` — R10 (12 recordings) (BUGs REC-79..87)
- [x] Analisar `recordings_failed/` — R11 (3 SIMAX auto-movidos) (BUGs REC-88..92)
- [ ] Analisar `src/testforge/SIFEC.zip` (sistema CAIXA)
- [ ] Analisar `src/testforge/SIOPI.zip` (sistema CAIXA — Simulador Habitação, referência hotfix22)
- [ ] Analisar `src/testforge/SISGH.zip` (sistema CAIXA)
- [ ] Analisar `src/testforge/simax.zip` (referência BUG-001 select)
- [ ] Analisar `src/testforge/uncategorized.zip`
- [ ] Ler outros recordings em `recordings_failed/` pra padrões repetidos (task 25)
- [ ] Verificar se BUG-REC-01 e BUG-REC-16 são o mesmo bug de nome diferente
- [ ] Comparar `diagnostic/steps.jsonl` vs `steps.jsonl` estrutura pra entender divergência
- [ ] Cross-check com bugs conhecidos em `docs/bugs-conhecidos.md`

---

## Referências

- Recording R1: `src/testforge/MASSA_DE_TESTE/SOLICITACAO/.../solicitar_massa_no_siiso/`
- Recording R2: `src/testforge/MASSA_DE_TESTE_01/CRIAR_SOLICITACAO_TEST/deve_criar_uma_solicitacao_siiso/`
- Bugs anteriores conhecidos: `docs/bugs-conhecidos.md`
- Plano fase 1-9: `docs/HEALING-GAPS-PLAN.md`
- Handoff: `docs/HANDOFF-NEXT-LLM.md`
