# Registro Diário — 2026-06-18

## Resumo

Sessão focada em **estabilizar a captura e execução de valores em campos com
currencymask (Angular Material)**, resolvendo falsos positivos de healing e
garantindo que valores digitados durante gravação sejam recuperáveis sem
re-gravação.

**10 commits**, **~1.500 linhas alteradas**, **4 arquivos fonte principais**.

---

## 1. Problema Central

O componente `dsc-input-currency` (Angular) chama `e.preventDefault()` no
evento `keydown`. Consequência:

- `input` event NÃO dispara → recorder não captura o valor
- Apenas `keydown`, `keypress`, `keyup` disparam
- Na execução, o step falha porque não há valor para preencher
- Healing tentava curar com selectores alternativos, mas sem valor o curry
  não tem contexto → falso positivo ou falha silenciosa

**Decisão arquitetural**: Recorder module is "closed" — no new event listeners.
Toda detecção e resolução é feita no normalizer e executor.

---

## 2. Commits (ordem cronológica)

| # | Hash | Tipo | Descrição |
|---|------|------|-----------|
| 1 | `0740a3d` | fix | Normalizer detecta missing fills em inputs currencymask — marca `needs_data_fill` |
| 2 | `061bc64` | fix | Reverte recorder, detecta no normalizer — recorder stays stable, normalizer smart |
| 3 | `03c3b44` | feat | Sugere template `--data` quando missing fills detectados |
| 4 | `a720e57` | feat | Recorder captura `form_values` no submit — normalizer propaga para input clicks |
| 5 | `f8fe74e` | feat | Blind spot audit — detecta `typing_not_captured`, `select_not_captured`, `long_gap` |
| 6 | `150c2ae` | feat | Polling safety net (`setInterval 300ms`) — captura QUALQUER mudança de valor |
| 7 | `ad37366` | feat | `FieldValueMap` dataclass com identifiers, intention, source no `SemanticTestCase` |
| 8 | `0c3bab8` | feat | `_build_field_value_map()` — cruza form_values, fill events, missing_fill |
| 9 | `5779e9f` | feat | Executor + runner usam field_value_map para matching preciso + fallback |
| 10 | `7654ea5` | fix | `getattr` para identifiers — suporta test fakes sem `element_id` |

---

## 3. Arquitetura do Field-Value Linking

### 3.1 Fluxo de dados

```
┌─────────────────────────────────────────────────────────────────────┐
│ RECORDING                                                           │
│                                                                     │
│  keydown → e.preventDefault() → ❌ input event                      │
│  setInterval(300ms) → polling → ✅ fill event (com valor final)    │
│  submit → form_values = {name: value} → ✅ form_values             │
└──────────────────────────┬──────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────────────┐
│ NORMALIZER                                                          │
│                                                                     │
│  raw_events.jsonl → _compact_fill_events → SemanticAction[]        │
│                                                                     │
│  1. _detect_overlay_steps()     ← calendar/dialog dedup exclusion  │
│  2. _deduplicate_steps()        ← remove identical consecutive     │
│  3. _detect_navigation_clicks() ← URL-changing clicks              │
│  4. _detect_missing_fills()     ← gap > 2s + no fill = missing     │
│     → context["missing_fill"] = True                                │
│     → context["fill_label"] = accessible_name|label|placeholder    │
│     → propaga form_values para input clicks anteriores             │
│  5. _audit_blind_spots()        ← relatório pós-recording          │
│  6. _build_field_value_map()    ← FieldValueMap[]                  │
│     → cada campo: value + intention + identifiers + source         │
│     → fontes: form_values > fill_event > missing_fill              │
└──────────────────────────┬──────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────────────┐
│ INCREMENTAL RUNNER                                                  │
│                                                                     │
│  stc.field_values → self._field_value_map                          │
│  _load_data_file() → cruza data_values com field_value_map         │
│  reporta: "📋 N campo(s) mapeado(s) com intenção"                  │
│  reporta: "⚠ N campo(s) sem valor — --data dados.json"             │
└──────────────────────────┬──────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────────────┐
│ STEP EXECUTOR                                                       │
│                                                                     │
│  _resolve_field_value(step, data_values, field_value_map)           │
│    → (value, intention)                                             │
│                                                                     │
│  Estratégias de matching (ordem):                                   │
│  1. field_value_map → exact match por identifier (name, aria-label,│
│     placeholder, id, label)                                         │
│  2. field_value_map → canonical key match                           │
│  3. data_values → exact match por identifier                        │
│  4. data_values → canonical key match                               │
│  5. data_values → substring match (legacy fallback)                 │
│                                                                     │
│  _inject_intention(step, value, intention)                          │
│    → step.context["resolved_value"]                                 │
│    → step.context["resolved_intention"]                             │
│                                                                     │
│  Se todas estratégias falham:                                       │
│    raise ValueError("fill_failed: '<intention>' value='<value>'")   │
│    → healer recebe intenção + valor no payload                      │
└─────────────────────────────────────────────────────────────────────┘
```

