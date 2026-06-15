# TestForge v0.3.1 — Sprint Review & Retrospectiva

**Data:** 2026-06-15
**Sprint:** 8-11 (v0.2.0 → v0.3.1)
**Duração:** 1 dia

---

## 🎯 Agenda

1. **Review** (20 min) — Demo das funcionalidades entregues
2. **Métricas** (5 min) — Números da sprint
3. **Retrospectiva** (15 min) — O que funcionou, o que melhorar
4. **Próxima Sprint** (10 min) — MVP EP-12

---

# PARTE 1: SPRINT REVIEW

## 1.1 Visão Geral do TestForge

> TestForge grava fluxos de usuário em páginas web e gera scripts Playwright que se auto-consertam quando seletores quebram.

```
QA grava fluxo → MIS normaliza → Compiler gera script → Runner executa
                                              ↓ (se falhar)
                                   Healing L0→L1→L2→L3 cura
```

---

## 1.2 Demo: Gravação + Compilação + Execução

### Passo 1: Gravar um fluxo
```bash
testforge record http://localhost:8765 --name "demo-review"
```
**O que mostrar:**
- [ ] Navegador abre no fake-bank
- [ ] Preencher CPF `12345678900`
- [ ] Clicar em Pesquisar
- [ ] Shift+S para parar
- [ ] Console mostra `✓ N passos gravados`

### Passo 2: Compilar com massa de dados
```bash
testforge compile demo-review --data
```
**O que mostrar:**
- [ ] `test_data.json` gerado com valores extraídos
- [ ] Alerta de campo sensível (CPF)
- [ ] Script gerado com `_data.get("cpf", "12345678900")`

### Passo 3: Executar
```bash
testforge run semantic_tests/ST-demo-review/test_st_demo_review.py
```
**O que mostrar:**
- [ ] 5 steps executados sem falhas
- [ ] `✓ Step 1: navigation`, `✓ Step 2: fill`, `✓ Step 3: click`
- [ ] Métricas: 0 healings

---

## 1.3 Demo: Healing com Mutação

### Testar L1 — FallbackRunner com candidatos
```bash
testforge demo-heal
```
**O que mostrar:**
- [ ] Fase 1: Gravação do fluxo normal
- [ ] Fase 3: `Seletor original #btnPesquisar: NAO EXISTE (quebrado!)`
- [ ] Fase 4: `✓ Clique com candidato alternativo funcionou!`
- [ ] Fase 5: `✓ visual_dom: passed`, `✓ business_state: passed`
- [ ] **✅ HEALING FUNCIONOU!**

### Testar L3 — MockLLMHealer
```bash
# Compilar para mutation
testforge compile demo-review --data
# Editar BASE_URL no script para ?mutation=change_id
testforge run semantic_tests/ST-demo-review/test_st_demo_review.py
```
**O que mostrar:**
- [ ] Step 3 falha (botão com ID quebrado)
- [ ] Classifier: `FAM-01 / SEL-004`
- [ ] Curador: `PASSED_STEP [L3]`
- [ ] Proposal: `has_text_fallback → text=Pesquisar`
- [ ] Step curado com sucesso

---

## 1.4 Demo: Páginas de Curadoria (12 famílias)

### Página FAM-01: Selector Healing
```bash
python -m http.server 8770 -d tests/test_pages &
open http://localhost:8770/curation/fam-selector/index.html
```
**O que mostrar:**
- [ ] Botão "Clique Aqui" com ID estável
- [ ] Explicar: ID pode mudar, mas healing encontra por texto

### Executar testes automatizados
```bash
python -m pytest tests/test_pages/test_curation_pipeline.py -v
```
**O que mostrar:**
- [ ] 38 testes passando (classificação + agentes + evidência + healing)
- [ ] FAM-01 a FAM-06 todos curados pelo SmartStepRunner

---

## 1.5 Demo: Data-Driven Testing

### Alterar massa sem recompilar
```bash
# Editar test_data.json: CPF para 99988877766
vim semantic_tests/ST-demo-review/test_data.json
# Reexecutar
testforge run semantic_tests/ST-demo-review/test_st_demo_review.py
```
**O que mostrar:**
- [ ] Script usa novo CPF sem recompilar
- [ ] Resultado mostra CPF alterado

---

## 1.6 Demo: SmartStepRunner — 10 Estratégias

### Mostrar código
```python
# src/testforge/runner/fallback_runner.py
class SmartStepRunner:
    def execute(self, step_data, strategy):
        if strategy == "visibility_wait":
            self._page.wait_for_selector(sel, state="visible")
        if strategy == "overlay_dismiss":
            self._dismiss_overlays()  # Escape + click overlay
        if strategy == "press_sequentially":
            self._page.press_sequentially(sel, value)
        if strategy == "synthetic_click":
            self._page.evaluate("document.querySelector('...').click()")
        # ... 6 more strategies
```

**O que mostrar:**
- [ ] 10/10 estratégias implementadas
- [ ] Overlay dismiss: pressiona Escape, tenta fechar modais
- [ ] Press sequentially: para campos com máscara JS
- [ ] Visibility wait: espera elemento aparecer antes de clicar

---

# PARTE 2: MÉTRICAS

