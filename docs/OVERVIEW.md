# TestForge — Visão Geral Executiva

**Versão:** 0.4.0  
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

### ✅ Gravação Inteligente

- Captura cliques, preenchimentos, navegações
- Coleta evidência visual (screenshots, DOM, logs)
- Detecta intenção mesmo em campos com máscara JS
- Suporta SPA (React, Angular, Vue)

### ✅ Compilação para Playwright

- Gera Python válido automaticamente
- Suporta assertions robustas (semânticas, não estruturais)
- Injeta dados externos via `--data JSON`
- Uma linha de comando: `testforge compile`

### ✅ Self-Healing Automático

- **L0:** Retry simples (timeout, stale element)
- **L1:** Classificação + routing para agents (11 famílias)
- **L2:** Healing propose (novo seletor, estratégia)
- **L3:** Oracle validation (learning automático)

### ✅ Métricas de Qualidade

- Integridade de evidência (cobertura de campos)
- Taxa de healing (true vs false cures)
- Execution report com detalhes por step
- Identificação de blind spots

---

## Arquitetura de Healing

```
Step Falha
    ↓
[L0] Retry simples
    └─ Timeout? → wait + retry
    └─ Stale? → find + retry
    
[L1] Classifier + Agent roteamento
    └─ Classify erro em FAM-01 a FAM-11
    └─ Route para SelectorAgent, TimingAgent, etc
    
[L2] Proposal + Execution
    └─ Agent propõe novo seletor/estratégia
    └─ Tenta aplicar proposta
    
[L3] Oracle Validation
    └─ Valida se healing funcionou
    └─ Armazena em base de conhecimento

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

**Fase D (🎯 Planejada)** — Executor com healing L0-L3 completo

---

## Próximas Ações

1. **Testers:** [Guia Rápido](USER-GUIDE/QUICK-START.md) — Comece a gravar em 5 min
2. **Developers:** [Arquitetura](ARQUITETURA/FASES.md) — Entenda as 4 fases
3. **Pesquisadores:** [Análise LLM](PESQUISA/ANALISE-LLM.md) — Como o LLM valida

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

**Última atualização:** 2026-06-20  
**Versão:** v0.4.0
