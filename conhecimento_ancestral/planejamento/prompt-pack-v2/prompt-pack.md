# TestForge — Prompt Pack LLM v0.2.0

**Versão:** 0.2.0  
**Status:** draft  
**Atualização principal:** inclusão explícita do Recorder Sensorial e da localização dos artefatos gravados.  
**Política de dados sensíveis no MVP:** `alert_only`; não mascarar automaticamente evidências ou gravações.

---

# 1. Prompt base para todas as iterações

```text
Você é um agente de desenvolvimento trabalhando no projeto TestForge.

Contexto do projeto:
O TestForge é uma plataforma para gravar fluxos de usuário como contratos semânticos, gerar testes Playwright robustos, executar validações em shadow mode, sugerir self-healing determinístico, coletar evidências, validar oracles pós-ação e promover curas apenas por meio de Promotion Gate.

Arquitetura alvo:
Recorder Sensorial
  -> RawRecordedSession
  -> Modelo Intermediário Semântico / SemanticTestCase
  -> Playwright Compiler
  -> Generated Playwright Test
  -> Runner / Shadow Mode / Evidence / Oracle / Promotion Gate

Diretórios normativos:
- recordings/{recording_id}/ para gravação bruta;
- semantic_tests/{test_id}/ para SemanticTestCase;
- generated_tests/{test_id}/ para teste Playwright gerado;
- evidence/{run_id}/ para evidências de execução;
- policies/ para políticas versionadas;
- schemas/ para contratos versionados;
- adrs/ para decisões arquiteturais.

Princípios obrigatórios:
1. Determinístico primeiro.
2. LLM apenas como curadoria, nunca como mecanismo principal de healing.
3. Nenhum healing sem evidência.
4. Nenhuma promoção sem Promotion Gate.
5. Shadow mode antes de auto-heal.
6. Synthetic Lab antes de piloto real.
7. O Recorder Sensorial não gera script final como fonte de verdade.
8. O Recorder Sensorial não escolhe locator definitivo.
9. O SemanticTestCase é a fonte de verdade do teste.
10. O teste Playwright gerado é artefato derivado e pode ser regenerado.
11. Dados sensíveis no MVP: alert_only, sem mascaramento automático.

Restrições:
- Não implemente auto-heal no MVP inicial.
- Não chame LLM para corrigir locators no caminho principal.
- Não use mascaramento automático de dados sensíveis.
- Não misture responsabilidades.
- Todo código deve ter teste ou execução sintética demonstrável.

Padrão de entrega:
- Resumo do que foi implementado.
- Arquivos criados/alterados.
- Como executar.
- Como testar.
- Critérios de aceite atendidos.
- Próximo passo recomendado.
```

---

# 2. Sprint 1 — Fundação e Synthetic Lab mínimo

## Iteração 1.1 — Criar estrutura inicial do repositório

```text
Implemente a estrutura inicial do repositório TestForge.

Crie:
- README.md
- CHANGELOG.md
- VERSION
- docs/
- adrs/
- policies/
- schemas/
- src/testforge/
- tests/
- synthetic_lab/
- scripts/
- recordings/
- semantic_tests/
- generated_tests/
- evidence/

Inclua no README a arquitetura:
Recorder Sensorial -> RawRecordedSession -> SemanticTestCase -> Playwright Compiler -> Generated Test -> Runner/Shadow.

Inclua ADRs:
- ADR-0001: Usar shadow mode antes de auto-heal.
- ADR-0002: EvidenceCollector e Recorder em modo alert_only para dados sensíveis.
- ADR-0003: SemanticTestCase é fonte de verdade; Playwright gerado é derivado.

Critérios de aceite:
- Todos os diretórios existem.
- O README documenta onde fica gravação bruta, teste semântico, teste gerado e evidência.
- VERSION = 0.2.0.
- CHANGELOG possui entrada 0.2.0.
```

## Iteração 1.2 — Criar fake-react-bank-app

```text
Implemente synthetic_lab/fake-react-bank-app com fluxo simples de consulta por CPF.

Requisitos:
- campo CPF com label acessível;
- botão Pesquisar;
- seção Resultado da consulta;
- resultado exibe CPF informado;
- suporte a query string mutation.

Crie teste Playwright mínimo validando fluxo sem mutação.

Critérios de aceite:
- Fake app roda localmente.
- Teste Playwright passa.
- Locators acessíveis existem para CPF, Pesquisar e Resultado da consulta.
```

## Iteração 1.3 — Criar mutation_matrix.yaml

