# TestForge v0.3.0 — Prompt Pack GSD

**Versão:** 0.3.0
**Data:** 2026-06-15
**Status:** Ativo
**Objetivo:** Prompts otimizados para agentes GSD trabalharem no TestForge em cada fase do pipeline.

---

## 1. Prompt Base (Contexto do Projeto)

Use este prompt como contexto fixo do agente antes de qualquer tarefa:

```text
Você é um agente de desenvolvimento trabalhando no projeto TestForge v0.3.0.

## Sobre o TestForge

TestForge é uma ferramenta CLI Python que grava fluxos de usuário em páginas web,
gera scripts Playwright com self-healing determinístico, e cura testes quebrados
automaticamente usando um pipeline de 4 camadas (L0→L3).

## Stack
- Python 3.10+, Playwright (sync_api), pytest
- JSONL + filesystem (zero DB)
- Azure OpenAI (gpt-4.1-mini) para L3 healing
- Fake-bank app em synthetic_lab/ para testes

## Arquitetura
```
Recorder → SemanticTestCase (MIS) → Compiler → Runner + Healing (L0→L3)
```

- L0: HealingCatalog (recipe match JSONL, <50ms, zero LLM)
- L1: FallbackRunner (candidatos MIS, determinístico, timeout 2s)
- L2: SpecialistAgents (6 agentes: Selector, Timing, Context, State, DynamicDOM, Input)
- L3: LLMHealer / MockLLMHealer (Azure GPT-4.1-mini, off critical path)

## Princípios obrigatórios
1. Determinístico primeiro — LLM só como último recurso
2. MockLLMHealer sem API key (funciona offline)
3. Confidence gate ≥ 0.5 para auto-healing
4. Max retry depth = 1
5. Auto-learn: curas bem-sucedidas → HealingCatalog
6. Dados sensíveis: alert_only, nunca mascarar
7. Nenhum healing sem evidência (DOM ≥ 100 chars)
8. Conventional commits (feat:, fix:, docs:, test:, chore:)

## Diretórios principais
- src/testforge/ — código fonte (21 módulos)
- tests/ — 124 testes (pytest + Playwright)
- recordings/ — gravações de fluxo (JSONL + screenshots)
- semantic_tests/ — scripts Playwright gerados
- synthetic_lab/ — fake-react-bank-app para testes
- .planning/ — GSD artifacts (ROADMAP, STATE, EPICOS-STORIES)
- docs/diagramas/ — 13 diagramas PlantUML

## Comandos CLI
- testforge record <url> — gravar fluxo
- testforge compile <recording> [--data] — gerar script
- testforge run <script> [--headless] — executar com healing L0→L3
- testforge pipeline <url> — pipeline completa
- testforge demo-heal — demo de healing real
```

---

## 2. Prompt: Record (Gravação de Fluxo)

```text
## Tarefa: Implementar ou debugar o Recorder

### Contexto
O recorder usa Playwright sync_api com injeção JS via add_init_script.
Captura eventos: pointerup, input, keydown. Gera raw_events.jsonl.
Comandos de teclado: Shift+P (pause), Shift+S (stop), Shift+A (assert).

### Arquivos relevantes
- src/testforge/recorder/recorder_controller.py — controlador principal
- src/testforge/recorder/recording_session.py — sessão de gravação
- src/testforge/recorder/raw_event.py — modelo de evento
- src/testforge/cli/app.py:cmd_record() — CLI entry point

### Critérios de aceite
- Gravação gera raw_events.jsonl com eventos de fill, click, navigation
- Screenshots salvos em recordings/{id}/screenshots/
- DOM snapshots em recordings/{id}/dom_snapshots/
- Network log em recordings/{id}/network_log.json
- Overlay UI funcional (contador de passos, botões)
- Funciona em modo headless e headed

### Padrões a seguir
- Playwright API nativa (page.on()), sem extensão de browser
- add_init_script() para injeção JS
- Eventos com timestamp ISO 8601
- Target element com role, accessible_name, label, placeholder, text, tag, element_id
```

---

## 3. Prompt: Compile (Compilação de Script)

```text
## Tarefa: Implementar ou debugar o Compiler

### Contexto
O compiler lê SemanticTestCase (MIS) e gera script Playwright Python com fallback loop.
Suporte a data-driven testing via flag --data (extrai valores para JSON externo).

### Arquivos relevantes
- src/testforge/semantic/compiler.py — PlaywrightCompiler
- src/testforge/semantic/model.py — SemanticTestCase, SemanticAction, SemanticTarget
- src/testforge/semantic/recording_normalizer.py — RecordingNormalizer
- src/testforge/semantic/data_extractor.py — extração de massa de dados
- src/testforge/cli/app.py:cmd_compile() — CLI entry point

### Critérios de aceite
- Script gerado compila sem erros (compile() built-in)
- Fallback loop: for/else/try/except para cada step
- Candidatos ordenados por score decrescente
- Data-driven: --data gera test_data.json, script lê _data.get()
- Suporte a 4 tipos de assert: textual, estado, visivel, automatico
- Script standalone: executável via pytest

### Padrões a seguir
- Seletores CSS/text (não Playwright API chains como page.get_by_role)
- Template de script: imports → BASE_URL → _data → test function
- Safe naming: sanitizar IDs com regex [^a-zA-Z0-9_]
```

---

## 4. Prompt: Run + Healing (Execução com Cura)

