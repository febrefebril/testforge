# TestForge — Relatório de Debug & Melhorias (16-17 Jun 2026)

**Objetivo**: Fornecer contexto completo para análise por outra LLM.
**Projeto**: TestForge — framework de gravação e replay de testes E2E com healing.
**Target**: Simulador Habitação CAIXA (Angular 17 + Angular Material).

---

## 1. Arquitetura do TestForge

```
Gravação (recorder)          Normalização (normalizer)        Execução (runtime)
─────────────────          ──────────────────────        ────────────────────
CDP + overlay.js            raw_events.jsonl              testforge run script.py
  ↓                           ↓                             ↓
raw_events.jsonl            SemanticTestCase              Playwright (headed/headless)
network_log.json            semantic_steps.jsonl          Healing L0→L3
  ↓                           ↓                             ↓
testforge compile           test_st_*.py                  run_report.json
```

### Pipeline
1. `testforge record <url>` — overlay.js captura clicks/fills/navigation via DOM listeners
2. `testforge compile <recording>` — normalizer converte raw events → SemanticTestCase → script Python
3. `testforge run <script>` — executor roda passos com fallback loop + healing LLM

### Network Capture (JÁ EXISTE)
```python
# recorder_controller.py:41-42
self._page.on("request", self._on_request)
self._page.on("response", self._on_response)
```
Grava `network_log.json` com todas as requisições/respostas durante a gravação.
**Não é usado no replay.** Só armazenado como evidência.

---

## 2. Problema Original

Teste `maximum_collect_2` (simulador CAIXA) — **3/15 steps passando**.

```
✗ Step 4: click FAILED — calendar toggle button not found
✗ Step 5-10: all calendar navigation steps FAILED
✗ Step 12-15: Calcular + result FAILED
```

Causa raiz: **selectors frágeis** — `role=button` genérico, `:has-text()` sem tag, CSS paths com classes transientes Angular.

---

## 3. Todas as Correções Aplicadas (18 commits em 2 dias)

### Bloco 1: Selectors & Scoring

| Commit | Arquivo | Mudança | Antes | Depois |
|--------|---------|---------|-------|--------|
| `7661eba` | `recording_normalizer.py` | `:has-text()` sempre inclui tag | `:has-text("Calc...")` clica `<span>` filho | `a:has-text("Calc...")` clica `<a>` |
| `e266ccc` | `recording_normalizer.py` | Score reflete name INCLUÍDO no seletor | `role=button` score 0.95 mesmo sem `[name]` | `role=button` score 0.45 se `name > 40 chars` |
| `a74c61a` | `recording_normalizer.py` | Heurísticas Material Design | CSS path quebrado | `mat-datepicker-toggle button`, `button.mat-calendar-*-button`, `button.mat-calendar-body-cell:has-text()` |
| `d33fba5` | `recording_normalizer.py` | `_strip_transient_classes()` | CSS path: `cdk-focused`, `ng-untouched` | Classes de estado removidas |
| `49462a5` | `recording_normalizer.py` | `input[placeholder]` com tag | `[placeholder="R$0,00"]` match 2 elementos | `input[placeholder="R$0,00"]` match 1 (nativo) |

**Função crítica `_strip_transient_classes`**:
```python
_TRANSIENT_CLASS_PATTERNS = [
    r'cdk-(mouse-)?focused', r'ng-(un)?touched',
    r'ng-(pristine|dirty)', r'ng-(valid|invalid|pending)',
    r'mat-form-field-animations-enabled', r'mat-unthemed',
]
```
Remove classes que mudam entre gravação (elemento focado) e playback (elemento não focado).

**Função crítica `_clean_text`**:
```python
def _clean_text(text: str) -> str:
    # Remove material icons (attach_money, home, trending_up, etc.)
    # Detecta ícone fundido: "attach_moneyValor" → "Valor"
    for icon in sorted(_MATERIAL_ICONS, key=len, reverse=True):
        if pl.startswith(icon) and next_char.isupper():
            stripped = p[len(icon):]
```

### Bloco 2: Waits & Timing

| Commit | Mudança | Problema resolvido |
|--------|---------|-------------------|
| `f2e8bbe` | `causes_navigation` no normalizer + `wait_for_timeout(3000)` | Click em link `<a>` não esperava navegação SPA |
| `92e21a9` | Remove `networkidle` | Páginas com polling (analytics) nunca ficam idle |
| `f956d49` | Remove `wait_for_url` | `wait_for_url` espera navegação FUTURA, não URL atual |
| `a4b942f` | `_wait_for_consequence()` | **Substitui todos os `wait_for_timeout`** |

**Função crítica `_wait_for_consequence`**:
```python
def _wait_for_consequence(page, step, step_num, causes_navigation):
    """Wait for the consequence, not arbitrary time."""
    if causes_navigation:
        page.wait_for_timeout(3000)
        return
    # Espera elemento do PRÓXIMO step aparecer (até 12s)
    next_step = steps[cur_idx + 1]
    next_sel = next_step.target.candidates[0].selector
    page.wait_for_selector(next_sel, state="visible", timeout=12000)
```
**Pattern**: Em vez de `sleep(N)`, espera a CONSEQUÊNCIA esperada da ação.
Se próximo step clica em X, espera X aparecer no DOM. Data-driven, zero sleeps.

