# TestForge — Taxonomia por Tecnologia, Oracle Pós-Ação, Evidências em Shadow Mode e Laboratório Sintético

## 1. Objetivo

Definir como o TestForge deve evoluir o self-healing de forma segura durante o desenvolvimento, sem depender exclusivamente dos ambientes reais da CAIXA.

Este documento cobre:

1. adaptação da taxonomia para React, Angular e outras tecnologias;
2. medição da precisão do oracle pós-ação;
3. registro e revisão de evidências no shadow mode;
4. uso de sistemas falsos/sintéticos para gerar casos controlados;
5. criação progressiva de um banco de dados de healing desde a implementação.

---

## 2. Taxonomia adaptada por tecnologia

A taxonomia deve ter duas camadas:

```text
Taxonomia Core
    +
Extensões por Tecnologia
```

A taxonomia core classifica falhas universais. As extensões por tecnologia refinam a causa raiz, ajustam pesos de ranking e definem estratégias específicas de recuperação.

### 2.1 Taxonomia Core

```yaml
core_taxonomy:
  locator_resolution:
    - LOCATOR_NOT_FOUND
    - LOCATOR_AMBIGUOUS
    - LOCATOR_WRONG_CONTEXT
    - LOCATOR_STALE_OR_DETACHED

  actionability:
    - ACTIONABILITY_NOT_VISIBLE
    - ACTIONABILITY_DISABLED
    - ACTIONABILITY_OBSCURED
    - ACTIONABILITY_NOT_EDITABLE
    - ACTIONABILITY_UNSTABLE

  synchronization:
    - PAGE_NOT_READY
    - ASYNC_RENDER_PENDING
    - NETWORK_IDLE_TIMEOUT
    - SPINNER_TIMEOUT
    - DEBOUNCE_PENDING

  oracle:
    - ORACLE_MISSING
    - ORACLE_WEAK
    - ORACLE_CONFLICT
    - ORACLE_FAILED

  environment:
    - NETWORK_FAILURE
    - BACKEND_FAILURE
    - AUTHORIZATION_FAILURE
    - SESSION_EXPIRED
    - TEST_DATA_FAILURE

  context:
    - FRAME_CONTEXT_FAILURE
    - SHADOW_DOM_CONTEXT_FAILURE
    - POPUP_OR_TAB_CONTEXT_FAILURE
```

### 2.2 Extensão React

```yaml
react_extension:
  technology_hints:
    - "__REACT_DEVTOOLS_GLOBAL_HOOK__"
    - "data-reactroot"
    - "id/class gerados por CSS-in-JS"

  failure_codes:
    - REACT_GENERATED_ID_CHANGED
    - REACT_CSS_IN_JS_CLASS_CHANGED
    - REACT_COMPONENT_RERENDERED
    - REACT_HYDRATION_DELAY
    - REACT_PORTAL_CONTEXT_CHANGED
    - REACT_VIRTUALIZED_LIST_ITEM_NOT_MOUNTED

  locator_policy:
    prefer:
      - role
      - accessible_name
      - label
      - test_id
      - stable_text_with_context
    penalize:
      - generated_id
      - css_in_js_class
      - nth_child
      - absolute_xpath
```

### 2.3 Extensão Angular

```yaml
angular_extension:
  technology_hints:
    - "ng-version"
    - "_ngcontent"
    - "ng-reflect"
    - "cdk-overlay-container"
    - "mat-"

  failure_codes:
    - ANGULAR_NG_GENERATED_ATTRIBUTE_CHANGED
    - ANGULAR_CHANGE_DETECTION_PENDING
    - ANGULAR_MATERIAL_OVERLAY_OBSCURED
    - ANGULAR_ASYNC_VALIDATOR_PENDING
    - ANGULAR_ROUTER_NAVIGATION_PENDING
    - ANGULAR_CDK_VIRTUAL_SCROLL_NOT_RENDERED

  locator_policy:
    prefer:
      - role
      - label
      - test_id
      - form_control_name
      - aria_label
    penalize:
      - _ngcontent
      - ng_reflect
      - material_internal_class
      - absolute_xpath
```

---

## 3. Precisão do oracle pós-ação

O oracle pós-ação deve ser tratado como um classificador. Portanto, ele precisa de métricas próprias.

### 3.1 Classes possíveis

