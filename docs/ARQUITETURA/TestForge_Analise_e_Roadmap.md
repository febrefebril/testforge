
# TestForge — Análise Técnica, Comparação com o Mercado e Roadmap de Evolução

> Base da análise: snapshot do repositório `testforge` (126 arquivos, gerado em 2026-07-27). Todas as observações abaixo referem-se a código real presente no snapshot.

---

## 1. Diagnóstico — o que já existe e está bom

O projeto já tem uma arquitetura madura e bem acima da média de ferramentas caseiras. Componentes sólidos:

| Camada | Módulo | O que faz | Avaliação |
|--------|--------|-----------|-----------|
| Modelo semântico | `semantic/model.py` (MIS: `SemanticTarget`, `LocatorCandidate`) | Representação intermediária rica: role, accessible_name, label, test_id, fingerprint, ax_path, `attribute_stability`, `form_control_name`, `capture_confidence` | Excelente base |
| Scoring de seletor | `semantic/locator/scorer.py` | Estabilidade por atributo alinhada às boas práticas do Playwright (test_id/role+name/label acima; CSS/nth-child/XPath penalizados) | Muito bom |
| Resolução em runtime | `runtime/resolver.py` | Cadeia L0 (cache memória → winning-idx → SQLite) → L1 (candidatos por score) | Bom, mas loop incompleto (ver §3) |
| Auto-healing | `runtime/healer.py` | Pontua DOM vivo contra fingerprint gravada + `HealCatalog` auto-aprendido | Bom |
| Curadoria | `healing/curator.py` | Pipeline L0→L1→L2→L3 (receita → fallback → evidência → LLM) | Muito bom |
| Observabilidade | `metrics/telemetry.py`, `reporting/run_report.py`, `metrics/pilot_metrics.py` | Spans JSONL estilo OpenTelemetry, relatório completo por run, dashboard de prontidão | Bom |
| Detecção em gravação | `recorder/anomaly_detector.py` | Captura console error / pageerror / crash / respostas HTTP ≥400 | Bom |
| Handlers por framework | `handlers/angular_material.py`, `react_mui.py`, `primeFaces.py`, `cdk_overlay.py` | Especialistas por stack de UI | Bom |
| Governança da cura | `promotion/promotion_gate.py`, `oracle/oracle_runner.py` | Só promove cura com evidência + oráculo + unicidade (shadow mode) | Excelente |

**Conclusão:** você não precisa reescrever nada. O núcleo conceitual está correto e é competitivo. Os ganhos virão de **fechar loops que hoje estão pela metade**, **unificar aprendizado fragmentado** e **cortar duplicações**.

---

## 2. Como o mercado resolve os mesmos problemas (estado da arte)

| Problema | Como o mercado resolve | Onde você já faz algo parecido |
|----------|------------------------|-------------------------------|
| **Seletor quebradiço** | Testim, mabl, Functionize, testRigor guardam **vários atributos ponderados** por elemento; em runtime pontuam o DOM vivo e escolhem o melhor match. | `runtime/healer.py::_score_match` faz exatamente isso |
| **Self-healing com aprendizado** | Healenium (open-source) grava cada cura no banco, usa similaridade de nós e **reporta o seletor curado para revisão humana**. | `IntentCatalog` (SQLite) + `HealCatalog` + `promotion_gate` |
| **Seletores estáveis** | Playwright/Cypress recomendam locators voltados ao usuário (`getByRole`/`getByLabel`/`getByTestId`) e evitam CSS/XPath. | `scorer.py` já prioriza isso |
| **Escolher o seletor que funciona** | "Adaptive/ranked locators": mantém **estatística de sucesso por estratégia** e reordena a lista (frequentemente com *multi-armed bandit* / Thompson sampling). | Parcial — só `promote_winning_candidate` em memória |
| **Alerta de quebra** | Integração de CI (Azure Pipelines/GitHub Actions) + detecção de *flaky* (rerun/quarentena) + notificação Slack/Teams + agrupamento por assinatura de falha. | **Ausente** (só existe relatório, não notificação) |
| **Aproveitar LLM** | LLM **fora do caminho crítico** (batch/offline), saída estruturada validada por schema, *eval harness* com dataset dourado para evitar regressão de prompt. | `llm_healer.py` + `ALLOWED_STRATEGIES` + `llm_prompts.py` (falta eval harness) |

O ponto-chave: **o mercado não tem seletor melhor que o seu — tem o *loop de feedback* fechado.** É aí que está seu maior ganho de estabilidade.

---

## 3. Dívidas e riscos identificados no código

### 3.1 Fragmentação de aprendizado (crítico)
Existem **quatro** repositórios de aprendizado que não conversam:

1. `.testforge/heal_catalog.jsonl` — usado por `runtime/healer.py` (fingerprint → seletor)
2. `.testforge/intent_catalog.sqlite` — usado por `runtime/resolver.py` (intent → resolved_call)
3. `.planning/healing-catalog.jsonl` — usado por `healing/healing_catalog.py` (erro → receita)
4. `.planning/failure-counts.json` — `FailureTracker` no `curator.py`

