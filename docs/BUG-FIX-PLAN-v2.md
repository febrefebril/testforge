# TestForge — Plano de Correção: bugs.md

**Fonte:** `docs/bugs.md` — 20 bugs de testes reais (CAIXA)
**Data:** 2026-06-15
**Status:** 🔴 7 P0 · 🟡 7 P1 · 🟢 6 P2

---

Cada bug segue: **Verificar → Corrigir → Testar**.

---

# 🔴 P0 — Corrigir antes de continuar evoluindo o self-healing

---

## BUG-001: `<select>` gera seletor de `<input>` (label:has-text + input inexistente)

### US-001-V: Verificar

**Objetivo:** Confirmar que script gerado para `<select>` usa `label:has-text("UF") + input` em vez de `select_option`.

**Passos:**
1. Gravar fluxo no SIMAX com campos `<select name="lstUf">`, `<select name="lstEdificio">`, `<select name="lstData">`
2. Compilar: `testforge compile simax`
3. Verificar script gerado

**Critério de falha:** Script contém `label:has-text("UF") + input` — seletor que não existe.

**Status:** [ ] Verificado

---

### US-001-F: Corrigir

**Objetivo:** Compiler gerar `select_option()` para elementos `<select>`.

**Solução:**
- No `RecordingNormalizer._build_target()`: quando `target_data["tag"] == "select"`, gerar candidatos `select[name="lstUf"]`, `#lstUf`, `select[aria-label="UF"]`
- No `PlaywrightCompiler._generate()`: quando `action == "click"` e target é `<select>`, gerar `page.select_option(sel, value)` em vez de `page.click(sel)`
- Adicionar `infer_playwright_action(tag, input_type, action) → "select_option" | "fill" | "click" | "check"`
- No `cmd_run`: step de `select_option` → `page.select_option(sel, value, timeout=5000)`

**Arquivos:**
- `src/testforge/semantic/recording_normalizer.py` — `_build_target()` detecta tag select
- `src/testforge/semantic/compiler.py` — `_gen_select()` novo método
- `src/testforge/cli/app.py` — `cmd_run` suporta `select_option`

**Status:** [ ] Corrigido

---

### US-001-T: Testar

**Objetivo:** Script gerado usa `select_option()` para `<select>`.

**Teste:**
```bash
# Criar página de teste com <select>
# tests/test_pages/curation/fam-select/index.html
# Gravar, compilar, verificar script gerado
pytest tests/test_semantic.py -k "select" -v
```

**Critérios:**
- [ ] Script contém `page.select_option('select[name="lstUf"]', 'MT')`
- [ ] Script NÃO contém `label:has-text("UF") + input`
- [ ] Teste passa no fake-bank com `<select>`

**Status:** [ ] Testado

---

## BUG-002: DOM snapshots com 0 bytes

### US-002-V: Verificar

**Objetivo:** Confirmar que `dom_snapshots/*.html` são salvos vazios (0 bytes).

**Passos:**
1. Gravar qualquer fluxo
2. Verificar `recordings/<id>/dom_snapshots/evt_*.html`
3. `ls -la` → vários arquivos com 0 bytes

**Status:** [ ] Verificado

---

### US-002-F: Corrigir

**Objetivo:** Garantir que DOM snapshot contém HTML não vazio.

**Solução:**
- Em `EvidenceCollector.capture_dom()`: validar `len(html.strip()) >= 100`
- Se vazio: registrar `quality_flags.append("DOM_SNAPSHOT_EMPTY")` + alerta
- No recorder: adicionar `page.wait_for_load_state("domcontentloaded")` antes de capturar
- Adicionar validação no `finalize()`: se >50% snapshots vazios → warning crítico

**Arquivos:**
- `src/testforge/evidence/evidence_collector.py` — validação de conteúdo
- `src/testforge/recorder/recorder_controller.py` — wait_for_load_state antes do snapshot

**Status:** [ ] Corrigido

---

### US-002-T: Testar

**Objetivo:** Nenhum DOM snapshot com 0 bytes.

**Teste:**
```bash
testforge record http://localhost:8765 --name "test-dom" --headless
find recordings/test-dom/dom_snapshots -name "*.html" -exec wc -c {} \; | grep " 0 "
# Deve retornar vazio (nenhum arquivo com 0 bytes)
```

