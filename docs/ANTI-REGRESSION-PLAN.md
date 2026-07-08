# TestForge — Anti-Regression Plan

**Data**: 2026-07-07
**Motivo**: análise 92 bugs REC descobriu **4 regressões parciais confirmadas** em commits shipados. Padrão: fix aplicado em UMA fonte, esquece outras fontes que emitem mesmo tipo de dado.
**Contrato**: [[feedback-no-regression]]
**Escopo**: infra + processo que garante que fixes futuros NÃO regridem em fontes secundárias.

---

## 1. Regressões documentadas

| Commit | Fix esperado | Fonte coberta | Fonte VAZANDO | Bug REC |
|---|---|---|---|---|
| `2796c80` fix(Bug9) fill dedup | Single fill final por campo | `_fill_input` | `value_mutation_collector` | REC-07/19/48/51 (13x currency) |
| `f1c1881` fix(overlay) DD/MM/AAAA skip | Não capturar placeholder date | Fill events | value_mutations | REC-54 |
| `966f3bc` demote mat-input-N | Fingerprint dinâmico não primary | Fill fingerprint | value_mutation fingerprint | REC-52 |
| `2b151d5` fix(select) bugs 11-16 | SELECT tratamento correto | Compile/playback | `target.text` extraction | REC-30/69 |

**Padrão consistente**: cada fix cobre 1 pipeline stage, 2-4 stages relacionadas não são tocadas.

---

## 2. Root cause de regressões

**Data flow tem múltiplas fontes**:
```
DOM event
   ├→ _fill_input (fill event → raw_events)
   ├→ value_mutation_collector (MutationObserver → value_mutations.jsonl)
   ├→ field_snapshots (periodic scan → field_snapshots.jsonl)
   ├→ keystroke_buffer (keydown → keystroke_buffer.jsonl)
   ├→ overlay_inject.js (setter hook → __tf queues)
   └→ IR reconstruction (post-processing → semantic action)
```

Se bug afeta "input value", **todas as 6 fontes** precisam do mesmo tratamento. Historicamente fix aplicado em 1-2 fontes, deixando 4-5 vazando.

---

## 3. Infra anti-regressão (5 camadas)

### Camada 1 — Source Registry (documentação viva)

Arquivo: `docs/DATA-SOURCE-REGISTRY.md` (a criar).

Documenta TODAS as fontes por tipo de dado emitido. Formato:

```markdown
## Tipo: input value (`str`)
Fontes:
1. `src/testforge/recorder/overlay_inject.js:_fill_input` → `raw_events.jsonl`
2. `src/testforge/recorder/overlay_inject.js:_snapshotFields` (setInterval 2s) → `field_snapshots.jsonl`
3. `src/testforge/recorder/overlay_inject.js:MutationObserver value` → `value_mutations.jsonl`
4. `src/testforge/recorder/overlay_inject.js:setter_hook` → `__tfSetterQueue`
5. `src/testforge/recorder/keystroke_buffer.js` → `keystroke_buffer.jsonl`
6. `src/testforge/semantic/recording_normalizer.py:_ir_value_mutations` → `SemanticAction.value`

Invariantes:
- Nenhuma fonte emit placeholder (`DD/MM/AAAA`, `c999999`, etc)
- Nenhuma fonte emit valor com whitespace leading/trailing (currency masks)
- Fingerprint estável (não `mat-input-N` sozinho — combinar com placeholder + label + accessible_name)
```

**Uso**: antes de fix, dev consulta registry pra ver quais fontes tocar.

### Camada 2 — Contract Tests cross-source (pytest)

Diretório: `tests/contract/`.

Para cada tipo de dado + invariante, 1 teste que **percorre TODAS as fontes** e valida invariante.

