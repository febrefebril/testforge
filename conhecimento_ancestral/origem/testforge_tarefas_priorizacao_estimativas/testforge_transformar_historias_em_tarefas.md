# TestForge — Plano de Épicos, Histórias e Critérios de Aceite

## 1. Objetivo

Este plano transforma o plano macro do TestForge em um backlog inicial organizado por épicos e histórias. O objetivo é permitir que o desenvolvimento comece por slices verticais testáveis, mantendo rastreabilidade com a arquitetura definida: Modelo Intermediário Semântico, Synthetic Lab, EvidenceCollector, Shadow Mode, Oracle pós-ação, Promotion Gate e curadoria LLM.

## 2. Princípios de planejamento

1. Cada épico deve entregar uma capacidade verificável.
2. Cada história deve ter critério de aceite objetivo.
3. Nenhuma história de healing deve ser considerada pronta sem evidência e teste sintético.
4. O MVP deve priorizar aprendizado validado, não automação total.
5. O plano macro deve ser versionado como artefato normativo.
6. Mudanças relevantes devem gerar ADR ou registro de decisão.
7. O EvidenceCollector, inicialmente, deve apenas alertar presença potencial de dados sensíveis, sem mascaramento automático.

---

# 3. Épicos propostos

## EP-00 — Fundação do Produto e Governança

### Objetivo

Criar a base mínima para desenvolvimento controlado: repositório, estrutura de módulos, políticas versionadas, plano macro, ADRs e feature flags.

### Histórias

#### US-00.01 — Criar estrutura inicial do repositório

Como desenvolvedor do TestForge, quero uma estrutura inicial de projeto para organizar módulos, políticas, scripts e documentação.

Critérios de aceite:

- O repositório possui diretórios para `docs`, `src`, `tests`, `policies`, `schemas`, `synthetic_lab` e `adrs`.
- Existe um `README.md` com visão geral do projeto.
- Existe um arquivo `VERSION` ou equivalente com a versão inicial do plano.
- Existe um `CHANGELOG.md` inicial.
- Existe pelo menos um ADR registrando a decisão de usar shadow mode antes de auto-heal.

#### US-00.02 — Versionar plano macro como artefato normativo

Como arquiteto do TestForge, quero versionar o plano macro para garantir rastreabilidade das decisões e mudanças.

Critérios de aceite:

- O plano macro está salvo em `docs/plano_macro.md`.
- O plano possui versão, data, status e responsável.
- Alterações relevantes exigem atualização no `CHANGELOG.md`.
- Alterações arquiteturais exigem ADR.
- O plano referencia épicos e histórias derivados dele.

#### US-00.03 — Definir política inicial de dados sensíveis nas evidências

Como responsável pela governança do TestForge, quero registrar a política inicial de dados sensíveis para evitar decisões implícitas no EvidenceCollector.

Critérios de aceite:

- Existe política em `policies/evidence_sensitive_data_policy.yaml`.
- A política define `mode: alert_only`.
- A política define `masking_applied: false`.
- O Evidence Package possui campo para alerta de possível dado sensível.
- Não há mascaramento automático implementado no MVP.

---

## EP-01 — Synthetic Lab Mínimo

### Objetivo

Criar um laboratório sintético para validar falhas controladas antes de depender de ambientes reais.

### Histórias

#### US-01.01 — Criar fake-react-bank-app

Como desenvolvedor do TestForge, quero uma aplicação fake React-like para simular fluxos bancários simples e falhas controladas.

Critérios de aceite:

- A aplicação fake possui um fluxo de consulta por CPF.
- A aplicação possui botão de pesquisa, campo CPF e área de resultado.
- O resultado exibe o CPF informado.
- A aplicação pode ser executada localmente sem backend real.
- A aplicação suporta mutações via query string.

#### US-01.02 — Implementar mutação `change_id`

Como desenvolvedor do Synthetic Lab, quero alterar o ID de um elemento para validar se o TestForge não depende de ID frágil.

Critérios de aceite:

