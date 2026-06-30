# TestForge — Visão Geral Executiva

**Versão:** 0.4.2  
**Leia em:** 5 minutos

---

## O que é TestForge?

TestForge é um **gravador de intenção** para testes de aplicações web.

Você clica, preenche e interage com um website. O TestForge:

1. **Grava** cada clique e preenchimento
2. **Entende** a intenção por trás de cada ação
3. **Compila** em script Playwright executável
4. **Cura automaticamente** quando o site muda

Resultado: **Testes resilientes sem manutenção manual**.

---

## Em 3 Exemplos

### Exemplo 1: Simulador Habitacional

```bash
# Você grava:
1. Clica "Novo Cálculo"
2. Preenche CPF: 407.123.456-89
3. Preenche renda mensal: R$ 5.000,00
4. Clica "Calcular"
5. Vê resultado: "Poder de Compra: R$ 250.000"

# TestForge gera:
await page.click("text=Novo Cálculo")
await page.fill("input[name=cpf]", "407.123.456-89")
await page.fill("input[name=renda]", "5000.00")
await page.click("text=Calcular")
await expect(page.get_by_text("Poder de Compra")).to_be_visible()
```

### Exemplo 2: Self-Healing Automático

```
Semana 1: Teste passa ✅
Semana 2: Dev muda CSS do botão
  └─ Teste falha em "await page.click()"
  └─ TestForge tenta 3 estratégias:
     1. Retry (talvez mude de novo) ❌
     2. Busca novo seletor por texto ✅ Encontrou!
     3. Executa com novo seletor
  └─ Teste passa ✅
Semana 3: Dev muda conteúdo do texto
  └─ TestForge sugere novo seletor (L2 Agent)
  └─ Tester valida: "Sim, é o botão correto"
  └─ Teste atualizado automaticamente
```

### Exemplo 3: Dados Complexos

```bash
# Alguns campos não aparecem durante gravação
# (preenchidos por JS, máscara, async)

# TestForge encontra a intenção em 5 fontes:
1. Clique/change event direto ✅
2. Snapshot de campo (antes/depois) ✅
3. Valor da máscara JS (currency) ✅
4. Payload da requisição POST ✅
5. Estado final do formulário ✅

# Resultado: 95% dos campos resolvidos
```

---

## As 4 Fases

| Fase | Nome | O que faz | Entrada | Saída |
|------|------|----------|---------|-------|
| **A** | Recorder | Você grava interações | Navegação manual | raw_events.jsonl |
| **B** | Intent Reconstructor | Entende a intenção | raw_events.jsonl | SemanticTestCase |
| **C** | Compiler | Gera código Playwright | SemanticTestCase | script.py |
| **D** | Executor + Healer | Executa com self-healing | script.py | execution_report.json |

---

## Comece Agora

### 1️⃣ Setup (1 min)

```bash
git clone <repo>
cd testforge
python -m venv venv
source venv/bin/activate  # ou .venv\Scripts\activate no Windows
pip install -r requirements.txt
```

### 2️⃣ Seu Primeiro Teste (3 min)

```bash
# Comece a gravar
testforge record --name meu_primeiro_teste https://site.com

# Clique, preencha, navegue no navegador
# (TestForge captura tudo)

# Quando terminar, feche o navegador
# TestForge compila e mostra: ✅ 12 passos gravados

# Execute o teste
testforge run --recording meu_primeiro_teste
# Resultado: ✅ Todos os 12 passos passaram!
```

### 3️⃣ Veja o Código Gerado

```bash
cat recordings/meu_primeiro_teste/script.py
# Código Playwright legível e executável
```

---

## Principais Características

### ✅ Diagnostic Mode (Sprint 0)

- FrameworkDetector: análise de CDP bundle + window/DOM/custom-elements
- CaptureQualityTracker: value_kind regex, framework_signal, blind_spots
- ReplayCheck: probe de localizadores (imediato ou batch)
- GherkinWriter: geração de `scenario.feature` em português
- Publisher Azure DevOps (G4 + Z1+Z5)
```bash
testforge record --diagnostic-mode <url>
testforge diagnose <url>
```

### ✅ Gravação Inteligente

- Captura cliques, preenchimentos, navegações
- Coleta evidência visual (screenshots, DOM, logs)
- Detecta intenção mesmo em campos com máscara JS
- Suporta SPA (React, Angular, Vue, PrimeFaces)

### ✅ Diagnostic Mode (Novo v0.4.2)

- Modo standalone de coleta de telemetria para equipes de QA
- `FrameworkDetector` — análise de CDP bundle + window/DOM/custom-elements
- `CaptureQualityTracker` — value_kind regex, framework_signal, blind_spots
- `ReplayCheck` — probe de localizadores (imediato ou batch)
- `GherkinWriter` — geração de `scenario.feature` em português
- Publisher para Azure DevOps (G4 + Z1+Z5)

### ✅ Architecture v2 (Phases 1-7)

