# Plano de Melhorias — Gravador de Intenção (Recorder)

**Data:** 2026-06-30  
**Versão:** 1.0  
**Autor:** Análise consolidada de 27 fontes, 20 testes, docs ancestrais, pesquisa de mercado  
**Status:** Rascunho

---

## Sumário

1. [Diagnóstico Resumido](#1-diagnóstico-resumido)
2. [Fase 1 — ESTABILIZAR (Prioridade Máxima)](#2-fase-1--estabilizar-prioridade-máxima)
3. [Fase 2 — CAPTURA MULTI-ESTRATÉGIA](#3-fase-2--captura-multi-estratégia)
4. [Fase 3 — EVOLUIR](#4-fase-3--evoluir)
5. [Estratégias de Captura por Framework](#5-estratégias-de-captura-por-framework)
6. [Arquitetura Alvo](#6-arquitetura-alvo)
7. [Checklist de Prontidão](#7-checklist-de-prontidão)

---

## 1. Diagnóstico Resumido

O gravador tem **3 camadas**, cada uma com problema diferente:

| Camada | O Que Faz | Problema Central |
|--------|-----------|-----------------|
| **1. Overlay JS** (`overlay_inject.js`) | Captura eventos do usuário no browser | Perde fills em React (controlled inputs), Angular currencymask, shadow DOM |
| **2. Controller Python** (`recorder_controller.py`) | Drena filas, persiste, gerencia sessão | P0 bugs (event_id reset, DOM 0 bytes, contagem divergente) |
| **3. Pós-gravação** (normalizer + reconstructor) | Reconstrói intenção a partir dos artefatos | Causa raiz: se camada 1 falhou, nada recupera |

**Prioridade: estabilizar camadas 1 e 2 AGORA. Camada 3 pode ser melhorada depois.**

### Bugs Abertos Prioritários

| ID | Problema | Impacto | Módulo |
|----|----------|---------|--------|
| BUG-001 | `<select>` gera seletor de `<input>` em vez de `select_option` | 🟢 Bloqueante | overlay_inject.js |
| BUG-002 | DOM snapshots com 0 bytes | 🟢 Bloqueante | recorder_controller.py |
| BUG-003 | Contagem divergente (terminal vs compile vs runner) | 🟢 Bloqueante | recorder_controller.py |
| BUG-004 | `event_id` reinicia após navegação — múltiplos `evt_0001` | 🟢 Bloqueante | overlay_inject.js |
| BUG-005 | `record --name X` anexa silenciosamente em vez de criar novo | 🟢 Bloqueante | recording_session.py |
| BUG-007 | Tela pisca SIMAX — navegações múltiplas | 🟢 Bloqueante | recorder_controller.py |
| BUG-008 | Digitação vira dezenas de fills (sem debounce) | 🟡 Crítico | overlay_inject.js |

### Market Research — Referências

| Ferramenta | Diferencial | O Que Podemos Usar |
|-----------|-------------|-------------------|
| **Playwright Codegen** | `getByRole`, `getByLabel`, `getByTestId` priority | Já usamos overlay JS, podemos enriquecer com AX tree |
| **Cypress Studio AI** | DOM diff entre steps → sugere assertions automaticamente | Implementar diff hash no flush |
| **BugBug** | Adaptive Locators — AI escolhe estratégia mais estável | `match_count_by_strategy` em cada evento |
| **PiperTest** | AX-enriched: axPath, matchCount, boundingBox por elemento | Adicionar ao `_extractTarget()` |
| **Kiwigen** | Multi-strategy por elemento com confidence levels | Score por estratégia no overlay |
| **auto-fill (GitHub)** | `_valueTracker.setValue()` + native prototype setter para React | Implementar no setter hook |
| **refined-github (React)** | Native prototype setter pattern para controlled inputs | Mesmo padrão |
| **Flows (BetterQA)** | Self-healing selectors, MCP integration | Fase 3 |

---

## 2. Fase 1 — ESTABILIZAR (Prioridade Máxima — Hoje)

### 2.1 Fixar P0 Bugs do Controller

#### BUG-004: `event_id` reinicia após navegação

**Arquivo:** `overlay_inject.js:166`

**Problema:** O `window.__tfEventCounter` é reiniciado quando a página é recarregada (navegação cross-page). SPA routes dentro do mesmo `window` mantêm o contador.

**Solução:** O JS envia `event_id: null` e o Python numera sequencialmente.

```js
// overlay_inject.js — _pushEvent()
function _pushEvent(type, el) {
    // Remove event_id assignment — Python gerencia
    window.__tfEventQueue.push({
        // event_id: NÃO GERAR AQUI
        type: type,
        timestamp: new Date().toISOString(),
        url: window.location.href,
        page_title: document.title,
        target: _extractTarget(el || document.activeElement),
        value: (el && el.value) ? el.value.substring(0,200) : null
    });
}
```

```python
# recorder_controller.py — _persist_raw_event()
def _persist_raw_event(self, data: dict):
    self._event_counter += 1
    event = RawRecordedEvent(
        event_id=f"evt_{self._event_counter:05d}",  # Python numera
        ...
    )
```

**Efeito colateral:** Navegação SPA (pushState) mantém o JS rodando → event_counter JS continua.
Navegação cross-page (nova URL) → JS reinicia, mas Python continua.

#### BUG-002: DOM snapshots com 0 bytes

**Arquivo:** `recorder_controller.py:430-434`

**Problema:** `page.content()` pode retornar string vazia se a página está em transição.
`RawRecordingStore.save_dom()` já valida `len(html.strip()) < 20` (linha 32-34).
Mas o controller ignora o retorno — salva o path mesmo se for vazio.

**Solução:** Validar antes de salvar no controller.

```python
def _capture_snapshots(self, event: RawRecordedEvent):
    try:
        dom = self._page.content()
        if dom and len(dom.strip()) >= 20:
            event.dom_snapshot_path = self._store.save_dom(eid, dom)
    except Exception:
        pass
```

#### BUG-003: Contagem divergente

**Arquivo:** `recorder_controller.py`

**Problema:** Terminal mostra "1 passos gravados" (monitora `steps.jsonl`), compile mostra "15 steps", runner mostra "15 steps". Mistura eventos brutos, steps semânticos, steps executáveis.

**Solução:** 3 contadores separados no log:

```python
# No loop de gravação:
raw_count = self._event_counter      # Eventos brutos (click, fill, navigation...)
step_count = self._step_counter       # Steps manuais (asserts, checkpoints)
command_count = len(self._command_queue)  # Comandos (pause, stop)

print(f"[TestForge] Eventos brutos: {raw_count} | Steps: {step_count}")
```

#### BUG-001: `<select>` gera seletor de `<input>`

**Arquivo:** `overlay_inject.js:597-598`

**Problema:** Quando `el.tagName === 'SELECT'`, o overlay faz `return` sem gravar o click (linha 597). O evento de `change` captura o valor, mas o tipo inferido está errado.

**Solução:** Gravar evento `select_option` com o valor selecionado.

```js
// overlay_inject.js — click handler
if (el && el.tagName === 'SELECT') {
    _pushEvent('select_option', el);
    return;
}
```

#### BUG-007: Tela pisca SIMAX

**Arquivo:** `recorder_controller.py:544-571`

**Problema:** `_on_framenavigated` gera `navigation` event para toda navegação, mesmo quando é reload da mesma URL (SIMAX faz pós-back).

**Solução:** Detectar se URL realmente mudou antes de emitir navigation.

```python
_last_nav_url = None

def _on_framenavigated(self, frame):
    if frame != self._page.main_frame:
        return
    try:
        current_url = self._page.url
    except Exception:
        current_url = frame.url
    
    # Skip se mesma URL (reload/navigation noise)
    if current_url == self._last_nav_url:
        return
    self._last_nav_url = current_url
    
    # ... resto do handler
    logger.info("Navigation detected: %s — %s", current_url, page_title[:60])
```

### 2.2 Fortalecer Captura de Input (Overlay JS)

**Problema central:** O `addEventListener('input')` e o setter hook atual (`_hookValue`) perdem valores em:

1. **React controlled inputs:** React sobrescreve o setter `HTMLInputElement.prototype.value` via `_valueTracker`. Quando o setter hook do TestForge intercepta, ele captura o valor ANTES do React processar.

2. **Angular currencymask:** Usa o setter nativo direto (`el.value = ...`) sem disparar `input` event. O setter hook captura, mas o valor é formatado em centavos.

3. **Frameworks que sobrescrevem o setter:** Qualquer framework que faça `Object.defineProperty(input, 'value', ...)` depois do hook do TestForge.

#### 2.2.A — MutationObserver para atributo `value`

**Arquivo:** `overlay_inject.js`

**Problema:** Angular, Vue, e Svelte atualizam o valor do input através do property binding, que modifica o atributo `value` no DOM. O MutationObserver atual só observa `aria-valuenow`, `aria-valuetext`, e `contenteditable`.

**Solução:** Expandir o MutationObserver para capturar mudanças no atributo `value`.

```js
// overlay_inject.js — dentro do MutationObserver existente (linha 473)
var observer = new MutationObserver(function(mutations) {
    mutations.forEach(function(mut) {
        // ... existing: contentEditable + ARIA handling ...
        
        // NOVO: capturar mudanças no atributo value
        if (mut.type === 'attributes' && mut.attributeName === 'value') {
            var el = mut.target;
            if (!el || !el.tagName) return;
            var tag = el.tagName.toLowerCase();
            if (tag !== 'input' && tag !== 'textarea') return;
            if (window.__tfAssertWaiting) return;
            _scheduleFillFromMutation(el);
        }
    });
});

// Expandir attributeFilter
observer.observe(document.documentElement, {
    childList: true,
    subtree: true,
    characterData: true,
    attributes: true,
    attributeFilter: [
        'aria-valuenow', 'aria-valuetext',
        'contenteditable',
        'value',  // ← NOVO
    ]
});
```

#### 2.2.B — Setter hook com `_valueTracker` para React

**Arquivo:** `overlay_inject.js:352-372`

**Problema:** React controlled inputs usam `_valueTracker` interno. Quando o valor é setado programaticamente, React compara o valor armazenado no tracker com o novo valor. Se forem iguais, React não dispara `onChange`.

O setter hook atual intercepta a chamada ao setter, mas se o React já hookeou o prototype ANTES do TestForge, a ordem é:

```
el.value = "foo"
  → TestForge hook (captura "foo")
  → React hook (atualiza _valueTracker, dispara onChange)
```

Isso funciona se TestForge hookear por último. Mas se React hookear depois (ex: mount atrasado), TestForge não captura nada.

**Referência:** [refined-github `set-react-input-value.ts`](https://github.com/refined-github/refined-github) — padrão canônico para React.

**Solução segura:** Hookear o `HTMLInputElement.prototype.value` e `HTMLTextAreaElement.prototype.value` usando `Object.getOwnPropertyDescriptor` para obter o setter ORIGINAL (que pode já ter sido hookeado por React).

```js
function _hookValueReactSafe(proto) {
    // Obtém o descriptor ATUAL (pode ser React hook ou nativo)
    var orig = Object.getOwnPropertyDescriptor(proto, 'value');
    if (!orig || !orig.set) return;
    
    Object.defineProperty(proto, 'value', {
        get: orig.get,
        set: function(v) {
            // Chama o setter atual (React ou nativo)
            orig.set.call(this, v);
            // Agenda fill — o valor já está no DOM
            _scheduleFillFromMutation(this);
        },
        configurable: true  // Permite que outros hookeiem depois
    });
}

// hookear depois que React tiver chance de hookear
document.addEventListener('DOMContentLoaded', function() {
    _hookValueReactSafe(HTMLInputElement.prototype);
    _hookValueReactSafe(HTMLTextAreaElement.prototype);
});
```

**Estratégia adicional — `_valueTracker` reset (para setter bypass no runner, não no recorder):**

```js
// Para uso no RUNNER (playback), quando precisamos SETAR valor em React:
function _setReactValue(el, val) {
    // 1. Reseta o tracker do React para força diff detection
    if (el._valueTracker) {
        el._valueTracker.setValue('');
    }
    // 2. Usa o setter nativo do prototype (não o do React)
    var nativeSetter = Object.getOwnPropertyDescriptor(
        el.tagName === 'TEXTAREA'
            ? HTMLTextAreaElement.prototype
            : HTMLInputElement.prototype,
        'value'
    ).set;
    nativeSetter.call(el, val);
    // 3. Dispara eventos na ordem correta
    el.dispatchEvent(new Event('input', { bubbles: true }));
    el.dispatchEvent(new Event('change', { bubbles: true }));
}
```

#### 2.2.C — CDP `Input.dispatchKeyEvent` como fallback

**Arquivo:** `recorder_controller.py`

**Problema:** Framework detectors rodam no Python, mas a captura de input é no JS. Se o JS falha (ex: React setter bypass), não temos fallback.

**Solução:** Quando CDP está ativo, escutar `Input.dispatchKeyEvent` via CDP session para capturar TODAS as teclas digitadas, independente do framework.

```python
# Em RecorderController.start() — quando CDP ativo
if self._use_cdp:
    self._cdp_session.on("Input.dispatchKeyEvent", self._on_keyboard_event)

def _on_keyboard_event(self, event: dict):
    """Captura teclas via CDP — framework-agnostic."""
    key = event.get("key", "")
    text = event.get("text", "")
    if text and len(text) == 1:
        # Tecla com caractere — acumular no buffer do campo focado
        self._keyboard_buffer += text
    elif key == "Tab" or key == "Enter":
        # Final de digitação — push fill event
        if self._keyboard_buffer:
            focused = self._page.evaluate("document.activeElement")
            self._push_cdp_fill(focused, self._keyboard_buffer)
            self._keyboard_buffer = ""
```

**Nota:** CDP `Input.dispatchKeyEvent` é o mesmo mecanismo que Playwright usa internamente. Escutar esses eventos permite capturar teclas que o overlay JS perdeu.

### 2.3 Framework Detection em Tempo de Gravação

**Arquivo:** `recorder_controller.py` + `framework_detector.py`

**Problema:** `FrameworkDetector` já existe (A1-A4) mas roda APENAS no modo `--diagnostic-mode`. A captura não se adapta ao framework.

**Solução:** Rodar framework detection após cada navegação e adaptar captura.

```python
class RecorderController:
    def start(self, ...):
        # ...
        self._framework = "unknown"
        self._detect_framework()  # Primeira detecção
    
    def _detect_framework(self):
        """Detecta framework e adapta estratégias de captura."""
        det = FrameworkDetector(self._page, self._cdp_session)
        result = det.detect()
        self._framework = result.get("primary", "unknown")
        
        if self._framework in ("react", "mui"):
            logger.info("React detected — activating _valueTracker compat")
            self._page.evaluate("window.__tfReactCompat = true")
        elif self._framework in ("angular", "angular-material"):
            logger.info("Angular detected — activating attribute observer")
            # MutationObserver já lida com value attribute
        elif self._framework == "primefaces":
            logger.info("PrimeFaces detected — activating jQuery compat")
        
        return self._framework
    
    def flush_events(self):
        # ...
        # Re-detect após navegação (framework pode mudar com SPA)
        if self._last_url != self._page.url:
            self._detect_framework()
```

### 2.4 Debounce Inteligente de Fill Events

**Arquivo:** `overlay_inject.js`

**Problema (BUG-008):** Cada tecla gera um fill event separado. Campo CPF gera:
`fill "4"`, `fill "40"`, `fill "407"`, ..., `fill "407.123.456-89"`.

**Solução:** Debounce com coalescing — agrupa digitação rápida em um único evento.

```js
// overlay_inject.js — adicionar ao state init
window.__tfFillCoalesceTimers = {};

// NOVA função de push com coalescing
function _coalescedPushEvent(el) {
    var key = _fillKey(el);
    var existing = window.__tfFillCoalesceTimers[key];
    if (existing) {
        clearTimeout(existing);
    }
    window.__tfFillCoalesceTimers[key] = setTimeout(function() {
        _pushEvent('fill', el);
        delete window.__tfFillCoalesceTimers[key];
    }, 400);  // 400ms sem digitar = valor final
}

// Substituir _pushEvent('fill', el) por _coalescedPushEvent(el) nos handlers:
// input handler (linha 626)
_coalescedPushEvent(el);

// change handler (linha 637)
_coalescedPushEvent(el);
```

**Configuração:** `__tfFillDebounceMs = 400` — pode ser ajustado por framework.
Para Angular/Material que tem delay de processamento maior: `600ms`.
Para React: `400ms` (já tem debounce do onChange).

---

## 3. Fase 2 — CAPTURA MULTI-ESTRATÉGIA

### 3.1 Enriquecer Target Info com Match Count

**Arquivo:** `overlay_inject.js:89-142`

**Problema:** O `_extractTarget()` captura identidade do elemento mas não sabe quantos elementos correspondem a cada estratégia de seletor. O compiler depois precisa tentar cada estratégia cegamente.

**Solução:** Para cada interação, calcular quantos matches cada estratégia teria na página atual.

```js
function _extractTarget(el) {
    // ... existing code ...
    
    // NOVO: match count por estratégia
    var matchCountByStrategy = {};
    var tag = (el.tagName || '').toLowerCase();
    
    // role + accessible_name
    var role = el.getAttribute('role') || null;
    var accName = el.getAttribute('aria-label') || el.getAttribute('title') || null;
    if (role && accName) {
        matchCountByStrategy.role_name = document
            .querySelectorAll('[role="' + CSS.escape(role) + '"]')
            .length;
    }
    
    // label
    var labelEl = el.id ? document.querySelector('label[for="' + CSS.escape(el.id) + '"]') : null;
    if (labelEl) {
        matchCountByStrategy.label = document
            .querySelectorAll('label[for="' + CSS.escape(el.id) + '"]')
            .length;
    }
    
    // test id
    var testId = el.getAttribute('data-testid') || el.getAttribute('data-test-id') || null;
    if (testId) {
        matchCountByStrategy.testid = document
            .querySelectorAll('[data-testid="' + CSS.escape(testId) + '"]')
            .length;
    }
    
    // placeholder
    var placeholder = el.getAttribute('placeholder') || null;
    if (placeholder) {
        matchCountByStrategy.placeholder = document
            .querySelectorAll('[placeholder="' + CSS.escape(placeholder) + '"]')
            .length;
    }
    
    // CSS path uniqueness
    if (css_path) {
        try {
            matchCountByStrategy.css = document.querySelectorAll(css_path).length;
        } catch(e) {
            matchCountByStrategy.css = -1;  // seletor inválido
        }
    }
    
    return {
        // ... existing fields ...
        match_count_by_strategy: matchCountByStrategy,
    };
}
```

### 3.2 Snapshot Diff Integrado ao Flush

**Arquivo:** `recorder_controller.py`

**Problema:** O `IntentReconstructor` faz snapshot diff pós-gravação (comparando snapshots consecutivos). Se pudermos calcular o diff durante a gravação, o reconstructor não precisa refazer.

**Solução:** No `flush_events()`, quando recebemos field snapshots, calcular diff entre o atual e o anterior.

```python
def flush_events(self):
    # ... existing code ...
    
    for batch in raw_fsnaps:
        self._save_field_snapshot(batch)
        self._diff_field_snapshot(batch)  # NOVO
    
    # ...

_last_field_snapshot = None

def _diff_field_snapshot(self, batch):
    """Calcula diff entre snapshots consecutivos e salva field diffs."""
    current = batch.get("snapshots", [])
    if self._last_field_snapshot is None:
        self._last_field_snapshot = current
        return
    
    diffs = []
    for snap in current:
        fp = snap.get("fingerprint", "")
        val = snap.get("value", "")
        # Procura snapshot anterior com mesmo fingerprint
        prev_val = None
        for prev in self._last_field_snapshot:
            if prev.get("fingerprint") == fp:
                prev_val = prev.get("value")
                break
        if prev_val is not None and prev_val != val:
            diffs.append({
                "timestamp": batch.get("timestamp"),
                "fingerprint": fp,
                "identifiers": snap.get("identifiers", {}),
                "old_value": prev_val,
                "new_value": val,
                "changed": True,
            })
    
    if diffs:
        path = os.path.join(self._store._session_dir, "field_diffs.jsonl")
        with open(path, "a", encoding="utf-8") as f:
            for d in diffs:
                f.write(json.dumps(d, default=str) + "\n")
        logger.debug("Field diffs: %d changes", len(diffs))
    
    self._last_field_snapshot = current
```

### 3.3 Value Capture via DOM Evaluation (Fallback Python)

**Arquivo:** `recorder_controller.py`

**Problema:** Se o overlay JS falha completamente (ex: página que bloqueia scripts injetados), nenhum fill é capturado.

**Solução:** No `flush_events()`, ler valores atuais do DOM via `page.evaluate()` como fallback.

```python
def _capture_all_field_values(self):
    """Fallback: lê todos os campos do DOM via page.evaluate."""
    try:
        field_values = self._page.evaluate("""() => {
            const results = {};
            document.querySelectorAll('input, textarea, select').forEach(function(el) {
                if (el.type === 'hidden' || el.type === 'password') return;
                var name = el.name || el.id || el.placeholder 
                    || el.getAttribute('aria-label') || '';
                if (name && el.value) {
                    results[name] = (el.value || '').substring(0, 200);
                }
            });
            return results;
        }""")
        if field_values:
            path = os.path.join(self._store._session_dir, "field_values.json")
            # Append em vez de sobrescrever (histórico de mudanças)
            existing = {}
            try:
                with open(path) as f:
                    existing = json.load(f)
            except (FileNotFoundError, json.JSONDecodeError):
                pass
            existing.update(field_values)
            with open(path, "w", encoding="utf-8") as f:
                json.dump(existing, f, indent=2, default=str)
    except Exception:
        pass
```

### 3.4 CDP AX Tree + Tracing como Padrão

**Arquivo:** `recorder_controller.py`

**Problema:** CDP está atrás de `--use-cdp-recorder` flag. Sem CDP, perdemos:
- AX tree (full accessibility tree via `getFullAXTree`)
- Match count via `queryAXTree`
- Playwright tracing (`trace.zip`)
- CDP network bundle analysis (framework detection A3)

**Solução:** CDP ativo por padrão. Remover feature flag.

```python
def start(self, ...):
    # Remover: self._use_cdp = bool(use_cdp)
    # Sempre ativar:
    self._tracing = TracingManager(self._page)
    self._tracing.start(session.session_dir, recording_id)
    self._cdp = CDPSnapshotter(self._page)
    self._cdp.attach()
    logger.info("CDP capture enabled: tracing + AX snapshots")
```

### 3.5 Iframe-aware Event Delegation

**Arquivo:** `overlay_inject.js`

**Problema:** Event listeners registrados no `window` do top frame não capturam eventos dentro de iframes de mesma origem.

**Solução:** Propagar listeners para iframes de mesma origem (cross-origin não é possível por política do browser).

```js
// overlay_inject.js — após registrar listeners no window
function _delegateToIframes() {
    var iframes = document.querySelectorAll('iframe');
    iframes.forEach(function(iframe) {
        try {
            var iDoc = iframe.contentDocument || iframe.contentWindow.document;
            if (!iDoc) return;
            
            // Re-registrar listeners críticos
            iDoc.addEventListener('click', handleIframeClick, true);
            iDoc.addEventListener('input', handleIframeInput, true);
            
            // Se o iframe carregar novo conteúdo, re-delegar
            iframe.addEventListener('load', function() {
                _delegateToIframes();
            });
        } catch(e) {
            // Cross-origin — não podemos acessar
            console.log('[TestForge] Iframe cross-origin ignorado');
        }
    });
}

// Chamar após load
window.addEventListener('load', function() {
    setTimeout(function() { 
        _showOverlay(); 
        _delegateToIframes(); 
    }, 100);
});
```

### 3.6 Shadow DOM Event Delegation

**Arquivo:** `overlay_inject.js`

**Problema:** Event listeners no `window` não penetram shadow roots — elementos dentro de shadow DOM não disparam eventos no listener do topo.

**Solução:** Escanear shadow roots existentes e registrar listeners dentro deles. Monitorar novos shadow roots via MutationObserver.

```js
// overlay_inject.js — novo helper
function _delegateToShadowRoots(root) {
    root = root || document;
    var allElements = root.querySelectorAll('*');
    allElements.forEach(function(el) {
        if (el.shadowRoot && el.shadowRoot.mode === 'open') {
            // Registrar listeners dentro do shadow root
            el.shadowRoot.addEventListener('click', function(e) {
                // Re-disparar como se fosse do topo
                handleClick(e);
            }, true);
            el.shadowRoot.addEventListener('input', function(e) {
                handleInput(e);
            }, true);
            // Recursivo: shadow root pode conter outro shadow root
            _delegateToShadowRoots(el.shadowRoot);
        }
    });
}

// MutationObserver para monitorar NOVOS shadow roots
var shadowObserver = new MutationObserver(function(mutations) {
    mutations.forEach(function(mut) {
        mut.addedNodes.forEach(function(node) {
            if (node.nodeType === 1 && node.shadowRoot) {
                _delegateToShadowRoots(node.shadowRoot);
            }
        });
    });
});
shadowObserver.observe(document.documentElement, {
    childList: true,
    subtree: true
});
```

---

## 4. Fase 3 — EVOLUIR

### 4.1 DOM Diff para Sugestão de Asserts (Cypress Studio AI Style)

**Arquivo:** `recorder_controller.py`

**Problema:** Após gravar, o usuário precisa manualmente adicionar asserts. Não há sugestão automática.

**Solução:** Após cada interação, capturar DOM hash e comparar com o anterior. Se detectar mudança, sugerir assert.

```python
_last_dom_signature = None

def _capture_dom_signature(self) -> dict:
    """Captura assinatura do DOM para detectar mudanças."""
    try:
        return self._page.evaluate("""() => {
            const sig = {
                url: window.location.href,
                title: document.title,
                elements: {}
            };
            // Captura texto visível de elementos-chave
            document.querySelectorAll('h1,h2,h3,h4,p,.alert,.message,.toast,' +
                '[role=alert],[role=status],[aria-live]').forEach(function(el) {
                var text = (el.textContent || '').trim().substring(0, 100);
                if (text) {
                    var key = el.tagName.toLowerCase() + '#' + 
                        (el.id || el.className || '') + ':' + text.substring(0, 30);
                    sig.elements[key] = text;
                }
            });
            // Captura valores de campos
            document.querySelectorAll('input[value], textarea').forEach(function(el) {
                if (el.value) {
                    var key = (el.name || el.id || el.placeholder || el.tagName) + ':value';
                    sig.elements[key] = (el.value || '').substring(0, 100);
                }
            });
            return sig;
        }""")
    except Exception:
        return None

def _compute_dom_diff(self, before: dict, after: dict) -> list:
    """Compara duas assinaturas DOM e retorna mudanças."""
    if not before or not after:
        return []
    changes = []
    # Elementos que apareceram
    for key, val in after.get("elements", {}).items():
        if key not in before.get("elements", {}):
            changes.append({"type": "appeared", "key": key, "value": val})
        elif before["elements"][key] != val:
            changes.append({"type": "changed", "key": key, 
                          "old": before["elements"][key], "new": val})
    # Elementos que sumiram
    for key, val in before.get("elements", {}).items():
        if key not in after.get("elements", {}):
            changes.append({"type": "disappeared", "key": key, "value": val})
    return changes
```

### 4.2 `press_sequentially` Fallback no Recorder

**Arquivo:** `overlay_inject.js`

**Problema:** Currencymask e CPF mask interceptam `el.value = ...` e formatam o valor. O setter hook captura o valor formatado, não o digitado. Resultado: grava valor errado.

**Solução:** Quando H21 detecta máscara (≥2 teclas, valor vazio), tentar estratégia alternativa.

```js
// overlay_inject.js — H21 já faz prompt (linha 262-321)
// Adicionar estratégia de fallback automático:

function _tryMaskFallback(el) {
    // Se H21 detectou máscara, em vez de prompt, tenta capturar
    // o valor via estratégia alternativa:
    
    // 1. Tenta ler do atributo value (pode ter sido setado programaticamente)
    var attrVal = el.getAttribute('value');
    if (attrVal && attrVal.length > 0) {
        _pushEvent('fill', el);
        return;
    }
    
    // 2. Se for Angular currencymask, o valor formatado está no placeholder
    //    ou em um elemento pai com formatação
    var parent = el.closest('[class*="currency"], [class*="moeda"], dsc-input-currency');
    if (parent) {
        var formatted = parent.textContent || '';
        if (formatted) {
            window.__tfEventQueue.push({
                type: 'fill',
                timestamp: new Date().toISOString(),
                url: window.location.href,
                page_title: document.title,
                target: _extractTarget(el),
                value: formatted,
                source: 'currencymask_heuristic'
            });
            return;
        }
    }
    
    // 3. Fallback: prompt (H21 exists)
}
```

### 4.3 Catálogo SQLite de Intents (Phase 4)

**Arquivo:** `healing/sqlite_intent_catalog.py`

**Problema:** Cada execução precisa re-resolver locators — sem cache, sem aprendizagem.

**Solução:** O `SqliteIntentCatalog` já existe (Phase 4). Integrar ao recorder:

```python
# Em RecorderController.start():
self._catalog = SqliteIntentCatalog(
    os.path.join(self._store._session_dir, "intent_catalog.sqlite")
)

# Em _persist_raw_event():
self._catalog.record_intent(
    intent_text=event.value or "",
    url_signature=_normalize_url(event.url),
    action=event.event_type,
    candidates=target_data,  # Lista de estratégias
    success=True,
)
```

### 4.4 Self-Healing Durante Gravação

**Arquivo:** `recorder_controller.py`

**Problema:** Se um fill falha durante gravação (ex: máscara rejeita valor), ninguém percebe até o compile/run.

**Solução:** Validar fill imediatamente após gravar.

```python
def _validate_fill(self, step_data: dict):
    """Verifica se o fill foi realmente aplicado ao campo."""
    try:
        selector = step_data.get("selector", "")
        expected_value = step_data.get("value", "")
        if not selector or not expected_value:
            return
        
        actual = self._page.evaluate(
            f"""() => {{
                var el = document.querySelector({json.dumps(selector)});
                return el ? el.value : null;
            }}"""
        )
        if actual != expected_value:
            logger.warning("Fill validation failed: expected=%s actual=%s",
                          expected_value, actual)
            # Tenta fallback: press_sequentially
            self._heal_fill(selector, expected_value)
    except Exception:
        pass
```

---

## 5. Estratégias de Captura por Framework

```
Framework       | addEvent- | Setter  | _value- | Mutation- | CDP Key | page.
                | Listener  | Hook    | Tracker | Observer  | Events  | evaluate
────────────────┼───────────┼─────────┼─────────┼───────────┼─────────┼─────────
Plain HTML      | ✅ nativo | ✅      | n/a     | n/a       | ✅      | ✅
Angular ngModel | ❌ zone.js | ✅ v0.3 | n/a     | ✅ attr   | ✅      | ✅
Angular Reactive| ❌ zone.js | ✅ v0.3 | n/a     | ❌        | ✅      | ✅
Angular Mat     | ❌ mask    | ✅ v0.4 | n/a     | n/a       | ✅      | ✅
React useState  | ❌ synth.ev| ❌      | ✅ NEW  | ❌        | ✅      | ✅
React Hook Form | ❌ synth.ev| ❌      | ✅ NEW  | ❌        | ✅      | ✅
Vue v-model     | ✅ (setter)| ✅      | n/a     | ✅ attr   | ✅      | ✅
Svelte          | ✅ (setter)| ✅      | n/a     | n/a       | ✅      | ✅
PrimeFaces      | ❌ jQuery  | ❌      | n/a     | ❌        | ✅      | ✅
Legacy ASP.NET  | ✅ (post)  | n/a     | n/a     | n/a       | ✅      | ✅

Legenda: ✅ funciona | ❌ não funciona | n/a não se aplica
```

### Handlers por Framework

| Handler | Status | Tipo |
|---------|--------|------|
| `AngularMaterialHandler` | ✅ Completo (451 linhas) | Detect + Execute + Normalize |
| `ReactMUIHandler` | 🟡 Skeleton (70 linhas) | Detect only — execute() levanta NotImplementedError |
| `PrimeFacesHandler` | 🟡 Skeleton (65 linhas) | Detect only — execute() levanta NotImplementedError |
| `VuetifyHandler` | ❌ Não existe | — |

---

## 6. Arquitetura Alvo

```
┌──────────────────────────────────────────────────────────────┐
│                        RECORDER                              │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │           Capture Layer (overlay_inject.js)          │   │
│  │                                                      │   │
│  │  ┌──────────┐  ┌──────────────┐  ┌────────────────┐ │   │
│  │  │ Event    │  │ Setter Hook  │  │ Value Mutation │ │   │
│  │  │ Listener │  │ (prototype)  │  │ Observer (attr)│ │   │
│  │  │          │  │ + _valueTrkr │  │                │ │   │
│  │  └──────────┘  └──────────────┘  └────────────────┘ │   │
│  │                                                      │   │
│  │  ┌──────────┐  ┌──────────────┐  ┌────────────────┐ │   │
│  │  │ Periodic │  │ DOM Eval     │  │ Coalescing     │ │   │
│  │  │ Fill Scan│  │ (fallback)   │  │ Debounce       │ │   │
│  │  └──────────┘  └──────────────┘  └────────────────┘ │   │
│  └──────────────────────────────────────────────────────┘   │
│                           │                                  │
│  [FrameworkDetector] ─────┘  (detecta e adapta estratégias)  │
│                           │                                  │
│  ┌──────────────────────────────────────────────────────┐   │
│  │           Flush Layer (recorder_controller.py)        │   │
│  │                                                      │   │
│  │  ┌──────────┐  ┌──────────────┐  ┌────────────────┐ │   │
│  │  │ Events   │  │ Snapshots    │  │ DOM Diff Calc  │ │   │
│  │  │ + Steps  │  │ (DOM + SS    │  │ (assert suger. │ │   │
│  │  │          │  │  + AX + CDP) │  │  + field diff) │ │   │
│  │  └──────────┘  └──────────────┘  └────────────────┘ │   │
│  │                                                      │   │
│  │  ┌──────────┐  ┌──────────────┐  ┌────────────────┐ │   │
│  │  │ Network  │  │ Framework    │  │ Pseudo-Submit  │ │   │
│  │  │ Capture  │  │ Re-detect    │  │ Detection      │ │   │
│  │  └──────────┘  └──────────────┘  └────────────────┘ │   │
│  └──────────────────────────────────────────────────────┘   │
│                           │                                  │
│  ┌──────────────────────────────────────────────────────┐   │
│  │           Persist Layer                              │   │
│  │                                                      │   │
│  │  raw_events.jsonl          steps.jsonl               │   │
│  │  field_snapshots.jsonl     value_mutations.jsonl     │   │
│  │  field_diffs.jsonl         suggested_assertions.jsonl│   │
│  │  enriched_targets.jsonl    network_log.json          │   │
│  │  field_values.json         final_state_snapshot.json │   │
│  │  ax_snapshots/{id}.json   trace.zip (CDP)           │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

---

## 7. Roadmap e Esforço

### Sprint 1 — Estabilização Imediata (~12h)

| # | Tarefa | Arquivo | Esforço | Impacto |
|---|--------|---------|---------|---------|
| 1 | BUG-004: event_id monotônico via Python | `overlay_inject.js`, `recorder_controller.py` | 1h | 🟢 |
| 2 | BUG-002: validar DOM > 100 bytes | `recorder_controller.py` | 30min | 🟢 |
| 3 | BUG-003: 3 contadores separados | `recorder_controller.py` | 1h | 🟢 |
| 4 | BUG-001: `<select>` como `select_option` | `overlay_inject.js` | 2h | 🟢 |
| 5 | BUG-008: debounce coalescing (400ms) | `overlay_inject.js` | 1h | 🟢 |
| 6 | Setter hook: `_valueTracker` reset | `overlay_inject.js` | 3h | 🟢 |
| 7 | Framework detector ativo por padrão | `recorder_controller.py` | 2h | 🟡 |
| 8 | MutationObserver para attr `value` | `overlay_inject.js` | 1h | 🟡 |
| 9 | BUG-007: navigation dedup (URL igual) | `recorder_controller.py` | 1h | 🟡 |

### Sprint 2 — Captura Robusta (~24h)

| # | Tarefa | Esforço | Impacto |
|---|--------|---------|---------|
| 10 | Enriquecer target info com match_count | 4h | 🟢 |
| 11 | Snapshot diff no flush | 3h | 🟢 |
| 12 | CDP sempre ativo (remover flag) | 2h | 🟢 |
| 13 | Shadow DOM event delegation | 4h | 🟡 |
| 14 | CDP Input.dispatchKeyEvent listener | 4h | 🟡 |
| 15 | React MUI handler executável | 4h | 🟡 |
| 16 | PrimeFaces handler executável | 4h | 🟡 |

### Sprint 3 — Inteligência (~30h)

| # | Tarefa | Esforço | Impacto |
|---|--------|---------|---------|
| 17 | DOM diff → sugestão de assert | 6h | 🟢 |
| 18 | press_sequentially fallback no recorder | 3h | 🟢 |
| 19 | Value capture fallback Python | 2h | 🟢 |
| 20 | Iframe-aware event delegation | 4h | 🟡 |
| 21 | Testes E2E React + Angular + masked | 8h | 🟢 |
| 22 | Modo "Playback Cego" validation | 4h | 🟡 |
| 23 | Self-healing durante gravação | 6h | 🟢 |

### Sprint 4 — Resiliência (~30h)

| # | Tarefa | Esforço | Impacto |
|---|--------|---------|---------|
| 24 | Catálogo SQLite de intents (Phase 4) | 6h | 🟢 |
| 25 | Super-selector runtime (Phase 3) | 8h | 🟢 |
| 26 | Vuetify handler (Vue) | 3h | 🟡 |
| 27 | Select2/jQuery handler | 3h | 🟡 |
| 28 | Playwright trace.zip + CDP viewer | 4h | 🟡 |
| 29 | Adaptive Waiting (networkIdle) | 4h | 🟡 |

---

## 8. Checklist de Prontidão para Gravar

Para iniciar gravações com qualidade mínima:

- [ ] **BUG-004**: `event_id` não duplica após navegação
- [ ] **BUG-002**: DOM snapshots têm conteúdo real
- [ ] **BUG-001**: `<select>` gera `select_option`
- [ ] **BUG-008**: Debounce coalescing (1 fill por campo)
- [ ] **Setter hook** captura React (`_valueTracker`)
- [ ] **Framework detector** ativo (adapta captura)
- [ ] **CDP** ativo por padrão (AX tree + tracing)

Após o checklist, gravações funcionam para:
- ✅ Plain HTML
- ✅ Angular (com/sem Material)
- ✅ React (controlled + uncontrolled)
- ✅ Vue / Svelte
- ✅ ASP.NET legado (__doPostBack)

---

## 9. Riscos e Mitigações

| Risco | Probabilidade | Impacto | Mitigação |
|-------|--------------|---------|-----------|
| React 19 compiler muda _valueTracker | Média | Alto | Feature flag para React 18 vs 19; detectar via `React.version` |
| Angular zone.js interfere com setter hook | Baixa | Médio | Usar `NgZone.runOutsideAngular()` para hooks |
| Cross-origin iframes impossíveis de capturar | Alta | Médio | Documentar limitação; capturar via CDP session do iframe quando mesma origin |
| Shadow DOM fechado não acessível | Alta | Baixo | Não capturar; apenas shadow roots `mode: "open"` |
| Performance: CDP + tracing + snapshot diffs | Média | Médio | O batch de 300ms já lida com latência. CDP custa ~50ms/evento |
| Browser corporativo bloqueia CDP (BUG-006) | Média | Alto | Fallback para modo legacy sem CDP; detectar e warn |
