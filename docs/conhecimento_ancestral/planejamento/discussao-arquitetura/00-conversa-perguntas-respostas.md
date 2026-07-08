# TestForge — Perguntas e Respostas Consolidadas da Discussão

## 1. Problema inicial: a fragilidade mudou de lugar

### Pergunta do Andre

O TestForge começou tentando resolver tudo pelo gravador: identificar tecnologias e gerar script robusto. Depois a responsabilidade foi para o runner. Depois criamos self-healing via LLM, mas o problema virou o prompt. Como resolver a arquitetura para gravar testes que não quebrem logo após a gravação e que nasçam com self-healing determinístico, usando LLM apenas para curadoria?

### Resposta consolidada

A conclusão foi que o problema era arquitetural. Cada camada estava recebendo a responsabilidade de inferir intenção e corrigir fragilidade. A solução proposta foi separar responsabilidades:

```text
Recorder Sensorial
  -> Modelo Intermediário Semântico
  -> Compilador Determinístico
  -> Runner
  -> Self-Healing Determinístico
  -> Curadoria LLM
```

O teste não deve nascer como uma sequência de seletores frágeis. Ele deve nascer como um contrato semântico contendo intenção, alvo, contexto, candidatos de locator, critérios de sucesso e evidências.

---

## 2. Modelo Intermediário Semântico

### Pergunta do Andre

Como implementar o modelo intermediário semântico?

### Resposta consolidada

Foi proposto o MIS como camada entre Recorder e Compiler/Runner. O MIS representa cada passo como `SemanticAction`, contendo:

- intenção;
- tipo de ação;
- alvo semântico;
- contexto;
- candidatos de locator;
- assertions pós-ação;
- política de healing.

Componentes principais:

```text
SemanticTestCase
SemanticAction
SemanticTarget
ActionContext
LocatorCandidate
SemanticCompiler
```

Foram gerados arquivos com guia, schema YAML e modelo Python inicial.

---

## 3. Candidatos de locators, ranking e fallback determinístico

### Pergunta do Andre

Como gerar candidatos de locators automaticamente? Como funciona o ranking de score de locators? Como implementar fallback determinístico?

### Resposta consolidada

Foi proposta a separação em três motores:

```text
LocatorCandidateGenerator
LocatorScorer
DeterministicFallbackRunner
```

A ordem recomendada de geração de candidatos:

```text
role + accessible name
label
placeholder
test id
texto visível
atributos estáveis
locator contextual
CSS simples
XPath relativo
```

A fórmula inicial de score proposta:

```text
score =
  0.25 * semantic_strength +
  0.20 * uniqueness +
  0.15 * stability +
  0.15 * context_match +
  0.10 * action_compatibility +
  0.10 * historical_success +
  0.05 * simplicity
```

O fallback determinístico deve tentar candidatos em ordem de score, validar unicidade, actionability e assertion pós-ação, e só considerar sucesso se a intenção for comprovada.

---

## 4. Uniqueness, actionability, histórico e validação da arquitetura

### Pergunta do Andre

Como calcular score de uniqueness? Como validar actionability de um locator? Como persistir histórico de sucesso? O que ainda não estamos vendo? Como saber se o plano realmente vai funcionar?

### Resposta consolidada

O score de uniqueness não deve ser apenas `count == 1`. Foi proposta fórmula:

```text
uniqueness_score =
  0.40 * cardinality_score +
  0.25 * context_uniqueness_score +
  0.20 * semantic_gap_score +
  0.15 * cross_snapshot_stability_score
```

A actionability deve validar se o elemento pode receber a ação, mas actionability não é sucesso. Sucesso exige oracle pós-ação.

O histórico deve ser persistido em SQLite/PostgreSQL, usando métricas conservadoras como Wilson lower bound, evitando promover locator por poucas execuções.

Foi destacada a necessidade de validação científica com hipóteses, gold set, mutações sintéticas, shadow mode e kill criteria.

---

## 5. Shadow mode, falso healing e taxonomia

### Pergunta do Andre

Como implementar shadow mode na prática? Como medir falso healing em testes reais? Como validar assertividade pós-ação? Onde entra a taxonomia das falhas, famílias de erros e tecnologias? O que reaproveitar do que já foi feito?

### Resposta consolidada

Shadow mode foi definido como modo em que o TestForge calcula a cura provável, mas não aplica automaticamente. Ele registra a sugestão, evidências, oracles e revisão.

Falso healing foi definido como quando o sistema escolhe um elemento alternativo que permite o teste continuar, mas não representa a intenção original.

Métricas propostas:

```text
false_heal_rate
precision
recall
quarantine_rate
llm_escalation_rate
```

A taxonomia entra antes do healing, classificando se a falha é de locator, actionability, sincronização, dado, ambiente, permissão, iframe, shadow DOM etc. Nem toda falha deve acionar healing.

Foi decidido reaproveitar taxonomia, MIS, ranking, histórico, evidence package, prompts de curadoria e relatórios, mas reorganizados em papéis mais claros.

---

## 6. Experimento de shadow mode e oracle robusto

### Pergunta do Andre

Como estruturar o experimento de shadow mode? Como criar oracle pós-ação robusto? Como adaptar taxonomia para diferentes tecnologias?

### Resposta consolidada

Foi proposto um experimento controlado com hipóteses:

