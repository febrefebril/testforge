# TestForge — Plano de Correção de Bugs

**Versão:** 0.3.1
**Data:** 2026-06-15
**Status:** ✅ Todos os 5 bugs corrigidos (100%)

---

Cada bug segue o ciclo BMAD: **Verificar → Corrigir → Testar**.

---

# BUG-1: TIM-001 — Healing não resolve timeout (FAM-02)

## 📋 US-B01-V: Verificar se o bug existe

**Objetivo:** Confirmar que o healing pipeline não resolve timeout em FAM-02.

**Passos:**
1. Navegar para `tests/test_pages/curation/fam-timing/index.html`
2. Clicar no botão "Carregar conteúdo" (que carrega após 5s)
3. Simular falha: o step_runner tenta `page.click()` e falha por timeout
4. Classificar erro: `Timeout 5000ms exceeded` → FAM-02 / TIM-005 ✅
5. L2 TimingAgent propõe `visibility_wait` (conf 0.80)
6. Step_runner tenta executar proposta → `page.click()` **NÃO implementa wait** → **FALHA**

**Resultado esperado do teste de verificação:** ❌ FAIL

**Teste automatizado:**
```bash
pytest tests/test_pages/test_curation_pipeline.py::TestHealingPipeline -k "FAM-02" -v
# Deve falhar: UNRESOLVED
```

**Status:** ✅ Verificado — Bug confirmado

---

## 📋 US-B01-F: Corrigir o bug

**Objetivo:** Implementar `visibility_wait` no step_runner para esperar elemento visível antes de clicar.

**Solução:**
- Criar `SmartStepRunner` com método `execute(step_data, strategy)`
- Se `strategy == "visibility_wait"` → `page.wait_for_selector(sel, state="visible", timeout=10000)`
- Injetar estratégia no `step_data` via `_build_step_copy(step_data, sel, strategy)`
- Atualizar `CuradorAutomatico` para passar `proposal.strategy` ao `_build_step_copy`

**Arquivos alterados:**
- `src/testforge/runner/fallback_runner.py` — novo `SmartStepRunner`
- `src/testforge/healing/curator.py` — `_build_step_copy` com parâmetro `strategy`
- `src/testforge/cli/app.py` — `_heal_step` usa `SmartStepRunner`

**Commit:** `c5c1d01`

**Status:** ✅ Corrigido

---

## 📋 US-B01-T: Testar a correção

**Objetivo:** Verificar que o healing pipeline agora resolve timeout em FAM-02.

**Passos:**
1. Rodar teste automatizado de healing para FAM-02
2. Verificar que `SmartStepRunner` detecta `visibility_wait` e espera o elemento
3. Verificar que o step é executado com sucesso após o wait

**Teste automatizado:**
```bash
pytest tests/test_pages/test_curation_pipeline.py::TestHealingPipeline -k "FAM-02" -v
# Deve passar: PASSED_STEP
```

**Resultado esperado:** ✅ PASS

**Critérios de aceite:**
- [x] `SmartStepRunner.execute()` suporta `visibility_wait`
- [x] `CuradorAutomatico` injeta estratégia no `patched_step`
- [x] Teste FAM-02 passa (PASSED_STEP)
- [x] Nenhuma regressão nos outros testes (124→124)

**Status:** ✅ Testado — Pass

---

---

# BUG-2: DOM-001 — Healing não resolve stale element (FAM-05)

## 📋 US-B02-V: Verificar se o bug existe

**Objetivo:** Confirmar que o healing pipeline não resolve stale element em FAM-05.

**Passos:**
1. Navegar para `tests/test_pages/curation/fam-dynamic-dom/index.html`
2. Elemento `#old-btn` é removido do DOM (simula SPA navigation)
3. Classificar erro: `stale element reference` → FAM-05 / DOM-001 ✅
4. L2 DynamicDOMAgent propõe `has_text_fallback` (conf 0.78)
5. Step_runner tenta `page.click()` com seletor antigo → **elemento não existe** → **FALHA**

**Resultado esperado do teste de verificação:** ❌ FAIL

**Teste automatizado:**
```bash
pytest tests/test_pages/test_curation_pipeline.py::TestHealingPipeline -k "FAM-05" -v
# Deve falhar: UNRESOLVED
```

**Status:** ✅ Verificado — Bug confirmado

---

## 📋 US-B02-F: Corrigir o bug

**Objetivo:** Step_runner usar `new_locator` da proposta (has_text_fallback) em vez do seletor antigo.

**Solução:**
- `SmartStepRunner.execute()` usa o seletor do `step_data` (que já foi substituído pelo `new_locator` da proposta via `_build_step_copy`)
- Estratégia `has_text_fallback` → tenta localizar por texto em vez de ID
- Adicionar `visibility_wait` antes da tentativa (elemento pode não ter renderizado ainda)

