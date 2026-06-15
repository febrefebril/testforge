# TestForge v0.3.1 — Apresentação Sprint Review

> **Formato:** Markdown slides (fallback para Figma)
> **Duração:** 50 min
> **Data:** 2026-06-15

---

# Slide 1: Título

## TestForge v0.3.1
### Sprint Review & Retrospectiva

**Gravador inteligente de testes E2E com self-healing determinístico**

100 commits · 162 testes · 28 módulos · 14 diagramas

---

# Slide 2: O Problema

## Por que TestForge?

> Testes E2E quebram constantemente por fragilidade de seletores em aplicações enterprise.

```
Botão #btnPesquisar → deploy → #btnPesquisar_1781492388297
                                  ↑ ID dinâmico quebrou o teste!
```

- QAs perdem horas "consertando" testes
- CI/CD quebra sem motivo real
- Frameworks enterprise (Angular, PrimeFaces) geram IDs dinâmicos

---

# Slide 3: A Solução

## Gravar intenção, não seletores

```
QA grava fluxo → MIS captura intenção → Script com fallback → Self-healing
```

| Camada | O que faz | Custo |
|--------|----------|-------|
| L0 | Catálogo de receitas | <50ms |
| L1 | Candidatos alternativos | 2-5s |
| L2 | Agentes especialistas | Determinístico |
| L3 | LLM (Azure GPT-4.1-mini) | Off critical path |

**MockLLMHealer funciona offline — sem API key!**

---

# Slide 4: Demo 1 — Gravação

## `testforge record`

```bash
testforge record http://localhost:8765 --name "demo-review"
```

1. Abre fake-bank no navegador
2. Preenche CPF: `12345678900`
3. Clica em Pesquisar
4. **Shift+S** → finaliza

**Output:**
```
[TestForge] Gravando: demo-review
[TestForge] ✓ 5 passos gravados
[TestForge] Sessao salva: recordings/demo-review/
```

---

# Slide 5: Demo 2 — Compilação Data-Driven

## `testforge compile --data`

```bash
testforge compile demo-review --data
```

**Gera:**
- `semantic_tests/ST-demo-review/test_st_demo_review.py` ← Script Playwright
- `semantic_tests/ST-demo-review/test_data.json` ← Massa externa

```json
{"fields": {"cpf": "12345678900"}}
```

Script usa `_data.get("cpf", "12345678900")` — valores do JSON!

---

# Slide 6: Demo 3 — Execução

## `testforge run`

```bash
testforge run semantic_tests/ST-demo-review/test_st_demo_review.py
```

```
  ✓ Step 1: navigation
  ✓ Step 2: fill 12345678900
  ✓ Step 3: click
  ✓ Step 4: assert "CPF consultado"

[TestForge] Metricas:
Total runs: 1  |  Healings: 0
```

**0 falhas — script funciona perfeitamente!**

---

# Slide 7: Demo 4 — Healing com Mutação

## Quando o seletor quebra...

```bash
testforge demo-heal
```

```
Fase 3: Seletor original #btnPesquisar: NAO EXISTE (quebrado!)
Fase 4: ✓ Clique com candidato alternativo funcionou!
Fase 5: ✓ visual_dom: passed  |  ✓ business_state: passed

✅ HEALING FUNCIONOU!
```

**L1 — FallbackRunner resolve sem LLM:** testa `text=Pesquisar`, `role=button[name='Pesquisar']`

---

# Slide 8: Demo 5 — L3 LLM Healing

## Com Azure GPT-4.1-mini

```bash
export AZURE_OPENAI_ENDPOINT="https://..."
testforge run script.py --headless
```

```
  ✗ Step 3: click FAILED
    Falha: SEL-004 [FAM-01]
    Healer: LLM real (Azure/OpenAI)
    Curador: PASSED_STEP [L3]
    Proposal: has_text_fallback → button:has-text('Pesquisar')
    Confidence: 0.90
```

**LLM analisou o DOM e propôs seletor correto!**

---

# Slide 9: Arquitetura — Pipeline L0→L3

```
Step falha
  → FailureClassifier.classify() → FAM-01 / SEL-004
  → L0: HealingCatalog.match() → receita exata?
  → L2: route_to_agent(FAM-01) → SelectorAgent
  → L3: LLMHealer.heal(evidence) → Azure GPT-4.1-mini
  → SmartStepRunner.execute(proposal)
  → PASSED_STEP → _register_learned() → catálogo
```