O `resolver` e o `healer` mantêm **caches paralelos que não trocam informação**. Uma cura descoberta pelo `healer` não vira prioridade no `resolver`, e vice-versa. Isso dilui o aprendizado e dificulta responder "qual seletor realmente funciona".

### 3.2 Reordenação por execução está incompleta (crítico p/ sua pergunta)
Hoje:
- `resolver._winning_idx_cache` promove o vencedor — **mas só em memória, perde entre execuções**.
- `IntentCatalog` persiste o `resolved_call` único e ajusta `confidence` (+0.05 sucesso / −0.2 falha) — **mas não reordena a lista de candidatos** em `candidates/step_NNN.json`.
- A ordem dos candidatos compilados continua vindo **só do score estático** do `scorer.py`.

Ou seja: o seletor que *de fato funcionou* não é promovido de forma persistente para a frente da lista. **O loop existe pela metade.**

### 3.3 God-modules (dificultam manutenção e testes)
- `semantic/recording_normalizer.py` — **3.422 linhas**
- `cli/app.py` — **2.595 linhas**
- `recorder/overlay_inject.js` — 2.061 linhas
- `semantic/compiler.py` — 1.627 linhas (ainda mantém `compile` legado + `compile_v2`)

### 3.4 Duplicações e código morto
- `updater.py` (git pull) **e** `updater/auto_updater.py` (via `testforge_update.yml`) — duas implementações do mesmo conceito.
- Dois compiladores vivos (`compile` legado e `compile_v2`) — custo de manter os dois.
- `MockLLMHealer` fora do escopo de teste (verificar uso real).

### 3.5 Sem camada de alerta
`telemetry.py` e `run_report.py` produzem dados ricos, mas **nada notifica** ninguém quando um script quebra. `publisher/azure_devops.py` já sabe falar com o Azure DevOps — está subutilizado.

---

## 4. Roadmap incremental (por ROI, entregas testáveis)

> Alinhado ao seu estilo: sprints com incremento demonstrável e verificável. Nada de *big-bang rewrite*.

### 🥇 Sprint 1 — Fechar o loop de seleção (maior ROI)
**Objetivo:** o seletor que funcionou sobe na lista, de forma persistente.

1. **Criar `SelectorStatsRepository` (SQLite único)** substituindo os caches paralelos. Chave: `(intent, url_sig, action, strategy)`. Métricas por candidato:
   - `attempts`, `successes`, `last_success`, `avg_resolve_ms`
   - `success_rate_ewma` (média móvel exponencial — dá recência sem esquecer histórico)
2. **`resolver` grava TODA tentativa por candidato** (não só o vencedor) — hoje só o vencedor é registrado.
3. **Passo `reorder`** (pós-run ou pré-run): recomputa a ordem em `candidates/step_NNN.json` por score combinado:
   ```
   score_final = w1·estabilidade_estática(scorer) + w2·success_rate_ewma + w3·recência
   ```
   Vencedores vão para o topo, de forma **persistente entre execuções**.
4. **Avançado (opcional):** *Thompson sampling* — explora candidatos alternativos ocasionalmente para não "congelar" num seletor que começou a degradar.

**Entregável demonstrável:** rodar o mesmo teste 2×; na 2ª execução o seletor vencedor aparece em 1º na lista e o `avg_resolve_ms` cai.

### 🥈 Sprint 2 — Alerta automático de quebra
**Objetivo:** quebrou → alguém sabe em minutos, sem spam.

1. **`EventBus` (Observer):** `run_report` e `telemetry` emitem `step_failed` / `script_broken`.
2. **Plugins `Notifier`:** Teams (webhook), e-mail (SMTP) e — reaproveitando `publisher/azure_devops.py` — **abertura automática de work item/bug**.
3. **Dedup por assinatura:** agrupa por `(taxonomy_id, intent, url_sig)` e usa o `FailureTracker`/`REVIEW_THRESHOLD` já existente para só alertar acima do limiar (evita ruído em *flaky*).
4. **Dashboard "Top seletores quebrados"** derivado de `spans.jsonl` (já tem os dados).

**Entregável demonstrável:** derrubar um seletor de propósito → bug criado no Azure DevOps + card no Teams, agrupado.

### 🥉 Sprint 3 — Estabilizar gravador e escalar cobertura
1. **Fechar o contrato do gravador** (você já o considera "closed"): congelar a interface `RawEvent → SemanticTarget`; toda evolução vai para handlers/compiler.
2. **Golden recordings + testes de regressão** do `recording_normalizer.py` (3.422 linhas hoje sem rede de segurança).
3. **Compilação em lote** para subir muitos testes ao repositório de uma vez (aumenta o volume que você pediu).

### Sprint 4 — Refatoração enxuta (em paralelo, guiada por dívida)
1. **Quebrar `recording_normalizer.py`** movendo lógica para `semantic/stages/` (a estrutura de estágios já existe).
2. **Dividir `cli/app.py`** em `cli/commands/*.py` (um arquivo por comando).
3. **`Repository` pattern** unificando os catálogos (consequência do Sprint 1).
4. **Sunset do `compile` legado** — manter só `compile_v2`.
5. **Remover `updater` duplicado.**

