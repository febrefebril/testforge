# Proposta de Arquitetura para TestForge: Gravação Resiliente com Self-Healing Determinístico

## Diagnóstico

O problema atual não está apenas no gravador, no runner ou no prompt. O problema é arquitetural: cada camada recebeu responsabilidade de inferir intenção e corrigir fragilidade em tempo de execução. Isso deslocou a instabilidade de um lugar para outro.

A solução proposta é separar claramente: captura de evidências, compilação determinística, execução com healing controlado, curadoria e evolução de regras.

## Princípio central

O teste não deve nascer como uma sequência frágil de seletores. Ele deve nascer como um contrato semântico de interação:

- intenção da ação;
- identidade semântica do elemento;
- contexto da página;
- sinais alternativos de localização;
- critérios de sucesso observáveis;
- evidências capturadas no momento da gravação.

## Arquitetura recomendada

1. Recorder Sensorial
   - Captura o máximo de evidências possível.
   - Não tenta gerar teste final robusto.
   - Não contém regras específicas por aplicação.

2. Modelo Intermediário de Teste
   - Representa ações como contratos semânticos.
   - Mantém fingerprint do elemento, contexto e objetivo da ação.
   - É a fonte de verdade antes da geração de código.

3. Compilador Determinístico
   - Transforma o modelo intermediário em Playwright Python.
   - Usa ranking de estratégias de localização.
   - Gera assertions e waits explícitos baseados em estado de negócio.

4. Runtime de Execução
   - Executa o teste.
   - Usa locators primários e alternativos.
   - Aciona self-healing apenas quando há falha de localização ou ambiguidade controlada.

5. Motor de Self-Healing Determinístico
   - Reextrai DOM e árvore de acessibilidade.
   - Gera candidatos.
   - Calcula score de similaridade.
   - Aplica thresholds para auto-heal, quarentena ou falha.
   - Persiste a decisão com evidências.

6. Curadoria com LLM
   - Fora do caminho crítico.
   - Usada apenas quando o determinístico não resolve.
   - Gera proposta de regra, patch ou explicação.
   - Nunca deve apenas “inventar seletor” sem validação.

## Ordem de prioridade dos locators

1. getByRole com accessible name
2. getByLabel
3. getByPlaceholder
4. getByTestId / data-testid
5. texto visível quando o texto é contrato de negócio
6. atributos estáveis de domínio
7. relações com âncoras próximas
8. CSS simples e estável
9. XPath apenas como último recurso

## Regra de ouro

O LLM não deve ser o self-healing principal. Ele deve ser o curador quando a heurística determinística não tiver confiança suficiente.

## Próximos artefatos sugeridos

- ADR da decisão arquitetural.
- Diagrama PlantUML C4 Container.
- Esquema YAML do modelo intermediário.
- Contrato JSON do evento gravado.
- Pseudocódigo do algoritmo de scoring.