**Critérios:**
- [ ] Todos os snapshots têm ≥ 100 bytes
- [ ] Se snapshot vazio, quality_flag registrado
- [ ] Warning se >50% vazios

**Status:** [ ] Testado

---

## BUG-003: Contagem de passos divergente (record: 1, compile: 15, run: 15)

### US-003-V: Verificar

**Objetivo:** Confirmar que o contador de passos no record difere do compile/run.

**Passos:**
1. Gravar fluxo: `testforge record http://localhost:8765 --name "count-test"`
2. Anotar "✓ N passos gravados" do terminal
3. Compilar: `testforge compile count-test`
4. Anotar "SemanticTestCase: M steps" do terminal
5. Comparar N vs M

**Critério de falha:** N ≠ M sem explicação clara.

**Status:** [ ] Verificado

---

### US-003-F: Corrigir

**Objetivo:** Separar claramente os 3 contadores no log.

**Solução:**
- No `cmd_record.finalize()`: exibir separadamente:
  - Eventos brutos capturados
  - Steps semânticos gerados (após normalização)
  - Asserts manuais
- No `cmd_compile`: exibir "Steps executáveis: N (M asserts + K interações)"
- No `cmd_run`: exibir "Carregados N passos (M interações + K asserts)"

**Arquivos:**
- `src/testforge/cli/app.py` — `cmd_record`, `cmd_compile`, `cmd_run`

**Status:** [ ] Corrigido

---

### US-003-T: Testar

**Objetivo:** Contadores consistentes e explicados.

**Teste:**
```bash
testforge record http://localhost:8765 --name "count-test"
testforge compile count-test
testforge run semantic_tests/ST-count-test/test_st_count_test.py
```

**Critérios:**
- [ ] Terminal mostra "Eventos brutos: N" e "Steps semânticos: M"
- [ ] Se N ≠ M, explicação visível (ex: "eventos compactados: K")
- [ ] Usuário entende a diferença

**Status:** [ ] Testado

---

## BUG-004: event_id reinicia após navegação

### US-004-V: Verificar

**Objetivo:** Confirmar que `evt_0001` aparece múltiplas vezes no mesmo recording.

**Passos:**
1. Gravar fluxo com múltiplas navegações
2. Verificar `raw_events.jsonl`:
```bash
grep "evt_0001" recordings/<id>/raw_events.jsonl | wc -l
```

**Critério de falha:** `evt_0001` aparece mais de 1 vez.

**Status:** [ ] Verificado

---

### US-004-F: Corrigir

**Objetivo:** event_id monotônico global dentro do recording.

**Solução:**
- No `RecorderController`: usar contador global `self._event_counter` inicializado em 0
- Nunca resetar após navegação
- Se precisar de subfluxo, usar `navigation_id` separado, mas event_id segue monotônico

**Arquivos:**
- `src/testforge/recorder/recorder_controller.py` — `_event_counter` global
- `src/testforge/recorder/raw_event.py` — documentar convenção

**Status:** [ ] Corrigido

---

### US-004-T: Testar

**Objetivo:** Nenhum event_id duplicado.

**Teste:**
```bash
# Gravar fluxo com 3 navegações
python -c "
import json
with open('recordings/<id>/raw_events.jsonl') as f:
    ids = [json.loads(l)['event_id'] for l in f]
assert len(ids) == len(set(ids)), f'Duplicate event_ids found!'
print('✓ All event_ids unique')
"
```

**Critérios:**
- [ ] Todos os event_id são únicos
- [ ] Sequência monotônica: evt_0001, evt_0002, ..., evt_NNNN

**Status:** [ ] Testado

---

## BUG-005: Sessões diferentes anexadas no mesmo recording

### US-005-V: Verificar

**Objetivo:** Confirmar que `record --name X` anexa eventos a recording existente.

**Passos:**
1. `testforge record http://localhost:8765 --name "dup-test"` → Shift+S
2. `testforge record http://localhost:8765 --name "dup-test"` → Shift+S
3. Verificar `recordings/dup-test/raw_events.jsonl`

**Critério de falha:** Arquivo contém eventos das 2 sessões.

**Status:** [ ] Verificado

---

### US-005-F: Corrigir

**Objetivo:** Novo record com mesmo nome cria pasta incremental ou alerta.

**Solução:**
- Em `cmd_record`: se `recordings/{name}/` já existe:
  - Criar `recordings/{name}_2/` (incremental)
  - Ou: alertar e perguntar (se interativo)
  - Padrão seguro: **nunca anexar silenciosamente**

