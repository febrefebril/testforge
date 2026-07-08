# TestForge — Recording Bugs Fix Plan

**Autor**: Session audit 2026-07-07
**Baseado em**: `.planning/bugs-recording-analysis.md` (92 bugs REC catalogados, 49 recordings, 10 sistemas CORPORATIVO)
**Contexto prévio**: `docs/HEALING-GAPS-PLAN.md` (Fases 1-9 já shipadas via bundle 2026-07-06)
**Objetivo**: agrupar 92 bugs em **root causes** + **9 fases ordenadas** por risco crescente
**Target executor**: LLM implementadora (Sonnet/Opus 4.7)
**Custo estimado total**: ~40-50h

---

## 1. Sumário executivo

Análise de recordings reais CORPORATIVO (Portal de Massa, AGENDAMENTO, CADASTRO, SIMULADOR, GESTAO, CONSULTA, PLATAFORMA DES, MASSA_DE_TESTE + uncategorized) revelou 92 bugs em recorder/publisher/compiler/runner. **NÃO são bugs individuais isolados** — são **30 root-causes sistêmicos** com muitos sintomas duplicados entre sistemas.

**Padrão dominante** (ver Seção 4):
- **Compliance blockers** (PII, credentials, dados corporativos) — 15 bugs — **P0 imediato**
- **Publisher pipeline quebrado** (steps.jsonl só asserts, overlay auto-injection) — 3 bugs — **P0 blocker**
- **Mask/typing amplification** (currency 13x, CPF 5x, select 3-5x) — 9 bugs
- **Seletores frágeis** (posicional, generic ID, concat text) — 12 bugs
- **Taxonomy/lifecycle management** (regravações, uncategorized, failed folder) — 14 bugs

Este plano NÃO substitui `HEALING-GAPS-PLAN.md` (aquele foi shipado, cobria 17 gaps de code review). Este cobre bugs descobertos EM PRODUÇÃO por análise de recordings reais.

---

## 2. Como usar este plano

1. Leia `.planning/bugs-recording-analysis.md` primeiro (bugs originais com evidências).
2. Este documento agrupa por root-cause + define fases executáveis.
3. Cada Fase tem: objetivo, RCs cobertos, arquivos, testes obrigatórios, DoD, commits sugeridos.
4. **Fase 1 (compliance)** deve ser executada ANTES de qualquer merge ou push próximo — bugs bloqueiam LGPD/BCB.
5. Fases 2-9 podem paralelizar (branches distintos).

---

## 3. Contexto do projeto

TestForge grava testes E2E com self-healing. Cliente: QA em setores regulados (bancos, seguros, saúde, gov). Falha silenciosa = bug vaza para produção.

**Recordings analisados** (49 total):
| # | Sistema | Recordings | Data |
|---|---|---|---|
| MASSA_DE_TESTE | Portal gestão massa testes | 1 | 07-03 |
| MASSA_DE_TESTE_01 | Portal-des Cliente | 1 | 07-06 |
| PLATAFORMA DES | Cliente/CEF | 1 | 07-06 |
| Portal de Massa | Gás do Povo + SIISO | 2 | 07-02 |
| AGENDAMENTO | Farmácia Popular | 2 | 07-02 |
| CADASTRO | Login CORPORATIVO | 4 | 07-03/06 |
| SIMULADOR (produção!) | Sim Habitação | 2 | 07-02 |
| GESTAO | Gestão Honras | 1 | 07-02 |
| CONSULTA | Agendamento massagem | 20 | 07-02/03 |
| uncategorized | 12 sistemas mistos | 12 | 06-24/26 |
| recordings_failed | 3 CONSULTA auto-movidos | 3 | 07-03 |

---

## 4. Root causes (30 famílias de bugs)

Cada RC agrupa múltiplos BUG-REC-NN da análise original.

### RC-1 — Sanitização PII/credenciais AUSENTE (COMPLIANCE BLOCKER)
**Bugs**: REC-06, 23, 24, 29, 30, 31, 35, 37, 38, 42, 43, 44, 45, 61, 62, 63, 89

**Sintomas**:
- Senhas/PINs plaintext em raw_events (`&lt;SENHA&gt;`, `&lt;SENHA&gt;`, `&lt;SENHA&gt;`, `&lt;SENHA&gt;`, `&lt;SENHA&gt;`, typing burst com N tentativas)
- CPF do QA (6 identidades distintas: `&lt;CPF&gt;`, `&lt;CPF&gt;`, `&lt;CPF&gt;`, etc)
- 4 matrículas QA (`c000011`, `c000000`, `c000098`, `c000018`)
- CNPJs de terceiros (13 revendedores em `<select>` textContent)
- PII cliente real (`JOAO DA SILVA`, endereço, email, telefone)
- Keycloak session tokens (state, nonce, code_challenge, execution)
- Nome arquivo interno (`CNT.EMP.MZ.BMX0.PRONAMPE.D260625.R4`)
- Windows path (`C:\Desenvolvimento\AUTOMATA-PRIMUS\...`)

**Escopo do fix**: PII detector unificado em pipeline write.

### RC-2 — Publisher steps.jsonl publica APENAS asserts (compile blocker)
**Bugs**: REC-01, 16

**Sintoma**: 34/34 recordings schema novo têm steps.jsonl com só `action=assert`. Diagnostic tem N steps mas main publisher descarta clicks/fills.

**Escopo**: reconciliar `steps.jsonl` com `diagnostic/steps.jsonl`. Compile deve ler do ÚNICO source of truth.

### RC-3 — Overlay TestForge auto-injection (`tf-btn-*` capturado)
**Bugs**: REC-02

**Sintoma**: `#tf-btn-assert`, `#tf-btn-stop` (botões do próprio TestForge overlay) capturados como user clicks. 4/14 recordings schema novo têm.

**Escopo**: recorder blocklist para elementos com prefix `tf-*`/`__tf-*`.

### RC-4 — Typing/mask amplification (3-13x)
**Bugs**: REC-07, 12, 19, 41, 48, 51, 52, 53, 54, 70

**Sintomas**:
- Currency mask: 13x amplification (` 0,00 → 0,00 1 → 0,01 → ...`)
- CPF mask: 5x (`0` → `01` → `019` → `019.4` → `0194` → `019.4`)
- Username typing burst: 6 fills para 6 chars (`C → C000 → C0 → C000 → C00001`)
- select_option: 3-5 events consecutivos por 1 escolha
- `mat-input-N` reused entre calculadoras (dedup vazando)
- `DD/MM/AAAA` placeholder capturado como value (regressão `f1c1881`)
- Currency values com espaços leading/trailing

