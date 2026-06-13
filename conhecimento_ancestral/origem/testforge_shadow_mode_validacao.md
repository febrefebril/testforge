# TestForge — Shadow Mode, Medição de Falso Healing, Assertions Pós-Ação e Uso da Taxonomia

## 1. Objetivo

Implementar um modo de validação em que o TestForge calcula a cura provável, mas não altera automaticamente o teste nem executa a ação curada como fonte de verdade. O objetivo é medir se o mecanismo de self-healing determinístico está correto antes de liberar auto-heal em produção.

## 2. Shadow Mode

### Conceito

No shadow mode, quando um locator falha:

1. O runner registra a falha real.
2. O healing engine gera candidatos alternativos.
3. O sistema ranqueia os candidatos.
4. O sistema simula/valida o candidato em ambiente controlado.
5. O sistema registra qual cura teria aplicado.
6. O teste continua com o comportamento antigo ou falha normalmente.
7. Um humano ou oracle automático classifica se a cura sugerida estava correta.

### Estados possíveis

- NO_HEAL_NEEDED
- HEAL_SUGGESTED_NOT_APPLIED
- HEAL_SUGGESTED_VALIDATED_BY_ORACLE
- HEAL_REJECTED_BY_ORACLE
- HEAL_REQUIRES_HUMAN_REVIEW
- HEAL_FALSE_POSITIVE
- HEAL_PROMOTED_TO_AUTO

## 3. Medição de falso healing

### Definição

Falso healing ocorre quando o sistema escolhe um elemento alternativo que permite a execução continuar, mas não representa a intenção original do passo.

### Métrica principal

```text
false_heal_rate = false_heals / total_heal_suggestions_reviewed
```

### Métricas auxiliares

```text
precision = true_positive_heals / all_applied_or_suggested_heals
recall = recovered_locator_failures / all_recoverable_locator_failures
llm_escalation_rate = llm_escalations / locator_failures
quarantine_rate = quarantined_heals / heal_suggestions
```

## 4. Validação da assertividade pós-ação

Toda cura precisa ser validada por oráculos pós-ação. A validação deve combinar pelo menos uma das seguintes famílias:

1. Estado visual esperado.
2. Mudança de URL ou rota.
3. Resposta de rede esperada.
4. Alteração de DOM/a11y tree.
5. Mudança de valor em campo.
6. Mensagem de sucesso/erro esperada.
7. Estado de negócio consultável via API ou banco de teste.

## 5. Uso da taxonomia de falhas

A taxonomia entra no roteamento da decisão. Antes de tentar healing, o TestForge precisa classificar a falha.

### Exemplo de roteamento

- LOCATOR_NOT_FOUND -> fallback/healing.
- LOCATOR_AMBIGUOUS -> refinamento contextual.
- ACTIONABILITY_OBSCURED -> wait/overlay/spinner policy.
- ACTIONABILITY_DISABLED -> regra de estado ou massa de dados.
- ASSERTION_FAILED -> provável bug, dado inválido ou oráculo incorreto.
- NETWORK_FAILURE -> sincronização, backend ou ambiente.
- AUTHORIZATION_FAILURE -> perfil/permissão.
- TEST_DATA_FAILURE -> massa de dados.
- FRAME_OR_SHADOW_CONTEXT_FAILURE -> tecnologia/contexto.

## 6. Famílias tecnológicas

A tecnologia da tela ajusta os pesos do ranking e as estratégias de fallback.

### Exemplos

- Web tradicional/server-side: ids e names podem ser mais estáveis.
- React/Angular/Vue: classes e ids gerados devem ser penalizados.
- PrimeFaces/JSF: ids podem ser compostos e parcialmente previsíveis.
- Shadow DOM: precisa atravessar boundary de componente.
- Iframe: precisa resolver frame antes do locator.
- Design systems com data-testid: test id deve receber alto peso.

## 7. O que reaproveitar

Reaproveitar:

- taxonomia de falhas;
- modelo intermediário semântico;
- ranking de locators;
- histórico de sucesso/falha;
- evidence package;
- prompts de curadoria LLM;
- relatórios Allure/trace;
- contratos YAML/JSON já definidos.

Não reaproveitar como núcleo:

- prompts grandes que tentam resolver tudo;
- regras específicas hardcoded no runner;
- gravação que gera script final sem modelo intermediário;
- healing sem assertion pós-ação.

## 8. Critério para sair do shadow mode

Liberar auto-heal apenas quando:

- pelo menos 100 sugestões revisadas;
- false_heal_rate < 2%;
- precision >= 95%;
- LLM escalation rate < 10%;
- nenhum falso healing crítico nos últimos N ciclos;
- todos os heals promovidos possuem evidência e assertion pós-ação.
