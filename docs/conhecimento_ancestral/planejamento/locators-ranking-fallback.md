# TestForge — Geração de Candidatos, Ranking de Locators e Fallback Determinístico

## 1. Geração automática de candidatos de locators

A geração automática de candidatos deve partir do `SemanticTarget` e das evidências coletadas pelo recorder: DOM, accessibility tree, atributos, texto visível, labels, contexto da página, elementos vizinhos, iframe/shadow DOM e histórico de sucesso.

### Ordem recomendada de geração

1. Role + accessible name
2. Label
3. Placeholder
4. Test id
5. Texto visível
6. Atributos estáveis de domínio
7. Relação com elementos próximos
8. CSS simples
9. XPath relativo

### Exemplo conceitual

```python
candidates = []

if target.role and target.accessible_name:
    candidates.append(role_candidate(target.role, target.accessible_name))

if target.label:
    candidates.append(label_candidate(target.label))

if target.test_id:
    candidates.append(test_id_candidate(target.test_id))

if target.visible_text:
    candidates.append(text_candidate(target.visible_text))

if target.attributes:
    candidates.extend(attribute_candidates(target.attributes))

candidates.extend(contextual_candidates(target, context))
```

## 2. Ranking de score de locators

O score deve medir a probabilidade de um candidato representar o mesmo elemento da intenção gravada.

### Fórmula inicial sugerida

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

### Componentes

- `semantic_strength`: role, label, accessible name e placeholder.
- `uniqueness`: candidato resolve exatamente um elemento.
- `stability`: evita id dinâmico, classes geradas e XPath absoluto.
- `context_match`: proximidade com textos e seção esperada.
- `action_compatibility`: elemento permite a ação desejada.
- `historical_success`: candidato já funcionou antes.
- `simplicity`: locator é curto, legível e de baixa fragilidade.

## 3. Fallback determinístico

O fallback determinístico é uma lista ordenada de tentativas, sem LLM, com critérios objetivos.

### Fluxo

```text
1. Ordenar candidatos por score.
2. Para cada candidato:
   a. Resolver locator.
   b. Verificar quantidade de matches.
   c. Verificar actionability.
   d. Executar ação.
   e. Validar assertion pós-ação.
3. Se passar, registrar sucesso.
4. Se falhar, tentar próximo candidato.
5. Se todos falharem, acionar healing determinístico.
6. Se healing tiver baixa confiança, acionar curadoria/LLM.
```

### Critérios de decisão

- `score >= 0.90`: candidato primário.
- `0.75 <= score < 0.90`: fallback aceitável.
- `0.60 <= score < 0.75`: usar apenas com validação forte pós-ação.
- `score < 0.60`: não usar automaticamente.

## 4. Regra essencial

O fallback só pode ser considerado bem-sucedido se a assertion pós-ação confirmar que a intenção foi cumprida. Encontrar e clicar em um elemento não basta.

## 5. Eventos que devem ser persistidos

- candidato escolhido;
- score;
- tempo de resolução;
- quantidade de matches;
- resultado da actionability check;
- assertion pós-ação;
- screenshot antes/depois;
- DOM/accessibility snapshot;
- motivo de falha dos candidatos rejeitados.
