# TestForge — Plano de Experimento de Shadow Mode, Oracle Pós-Ação e Taxonomia por Tecnologia

## 1. Objetivo do experimento

Validar, antes do auto-healing em produção, se o TestForge consegue sugerir curas corretas para falhas de locator sem introduzir falso healing.

## 2. Hipóteses

- H1: O shadow mode identifica corretamente curas para falhas reais de locator.
- H2: A taxa de falso healing fica abaixo de 2%.
- H3: Pelo menos 70% das falhas recuperáveis de locator recebem sugestão correta.
- H4: Menos de 10% dos casos precisam de LLM.
- H5: O custo de execução adicional fica abaixo de 20%.

## 3. Escopo inicial

- Aplicação: SIOPI ou aplicação piloto equivalente.
- Fluxos: 5 a 10 fluxos reais.
- Massa: 3 variações por fluxo.
- Perfis: pelo menos 2 perfis de usuário.
- Viewports: desktop padrão e resolução alternativa.
- Execuções mínimas: 100 observações de healing sugerido antes de qualquer promoção para auto-heal.

## 4. Modos de execução

### Baseline

Executa o teste atual, sem MIS, sem fallback e sem healing.

### Candidate Mode

Executa teste gerado com MIS e ranking de locators, mas sem healing.

### Shadow Mode

Quando há falha elegível para healing, o TestForge gera candidato de cura, valida por oracle, registra evidências, mas não altera automaticamente o teste.

### Auto-Heal Canary

Apenas depois do shadow mode aprovado. Auto-heal liberado para poucos fluxos, baixo risco e com rollback.

## 5. Métricas obrigatórias

- pass_rate
- locator_failure_rate
- recoverable_locator_failure_rate
- heal_suggestion_rate
- true_positive_heal_rate
- false_heal_rate
- quarantine_rate
- llm_escalation_rate
- mean_extra_runtime_percent
- post_action_oracle_pass_rate
- human_review_agreement_rate

## 6. Critérios de aprovação

- false_heal_rate < 2%
- precision >= 95%
- llm_escalation_rate < 10%
- post_action_oracle presente em 100% das sugestões promovíveis
- evidência completa em 100% das sugestões
- nenhum falso healing crítico nos últimos 30 casos revisados

## 7. Critérios de parada

- false_heal_rate >= 2%
- falso healing crítico identificado
- mais de 20% de aumento médio de tempo de execução
- mais de 20% de acionamento de LLM
- curas sem evidence package
- curas sem oracle pós-ação

## 8. Oracle pós-ação robusto

Cada passo relevante deve possuir pelo menos dois oráculos, sendo idealmente um técnico e um de negócio.

Famílias:

1. Visual/DOM
2. URL/Rota
3. Rede
4. Valor de campo
5. Mensagem de sistema
6. Estado de negócio
7. Banco/API controlada de teste
8. Acessibilidade/estrutura semântica

## 9. Taxonomia adaptável por tecnologia

A taxonomia deve ter núcleo comum e extensões por tecnologia.

Núcleo comum:

- LOCATOR_NOT_FOUND
- LOCATOR_AMBIGUOUS
- ACTIONABILITY_NOT_VISIBLE
- ACTIONABILITY_DISABLED
- ACTIONABILITY_OBSCURED
- ASSERTION_FAILED
- NETWORK_FAILURE
- AUTHORIZATION_FAILURE
- TEST_DATA_FAILURE
- FRAME_CONTEXT_FAILURE
- SHADOW_DOM_CONTEXT_FAILURE
- TECHNOLOGY_SPECIFIC_FAILURE

Extensões:

- React/Angular/Vue: generated_id, virtual_dom_rerender, hydration_delay
- JSF/PrimeFaces: naming_container_id_changed, ajax_update_partial, component_overlay
- Iframe: wrong_frame, frame_not_loaded, cross_origin_frame
- Shadow DOM: shadow_root_closed, slot_projection_changed
- Design System: missing_testid, duplicate_accessible_name, component_state_not_ready

## 10. Próximo passo recomendado

Implementar o experimento como feature flag:

```yaml
healing:
  mode: shadow
  auto_apply: false
  require_post_action_oracle: true
  require_evidence_package: true
  thresholds:
    auto_candidate: 0.90
    quarantine: 0.75
    reject: 0.60
```
