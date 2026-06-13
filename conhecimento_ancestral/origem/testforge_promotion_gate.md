# TestForge — Promotion Gate, Mutações Sintéticas e Evidências Automáticas

## 1. Decisão arquitetural

O Promotion Gate é o componente responsável por decidir se uma sugestão de healing pode evoluir de experimental para shadow_validated, canary ou trusted.

Ele não gera locator, não executa teste e não chama LLM. Ele apenas avalia evidências, métricas, histórico e regras de governança.

## 2. Estados de promoção

```text
experimental -> shadow_validated -> canary -> trusted -> deprecated/rejected
```

## 3. Entradas do Promotion Gate

- healing_suggestion
- evidence_package
- oracle_observations
- review_decisions
- historical_metrics
- technology_profile
- taxonomy_classification
- synthetic_mutation_results

## 4. Regras mínimas

Uma sugestão só pode ser promovida se:

- possuir evidence package completo;
- possuir oracle pós-ação;
- não possuir conflito entre oracles;
- não possuir revisão humana como falso healing;
- atingir precisão mínima definida;
- manter false acceptance rate abaixo do limite;
- possuir quantidade mínima de observações revisadas;
- passar nos testes sintéticos obrigatórios para a tecnologia/família de erro.

## 5. Mutações sintéticas controladas

O Synthetic Lab deve gerar cenários controlados com resultado esperado conhecido.

Famílias iniciais:

- locator: change_id, change_class, duplicate_text, remove_testid, change_accessible_name;
- actionability: overlay, disabled_button, delayed_enable, animation;
- synchronization: delayed_render, debounce, delayed_response, spinner_timeout;
- react: rerender, portal_modal, virtualized_row;
- angular: material_overlay, async_validator, router_delay;
- iframe: wrong_frame, delayed_frame;
- shadow_dom: slot_change, closed_shadow_root.

## 6. Evidências automáticas

Cada falha elegível e cada sugestão de healing deve coletar automaticamente:

- screenshot antes;
- screenshot depois da tentativa/simulação;
- DOM snapshot antes/depois;
- accessibility tree antes/depois;
- rede associada;
- trace Playwright;
- vídeo opcional;
- score breakdown;
- taxonomy code;
- technology profile;
- decisão do Promotion Gate.

## 7. Decisões necessárias para começar

1. Escopo do primeiro slice vertical.
2. Tecnologia piloto.
3. Formato canônico do Evidence Package.
4. Banco inicial: SQLite ou PostgreSQL.
5. Thresholds iniciais.
6. Labels da revisão humana.
7. Mutações sintéticas mínimas.
8. Critérios de promoção e rejeição.
9. Integração com runner/Allure/trace.
10. Política de uso da LLM.