**Escopo**: dedup por fingerprint stable + debounce final + strip placeholder + strip whitespace.

### RC-5 — Healing default OFF em run-incremental
**Bugs**: REC-03

**Sintoma**: 11 failures reportam "Healing desativado". `total_healings: 0`.

**Escopo**: flip default. Flag `--no-healing` opt-out.

### RC-6 — Replay batched 0% success
**Bugs**: REC-04

**Sintoma**: `selectors_immediate_ok/fail: 0/N` em todos recordings. Batched-at-end testa selectors contra DOM final que não tem elementos intermediários.

**Escopo**: replay step-a-step com URL correta.

### RC-7 — Framework detection intermitente (null em Angular óbvio)
**Bugs**: REC-05

**Sintoma**: R2/R3 mesmo domínio `sistema-des.example.com` → framework_detection.angular_version=null. R1 detecta OK.

**Escopo**: retry defer detection quando DOM population < threshold.

### RC-8 — URL drift false-positive
**Bugs**: REC-08

**Sintoma**: `url before='<X>' after='<X>'` idênticas mas reporta drift. 4+ ocorrências.

**Escopo**: bug lógico compare — normalizar antes.

### RC-9 — Seletores frágeis (posicional, generic, concat text)
**Bugs**: REC-09, 11, 20, 26, 40, 47, 57, 67, 68, 74, 78

**Sintomas**:
- `#next` reused em wizard multi-step (até 6 ocorrências)
- Gherkin confunde placeholder (`c999999`) com botão
- Assert value=`"visible"` literal (não state estruturado)
- `.container-fluid` capturado (container inteiro da página)
- `role=button[name="RecolhidoMFEs em desenv. (SICCR)"]` (placeholder + option concat)
- `tr:nth-of-type(N) > td:nth-of-type(M)` sem identificador temporal
- `role=menuitem` inferido incorretamente
- `.mat-button-wrapper` interno (fragile)

**Escopo**: blacklist IDs genéricos + assert generator melhor + role validation.

### RC-10 — `<select>` handling (BUG-001 fix parcial)
**Bugs**: REC-30, 69

**Sintoma**: recorder AGORA emite `type=select_option` (fix `2b151d5` OK). MAS `target.text` ainda concatena TODAS options.

**Escopo**: para `<select>`, `target.text` = apenas placeholder + option selecionada.

### RC-11 — File input handling
**Bugs**: REC-60, 66

**Sintomas**:
- fill value = `"C:\\fakepath\\..."` (browser security prefix) — Playwright rejeita
- `<label for="files">` visible timeout 3000ms

**Escopo**: normalizer detect `type=file` OR `file_upload` metadata → emit `set_input_files()`.

### RC-12 — Postback / SSO event handling
**Bugs**: REC-33

**Sintoma**: `type=postback` emitido pelo recorder mas normalizer/compiler sem handler. Transição SSO perdida.

**Escopo**: handler `postback` → emit `wait_for_navigation()` step.

### RC-13 — Calendar/date picker patterns
**Bugs**: REC-34, 55, 56

**Sintomas**:
- 15 clicks em calendar `‹`/`›` sem aggregation
- 7 clicks `<span>` Material datepicker (year → month → day)
- `click input` + `fill input` redundante (Playwright fill já foca)

**Escopo**: handler `mat_datepicker` + `date_range_picker` component patterns.

### RC-14 — Assert overlay validation
**Bugs**: REC-10, 27, 49

**Sintomas**:
- assert sem `expected_value` aceito
- assert em erro app sem classificação `expected_error` vs `expected_success`

**Escopo**: overlay valida ANTES de aceitar assert. Prompt para `expected_state`.

### RC-15 — Timeout wait 3000ms hardcoded
**Bugs**: REC-25

**Sintoma**: 5 failures cascata Step 20/22/34/35/36 com timeout fixo. Angular formcontrol carrega em tempo variável.

**Escopo**: timeout adaptativo — `wait_for(load_state)` primeiro, depois `wait_for(visible)`. Config por sistema.

### RC-16 — value_mutation snapshot form completo (não diff)
**Bugs**: REC-21, 41

**Sintoma**: cada mutation em `inputSearchCpfCnpj` traz junto `inputSearchNis` com value="". 90 mutations pra 18 fills.

**Escopo**: MutationObserver com attributeFilter — emit APENAS quem mudou.

### RC-17 — Taxonomy + lifecycle management
**Bugs**: REC-22, 64, 71, 75, 76, 77, 79, 80, 81, 82, 83, 87, 88, 90, 91, 92

**Sintomas**:
- Metadata suite/test_case não bate com hierarquia path (path 4-níveis, metadata 3)
- GESTAO vs SGH (metadata vs page_title)
- Regravações duplicadas (`_2`, `_3`, `_2_2`, `_YYYYMMDD-HHMMSS`)
- 2 padrões sanitize `ç` (`_a` vs `c_a`)
- 12 recordings uncategorized (schema=null, sem taxonomy)
- `application` field ambíguo ("web" vs "SIMULADOR")
- Statuses deprecated (`needs_review`, `ready_for_team`)
- User regravando viola `no-regrave` (8+ casos)
- Old recording sem alerta "sistema evoluiu, regravar"
- Sem `testforge fix-recording <path>` CLI
- Duplicação `recordings_failed/` E `consulta.zip`
- Sem README em `recordings_failed/`
- Storage bloat rec movidos

**Escopo**: overhaul taxonomy + recording lifecycle. Grande.

### RC-18 — Instrumentação silent-skip parcialmente shipada
**Bugs**: originais Fase 1 do HEALING-GAPS-PLAN — verificar se instrumentação chegou

**Escopo**: cross-check com plano anterior. Se não shipado, aplicar.

### RC-19 — `<script>` como `.textContent` de div (2 sistemas)
**Bugs**: REC-46, 65

**Sintoma**: CADASTRO login DES + GESTAO login TQS legacy têm `<script>` inline no HTML. Recorder captura como div.text.

**Escopo**: recorder filter `<script>`, `<style>` children ao computar textContent.

### RC-20 — Detecção de produção (compliance)
**Bugs**: REC-59, 86

**Sintoma**: SIMULADOR R7a/b + uncategorized `verifica_regrecao` gravados em `sistema-prod.example.com` (**PRODUÇÃO**), não DES/TQS.

**Escopo**: recorder detect production domains (`example.com` sem `-des/-tqs`) → alert antes de gravar.

### RC-21 — Agents DOM validation ausente (memory `[[project-simulador-15-run-analysis]]`)
**Bugs**: complementar HEALING-GAPS Fase 6 — verificar se recordings mostram regressão

