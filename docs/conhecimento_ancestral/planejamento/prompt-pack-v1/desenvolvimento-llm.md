# TestForge — Sequência de Prompts para Desenvolvimento Assistido por LLM

**Versão:** 0.1.0  
**Status:** draft  
**Objetivo:** orientar uma LLM/Agente de desenvolvimento a implementar o TestForge em iterações pequenas, testáveis e com entrega de valor a cada passo.  
**Política de dados sensíveis no MVP:** `alert_only`; não mascarar automaticamente evidências.

---

# 1. Como usar este arquivo

Cada prompt abaixo deve ser executado em sequência, como se fosse uma sprint incremental. Cada iteração deve produzir:

1. código versionável;
2. testes automatizados ou sintéticos;
3. evidências de execução;
4. atualização de documentação;
5. critérios de aceite verificáveis.

A LLM não deve avançar para a próxima iteração se os critérios de aceite da iteração atual não estiverem cumpridos.

---

# 2. Prompt base para todas as iterações

Use este prompt antes de qualquer iteração, ou como contexto fixo do agente.

```text
Você é um agente de desenvolvimento trabalhando no projeto TestForge.

Contexto do projeto:
O TestForge é uma plataforma para gravar fluxos de usuário como contratos semânticos, gerar testes Playwright robustos, executar validações em shadow mode, sugerir self-healing determinístico, coletar evidências, validar oracles pós-ação e promover curas apenas por meio de Promotion Gate.

Princípios arquiteturais obrigatórios:
1. Determinístico primeiro.
2. LLM apenas como curadoria, nunca como mecanismo principal de healing.
3. Nenhum healing sem evidência.
4. Nenhuma promoção sem Promotion Gate.
5. Shadow mode antes de auto-heal.
6. Synthetic Lab antes de piloto real.
7. EvidenceCollector deve operar no MVP em modo alert_only para dados sensíveis: deve alertar possível presença de dados sensíveis, mas não mascarar, remover ou alterar evidências.
8. Toda decisão relevante deve ser documentada em README, CHANGELOG ou ADR.

Restrições:
- Não implemente auto-heal no MVP inicial.
- Não chame LLM para corrigir locators no caminho principal.
- Não use mascaramento automático de dados sensíveis.
- Não misture responsabilidades: EvidenceCollector coleta, PromotionGate decide, OracleRunner valida, SyntheticLab gera falhas controladas.
- Todo código deve ter teste ou execução sintética demonstrável.

Padrão de entrega esperado em cada iteração:
- Resumo do que foi implementado.
- Arquivos criados/alterados.
- Como executar.
- Como testar.
- Critérios de aceite atendidos.
- Próximo passo recomendado.
```

---

# 3. Sprint 1 — Fundação e Synthetic Lab mínimo

## Iteração 1.1 — Criar estrutura inicial do repositório

```text
Implemente a estrutura inicial do repositório TestForge.

Objetivo:
Criar uma base organizada para desenvolvimento incremental.

Crie a seguinte estrutura:

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

Conteúdo mínimo:
1. README.md com visão geral do TestForge, princípios arquiteturais e como rodar o projeto localmente.
2. VERSION com valor 0.1.0.
3. CHANGELOG.md com entrada inicial 0.1.0.
4. ADR-0001 em adrs/ registrando a decisão: "Usar shadow mode antes de auto-heal".
5. ADR-0002 em adrs/ registrando a decisão: "EvidenceCollector em modo alert_only para dados sensíveis no MVP".
6. policies/evidence_sensitive_data_policy.yaml com mode: alert_only e masking_applied: false.

Critérios de aceite:
- A estrutura de diretórios existe.
- O README explica que o TestForge não fará auto-heal no MVP inicial.
- O README explica que dados sensíveis serão apenas alertados, não mascarados.
- Os dois ADRs existem.
- O CHANGELOG possui versão 0.1.0.
- O projeto pode ser versionado imediatamente em Git.

Ao final, mostre a árvore de diretórios criada e explique brevemente cada arquivo.
```

## Iteração 1.2 — Criar fake-react-bank-app