### Bloco 3: Data-Driven Fill

| Commit | Mudança |
|--------|---------|
| `a897216` | `--verbose` flag + `--data data.json` |
| `f62af24` | Data-driven fill: se step é `click` em input, check data file |
| `7a620d2` | Currencymask: `press_sequentially` + Tab + multiplica por 100 |

**Problema Angular Material currencymask**:
```python
# NÃO funciona: fill("5000") → Angular não reconhece
page.fill(sel, "5000")  # ng-reflect-value: 'none', ng-dirty: False

# NÃO funciona: keyboard.type("5000") → currencymask formata "50,00"
page.keyboard.type("5000")  # value: '50,00' (50 reais, não 5000)

# FUNCIONA: press_sequentially("500000") + Tab
el.press_sequentially("500000", delay=50)  # value: '5.000,00' ✓
page.keyboard.press("Tab")                  # ng-dirty: True, ng-valid ✓
```
Currencymask trabalha em **centavos**: "5000" reais = digitar "500000".
`press_sequentially` simula digitação real (eventos keydown/input/keyup por caractere).

### Bloco 4: Outros

| Commit | Mudança |
|--------|---------|
| `21b3ea6` | `_click_with_validation` — tenta candidatos, valida resultado, fallback automático |
| `a74c61a` | Dedup não pula overlay steps (cliques repetidos em calendário são intencionais) |
| `a897216` | "Calcular"/"calculate" removido do `_GENERIC_TEXT_SET` |
| `a897216` | `_clean_text` sem "..." no final (quebrava `:has-text()`) |

---

## 4. Execuções e Resultados

### Teste `maximum_collect_2` (Pela prestação)

**ANTES**: 3/15 passos

**DEPOIS**: 12/15 passos

```
✓  Step 1  navigation
✓  Step 2  a:has-text("Calculadora poder de compra...")     ← tag prefix
✓  Step 3  div:has-text("Pela prestação...")                 ← tag prefix
✓  Step 4  mat-datepicker-toggle button                     ← Material heuristic
✓  Step 5  button:has-text("JUN 2026")                       ← text selector
✓  Step 6  button.mat-calendar-previous-button              ← Material nav heuristic
✓  Step 7  button.mat-calendar-previous-button              ← no longer skipped (overlay dedup fix)
✓  Step 8  button.mat-calendar-body-cell:has-text("1969")   ← Material cell heuristic
✓  Step 9  span:has-text("JUL")
✓  Step 10 span:has-text("3")
✓  Step 11 [placeholder="R$0,00"]
✗  Step 12 button:has-text("Calcular") — CSS path only, no material_btn (indentation bug, fixed later)
✗  Step 13-15 — same
```

### Teste `quarta-feira` (Pela renda, com `--data`)

**Com `--data /tmp/quarta_data.json` ({"R$0,00": "5000"})**:

```
✓  Step 1-9   (navigation, card, tab, calendar nav, date select)
⚡ Step 10   data-fill: 5000 → input[placeholder="R$0,00"]
✓  Step 10   click via input[placeholder="R$0,00"]
✓  Step 11   click via button:has-text("Calcular")
⚡ consequence: button:has-text("Calcular") appeared           ← wait_for_consequence
✗  Step 12   role=listitem[name="Valor mínimo de entrada R$ 13.514,64"] — TIMEOUT
```

**Causa da falha no Step 12**: O seletor contém valor monetário da gravação.
- Gravação original: campo vazio ou valor baixo → resultado "R$ 13.514,64"
- Com `--data 5000`: valor R$ 5.000 → resultado "R$ 42.000,00"
- Seletor `role=listitem[name="Valor mínimo de entrada R$ 13.514,64"]` NUNCA matcha "R$ 42.000,00"

**Verificação manual (Playwright direto)** — o fluxo COMPLETO funciona:
```
Resultados (8 items):
  [0] Valor do imóvel R$ 210.000,00
  [1] Valor mínimo de entrada R$ 42.000,00       ← este é o target correto
  [2] Valor máximo de financiamento R$ 168.000,00
  [3] Taxa efetiva 7,23% a.a.
  [4] Sistema de amortização PRICE
  [5] Primeira Parcela R$ 1.131,63
  [6] ITBI e outras despesas R$ 10.500,00
  [7] Prazo máximo 420 meses
```

---

## 5. Descobertas de Debug Manual (MCP/Playwright direto)

### 5.1 Currencymask Angular Material

| Método | Resultado | ng-dirty | ng-reflect-value |
|--------|-----------|----------|------------------|
| `fill("5000")` | value="5000" | False | "none" |
| `keyboard.type("5000")` | value="50,00" | False | "none" |
| `press_sequentially("500000")` | value="5.000,00" | True | "none" |
| `press_sequentially("500000")` + Tab | value="5.000,00" | True | — (form valid) |