```text
Crie synthetic_lab/mutation_matrix.yaml com mutações:
- change_id;
- change_accessible_name;
- duplicate_button_text;
- overlay_blocks_click;
- disabled_button.

Cada mutação deve declarar:
- code;
- technology;
- url_query;
- expected_taxonomy;
- expected_recoverable;
- expected_strategy;
- expected_oracles.

Critérios de aceite:
- YAML válido.
- README explica que mutações sem expectativa definida falham no pipeline sintético.
```

## Iteração 1.4 — Implementar mutações sintéticas iniciais

```text
Implemente as mutações declaradas no fake-react-bank-app e crie testes Playwright para cada uma.

Critérios de aceite:
- Cada mutação é acionada por query string.
- duplicate_button_text gera ambiguidade real.
- overlay_blocks_click gera problema de actionability, não de locator.
- disabled_button gera ACTIONABILITY_DISABLED.
```

---

# 3. Sprint 2 — Recorder Sensorial

## Iteração 2.1 — Implementar RecordingSession e RecorderController

```text
Implemente o núcleo do Recorder Sensorial.

Arquivos sugeridos:
- src/testforge/recorder/recording_session.py
- src/testforge/recorder/recorder_controller.py
- src/testforge/recorder/raw_event.py
- src/testforge/recorder/raw_recording_store.py

Requisitos:
1. Criar RecordingSession com recording_id, application, base_url, started_at, finished_at e status.
2. Criar RecorderController.start().
3. Criar RecorderController.stop().
4. Criar diretório recordings/{recording_id}.
5. Criar recording_metadata.json.
6. Criar raw_events.jsonl vazio no início.

Critérios de aceite:
- Iniciar gravação cria diretório correto.
- Finalizar gravação atualiza metadata.
- Sessão finalizada não aceita novos eventos.
- Teste unitário cobre start/stop.
```

## Iteração 2.2 — Capturar eventos básicos no navegador

```text
Implemente captura de eventos básicos do usuário via Playwright.

Eventos mínimos:
- click;
- input/fill;
- navigation.

Requisitos:
1. Criar EventListener ou mecanismo equivalente.
2. Cada evento deve gerar RawRecordedEvent.
3. Cada evento deve ser persistido em raw_events.jsonl.
4. Cada evento deve conter event_id, timestamp, type, url, page_title e target básico.

Critérios de aceite:
- Ao executar fluxo no fake-react-bank-app, raw_events.jsonl contém eventos de fill e click.
- Eventos possuem timestamp e URL.
- O recorder não gera locator final.
- Teste sintético demonstra a gravação.
```

## Iteração 2.3 — Capturar snapshot do alvo e contexto

```text
Expanda o Recorder Sensorial para capturar detalhes do elemento alvo e contexto da página.

Para cada evento com alvo DOM, capturar:
- tag;
- text;
- role;
- accessible_name;
- id;
- name;
- data-testid;
- placeholder;
- label inferida;
- attributes relevantes;
- bounding box;
- textos próximos;
- frame context;
- shadow DOM context.

Critérios de aceite:
- raw_events.jsonl contém target enriquecido.
- Para o botão Pesquisar, role e accessible_name são preenchidos quando disponíveis.
- Para o campo CPF, label é preenchida quando detectável.
- Nenhum locator definitivo é escolhido.
```

## Iteração 2.4 — Capturar artefatos da gravação

```text
Implemente captura de artefatos por evento durante a gravação.

Artefatos:
- screenshot por evento;
- DOM snapshot por evento;
- accessibility snapshot quando disponível;
- network_log.json da sessão.

Diretórios:
- recordings/{recording_id}/screenshots/
- recordings/{recording_id}/dom_snapshots/
- recordings/{recording_id}/ax_snapshots/

Critérios de aceite:
- Cada evento relevante referencia seus artefatos.
- Os arquivos existem no diretório da gravação.
- network_log.json é criado.
- Se AX snapshot não estiver disponível, registrar erro controlado, sem quebrar gravação.
```

## Iteração 2.5 — Implementar alerta de dados sensíveis na gravação

```text
Implemente detector alert_only para possíveis dados sensíveis na gravação.

Requisitos:
1. Detectar padrões simples como CPF, CNPJ e identificador numérico longo.
2. Registrar sensitive_data_alert.json na sessão.
3. Incluir no recording_metadata.json um resumo do alerta.
4. Não mascarar.
5. Não remover.
6. Não alterar raw_events, screenshots, DOM ou network log.

Critérios de aceite:
- Ao gravar CPF no fake app, o alerta indica possível dado sensível.
- masking_applied é false.
- policy é alert_only.
- O valor original permanece preservado.
```