- A mutação é acionada por `?mutation=change_id`.
- O ID do botão muda.
- A intenção funcional da tela permanece igual.
- A taxonomia esperada é `LOCATOR_NOT_FOUND` ou equivalente específico.
- A mutação é registrada na matriz de mutações.

#### US-01.03 — Implementar mutação `duplicate_button_text`

Como desenvolvedor do Synthetic Lab, quero duplicar textos de botões para validar tratamento de ambiguidade.

Critérios de aceite:

- A mutação é acionada por `?mutation=duplicate_button_text`.
- Existem pelo menos dois botões com o mesmo texto visível.
- A taxonomia esperada é `LOCATOR_AMBIGUOUS`.
- O caso é marcado como recuperável por refinamento contextual.
- O resultado esperado está descrito em `mutation_matrix.yaml`.

#### US-01.04 — Implementar mutação `overlay_blocks_click`

Como desenvolvedor do Synthetic Lab, quero simular overlay bloqueando clique para validar que actionability não seja tratada como falha de locator.

Critérios de aceite:

- A mutação é acionada por `?mutation=overlay_blocks_click`.
- Um overlay bloqueia a interação com o botão.
- A taxonomia esperada é `ACTIONABILITY_OBSCURED`.
- O caso é marcado como não recuperável por locator healing.
- O sistema não sugere troca de locator como solução primária.

#### US-01.05 — Criar matriz de mutações sintéticas

Como QA/engenheiro de plataforma, quero uma matriz declarativa de mutações para saber o comportamento esperado de cada caso sintético.

Critérios de aceite:

- Existe `synthetic_lab/mutation_matrix.yaml`.
- Cada mutação possui código, tecnologia, taxonomia esperada, recoverable esperado, estratégia esperada e oracles esperados.
- O runner consegue carregar a matriz.
- Mutações sem expectativa definida falham no pipeline sintético.

---

## EP-02 — EvidenceCollector e EvidenceStore

### Objetivo

Coletar e persistir evidências automaticamente para cada falha, sugestão de healing e validação em shadow mode.

### Histórias

#### US-02.01 — Implementar EvidenceCollector básico com Playwright

Como executor do TestForge, quero coletar evidências antes e depois de uma tentativa de ação para permitir auditoria e revisão.

Critérios de aceite:

- Coleta screenshot antes e depois.
- Coleta DOM antes e depois.
- Tenta coletar accessibility tree antes e depois.
- Coleta network log básico.
- Gera `manifest.json`.
- Gera alerta de possível dado sensível em modo `alert_only`.
- Não aplica mascaramento automático.

#### US-02.02 — Persistir evidências em SQLite

Como plataforma TestForge, quero persistir referências das evidências em SQLite para consulta e revisão posterior.

Critérios de aceite:

- Existe tabela `healing_suggestion`.
- Existe tabela `evidence_package`.
- Existe tabela `oracle_observation`.
- Existe tabela `review_decision`.
- Uma execução sintética grava pelo menos uma sugestão e seu pacote de evidências.

#### US-02.03 — Criar query de casos pendentes de revisão

Como revisor, quero listar sugestões pendentes para decidir se uma cura é correta, falsa ou inconclusiva.

Critérios de aceite:

- Existe query `pending_reviews.sql`.
- A query lista sugestões em modo shadow sem revisão.
- A query retorna locator original, locator sugerido, score, taxonomia, tecnologia e caminhos de evidência.
- A query permite ordenar por data mais recente.

---

## EP-03 — Modelo Intermediário Semântico

### Objetivo

Representar a gravação como intenção, alvo semântico, contexto e candidatos, evitando que o script nasça acoplado a seletores frágeis.

### Histórias

#### US-03.01 — Definir schema do Semantic Test Case

Como arquiteto do TestForge, quero um schema versionado para o Modelo Intermediário Semântico.

Critérios de aceite:

- Existe schema YAML ou JSON em `schemas/semantic_test_case.schema.yaml`.
- O schema possui versão.
- O schema define metadata, preconditions, steps, target, context, locator_candidates e expected_after_action.
- O schema possui exemplo válido.