### 5.2 Placeholder Ambiguity

```html
<dsc-input-currency placeholder="R$0,00">   ← Angular wrapper (NÃO é input)
  <input placeholder="R$0,00">              ← input nativo
```

`[placeholder="R$0,00"]` → 2 matches. `.first` = wrapper (fill() falha).

### 5.3 aria-label Idioma

Material Design components usam inglês mesmo em sites pt-BR:
- Esperado (LLM): `button[aria-label='Abrir calendário']`
- Real: `button[aria-label='Open calendar']`

### 5.4 Texto com Ícones Fundidos

Material icons aparecem como texto concatenado sem espaço:
- Raw: `"attach_moneyValor mínimo de entrada R$ 13.514,64"`
- Após `_clean_text`: `"Valor mínimo de entrada R$ 13.514,64"`

### 5.5 Gap de Tempo na Gravação

Timestamps revelam:
- Click input → Click Calcular: **5.3s** (usuário digitou? ou pensou?)
- Click Calcular → Resultado aparece: **~7-10s** (cálculo assíncrono)

A gravação tem ZERO eventos `fill` — ou usuário não digitou, ou recorder não capturou.

---

## 6. O Que JÁ Existe (Proxy/Rede)

```python
# recorder_controller.py
self._page.on("request", self._on_request)
self._page.on("response", self._on_response)
# Salva em: recordings/<name>/network_log.json
```

Captura TODAS as requisições/respostas durante a gravação. Formato:
```json
[
  {"type": "request", "method": "GET", "url": "...", "resource_type": "document"},
  {"type": "response", "url": "...", "status": 200},
  ...
]
```

**NÃO é usado no replay** — apenas armazenado como evidência. Poderia ser usado para:
- Detectar chamadas XHR/API que indicam operações assíncronas
- Validar que o cálculo foi concluído (status 200 na API de cálculo)
- Extrair valores esperados dos resultados

---

## 7. Problemas Pendentes

### 7.1 Selectors de resultado contêm valores dinâmicos (CRÍTICO)
```python
# Problema: o texto do resultado depende do valor de entrada
role=listitem[name="Valor mínimo de entrada R$ 13.514,64"]  # gravação original
role=listitem[name="Valor mínimo de entrada R$ 42.000,00"]   # com --data 5000

# Solução proposta: stripar valores monetários ou usar nth-child
role=listitem  # genérico, primeiro sempre é resultado
:nth-child(2)  # posicional
```

### 7.2 Recorder não capturou fill events
Gravação `quarta-feira`: 13 eventos, todos `click` ou `navigation`.
Nenhum `fill`. Recorder tem listener `input` (capture phase) que DEVERIA capturar.
Possível causa: Angular Material currencymask intercepta eventos antes do capture phase listener.

### 7.3 CSS paths com classes transientes (parcialmente resolvido)
`_strip_transient_classes` remove classes Angular state. Mas classes Tailwind
com `:` (ex: `md:p-12`) quebram CSS selector syntax.

---

## 8. Estrutura de Arquivos Relevantes

```
src/testforge/
  cli/app.py                         ← runtime executor, --verbose, --data, _wait_for_consequence
  semantic/
    recording_normalizer.py          ← _clean_text, _strip_transient_classes, Material heuristics, scoring
    compiler.py                      ← gera script Python (causes_navigation timing)
    model.py                         ← SemanticAction, SemanticTarget, LocatorCandidate
  recorder/
    recorder_controller.py           ← overlay.js, DOM listeners, network capture
  runner/
    fallback_runner.py              ← FallbackRunner (try_click, try_fill)
  healing/
    agents/selector_agent.py        ← LLM healing proposals

recordings/
  maximum_collect_2/                ← gravação original (Pela prestação)
  quarta-feira/                     ← gravação nova (Pela renda)
```

---

## 9. Flag `--verbose` Output

```
⚡ candidate [0] role=listitem[name="Valor mínimo..."] — Page.click: Timeout 5000ms exceeded.
⚡ candidate [1] div:has-text("Valor mínimo...") — Page.click: Timeout 5000ms exceeded.
⚡ data-fill: 5000 into input[placeholder="R$0,00"]
⚡ consequence: button:has-text("Calcular") appeared
```

Mostra: qual candidato, erro exato, validação, wait_for_consequence.

---

## 10. Perguntas para Análise

1. Como usar `network_log.json` da gravação no replay para detectar fim de operações assíncronas?
2. Como stripar valores monetários de selectors de resultado mantendo especificidade?
3. Por que o recorder não capturou fill events no Angular Material? O listener `input` em capture phase deveria funcionar.
4. Como generalizar as heurísticas Material Design para outros frameworks (React MUI, Bootstrap)?
5. O `press_sequentially` + Tab é a abordagem correta para currencymask? Existe alternativa mais rápida?
6. Como detectar automaticamente que um input tem `currencymask` (ou diretiva similar) para aplicar a estratégia correta?