```text
Implemente o primeiro aplicativo sintético do TestForge: synthetic_lab/fake-react-bank-app.

Objetivo:
Criar uma aplicação fake simples, local e controlável para simular fluxos bancários e falhas de locator/actionability.

Requisitos funcionais:
1. A aplicação deve ter uma tela de consulta de cliente por CPF.
2. Deve possuir campo CPF com label acessível.
3. Deve possuir botão principal com texto "Pesquisar".
4. Após submeter, deve exibir uma seção "Resultado da consulta".
5. O resultado deve exibir o CPF pesquisado.
6. A aplicação deve funcionar sem backend real.

Requisitos técnicos:
1. Pode ser HTML/JS simples ou app React mínimo, desde que rode localmente.
2. Deve aceitar query string `mutation` para ativar mutações futuras.
3. Deve ter instrução clara de execução no README do synthetic_lab.

Critérios de aceite:
- Ao abrir a aplicação sem mutação, o usuário consegue preencher CPF e pesquisar.
- O resultado exibe o CPF informado.
- Existem locators acessíveis mínimos: label CPF, botão Pesquisar, região Resultado da consulta.
- A aplicação roda localmente sem dependências corporativas.

Crie também um teste Playwright mínimo que abra a aplicação, preencha CPF, clique em Pesquisar e valide que o resultado contém o CPF.
```

## Iteração 1.3 — Implementar mutation_matrix.yaml

```text
Crie a matriz declarativa de mutações sintéticas em synthetic_lab/mutation_matrix.yaml.

Objetivo:
Registrar, de forma versionada, quais mutações existem, qual falha esperada elas simulam e se são recuperáveis por locator healing.

Inclua inicialmente as mutações:

1. change_id
   - expected_taxonomy: LOCATOR_NOT_FOUND
   - expected_recoverable: true
   - expected_strategy: fallback_to_role_or_testid
   - expected_oracles: visual_dom, business_state

2. change_accessible_name
   - expected_taxonomy: LOCATOR_NOT_FOUND
   - expected_recoverable: true
   - expected_strategy: fallback_to_testid
   - expected_oracles: visual_dom, business_state

3. duplicate_button_text
   - expected_taxonomy: LOCATOR_AMBIGUOUS
   - expected_recoverable: true
   - expected_strategy: refine_by_context_or_testid
   - expected_oracles: visual_dom, business_state

4. overlay_blocks_click
   - expected_taxonomy: ACTIONABILITY_OBSCURED
   - expected_recoverable: false
   - expected_strategy: overlay_wait_policy_not_locator_healing
   - expected_oracles: none

5. disabled_button
   - expected_taxonomy: ACTIONABILITY_DISABLED
   - expected_recoverable: false
   - expected_strategy: state_or_test_data_diagnosis
   - expected_oracles: none

Critérios de aceite:
- O arquivo YAML é válido.
- Cada mutação possui código, tecnologia, query string, taxonomia esperada, recoverable esperado, estratégia esperada e oracles esperados.
- O README explica que mutações sem expectativa definida não devem ser aceitas.
```

## Iteração 1.4 — Implementar mutações sintéticas iniciais

```text
Implemente no fake-react-bank-app as mutações declaradas em mutation_matrix.yaml.

Mutações obrigatórias:

1. change_id
   - altera o id do botão de pesquisa;
   - mantém texto e comportamento funcional.

2. change_accessible_name
   - altera texto/acessible name de "Pesquisar" para "Consultar";
   - mantém data-testid estável, se existir.

3. duplicate_button_text
   - cria dois botões com texto "Pesquisar";
   - um deve representar pesquisar cliente e outro pesquisar contrato.

4. overlay_blocks_click
   - adiciona overlay bloqueando o clique no botão.

5. disabled_button
   - renderiza o botão em estado disabled.

Crie testes Playwright para cada mutação validando o comportamento esperado da UI.

Critérios de aceite:
- Cada mutação é acionada por query string.
- Cada mutação possui teste específico.
- A mutação overlay_blocks_click não deve ser tratada como falha de locator.
- A mutação disabled_button não deve ser tratada como falha de locator.
- A matriz YAML e a implementação estão coerentes.
```

