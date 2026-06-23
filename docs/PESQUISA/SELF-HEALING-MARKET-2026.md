# Pesquisa: Self-Healing em Testes Automatizados — Mercado, Abordagens e Comparação com TestForge

**Versão:** 1.0  
**Data:** 2026-06-23  
**Autor:** Pesquisa automatizada via web + análise comparativa

---

## Sumário Executivo

O mercado de self-healing em automação de testes cresceu e amadureceu significativamente entre 2024-2026. As ferramentas comerciais líderes (Testim, Mabl, Functionize) curam entre **60-85%** das falhas de seletor automaticamente. No entanto, 41% dos times abandonam essas ferramentas no primeiro ano — principalmente por **custo elevado** ($4k-$15k/mês), **vendor lock-in** e **falsos positivos** não auditáveis.

O TestForge ocupa um nicho específico: **open-source, determinístico, recorder-first, com fallback LLM opcional**. Nossa abordagem híbrida (L0-L3) é única no mercado — ninguém mais combina healing catalog, fallback runner, agentes especialistas E LLM em uma única ferramenta open-source.

Este documento mapeia o ecossistema, compara abordagens e propõe direções para tornar o TestForge mais competitivo.

---

## 1. Taxonomia das Abordagens de Self-Healing

### 1.1 Locator Fallback (Abordagem Clássica)

Guarda N alternativas de seletor. Quando o primário falha, tenta os demais em ordem.

| Ferramenta | Implementação |
|-----------|--------------|
| **Healenium** | LCS algorithm — compara DOM atual vs. snapshot, gera candidatos com score, usa o de maior confiança |
| **Katalon** | Smart XPath — fallback chain: ID → CSS → XPath → attributes |
| **Testim** | Smart Locators — captura 50+ atributos por elemento, ordena por confiabilidade ML |

**Prós:** Determinístico, auditável, sem custo de LLM.  
**Contras:** Falha em redesigns completos. Não entende intenção.

### 1.2 Multi-Attribute Fingerprinting (Abordagem ML Leve)

Captura fingerprint do elemento (texto, posição, vizinhos, atributos, role) e usa ML para ponderar.

| Ferramenta | Implementação |
|-----------|--------------|
| **Mabl** | ML auto-heal + 2-stage: fingerprint → GenAI fallback |
| **Testim** | ML-trained reliability scores por aplicação |

**Prós:** Cobre 70-85% dos casos. Mais robusta que fallback simples.  
**Contras:** Requer treino por aplicação. Decisões opacas (black box).

### 1.3 Intent-Based (Abordagem Semântica)

Armazena descrição semântica do elemento (o que ele FAZ, não onde está) e resolve em runtime.

| Ferramenta | Implementação |
|-----------|--------------|
| **Functionize** | NLP + computer vision — entende intenção do usuário |
| **TestRigor** | Plain English locators — elemento descrito por texto |
| **Shiplight AI** | Intent-based — YAML de intenção, runtime mapping |
| **CANVAS (acadêmico)** | Sentence transformers embedding do intent → nearest neighbor match |
| **WebTestPilot (acadêmico)** | Neurosymbolic — simboliza elementos GUI para oráculos |

**Prós:** Mais resiliente a redesigns. Entende o que o teste quer fazer.  
**Contras:** ML pesado em runtime. Falsos positivos por "achar" elemento errado.

### 1.4 Live-Snapshot (Abordagem Nova 2026)

Não armazena seletor nem intent. Toda execução lê a árvore de acessibilidade fresca e resolve por nome/role.

| Ferramenta | Implementação |
|-----------|--------------|
| **Assrt** | LLM lê accessibility tree via Playwright MCP, decide elemento por accessible name |
| **Promptomate** | `heal` re-captura ARIA snapshot, regenera spec |

**Prós:** Zero estado armazenado. Zero lock-in. Custo ~$0.01-0.05 por cenário.  
**Contras:** Dependente de LLM em runtime (latência). Não adequado para CI de alta frequência.

### 1.5 Agentic / LLM-First (Abordagem 2025-2026)

Agente AI navega, grava e repara testes. Geração e healing integrados.