---

## 5. Padrões de projeto recomendados (mapa direto ao código)

| Padrão | Onde aplicar | Benefício |
|--------|--------------|-----------|
| **Strategy** | Formalizar interface de estratégia de locator (candidatos) | Adicionar estratégia sem tocar no resolver |
| **Chain of Responsibility** | Extrair classe base para `resolver` (L0→L1) e `curator` (L0→L3) | Camadas plugáveis e testáveis isoladamente |
| **Registry / Plugin** | Handlers de framework, `Notifier`, `Oracle` | Registrar por decorator; abrir/fechar sem editar núcleo |
| **Repository** | `SelectorStatsRepository` unificando os 4 stores | Uma fonte de verdade para aprendizado |
| **Observer / EventBus** | Anomalias + alertas (Sprint 2) | Desacopla detecção de notificação |
| **Pipeline** | `semantic/stages/` (já iniciado) | Absorver o god-module do normalizador |
| **Circuit Breaker** | Chamadas LLM em `llm_healer` | Falha rápida quando a API cai; não trava o run |
| **Multi-armed bandit** | Ordenação de seletores (Sprint 1 avançado) | Balanço explorar/explotar automático |

---

## 6. Como tirar mais proveito de LLM

1. **Tire o LLM do caminho crítico.** Mantenha-o só na camada L3 do curator, idealmente **offline/batch**, com **Circuit Breaker**. Runtime rápido usa cache/heurística.
2. **Saída estruturada validada por schema.** Você já tem `ALLOWED_STRATEGIES` — force JSON schema e rejeite proposta fora do contrato (menos alucinação aplicada em produção).
3. **Triagem de falhas com LLM (batch).** Agrupar falhas por assinatura, gerar hipótese de causa e **sugerir uma receita** para o `HealingCatalog` (com revisão humana via `promotion_gate`).
4. **Eval harness com dataset dourado.** Guarde um conjunto de falhas reais gravadas. A cada mudança de prompt, meça **taxa de cura** — assim você evita regressão de prompt (dor recorrente com LLM).
5. **Enriquecer asserts no compile.** `SemanticTestCase.suggested_asserts` já existe; use LLM para propor asserts a partir do DOM diff, sempre com aprovação do QA.
6. **Versione os prompt packs** (`llm_prompts.py`) e teste-os como código.
7. **Gerar handlers via LLM.** Dê exemplos de DOM (Angular Material/PrimeFaces) e peça ao Copilot/Claude para gerar/estender handlers — acelera cobertura de frameworks.

---

## 7. Respostas diretas às suas perguntas

- **Como o mercado resolve?** Mesmos seletores multi-atributo que você já tem; o diferencial deles é o **loop de feedback fechado** e a **notificação/quarentena**. Você está a 2 sprints de igualar.
- **Como avançar mais rápido e ter mais testes?** Compilação em lote + golden recordings + fechar contrato do gravador. O gargalo hoje não é gravar, é **confiar** no que foi gravado (por isso o loop de seleção vem primeiro).
- **Como automatizar alerta de quebra?** Sprint 2: EventBus + Notifier (Teams/e-mail/Azure DevOps), com dedup por assinatura reusando o `FailureTracker`.
- **Como eleger e reordenar seletores por execução?** Sprint 1: `SelectorStatsRepository` + gravar toda tentativa + passo `reorder` persistente (`score_final = estabilidade + success_rate_ewma + recência`).
- **Quais padrões aplicar?** Strategy, Chain of Responsibility, Registry, Repository, Observer, Pipeline, Circuit Breaker, Bandit (§5).
- **Quais alterações potencializam o projeto?** Unificar catálogos (§3.1) e fechar o loop de seleção (§3.2) — juntos, é o maior salto de estabilidade.
- **O que descartar?** `updater` duplicado, `compile` legado (após migração), consolidar 3 catálogos, revisar `MockLLMHealer`.
- **Vale refatorar / deixar mais enxuto?** **Sim, mas incremental.** Foque nos god-modules (`recording_normalizer`, `cli/app`) e na fragmentação de catálogos. **Não** faça rewrite — o núcleo é bom.
- **Como aproveitar LLM?** §6: fora do hot path, saída estruturada, eval harness, triagem em batch.

---

## 8. Sequência sugerida (visão de uma página)

1. **Semana 1–2:** `SelectorStatsRepository` + gravação de tentativas + reorder persistente. *(estabilidade sobe imediatamente)*
2. **Semana 3–4:** EventBus + Notifier (Teams + Azure DevOps). *(quebras deixam de passar despercebidas)*
3. **Semana 5–6:** Golden recordings + testes de regressão do normalizador + compilação em lote. *(volume de testes cresce com segurança)*
4. **Contínuo:** refatoração dos god-modules + eval harness de LLM.

> Regra de ouro: cada incremento deve ser **demonstrável e reversível**. Comece pelo loop de seleção — é o que dá mais estabilidade por linha de código alterada.