### 3.2 FieldValueMap (model.py)

```python
@dataclass
class FieldValueMap:
    field_key: str          # Canonical key (normalized)
    value: str              # Captured or provided value
    intention: str          # "fill Valor da Renda on input step 5"
    identifiers: dict       # {name, aria_label, placeholder, id, label}
    source: str             # "form_values" | "fill_event" | "missing_fill"
    step_index: int         # Step index in the recording
```

### 3.3 Fontes de valor (prioridade)

| Fonte | Como | Confiabilidade |
|-------|------|----------------|
| `form_values` | Capturado no `submit` — lê `el.value` de todos inputs | Alta — valor exato no momento do submit |
| `fill_event` | Evento `input` nativo ou polling `setInterval` | Média — pode ser valor parcial |
| `missing_fill` | Detectado por gap > 2s sem fill | Baixa — sem valor, precisa de `--data` |
| `data_file` | `--data dados.json` fornecido pelo usuário | Alta — depende do usuário |

---

## 4. Detalhamento dos Mecanismos

### 4.1 Missing Fill Detection (`_detect_missing_fills`)

- Input click + gap > 2s + no fill event following → `missing_fill = True`
- `fill_label` extraído de: `accessible_name` > `label` > `placeholder`
- `form_values` de submit propagado **para trás** para input clicks anteriores
- Steps com `form_values` já preenchidos são ignorados (não marcam missing)

### 4.2 Form Values Capture (recorder)

```javascript
// 3 linhas no handler de submit existente
var _formInputs = (form || document).querySelectorAll('input, textarea, select');
var _formValues = {};
_formInputs.forEach(function(inp) {
    var name = inp.name || inp.getAttribute('aria-label') || inp.placeholder || inp.id;
    if (name && inp.value && inp.value.trim()) {
        _formValues[name] = inp.value.trim();
    }
});
if (Object.keys(_formValues).length) {
    var _last = window.__tfEventQueue[window.__tfEventQueue.length - 1];
    if (_last && _last.type === 'submit') _last.form_values = _formValues;
}
```

### 4.3 Polling Safety Net (recorder)

```javascript
window.__tfLastValues = {};
window.__tfPollInterval = setInterval(function() {
    document.querySelectorAll('input, textarea, select').forEach(function(el) {
        var key = el.name || el.getAttribute('aria-label') || el.placeholder || el.id;
        if (!key) return;
        var val = (el.value || '').trim();
        if (val && val !== window.__tfLastValues[key]) {
            window.__tfLastValues[key] = val;
            _tf_pushEvent('fill', el);  // ← gera fill event mesmo sem input event
        }
    });
}, 300);
```

### 4.4 Blind Spot Audit (`_audit_blind_spots`)

Gera relatório de 3 padrões não capturados:

| Padrão | Detecção | Resolução |
|--------|----------|-----------|
| `typing_not_captured` | Click input + gap > 2s + no fill | `--data` ou `form_values` |
| `select_not_captured` | Click select + no select_option | `--data` |
| `long_gap` | Gap entre clicks > 10s | Revisão manual |

### 4.5 Field-Value Resolution (`_resolve_field_value`)