- **Phase 1:** Playwright tracing + CDP AX-tree capture (paralelo)
- **Phase 2:** v2 LocatorExtractor + Playwright codegen + intent normalization
- **Phase 3:** LocatorResolver + step API + v2 compiler
- **Phase 4:** SQLite intent-keyed catalog + persistent L0
- **Phase 5:** Pipes & Filters pipeline (4 extracted stages)
- **Phase 6:** Zero-dep tracer + static dashboard.html
- **Phase 7:** YAML-driven ComponentResolver

### ✅ Component Handler System (v0.4.1)

- Handlers específicos por framework (Angular Material, PrimeFaces, React MUI)
- `detect_handler()` → delega execução para handler correto
- Normalização automática de componentes (mat-select, autocomplete, dialog, tabs)
- Healing especializado por componente (ex: mat-option não encontrado → scroll + retry)

### ✅ Compilação para Playwright

- Gera Python válido automaticamente
- Suporta assertions robustas (semânticas, não estruturais)
- Injeta dados externos via `--data JSON`
- Uma linha de comando: `testforge compile`

### ✅ Self-Healing Automático

- **L0:** HealingCatalog JSONL (<50ms) + auto-learning de curas bem-sucedidas
- **L1:** FallbackRunner — tenta LocatorCandidates[] ranqueados do MIS
- **L2:** 6 SpecialistAgents determinísticos por família (FAM-01→07)
- **L3:** LLMHealer (Azure GPT-4.1-mini ou MockLLMHealer offline)

### ✅ Métricas de Qualidade

- Integridade de evidência (cobertura de campos)
- Taxa de healing (true vs false cures)
- Execution report com detalhes por step
- Identificação de blind spots

---

## Arquitetura de Healing

```
Script compilado: tenta nativos PW (get_by_role, get_by_label, etc.)
    └─ L0.5: get_by_role + regex fuzzy antes do CSS fallback

Step Falha em Runtime
    ↓
[L0] HealingCatalog (<50ms, zero LLM)
    └─ Match exato por family+symptom no JSONL
    └─ Auto-aprendizado: record_success() grava curas bem-sucedidas
    
[L1] FallbackRunner (2-5s)
    └─ Tenta LocatorCandidates[] do MIS em ordem de score
    └─ compound multi-attr candidates (placeholder+aria-label, etc.)
    
[L2] SpecialistAgents (<100ms, determinístico)
    └─ 6 agentes: Selector, Timing, Input, Context, State, DynamicDOM
    └─ FAM-08→FAM-11 escalam direto para L3
    
[L3] LLMHealer (~500 tokens)
    └─ Azure GPT-4.1-mini (ou MockLLMHealer offline)
    └─ Prompt por família (11 templates)
    └─ Cura bem-sucedida → registra em HealingCatalog

Métricas
    ├─ true_heals: healing resolveu o problema
    ├─ false_heals: achou um seletor errado
    └─ unresolved: não conseguiu curar
```

---

## Roadmap

**Fase A (✅ Concluída)** — Recorder com 11 famílias cobertas

**Fase B (✅ Implementada)** — Intent Reconstructor com 5 estratégias

**Fase C (⏳ Em Progresso)** — Compiler integrado, data file support

**Fase D (⏳ Em Progresso)** — Executor com healing L0-L3 completo

**🎯 Diagnostic Mode (✅ v0.4.2)** — Sprint 0: FrameworkDetector, CaptureQuality, ReplayCheck, GherkinWriter, TelemetryStore

**🎯 Architecture v2 (✅ Phases 1-7)** — Tracing, CDP, v2 locator, resolver, SQLite catalog, pipes & filters, telemetry, dashboard, component resolver

**🎯 ComponentHandler System (✅ v0.4.1)** — Sprints 1-6: Angular Material completo + PrimeFaces/React MUI skeletons

**🎯 Native Playwright Locators + Auto-Healing (✅ v0.4.2)** — Compiler gera get_by_role/label/placeholder; L0.5 fuzzy regex; compound multi-attr candidates; HealCatalog auto-learning; IntentReconstructor merged em RecordingNormalizer

---

## Próximas Ações

1. **Testers:** [Guia Rápido](USER-GUIDE/QUICK-START.md) — Comece a gravar em 5 min
2. **Developers:** [Arquitetura](ARQUITETURA/FASES.md) — Entenda as 4 fases
3. **Developers:** [Architecture v2](ARCHITECTURE-V2.md) — Phases 1-7 migration
4. **Pesquisadores:** [Análise LLM](PESQUISA/ANALISE-LLM.md) — Como o LLM valida

---

## FAQ Rápido

**P: Funciona com qualquer website?**  
R: Sim, qualquer SPA (React, Angular, Vue) ou site clássico. Testado com CAIXA, Simulador Habitacional.

**P: Quanto tempo para aprender?**  
R: 5 minutos para gravar. 15 minutos para entender o código gerado. 1 hora para dominarm healing.

**P: Os testes quebram quando o site muda?**  
R: Às vezes — mas TestForge tenta consertar automaticamente antes de falhar.

**P: Preciso de conhecimento de Playwright?**  
R: Não! TestForge gera o código. Mas saber Playwright ajuda a entender o output.

---

**Veja também:**  
[📖 Documentação Completa](INDEX.md) — Todos os guias e referências

---

**Última atualização:** 2026-06-30  
**Versão:** v0.4.2