**Arquivos alterados:**
- `src/testforge/runner/fallback_runner.py` — `SmartStepRunner`
- `src/testforge/healing/curator.py` — `_build_step_copy` com estratégia

**Commit:** `c5c1d01`

**Status:** ✅ Corrigido

---

## 📋 US-B02-T: Testar a correção

**Objetivo:** Verificar que o healing pipeline resolve stale element.

**Teste automatizado:**
```bash
pytest tests/test_pages/test_curation_pipeline.py::TestHealingPipeline -k "FAM-05" -v
# Deve passar: PASSED_STEP
```

**Critérios de aceite:**
- [x] Step_runner usa `new_locator` (text-based) em vez do seletor antigo (ID)
- [x] `has_text_fallback` localiza elemento pelo texto
- [x] Teste FAM-05 passa (PASSED_STEP)
- [x] Nenhuma regressão

**Status:** ✅ Testado — Pass

---

---

# BUG-3: STA-001 — Healing não resolve overlay blocking (FAM-04)

## 📋 US-B03-V: Verificar se o bug existe

**Objetivo:** Confirmar que overlay bloqueia clique e healing não resolve.

**Passos:**
1. Navegar para `tests/test_pages/curation/fam-state/index.html`
2. Overlay cobre o botão `#target-btn`
3. Classificar erro: `element is not clickable — overlay intercepts` → FAM-04 / STA-002
4. StateAgent propõe `overlay_dismiss` (conf 0.75)
5. Step_runner tenta `page.click()` → **overlay bloqueia** → **FALHA**
6. Retry também falha → UNRESOLVED

**Resultado esperado do teste de verificação:** ❌ FAIL

**Teste automatizado:**
```bash
pytest tests/test_pages/test_curation_pipeline.py::TestHealingPipeline -k "FAM-04" -v
# Deve falhar: UNRESOLVED
```

**Status:** ✅ Verificado — Bug confirmado

---

## 📋 US-B03-F: Corrigir o bug

**Objetivo:** SmartStepRunner implementar `overlay_dismiss` — fechar overlays antes de clicar.

**Solução:**
- Criar `SmartStepRunner._dismiss_overlays()`:
  1. `page.keyboard.press("Escape")` — tenta fechar com ESC
  2. `page.click(".overlay")` — tenta clicar no overlay
  3. `page.click('[role="dialog"] .close')` — tenta botão fechar do modal
  4. `page.click(".modal .close")` — fallback
  5. `page.click(".cdk-overlay-backdrop")` — fallback Angular Material
- Se `strategy == "overlay_dismiss"`, chama `_dismiss_overlays()` antes do click

**Arquivos alterados:**
- `src/testforge/runner/fallback_runner.py` — `SmartStepRunner._dismiss_overlays()`

**Commit:** `c5c1d01`

**Status:** ✅ Corrigido

---

## 📋 US-B03-T: Testar a correção

**Objetivo:** Verificar que overlay é fechado e clique funciona.

**Teste automatizado:**
```bash
pytest tests/test_pages/test_curation_pipeline.py::TestHealingPipeline -k "FAM-04" -v
# Deve passar: PASSED_STEP
```

**Critérios de aceite:**
- [x] `_dismiss_overlays()` tenta ESC + 5 seletores de close
- [x] Overlay é removido antes do `page.click()`
- [x] Teste FAM-04 passa (PASSED_STEP)
- [x] Nenhuma regressão

**Status:** ✅ Testado — Pass

---

---

# BUG-4: INP-001 — Healing não resolve masked input (FAM-06)

## 📋 US-B04-V: Verificar se o bug existe

**Objetivo:** Confirmar que `page.fill()` falha em campo com máscara JS e healing não resolve.

**Passos:**
1. Navegar para `tests/test_pages/curation/fam-input/index.html`
2. Campo CPF tem máscara JS que bloqueia `fill()` direto
3. `page.fill()` é interceptado pela máscara → campo fica com valor incorreto
4. Classificar erro: `fill failed — input is masked` → FAM-06 / INP-007
5. InputAgent propõe `press_sequentially` (conf 0.82)
6. Step_runner tenta `page.fill()` → **máscara bloqueia** → **FALHA**

**Resultado esperado do teste de verificação:** ❌ FAIL

**Teste automatizado:**
```bash
pytest tests/test_pages/test_curation_pipeline.py::TestHealingPipeline -k "FAM-06" -v
# Deve falhar: UNRESOLVED
```

**Status:** ✅ Verificado — Bug confirmado

---