---

# 4. Sprint 2 — EvidenceCollector e EvidenceStore

## Iteração 2.1 — Implementar EvidenceCollector básico

```text
Implemente o EvidenceCollector básico em src/testforge/evidence/evidence_collector.py.

Objetivo:
Coletar evidências antes e depois de uma ação ou sugestão em shadow mode.

O EvidenceCollector deve coletar:
1. screenshot_before.png;
2. screenshot_after.png;
3. dom_before.html;
4. dom_after.html;
5. ax_tree_before.json, quando disponível;
6. ax_tree_after.json, quando disponível;
7. network_log.json;
8. score_breakdown.json, quando informado;
9. oracle_results.json, quando informado;
10. manifest.json.

Política de dados sensíveis:
- Implementar apenas alerta de possível dado sensível.
- Não mascarar.
- Não remover.
- Não alterar screenshots, DOM, AX tree, network log ou trace.
- O manifest deve conter `sensitive_data_alert` com `policy: alert_only` e `masking_applied: false`.

Critérios de aceite:
- Uma execução sintética gera diretório de evidências.
- O manifest referencia todos os artefatos coletados.
- O manifest contém a política alert_only.
- Nenhum dado é mascarado ou removido.
- Existe teste automatizado ou script demonstrando a coleta contra o fake-react-bank-app.
```

## Iteração 2.2 — Implementar EvidenceStore SQLite

```text
Implemente o EvidenceStore em src/testforge/evidence/evidence_store.py usando SQLite.

Objetivo:
Persistir sugestões de healing, pacotes de evidência, observações de oracle e decisões de revisão.

Tabelas mínimas:
1. healing_suggestion;
2. evidence_package;
3. oracle_observation;
4. review_decision;
5. promotion_decision.

Métodos mínimos:
- init_db()
- insert_healing_suggestion(...)
- insert_evidence_package(...)
- insert_oracle_observation(...)
- insert_review_decision(...)
- insert_promotion_decision(...)
- list_pending_reviews(...)

Critérios de aceite:
- O banco SQLite é criado automaticamente.
- Uma execução sintética insere healing_suggestion.
- Uma execução sintética insere evidence_package.
- Uma execução sintética insere oracle_observation.
- list_pending_reviews retorna sugestões em modo shadow sem revisão.
- Existem testes unitários para os métodos principais.
```

## Iteração 2.3 — Criar query de pendentes de revisão

```text
Crie scripts/sql/pending_reviews.sql.

Objetivo:
Permitir revisão humana inicial sem criar dashboard web.

A query deve retornar:
- healing_suggestion_id;
- created_at;
- application;
- page_signature;
- action_id;
- technology_family;
- taxonomy_code;
- original_locator;
- suggested_locator;
- total_score;
- status;
- screenshot_before;
- screenshot_after;
- manifest_json.

Critérios de aceite:
- A query lista apenas sugestões em mode = shadow.
- A query ignora sugestões já revisadas.
- A query ordena por data mais recente.
- A query é documentada no README.
```

---

# 5. Sprint 3 — Oracles e PromotionGate mínimo

## Iteração 3.1 — Implementar OracleRunner visual_dom

```text
Implemente o OracleRunner com suporte inicial a oracle visual_dom.

Objetivo:
Validar se a UI atingiu um estado esperado após uma ação ou sugestão de healing.

Requisitos:
1. Criar src/testforge/oracle/oracle_runner.py.
2. Suportar oracle tipo visual_dom.
3. O oracle deve validar visibilidade de texto, role ou seletor Playwright.
4. O resultado deve ser `passed`, `failed` ou `inconclusive`.
5. O resultado deve ser persistível em oracle_observation.

Critérios de aceite:
- O fake-react-bank-app permite validar que "Resultado da consulta" aparece.
- O oracle registra expected, actual e result.
- Falha de oracle não deve ser tratada como falha de locator.
- Existe teste sintético cobrindo passed e failed.
```

## Iteração 3.2 — Implementar OracleRunner business_state mínimo

