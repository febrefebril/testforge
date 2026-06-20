# ADR-006: Estratégia de Consumo de Evidência Downstream (Fase B)

**Status:** Accepted
**Data:** 2026-06-20

---

## Contexto

O Recorder (Fase A) captura `raw_events.jsonl` e arquivos de evidência associados
durante a gravação de uma sessão de usuário. Esses artefatos representam a intenção
bruta do usuário, mas não são diretamente consumíveis pelos módulos downstream:
o compilador precisa de valores de campo, e o validador precisa de completude de intenção.

Os módulos downstream (`RecordingNormalizer`, `PlaywrightCompiler`) precisavam de uma
estratégia explícita para reconstruir a intenção a partir das fontes disponíveis, com
prioridade clara quando duas fontes divergem, e um gate formal de qualidade antes de
promover um caso de teste para execução.

**Fontes de evidência disponíveis (Fase A → Fase B):**

| Arquivo | Conteúdo |
|---------|----------|
| `raw_events.jsonl` | eventos brutos (click, fill, keypress, submit, navigation) |
| `value_mutations.jsonl` | mutações programáticas de `.value` (setter hooks, currency masks) |
| `field_snapshots.jsonl` | snapshots de campo em tempo de gravação (value, checked, timestamps) |
| `network_log.json` | requisições POST/PUT com payloads de formulário |
| `final_state_snapshot.json` | dump JSON do estado final de todos os campos |

---

## Decisão

Adotar 5 estratégias de reconstrução de intenção com prioridade explícita, implementadas
em `IntentReconstructor`, mais um gate de completude com threshold 0.70 implementado em
`IntentCompletenessValidator`.

### 5 Estratégias de Reconstrução (ordem de prioridade)

| Prioridade | Estratégia | Fonte | Score |
|-----------|-----------|-------|-------|
| 1 | `form_values` | submit payload no evento de submissão | 100 |
| 2 | `fill_event` | evento `fill` do Playwright | 80 |
| 3 | `setter_hook` | `value_mutations.jsonl` (programmatic .value) | 78 |
| 4 | `checked_transition` | transição checked/unchecked em `field_snapshots.jsonl` | 72 |
| 5 | `snapshot_diff` | diff de valor entre snapshots consecutivos | 70 |
| 6 | `network_payload` | parsing de body POST/PUT em `network_log.json` | 60 |
| 7 | `final_state` | `final_state_snapshot.json` (fallback de último recurso) | 55 |
| 8 | `polling` | entradas periódicas de `field_snapshots.jsonl` | 50 |

Quando duas fontes capturam o mesmo campo (`field_key`), a entrada com score mais alto
prevalece. Empates são resolvidos pelo campo mais recente (`step_index` maior).

### Gate de Completude (threshold 0.70)

Após a reconstrução, `IntentCompletenessValidator.validate()` calcula:

```
score = campos_resolvidos / total_campos_fill
```

Onde `campos_resolvidos` inclui `resolved` e `resolved_with_warning`, mas exclui
`missing` e campos com blind spot de tipo `typing` (que rebaixam para `review_required`).

- `score >= 0.70` → gate aprovado, caso de teste pode ser promovido para Fase C
- `score < 0.70` → gate reprovado, campos ausentes listados em `missing_fields`

### Extensões implementadas na Fase B

**Polling strategy:** Entradas marcadas como `"polling"` em `field_snapshots.jsonl`
(capturadas por `interval_ms`) são tratadas como fonte separada com score 50, abaixo
de `final_state`. Permite capturar valores em formulários com auto-save sem evento fill.

**Masked field detection:** Valores com padrão de máscara (moeda, CPF, CNPJ, telefone,
data) recebem `is_masked=True` em `identifiers`. O `raw_value` original (antes da máscara)
é preservado quando disponível. Isso evita que o compilador injete `R$ 1.234,56` onde
a aplicação espera `1234.56`.

**Network confidence score:** Entradas de `network_payload` recebem `confidence` em
`identifiers` — 1.0 para match direto por nome de campo, 0.6 para match via URL fallback.
Permite que o consumidor decida se aceita evidência de baixa confiança.

**Compiler passthrough:** `PlaywrightCompiler.compile()` aceita `field_values` e
`data_file_dict`. Quando presentes, o compilador substitui `step.value` pelos valores
reconstruídos, produzindo scripts com fill rates mais altos em formulários complexos.

---

## Consequências

**Positivas:**

- Fase C pode executar `IntentCompletenessValidator` em batch para identificar gravações
  que precisam de `data file` externo antes de distribuição ao time de testers.
- O compilador gera scripts com fill rates mais altos sem depender de valores hardcoded
  nos passos semânticos.
- A cadeia de prioridade é explícita e testável — cada fonte tem um score fixo auditável.
- Campos mascarados não mais produzem fills com valores formatados incorretamente.

**Trade-offs aceitos:**

- A estratégia `polling` tem score baixo (50) para evitar sobrescrever evidências mais
  confiáveis. Isso significa que valores capturados por polling em formulários sem evento
  fill podem ser descartados em favor de `final_state` (55) — aceitável porque
  `final_state` representa o estado de commit da sessão.
- O threshold 0.70 é conservador. Casos de teste com muitos campos opcionais não preenchidos
  pelo usuário (e portanto ausentes no FieldValueMap) podem reprovar o gate mesmo que
  a intenção essencial esteja capturada. Fase C deverá avaliar se o threshold precisa
  de ajuste por tipo de formulário.
- `confidence = 0.6` para network URL fallback é um número heurístico. Fase C coletará
  dados reais para calibrar.

**Não impactado:**

- `SemanticTestCase` (YAML) continua sendo a fonte de verdade (ADR-0003 mantido).
- O modo shadow de healing (ADR-0001) não é afetado — Fase B atua antes da execução.

---

## Alternativas Consideradas

**Alternativa A — Fonte única (network_payload apenas):**
Simples, mas falha quando formulários não têm request de rede visível (formulários
SPA com state management sem fetch). Rejeitada.

**Alternativa B — Final state apenas:**
Baixo custo de implementação, mas perde informação de campos opcionais que o usuário
deixou em branco (vs. campos que o usuário nunca tocou). Rejeitada.

**Alternativa C — Threshold adaptativo por tipo de formulário:**
Mais preciso, mas requer classificação prévia de formulários. Adiado para Fase C
como melhoria no `IntentCompletenessValidator`.

---

**Referências:**

- `src/testforge/semantic/intent_reconstructor.py` — implementação das 5 estratégias
- `src/testforge/validation/intent_completeness.py` — gate de completude
- `src/testforge/semantic/compiler.py` — passthrough de field_values
- `docs/PHASE-B-RUNBOOK.md` — guia de debugging do pipeline
- `FASE-B-COMPLETION-REPORT.md` — métricas e critérios de aceitação