## Iteração 2.6 — Teste E2E da gravação bruta

```text
Crie script scripts/record_fake_flow.py.

Fluxo:
1. Inicia RecorderController.
2. Abre fake-react-bank-app sem mutação.
3. Preenche CPF.
4. Clica em Pesquisar.
5. Finaliza gravação.
6. Imprime caminho da gravação.

Critérios de aceite:
- O script cria recordings/{recording_id}.
- raw_events.jsonl contém fill e click.
- Existem screenshots e DOM snapshots.
- Existe sensitive_data_alert.json.
- O README explica como executar.
```

---

# 4. Sprint 3 — EvidenceCollector e EvidenceStore

## Iteração 3.1 — Implementar EvidenceCollector básico

```text
Implemente src/testforge/evidence/evidence_collector.py.

Coletar:
- screenshot_before/after;
- dom_before/after;
- ax_tree_before/after quando disponível;
- network_log;
- score_breakdown;
- oracle_results;
- promotion_decision;
- manifest.json.

Política de dados sensíveis:
- alert_only;
- masking_applied false;
- sem alteração de evidências.

Critérios de aceite:
- Execução sintética gera evidence/{run_id}.
- manifest referencia artefatos.
- manifest inclui sensitive_data_alert.
```

## Iteração 3.2 — Implementar EvidenceStore SQLite

```text
Implemente SQLite store com tabelas:
- healing_suggestion;
- evidence_package;
- oracle_observation;
- review_decision;
- promotion_decision.

Critérios de aceite:
- Banco é criado automaticamente.
- Inserts principais possuem testes unitários.
- list_pending_reviews retorna sugestões shadow sem revisão.
```

## Iteração 3.3 — Criar pending_reviews.sql

```text
Crie scripts/sql/pending_reviews.sql para listar sugestões pendentes de revisão.

Critérios de aceite:
- Lista apenas mode shadow.
- Ignora itens já revisados.
- Retorna caminhos das evidências.
```

---

# 5. Sprint 4 — SemanticTestCase e Compiler

## Iteração 4.1 — Definir schema do SemanticTestCase

```text
Crie schemas/semantic_test_case.schema.yaml.

Deve conter:
- metadata;
- source_recording_id;
- preconditions;
- steps;
- SemanticAction;
- SemanticTarget;
- ActionContext;
- locator_candidates;
- expected_after_action;
- healing_policy.

Critérios de aceite:
- Schema possui versão.
- Exemplo representa fluxo gravado do fake app.
- Suporta múltiplos candidatos.
```

## Iteração 4.2 — Converter RawRecordedSession para SemanticTestCase

```text
Implemente src/testforge/semantic/recording_normalizer.py.

Fluxo:
1. Ler recordings/{recording_id}/raw_events.jsonl.
2. Converter eventos relevantes em SemanticAction.
3. Converter target bruto em SemanticTarget.
4. Gerar contexto inicial.
5. Persistir semantic_tests/{test_id}/semantic_test_case.yaml.

Critérios de aceite:
- Gravação fake vira SemanticTestCase.
- Cada ação referencia event_id original.
- Nenhum locator definitivo é obrigatório.
```

## Iteração 4.3 — Implementar LocatorCandidateGenerator

```text
Implemente geração de candidatos:
- role + accessible name;
- label;
- placeholder;
- test_id;
- visible_text;
- CSS simples como fallback.

Critérios de aceite:
- Campo CPF gera candidato label.
- Botão Pesquisar gera candidato role.
- data-testid gera candidato quando disponível.
- Cada candidato tem reason.
```

## Iteração 4.4 — Implementar PlaywrightPythonCompiler inicial

```text
Implemente compiler que lê SemanticTestCase e gera teste Playwright Python.

Saída:
generated_tests/{test_id}/test_*.py

Critérios de aceite:
- Teste gerado executa contra fake-react-bank-app sem mutação.
- Usa locators priorizados.
- Inclui assertion visual ou business_state quando disponível.
- Teste gerado é tratado como artefato derivado.
```

---

# 6. Sprint 5 — Oracles e PromotionGate mínimo

## Iteração 5.1 — Implementar OracleRunner visual_dom

```text
Implemente oracle visual_dom.

Critérios de aceite:
- Valida Resultado da consulta visível.
- Registra passed/failed/inconclusive.
- Persiste oracle_observation.
```

## Iteração 5.2 — Implementar OracleRunner business_state