**Escopo**: cross-check com bundle atual.

### RC-22 — Autocomplete + dead fills
**Bugs**: REC-14, 73

**Sintomas**:
- `fill t` seguido de click card (2 events sem acoplamento)
- `fill input value="t"` sem target identifier em TODOS 20 CONSULTA (dead fill)

**Escopo**: normalizer detect "search+select" pattern OU skip dead fills sem target.

### RC-23 — Intent aggregation ausente
**Bugs**: REC-28, 49, 50

**Sintomas**:
- verificar+clicar em 2 events desconexos
- assert em erro app sem contexto
- value_captured baixo (38% R6b) por typing burst inflando missing

**Escopo**: normalizer detect patterns `check-then-act`, `assert_error_context`.

### RC-24 — Paste event handling
**Bugs**: REC-42

**Sintoma**: recorder detecta `paste: true` em password field mas ignora → plaintext em raw_events.

**Escopo**: `paste=true` + `type=password` → masking obrigatório.

### RC-25 — Healing report vazio quando healing off
**Bugs**: REC-15

**Escopo**: log verboso "healing disabled, use --enable-healing" no report.

### RC-26 — Windows path serialização (cross-platform)
**Bugs**: REC-36, 89

**Sintoma**: `"dom_snapshot":"dom_snapshots\\evt_00019.html"` — backslash Windows literal em JSON. `source_dir` absoluto.

**Escopo**: sempre `PurePosixPath` OU `.replace('\\', '/')` antes de serialize.

### RC-27 — Recorder timing/consistency
**Bugs**: REC-72

**Sintoma**: mesmo botão capturado com/sem element_id em recordings diferentes.

**Escopo**: retry sanity check "id ou role obrigatório" antes de commit event.

### RC-28 — Confidence heurística instável
**Bugs**: REC-13

**Sintoma**: `evt_00011 modal appeared` confidence 0.2 (subestimado). Regra conta N de appeared/disappeared sem semântica.

**Escopo**: rule-based weights (role=dialog, [modal-title], URL delta).

### RC-29 — raw_events ordem cronológica
**Bugs**: REC-18

**Sintoma**: raw_events ordenado por append order, não timestamp.

**Escopo**: sort final por timestamp no flush.

### RC-30 — Keycloak DES infra (NÃO É BUG TESTFORGE)
**Bugs**: REC-39

**Sintoma**: `execution=939b3be6-f791-489f-a749-a2a9dfcdaecd` idêntico R4a e R5a. Grep zerou no source TestForge.

**Ação**: reportar time infra CORPORATIVO (Task 27 já criada).

---

## 5. Fases

Fases ordenadas por: (a) impacto compliance/blocker; (b) blast radius baixo; (c) dependências.

### FASE 1 — PII detector observability layer (~6h) — REVISADA 2026-07-07

**Objetivo**: **detectar e reportar** dados sensíveis em recordings sem intervir. Dados são massa de teste — não podem ser mascarados sem quebrar reprodução.

**Contrato**: `[[feedback-pii-alert-only]]` — dados NÃO são mascarados. TestForge fornece **detection + warning + audit trail**.

**RCs cobertos**: RC-1 (detect + alert dos 17 bugs), RC-24 (alert paste), RC-26 (Windows path — este SIM normalizar por causa de cross-platform break).

**Trabalho**:

**5.1.1 PII Detector unificado** (`src/testforge/security/pii_detector.py` — CRIAR):
- Patterns:
  - CPF: `\b\d{3}\.?\d{3}\.?\d{3}-?\d{2}\b`
  - CNPJ: `\b\d{2}\.?\d{3}\.?\d{3}/?\d{4}-?\d{2}\b`
  - Telefone BR: `\(?\d{2}\)?\s?\d{4,5}-?\d{4}`
  - Email: `[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}`
  - Matrícula CORPORATIVO: `\bc\d{6}\b`
  - Nome completo: heurística (2+ palavras título com iniciais maiúsculas)
  - Filename corporativo: `[A-Z]+\.[A-Z]+\.[A-Z0-9]+\.\d{6,8}`
- API:
  ```python
  @dataclass
  class PiiHit:
      pattern: str  # "cpf", "cnpj", "email", ...
      value: str    # valor detectado (mantido - NÃO mascarado)
      context: str  # onde apareceu (raw_events evt_00005, steps.jsonl step_0002, etc)
      severity: str # "critical" (senha, PIN), "high" (CPF, CNPJ), "med" (email, tel), "low" (nome)
  
  def detect(value: str, ctx: dict) -> list[PiiHit]:
      """Retorna hits SEM modificar valor. Detection-only."""
  ```

**5.1.2 Password field + paste detection** (observability):
- Detect `type=password` OU `paste=true` OU `type=text` com placeholder/label contendo `senha/password/pin` → emit PiiHit severity="critical".
- **NÃO mascarar** o value. Apenas emit hit.

**5.1.3 URL Keycloak detection**:
- `url_scan(url: str) -> list[PiiHit]` — busca params Keycloak sensíveis (`state`, `nonce`, `code_challenge`, `session_state`, `execution`, `session_code`, `code`).
- Reporta em hits. **NÃO strip params**.

**5.1.4 `<select>` textContent handling** (**este SIM é fix, não alert**):
- BUG independente de PII: `<select>` `.textContent` concatena TODAS options — vaza dados corporativos E quebra selectors.
- Fix: para `<select>` no recorder, `target.text` = apenas placeholder + option selecionada.
- **Motivo**: sem intervir aqui, selectors gerados usam string poluída (`role=button[name="RecolhidoMFEs em desenv. (SICCR)"]`), quebrando replay.
- Isso NÃO é masking — é extração correta.

**5.1.5 Windows path normalization** (fix, não alert):
- BUG cross-platform: JSON com backslash literal quebra Read no Linux.
- Fix: `PurePosixPath(p).as_posix()` em `dom_snapshot`, `ax_snapshot`, `FAILED_MARKER.source_dir`.
- Também converte source_dir absoluto → relativo (previne leak Windows local path).

**5.1.6 Sensitive alerts report** (`test_data.json` + `submission_report.json`):
- Após gravação, agregar todos PiiHit em `sensitive_alerts`:
  ```json
  {
    "sensitive_alerts": [
      {
        "pattern": "cpf",
        "count": 2,
        "severity": "high",
        "contexts": ["raw_events.evt_00005", "steps.jsonl.step_0003"],
        "policy": "alert_only",
        "action_taken": "none",
        "recommendation": "Review before public export. Este recording contém CPF real."
      }
    ]
  }
  ```
