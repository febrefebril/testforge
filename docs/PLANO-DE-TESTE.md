# TestForge v0.3.0 — Plano de Teste Manual

**Versão:** 0.3.0
**Data:** 2026-06-15
**Objetivo:** Validar manualmente todas as funcionalidades do TestForge
**Pré-requisitos:** `source activate.sh`, fake-bank rodando em `localhost:8765`

---

## Setup

```bash
cd testforge-v1
source activate.sh
cd synthetic_lab/fake-react-bank-app && python -m http.server 8765 &
cd ../..
```

---

## TC-01: Gravação de Fluxo

### TC-01.01: Gravar fluxo simples no fake-bank

| Campo | Valor |
|-------|-------|
| **Objetivo** | Verificar que o recorder captura eventos de fill e click |
| **Pré-condição** | Fake-bank rodando em `localhost:8765` |

**Passos:**
1. Execute: `testforge record http://localhost:8765 --name "TC-01"`
2. No navegador que abrir, preencha o campo CPF com `12345678900`
3. Clique no botão **Pesquisar**
4. Aguarde o resultado aparecer
5. Pressione **Shift+S** para parar a gravação

**Resultado esperado:**
- [ ] Console mostra `[TestForge] ✓ N passos gravados`
- [ ] Console mostra `[TestForge] Sessao salva: recordings/TC-01/`
- [ ] Diretório `recordings/TC-01/` existe
- [ ] `raw_events.jsonl` contém eventos de fill e click
- [ ] `screenshots/` contém screenshots

**Status:** [ ] PASS  [ ] FAIL

---

### TC-01.02: Gravar com nome com espaço e caracteres especiais

| Campo | Valor |
|-------|-------|
| **Objetivo** | Verificar sanitização de nomes |

**Passos:**
1. Execute: `testforge record http://localhost:8765 --name "teste @ especial!"`
2. Faça uma interação simples (fill + click)
3. Pressione **Shift+S**

**Resultado esperado:**
- [ ] Nome sanitizado: `recordings/teste_especial/` (sem @, sem !)
- [ ] Gravação salva corretamente

**Status:** [ ] PASS  [ ] FAIL

---

### TC-01.03: Usar modo Assert durante gravação

| Campo | Valor |
|-------|-------|
| **Objetivo** | Verificar captura de asserts |

**Passos:**
1. Execute: `testforge record http://localhost:8765 --name "TC-assert"`
2. Preencha CPF e clique Pesquisar
3. Quando o resultado aparecer, pressione **Shift+A**
4. Selecione o tipo de assert (Textual)
5. Selecione o elemento de resultado na tela
6. Confirme o valor esperado
7. Pressione **Shift+S**

**Resultado esperado:**
- [ ] `raw_events.jsonl` contém evento do tipo `assert`
- [ ] Evento de assert tem `assert_type`, `selector`, `expected_value`

**Status:** [ ] PASS  [ ] FAIL

---

## TC-02: Compilação

### TC-02.01: Compilar gravação para script

| Campo | Valor |
|-------|-------|
| **Objetivo** | Verificar geração de script Playwright |

**Passos:**
1. Execute: `testforge compile TC-01`
2. Verifique a saída

**Resultado esperado:**
- [ ] `[TestForge] ✓ SemanticTestCase: N steps`
- [ ] `[TestForge] ✓ Script gerado: semantic_tests/ST-TC-01/test_st_tc_01.py`
- [ ] `[TestForge] ✓ Script compila sem erros`
- [ ] Script contém `from playwright.sync_api import Page, expect`
- [ ] Script contém fallback loop (`for _sel in _sels: try: ... except:`)
- [ ] Script contém `BASE_URL`

**Status:** [ ] PASS  [ ] FAIL

---

### TC-02.02: Compilar com massa de dados externa (--data)

| Campo | Valor |
|-------|-------|
| **Objetivo** | Verificar extração de test_data.json e script data-driven |

**Passos:**
1. Execute: `testforge compile TC-01 --data`
2. Verifique os arquivos gerados

**Resultado esperado:**
- [ ] `[TestForge] ✓ Massa de dados: .../test_data.json`
- [ ] `[TestForge] ✓ Script data-driven (le test_data.json)`
- [ ] `semantic_tests/ST-TC-01/test_data.json` existe
- [ ] JSON contém `"fields"` com os valores preenchidos
- [ ] Script contém `_data.get("cpf", "12345678900")`
- [ ] Alerta de campo sensível (CPF) é exibido

**Status:** [ ] PASS  [ ] FAIL

---

### TC-02.03: Compilar com caminho relativo (recordings/)