```text
## Tarefa: Implementar ou debugar o Runner + Healing Pipeline

### Contexto
O runner executa passos inline com healing L0→L3 via CuradorAutomatico.
Pipeline: classifier → L0 catalog → L2 agent → L3 LLM/Mock.
Auto-learn registra curas bem-sucedidas no HealingCatalog.

### Arquivos relevantes
- src/testforge/cli/app.py:cmd_run() — execução inline
- src/testforge/healing/curator.py — CuradorAutomatico (L0→L3 pipeline)
- src/testforge/healing/llm_healer.py — LLMHealer + MockLLMHealer
- src/testforge/healing/agents/ — 6 agentes especialistas L2
- src/testforge/healing/evidence_payload.py — EvidencePayload
- src/testforge/evidence/evidence_collector.py — EvidenceCollector
- src/testforge/taxonomy/taxonomy.py — FailureClassifier (11 famílias, 88 códigos)
- src/testforge/runner/fallback_runner.py — FallbackRunner (L1)

### Critérios de aceite
- Passos executados inline (não depende de subprocess)
- Falha → classifier → evidence → curator.cure()
- L0: HealingCatalog.match() por family+symptom
- L2: route_to_agent() → specialist deterministic healing
- L3: MockLLMHealer (sem API) ou Azure GPT-4.1-mini (com API)
- Curas bem-sucedidas → _register_learned() no catálogo
- Failure tracker: 5 falhas consecutivas → notificação
- Métricas: healed, layer_used, llm_used, false_heal_rate

### Debug
- MockLLMHealer ativo por padrão (sem API key)
- AZURE_OPENAI_KEY + AZURE_OPENAI_ENDPOINT → LLM real
- Fake-bank em http://localhost:8765 para testes
- Mutation via ?mutation=change_id para forçar falhas
```

---

## 5. Prompt: Code Review

```text
## Tarefa: Revisar código do TestForge

### Checklist de revisão

#### Arquitetura
- [ ] LLM nunca no critical path? (MockLLMHealer padrão)
- [ ] Separação de responsabilidades? (Recorder grava, Compiler gera, Curator cura)
- [ ] EvidenceCollector apenas coleta, não decide healing?
- [ ] PromotionGate apenas decide promoção?

#### Segurança
- [ ] Dados sensíveis em alert_only? (nunca mascarar)
- [ ] DOM sanitizado antes de enviar ao LLM? (scripts/styles removidos)
- [ ] API keys via env vars, nunca hardcoded?
- [ ] Sem eval() ou exec() em input de usuário?

#### Qualidade
- [ ] Testes para cada módulo novo? (pytest + Playwright)
- [ ] Conventional commits? (feat:, fix:, docs:, test:)
- [ ] Sem imports não utilizados?
- [ ] Tipagem consistente? (dataclasses com type hints)
- [ ] Docstrings em funções públicas?
- [ ] Fallback loop em scripts gerados? (for/else/try/except)

#### Performance
- [ ] L0: <50ms (JSONL match)
- [ ] L1: timeout 2s por candidato
- [ ] L2: deterministico, sem chamada externa
- [ ] L3: apenas quando L0-L2 esgotam (raro)
- [ ] DOM truncado em 3000 chars (não enviar HTML inteiro ao LLM)

#### Healing
- [ ] Confidence gate ≥ 0.5?
- [ ] Taxonomy validation? (family ∈ FAMILIES, taxonomy ∈ TAXONOMIES)
- [ ] Strategy validation? (∈ ALLOWED_STRATEGIES)
- [ ] Rollback automático em REGRESSED/STAGNATED?
- [ ] Max retry depth = 1?
- [ ] Auto-learn registra receitas no catálogo?
```

---

## 6. Prompt: Verificação

```text
## Tarefa: Verificar implementação de fase

### Passos de verificação

1. **Goal-backward check:** O que foi implementado resolve o problema da fase?
2. **Test coverage:** Todos os novos módulos têm testes?
3. **Integration:** O novo código integra com módulos existentes sem quebrar?
4. **Regression:** Rodar `pytest tests/ -q` — 124+ testes passando?
5. **Manual smoke test:** Fluxo end-to-end no fake-bank?

### Comandos de verificação
```bash
# Testes completos
python -m pytest tests/ -v

# Verificar imports
python -c "from testforge.cli.app import main"

# Testar CLI
python -m testforge.cli.app --help

# Testar compilação
python -m testforge.cli.app compile HEAL-DEMO

# Testar execução (sem mutation)
python -m testforge.cli.app run semantic_tests/ST-HEAL-DEMO/test_st-heal-demo.py --headless

# Testar data-driven
python -m testforge.cli.app compile HEAL-DEMO --data
python -m testforge.cli.app run semantic_tests/ST-HEAL-DEMO/test_st-heal-demo.py --headless
```

### Sinais de alerta
- Número de testes diminuiu (regressão)
- Novos imports quebrando (dependência circular)
- CLI command quebrado (argparse)
- Script gerado não compila (SyntaxError)
- Healing pipeline não ativado na falha
```

---

## 7. Prompt: Nova Feature (Template)

```text
## Tarefa: Implementar [NOME DA FEATURE]

### Contexto
[Descrever o problema que a feature resolve e como se encaixa na arquitetura]

### Arquivos que serão criados/alterados
- src/testforge/[modulo]/[arquivo].py — [descrição]
- tests/test_[feature].py — [descrição]

### Critérios de aceite
- [ ] [Critério 1]
- [ ] [Critério 2]
- [ ] Testes passando (não regredir)

### Padrões a seguir
- Dataclasses com type hints
- JSONL para storage (sem SQLite)
- Playwright sync_api (não async)
- Conventional commits
- Docstrings em português, código em inglês

### Referências
- [Link para doc de arquitetura]
- [Link para issue/story]
```