- Field `masking_applied: false` sempre (nunca masking).

**5.1.7 CLI `testforge audit-pii <recording>`**:
- Executa detector sobre recording existente.
- Reporta hits categorizados.
- Exit code non-zero se `severity=critical` encontrado.
- Uso: pre-push git hook opcional.

**5.1.8 Telemetry counter**:
- `metrics.record_pii_hit(pattern, severity)` — counter agregado.
- Aparece em `testforge pilot-report`.

**5.1.9 Summary ao QA no fim da gravação**:
- No console (não overlay):
  ```
  [TestForge] Recording finalized: 45 events
  [TestForge] Sensitive data detected:
    - 2 CPFs (severity: high)
    - 1 senha (severity: critical)
    - 3 params Keycloak URL (severity: high)
  [TestForge] Detalhes: recordings/<id>/sensitive_alerts.json
  [TestForge] AÇÃO SUGERIDA: revisar antes de export público.
  ```

**5.1.10 Detecção produção (RC-20 combined)**:
- Detect base_url em domínio produção (`example.com` sem `-des/-tqs/-hom`).
- Emit PiiHit severity="critical" + prompt início gravação: "Você está gravando em PRODUÇÃO — recomenda ambiente DES/TQS. Continuar? [y/N]".

**Testes obrigatórios** (padrão `docs/TEST-PATTERNS.md`, contract cross-source por `docs/ANTI-REGRESSION-PLAN.md`):

```
tests/unit/security/test_pii_detector_when_cpf_pattern_then_emits_hit_without_masking.py
tests/unit/security/test_pii_detector_when_cnpj_pattern_then_emits_hit.py
tests/unit/security/test_pii_detector_when_matricula_br_then_emits_hit.py
tests/unit/security/test_pii_detector_when_keycloak_url_params_then_emits_hits.py
tests/unit/security/test_pii_detector_when_password_type_then_emits_critical.py
tests/unit/security/test_pii_detector_when_paste_true_password_then_emits_critical.py
tests/unit/security/test_pii_detector_when_production_domain_then_emits_critical.py
tests/unit/security/test_pii_detector_preserves_original_value.py  # ← CONTRACT
tests/unit/recorder/test_select_textContent_when_multiple_options_then_extracts_selected_only.py
tests/unit/recorder/test_windows_path_normalize_when_backslash_then_forward.py
tests/unit/recorder/test_source_dir_when_absolute_then_relative.py
tests/contract/test_no_source_ever_masks_pii_values.py  # ← CROSS-SOURCE INVARIANT
tests/integration/cli/test_audit_pii_when_critical_severity_then_exit_nonzero.py
tests/regression/recording/test_r5a_audit_reports_credenciais_alert.py
tests/regression/recording/test_r3_audit_reports_pii_cliente_alert.py
tests/regression/recording/test_r4a_audit_reports_cnpj_alert.py
tests/regression/recording/test_r7a_prod_domain_detected.py
```

**Contract test crítico** (invariante anti-regressão):
```python
# tests/contract/test_no_source_ever_masks_pii_values.py
@pytest.mark.contract
@pytest.mark.critical
def test_no_source_masks_pii_values():
    """Invariante: TestForge NUNCA modifica valor de campo sensível.
    Dados sensíveis são massa de teste. Fix regride se algum source
    aplicar masking silencioso.
    """
    rec = load_recording_fixture("r5a_sifap_login_with_credentials")
    original_pw = "&lt;SENHA&gt;"  # conhecido do anchor
    
    # Act — reprocess
    output = reprocess_recording(rec)
    
    # Assert — valor deve estar preservado EM TODAS AS FONTES
    def find_password_value(source_data):
        for entry in source_data:
            if entry.get("target", {}).get("element_id") == "password":
                return entry.get("value")
        return None
    
    assert find_password_value(output["raw_events"]) == original_pw, \
        "raw_events masking (regressão contrato PII alert-only)"
    assert find_password_value(output["value_mutations"]) == original_pw, \
        "value_mutations masking (regressão contrato PII alert-only)"
    # PII detector reportou mas não modificou:
    assert any(h["pattern"] == "password" for h in output["sensitive_alerts"])
    assert output["masking_applied"] is False
```

**Recording âncora obrigatório** (por `docs/ANTI-REGRESSION-PLAN.md` Camada 3):
- `tests/fixtures/recordings/r5a_sifap_login_with_credentials/`
- `tests/fixtures/recordings/r3_plataforma_des_pii_cliente/`
- `tests/fixtures/recordings/r4a_portal_massa_select_cnpj/`
- `tests/fixtures/recordings/r7a_siopi_producao/`

Cada âncora tem `expected/sensitive_alerts.json` como golden.

**DoD Fase 1**:
- [ ] PII detector com 8+ patterns testados (contract test preserve value)
- [ ] Password/paste detection reporta sem mascarar
- [ ] Keycloak URL detection reporta sem strip
- [ ] `<select>` textContent = selected option only (fix não-mask)
- [ ] Windows path normalizado (fix não-mask)
- [ ] `sensitive_alerts` populated em test_data.json E submission_report.json
- [ ] `masking_applied: false` sempre presente
- [ ] CLI `testforge audit-pii <rec>` funciona
- [ ] Detecção produção com prompt início
- [ ] 4 recordings âncora + golden files criados
- [ ] Regressão: reprocess R5a → password `&lt;SENHA&gt;` PRESERVADO + alert emitido
- [ ] Regressão: reprocess R3 → CPF `&lt;CPF&gt;` PRESERVADO + alert emitido
- [ ] Regressão: reprocess R4a → 13 CNPJs PRESERVADOS + alert emitido
- [ ] Regressão: reprocess R7a → produção detectada + alert critical
- [ ] Config `.testforge/pii_policy.yaml` documentada (default: alert_only)
- [ ] Contract test `test_no_source_masks_pii_values` passa (anti-regressão)

**Commits sugeridos**:
1. `feat(security): pii_detector com patterns CPF/CNPJ/email/telefone/matrícula/Keycloak`
2. `feat(security): password + paste detection (alert-only, não mask)`
3. `feat(security): URL scan Keycloak SSO params (alert-only)`
4. `feat(security): production domain detection + prompt início`
5. `fix(recorder): <select> textContent = selected option only (não é masking, é extração correta)`
6. `fix(paths): normalize Windows backslash + convert absolute source_dir → relative`
7. `feat(recorder): sensitive_alerts populated em test_data + submission_report`
8. `feat(cli): testforge audit-pii <recording>`
9. `feat(metrics): pii_hit counter em pilot-report`
10. `test(contract): invariante PII values preservados em todas as fontes`
11. `test(regression): 4 recordings âncora reprocessados + goldens`