## 📋 US-B04-F: Corrigir o bug

**Objetivo:** SmartStepRunner usar `press_sequentially` para campos com máscara JS.

**Solução:**
- No `SmartStepRunner.execute()`:
  - Se `action == "fill"` e `strategy in ("press_sequentially", "masked_input_detection")`:
    - Usar `page.press_sequentially(sel, value, timeout=5000)` em vez de `page.fill()`
  - Senão, usar `page.fill()` normalmente

**Arquivos alterados:**
- `src/testforge/runner/fallback_runner.py` — `SmartStepRunner.execute()`

**Commit:** `c5c1d01`

**Status:** ✅ Corrigido

---

## 📋 US-B04-T: Testar a correção

**Objetivo:** Verificar que press_sequentially preenche campo com máscara corretamente.

**Teste automatizado:**
```bash
pytest tests/test_pages/test_curation_pipeline.py::TestHealingPipeline -k "FAM-06" -v
# Deve passar: PASSED_STEP
```

**Critérios de aceite:**
- [x] `SmartStepRunner` detecta `press_sequentially` e usa `page.press_sequentially()`
- [x] Campo CPF é preenchido corretamente (máscara não bloqueia)
- [x] Teste FAM-06 passa (PASSED_STEP)
- [x] Nenhuma regressão

**Status:** ✅ Testado — Pass

---

---

# BUG-5: CLS-001 — Classificação incorreta net::ERR_ (FAM-10)

## 📋 US-B05-V: Verificar se o bug existe

**Objetivo:** Confirmar que `net::ERR_CONNECTION_REFUSED` classifica errado.

**Passos:**
1. Classificar mensagem: `net::ERR_CONNECTION_REFUSED — request failed`
2. Classifier retorna FAM-02 / TIM-003 (timing)
3. Deveria retornar FAM-10 / OBS-003 (execution)

**Resultado esperado do teste de verificação:** Classificação incorreta

**Teste automatizado:**
```bash
pytest tests/test_pages/test_curation_pipeline.py::TestClassification -k "FAM-10" -v
# Deve falhar: expected FAM-10, got FAM-02
```

**Status:** ✅ Verificado — Bug confirmado

---

## 📋 US-B05-F: Corrigir o bug

**Objetivo:** Adicionar keyword específica para `connection refused` → FAM-10.

**Solução:**
- Adicionar keyword `("connection refused", "FAM-10", "OBS-003")` em `KEYWORD_PATTERNS`
- `net::ERR_` mantém mapeamento FAM-02 para `net::err_timed_out` e outros erros de rede/timing
- `connection refused` (18 chars) é mais específica e tem prioridade sobre `net::err` (8 chars)

**Arquivos alterados:**
- `src/testforge/taxonomy/taxonomy.py` — nova keyword

**Commit:** `c5c1d01`

**Status:** ✅ Corrigido

---

## 📋 US-B05-T: Testar a correção

**Objetivo:** Verificar classificação correta para erros de rede.

**Teste automatizado:**
```bash
pytest tests/test_pages/test_curation_pipeline.py::TestClassification -v
# Todos 11/11 passam
```

**Critérios de aceite:**
- [x] `connection refused` → FAM-10 / OBS-003
- [x] `net::ERR_TIMED_OUT` → FAM-02 / TIM-003 (não afetado)
- [x] `net::ERR_NAME_NOT_RESOLVED` → FAM-02 / TIM-003 (não afetado)
- [x] Teste de classificação 11/11 passa
- [x] Nenhuma regressão

**Status:** ✅ Testado — Pass

---

---

# Resumo

| Bug | Verificar | Corrigir | Testar | Status |
|-----|----------|----------|--------|--------|
| BUG-TIM-001 | ✅ | ✅ `visibility_wait` | ✅ PASS | Corrigido |
| BUG-DOM-001 | ✅ | ✅ `has_text_fallback` | ✅ PASS | Corrigido |
| BUG-STA-001 | ✅ | ✅ `overlay_dismiss` | ✅ PASS | Corrigido |
| BUG-INP-001 | ✅ | ✅ `press_sequentially` | ✅ PASS | Corrigido |
| BUG-CLS-001 | ✅ | ✅ keyword `connection refused` | ✅ PASS | Corrigido |

**15 stories · 5 bugs · 0 pendentes · 162 testes · 100% pass**

---

## Como rodar todos os testes de verificação

```bash
# Todos os testes de classificação (11/11)
pytest tests/test_pages/test_curation_pipeline.py::TestClassification -v

# Todos os testes de healing (5/5)
pytest tests/test_pages/test_curation_pipeline.py::TestHealingPipeline -v

# Suite completa (162/162)
pytest tests/ -v
```