| Ferramenta | Implementação |
|-----------|--------------|
| **TestSprite** | AI agent replay — agente re-executa fluxo e re-identifica elementos |
| **Selora** | Rule-based + LLM repair (2-attempt max) com diff audit trail |
| **Playwright Healer Agent (Microsoft)** | Agente Playwright dedicado que repara seletores quebrados |

**Prós:** Mais adaptativo. Entende contexto maior (não só seletor).  
**Contras:** Imprevisível. Custo de LLM por execução. Difícil auditar.

---

## 2. Comparação de Mercado — Matriz Completa

### 2.1 Ferramentas Comerciais (2026)

| Característica | Testim (Tricentis) | Mabl | Functionize | Applitools | Katalon |
|---------------|-------------------|------|-------------|------------|---------|
| **Healing approach** | ML Smart Locators | ML Auto-Heal 2-stage | NLP + Vision + ML | Visual AI | Fallback chain |
| **Healing accuracy** | ~80% | ~85% | ~78% | ~90% visual | ~65% |
| **Record & Play** | ✅ | ✅ | ✅ NLP-based | ❌ add-on | ✅ |
| **Playwright support** | ✅ | ✅ | ✅ | ✅ | ✅ |
| **Open Source** | ❌ | ❌ | ❌ | ❌ | ❌ (freemium) |
| **Custo médio/mês** | $5k-$15k | $5k-$15k | $10k-$20k | $2k-$10k | $2k-$6k |
| **Vendor lock-in** | Alto (proprietário) | Alto | Alto | Médio | Médio |
| **Audit trail healing** | Parcial | ✅ | ✅ | ✅ | Parcial |
| **CI/CD nativo** | ✅ | ✅ | ✅ | ✅ | ✅ |
| **Empresas que usam** | Mercedes-Benz | LendingClub, JetBlue | Large enterprise | Adobe, Netflix | SAP, Salesforce |

### 2.2 Ferramentas Open-Source (2026)

| Característica | Healenium | playwright-self-healing | selfmend | Selora | CANVAS |
|---------------|-----------|------------------------|----------|--------|--------|
| **Framework** | Selenium | Playwright TS | Playwright TS | Playwright TS | Playwright/Python |
| **Healing approach** | LCS algorithm | 6-dimensional scoring | Signal-matching | Rule + LLM | Semantic embedding |
| **LLM dependency** | ❌ | ❌ | ❌ | ✅ (optional) | ✅ (sentence-transformers) |
| **Setup complexity** | Alta (Docker + PG) | Média | Baixa (1 import) | Alta | Média |
| **Stars** | ~1.2k | ~500 | ~200 | ~6 | Novo (PyPI) |
| **Licença** | Apache 2.0 | MIT | MIT | AGPL v3 | MIT |
| **False positive rate** | Baixa | Baixa | Muito baixa | Média | Média (prototype) |
| **Produção ready** | ✅ Sim | ✅ Sim | ✅ Sim | ⚠️ Beta | ❌ Prototype |

### 2.3 TestForge na Matriz

| Característica | TestForge v0.4.1 |
|---------------|-----------------|
| **Framework** | Playwright (Python) |
| **Healing approaches** | Híbrido: L0 Catalog + L1 Fallback + L2 Agents + L3 LLM |
| **ComponentHandler** | ✅ Angular Material, PrimeFaces, React MUI |
| **Record & Play** | ✅ Recorder sensorial próprio (não codegen) |
| **LLM dependency** | ❌ Opcional (MockLLMHealer default) |
| **Open Source** | ✅ MIT |
| **Custo** | $0 (infra própria) |
| **Vendor lock-in** | Zero (Playwright code output) |
| **Audit trail healing** | ✅ healing_report.md |
| **CI/CD** | ✅ CLI commands |
| **Produção ready** | ✅ Sim (162+ gravações reais) |

---

## 3. Análise Comparativa Detalhada

### 3.1 O Que o Mercado Faz Melhor Que Nós