```text
Adicione ao OracleRunner suporte a business_state mínimo.

Objetivo:
Validar que o resultado funcional corresponde à intenção original do passo.

Caso inicial:
- Após pesquisar CPF no fake-react-bank-app, o resultado deve conter o mesmo CPF informado.

Requisitos:
1. O oracle deve receber expected_value.
2. Deve localizar o campo/elemento de resultado.
3. Deve comparar valor exibido com valor esperado.
4. Deve registrar passed, failed ou inconclusive.

Critérios de aceite:
- Quando o CPF exibido é igual ao pesquisado, o oracle passa.
- Quando o CPF exibido diverge, o oracle falha.
- O resultado é persistido em oracle_observation.
- O Evidence Package referencia o resultado do oracle.
```

## Iteração 3.3 — Implementar PromotionGate mínimo

```text
Implemente o PromotionGate mínimo em src/testforge/promotion/promotion_gate.py.

Objetivo:
Bloquear promoções de sugestões de healing sem evidência, sem oracle ou com falso healing.

Estados mínimos:
- experimental;
- shadow_validated;
- rejected.

Bloqueios mínimos:
1. evidence package incompleto;
2. oracle ausente;
3. oracle conflitante;
4. false_heal revisado;
5. uniqueness_score abaixo de 0.85;
6. actionability_score abaixo de 0.95;
7. semantic_gap abaixo de 0.15.

Critérios de aceite:
- O PromotionGate recebe PromotionContext e retorna PromotionDecision.
- A decisão possui allowed true/false.
- A decisão possui lista de razões.
- Sugestão sem evidência completa é bloqueada.
- Sugestão sem oracle é bloqueada.
- Decisão é persistida em promotion_decision.
```

## Iteração 3.4 — Integrar fluxo sintético completo

```text
Integre Synthetic Lab + EvidenceCollector + EvidenceStore + OracleRunner + PromotionGate em um script único.

Nome sugerido:
scripts/run_synthetic_shadow_flow.py

Fluxo esperado:
1. Abrir fake-react-bank-app com uma mutação.
2. Executar ação ou simular falha do locator original.
3. Criar healing_suggestion em modo shadow.
4. Coletar Evidence Package.
5. Rodar oracle visual_dom e business_state quando aplicável.
6. Persistir oracle_observation.
7. Executar PromotionGate.
8. Persistir promotion_decision.
9. Listar sugestão pendente de revisão.

Critérios de aceite:
- O script roda com mutation=change_accessible_name.
- O script gera evidências.
- O script grava no SQLite.
- O script roda pelo menos um oracle.
- O PromotionGate retorna decisão com motivos.
- A sugestão aparece na query de pendentes quando não revisada.
```

---

# 6. Sprint 4 — Modelo Intermediário Semântico e candidatos

## Iteração 4.1 — Definir schema do Semantic Test Case

```text
Defina o schema versionado do Modelo Intermediário Semântico em schemas/semantic_test_case.schema.yaml.

O schema deve conter:
- version;
- kind;
- metadata;
- preconditions;
- steps;
- action_id;
- intent;
- action;
- input;
- target;
- context;
- locator_candidates;
- expected_after_action;
- healing_policy.

Critérios de aceite:
- O schema possui exemplo válido.
- O exemplo representa o fluxo de consulta CPF do fake-react-bank-app.
- O schema não armazena apenas um locator final.
- O schema suporta múltiplos candidatos de locator.
```

## Iteração 4.2 — Implementar SemanticAction e SemanticTarget

```text
Implemente as classes do MIS em src/testforge/semantic/model.py.

Classes mínimas:
- SemanticTestCase;
- SemanticAction;
- SemanticTarget;
- ActionContext;
- LocatorCandidate;
- ExpectedAfterAction.

Critérios de aceite:
- As classes podem ser serializadas para JSON/YAML.
- Um fluxo fake pode ser representado como SemanticTestCase.
- Uma ação click e uma ação fill são suportadas.
- Testes unitários validam serialização e desserialização.
```

## Iteração 4.3 — Implementar LocatorCandidateGenerator