| Campo | Valor |
|-------|-------|
| **Objetivo** | Verificar que compile aceita `recordings/` prefix |

**Passos:**
1. Execute: `testforge compile recordings/TC-01`

**Resultado esperado:**
- [ ] Compilação funciona (não duplica `recordings/recordings/`)
- [ ] Script gerado corretamente

**Status:** [ ] PASS  [ ] FAIL

---

## TC-03: Execução

### TC-03.01: Executar script sem falhas (fake-bank)

| Campo | Valor |
|-------|-------|
| **Objetivo** | Verificar execução inline com todos os passos passando |

**Passos:**
1. Execute: `testforge run semantic_tests/ST-TC-01/test_st_tc_01.py`
2. Observe o output

**Resultado esperado:**
- [ ] Todos os steps mostram `✓ Step N: ...`
- [ ] Nenhum step mostra `✗` ou `skip`
- [ ] Métricas mostram `Total runs: 1`, `Healings: 0`
- [ ] `Healer:` mostra o tipo (Mock/LLM real)

**Status:** [ ] PASS  [ ] FAIL

---

### TC-03.02: Executar com script data-driven

| Campo | Valor |
|-------|-------|
| **Objetivo** | Verificar que script lê dados do JSON externo |

**Passos:**
1. Edite `semantic_tests/ST-TC-01/test_data.json` e mude o CPF para `99988877766`
2. Execute: `testforge run semantic_tests/ST-TC-01/test_st_tc_01.py`

**Resultado esperado:**
- [ ] Script usa o novo CPF do JSON (visível no output)
- [ ] Resultado no fake-bank mostra o CPF alterado
- [ ] Sem necessidade de recompilar

**Status:** [ ] PASS  [ ] FAIL

---

## TC-04: Healing — Fake Bank com Mutações

### TC-04.01: L1 — FallbackRunner (change_id)

| Campo | Valor |
|-------|-------|
| **Objetivo** | Verificar que L1 cura mudança de ID |

**Passos:**
1. Execute: `testforge demo-heal`
2. Observe cada fase

**Resultado esperado:**
- [ ] Fase 1: `✓ N eventos gravados`
- [ ] Fase 2: `✓ Script: semantic_tests/ST-HEAL/test_st-heal.py`
- [ ] Fase 3: `Seletor original #btnPesquisar: NAO EXISTE (quebrado!)`
- [ ] Fase 4: `✓ Clique com candidato alternativo funcionou!`
- [ ] Fase 5: `✓ visual_dom: passed`, `✓ business_state: passed`
- [ ] `✅ HEALING FUNCIONOU!`

**Status:** [ ] PASS  [ ] FAIL

---

### TC-04.02: L3 — MockLLMHealer cura seletor quebrado

| Campo | Valor |
|-------|-------|
| **Objetivo** | Verificar que MockLLMHealer propõe seletor alternativo |

**Passos:**
1. Execute `testforge compile TC-01 --data`
2. Edite o script gerado: mude `BASE_URL` para `http://localhost:8765/?mutation=change_id`
3. Execute: `testforge run semantic_tests/ST-TC-01/test_st_tc_01.py`

**Resultado esperado:**
- [ ] Step de click falha (botão com ID quebrado)
- [ ] Classifier: `FAM-01 / SEL-004`
- [ ] Healer: `MockLLMHealer` (ou `LLM real` se Azure configurado)
- [ ] Curador mostra `[L3]` ou `[L2]`
- [ ] Proposal tem `strategy: has_text_fallback` e `locator: text=Pesquisar`
- [ ] Step curado: `✓` após healing

**Status:** [ ] PASS  [ ] FAIL

---

### TC-04.03: Auto-learn — receita salva no catálogo

| Campo | Valor |
|-------|-------|
| **Objetivo** | Verificar que cura bem-sucedida é registrada |

**Passos:**
1. Após TC-04.02 passar, verifique o catálogo: `cat .planning/healing-catalog.jsonl | tail -1`
2. Execute o mesmo teste novamente

**Resultado esperado:**
- [ ] Catálogo contém nova entrada com `trigger_code: SEL-004`
- [ ] Na segunda execução, o curador usa `[L0]` (catálogo) em vez de L3
- [ ] L0 é mais rápido (<50ms vs chamada LLM)

**Status:** [ ] PASS  [ ] FAIL

---

## TC-05: Healing — Páginas de Curadoria

### TC-05.01: FAM-01 — Selector healing (ID dinâmico)

| Campo | Valor |
|-------|-------|
| **Objetivo** | Verificar healing de seletor quebrado |
| **Setup** | Servidor de teste: `python -m http.server 8770 -d tests/test_pages` |