| Capacidade | Líder de Mercado | Como Faz | O Que Falta no TestForge |
|-----------|-----------------|---------|------------------------|
| **Multi-attribute fingerprinting** | Testim (50+ attributes) | ML weighted scoring de atributos | Nosso L0/L1 usa match exato, não fuzzy score |
| **Confidence scoring** | Mabl, Healenium | Score 0.0-1.0 por candidato, gate configurável | Nosso L2 agents retornam confiança binária ou não retornam |
| **Visual healing** | Applitools, Mabl | Visual AI + screenshot diff | Não temos healing visual |
| **NLP test authoring** | Functionize, TestRigor | Plain English → script | Só recorder manual |
| **Dashboard + governance** | Mabl, Testim | Healing review queue, RBAC, audit logs | CLI-only, sem dashboard |
| **Learning over time** | Healenium, Testim | Feed de heal history → modelo melhora | Nosso catalog é estático (pre-populated) |
| **Cross-browser healing** | Mabl, Functionize | Executa healing em múltiplos browsers | Single browser (Chromium) |
| **Semantic intent embedding** | CANVAS (acadêmico) | Sentence transformers → nearest neighbor match | Nosso intent é textual (accessible_name, role) não vetorizado |

### 3.2 O Que Fazemos Melhor Que o Mercado

| Capacidade | TestForge | Mercado |
|-----------|-----------|---------|
| **Custo** | $0 (open source + LLM opcional) | $4k-$20k/mês |
| **Determinismo L0-L2** | Healing sem LLM em 3 camadas (catalog, fallback, agents) | Maioria depende de ML/LLM como motor primário |
| **ComponentHandler system** | Handlers específicos por framework (mat-select, autocomplete, dialog) | Nenhuma ferramenta open-source tem isso |
| **Recorder sensorial próprio** | Captura intenção + evidência + network + DOM snapshots | Codegen (Playwright, Selenium IDE) ou record-only |
| **Sem vendor lock-in** | Output é Playwright Python padrão | Testes em formato proprietário (Testim, Mabl) |
| **Transparência de healing** | healing_report.md completo com reasoning | Black box (Testim) ou parcial |
| **LLM como opção, não obrigação** | MockLLMHealer default, Azure/OpenAI opcional | LLM como core do produto (Functionize, TestRigor) |
| **Framework-agnostic healing** | L2 agents tratam 11 famílias de falha (locator, timing, context, state...) | Healing focado em seletor (maioria) |

### 3.3 Onde Nossas Abordagens Diferem

| Dimensão | Abordagem Comercial Típica | Abordagem TestForge |
|----------|---------------------------|-------------------|
| **Gravação** | Codegen (Playwright, Selenium) ou low-code | Recorder sensorial próprio com captura de evidência |
| **Armazenamento de intenção** | Server-side (vendor cloud) | Local filesystem (JSONL + YAML) |
| **Healing primário** | ML model treinado por aplicação | Pipeline determinístico L0→L1→L2 |
| **Healing fallback** | GenAI (LLM + vision) | LLM opcional (L3) |
| **Healing de framework** | Genérico (tenta qualquer seletor) | Específico (ComponentHandler sabe como cada framework funciona) |
| **Output do teste** | Proprietário ou parcial | Playwright Python padrão |
| **Métrica de qualidade** | Dashboard proprietário | healing_report.md + CLI |

---

## 4. Lacunas e Oportunidades

### 4.1 Lacunas Críticas no TestForge (O Que IMPEDE Adoção)

| Lacuna | Impacto | Prioridade |
|--------|---------|-----------|
| **Falta confidence scoring nos healings** | Usuário não sabe se pode confiar no healing | 🔴 Alta |
| **Sem multi-attribute fingerprinting** | Healing L1 muito simples (só tenta candidatos do recording) | 🔴 Alta |
| **Sem healing visual** | Não detecta mudanças CSS/layout sem mudança de DOM | 🔴 Alta |
| **Sem dashboard/review de healing** | Usuário precisa ler relatório markdown | 🟡 Média |
| **Catalog de healing estático** | Não aprende com healings bem-sucedidos automaticamente | 🟡 Média |
| **Sem suporte a mobile** | Apenas web | 🟡 Média |
| **Documentação de comparação inexistente** | Usuário não sabe por que escolher TestForge vs. Mabl | 🟢 Baixa |