```text
Implemente LocatorCandidateGenerator em src/testforge/locator/candidate_generator.py.

Estratégias mínimas:
- role + accessible name;
- label;
- placeholder;
- test_id;
- visible_text;
- CSS simples como fallback.

Critérios de aceite:
- A partir de um SemanticTarget com role e accessible name, gera candidato role.
- A partir de label, gera candidato label.
- A partir de test_id, gera candidato test_id.
- Cada candidato possui strategy, value, playwright expression e reason.
- XPath absoluto não deve ser gerado no MVP.
```

## Iteração 4.4 — Implementar LocatorScorer inicial

```text
Implemente LocatorScorer em src/testforge/locator/scorer.py.

Score inicial:
- semantic_strength;
- uniqueness;
- stability;
- context_match;
- actionability;
- historical_success;
- simplicity.

Critérios de aceite:
- O score é explicável por breakdown.
- role, label e test_id recebem peso positivo.
- XPath absoluto, nth-child, classe gerada e ID dinâmico são penalizados.
- O score breakdown pode ser persistido no Evidence Package.
```

---

# 7. Sprint 5 — Taxonomia, ShadowValidator e fallback

## Iteração 5.1 — Implementar taxonomia core

```text
Implemente a taxonomia core em src/testforge/taxonomy/taxonomy.py e policies/failure_taxonomy.yaml.

Famílias mínimas:
- locator_resolution;
- actionability;
- synchronization;
- oracle;
- environment;
- context.

Critérios de aceite:
- Cada código possui descrição.
- Cada código possui política allow_healing true/false.
- ACTIONABILITY_OBSCURED não permite locator healing.
- ASSERTION_FAILED não permite locator healing.
- LOCATOR_NOT_FOUND permite fallback/healing.
```

## Iteração 5.2 — Implementar FailureClassifier mínimo

```text
Implemente FailureClassifier em src/testforge/taxonomy/failure_classifier.py.

Objetivo:
Classificar exceções e estados observados em códigos da taxonomia.

Casos mínimos:
- locator não encontrado -> LOCATOR_NOT_FOUND;
- locator ambíguo -> LOCATOR_AMBIGUOUS;
- overlay bloqueando clique -> ACTIONABILITY_OBSCURED;
- botão disabled -> ACTIONABILITY_DISABLED;
- oracle falhou -> ORACLE_FAILED.

Critérios de aceite:
- Cada mutação do fake app é classificada conforme mutation_matrix.yaml.
- Casos de actionability não acionam locator healing.
- O classification result é registrado no Evidence Package.
```

## Iteração 5.3 — Implementar ShadowValidator

```text
Implemente ShadowValidator em src/testforge/shadow/shadow_validator.py.

Objetivo:
Gerar e avaliar sugestão de healing sem aplicar auto-heal.

Fluxo:
1. Receber SemanticAction, falha classificada e snapshot atual.
2. Verificar se taxonomia permite healing.
3. Gerar candidatos.
4. Ranquear candidatos.
5. Calcular uniqueness e actionability quando possível.
6. Registrar ShadowHealingObservation.
7. Não alterar teste original.

Critérios de aceite:
- LOCATOR_NOT_FOUND gera sugestão quando houver candidato.
- ACTIONABILITY_OBSCURED não gera sugestão de troca de locator.
- Sugestão é persistida como mode shadow.
- Sugestão aparece na query de pendentes.
```

## Iteração 5.4 — Implementar fallback determinístico inicial

```text
Implemente DeterministicFallbackRunner em src/testforge/runner/fallback_runner.py.

Objetivo:
Tentar candidatos conhecidos em ordem de score antes de acionar healing.

Critérios de aceite:
- Candidatos são tentados em ordem decrescente de score.
- Candidatos abaixo do threshold mínimo são ignorados.
- Cada tentativa registra outcome.
- A ação só é considerada sucesso se oracle pós-ação passar.
- Não usa LLM.
```

---

# 8. Sprint 6 — Métricas, revisão e preparação para piloto

## Iteração 6.1 — Implementar métricas de false healing e precision