**Arquivos:**
- `src/testforge/cli/app.py` — `cmd_record` detecta pasta existente

**Status:** [ ] Corrigido

---

### US-005-T: Testar

**Objetivo:** Segunda gravação não contamina a primeira.

**Teste:**
```bash
testforge record http://localhost:8765 --name "unique-test"
testforge record http://localhost:8765 --name "unique-test"
ls recordings/unique-test*  # Deve ter unique-test e unique-test_2
```

**Critérios:**
- [ ] Segunda gravação cria `_2` ou alerta
- [ ] Primeira gravação intacta
- [ ] Nenhum merge silencioso

**Status:** [ ] Testado

---

## BUG-006: Browser Playwright bloqueado sem fallback (Edge/Chrome corporativo)

### US-006-V: Verificar

**Objetivo:** Confirmar que `chromium.launch()` falha em ambiente corporativo CAIXA.

**Passos:**
1. No ambiente CAIXA: `testforge record https://simax.caixa/...`
2. Verificar erro: `Browser closed unexpectedly` ou `Target closed`

**Status:** [ ] Verificado

---

### US-006-F: Corrigir

**Objetivo:** Fallback em camadas para browser corporativo.

**Solução:**
- Camada 1: `chromium.launch()` (padrão)
- Camada 2: `chromium.launch(channel="msedge")` (Edge instalado)
- Camada 3: `chromium.launch(channel="chrome")` (Chrome instalado)
- Camada 4: `chromium.connect_over_cdp("http://127.0.0.1:9222")` (navegador já aberto)
- Flag `--browser edge|chrome|chromium` para seleção manual

**Arquivos:**
- `src/testforge/cli/app.py` — `cmd_record` e `cmd_run` com fallback
- `src/testforge/recorder/recorder_controller.py` — aceitar `browser_type`

**Status:** [ ] Corrigido

---

### US-006-T: Testar

**Objetivo:** TestForge funciona com Edge/Chrome corporativo.

**Teste:**
```bash
testforge record http://localhost:8765 --browser edge --headless
testforge run script.py --browser chrome --headless
```

**Critérios:**
- [ ] `--browser edge` funciona se Edge instalado
- [ ] `--browser chrome` funciona se Chrome instalado
- [ ] Fallback automático sem flag
- [ ] Mensagem clara se nenhum browser disponível

**Status:** [ ] Testado

---

## BUG-007: Tela pisca/recarrega no SIMAX durante gravação

### US-007-V: Verificar

**Objetivo:** Confirmar que a página recarrega a cada interação no SIMAX.

**Passos:**
1. Gravar no SIMAX: preencher formulário, clicar em elementos
2. Observar se a tela "pisca" a cada clique

**Status:** [ ] Verificado

---

### US-007-F: Corrigir

**Objetivo:** Recorder não interferir no fluxo, distinguir clique de submit.

**Solução:**
- Distinguir eventos: clique simples vs submit vs POST/navegação vs alteração de `<select>` com reload
- Para páginas ASP clássicas: detectar form postback e tratar como navegação intencional
- Adicionar `page.wait_for_load_state("networkidle")` após ações que causam navegação
- Overlay do recorder: garantir que não bloqueia eventos da página

**Arquivos:**
- `src/testforge/recorder/recorder_controller.py` — detecção de postback
- `src/testforge/semantic/recording_normalizer.py` — classificar navegação vs submit

**Status:** [ ] Corrigido

---

### US-007-T: Testar

**Objetivo:** Gravação no SIMAX sem flicker.

**Critérios:**
- [ ] Tela não "pisca" durante gravação
- [ ] Eventos de submit vs clique distinguidos
- [ ] Formulários ASP com postback funcionam

**Status:** [ ] Testado

---

---

# 🟡 P1 — Corrigir para tornar os testes confiáveis

---

## BUG-008: Digitação caractere por caractere gera dezenas de fills

### US-008-V: Verificar

**Objetivo:** Confirmar que cada tecla vira um step de fill.

**Passos:**
1. Gravar login com CPF digitado caractere por caractere
2. Verificar `raw_events.jsonl` → múltiplos eventos fill para o mesmo seletor

**Status:** [ ] Verificado

---

### US-008-F: Corrigir