```text
TP: oracle aprovou e a cura estava correta.
FP: oracle aprovou, mas a cura estava errada.
TN: oracle rejeitou e a cura estava errada.
FN: oracle rejeitou, mas a cura estava correta.
```

### 3.2 Métricas

```text
oracle_precision = TP / (TP + FP)
oracle_recall    = TP / (TP + FN)
oracle_f1        = 2 * precision * recall / (precision + recall)
false_acceptance_rate = FP / (TP + FP)
false_rejection_rate  = FN / (TP + FN)
```

### 3.3 Regras de promoção

Um oracle só deve ser usado para promoção automática de healing se:

- precision >= 0.95;
- false_acceptance_rate < 0.02;
- tiver pelo menos 30 observações revisadas para aquele tipo de ação;
- tiver pelo menos um sinal de negócio ou rede para ações críticas;
- não houver conflito entre oracles.

---

## 4. Registro e revisão de evidências em shadow mode

Cada sugestão de healing deve gerar um Evidence Package.

### 4.1 Conteúdo mínimo

```yaml
evidence_package:
  run_id: "run-001"
  action_id: "step_004"
  taxonomy_code: "LOCATOR_NOT_FOUND"
  technology_profile: "react"
  original_locator: "page.get_by_role('button', name='Pesquisar')"
  suggested_locator: "page.get_by_role('button', name='Consultar')"
  score_breakdown:
    semantic_score: 0.82
    uniqueness_score: 0.91
    actionability_score: 1.0
    oracle_score: 0.88
    historical_score: 0.0
  artifacts:
    screenshot_before: "..."
    screenshot_after_candidate: "..."
    dom_before: "..."
    dom_after: "..."
    ax_tree_before: "..."
    ax_tree_after: "..."
    network_log: "..."
    trace: "..."
  review:
    status: "pending"
    label: null
```

### 4.2 Fila de revisão

A fila de revisão deve permitir classificar cada caso como:

```text
TRUE_POSITIVE_HEAL
FALSE_HEAL
NOT_RECOVERABLE
ORACLE_WEAK
TAXONOMY_WRONG
TECHNOLOGY_PROFILE_WRONG
INCONCLUSIVE
```

---

## 5. Sistemas falsos para teste controlado

Criar um TestForge Synthetic Lab com aplicações falsas e mutáveis.

### 5.1 Objetivo

Gerar falhas controladas que talvez sejam raras ou difíceis de encontrar nos ambientes reais.

### 5.2 Aplicações falsas sugeridas

```text
fake-react-bank-app
fake-angular-form-app
fake-jsf-like-legacy-app
fake-iframe-app
fake-shadow-dom-app
fake-design-system-app
```

### 5.3 Mutações controladas

```yaml
mutations:
  locator:
    - change_id
    - change_css_class
    - remove_data_testid
    - duplicate_button_text
    - change_accessible_name

  actionability:
    - add_overlay
    - disable_button
    - delayed_enable
    - animation_before_click

  synchronization:
    - delayed_render
    - debounce_search
    - delayed_network_response
    - spinner_timeout

  technology_specific:
    react:
      - rerender_component
      - portal_modal
      - virtualized_row_unmounted
    angular:
      - material_overlay
      - async_validator_pending
      - router_navigation_delay
    iframe:
      - change_frame_url
      - delayed_frame_load
    shadow_dom:
      - slot_projection_change
      - closed_shadow_root
```

---

## 6. Banco de dados de healing durante o desenvolvimento

Durante o desenvolvimento, cada execução deve alimentar um banco de observações.

### 6.1 Tipos de registro

```text
locator_observation
healing_suggestion
oracle_observation
review_decision
technology_detection
mutation_result
promotion_decision
```

### 6.2 Promoção progressiva

```text
experimental -> shadow_validated -> canary -> trusted -> deprecated
```

### 6.3 O que melhora com o tempo

- pesos por tecnologia;
- thresholds de score;
- classificação da taxonomia;
- seleção de oracles;
- regras de fallback;
- lista de locators confiáveis por aplicação;
- detecção de anti-padrões de acessibilidade/testabilidade.

---

## 7. Critério de sucesso do laboratório sintético

Antes de testar em ambiente real, o motor deve passar em bateria sintética:

```text
100% dos casos de mutação conhecida classificados pela taxonomia;
precision do oracle >= 95%;
false healing < 2%;
zero auto-heal em casos marcados como não recuperáveis;
LLM acionada apenas em casos inconclusivos.
```