#### US-03.02 — Converter RawRecordedEvent para SemanticAction

Como desenvolvedor do recorder, quero converter eventos brutos em ações semânticas para preservar intenção e contexto.

Critérios de aceite:

- Um evento de click vira `SemanticAction`.
- Um evento de fill vira `SemanticAction`.
- A ação preserva role, accessible name, label, texto visível, atributos e contexto.
- A conversão não escolhe locator definitivo.

#### US-03.03 — Gerar candidatos de locator a partir do SemanticTarget

Como compilador do TestForge, quero gerar múltiplos candidatos para cada alvo semântico.

Critérios de aceite:

- Gera candidato por role quando houver role e accessible name.
- Gera candidato por label quando houver label.
- Gera candidato por test id quando houver test id.
- Gera candidato textual quando houver texto visível.
- Gera candidato CSS apenas como fallback.
- Todos os candidatos possuem razão e estratégia.

---

## EP-04 — Ranking, Uniqueness e Fallback Determinístico

### Objetivo

Ranquear candidatos de locator de forma explicável e executar fallback determinístico sem LLM.

### Histórias

#### US-04.01 — Implementar LocatorScorer determinístico

Como runtime do TestForge, quero ranquear candidatos com base em semântica, unicidade, estabilidade, contexto, actionability e histórico.

Critérios de aceite:

- O score final é explicável por componentes.
- O score penaliza XPath absoluto, `nth-child`, classe gerada e ID dinâmico.
- O score favorece role, label e test id.
- O score é persistido no Evidence Package.

#### US-04.02 — Calcular uniqueness score

Como runtime do TestForge, quero medir unicidade de locator para evitar candidatos ambíguos.

Critérios de aceite:

- O cálculo considera cardinalidade.
- O cálculo considera unicidade dentro do contexto esperado.
- O cálculo considera semantic gap.
- O cálculo considera estabilidade entre snapshots quando disponível.
- Locators ambíguos são enviados para refinamento ou quarentena.

#### US-04.03 — Validar actionability por tipo de ação

Como runner, quero validar se o elemento está pronto para a ação antes de interagir.

Critérios de aceite:

- Para click, valida visibilidade, enabled e trial click quando aplicável.
- Para fill, valida visibilidade, enabled e editable.
- Para select, valida compatibilidade com select ou combobox.
- Actionability failure não é classificada automaticamente como locator failure.

#### US-04.04 — Executar fallback determinístico

Como runner, quero tentar candidatos em ordem de score antes de acionar healing.

Critérios de aceite:

- Candidatos são tentados em ordem decrescente de score.
- Candidatos abaixo do threshold mínimo são ignorados.
- Cada tentativa registra sucesso ou falha.
- A ação só é considerada bem-sucedida se o oracle pós-ação passar.

---

## EP-05 — Taxonomia e Classificação de Falhas

### Objetivo

Classificar falhas antes de decidir se healing é permitido.

### Histórias

#### US-05.01 — Implementar taxonomia core

Como TestForge, quero classificar falhas universais para evitar acionar healing indevidamente.

Critérios de aceite:

- Taxonomia contém famílias locator_resolution, actionability, synchronization, oracle, environment e context.
- Cada família possui códigos documentados.
- Cada código possui política de recuperação.
- Falhas de assertion, dado ou ambiente não acionam locator healing automaticamente.

#### US-05.02 — Criar TaxonomyRouter

Como runtime, quero rotear falhas para estratégia adequada.

Critérios de aceite:

- `LOCATOR_NOT_FOUND` permite fallback/healing.
- `LOCATOR_AMBIGUOUS` permite refinamento contextual.
- `ACTIONABILITY_OBSCURED` aciona política de overlay/wait.
- `ASSERTION_FAILED` não aciona healing de locator.
- O roteamento é registrado no Evidence Package.

#### US-05.03 — Adicionar extensão React

