
# TestForge — Plano Macro de Desenvolvimento do Sistema de Gravação Resiliente e Self-Healing Governado

## 1. Visão

Construir uma plataforma que grave fluxos de usuário como contratos semânticos, gere testes Playwright robustos, execute em shadow mode, sugira self-healing determinístico, colete evidências, valide oracles pós-ação e promova curas apenas mediante governança objetiva.

## 2. Princípios

1. Determinístico primeiro.
2. LLM apenas como curadoria.
3. Nenhum healing sem evidência.
4. Nenhum healing promovido sem oracle pós-ação.
5. Nenhuma promoção sem Promotion Gate.
6. Toda decisão precisa ser auditável.
7. Sistemas sintéticos validam antes dos ambientes reais.

## 3. Fases macro

### Fase 0 — Fundação e decisões

Objetivo: congelar decisões mínimas para iniciar desenvolvimento.

Entregas:
- arquitetura alvo;
- schema SQLite inicial;
- formato canônico do Evidence Package;
- taxonomia core;
- política inicial do Promotion Gate;
- definição do primeiro fake app.

Critério de saída:
- repositório criado;
- pipeline local executando;
- SQLite inicial versionado;
- primeiro teste sintético abrindo o fake app.

### Fase 1 — Synthetic Lab mínimo

Objetivo: criar laboratório controlado para validar falhas conhecidas.

Entregas:
- fake-react-bank-app;
- mutation_matrix.yaml;
- mutações: change_id, change_accessible_name, duplicate_button_text, overlay_blocks_click;
- runner de mutações;
- registro de mutation_result.

Critério de saída:
- cada mutação gera resultado esperado;
- taxonomia classifica corretamente casos básicos;
- evidências são coletadas automaticamente.

### Fase 2 — EvidenceCollector e banco de conhecimento

Objetivo: registrar automaticamente evidências e histórico.

Entregas:
- EvidenceCollector;
- EvidenceStore SQLite;
- tabelas healing_suggestion, evidence_package, oracle_observation, review_decision;
- queries de revisão;
- manifest.json por execução.

Critério de saída:
- cada falha sintética gera evidence package completo;
- casos pendentes aparecem em query de revisão;
- oracles são persistidos.

### Fase 3 — Modelo Intermediário Semântico e geração de candidatos

Objetivo: representar passos como intenção + alvo + contexto + candidatos.

Entregas:
- MIS schema;
- RawRecordedEvent -> SemanticAction;
- LocatorCandidateGenerator;
- LocatorScorer;
- cálculo de uniqueness/actionability;
- fallback determinístico inicial.

Critério de saída:
- um fluxo fake gera MIS;
- candidatos são ranqueados;
- fallback é executado em ambiente sintético.

### Fase 4 — Shadow Mode

Objetivo: sugerir healing sem aplicar automaticamente.

Entregas:
- ShadowHealingObservation;
- FailureClassifier;
- TaxonomyRouter;
- ShadowValidator;
- integração com EvidenceCollector;
- revisão humana via query/arquivo/endpoint simples.

Critério de saída:
- falha sintética gera sugestão de healing;
- sugestão não é autoaplicada;
- evidência + oracle + revisão são registrados.

### Fase 5 — Oracle pós-ação robusto

Objetivo: validar intenção após ação sugerida.

Entregas:
- OracleRunner;
- oracles visual_dom, field_value, network, business_state;
- matriz de confusão do oracle;
- métricas precision, recall, false_acceptance_rate;
- política de oracle por tipo de ação.

Critério de saída:
- pelo menos dois oracles por ação crítica;
- falso aceite medido;
- oracle fraco impede promoção.

### Fase 6 — Promotion Gate

Objetivo: governar evolução de sugestões.

Entregas:
- PromotionGate;
- políticas por estado: experimental, shadow_validated, canary, trusted;
- blockers globais;
- registro de promotion_decision;
- integração com review_decision e oracle_observation.

Critério de saída:
- nenhuma sugestão é promovida sem evidência completa;
- gate retorna razões objetivas;
- query mostra estado de promoção.

### Fase 7 — Adaptação por tecnologia

Objetivo: suportar políticas específicas por tecnologia.

Entregas:
- TechnologyDetector;
- perfis React, Angular, JSF-like, iframe, shadow DOM;
- score_adjustments por tecnologia;
- extensões de taxonomia;
- synthetic apps adicionais.

Critério de saída:
- mutações React e Angular têm classificação especializada;
- pesos mudam conforme tecnologia;
- casos não recuperáveis não acionam locator healing.

### Fase 8 — Integração com aplicação real piloto

Objetivo: rodar em fluxo real controlado.

Entregas:
- seleção de 5 fluxos reais;
- shadow mode only;
- evidence package em ambiente real;
- métricas por fluxo;
- relatório de falsos positivos.

Critério de saída:
- 100 sugestões revisadas ou volume acordado;
- false_heal_rate < 2%;
- precision >= 95%;
- 0 falso healing crítico.

### Fase 9 — Canary auto-heal

Objetivo: liberar auto-heal limitado.

Entregas:
- feature flag de auto-heal;
- rollback;
- allowlist de fluxos/casos;
- relatório pós-execução;
- revisão obrigatória após canary.

Critério de saída:
- sem falso healing crítico;
- overhead < 20%;
- LLM escalation < 10%.

### Fase 10 — Produto interno e operação contínua

Objetivo: transformar em plataforma operável.

Entregas:
- dashboard de revisão;
- exportação Allure/HTML;
- políticas versionadas;
- auditoria;
- documentação;
- integração CI/CD;
- processo de curadoria LLM.

Critério de saída:
- ciclo completo funcionando em rotina de desenvolvimento;
- banco de healing evoluindo continuamente;
- governança aprovada.

## 4. Componentes finais

- Recorder Sensorial
- Modelo Intermediário Semântico
- Candidate Generator
- Locator Scorer
- Failure Classifier
- Technology Detector
- Taxonomy Router
- Deterministic Fallback Runner
- Shadow Validator
- Oracle Runner
- Evidence Collector
- Evidence Store
- Review Queue
- Promotion Gate
- Synthetic Lab
- LLM Curator
- Reporting/Dashboard

## 5. Decisões pendentes antes de quebrar em épicos

1. Tecnologia do backend do TestForge.
2. SQLite apenas local ou PostgreSQL já no MVP corporativo.
3. Formato final do MIS.
4. Primeiro fluxo real piloto.
5. Limite aceitável de falso healing por criticidade.
6. Política de armazenamento de screenshots/DOM por sensibilidade.
7. Quem revisa sugestões no shadow mode.
8. Se haverá UI de revisão desde o início ou query/arquivo no MVP.
9. Como mascarar dados sensíveis nas evidências.
10. Como versionar políticas de tecnologia e Promotion Gate.

## 6. MVP recomendado

MVP deve ser um slice vertical, não uma suíte completa.

Escopo:
- fake-react-bank-app;
- 4 mutações;
- EvidenceCollector;
- SQLite;
- Oracle visual + business_state;
- query de pendentes;
- PromotionGate experimental -> shadow_validated;
- relatório simples.

Resultado esperado:
- uma falha sintética produz uma sugestão de healing;
- a sugestão gera evidências;
- a sugestão aparece para revisão;
- a revisão alimenta métricas;
- o Promotion Gate decide com motivos.