| Métrica | v0.1.0 | v0.3.1 |
|---------|--------|--------|
| Commits | 31 | 100 |
| Testes | 93 | 162 |
| Módulos | 9 | 28 |
| Diagramas | 4 | 14 |
| Bugs corrigidos | — | 5 |
| Estratégias healing | 1 (L1) | 10 (L0-L3) |
| Famílias cobertas | 1/11 | 11/11 |
| Cobertura testes | — | 100% |
| LLM validado | — | ✅ Azure GPT-4.1-mini |

---

# PARTE 3: RETROSPECTIVA

## 🟢 O que funcionou bem

1. **Pipeline BMAD → GSD → Git → Caveman**
   - 40 commits em 1 dia, sem perder código
   - Planejamento documentado, execução rastreável

2. **Port do projeto anterior**
   - Código do `projeto-anterior` foi referência sólida
   - Taxonomia, curador, agentes — portados e melhorados

3. **SmartStepRunner**
   - Abstração correta: 10 estratégias em 1 classe
   - Resolveu 4 bugs de uma vez (overlay, mask, timing, stale)

4. **Testes de curadoria**
   - 12 páginas focadas, 1 por família
   - 39 testes parametrizados
   - Cobertura subiu de 0% para 100% nas famílias críticas

5. **Data-driven testing**
   - Extração automática de massa do recording
   - Reexecução com dados diferentes sem recompilar

## 🟡 O que pode melhorar

1. **cmd_run vs subprocess**
   - Execução inline é mais frágil que pytest subprocess
   - Timeouts precisam de ajuste fino por site

2. **LLM prompt format**
   - LLM ainda retorna formatos inconsistentes
   - `_parse_response` flexível resolveu, mas prompt poderia ser mais restritivo

3. **Recording quality**
   - Elementos sem atributos (divs, icons) geram seletores vazios
   - Melhorias no recorder ajudaram (aria-*, data-*, parent_text)

4. **Testes de integração lentos**
   - Servidor HTTP + Playwright = 30s+ por suite
   - Poderia usar `file://` para páginas estáticas

## 🔴 Ações para próxima sprint

1. **Pipeline CI** — GitHub Actions para rodar testes automaticamente
2. **Flag --llm / --no-llm** — Controle explícito do LLM pelo usuário
3. **Melhorar recorder** — Capturar CSS path, nth-child, parent hierarchy
4. **Dashboard de métricas** — Visualizar false_heal_rate, precision ao longo do tempo

---

# PARTE 4: PRÓXIMA SPRINT (EP-12)

## EP-12: Pipeline CI + Qualidade (v0.4.0)

### US-12.01: GitHub Actions CI
- [ ] Workflow `.github/workflows/test.yml`
- [ ] Rodar `pytest tests/` em push/PR
- [ ] Matrix: Python 3.10, 3.11, 3.12, 3.13
- [ ] Upload de artefatos (screenshots, logs)

### US-12.02: Flag --llm / --no-llm
- [ ] `testforge run script.py --llm` → força LLM real
- [ ] `testforge run script.py --no-llm` → força MockLLMHealer
- [ ] Default: auto-detect (Azure key → real, sem key → mock)

### US-12.03: Melhorar Recorder
- [ ] Capturar CSS path do elemento
- [ ] Capturar parent hierarchy (até 3 níveis)
- [ ] Capturar nth-child para desambiguação
- [ ] Armazenar no TargetInfo: css_path, parent_chain

### US-12.04: Relatório de Execução
- [ ] `testforge report` — gera relatório Markdown
- [ ] Métricas: total runs, healings, false_heal_rate, precision
- [ ] Breakdown por família de falha
- [ ] Timeline de execuções

### US-12.05: Melhorar cobertura de testes
- [ ] Testes para data_extractor
- [ ] Testes para SmartStepRunner (cada estratégia)
- [ ] Testes para cmd_run (edge cases)
- [ ] Meta: 180+ testes

---

## 🎬 Roteiro da Apresentação

| Minuto | O quê | Quem | Demo |
|--------|-------|------|------|
| 0-5 | Contexto: o que é TestForge | — | Slides |
| 5-10 | Demo: gravar → compilar → executar | QA | Fake-bank |
| 10-15 | Demo: healing com mutação | QA | `demo-heal` |
| 15-20 | Demo: data-driven (massa externa) | QA | `--data` |
| 20-22 | Métricas da sprint | — | Números |
| 22-30 | Arquitetura: L0→L3, SmartStepRunner | Dev | Diagramas |
| 30-35 | Páginas de curadoria (12 famílias) | Dev | Browser |
| 35-38 | Retrospectiva | Todos | Discussão |
| 38-45 | Próxima sprint (EP-12) | PM | Planejamento |
| 45-50 | Q&A | Todos | — |

---

## 📁 Arquivos de Apoio

- Diagramas: `docs/diagramas/png/` (14 arquivos)
- Plano de teste: `docs/PLANO-DE-TESTE.md` (27 casos)
- Bugs: `docs/BUGS.md` (5 bugs, todos corrigidos)
- Tutorial: `docs/TUTORIAL-LLM-HEALING.md`
- Prompt pack: `.planning/prompt-pack-v0.3.0.md`
- Estado: `.planning/STATE.md`
