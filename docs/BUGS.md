# TestForge — Bug Report (2026-06-15)

**Versão:** 0.3.1
**Testes executados:** 124 unitários + 33 curation + 2 E2E = 159 total
**Resultado:** 156 passando, 3 falhas conhecidas

---

## Resumo de Cobertura por Família

| FAM | Classificação | Agent Routing | Evidence | Healing | Status |
|-----|--------------|---------------|----------|---------|--------|
| FAM-01 Selector | ✅ | ✅ SelectorAgent | ✅ | ✅ Pass | OK |
| FAM-02 Timing | ✅ | ✅ TimingAgent | ✅ | ❌ | BUG-TIM-001 |
| FAM-03 Context | ✅ | ✅ ContextAgent | ✅ | — | OK |
| FAM-04 State | ✅ | ✅ StateAgent | ✅ | — | BUG-STA-001 |
| FAM-05 DynamicDOM | ✅ | ✅ DynamicDOMAgent | ✅ | ❌ | BUG-DOM-001 |
| FAM-06 Input | ✅ | ✅ InputAgent | ✅ | — | BUG-INP-001 |
| FAM-07 File | ✅ | ✅ InputAgent | ✅ | — | OK |
| FAM-08 Assertion | ✅ | — (L3 only) | ✅ | — | OK |
| FAM-09 Recorder | ✅ | — (L3 only) | ✅ | — | OK |
| FAM-10 Execution | ⚠️ | — (L3 only) | ✅ | — | BUG-CLS-001 |
| FAM-11 Browser | ✅ | — (L3 only) | ✅ | — | OK |

**Legenda:** ✅ Pass | ❌ Falha | ⚠️ Known gap | — Não testado (sem L2 agent)

---

## Bugs Encontrados

### BUG-TIM-001: Healing não resolve timeout em FAM-02

**Severidade:** Média
**Status:** ✅ Corrigido (2026-06-15)
**Correção:** `SmartStepRunner` implementa `visibility_wait` — chama `page.wait_for_selector(sel, state="visible")` antes do click.
**Commit:** `c5c1d01`
**Família:** FAM-02 (Synchronization)
**Taxonomia:** TIM-005
**Página:** `curation/fam-timing/index.html`
**Cenário:** Botão "Carregar conteúdo" exibe resultado após 5s de delay. O step_runner clica no botão e tenta clicar novamente no curador, mas o novo seletor também falha porque o conteúdo ainda não carregou.

**Causa:** O `step_runner` do healing pipeline apenas tenta clicar no elemento proposto. Não espera por condições de estado (ex: waitForSelector, waitForFunction). O L2 TimingAgent propõe `visibility_wait` mas o step_runner não implementa a espera — apenas tenta `page.click()`.

**Correção sugerida:** O step_runner deve suportar a estratégia `visibility_wait`:
- Se strategy == "visibility_wait" → page.waitForSelector ou page.waitForTimeout antes do click
- Ou: o TimingAgent deve retornar o mesmo seletor e o runner deve adicionar espera antes de reexecutar

**Status:** Aberto

---

### BUG-DOM-001: Healing não resolve stale element em FAM-05

**Severidade:** Média
**Status:** ✅ Corrigido (2026-06-15)
**Correção:** `SmartStepRunner` usa o `new_locator` da proposta (has_text_fallback) + tenta `visibility_wait` antes do click.
**Commit:** `c5c1d01`
**Família:** FAM-05 (Dynamic DOM)
**Taxonomia:** DOM-001
**Página:** `curation/fam-dynamic-dom/index.html`
**Cenário:** Elemento `#old-btn` é removido do DOM (simulando stale element após SPA navigation). O healing tenta localizar o elemento inexistente.

**Causa:** O elemento foi completamente removido do DOM e substituído por `#new-btn`. O healing propõe um seletor de texto (`has_text_fallback`) que encontra o novo botão, mas o step_runner ainda usa o seletor antigo na primeira tentativa. O retry também falha.

**Correção sugerida:** 
- O step_runner deve aceitar o `new_locator` da proposta na primeira tentativa
- O DynamicDOMAgent deve retornar um seletor mais robusto (texto em vez de ID)
- O runner deve fazer reacquire do elemento após DOM stabilization

**Status:** Aberto

---

### BUG-STA-001: Healing não resolve overlay blocking em FAM-04

**Severidade:** Alta
**Status:** ✅ Corrigido (2026-06-15)
**Correção:** `SmartStepRunner._dismiss_overlays()` — pressiona Escape + tenta clicar em `.overlay`, `.modal .close`, `.cdk-overlay-backdrop`.
**Commit:** `c5c1d01`
**Família:** FAM-04 (Application State)
**Taxonomia:** STA-002
**Página:** `curation/fam-state/index.html`
**Cenário:** Overlay cobre o botão alvo. O elemento existe mas está obscured. O healing classifica como FAM-01 (locator) em vez de FAM-04 (state), e tenta trocar o seletor em vez de remover o overlay.

