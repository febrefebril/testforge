# TestForge — Bugs Conhecidos e Resolvidos

**Versão:** 0.4.2  
**Última atualização:** 2026-06-30  
**Status:** Consolidado — Sprint 0 hotfixes (30+ bugs corrigidos)

---

## 📋 Resumo Executivo

A documentação de bugs do TestForge cobre:

1. **5 Bugs Corrigidos** — Implementados e validados em v0.3.1 (commit c5c1d01)
2. **20 Bugs Abertos** — Identificados em fase de teste corporativo (SIMAX, CAIXA)
3. **3 Limitações Conhecidas** — Não são bugs, mas restrições operacionais
4. **Priorização P0/P1/P2** — Roadmap recomendado para próximas releases

---

## ✅ Seção 1: Bugs Corrigidos em v0.3.1

### BUG-TIM-001: Healing não resolve timeout em FAM-02 (Timing)

| Propriedade | Valor |
|-------------|-------|
| **Severidade** | Média |
| **Status** | ✅ **Corrigido** |
| **Commit** | `c5c1d01` |
| **Família** | FAM-02 (Synchronization) |
| **Página teste** | `curation/fam-timing/index.html` |

**Problema:**
O `SmartStepRunner` não implementava estratégia de `visibility_wait`. Quando o healing propunha esperar visibilidade antes de clicar, o runner ignorava a estratégia e tentava clicar imediatamente, mesmo com elemento fora de tela.

**Correção:** O step_runner agora suporta `visibility_wait` — aguarda `page.wait_for_selector(sel, state="visible", timeout=5000)` antes do click.

---

### BUG-DOM-001: Healing não resolve stale element em FAM-05 (Dynamic DOM)

| Propriedade | Valor |
|-------------|-------|
| **Severidade** | Média |
| **Status** | ✅ **Corrigido** |
| **Commit** | `c5c1d01` |
| **Família** | FAM-05 (Dynamic DOM) |

**Problema:**
Elemento removido do DOM após navegação SPA (`#old-btn` → `#new-btn`). O runner ignorava o `new_locator` da proposta de healing.

**Correção:** Runner agora aceita `new_locator` na primeira tentativa, aguarda estabilização de DOM, faz reacquire do elemento.

---

### BUG-STA-001: Healing não resolve overlay blocking em FAM-04

| Propriedade | Valor |
|-------------|-------|
| **Severidade** | **Alta** |
| **Status** | ✅ **Corrigido** |
| **Commit** | `c5c1d01` |
| **Família** | FAM-04 (Application State) |

**Problema:**
Elemento obscured por overlay era classificado como FAM-01 (locator) em vez de FAM-04 (state).

**Correção:** 
- Classifier agora prioriza "intercepts pointer events"
- `SmartStepRunner._dismiss_overlays()` tenta Escape, clica em overlay, removes backdrop

---

### BUG-INP-001: Healing não resolve masked input em FAM-06

| Propriedade | Valor |
|-------------|-------|
| **Severidade** | Média |
| **Status** | ✅ **Corrigido** |
| **Commit** | `c5c1d01` |
| **Família** | FAM-06 (Input) |

**Problema:**
Campo CPF com máscara JS. `fill()` bloqueado pela máscara.

**Correção:** `SmartStepRunner` detecta `press_sequentially` e usa `page.type()` com delay=30.

---

### BUG-CLS-001: net::ERR_ classifica como FAM-02 (Timing)

| Propriedade | Valor |
|-------------|-------|
| **Severidade** | Baixa |
| **Status** | ✅ **Corrigido** |
| **Commit** | `c5c1d01` |
| **Família** | FAM-10 (Execution) |

**Problema:**
`net::ERR_CONNECTION_REFUSED` era mapeado para FAM-02 (Timing), não FAM-10 (Execution).

**Correção:** Adicionada keyword `connection refused` → FAM-10 (OBS-003). Mantém `net::err_timed_out` → FAM-02.

---

## ✅ Seção 1.5: Bugs Corrigidos em v0.4.1 (Sprints 1-6)

### BUG-NRM-001: Normalizer — contenteditable false positive + Angular datepicker dedup

| Propriedade | Valor |
|-------------|-------|
| **Severidade** | Média |
| **Status** | ✅ **Corrigido** |
| **Commit** | `fa01a77` |
| **Módulo** | `semantic/recording_normalizer.py` |

**Problema:** Contenteditable detection falso positivo em elementos não editáveis. Datepicker dedup falhando em Angular com padrão CAIXA.

