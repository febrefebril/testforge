# Next session handoff — 2026-06-27

Continuação direta. Última sessão fechou em contexto 65%.

> **Ordem de leitura**: este arquivo → [EVIDENCE-ANALYSIS.md](EVIDENCE-ANALYSIS.md) → [REGRESSION-PATTERNS.md](REGRESSION-PATTERNS.md) → [BACKLOG.md](BACKLOG.md).

---

## Estado atual da branch `hotfix/sprint-0-recorder-fixes`

29 commits desde Sprint 0. Último: `38d1ab4 fix(normalizer): hotfix 22 — IntentReconstructor recovers masked-input values`.

**Commit pendente desta sessão** (será criado no fechamento):

- `.planning/EVIDENCE-ANALYSIS.md` — análise das 11 gravações em `evidencias/recordings.zip`
- `.planning/BACKLOG.md` — adicionados tickets H6-H19
- `.planning/REGRESSION-PATTERNS.md` — P3 recurrence count 3→4, hotfix 22 row, hard rule

---

## O que estava em andamento quando paramos

### 1. Análise das evidências do usuário ✅ ENTREGUE

Usuário forneceu `evidencias/recordings.zip` com 11 gravações de produção (SIOPI, SIMAX, SISGH, SIFAP, SIPBS-revendedor). Análise completa em `EVIDENCE-ANALYSIS.md`:

- **17 bugs identificados** (B1-B17).
- **14 tickets criados** (H6-H19).
- **2 bloqueadores críticos de piloto** identificados: H9 (HTTPS errors) e H16 (verdict false-positive).
- **5ª ocorrência do padrão P3** documentada (B16 — final_state schema sem labels).

### 2. Trabalhos parados antes da análise

Estes ficaram pendentes para esta sessão e devem entrar nos próximos commits:

- **Atualizar `tests/test_invariants.py`** com 2 novos round-trip tests:
  - `test_value_mutations_writer_reader_round_trip` (hotfix 22 — falta o invariante)
  - `test_raw_event_target_to_semantic_target_round_trip` (hotfix 22b — falta o invariante)

  Já referenciados em REGRESSION-PATTERNS.md P3 mas ainda não codificados. Bloqueiam a defesa estática prometida na "hard rule".

- **Atualizar `DECISIONS-LOG.md`** com entrada da análise de evidências (5ª ocorrência P3, 17 bugs achados, tickets H6-H19).

---

## Próximas ações priorizadas

Ordem decrescente de impacto. Cada uma é entregável independente.

### 🔴 H9 — `ignore_https_errors=True` no IncrementalRunner

**Custo**: ~20 min. **Bloqueia QA piloto Caixa**.

**Onde**: `src/testforge/runner/incremental_runner.py`, na criação do `browser.new_context(...)`. Adicionar `ignore_https_errors=True`. Verificar se há outras chamadas `new_context` (recorder, scripts compilados).

**Por quê**: 3 das 11 gravações falharam em step 1 com `ERR_CERT_AUTHORITY_INVALID` em `.apps.nprd.caixa`. Sem isso, 0% dos apps intranet rodam no piloto.

**Tests**: adicionar caso em `tests/test_runner_fill_paths.py` ou novo arquivo, mockando cert error. Inversão: rodar com `ignore_https_errors=False` deve ainda falhar; com `True` deve passar.

**Status**: cabe em sessão nova. Trivial.

### 🔴 H16 — Verdict semantics

**Custo**: ~30 min.

**Onde**: `src/testforge/validation/readiness_gate.py` (ou onde verdict é calculado). Atualmente `verdict=pass` se `criteria_passed == criteria_total` mesmo com 0 step runs.

**Mudança**: verdict `pass` exige TODAS as condições:
```python
verdict == "pass" iff (
    criteria_passed == criteria_total
    AND steps.passed > 0
    AND (steps.failed + steps.healing_rejected) == 0
)
```

Se passa critérios mas não rodou nenhum step → `verdict=gated_only` (semântica nova). Se rodou mas falhou → `fail`.

**Evidência**: `deve_logar_no_gas_do_povo_3` reporta `verdict=pass` com `steps=0`. Dashboard verde sem teste real. **Confiança do piloto depende disso**.

**Tests**: novo módulo `tests/test_verdict_semantics.py`. Pinar:
- 5 critérios + 0 steps → `gated_only` (não `pass`).
- 5 critérios + passed=N + 0 fail → `pass`.
- 5 critérios + qualquer fail → `fail`.

### 🟡 H6 — `_hookValue` não dispara em Material masked inputs

**Custo**: 2-4h (investigação + fix). **Não é trivial.**

