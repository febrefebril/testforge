# TestForge Synthetic Lab — Mutações Sintéticas Controladas

## Objetivo

Criar aplicações falsas e mutáveis para validar o TestForge antes de depender dos ambientes reais.

## Estratégias de implementação

### 1. Feature flags na aplicação falsa

Exemplo de URL:

```text
/fake-react-bank-app?mutation=duplicate_button_text
/fake-angular-form-app?mutation=material_overlay_obscured
```

### 2. Mutator no servidor

O servidor renderiza HTML/JS diferente conforme a mutação.

### 3. Mutator por injeção controlada no browser

Durante o teste, o runner injeta alteração controlada no DOM para simular quebra.

### 4. Matriz esperada

Cada mutação deve declarar:

- tecnologia;
- família;
- código da mutação;
- taxonomia esperada;
- se é recuperável por locator healing;
- oracle esperado;
- se LLM pode ser acionada.

## Exemplo de caso sintético

```yaml
mutation_case:
  app: fake-react-bank-app
  technology: react
  mutation: duplicate_button_text
  expected_taxonomy: LOCATOR_AMBIGUOUS
  expected_recoverable: true
  expected_policy: refine_context
  expected_oracle:
    - network
    - business_state
```