**Correção:** Heurística refinada para contenteditable. Datepicker dedup migrado para `AngularMaterialHandler.normalize()`.

---

### BUG-NRM-002: 3 bugs causando healing_rejected no botão Calcular

| Propriedade | Valor |
|-------------|-------|
| **Severidade** | Média |
| **Status** | ✅ **Corrigido** |
| **Commit** | `41e2818` |
| **Módulo** | `semantic/recording_normalizer.py` |

**Problema:** Três bugs no normalizer que causavam `healing_rejected` em steps de clique no botão "Calcular".

**Correção:** Correção de prioridade de candidatos, filtro de SVG inner_html, stripping de whitespace em field values.

---

### BUG-EXE-001: Executor usa intention_string como fill label

| Propriedade | Valor |
|-------------|-------|
| **Severidade** | Baixa |
| **Status** | ✅ **Corrigido** |
| **Commit** | `b95c7b8` |
| **Módulo** | `runner/step_executor.py` |

**Problema:** Executor usava `intention_string` (texto cru) como label para fill, em vez de `accessible_name`.

**Correção:** Substituído por `accessible_name` para melhor match com elementos de formulário.

---

### BUG-DEDUP-001: CAIXA datepicker pattern + --debug-healing

| Propriedade | Valor |
|-------------|-------|
| **Severidade** | Baixa |
| **Status** | ✅ **Corrigido** |
| **Commit** | `6076b7c` |
| **Módulo** | `semantic/recording_normalizer.py` |

**Problema:** Datepicker da CAIXA com padrão diferente de Angular — não era deduplicado.

**Correção:** Adicionado padrão CAIXA ao detector de datepicker. `--debug-healing` adicionado ao `run-incremental`.

---

### BUG-ASRT-001: Assert — element capture + semantic identity + hover highlight

| Propriedade | Valor |
|-------------|-------|
| **Severidade** | Média |
| **Status** | ✅ **Corrigido** |
| **Commit** | `ac4c65a` |
| **Módulo** | `runner/step_postcondition.py` |

**Problema:** Assert oracle capturava elemento errado, identidade semântica falhava com autogenerated IDs, hover highlight quebrado.

**Correção:** Degradação de IDs autogerados, captura por role/label/text, hover highlight via `locator.hover()`.

---

### BUG-RUN-001: 4 bugs — fill dedup, wrong selector, assert oracle failure

| Propriedade | Valor |
|-------------|-------|
| **Severidade** | Média |
| **Status** | ✅ **Corrigido** |
| **Commit** | `a3d9ff6` |
| **Módulo** | runner + normalizer |

**Problema:** Quatro bugs: (1) fill dedup removendo steps válidos, (2) seletor errado em candidates, (3) assert oracle falhando com timeout, (4) UnboundLocalError em `_validate_assert`.

**Correção:** Correções em cascata nos três módulos.

---

## 🔴 Seção 2: Bugs Abertos (20 Issues)

### P0 — Bloqueadores Críticos

#### BUG-001: `<select>` gera seletor de `<input>` (P0)

Compilador infere tipo errado. Gera `label:has-text("UF") + input` em vez de `select[name="lstUf"]`.

**Esperado:** Usar `page.select_option()` para todos os `<select>` gravados.

---

#### BUG-002: DOM snapshots com 0 bytes (P0)

Arquivos criados mas vazios. `DOMSnapshotCollector` não persiste `page.content()`.

**Esperado:** Validar `len(html) > 100` bytes antes de salvar.

---

#### BUG-003: Contagem divergente (P0)

Terminal: `1 passos gravados`, Compile: `15 steps`, Runner: `15 steps`. Confuso.

**Esperado:** Separar: eventos brutos, steps semânticos, asserts, steps executáveis.

---

#### BUG-004: event_id reinicia após navegação (P0)

`event_id` não é monotônico. Múltiplos `evt_0001` em URLs diferentes.

**Esperado:** Nenhum `event_id` duplicado em um `recording_id`.

---

#### BUG-005: Sessões diferentes anexadas (P0)

`record --name X` anexa silenciosamente em vez de criar novo recording.

**Esperado:** Oferecer opção: sobrescrever, criar X_2, ou anexar intencionalmente.

---

#### BUG-006: Browser Playwright bloqueado (P0)

Impossível usar em ambiente corporativo CAIXA.

**Esperado:** Fallback: Playwright → Edge/Chrome instalado → CDP → recorder externo.

---

#### BUG-007: Tela pisca SIMAX (P0)

Toda interação provoca reload visual. Múltiplas navegações a `novo_agendamento.asp`.