```python
# identifiers extraídos do step.target
ids = {"name": "renda", "aria_label": "Valor da Renda Familiar",
       "placeholder": "Ex: 5000", "id": "renda-input"}

# field_value_map (vindo do normalizer)
field_value_map = {
    "renda": FieldValueMap(value="5000", intention="fill renda familiar step 5", ...)
}

# data_values (vindo do --data)
data_values = {"renda": "7500", "entrada": "30000"}

# Matching priority:
# 1. field_value_map["renda"]["value"] → match por identifier "name"="renda"
# 2. field_value_map["renda"]["value"] → match canonical
# 3. data_values["renda"] → match por identifier
# 4. data_values["renda"] → match canonical
# 5. data_values["renda"] → match substring (legacy)
```

### 4.6 Intention-Aware Fallback

Quando executor tenta todas estratégias e falha:

```python
raise ValueError(
    f"fill_failed: '{intention}' value='{resolved_val}' "
    f"selector='{selector}' — nenhuma estrategia funcionou"
)
```

Runner captura exceção → `_heal_failed_step()` → healing payload inclui:
- `field_value`: valor resolvido
- `field_intention`: intenção do campo
- `intention`: descrição enriquecida

---

## 5. Arquivos Alterados

| Arquivo | Função | Linhas |
|---------|--------|--------|
| `src/testforge/recorder/recorder_controller.py` | Captura `form_values` + polling safety net | +47 |
| `src/testforge/semantic/model.py` | `FieldValueMap` dataclass | +30 |
| `src/testforge/semantic/recording_normalizer.py` | Missing fill, blind spots, field_value_map | +377 |
| `src/testforge/runner/step_executor.py` | `_resolve_field_value`, fallback com intenção | +198 |
| `src/testforge/runner/incremental_runner.py` | Carrega field_value_map, cruza data, healing | +55 |

---

## 6. Decisões Técnicas

1. **Recorder closed, normalizer smart**: Nenhum novo event listener no recorder.
   Toda lógica de detecção e resolução no normalizer e executor.

2. **Polling > events**: `setInterval(300ms)` captura changes que `input` event
   perde (Angular currencymask, React controlled inputs). Polling não requer
   mudanças no event system do recorder.

3. **Consequence-based waits > timeouts**: `_wait_for_consequence` espera pelo
   seletor do próximo step em vez de `page.wait_for_timeout`.

4. **Healing validation via oracle**: Curador propõe cura → oracle valida
   (post-condition) → `healed_validated` ou `healing_rejected`. Zero falso
   positivo.

5. **Form values propagate backward**: Submit captura valores de todos inputs →
   normalizer propaga para input clicks anteriores. Uma linha no recorder,
   lógica no normalizer.

6. **Intention-aware fallback**: Quando fill falha, o erro carrega intenção +
   valor para o healing pipeline, permitindo cura contextualizada.

---

## 7. Pendências

- **Step 12+ (quarta-feira, Pela renda)**: Seletor de resultado contém valor
  monetário dinâmico → `role=listitem[name="Valor mínimo de entrada R$ 13.514,64"]`
  não match com `--data`.
- **Step 14/15**: Assert step usa `#body` selector (genérico demais).
- **Result selectors**: Precisam de stripping de valores dinâmicos para
  match estável.
- **Blind spots estendidos**: Canvas, drag-drop, file upload ainda não cobertos.
- **`--data template` generation**: `run-incremental` imprime template textual;
  ideal seria gerar JSON automaticamente.

---

## 8. Métricas da Sessão

| Métrica | Valor |
|---------|-------|
| Commits | 10 |
| Arquivos alterados | 13 (4 fonte, 3 runs, 6 planning) |
| Linhas adicionadas | ~1.502 |
| Linhas removidas | ~24 |
| Testes passando | 120/122 (2 falhas pré-existentes) |
| Novos dataclasses | 1 (`FieldValueMap`) |
| Novos métodos | 5 (`_build_field_value_map`, `_canonical_field_key`,
  `_build_fill_intention`, `_resolve_field_value`, `_inject_intention`) |