```text
Implemente oracle business_state mínimo para validar que CPF exibido é igual ao CPF pesquisado.

Critérios de aceite:
- Passa quando CPF exibido é correto.
- Falha quando CPF diverge.
- Resultado é persistido.
```

## Iteração 5.3 — Implementar PromotionGate mínimo

```text
Implemente PromotionGate com estados:
- experimental;
- shadow_validated;
- rejected.

Bloqueios:
- evidence incompleto;
- oracle ausente;
- oracle conflitante;
- false_heal revisado;
- uniqueness_score baixo;
- actionability_score baixo;
- semantic_gap baixo.

Critérios de aceite:
- Retorna decisão com motivos.
- Persiste promotion_decision.
```

---

# 7. Sprint 6 — Taxonomia, ShadowValidator e fallback

## Iteração 6.1 — Implementar taxonomia core

```text
Implemente policies/failure_taxonomy.yaml e classes de taxonomia.

Famílias:
- locator_resolution;
- actionability;
- synchronization;
- oracle;
- environment;
- context.

Critérios de aceite:
- ACTIONABILITY_OBSCURED não permite locator healing.
- LOCATOR_NOT_FOUND permite fallback/healing.
```

## Iteração 6.2 — Implementar FailureClassifier mínimo

```text
Classifique:
- locator não encontrado;
- locator ambíguo;
- overlay;
- disabled;
- oracle failed.

Critérios de aceite:
- Mutações do fake app são classificadas conforme mutation_matrix.yaml.
```

## Iteração 6.3 — Implementar ShadowValidator

```text
Implemente ShadowValidator.

Critérios:
- Sugere healing para LOCATOR_NOT_FOUND.
- Não sugere troca de locator para ACTIONABILITY_OBSCURED.
- Persiste sugestão mode shadow.
- Sugestão aparece em pending_reviews.
```

## Iteração 6.4 — Implementar fallback determinístico inicial

```text
Implemente fallback runner que tenta candidatos em ordem de score.

Critérios:
- Não usa LLM.
- Só considera sucesso se oracle passar.
```

---

# 8. Sprint 7 — Métricas, revisão e relatório

## Iteração 7.1 — Implementar métricas

```text
Implemente MetricsRepository.

Métricas:
- false_heal_rate;
- precision;
- oracle_precision;
- false_acceptance_rate;
- quarantine_rate;
- llm_escalation_rate.

Critérios:
- Métricas calculadas a partir de review_decision e oracle_observation.
```

## Iteração 7.2 — Criar CLI de revisão

```text
Crie scripts/review_pending.py.

Critérios:
- Lista pendentes.
- Permite registrar TRUE_POSITIVE_HEAL, FALSE_HEAL, NOT_RECOVERABLE, ORACLE_WEAK, TAXONOMY_WRONG, TECHNOLOGY_PROFILE_WRONG, INCONCLUSIVE.
- Após revisão, item sai da lista de pendentes.
```

## Iteração 7.3 — Gerar relatório sintético Markdown

```text
Crie scripts/generate_synthetic_report.py.

Relatório:
- mutações executadas;
- sugestões;
- taxonomias;
- oracles;
- decisões do PromotionGate;
- pendentes;
- false_heal_rate, quando houver.

Critérios:
- reports/synthetic_report.md é gerado.
- Relatório indica se MVP está pronto para avançar.
```

---

# 9. Prompt de encerramento de sprint

```text
Revise o estado atual do TestForge.

Entregue:
1. Resumo do que foi implementado.
2. Arquivos criados/alterados.
3. Como executar.
4. Como testar.
5. Critérios de aceite atendidos.
6. Critérios pendentes.
7. Riscos técnicos.
8. Dívidas técnicas.
9. Atualizações necessárias em README, CHANGELOG, ADRs, schemas ou policies.

Não avance se houver critério crítico pendente.
```

---

# 10. Prompt de revisão crítica de implementação

```text
Revise a implementação da última iteração do TestForge.

Verifique:
1. O Recorder apenas captura e não escolhe locator definitivo?
2. O Recorder persiste RawRecordedSession em recordings/{recording_id}?
3. O SemanticTestCase é tratado como fonte de verdade?
4. O teste Playwright gerado é artefato derivado?
5. O EvidenceCollector apenas coleta evidências?
6. Dados sensíveis estão em modo alert_only, sem mascaramento automático?
7. O ShadowValidator não aplica auto-heal?
8. O PromotionGate apenas decide promoção?
9. Existe teste sintético ou unitário?
10. Documentação e CHANGELOG foram atualizados?

Entregue problemas, correções necessárias, riscos e decisão sobre concluir ou não a iteração.
```
