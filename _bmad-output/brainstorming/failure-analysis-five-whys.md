# BMAD Brainstorming: TestForge - Failure Analysis + Five Whys

**Data:** $(date)
**Metodo:** Failure Analysis + Five Whys
**Contexto:** 4 tentativas anteriores, documentacao ancestral analisada

---

## 1. O Que Funcionou (Preservar)

| Componente | Evidencia | Estado |
|-----------|-----------|--------|
| **Recorder com overlay injection** | `projeto-anterior/demo/` — 30+ sessoes de teste reais | Funcionando |
| **Suporte a PrimeFaces, Angular, jQuery UI, Kendo** | `projeto-anterior/testes/tf-pf/`, `tf-angular/`, `tf-jqui/`, `tf-kendo/` | Funcionando |
| **Deteccao de framework automatica** | `packages/core/testforge/core/recording/session.py` | Funcionando |
| **Bridge extensao Chrome** | `packages/bridge/extension/` | Funcionando |
| **Healing agents (6 agentes)** | `packages/core/testforge/core/healing/agents/` | Implementado |
| **Classifier de falhas** | `packages/core/testforge/core/healing/classifier.py` | Implementado |
| **Gravacao raw → script Playwright** | `packages/core/.../script/builder.py` | Parcial |

---

## 2. O Que Falhou (Corrigir)

### Falha #1: Arquiteta Astronauta
- **O que aconteceu:** Cada tentativa adicionava MAIS especificacao, MAIS governanca, MAIS fases
- **Consequencia:** 700 linhas de epicos, 0 tasks para o recorder
- **Evidencia:** `epicos-historias.md` tem 738 linhas; `tarefas.csv` tem 28 tasks e nenhuma pro recorder

### Falha #2: Codigo Funcional Descartado
- **O que aconteceu:** O recorder funcionava (30 sessoes de teste!) mas foi arquivado como "ancestral" e redesenhado do zero
- **Consequencia:** Perdeu-se o unico componente que realmente funcionava
- **Evidencia:** `projeto-anterior/demo/run_demo.py` executa gravacao completa; mas o `codigo-v020/` implementa recorder diferente

### Falha #3: Governanca Antes de Valor
- **O que aconteceu:** Promotion Gate, ADRs, policies, shadow mode, oracle matrices — tudo especificado antes de gravar 1 teste real
- **Consequencia:** 28 tasks de scaffolding, zero de core value
- **Evidencia:** 10 decisoes pendentes nunca resolvidas no `plano-macro.md`

### Falha #4: Integracao Inexistente
- **O que aconteceu:** Componentes existiam isolados (EvidenceCollector, Oracle, PromotionGate, SQLite) mas nunca integrados
- **Consequencia:** Nenhum teste end-to-end real
- **Evidencia:** `tarefas.csv` sem tasks de integracao

### Falha #5: O Recorder Nunca Foi o Foco
- **O que aconteceu:** O componente mais critico (captura de intencao) nunca teve um epic proprio
- **Consequencia:** Self-healing sem healing real possivel
- **Evidencia:** EP-01 comeca com "fake app", assumindo recorder pronto

---

## 3. Five Whys — Causa Raiz

### Por que o TestForge falhou 4+ vezes?

**Why #1:** Planejamento consumiu todo esforco; implementacao nunca chegou nas partes dificeis.

**Why #2:** Arquitetura foi inflada com governanca (Promotion Gate, ADRs, policies) antes de existir um recorder funcional.

**Why #3:** A equipe compensou falhas anteriores adicionando MAIS especificacao, MAIS fases — resposta de "arquiteto astronauta" a instabilidade.

**Why #4:** Nenhum mecanismo forcava desenvolvimento vertical-slice-first. A metodologia GSD existia no papel mas nao foi seguida para o recorder.

**Why #5 (RAIZ):** O problema fundamental — **gravar intencao do usuario em UIs enterprise reais (CSP, iframes, shadow DOM, widgets customizados)** — nunca foi resolvido. Cada tentativa tentou abstrair AO REDOR dele com camadas semanticas, formulas de scoring e governanca. Mas nao se pode curar o que nao se pode gravar.

---

## 4. Licoes Aprendidas

1. **Vertical slice primeiro.** O recorder funcional do `projeto-anterior` PROVA que e possivel. Comece por ele.

2. **Itere sobre o que funciona.** Nao descarte codigo funcional. O recorder com overlay injection + bridge Chrome + 30 sessoes de teste e o ponto de partida.

3. **Governanca e consequencia, nao pre-requisito.** Promotion Gate, shadow mode, oracle matrices sao UTEIS — mas so depois que o fluxo basico (gravar → gerar script → rodar) funciona.

4. **Integracao e o produto.** Componentes isolados nao entregam valor. O valor esta no fluxo completo: gravar intencao → gerar teste → rodar → detectar falha → curar.

5. **MIS (Modelo Intermediario Semantico) e o coracao.** A grande inovacao arquitetural esta correta: separar captura sensory de execucao de teste. Mas implemente o MIS como uma camada fina primeiro, nao como um mega-schema.

6. **LLM como curador, nao como motor.** O principio "LLM only as curator, never as primary healing engine" esta correto. Mantenha.

---

## 5. Recomendacao para Proxima Iteracao

### Anti-patterns a evitar:
- NAO projetar 10 fases antes de ter 1 funcionando
- NAO especificar formulas de scoring com 4 decimais antes de validar com dados reais
- NAO criar 6 fake apps antes de gravar 1 app real
- NAO escrever ADRs para decisoes nao validadas

### O que fazer diferente:
1. **Comecar pelo recorder funcional** do `projeto-anterior/`
2. **Integrar recorder → script generation → runner** como primeiro vertical slice
3. **Adicionar MIS como camada fina** (nao como mega-schema)
4. **Adicionar healing deterministico** (locator fallback) como segundo slice
5. **So depois: shadow mode, oracle, promotion gate**
6. **Cada slice = GSD phase completa (Discuss → Plan → Execute → Verify → Ship)**