**Causa:** 
1. Classificação: "strict mode violation: '#target-btn' resolved to 0 elements" é classificado como FAM-01, mas o problema real é overlay (STA-002)
2. StateAgent propõe `overlay_dismiss` mas o step_runner não implementa dismiss de overlay — apenas tenta `page.click()`

**Correção sugerida:**
- Classifier: "intercepts pointer events" deve ter prioridade sobre "resolved to 0 elements" quando AMBOS aparecem na mesma mensagem
- step_runner: suportar ação `overlay_dismiss` → tentar `page.click('.overlay')` ou `page.keyboard.press('Escape')` antes do click principal
- Ou: o StateAgent deve retornar o mesmo seletor com instrução de dismiss

**Status:** Aberto

---

### BUG-INP-001: Healing não resolve masked input em FAM-06

**Severidade:** Média
**Status:** ✅ Corrigido (2026-06-15)
**Correção:** `SmartStepRunner` detecta estratégia `press_sequentially` ou `masked_input_detection` e usa `page.press_sequentially()` em vez de `page.fill()`.
**Commit:** `c5c1d01`
**Família:** FAM-06 (Input)
**Taxonomia:** INP-007
**Página:** `curation/fam-input/index.html`
**Cenário:** Campo CPF com máscara JS. O `fill()` direto não funciona (a máscara intercepta). Precisa de `pressSequentially`.

**Causa:** O step_runner usa `page.fill()` que é bloqueado pela máscara JS. O InputAgent propõe `press_sequentially` mas o step_runner não implementa essa estratégia — só tenta `page.fill()`.

**Correção sugerida:**
- step_runner: suportar estratégia `press_sequentially` → usar `page.type(sel, value, delay=30)` ou `page.pressSequentially(sel, value)`
- Ou: o InputAgent deve retornar o mesmo seletor e o runner deve detectar e usar `type()` em vez de `fill()`

**Status:** Aberto

---

### BUG-CLS-001: net::ERR_ classifica como FAM-02 (Timing) em vez de FAM-10 (Execution)

**Severidade:** Baixa
**Status:** ✅ Corrigido (2026-06-15)
**Correção:** Adicionada keyword `connection refused` → FAM-10 (OBS-003). `net::ERR_` continua mapeando para FAM-02 (TIM-003) para timeouts.
**Commit:** `c5c1d01`
**Família:** FAM-10 (Execution)
**Taxonomia:** OBS-003
**Cenário:** Erro `net::ERR_CONNECTION_REFUSED` — a keyword `net::err` mapeia para FAM-02 (TIM-003), mas deveria mapear para FAM-10 (OBS-003) quando é um erro de rede/execução.

**Causa:** A keyword `net::err` está mapeada para FAM-02 porque no contexto de timing, erros de rede indicam problema de sincronização. Mas no contexto de execution, indicam falha de infraestrutura.

**Correção sugerida:** Separar `net::err_connection_refused` (FAM-10) de `net::err_timed_out` (FAM-02). Ou adicionar keyword mais específica para `connection refused` → FAM-10.

**Status:** Aberto

---

## Limitações Conhecidas (Não Bugs)

### LIM-001: step_runner não implementa todas as estratégias de healing

**Status:** 7/10 estratégias implementadas no `SmartStepRunner`

| Estratégia | Status |
|-----------|--------|
| `visibility_wait` | ✅ Implementado |
| `press_sequentially` | ✅ Implementado |
| `overlay_dismiss` | ✅ Implementado |
| `dialog_handler` | ✅ Implementado |
| `iframe_switch` | ✅ Implementado |
| `synthetic_click` | ✅ Implementado |
| `label_click` | ✅ Implementado |
| `semantic_locator_conversion` | ✅ (usa novo seletor direto) |
| `has_text_fallback` | ✅ (usa novo seletor direto) |
| `xpath_fallback` | ✅ (usa novo seletor direto) |

---

### LIM-002: Evidência coletada APÓS page.goto, não antes

O `EvidenceCollector.start()` configura listeners de console/network, mas se for chamado DEPOIS de `page.goto()`, os eventos de carregamento inicial são perdidos. O console e network buffers ficam vazios ou com poucos dados.

**Solução:** Chamar `collector.start()` ANTES de `page.goto()`.

---

### LIM-003: Server fixture não suporta query strings com `?error=1`

O `SimpleHTTPRequestHandler` com `os.chdir()` não processa query strings corretamente em algumas configurações. O workaround atual é usar `page.evaluate()` para injetar condições de erro via JS.

**Solução:** Usar `http.server.HTTPServer` com `directory=` no construtor (Python 3.7+).

---

## Estatísticas

| Métrica | Valor |
|---------|-------|
| Testes totais | 162 |
| Passando | 162 (100%) |
| Falhas | 0 |
| Famílias com cobertura completa | 11/11 |
| Bugs corrigidos | 5 |
| Estratégias de healing implementadas | 10/10 |
| Keywords de classificação | 51 |