**Objetivo:** Compactar fills sequenciais do mesmo campo.

**Solução:**
- `RecordingNormalizer._compact_fill_events()`: para eventos consecutivos com mesmo target, manter apenas o último valor
- Debounce: dentro de 500ms, mesmo seletor → só último fill persiste

**Arquivos:**
- `src/testforge/semantic/recording_normalizer.py` — `compact_fill_events()`

**Status:** [ ] Corrigido

---

### US-008-T: Testar

**Critérios:**
- [ ] Campo CPF digitado → 1 fill no script (não 11)
- [ ] Valor final é o correto
- [ ] Sem perda de eventos de campos diferentes

**Status:** [ ] Testado

---

## BUG-009: goto() excessivo no script gerado

### US-009-V / US-009-F / US-009-T

**Verificar:** Script contém múltiplos `page.goto(BASE_URL)` no meio do fluxo.
**Corrigir:** Script inicia com `goto()` uma vez. Navegações subsequentes usam `expect_navigation()` ou `wait_for_url()` apenas quando ação realmente causa navegação.
**Testar:** Script tem no máximo 1 `goto()` + navegações com `expect_navigation`.

---

## BUG-010: Healer sugere candidatos genéricos (text=Selecione)

### US-010-V / US-010-F / US-010-T

**Verificar:** Healer retorna `text=Selecione` como candidato primário.
**Corrigir:** Adicionar `_is_generic_text()` → lista de textos penalizados: "Selecione", "OK", "Cancelar", "Página inicial", "Calcular". Score reduzido para 0.10 se texto genérico sem escopo.
**Testar:** `text=Selecione` tem score ≤ 0.10. `text=MT` (específico) mantém score normal.

---

## BUG-011: Métricas de healing inconsistentes

### US-011-V / US-011-F / US-011-T

**Verificar:** Log mostra "4 falhas, 4 curados" mas métricas dizem "Total healings: 1".
**Corrigir:** Separar métricas: `falhas_detectadas`, `healings_tentados`, `healings_aplicados`, `healings_validados`, `healings_rejeitados`. Métricas por step, não globais.
**Testar:** Métricas batem com resumo de passos.

---

## BUG-012: Assertions frágeis por CSS estrutural

### US-012-V / US-012-F / US-012-T

**Verificar:** Script contém `expect(page.locator('#app-root > app-calculadora > div.bg-highlight...')).to_contain_text(...)`.
**Corrigir:** Assertions preferem `page.get_by_text()`, `page.get_by_role()`, `page.locator("body").to_contain_text()`. CSS estrutural apenas como último recurso.
**Testar:** Assert usa `get_by_text("Valor mínimo de entrada")` em vez de cadeia CSS longa.

---

## BUG-013: Elementos com bounding box zero aceitos como alvo

### US-013-V / US-013-F / US-013-T

**Verificar:** raw_events.jsonl contém `bounding_box: {x:0, y:0, width:0, height:0}`.
**Corrigir:** Recorder rejeita alvo com área ≤ 0. Se elemento invisível, sobe para ancestral acionável.
**Testar:** Nenhum evento com bounding box zero.

---

## BUG-014: Dependência httpx ausente

### US-014-V / US-014-F / US-014-T

**Verificar:** `pip install -e . && python -c "import httpx"` → ModuleNotFoundError.
**Corrigir:** Adicionar `httpx>=0.27` em `pyproject.toml` dependencies.
**Testar:** Instalação limpa não falha.

---

---

# 🟢 P2 — Melhorias de DX e manutenção

---

## BUG-015: URL com & quebra no PowerShell

### US-015-V / US-015-F / US-015-T

**Verificar:** `testforge record https://logindes.caixa.gov.br/auth?client_id=...&response_type=...` quebra no PowerShell.
**Corrigir:** CLI valida URL: se contém `&` não escapado, alerta "No PowerShell, envolva a URL entre aspas". Detecta URL truncada (terminando em `?param=`).
**Testar:** Mensagem de alerta aparece para URL com `&`.

---

## BUG-016: Logs truncados demais

### US-016-V / US-016-F / US-016-T

**Verificar:** Erro mostra `candidates: [:h...` (truncado).
**Corrigir:** Terminal mostra resumo. Arquivo `runs/<id>/execution_report.json` salva relatório completo.
**Testar:** Relatório JSON contém lista completa de candidatos.

---

## BUG-017: Steps pulados não explicados