### 4.2 Oportunidades Únicas (O Que Podemos FAZER que Ninguém Faz)

| Oportunidade | Vantagem Competitiva | Esforço |
|-------------|---------------------|---------|
| **Healing determinístico + LLM opcional** = melhor relação confiança/custo | Único open-source com L0-L3 completo | Já temos |
| **ComponentHandler por framework** → healing específico que entende Angular/PrimeFaces | Nenhuma ferramenta open-source faz isso | Parcial (sprints 1-6) |
| **Recorder sensorial próprio** → captura intenção real (não só seletor) | Diferencial contra codegen do Playwright | Já temos |
| **Tudo local, sem vendor** → compliance SOC2/ISO por padrão | Diferencial para empresas reguladas | Já temos |
| **Custom catalog aprendido** → healing melhora com uso | Diferencial contra Healenium (catálogo genérico) | Não temos |
| **Modo "explain heal"** → LLM explica por que escolheu cada seletor | Transparência > black box (vantagem contra Testim) | Parcial (healing_report.md) |

---

## 5. Recomendações Estratégicas

### 5.1 Curto Prazo (v0.5.0 — v0.6.0) — Fechar Lacunas

#### 🔴 Implementar Confidence Scoring
```python
# Atual: binário (achou / não achou)
class HealingProposal:
    passed: bool

# Novo: score + threshold
class HealingProposal:
    confidence: float  # 0.0 - 1.0
    strategy_used: str
    selector_used: str
    threshold: float = 0.7  # configurável
```

**Por que:** Ferramentas como Healenium e selfmend já fazem scoring. Sem score, usuário não sabe se o healing é confiável.

#### 🔴 Healing Visual (L4: Visual Diff)

Adicionar camada de healing visual entre L2 e L3:
- Capturar screenshot do elemento na gravação
- Em falha, comparar via template matching ou SSIM
- Se match visual > 0.8, usar mesmo seletor com scroll/visibility wait

**Por que:** Applitools e Mabl consideram visual o diferencial #1 em 2026.

#### 🟡 Catalog Auto-Aprendido
```python
# Atual: catalog populado manualmente
HealingCatalog(jsonl_path)  # recipes estáticas

# Novo: catalog que aprende
HealingCatalog(jsonl_path, learn_from=healing_history)
```
- Quando L2 ou L3 curam com sucesso, registrar recipe no catalog
- Próxima vez que erro similar ocorrer, L0 resolve diretamente (<50ms)

**Por que:** Healenium e Katalon já fazem isso. É o que reduz healing de 500ms para 50ms.

### 5.2 Médio Prazo (v0.7.0 — v0.8.0) — Diferenciação

#### 🟢 Multi-Attribute Fingerprinting no L1

Em vez de tentar candidatos em ordem fixa:
```python
class L1FallbackRunner:
    def score_candidate(self, candidate, live_element):
        score = 0.0
        if candidate.role == live_element.role: score += 0.3
        if candidate.accessible_name == live_element.name: score += 0.25
        if candidate.tag == live_element.tag: score += 0.15
        if levenshtein(candidate.selector, live_element.selector) < 0.3: score += 0.1
        # ...
        return score
```

#### 🟢 Dashboard Web de Healing

CLI é bom para devs, mas testers querem ver healing em dashboard:
- Histórico de healings por gravação
- True heal vs false heal rate
- "Explain this heal" com LLM opcional
- Aprovar/rejeitar healing com 1 clique

#### 🟢 Suporte a Multi-Browser

Healing específico por browser (ex: Firefox lida com shadow DOM diferente).

### 5.3 Longo Prazo (v0.9.0+) — Visão

#### Intent Embedding (como CANVAS)

Em vez de armazenar seletor textual, armazenar embedding semântico do elemento:
```python
# Atual: guardamos string do seletor
LocatorCandidates(selectors=["#btn-submit", "button.primary"])

# Futuro: guardamos intenção vetorizada
SemanticIntent(
    role="button",
    accessible_name="Submit Order",
    context="checkout page, after credit card form",
    embedding=[0.23, -0.45, 0.78, ...]  # 384-dim sentence-transformers
)
```

**Por que:** Único jeito de sobreviver a redesigns completos (ex: Angular → React).