Exemplo:
```python
# tests/contract/test_no_source_emits_placeholder_dd_mm_aaaa.py

@pytest.mark.contract
@pytest.mark.critical
def test_no_source_emits_placeholder_dd_mm_aaaa():
    """Invariante cross-source: nenhuma fonte pode emitir valor 'DD/MM/AAAA' que é
    placeholder de date input Angular Material.
    
    Fontes verificadas:
    - raw_events.jsonl (fill events)
    - value_mutations.jsonl
    - field_snapshots.jsonl
    - keystroke_buffer.jsonl (keystroke não emit value final — skip)
    - IR SemanticAction.value
    
    Regressão histórica: f1c1881 fix apenas fill events, value_mutations continuou emitindo.
    """
    # Arrange
    rec = load_recording_fixture("simax_calendar_material_r7a")
    
    # Act
    raw = load_jsonl(rec / "raw_events.jsonl")
    vm = load_jsonl(rec / "value_mutations.jsonl")
    fs = load_jsonl(rec / "field_snapshots.jsonl")
    ir = reconstruct_ir(rec)
    
    # Assert
    assert not any(e.get("value") == "DD/MM/AAAA" for e in raw), \
        "raw_events emit placeholder DD/MM/AAAA"
    assert not any(m.get("value") == "DD/MM/AAAA" for m in vm), \
        "value_mutations emit placeholder DD/MM/AAAA (regressão f1c1881)"
    assert not any(
        snap.get("value") == "DD/MM/AAAA"
        for batch in fs for snap in batch.get("snapshots", [])
    ), "field_snapshots emit placeholder"
    assert not any(action.value == "DD/MM/AAAA" for action in ir.actions), \
        "IR SemanticAction emit placeholder"
```

Toda RC do plano de fix ganha 1+ contract test.

### Camada 3 — Recording Âncora + Golden Files

Diretório: `tests/fixtures/recordings/` — recordings âncora versionados no git.

Escolher **10 recordings representativos** (1 por RC crítico):
- `r1_massa_de_teste_login_form/` (RC-1 PII + RC-31 Keycloak)
- `r3_plataforma_des_cliente_pii/` (RC-1 PII cliente)
- `r4a_portal_massa_select_cnpj/` (RC-10 select textContent)
- `r6d_sifec_password_typing_hell/` (RC-4 typing burst)
- `r7a_siopi_currency_mask_13x/` (RC-4 currency amplification)
- `r7b_siopi_asserts_nth_of_type/` (RC-9 seletores frágeis)
- `r8_sisgh_file_upload/` (RC-11 file input)
- `r9_simax_select_option/` (RC-4 select_option + RC-10)
- `r10_uncategorized_schema_null/` (RC-17 taxonomy migration)
- `r11_failed_marker/` (RC-17 failed lifecycle)

Cada âncora tem golden files `expected/`:
- `expected/raw_events.jsonl` — output canônico após reprocess
- `expected/steps.jsonl`
- `expected/value_mutations.jsonl`
- `expected/pii_audit_report.json` (para RC-1)

**Uso em CI**:
```python
# tests/regression/test_anchor_recordings.py

@pytest.mark.regression
@pytest.mark.critical
@pytest.mark.parametrize("anchor", ANCHOR_RECORDINGS, ids=lambda a: a.name)
def test_reprocess_anchor_matches_golden(anchor):
    # Arrange
    rec_dir = FIXTURES / anchor.name
    expected_dir = rec_dir / "expected"
    
    # Act — reprocess com código atual
    actual = reprocess_recording(rec_dir)
    
    # Assert por artifact
    for artifact in ["raw_events.jsonl", "steps.jsonl", "value_mutations.jsonl"]:
        expected = load_jsonl(expected_dir / artifact)
        actual_data = actual[artifact]
        assert normalize(actual_data) == normalize(expected), \
            f"{anchor.name}/{artifact} diverge do golden. Diff: {diff(expected, actual_data)}"
```

**Regra golden update**: se golden file precisa mudar, PR deve:
- Explicar por que (novo bug fixado? feature nova?)
- Ter aprovação de reviewer diferente
- Documentar diff em CHANGELOG

### Camada 4 — Multi-Source Coverage Matrix (obrigatório em PR)

Template de PR: `.github/PULL_REQUEST_TEMPLATE/recording_fix.md` (a criar).