**Passos (via teste automatizado):**
```bash
python -m pytest tests/test_pages/test_curation_pipeline.py::TestHealingPipeline -k "FAM-01" -v
```

**Resultado esperado:**
- [ ] Teste `test_heal_error_mode[curation/fam-selector-FAM-01...]` → PASSED

**Status:** [ ] PASS  [ ] FAIL

---

### TC-05.02: FAM-02 — Timing healing (conteúdo com delay)

```bash
python -m pytest tests/test_pages/test_curation_pipeline.py::TestHealingPipeline -k "FAM-02" -v
```

**Resultado esperado:**
- [ ] Teste → PASSED

**Status:** [ ] PASS  [ ] FAIL

---

### TC-05.03: FAM-04 — State healing (overlay bloqueando)

```bash
python -m pytest tests/test_pages/test_curation_pipeline.py::TestHealingPipeline -k "FAM-04" -v
```

**Resultado esperado:**
- [ ] Teste → PASSED (overlay dismiss funciona)

**Status:** [ ] PASS  [ ] FAIL

---

### TC-05.04: FAM-05 — Dynamic DOM healing (stale element)

```bash
python -m pytest tests/test_pages/test_curation_pipeline.py::TestHealingPipeline -k "FAM-05" -v
```

**Resultado esperado:**
- [ ] Teste → PASSED

**Status:** [ ] PASS  [ ] FAIL

---

### TC-05.05: FAM-06 — Input healing (masked field)

```bash
python -m pytest tests/test_pages/test_curation_pipeline.py::TestHealingPipeline -k "FAM-06" -v
```

**Resultado esperado:**
- [ ] Teste → PASSED (press_sequentially funciona)

**Status:** [ ] PASS  [ ] FAIL

---

## TC-06: Classification (Classificador de Falhas)

### TC-06.01: Classificar falhas por família

```bash
python -m pytest tests/test_pages/test_curation_pipeline.py::TestClassification -v
```

**Resultado esperado:**
- [ ] 11/11 testes passam
- [ ] FAM-01 a FAM-11 todos classificados corretamente

**Status:** [ ] PASS  [ ] FAIL

---

### TC-06.02: Classificar manualmente via Python

```python
from testforge.taxonomy import FailureClassifier
c = FailureClassifier()

# Locator
r = c.classify("strict mode violation: '#btn' resolved to 0 elements")
assert r.family_code == "FAM-01"  # SEL-004

# Overlay
r = c.classify("element is obscured by overlay")
assert r.family_code == "FAM-04"  # STA-002

# Timeout
r = c.classify("Timeout 5000ms exceeded waiting for selector")
assert r.family_code == "FAM-02"  # TIM-005

# Stale
r = c.classify("stale element reference: element is not attached to the DOM")
assert r.family_code == "FAM-05"  # DOM-001

print("✓ All 4 classifications correct")
```

**Resultado esperado:**
- [ ] Todas as 4 classificações corretas

**Status:** [ ] PASS  [ ] FAIL

---

## TC-07: Evidence Collection

### TC-07.01: Coletar evidências de página

```python
from playwright.sync_api import sync_playwright
from testforge.evidence import EvidenceCollector

with sync_playwright() as pw:
    browser = pw.chromium.launch(headless=True)
    page = browser.new_page()
    
    collector = EvidenceCollector(page)
    collector.start("test-evidence")
    page.goto("http://localhost:8765")
    page.wait_for_timeout(500)
    
    payload = collector.build_llm_payload({
        "action": "click", "selector": "#btn",
        "text": "Pesquisar", "intention": "Click search",
        "url": page.url, "framework": "react",
    })
    
    assert payload.is_sufficient
    assert len(payload.dom_snapshot) >= 100
    assert "Pesquisar" in payload.dom_snapshot
    print(f"✓ Evidence: {len(payload.dom_snapshot)} chars DOM, "
          f"{len(payload.console_errors)} console, "
          f"{len(payload.network_state)} network")
    browser.close()
```

**Resultado esperado:**
- [ ] `is_sufficient = True`
- [ ] DOM ≥ 100 chars
- [ ] DOM contém elementos da página

**Status:** [ ] PASS  [ ] FAIL

---

## TC-08: Data-Driven Testing

### TC-08.01: Extrair, modificar e reexecutar

| Campo | Valor |
|-------|-------|
| **Objetivo** | Verificar ciclo completo data-driven |

**Passos:**
1. `testforge compile TC-01 --data`
2. Edite `semantic_tests/ST-TC-01/test_data.json`: mude CPF para `11122233344`
3. `testforge run semantic_tests/ST-TC-01/test_st_tc_01.py`