Como TestForge, quero tratar falhas específicas de React.

Critérios de aceite:

- Existe extensão React versionada.
- Classes CSS-in-JS são penalizadas.
- IDs gerados são penalizados.
- Test id, role e accessible name são favorecidos.
- Casos de portal/modal e virtualização são classificados quando detectáveis.

#### US-05.04 — Adicionar extensão Angular

Como TestForge, quero tratar falhas específicas de Angular.

Critérios de aceite:

- Existe extensão Angular versionada.
- `_ngcontent` e `ng-reflect` são penalizados.
- Angular Material overlay é classificado como actionability/contexto, não locator.
- Async validator e router pending são classificados como sincronização.

---

## EP-06 — Shadow Mode

### Objetivo

Sugerir cura sem aplicar automaticamente, medindo precisão e falso healing.

### Histórias

#### US-06.01 — Criar ShadowHealingObservation

Como TestForge, quero registrar cada sugestão de cura em modo shadow para auditoria.

Critérios de aceite:

- A observação possui run_id, action_id, taxonomia, tecnologia, locator original, candidato sugerido, scores e oracles.
- A observação possui status de revisão.
- A observação referencia o Evidence Package.

#### US-06.02 — Implementar ShadowValidator

Como runtime, quero avaliar candidato de healing sem promovê-lo automaticamente.

Critérios de aceite:

- O candidato é gerado e ranqueado.
- O candidato é validado quanto a uniqueness e actionability.
- O resultado é registrado como sugestão, não como auto-heal.
- A sugestão aparece na fila de revisão.

#### US-06.03 — Medir falso healing

Como equipe do TestForge, quero medir falso healing para decidir se a arquitetura merece confiança.

Critérios de aceite:

- Existe métrica `false_heal_rate`.
- Existe métrica `precision`.
- Revisões humanas alimentam as métricas.
- O Promotion Gate bloqueia promoção quando falso healing ultrapassa limite.

---

## EP-07 — Oracle Pós-Ação

### Objetivo

Validar que a intenção original foi cumprida após ação ou sugestão de healing.

### Histórias

#### US-07.01 — Implementar oracle visual/DOM

Como TestForge, quero validar que elementos esperados aparecem ou mudam após a ação.

Critérios de aceite:

- O oracle valida visibilidade de elemento esperado.
- O oracle registra resultado `passed`, `failed` ou `inconclusive`.
- O resultado é persistido em `oracle_observation`.

#### US-07.02 — Implementar oracle de valor de campo

Como TestForge, quero validar que campos receberam o valor esperado.

Critérios de aceite:

- O oracle valida valor de input/select/checkbox.
- O oracle registra esperado, atual e resultado.
- O oracle pode ser usado para ações `fill`, `select` e `check`.

#### US-07.03 — Implementar oracle de negócio mínimo

Como TestForge, quero validar que o resultado da tela corresponde ao dado usado.

Critérios de aceite:

- O oracle valida, no fake app, que o CPF exibido corresponde ao CPF pesquisado.
- O oracle é obrigatório para promoção de ação crítica no fluxo sintético.
- Falha nesse oracle impede promoção.

#### US-07.04 — Medir precisão do oracle

Como arquiteto do TestForge, quero medir se o oracle aprova ou rejeita corretamente sugestões de healing.

Critérios de aceite:

- O sistema registra TP, FP, TN e FN quando houver revisão.
- Calcula precision, recall e false_acceptance_rate.
- Oracle com false_acceptance_rate acima do limite não pode promover healing.

---

## EP-08 — Promotion Gate

### Objetivo

Governar a evolução de sugestões de healing entre estados.

### Histórias

#### US-08.01 — Implementar estados de promoção

Como plataforma TestForge, quero controlar o ciclo de vida de uma sugestão de healing.

Critérios de aceite:

- Estados suportados: experimental, shadow_validated, canary, trusted, rejected e deprecated.
- A transição é registrada em `promotion_decision`.
- Toda decisão possui lista de motivos.