#### Agente Autônomo de Teste

Integrar TestForge com Playwright MCP para permitir:
- "Teste o fluxo de login com CPF inválido"
- Agente navega, grava, executa, repara

#### Playwright MCP Server Nativo

Expor TestForge como MCP server para agentes AI (Claude, Cursor, etc):
- `testforge_record` — grava fluxo
- `testforge_heal` — repara seletor quebrado
- `testforge_audit` — analise de suite

---

## 6. Referências

### Ferramentas Comerciais
- [Mabl Adaptive Auto-Healing](https://www.mabl.com/auto-healing-tests)
- [Testim (Tricentis)](https://www.tricentis.com/products/testim)
- [Functionize](https://www.functionize.com)
- [Applitools](https://applitools.com)
- [Katalon Studio](https://katalon.com)
- [testRigor](https://testrigor.com)
- [Shiplight AI](https://shiplight.ai)
- [TestSprite](https://testsprite.com)

### Open-Source
- [Healenium](https://healenium.io)
- [playwright-self-healing](https://github.com/jasonfredriksson/playwright-self-healing)
- [selfmend](https://github.com/BilalEjaz/selfmend)
- [Selora](https://github.com/sidrat2612/selora-AI-QA)
- [CANVAS](https://github.com/mandavillivijay/CANVAS)
- [Promptomate](https://github.com/guttaashok1/promptomate)
- [Quorvex AI](https://github.com/NihadMemmedli/quorvex_ai)
- [Playwright Self-Healing Agent](https://github.com/Karthick-1501/playwright-agent)

### Acadêmico
- CANVAS: Semantic intent-based self-healing (PyPI 2026)
- WebTestPilot: Neurosymbolic E2E testing (arXiv 2602.11724, 2026)
- Zero-cost self-healing via accessibility tree (arXiv 2603.20358, 2026)
- Semantic intelligence in test automation (Zenodo 2026)
- ML approaches for auto-repairing UI test steps (IJECS 2026)

### Pesquisas de Mercado
- QA Skills: Self-Healing Tools Comparison 2026
- Shiplight AI: Best Self-Healing Tools Ranked 2026
- ScrollTest: 68% Self-Healing Fail in Production
- Assrt: The Third Approach Nobody Writes About
- Qate AI: Self-Healing Tests — What Works, What Doesn't
- Testomat: Self-Healing Test Automation Guide 2026

---

## 7. Conclusão

**TestForge está em posição única no mercado:** é a única ferramenta open-source que combina recorder sensorial próprio + pipeline healing determinístico L0-L3 + ComponentHandler system + LLM opcional — tudo em um pacote zero-custo.

**Nossos diferenciais reais:**
1. ComponentHandler system (ninguém mais tem healing específico por framework UI)
2. Pipeline L0-L3 completo em open-source (Healenium só faz fallback simples)
3. Recorder sensorial próprio (não codegen — captura evidência, network, intenção)
4. Zero vendor lock-in (output é Playwright padrão)

**O que precisamos fazer para sermos mais acertivos:**

1. **Confidence scoring** — sem score, usuário não confia no healing (maior queixa sobre TestForge)
2. **Catalog auto-aprendido** — healing precisa melhorar com o uso (Healenium já faz)
3. **Visual healing** — sem isso, perdemos para Applitools e Mabl em cenários de CSS-only changes
4. **Dashboard web** — CLI não é suficiente para adoção enterprise
5. **Multi-attribute fingerprinting** — L1 precisa ser mais inteligente que "tenta a lista em ordem"

**O risco:** Se não evoluirmos nessas direções, ferramentas como selfmend (MIT, zero-LLM, confidence scoring) vão nos superar em simplicidade, e ferramentas como Selora (AGPL, LLM repair) vão nos superar em inteligência.

**A janela de oportunidade:** O mercado de 2026 está migrando de "self-healing como feature" para "self-healing como padrão". Ferramentas que não se adaptarem vão ser substituídas por Playwright puro + selfmend ou similares. TestForge precisa consolidar **healing determinístico + ComponentHandler + dashboard** como seu nicho antes que o mercado escolha outros.