**Resultado esperado:**
- [ ] Script usa o CPF do JSON (visível no log)
- [ ] Fake-bank mostra `CPF consultado: 11122233344`
- [ ] Nenhuma recompilação necessária

**Status:** [ ] PASS  [ ] FAIL

---

### TC-08.02: Múltiplos cenários (--scenarios)

| Campo | Valor |
|-------|-------|
| **Objetivo** | Verificar formato de múltiplos cenários |

**Passos:**
1. `testforge compile TC-01 --data --scenarios`
2. Verifique o JSON gerado

**Resultado esperado:**
- [ ] JSON tem formato `{"scenarios": {"default": {"cpf": "..."}}}`
- [ ] Script suporta múltiplos cenários

**Status:** [ ] PASS  [ ] FAIL

---

## TC-09: Edge Cases

### TC-09.01: Compilar sem gravação

```bash
testforge compile NAO-EXISTE
```

**Resultado esperado:**
- [ ] `[TestForge] ✗ Gravacao nao encontrada: ...`

**Status:** [ ] PASS  [ ] FAIL

---

### TC-09.02: Executar script inexistente

```bash
testforge run /caminho/inexistente.py
```

**Resultado esperado:**
- [ ] `[TestForge] ✗ Script nao encontrado: ...`

**Status:** [ ] PASS  [ ] FAIL

---

### TC-09.03: Recording sem steps de fill (só clicks)

| Campo | Valor |
|-------|-------|
| **Objetivo** | Verificar data extractor com gravação sem fills |

**Passos:**
1. Grave um fluxo que só tem clicks (sem preencher campos)
2. Compile com `--data`

**Resultado esperado:**
- [ ] JSON gerado com `"fields": {}` (vazio)
- [ ] Sem erro ou crash
- [ ] Script funciona normalmente (valores hardcoded)

**Status:** [ ] PASS  [ ] FAIL

---

### TC-09.04: Timeout na execução

| Campo | Valor |
|-------|-------|
| **Objetivo** | Verificar comportamento com timeout |

**Passos:**
1. Compile um script que acessa URL externa lenta
2. Execute com `--timeout 5`

**Resultado esperado:**
- [ ] `[TestForge] ⚠ Timeout (5s)`
- [ ] Healing pipeline inicia após timeout
- [ ] Não crasha

**Status:** [ ] PASS  [ ] FAIL

---

## TC-10: LLM Real (se Azure configurado)

### TC-10.01: Verificar ativação do LLM

```bash
export AZURE_OPENAI_ENDPOINT="https://seu-recurso.openai.azure.com/"
export AZURE_OPENAI_DEPLOYMENT="gpt-4.1-mini"
testforge run semantic_tests/ST-TC-01/test_st_tc_01.py
```

**Resultado esperado:**
- [ ] Output mostra `Healer: LLM real (Azure/OpenAI)`
- [ ] Se ocorrer falha, curador chama LLM (layer L3)
- [ ] LLM retorna proposta com confidence > 0

**Status:** [ ] PASS  [ ] FAIL  [ ] N/A (sem Azure)

---

## Resumo de Resultados

| TC | Descrição | Status |
|----|-----------|--------|
| TC-01.01 | Gravar fluxo simples | [ ] |
| TC-01.02 | Gravar com nome especial | [ ] |
| TC-01.03 | Modo Assert | [ ] |
| TC-02.01 | Compilar gravação | [ ] |
| TC-02.02 | Compilar com --data | [ ] |
| TC-02.03 | Compilar com prefixo | [ ] |
| TC-03.01 | Executar sem falhas | [ ] |
| TC-03.02 | Executar data-driven | [ ] |
| TC-04.01 | L1 healing (demo-heal) | [ ] |
| TC-04.02 | L3 MockLLMHealer | [ ] |
| TC-04.03 | Auto-learn | [ ] |
| TC-05.01 | FAM-01 healing | [ ] |
| TC-05.02 | FAM-02 healing | [ ] |
| TC-05.03 | FAM-04 healing | [ ] |
| TC-05.04 | FAM-05 healing | [ ] |
| TC-05.05 | FAM-06 healing | [ ] |
| TC-06.01 | Classification (11/11) | [ ] |
| TC-06.02 | Classification manual | [ ] |
| TC-07.01 | Evidence collection | [ ] |
| TC-08.01 | Data-driven cycle | [ ] |
| TC-08.02 | Múltiplos cenários | [ ] |
| TC-09.01 | Gravação inexistente | [ ] |
| TC-09.02 | Script inexistente | [ ] |
| TC-09.03 | Recording sem fills | [ ] |
| TC-09.04 | Timeout | [ ] |
| TC-10.01 | LLM real | [ ] |

**Total:** 27 casos de teste