#### US-08.02 — Bloquear promoção sem evidência completa

Como Promotion Gate, quero impedir promoção sem evidence package completo.

Critérios de aceite:

- Falta de screenshot bloqueia promoção.
- Falta de DOM bloqueia promoção.
- Falta de oracle bloqueia promoção.
- Falta de score breakdown bloqueia promoção.
- O motivo do bloqueio é registrado.

#### US-08.03 — Bloquear promoção por falso healing

Como Promotion Gate, quero impedir promoção quando houver falso healing revisado.

Critérios de aceite:

- Revisão `FALSE_HEAL` bloqueia promoção.
- `false_heal_rate >= 2%` bloqueia promoção.
- Falso healing crítico bloqueia promoção independentemente da taxa.

#### US-08.04 — Integrar PromotionGate ao fluxo do shadow mode

Como runtime, quero executar o Promotion Gate ao final do fluxo de shadow para registrar decisão preliminar.

Critérios de aceite:

- Após registrar evidência e oracle, o gate é chamado.
- A decisão é persistida.
- O status da sugestão é atualizado quando permitido.
- Sugestões bloqueadas permanecem pendentes ou rejeitadas com motivos.

---

## EP-09 — Curadoria LLM Controlada

### Objetivo

Usar LLM apenas para curadoria de casos inconclusivos, nunca como mecanismo principal de healing.

### Histórias

#### US-09.01 — Definir contrato de entrada da LLM

Como TestForge, quero enviar para LLM apenas evidence package estruturado, sem prompts genéricos de correção.

Critérios de aceite:

- Entrada possui taxonomia, candidatos, scores, DOM/AX resumido e oracles.
- Entrada não pede execução direta de ação.
- Entrada solicita classificação, justificativa ou proposta de regra.

#### US-09.02 — Registrar proposta da LLM como curadoria

Como TestForge, quero registrar resposta da LLM como proposta sujeita à revisão.

Critérios de aceite:

- Resposta da LLM não promove healing automaticamente.
- Resposta é persistida como curadoria.
- Reviewer humano pode aceitar, rejeitar ou marcar inconclusiva.

---

## EP-10 — Piloto Real e Canary

### Objetivo

Aplicar o sistema em fluxo real controlado após validação sintética.

### Histórias

#### US-10.01 — Selecionar fluxos reais piloto

Como equipe TestForge, quero selecionar fluxos reais de baixo risco para shadow mode.

Critérios de aceite:

- Existem 5 fluxos candidatos documentados.
- Cada fluxo possui massa de teste definida.
- Cada fluxo possui oracles mínimos definidos.
- Execução inicial é shadow mode only.

#### US-10.02 — Rodar shadow mode em piloto real

Como equipe TestForge, quero medir desempenho em ambiente real antes de auto-heal.

Critérios de aceite:

- São registradas sugestões de healing em banco.
- Revisões humanas são registradas.
- Métricas false_heal_rate, precision e LLM escalation são calculadas.
- Auto-heal permanece desligado.

#### US-10.03 — Habilitar canary controlado

Como equipe TestForge, quero habilitar auto-heal apenas em allowlist após aprovação.

Critérios de aceite:

- Existe feature flag para auto-heal.
- Existe rollback.
- Apenas fluxos allowlist usam auto-heal.
- Toda cura aplicada gera evidência e revisão posterior.

---

# 4. Como registrar critérios de aceite

## 4.1 Regra geral

Todo critério de aceite deve ser:

- verificável;
- objetivo;
- rastreável;
- automatizável sempre que possível;
- conectado a evidência quando envolver healing.

## 4.2 Template recomendado