---

### FASE 2 — Publisher steps.jsonl reconciliation (~3h)

**Objetivo**: fim do padrão "steps.jsonl só asserts". Compile deve ler source of truth único.

**RCs cobertos**: RC-2 (2 bugs)

**Trabalho**:

**5.2.1 Investigação estrutural**:
- Grep `steps.jsonl` em `src/testforge/` — quem escreve/lê?
- Grep `diagnostic/steps.jsonl` — como difere?
- Verificar `recorder_controller._publish_step()` ou similar.

Hipótese: `overlay_inject.js` só emit step quando user aperta Shift+A (assert). Clicks/fills automáticos vão pra raw_events + diagnostic mas não para steps.jsonl principal.

**5.2.2 Fix pipeline**:
- Publisher steps.jsonl deve incluir clicks/fills/navegações relevantes automaticamente.
- OU: compile deve ler `diagnostic/steps.jsonl` OR `raw_events.jsonl` (normalizado).
- Escolher SINGLE source of truth. Documentar.

**5.2.3 Migration**:
- Existing recordings com steps.jsonl=1 → compile deve funcionar consumindo raw_events.

**Testes**:
```
tests/integration/pipeline/test_publisher_when_click_recorded_then_appears_in_steps_jsonl.py
tests/integration/pipeline/test_compile_when_steps_jsonl_only_asserts_then_reads_raw_events.py
tests/regression/recording/test_r1_r2_r3_steps_jsonl_populated_after_fix.py
```

**DoD Fase 2**:
- [ ] Padrão "steps.jsonl só asserts" quebrado — recordings novos têm clicks/fills
- [ ] Compile funciona em recordings ANTIGOS (steps.jsonl=1) via fallback raw_events
- [ ] R1, R2, R3 reprocessados: compile gera test_*.py com múltiplos steps (não 1 assert isolado)
- [ ] Documentar single source of truth em `docs/ARCHITECTURE-V2.md`

**Commits**:
1. `investigate: mapear steps.jsonl vs diagnostic/steps.jsonl vs raw_events`
2. `fix(publisher): steps.jsonl inclui clicks/fills automaticamente`
3. `fix(compile): fallback pra raw_events quando steps.jsonl subutilizado`
4. `docs: documentar single source of truth em ARCHITECTURE-V2`

---

### FASE 3 — Overlay contamination + healing default (~2h)

**Objetivo**: recorder ignora próprio overlay. Healing ON por default.

**RCs cobertos**: RC-3 (1 bug), RC-5 (1 bug)

**Trabalho**:

**5.3.1 Overlay element blocklist**:
- `overlay_inject.js`: event listeners global adiciona check `if (e.target.id?.startsWith('tf-') || e.target.classList.contains('__tf-')) return;`
- Ancestor check (walk parents) — click DENTRO do overlay também skip.

**5.3.2 Healing default ON**:
- `src/testforge/cli/app.py`: `run-incremental` default `healing_enabled=True`.
- Novo flag `--no-healing` opt-out.
- Update `--help` + docs.

**Testes**:
```
tests/unit/recorder/test_overlay_when_click_on_tf_btn_then_skips.py
tests/unit/recorder/test_overlay_when_click_inside_overlay_ancestor_then_skips.py
tests/unit/cli/test_run_incremental_when_no_healing_flag_absent_then_healing_enabled.py
tests/regression/recording/test_reprocess_r2_no_tf_btn_in_raw_events.py
```

**DoD**:
- [ ] Recorder blocklist tf-*/`__tf-*`
- [ ] Healing default ON
- [ ] R2 reprocessado: nenhum `tf-btn-*` em raw_events
- [ ] R2 run-incremental sem `--no-healing`: healing tenta em failures

**Commits**:
1. `fix(overlay): blocklist elementos tf-*/__tf-* como user events`
2. `feat(cli): healing default ON, flag --no-healing opt-out`

---

### FASE 4 — Typing/mask amplification dedup (~5h)

**Objetivo**: 1 valor final por campo (não 3-13 mutations). Aplica currency, CPF, date, username.

**RCs cobertos**: RC-4 (10 bugs)

**Trabalho**:

**5.4.1 Value mutation dedup**:
- MutationObserver `attributeFilter: ['value']` (evita full form snapshot — RC-16 relacionado).
- Fingerprint stable: NÃO usar `mat-input-N` sozinho — combine com placeholder + label + accessible_name + tag path.
- Debounce final: 800ms após último keystroke — emit APENAS último value estável.
- Fallback: se debounce timer expira, emit valor `final_stable`.

**5.4.2 Strip placeholder capture**:
- `if value === placeholder → skip` (`DD/MM/AAAA`, `c999999`).
- Aplicar em value_mutations E raw_events fill.

**5.4.3 Currency whitespace strip**:
- `if type=currency → value.trim()` antes de emit.
- Detector currency: placeholder `R$`, ou class contém `currency`, ou input mask `9.999,99`.

**5.4.4 select_option dedup**:
- Deduplicate `select_option` consecutivos no mesmo element com mesmo value.
- Keep last-with-value only. Skip default `0` (Selecione).

**5.4.5 username/text field debounce**:
- Mesmo debounce por keystroke pattern.

**Testes**:
```
tests/unit/recorder/test_value_mutation_when_currency_typing_then_only_final_emitted.py
tests/unit/recorder/test_value_mutation_when_placeholder_dd_mm_aaaa_then_skips.py
tests/unit/recorder/test_value_mutation_when_currency_has_spaces_then_stripped.py
tests/unit/recorder/test_select_option_when_3_events_same_value_then_dedup_last.py
tests/unit/recorder/test_fingerprint_when_mat_input_n_then_uses_placeholder_fallback.py
tests/regression/recording/test_r7a_currency_1_mutation_not_13.py
tests/regression/recording/test_r3_cpf_1_mutation_not_5.py
tests/regression/recording/test_r6d_username_1_fill_not_6.py
```

**DoD**:
- [ ] Value mutation debounce 800ms + dedup fingerprint
- [ ] Placeholder skip (`DD/MM/AAAA`, `c999999`)
- [ ] Whitespace strip currency
- [ ] select_option dedup consecutivos
- [ ] R7a reprocessado: 1 mutation currency (era 13)
- [ ] R3 reprocessado: 1 mutation CPF (era 5)
- [ ] R6d reprocessado: 1 fill username (era 6)