---

# Slide 10: SmartStepRunner — 10 Estratégias

| Estratégia | O que faz |
|-----------|----------|
| `visibility_wait` | Espera elemento visível antes de clicar |
| `press_sequentially` | Digita caractere por caractere (máscara JS) |
| `overlay_dismiss` | Fecha overlays/modais (Escape + click) |
| `dialog_handler` | Aceita alerts/confirms nativos |
| `iframe_switch` | Troca contexto para iframe |
| `synthetic_click` | Click via JavaScript |
| `label_click` | Click no label associado |
| `has_text_fallback` | Localiza por texto em vez de ID |
| `semantic_locator_conversion` | Converte para seletor semântico |
| `xpath_fallback` | XPath como último recurso |

**10/10 implementadas — todos os bugs de healing resolvidos!**

---

# Slide 11: Páginas de Curadoria

## 12 páginas — 1 por família

```
tests/test_pages/curation/
├── fam-selector/index.html      # SEL-004: ID dinâmico
├── fam-timing/index.html        # TIM-005: Conteúdo com delay
├── fam-context/index.html       # CTX-001: Iframe
├── fam-state/index.html         # STA-002: Overlay
├── fam-dynamic-dom/index.html   # DOM-001: Stale element
├── fam-input/index.html         # INP-007: Máscara CPF
├── fam-capture/index.html       # FILE-001: Upload
├── fam-assertion/index.html     # AST-004: Assert texto
├── fam-recorder/index.html      # REC-002: Captura overlay
├── fam-execution/index.html     # OBS-003: Erro rede
├── fam-browser/index.html       # LIM-001: CAPTCHA
```

**39 testes parametrizados — 38/38 passando!**

---

# Slide 12: Data-Driven Testing

## Massa externa em JSON

```
Gravação → DataExtractor → test_data.json → Script lê do JSON
```

```json
{"fields": {"cpf": "12345678900"}}
```

**Alterar CPF sem recompilar:**
```bash
vim test_data.json  # muda CPF para 99988877766
testforge run script.py  # usa novo valor!
```

---

# Slide 13: Métricas da Sprint

| Métrica | Início | Fim |
|---------|--------|-----|
| Commits | 65 | 100 (+35) |
| Testes | 93 | 162 (+69) |
| Módulos | 16 | 28 (+12) |
| Diagramas | 7 | 14 (+7) |
| Bugs | 0 docs | 5 corrigidos |
| Estratégias | 1 (L1) | 10 (L0-L3) |
| Cobertura famílias | 1/11 | 11/11 |
| LLM validado | ❌ | ✅ Azure |

---

# Slide 14: Retrospectiva 🟢🟡🔴

### 🟢 Funcionou bem
- Pipeline BMAD→GSD→Git (40 commits, 0 perda)
- Port do projeto anterior (taxonomia, curador, agentes)
- SmartStepRunner (4 bugs resolvidos de uma vez)
- Testes de curadoria (100% cobertura famílias críticas)

### 🟡 Pode melhorar
- cmd_run inline mais frágil que pytest subprocess
- LLM prompt inconsistente (resolveu com parser flexível)
- Recording quality (elementos sem atributos)

### 🔴 Ações
- Pipeline CI (GitHub Actions)
- Flag --llm / --no-llm
- Melhorar recorder (CSS path, parent hierarchy)

---

# Slide 15: Próxima Sprint — EP-12

## v0.4.0: Pipeline CI + Qualidade

| Story | O quê |
|-------|-------|
| US-12.01 | GitHub Actions CI (testes em push/PR) |
| US-12.02 | Flag --llm / --no-llm |
| US-12.03 | Melhorar Recorder (CSS path, parent chain) |
| US-12.04 | `testforge report` (relatório Markdown) |
| US-12.05 | 180+ testes (data_extractor, SmartStepRunner, cmd_run) |

---

# Slide 16: Q&A

## Perguntas?

```
testforge --help
docs/SPRINT-REVIEW.md
docs/BUGS.md
docs/PLANO-DE-TESTE.md
docs/TUTORIAL-LLM-HEALING.md
docs/diagramas/png/  (14 diagramas)
```

**Repositório:** `testforge-v1`
**Branch:** `main`
**Commits:** 100
**Testes:** 162 (100%)