**Esperado:** Distinguir clique simples, submit, POST, reload, overlay.

---

### P1 — Tornar Testes Confiáveis (7 issues)

#### BUG-008: Digitação vira dezenas de fills

Campo CPF gera: `fill "4"`, `fill "40"`, ..., `fill "407.123.456-89"`.

**Esperado:** Debounce por campo. Um único `fill()` com valor final.

---

#### BUG-009: goto() excessivo no script

Script contém múltiplos `page.goto(BASE_URL)` no meio, apagando estado.

**Esperado:** `goto()` apenas no início. Navegações causadas usam `expect_navigation()`.

---

#### BUG-010: Healer sugere candidatos genéricos

Healing sugere `text=Selecione` ao invés de seletor específico.

**Esperado:** Ranking penaliza genéricos. Top 5 relacionados ao evento original.

---

#### BUG-011: Métricas inconsistentes

Log: `Total healings: 1`, Resumo: `4 falhas, 4 curados`. Números não batem.

**Esperado:** Separar: falhas_detectadas, healings_tentados, aplicados, validados, rejeitados.

---

#### BUG-012: Assertions frágeis (CSS estrutural)

Assertions: `app-root > app-calculadora > div > p:nth-child(3)`.

**Esperado:** Prefer semântico: texto, role, atributos estáveis.

---

#### BUG-013: Elementos bounding box zero aceitos

Seletores para elementos com `{x:0, y:0, width:0, height:0}`.

**Esperado:** Validar: visível, habilitado, bounding_box.area > 0, não obscured, estável.

---

#### BUG-014: httpx ausente nas dependências

Código importa `httpx`, mas não está em `requirements.txt`.

**Esperado:** `pip install -r requirements.txt && testforge --help` executa sem erro.

---

#### BUG-020: Runner continua após falhas críticas

Se UF falha, Edifício/Data ainda são executados e contadas como falhas independentes.

**Esperado:** Steps com `blocking=true` fazem dependentes ficar `blocked_by_previous_failure`.

---

### P2 — Melhorias de DX (6 issues)

#### BUG-015: URL com & quebra PowerShell

`record --name login https://site.com?param=1&other=2` quebra porque `&` é operador.

**Esperado:** CLI alerta: "No PowerShell, use aspas". Documentação clara.

---

#### BUG-016: Logs truncados

Erros aparecem como `candidates: [:h...`. Informação cortada.

**Esperado:** Terminal resume, arquivo salva relatório completo em `runs/<id>/<time>/healing_report.md`.

---

#### BUG-017: Steps pulados não explicados

Step 14, depois 17, depois 19. Steps 15, 16, 18 desaparecem.

**Esperado:** Mostrar `Step 15: skipped — evento duplicado compactado`.

---

#### BUG-018: Sem artefato semântico auditável

Sem `semantic_steps.jsonl`. Contrato opaco: raw_events → script.

**Esperado:** Gerar `semantic_steps.jsonl` com id, action, selector, evidence, healing_applied.

---

## ⚠️ Seção 3: Limitações Conhecidas

### LIM-001: 10/10 estratégias de healing implementadas ✅

- visibility_wait, press_sequentially, overlay_dismiss, dialog_handler
- iframe_switch, synthetic_click, label_click, semantic_locator_conversion
- has_text_fallback, xpath_fallback

### LIM-002: Evidência coletada APÓS page.goto()

Chamar `collector.start()` ANTES de `page.goto()` para capturar eventos iniciais.

### LIM-003: Query strings em SimpleHTTPRequestHandler

Usar `http.server.HTTPServer` com `directory=` (Python 3.7+), ou injetar via `page.evaluate()`.

---

## 📊 Estatísticas (v0.3.1)

| Métrica | Valor |
|---------|-------|
| Testes totais | 162 |
| Taxa de passa | 100% (162/162) |
| Bugs corrigidos | 5 |
| Estratégias de healing | 10/10 |
| Keywords de classificação | 51 |

**Cobertura:** 11/11 Famílias (FAM-01 a FAM-11)

---

## 🎯 Priorização

**P0** (Antes de evoluir): BUG-001, 002, 003, 004, 005, 006, 007  
**P1** (Confiabilidade): BUG-008, 009, 010, 011, 012, 013, 014, 020  
**P2** (DX): BUG-015, 016, 017, 018

---

## 📚 Arquivo Original

Consolidado de:
- `docs/BUGS.md` (184 linhas)
- `docs/bugs.md` (1713 linhas)

Histórico em: `.planning/ARCHIVE/bugs.md`