**Commits**:
1. `fix(recorder): value_mutation debounce 800ms com fingerprint stable`
2. `fix(recorder): skip placeholder DD/MM/AAAA em value_mutations (fix incompleto f1c1881)`
3. `fix(recorder): strip whitespace currency masks antes de emit`
4. `fix(recorder): dedup select_option consecutivos mesmo value`
5. `test(regression): 3 recordings validam amplification reduzida`

---

### FASE 5 — Replay batched + framework detection + URL drift (~4h)

**Objetivo**: diagnostic mode útil.

**RCs cobertos**: RC-6 (1 bug), RC-7 (1 bug), RC-8 (1 bug)

**Trabalho**:

**5.5.1 Replay step-a-step**:
- `diagnostic/replay_check.jsonl` deve testar cada selector no CONTEXTO do step original (URL, DOM state).
- Substituir batched-at-end por batched-por-URL ou step-by-step.

**5.5.2 Framework detection retry**:
- Se detection retorna null: retry 3x com delay 500ms.
- Threshold: DOM has > N interactive elements OR Angular bootstrap complete.

**5.5.3 URL drift normalize**:
- Compare URL: parse URL → sort query params → compare structure.
- Se strings idênticas → PASS (bug atual reporta drift em strings idênticas).

**Testes**:
```
tests/unit/diagnostic/test_replay_check_when_step_context_then_uses_correct_url.py
tests/unit/diagnostic/test_framework_detector_when_dom_empty_then_retries.py
tests/unit/runner/test_url_drift_when_identical_strings_then_pass.py
tests/regression/recording/test_r2_r3_framework_detects_angular.py
tests/regression/recording/test_r2_r3_step_2_no_false_drift.py
```

**DoD**:
- [ ] Diagnostic replay não bactch-at-end
- [ ] Framework detection retry
- [ ] URL drift compare corrigido
- [ ] R2/R3 reprocess: framework=Angular detectado
- [ ] R2/R3 Step 2: no false positive drift

**Commits**:
1. `fix(diagnostic): replay step-a-step com URL contextual`
2. `fix(diagnostic): framework detector retry defer`
3. `fix(runner): url drift compare normaliza antes de string compare`

---

### FASE 6 — Seletores frágeis + assert generator (~5h)

**Objetivo**: seletores robustos por step. Assert generator inteligente.

**RCs cobertos**: RC-9 (11 bugs), RC-10 (2 bugs), RC-14 (3 bugs)

**Trabalho**:

**5.6.1 Blacklist IDs genéricos**:
- Constante `GENERIC_ID_BLACKLIST = {'next', 'prev', 'back', 'submit', 'save', 'cancel', 'continue', 'ok', 'confirm'}`
- Recorder demote seletor com esses IDs — não usar como primary.
- Cross-check com Angular volátil IDs.

**5.6.2 Assert generator**:
- Se target é container genérico (`.container-fluid`, `div.wrapper`) → recorder sugere elemento mais específico (h1, label, botão).
- Assert value `"visible"` literal → substituir por `expected_state: visible` estruturado.
- Assert em erro (mensagem falha, class `error/alert/warning`) → mark `expected_error`.
- Assert em tr:nth-of-type sem identificador → buscar `has_text` do valor esperado como filter.

**5.6.3 role= inference validation**:
- `role=menuitem` precisa checar ax_snapshot pra role computed real.
- `role=button[name="..."]` — se name concatena placeholder+option (`<select>`), fallback.

**5.6.4 Overlay validation pre-assert**:
- Overlay bloqueia Shift+A se elemento não tem valor visível OR sem accessible_name.
- Prompt "Qual state esperado?" (visible / has_text / equals / matches).

**5.6.5 `.mat-button-wrapper` promotion**:
- Se selector alvo `.mat-button-wrapper` filho → promote pra `<button>` ancestral.

**Testes**:
```
tests/unit/recorder/test_selector_when_id_generic_then_demoted.py
tests/unit/recorder/test_assert_generator_when_container_fluid_then_suggests_specific.py
tests/unit/recorder/test_assert_when_visible_state_then_structured_not_string.py
tests/unit/recorder/test_role_inference_when_ax_snapshot_present_then_uses_computed.py
tests/regression/recording/test_r2_r3_no_next_reused_selector.py
tests/regression/recording/test_r5b_r7a_assert_more_specific_than_container.py
```

**DoD**:
- [ ] Blacklist IDs genéricos
- [ ] Assert generator com estado estruturado
- [ ] Role inference via ax_snapshot
- [ ] Overlay valida antes de aceitar assert
- [ ] R2/R3 reprocess: `#next` promovido para role+text ou XPath único
- [ ] R5b reprocess: assert em h1 específico não `.container-fluid`
- [ ] R7b reprocess: 2 asserts não têm `nth-of-type(3)` idêntico

**Commits**:
1. `feat(recorder): blacklist IDs genéricos (next, save, submit, etc)`
2. `feat(recorder): assert generator estruturado (state, not string)`
3. `fix(recorder): role= inference valida via ax_snapshot`
4. `feat(overlay): valida assert (expected_value obrigatório)`
5. `fix(recorder): promote .mat-button-wrapper para button ancestral`

---

### FASE 7 — Handlers específicos: file, postback, calendar, autocomplete (~6h)

**Objetivo**: patterns Angular Material + Angular auth + patterns comuns tratados corretamente.

**RCs cobertos**: RC-11 (2 bugs), RC-12 (1 bug), RC-13 (3 bugs), RC-22 (2 bugs)

**Trabalho**:

**5.7.1 File input handler** (`config/component_patterns.yaml` + `handlers/file_input.py`):
- Detect `input[type=file]` OR presence `file_upload` metadata.
- Emit `page.set_input_files(input#files, path)`.
- Bypass label click (`<label for="files">`).

**5.7.2 Postback handler**:
- Detect `type=postback` em raw_events.
- Emit step `wait_for_navigation()` OR `wait_for_url(after_url)`.

**5.7.3 Date picker Material handler**:
- Detect sequence: click open picker → click year selector → click month → click day.
- Aggregate em intent `select_date(date_string)` atômico.
- Compile emit `page.fill(date_input, date_string)` ou fluxo completo se fill direto rejeita.

**5.7.4 Calendar range picker**:
- Detect 3+ clicks em `‹`/`›`/dias → aggregate em `select_date_range(start, end)`.

**5.7.5 Autocomplete pattern**:
- Detect fill `t` seguido de click card/option → aggregate em `search_and_select(term, option)`.
- Compile emit fill + wait_for_selector option visible + click option.