**Investigação primeiro**:
1. Abrir Chromium DevTools em SIOPI calculadora.
2. Verificar se `HTMLInputElement.prototype.value` foi sobrescrito pelo overlay.
3. Tentar definir input.value via mask JS — observar se hook dispara.
4. Hipóteses:
   - Mask define `Object.defineProperty(el, 'value', ...)` por instância → shadow do nosso prototype hook.
   - Mask usa `el.setAttribute('value', ...)` → não dispara setter.
   - Hook não sobrevive Angular zone change.

**Possível fix**: instalar MutationObserver no `<input value>` attribute como redundância. Já existe template em `overlay_inject.js` ~line 300 para outros mutations.

**Status**: investigação necessária antes de patch. Não bloqueia piloto porque `final_state` recupera valores (hotfix 22 já consome eles).

### 🟡 H7 — Normalizer dedup multi-key

**Custo**: ~1h.

CPF gravado 2x: `"53986717749"` + `"539.867.177-49"`. Normalizer atual dedup por `element_id` igual; quando id vazio, não dedup.

**Onde**: `recording_normalizer.py:_compact_events` ou função similar de dedup de fills.

**Mudança**: dedup por chave composta `(aria_label_canonical | placeholder_canonical | element_id | css_path)`. Tomar o último valor do grupo.

### 🟡 H10 — SIMAX mat-select handler

**Custo**: ~2h.

3 gravações SIMAX falham em fill com `Element is not an <input>`. Mat-select é custom element. AngularMaterialHandler tem skeleton mas não está sendo invocado para SIMAX.

**Onde**: 
1. `recorder/overlay_inject.js:_extractTarget` — detectar mat-select e marcar como tag `mat-select`.
2. `recording_normalizer.py:_convert_step` — se tag=mat-select, ação="select_option" em vez de "fill".
3. `handlers/angular_material.py` — implementar `handle_select` se ainda skeleton.

---

## Tests de invariância pendentes

A "hard rule" gravada em REGRESSION-PATTERNS.md P3 promete que CADA artefato em disco tem round-trip test. Falta:

```python
# tests/test_invariants.py — TestP3UnanchoredState

def test_value_mutations_writer_reader_round_trip(self, tmp_path):
    """Write via overlay JS shape, read via _ir_value_mutations.
    Expected: at least 1 entry recovered."""

def test_raw_event_target_to_semantic_target_round_trip(self, tmp_path):
    """Write target with element_id key (overlay schema), read via
    _build_target. Expected: target.element_id matches."""

def test_final_state_snapshot_writer_reader_round_trip(self, tmp_path):
    """Pin B16. Write final_state with labels, read via _ir_final_state.
    Expected: labels survive."""
```

O terceiro é o mais crítico — ainda não implementado o WRITER com labels. Vide H19.

---

## Cuidados pra próxima sessão

1. **Não comitar arquivos em `.claude/worktrees/`** — são scratch de agentes anteriores. Ignorar com `.gitignore` quando refactor sprint começar.
2. **Antes de qualquer hotfix novo**: ler REGRESSION-PATTERNS.md. Se padrão matchar, fix DEVE atacar a classe.
3. **Antes de qualquer commit em `step_executor.py`**: rodar `pytest tests/test_invariants.py` — invariantes P1 garantem que `press_sequentially` continua em 1 lugar e métodos da classe não orfanam.
4. **B12 (verdict false-pass) é o maior risco do piloto**: priorizar H16 sobre tudo exceto H9.

---

## Telemetria — referência rápida

`.testforge/spans.jsonl` agora tem span `fill.attempted` com:
- `fill_path` (qual dos 4 helpers — hoje todos delegam a `_fill_masked`)
- `mask_kind` (`currency`, `date`, `none`)
- `mask_detect` (`attribute`, `placeholder`, `date_placeholder`, `none`)
- `cleared` (triple-click rodou)
- `value_len` (chars do input)
- `type_val_len` (após digit-strip)

Para debug futuro: `cat .testforge/spans.jsonl | grep fill.attempted | jq` mostra qual fill rodou. CS-3 da consolidação foi o item de maior ROI: hotfix 19 + 22 foram diagnosticados via spans.

---

## Para o usuário entender em 1 minuto

1. Análise de 11 gravações reais (5 sistemas Caixa) terminada.
2. 17 bugs identificados, 14 tickets novos no backlog.
3. **2 bloqueadores críticos** antes de liberar QA: H9 (cert HTTPS) e H16 (verdict mentiroso).
4. Padrão P3 (writer/reader mismatch) chegou a 5 ocorrências em 2 dias. Defesa estática precisa ser estendida.
5. Próxima sessão começa em H9 (~20 min) → H16 (~30 min) → piloto liberado.