```text
Implemente MetricsRepository em src/testforge/metrics/metrics_repository.py.

Métricas mínimas:
- false_heal_rate;
- precision;
- oracle_precision;
- false_acceptance_rate;
- quarantine_rate;
- llm_escalation_rate.

Critérios de aceite:
- Métricas são calculadas a partir de review_decision e oracle_observation.
- FALSE_HEAL aumenta false_heal_rate.
- TRUE_POSITIVE_HEAL aumenta precision.
- Métricas podem ser consultadas por application, page_signature e action_id.
```

## Iteração 6.2 — Criar CLI simples de revisão

```text
Crie uma CLI simples para revisar sugestões pendentes.

Comando sugerido:
python scripts/review_pending.py

A CLI deve:
1. listar sugestões pendentes;
2. mostrar locator original, sugerido, score, taxonomia e caminhos de evidência;
3. permitir registrar label:
   - TRUE_POSITIVE_HEAL;
   - FALSE_HEAL;
   - NOT_RECOVERABLE;
   - ORACLE_WEAK;
   - TAXONOMY_WRONG;
   - TECHNOLOGY_PROFILE_WRONG;
   - INCONCLUSIVE.

Critérios de aceite:
- A revisão é persistida em review_decision.
- Após revisão, o caso não aparece mais como pendente.
- Métricas são atualizadas.
```

## Iteração 6.3 — Gerar relatório sintético em Markdown

```text
Crie um relatório Markdown de execução sintética.

Comando sugerido:
python scripts/generate_synthetic_report.py

O relatório deve conter:
- total de mutações executadas;
- total de sugestões;
- taxonomias observadas;
- oracles pass/fail/inconclusive;
- pendentes de revisão;
- decisões do PromotionGate;
- false_heal_rate, se houver revisões.

Critérios de aceite:
- O relatório é gerado em reports/synthetic_report.md.
- O relatório referencia evidências por caminho.
- O relatório indica se o MVP-1 está pronto para avançar.
```

---

# 9. Prompt de encerramento da sprint

Use este prompt ao final de cada sprint.

```text
Revise o estado atual do projeto TestForge.

Entregue:
1. Resumo do que foi implementado.
2. Lista de arquivos criados/alterados.
3. Como executar os testes.
4. Critérios de aceite atendidos.
5. Critérios pendentes.
6. Riscos técnicos encontrados.
7. Dívidas técnicas introduzidas.
8. Recomendações para a próxima sprint.
9. Atualização necessária em CHANGELOG, README ou ADR.

Não avance para a próxima sprint se houver critério de aceite crítico pendente.
```

---

# 10. Prompt para gerar épicos/tarefas a partir de uma sprint

```text
Com base no estado atual do projeto TestForge e no plano de épicos/histórias, decomponha a próxima sprint em tarefas técnicas.

Para cada tarefa, informe:
- id;
- história relacionada;
- objetivo;
- arquivos esperados;
- critérios de aceite;
- testes necessários;
- dependências;
- estimativa em pontos ou tamanho P/M/G;
- riscos.

Respeite os princípios:
- determinístico primeiro;
- LLM apenas como curadoria;
- nenhum healing sem evidência;
- nenhuma promoção sem PromotionGate;
- dados sensíveis em modo alert_only no MVP.
```

---

# 11. Prompt para revisar uma implementação feita por LLM

```text
Revise a implementação feita para a última iteração do TestForge.

Verifique:
1. A implementação respeita a separação de responsabilidades?
2. O EvidenceCollector apenas coleta evidências e não decide healing?
3. O EvidenceCollector está em modo alert_only para dados sensíveis, sem mascaramento?
4. O PromotionGate apenas decide promoção e registra motivos?
5. O ShadowValidator não aplica auto-heal?
6. O OracleRunner valida intenção pós-ação?
7. Existem testes ou execução sintética?
8. O banco SQLite registra os dados esperados?
9. A documentação foi atualizada?
10. Alguma decisão arquitetural exige ADR?

Entregue:
- problemas encontrados;
- correções necessárias;
- riscos;
- se a iteração pode ser considerada concluída ou não.
```