**5.7.6 Dead fill skip**:
- Normalizer detecta fill sem target identifier em posição inicial pós-load → skip como noise.

**5.7.7 click+fill redundante**:
- Normalizer dedup `click input` seguido de `fill input` no mesmo target → fill only.

**Testes**:
```
tests/unit/handlers/test_file_input_when_type_file_then_uses_set_input_files.py
tests/unit/handlers/test_postback_when_detected_then_wait_for_navigation.py
tests/unit/handlers/test_date_picker_when_7_clicks_material_then_aggregates.py
tests/unit/handlers/test_autocomplete_when_fill_then_click_option_then_aggregates.py
tests/regression/recording/test_r8_file_upload_uses_set_input_files.py
tests/regression/recording/test_r7a_calendar_1_intent_not_7_clicks.py
tests/regression/recording/test_r1_r4b_autocomplete_aggregates.py
```

**DoD**:
- [ ] file input handler
- [ ] postback handler
- [ ] date_picker Material handler
- [ ] date_range_picker handler
- [ ] autocomplete handler
- [ ] Dead fill skip
- [ ] Click+fill dedup
- [ ] R8 reprocess: 1 `set_input_files` (era fill C:\fakepath)
- [ ] R7a reprocess: 1 `fill_date` (era 7 clicks span)
- [ ] R1 reprocess: 1 `search_and_select` (era 2 events)

**Commits**:
1. `feat(handlers): file_input via set_input_files`
2. `feat(handlers): postback trigger wait_for_navigation`
3. `feat(handlers): mat_datepicker aggregate calendar navigation`
4. `feat(handlers): date_range_picker aggregate multi-click`
5. `feat(handlers): autocomplete search+select aggregation`
6. `fix(normalizer): skip dead fills sem target identifier`
7. `fix(normalizer): dedup click+fill mesmo target`

---

### FASE 8 — Timeout adaptativo + value_mutation diff + textContent filter (~3h)

**Objetivo**: correções tático-pontuais.

**RCs cobertos**: RC-15 (1 bug), RC-16 (2 bugs), RC-19 (2 bugs), RC-27 (1 bug), RC-29 (1 bug)

**Trabalho**:

**5.8.1 Timeout adaptativo**:
- `wait_for_locator`: primeiro `wait_for(load_state='networkidle', timeout=5000)`, depois `wait_for(state='visible', timeout=3000)`.
- Config por sistema: `.testforge/timeouts.yaml` — timeout Angular hydration.

**5.8.2 MutationObserver diff**:
- MutationObserver `attributeFilter: ['value']` + emit APENAS o element que mudou.
- Não fazer full-form snapshot.

**5.8.3 textContent filter `<script>`/`<style>`**:
- Custom `getTextContent(el)` — recurse children skipping `<script>`, `<style>`, `<noscript>`.

**5.8.4 raw_events sort by timestamp**:
- Flush final: sort raw_events.jsonl por timestamp.
- Já feito no normalizer (commit `2eac52a`) mas verificar se aplicado no arquivo raw.

**5.8.5 Recorder consistency retry**:
- Se `id` OR `role` ausente na primeira leitura, retry 100ms.
- Consistência aumenta captura.

**Testes**:
```
tests/unit/runner/test_wait_for_when_angular_hydration_then_adaptive_timeout.py
tests/unit/recorder/test_mutation_observer_when_field_changed_then_only_that_emitted.py
tests/unit/recorder/test_get_text_content_when_script_child_then_excluded.py
tests/unit/recorder/test_raw_events_flush_when_out_of_order_then_sorted.py
tests/regression/recording/test_r3_r8_no_timeout_3000_cascade.py
tests/regression/recording/test_r3_value_mutation_only_cpf_field_no_nis.py
tests/regression/recording/test_r6d_r8_no_script_in_textContent.py
```

**DoD**:
- [ ] Timeout adaptativo com config sistema
- [ ] MutationObserver diff (não full-form)
- [ ] textContent filter `<script>`/`<style>`
- [ ] raw_events sorted
- [ ] Recorder consistency retry

**Commits**:
1. `fix(runner): timeout adaptativo Angular hydration`
2. `fix(recorder): MutationObserver diff-only, não full-form snapshot`
3. `fix(recorder): getTextContent filter script/style children`
4. `fix(recorder): raw_events sort by timestamp no flush`
5. `fix(recorder): retry sanity id/role missing`

---

### FASE 9 — Taxonomy + lifecycle overhaul (~8h) — GRANDE

**Objetivo**: overhaul completo taxonomy/status/recording lifecycle.

**RCs cobertos**: RC-17 (16 bugs)

**Trabalho**:

**5.9.1 Taxonomy 4-níveis**:
- Suporte a `system/subsystem/suite/test_case` opcional.
- Fallback: `system/suite/test_case` (compat).
- Detecção automática do path hierarchy.

**5.9.2 Metadata reconciliation**:
- No compile, cross-check `metadata.system` vs `page_title` first occurrence — alert se divergem.
- CLI `testforge fix-metadata <rec>` interativa.

**5.9.3 Regravações dedup**:
- Hash sequence de raw_events → dedup detection.
- Ao criar novo rec, `if hash matches → prompt: use existing, replace, ou create new`.

**5.9.4 Sanitize convention única**:
- Normalize: `ç → c`, `á → a`, `ã → a`, `õ → o`, `é → e`, etc (canonical unicode NFD).
- Alertar user se typo suspeito.

**5.9.5 Uncategorized migration script**:
- CLI `testforge migrate-uncategorized <path>` — analisa recordings antigos.
- Infer `system/suite/test_case` de: `base_url`, `page_title`, `recording_id`.
- Interactive prompt user pra confirmar.

**5.9.6 `application` field depreciar**:
- Depreciar em favor de `application_type` enum (web/mobile/desktop).
- Migration compat: se antigo `application` = URL → migrate.

**5.9.7 Statuses schema unificado**:
- Enum: `recording`, `stopped`, `intent_complete`, `incomplete_intent`, `needs_review` (restaurado!), `ready_for_team`.
- Documentar em `docs/ARCHITECTURE-V2.md`.

**5.9.8 CLI `testforge fix-recording <path>`**:
- Permite iterar sobre recording existente sem regravar.
- Actions: add-assert, remove-step, edit-step, add-metadata.
- Salva versionado (git-like).

**5.9.9 Old recording alert**:
- Ao rodar `compile`/`run` em recording com `schema < CURRENT`, banner: "Recording criado antes de fixes X/Y/Z. Regravar recomendado. [Continuar/Cancelar]".