```text
false_heal_rate < 2%
precision >= 95%
LLM escalation < 10%
overhead < 20%
```

O oracle robusto deve combinar sinais:

```text
visual/DOM
URL/rota
rede
valor de campo
mensagem
estado de negócio
API/banco controlado
acessibilidade
```

Para ações críticas, devem existir pelo menos dois oracles, idealmente um técnico e um de negócio.

A taxonomia deve ter núcleo comum e extensões por tecnologia: React, Angular, JSF/PrimeFaces, iframe, shadow DOM e design systems.

---

## 7. React, Angular, precisão do oracle, evidências e sistemas falsos

### Pergunta do Andre

Como adaptar a taxonomia para tecnologias específicas como React ou Angular? Como medir precisão do oracle pós-ação? Como registrar e revisar evidências no shadow mode? Como usar sistemas falsos para testar tudo sem depender dos ambientes CAIXA? Como criar banco de healing durante a implementação?

### Resposta consolidada

Foi proposta taxonomia em duas camadas:

```text
Taxonomia Core + Extensões por Tecnologia
```

Para React:

```text
generated_id_changed
css_in_js_class_changed
component_rerendered
hydration_delay
portal_context_changed
virtualized_list_item_not_mounted
```

Para Angular:

```text
ng_generated_attribute_changed
change_detection_pending
material_overlay_obscured
async_validator_pending
router_navigation_pending
cdk_virtual_scroll_not_rendered
```

O oracle foi tratado como classificador com TP, FP, TN e FN, medindo precision, recall, F1, false acceptance e false rejection.

Foi proposto um Synthetic Lab com apps falsos:

```text
fake-react-bank-app
fake-angular-form-app
fake-jsf-like-legacy-app
fake-iframe-app
fake-shadow-dom-app
fake-design-system-app
```

Cada execução deve alimentar um banco de healing com observações, sugestões, oracles, revisões, detecção tecnológica, mutações e decisões de promoção.

---

## 8. Promotion Gate, mutações sintéticas e evidências automáticas

### Pergunta do Andre

Como implementar o Promotion Gate na prática? Como criar mutações sintéticas controladas? Como registrar evidências automaticamente? O que precisamos decidir para começar o desenvolvimento?

### Resposta consolidada

O Promotion Gate foi definido como componente determinístico que decide se uma sugestão pode evoluir de estado:

```text
experimental -> shadow_validated -> canary -> trusted
```

Ele usa:

```text
evidence_package
oracle_observations
review_decisions
historical_metrics
technology_profile
taxonomy_classification
synthetic_mutation_results
```

Foram definidas mutações sintéticas controladas por query string ou injeção DOM, e evidências automáticas coletadas com screenshots, DOM, accessibility tree, network log, trace, score breakdown e decisão do Promotion Gate.

---

## 9. EvidenceCollector, fake React app e SQLite

### Pergunta do Andre

Como criar EvidenceCollector com Playwright? Como simular falhas sintéticas no fake-react-app? Como registrar evidências no banco SQLite?

### Resposta consolidada

Foi gerado um pacote com:

```text
evidence_collector.py
evidence_store.py
fake_react_bank_app.html
synthetic_failure_demo.py
README.md
```

O EvidenceCollector coleta screenshots, DOM, accessibility tree, network logs, trace, score breakdown, oracle results e manifest.

O fake app permite mutações como:

```text
change_id
change_accessible_name
duplicate_button_text
remove_testid_and_change_text
overlay_blocks_click
disabled_button
delayed_enable
delayed_response
```

O EvidenceStore persiste healing_suggestion, evidence_package, oracle_observation e review_decision no SQLite.

---

## 10. Integração do PromotionGate, queries e plano macro

### Pergunta do Andre

Como integrar PromotionGate nesse fluxo? Como criar query para listar casos pendentes? Como evoluir o slice com novas mutações? É possível criar um plano macro completo?

### Resposta consolidada

Foi gerado pacote com:

```text
promotion_gate.py
promotion_gate_integration.py
evidence_store_extensions.py
pending_reviews.sql
mutation_matrix.yaml
macro_plan.md
integration_guide.md
```

O PromotionGate entra após registrar sugestão, evidência e oracle. A query `pending_reviews.sql` lista casos pendentes de revisão em shadow mode.

Foi criado plano macro em 10 fases:

```text
0. Fundação e decisões
1. Synthetic Lab mínimo
2. EvidenceCollector e banco de conhecimento
3. MIS e candidatos
4. Shadow Mode
5. Oracle pós-ação robusto
6. Promotion Gate
7. Adaptação por tecnologia
8. Aplicação real piloto
9. Canary auto-heal
10. Produto interno e operação contínua
```

---

## 11. Decisão atual sobre dados sensíveis

### Pergunta/ajuste do Andre

Concordo com a recomendação, mas removeria o mascaramento básico de CPF/dados sensíveis no EvidenceCollector. Inicialmente só alertamos a presença de dados sensíveis.

### Resposta consolidada

Decisão incorporada ao pacote: no MVP inicial, o EvidenceCollector não aplica mascaramento automático. Ele deve apenas alertar possível presença de dados sensíveis no Evidence Package.

Política:

```text
alert_only
masking_applied = false
possible_sensitive_data_detected = true/false
```

Essa decisão preserva fidelidade das evidências durante a fase de validação e posterga o mascaramento para governança posterior.