### US-017-V / US-017-F / US-017-T

**Verificar:** Log mostra Step 14, depois Step 17 (15 e 16 sumiram).
**Corrigir:** Todo step omitido aparece como `Step N: skipped — motivo` (duplicado, compactado, inválido).
**Testar:** Log explica cada step pulado.

---

## BUG-018: Compile sem artefato semântico auditável

### US-018-V / US-018-F / US-018-T

**Verificar:** Só script .py é gerado, sem `semantic_steps.jsonl`.
**Corrigir:** `compile` gera também `semantic_steps.jsonl` com steps normalizados para auditoria.
**Testar:** `semantic_steps.jsonl` existe e contém steps.

---

## BUG-019: Runner continua após falhas críticas de estado

### US-019-V / US-019-F / US-019-T

**Verificar:** Se UF falha, Edifício e Data continuam e acumulam falhas em cascata.
**Corrigir:** Steps com `blocking: true` → se falhar, steps dependentes marcados como `blocked_by_previous_failure`.
**Testar:** Falha em UF bloqueia Edifício/Data (não executa).

---

## BUG-020: Contrato instável entre raw_events, steps e semantic_steps

### US-020-V / US-020-F / US-020-T

**Verificar:** `raw_events.jsonl` tem 14 eventos, `steps.jsonl` tem 1, script tem 15 steps.
**Corrigir:** Documentar contrato:
- `raw_events.jsonl`: tudo capturado
- `steps.jsonl`: passos manuais/curados/asserts
- `semantic_steps.jsonl`: saída compilada (NOVO)
- `script.py`: renderização executável
**Testar:** Documentação reflete realidade. `compile --data` gera `semantic_steps.jsonl`.

---

---

# Resumo

| ID | Bug | Sev | V | F | T |
|----|-----|-----|---|---|---|
| BUG-001 | `<select>` → `<input>` | P0 | [ ] | [ ] | [ ] |
| BUG-002 | DOM snapshots 0 bytes | P0 | [ ] | [ ] | [ ] |
| BUG-003 | Contagem divergente | P0 | [ ] | [ ] | [ ] |
| BUG-004 | event_id reinicia | P0 | [ ] | [ ] | [ ] |
| BUG-005 | Sessões misturadas | P0 | [ ] | [ ] | [ ] |
| BUG-006 | Browser bloqueado | P0 | [ ] | [ ] | [ ] |
| BUG-007 | Tela pisca SIMAX | P0 | [ ] | [ ] | [ ] |
| BUG-008 | Digitação char-char | P1 | [ ] | [ ] | [ ] |
| BUG-009 | goto() excessivo | P1 | [ ] | [ ] | [ ] |
| BUG-010 | Healer genérico | P1 | [ ] | [ ] | [ ] |
| BUG-011 | Métricas inconsistentes | P1 | [ ] | [ ] | [ ] |
| BUG-012 | Assertions frágeis | P1 | [ ] | [ ] | [ ] |
| BUG-013 | Bounding box zero | P1 | [ ] | [ ] | [ ] |
| BUG-014 | httpx ausente | P1 | [ ] | [ ] | [ ] |
| BUG-015 | URL com & PowerShell | P2 | [ ] | [ ] | [ ] |
| BUG-016 | Logs truncados | P2 | [ ] | [ ] | [ ] |
| BUG-017 | Steps pulados | P2 | [ ] | [ ] | [ ] |
| BUG-018 | Sem artefato semântico | P2 | [ ] | [ ] | [ ] |
| BUG-019 | Falha em cascata | P2 | [ ] | [ ] | [ ] |
| BUG-020 | Contrato instável | P2 | [ ] | [ ] | [ ] |

**Total: 20 bugs · 60 stories · 7 P0 · 7 P1 · 6 P2**

---

## Ordem de ataque recomendada

```
P0: 001 (select) → 002 (DOM vazio) → 003 (contagem) → 004 (event_id)
     → 005 (sessões) → 006 (browser fallback) → 007 (SIMAX flicker)

P1: 008 (fill compact) → 009 (goto excessivo) → 010 (healer genérico)
     → 011 (métricas) → 012 (asserts) → 013 (bounding box) → 014 (httpx)

P2: 015 (PowerShell) → 016 (logs) → 017 (steps skip) → 018 (artefato)
     → 019 (cascata) → 020 (contrato)
```