**5.9.10 recordings_failed lifecycle**:
- FAILED_MARKER usa relative path (não Windows absolute).
- README explicando pasta.
- Prune artifacts pesados (dom_snapshots) antes de mover.
- CLI `testforge recover-failed <id>` → move de volta pra `recordings/` + limpa marker.

**5.9.11 Recording duplicate suffix unificado**:
- Sempre `<name>_<YYYYMMDD-HHMMSS>` — deprecar `_2/_3/_N`.
- Migration: renomear existentes.

**Testes**:
```
tests/unit/taxonomy/test_metadata_when_path_4_levels_then_uses_subsystem.py
tests/unit/taxonomy/test_metadata_reconciliation_when_system_vs_title_diverge_then_alerts.py
tests/unit/recorder/test_regravacao_when_same_sequence_hash_then_prompts.py
tests/unit/taxonomy/test_sanitize_convention_when_c_cedilha_then_c.py
tests/integration/cli/test_migrate_uncategorized_when_run_then_infers_taxonomy.py
tests/unit/cli/test_fix_recording_when_add_assert_then_appends.py
tests/integration/recorder/test_old_recording_alert_when_schema_old_then_banner.py
tests/unit/recorder/test_failed_marker_uses_relative_path.py
tests/unit/recorder/test_recover_failed_when_id_then_moves_back.py
tests/integration/recorder/test_duplicate_suffix_uses_timestamp.py
```

**DoD**:
- [ ] Taxonomy 4-níveis suportada
- [ ] Metadata reconciliation
- [ ] Regravação dedup prompt
- [ ] Sanitize convention única (`terça → terca` sempre)
- [ ] Uncategorized migration script funciona nos 12 rec
- [ ] `application` depreciado com migration
- [ ] Statuses documentados
- [ ] `testforge fix-recording` CLI
- [ ] Old recording alert
- [ ] recordings_failed refactorado (README, relative path, prune, recover CLI)
- [ ] Sufixo timestamp único
- [ ] uncategorized/*: rodar migrate → todos com taxonomy válida
- [ ] consulta duplicados → 1 canonical + versionados

**Commits**:
1. `feat(taxonomy): suporte 4-níveis system/subsystem/suite/test_case`
2. `feat(taxonomy): metadata reconciliation cross-check page_title`
3. `feat(recorder): dedup regravações via hash sequence`
4. `fix(taxonomy): sanitize convention única unicode NFD`
5. `feat(cli): migrate-uncategorized com prompt interativo`
6. `feat(taxonomy): depreciar application, adotar application_type`
7. `feat(taxonomy): statuses schema unificado (needs_review restaurado)`
8. `feat(cli): fix-recording para iterar sobre existente`
9. `feat(recorder): banner old recording schema`
10. `fix(failed): FAILED_MARKER relative path + README + prune + recover CLI`
11. `fix(recorder): sufixo timestamp único, deprecate _2/_3`

---

## 6. Fases opcionais (P3-P4)

### FASE 10 — Assert em erro app, intent aggregation avançada, confidence heurística (~4h)
**RCs**: RC-14 partial, RC-23 (3 bugs), RC-28 (1 bug)

### FASE 11 — Detecção produção (~2h)
**RCs**: RC-20 (2 bugs) — block/alert domínios sem `-des/-tqs/-hom`.

### FASE 12 — healing_report + criteria breakdown (~2h)
**RCs**: RC-25 (1 bug), REC-84.

---

## 7. Ordem execução recomendada

```
FASE 1 (compliance) ──────────────────────────────→ URGENTE (bloqueia merge)
                     │
                     ├─ FASE 2 (steps.jsonl)
                     ├─ FASE 3 (overlay + healing)
                     └─ FASE 4 (mask amplification)
                            │
                            ├─ FASE 5 (diagnostic replay)
                            ├─ FASE 6 (seletores)
                            └─ FASE 7 (handlers específicos)
                                   │
                                   ├─ FASE 8 (timeout/diff/script)
                                   └─ FASE 9 (taxonomy overhaul) ── GRANDE
                                          │
                                          └─ FASE 10-12 (opcionais)
```

Fases 2-9 podem paralelizar em branches. Fase 1 gate obrigatório.

---

## 8. Critérios sucesso globais

**Antes de merge (após todas fases)**:
- [ ] Reprocessar 5 recordings representativos (R1, R2, R3, R4a, R7a) → 0 PII plaintext
- [ ] steps.jsonl inclui clicks/fills (não só asserts) em recordings novos
- [ ] `#next` reused resolve via role+text em replay
- [ ] R7a currency: 1 fill final (era 13 mutations)
- [ ] R3 CPF: 1 fill final (era 5 mutations)
- [ ] R6d password: 1 fill final (era 6 typing burst)
- [ ] R8 file upload: `set_input_files()` (era fill `C:\fakepath\`)
- [ ] R7a calendar: 1 date fill (era 7 clicks span)
- [ ] R2/R3 framework detection Angular OK
- [ ] R2/R3 Step 2 sem drift false positive
- [ ] uncategorized: 12 rec migrados com taxonomy
- [ ] Healing default ON

**Reporting**:
- Documento `docs/RECORDING-FIX-BASELINE.md` — reprocessar 5 recordings antes/depois com métricas quantitativas.
- Update `[[project-hotfix22-session-2026-07-01]]` memory com resultado por fase.

---

## 9. Anti-padrões (rejeitados)

- ❌ Fix em UMA fonte só (padrão histórico BUG-008: fix `_fill_input` mas não `value_mutation_collector`). Cada RC lista TODAS as fontes que precisam mudança.
- ❌ Ignorar recording antigo (schema=null). Migration explícita.
- ❌ Regravar recording pra testar fix (viola `[[feedback-no-regrave]]`). Iterar via `compile+run`.
- ❌ Fase 9 (taxonomy) sem plano de migração para recordings existentes.
- ❌ Adicionar bug detector novo (RC-20 production) sem policy configurável.
- ❌ Compliance fix parcial (mascarar só CPF, não CNPJ) — ALL patterns ou nenhum.

---

## 10. Referências

- Bugs originais: `.planning/bugs-recording-analysis.md`
- Plano anterior: `docs/HEALING-GAPS-PLAN.md` (Fases 1-9 shipadas)
- Padrão testes: `docs/TEST-PATTERNS.md`
- Handoff: `docs/HANDOFF-NEXT-LLM.md`
- Arquitetura: `docs/ARCHITECTURE-V2.md`
- Contrato no-regrave: `[[feedback-no-regrave]]`
- ARCHIVE bugs 001-018: `.planning/ARCHIVE/BUGS.md`