```markdown
## Recording bug fix

**Bug ID**: BUG-REC-XX (link para .planning/bugs-recording-analysis.md)

## Multi-source coverage matrix

Data type affected: `<input value | url | selector | ...>`

| Source | Affected | Fix applied | Test |
|---|---|---|---|
| `_fill_input` (overlay_inject.js) | ✓ | ✓ | test_XXX |
| `value_mutation_collector` | ✓ | ✓ | test_YYY |
| `field_snapshots` | ✓ | ✓ | test_ZZZ |
| `keystroke_buffer` | ✗ (irrelevant) | - | - |
| `IR reconstruction` | ✓ | ✓ | test_WWW |

**Explanation**: <por que fontes não afetadas não foram tocadas>

## Anchor recording

- [ ] Recording âncora escolhido: `<name>`
- [ ] Reprocess executado localmente
- [ ] Golden file atualizado (ou verificação passa contra golden existente)
- [ ] Contract test cross-source passa

## Regression tests

- [ ] Test que reproduz bug ANTES do fix (falha em `main`)
- [ ] Test passa com fix
- [ ] Golden diff explicado em CHANGELOG
```

### Camada 5 — CI Gate obrigatório

`.github/workflows/anti-regression.yml`:

```yaml
name: anti-regression
on: [pull_request]

jobs:
  contract-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Run contract tests
        run: pytest tests/contract/ -m critical --strict-markers
      - name: Run anchor reprocess
        run: pytest tests/regression/test_anchor_recordings.py --strict-markers
      - name: Check PII detector coverage
        run: python scripts/verify_pii_patterns_all_sources.py
```

CI bloqueia merge se qualquer contract test / anchor test falhar.

---

## 4. Registro histórico de regressões

Arquivo: `.planning/regression-history.md` (a criar).

Cada regressão observada → entry:
- Data
- Commit original (fix parcial)
- Bugs REC descobertos
- Fontes que faltaram cobrir
- Fix definitivo (commit)
- Lição aprendida

**Uso**: onboarding + fase-checklist "vi essa família antes?".

---

## 5. Aplicação prática (Fase 1 RECORDING-BUGS-FIX-PLAN revisada)

Ao executar **Fase 1 (compliance alert-only, revisado)**:

1. **Antes**: consultar `docs/DATA-SOURCE-REGISTRY.md` — quais fontes contêm PII?
2. **Durante**: escrever contract test antes do fix. Test falha em `main`.
3. **Durante**: escolher recording âncora (R1, R3, R4a) → salvar como fixture.
4. **Após**: reprocess recording âncora → validar output esperado → escrever golden.
5. **PR**: template com matriz multi-source preenchida.
6. **Merge**: CI verde nas 3 camadas (unit, contract, anchor).

---

## 6. Custo de implementação

**Setup inicial (~4h)**:
- Criar `docs/DATA-SOURCE-REGISTRY.md` skeleton (30 min)
- Criar 10 recordings âncora com golden files (2h — 12 min cada)
- Template PR + workflow CI (1h)
- Skeleton contract test framework (30 min)

**Custo por fix (adicional)**:
- Preencher matriz multi-source: 10 min
- Contract test cross-source: 20-40 min
- Reprocess âncora + verify golden: 15 min
- Total overhead: **~1h por PR**

**ROI**: cada regressão evitada = economiza 3-8h de debugging pós-produção.

---

## 7. Anti-padrões proibidos

- ❌ PR sem matriz multi-source preenchida.
- ❌ Contract test que só cobre 1 fonte.
- ❌ Regression test que usa mock em vez de recording âncora real.
- ❌ Fix aprovado sem reprocess de recording âncora.
- ❌ Golden file atualizado sem justificativa em CHANGELOG.
- ❌ Ignorar `DATA-SOURCE-REGISTRY.md` porque "só é bug em 1 lugar".

---

## 8. Referências

- Contrato: `[[feedback-no-regression]]`
- Bugs originais: `.planning/bugs-recording-analysis.md`
- Plano fix: `docs/RECORDING-BUGS-FIX-PLAN.md`
- Padrão testes: `docs/TEST-PATTERNS.md`
- Historico regressões: `.planning/regression-history.md`