```markdown
## US-XX.YY — Título da história

Como [persona], quero [capacidade], para [benefício].

### Contexto

[Explique o problema ou decisão relacionada.]

### Critérios de aceite

- Dado [estado inicial], quando [ação], então [resultado esperado].
- Dado [falha/condição], quando [sistema processa], então [decisão esperada].
- A execução deve registrar [evidência obrigatória].
- A execução deve persistir [registro no banco].
- A história só é aceita se [teste automatizado/manual/revisão] passar.

### Evidências obrigatórias

- Screenshot
- DOM snapshot
- AX snapshot, quando disponível
- Network log, quando aplicável
- Registro SQLite
- Resultado de oracle

### Fora de escopo

- [Liste explicitamente o que não será feito.]
```

## 4.3 Exemplo concreto

```markdown
## US-06.02 — Implementar ShadowValidator

Como runtime, quero avaliar candidato de healing sem aplicá-lo automaticamente.

### Critérios de aceite

- Dado um locator original quebrado, quando o ShadowValidator for executado, então deve gerar ao menos um candidato ou registrar motivo de ausência.
- Dado um candidato com score abaixo do threshold, quando avaliado, então deve ser marcado como rejeitado ou quarentena.
- Dado um candidato válido, quando avaliado, então deve registrar uniqueness, actionability, score e taxonomia.
- A sugestão não pode alterar o teste original.
- A sugestão deve aparecer na query de pendentes.
- O Evidence Package deve conter screenshot, DOM, AX snapshot, score breakdown e oracle result quando aplicável.
```

---

# 5. Como versionar o plano macro

## 5.1 Estratégia recomendada

Tratar o plano macro como artefato normativo versionado.

Arquivos recomendados:

```text
docs/plano_macro.md
docs/backlog_epicos_historias.md
CHANGELOG.md
VERSION
adrs/ADR-0001-shadow-mode-before-auto-heal.md
policies/promotion_gate_policy.yaml
policies/evidence_sensitive_data_policy.yaml
schemas/semantic_test_case.schema.yaml
```

## 5.2 Versionamento semântico do plano

Usar versão no formato:

```text
MAJOR.MINOR.PATCH
```

Sugestão:

```text
0.1.0 — plano inicial consolidado
0.2.0 — épicos e histórias adicionados
0.3.0 — critérios de aceite e policies versionadas
1.0.0 — plano aprovado para MVP
```

Regras:

```text
MAJOR: muda premissas arquiteturais ou governança central.
MINOR: adiciona épicos, fases, políticas ou fluxos relevantes.
PATCH: corrige texto, nomes, critérios sem mudar escopo.
```

## 5.3 Cabeçalho do plano macro

Todo plano macro deve iniciar com metadados:

```yaml
artifact: TestForge Plano Macro
version: 0.2.0
status: draft
owner: Andre Perotti Netto
date: 2026-06-12
source_of_truth: docs/plano_macro.md
related_adrs:
  - ADR-0001-shadow-mode-before-auto-heal
  - ADR-0002-evidence-alert-only-sensitive-data
```

## 5.4 Changelog

Exemplo:

```markdown
# Changelog

## [0.2.0] - 2026-06-12

### Added

- Plano de épicos e histórias.
- Critérios de aceite por épico.
- Política de versionamento do plano macro.

### Changed

- Política do EvidenceCollector alterada para alert-only para dados sensíveis.

### Removed

- Mascaramento automático de CPF/dados sensíveis no MVP.
```

## 5.5 ADRs obrigatórios

Criar ADR sempre que houver decisão que afete arquitetura, governança ou risco.

ADRs iniciais recomendados:

```text
ADR-0001 — Usar shadow mode antes de auto-heal.
ADR-0002 — EvidenceCollector em modo alert-only para dados sensíveis.
ADR-0003 — Usar Synthetic Lab antes de piloto real.
ADR-0004 — Promotion Gate obrigatório para promoção de healing.
ADR-0005 — LLM apenas como curadoria, não como mecanismo principal.
```

## 5.6 Estados do plano

```text
draft
review
approved
superseded
deprecated
```

## 5.7 Regra de governança

Nenhuma mudança de épico ou critério crítico deve ser feita apenas no chat. A mudança precisa entrar em:

```text
plano macro versionado
backlog versionado
CHANGELOG
ADR, se alterar decisão arquitetural
```
