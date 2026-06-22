# Revisão crítica dos diagramas PlantUML do TestForge

## 1. Consistência arquitetural

### Inconsistências encontradas

1. **Nome do pedido vs. conteúdo gerado no último diagrama**  
   O pedido menciona “Diagrama de sequência do selfhealing”, mas o texto do requisito descreve novamente um **diagrama de implantação**. O diagrama gerado seguiu corretamente o conteúdo solicitado, porém o nome do artefato ficou semanticamente ambíguo.

2. **Componentes ainda não uniformizados entre todos os diagramas**  
   Alguns diagramas usam `FailureSignatureBuilder`, outros enfatizam apenas `FailureDiagnostic` e `FailureClassifier`. O modelo de domínio possui `FailureSignature`, mas o pacote possui `failure_signature`. Isso é aceitável por camada, mas deve ser padronizado no documento de arquitetura para evitar dúvidas entre classe, módulo e serviço.

3. **Mistura pontual entre runtime e domínio no diagrama de implantação/self-healing**  
   O diagrama de implantação inclui muitos componentes internos de curadoria dentro do nó `Ambiente Python`. Isso ajuda na visualização, mas pode poluir o diagrama de implantação. Para documentação executiva, mantenha só containers/processos. Para implementação, o nível detalhado é útil.

4. **Uso de elementos auxiliares escondidos em alguns diagramas**  
   Foram usados elementos como `TargetBackendAlias`, `edge_hidden_1` e `actions_hidden_1` apenas para layout. Esses elementos podem aparecer ou gerar ruído dependendo do renderizador PlantUML. Recomenda-se remover.

5. **Dependências de pacote potencialmente excessivas**  
   No diagrama de pacotes, `patch` depende de `executor`, `failure`, `knowledge` e `models`; `agents` também depende de `patch`, `knowledge`, `failure` e `evidence`. Isso é coerente, mas exige disciplina para evitar ciclo indireto. A regra recomendada é: `agents` orquestra, `patch` valida/aplica, `executor` executa; `patch` não deve chamar `agents`.

### Ajustes recomendados

- Criar uma tabela de mapeamento entre **Container**, **Package**, **Component** e **Class**.
- Remover aliases escondidos usados só para layout.
- Separar o diagrama de implantação em duas versões:
  - **Implantação resumida**, com nós/processos.
  - **Implantação detalhada**, com componentes internos.
- Criar um diagrama específico de sequência do self-healing, porque o último pedido tinha título de sequência, mas requisitos de implantação.

---

## 2. Aderência ao fluxo do zero

### Pontos fortes

- A gravação foi tratada como **pipeline de coleta de evidências**, não só captura de evento.
- O fingerprint inicial aparece antes da primeira interação.
- O loop de gravação persiste steps incrementalmente.
- A gravação é validada antes da normalização e antes da geração do script.
- Há distinção clara entre `session_raw.json`, `session_normalized.json`, `steps_normalized.json`, `selector_candidates.json` e `script_v0.py`.

### Ajustes recomendados

- No diagrama de atividade, a transição da fase 12 que usa `detach` pode ficar ambígua. Melhor apontar explicitamente de volta à fase de classificação/curadoria ou usar nota indicando retorno lógico.
- Em todos os diagramas, reforçar que `fingerprint_initial.json` é salvo **antes** de `JSInjector` e `RecorderOverlay` quando a intenção for capturar o estado original da página sem instrumentação.

---

## 3. Aderência à taxonomia de falhas

### Pontos fortes

- As seis famílias aparecem no roteamento:
  - seletores frágeis;
  - timing/assincronismo;
  - contexto/escopo;
  - estado da aplicação;
  - DOM dinâmico;
  - interação especializada.
- Existem agentes especializados por família.
- O `ProgressDetector` contém os estados esperados:
  - `PASSED_STEP`;
  - `PROGRESSED`;
  - `STAGNATED`;
  - `REGRESSED`;
  - `ERROR_CHANGED`;
  - `UNRESOLVED`.
- Rollback em regressão está representado.
- `ERROR_CHANGED` retorna para classificação.

### Ajustes recomendados

- Incluir `GeneralDiagnosticAgent` no diagrama de sequência de curadoria como agente para falha desconhecida. Ele aparece no contexto e no diagrama de componentes, mas no diagrama de sequência foi representado apenas como estratégia geral interna do `AgentOrchestrator`.
- Representar explicitamente que `UNRESOLVED` pode voltar para `AGENT_SELECTED` enquanto ainda houver estratégia determinística disponível.

---

## 4. Uso correto de LLM

### Pontos fortes

- O LLM aparece como fallback opcional/controlado.
- Há validação posterior via `PatchValidator`.
- Há proteção via `SensitiveDataGuard` antes de envio externo.
- A resposta do LLM é tratada como hipótese ou patch candidato, não como correção automática.

### Ajustes recomendados

- Incluir em todos os diagramas onde houver LLM a frase arquitetural: **“LLM nunca aplica patch diretamente.”**
- Mostrar que o pacote enviado ao LLM deve conter apenas o mínimo necessário e deve ser mascarado/tokenizado.

---

## 5. Artefatos

### Artefatos cobertos nos diagramas

Os diagramas mencionam ou materializam os principais artefatos:

- `session_raw.json`;
- `fingerprint_initial.json`;
- `fingerprint_final.json`;
- `steps_normalized.json`;
- `selector_candidates.json`;
- `script_v0.py`;
- `failure_signature.json`;
- `script_final.py`;
- `test_data.json`;
- `locators.json`;
- `healing_rules.json`;
- `execution_report.json`.

### Ajustes recomendados

- Incluir explicitamente `sensitive_data_report.json` no C4 Container e no diagrama de implantação, pois é essencial para governança.
- Incluir `agent_history.json` no C4 Container como saída do `Final Artifact Builder`.
- Incluir `recording_summary.md` como relatório parcial da gravação.

---

## 6. Implementabilidade

### Pontos fortes

- Os componentes mapeiam bem para módulos Python.
- O diagrama de pacotes oferece uma organização inicial implementável.
- O modelo de domínio é suficiente para um protótipo incremental.
- Há separação entre gravação, evidência, geração, execução, falha, curadoria, patch, self-healing, dados e entrega.

### Ajustes recomendados

- Criar contratos Pydantic/dataclasses para:
  - `RecordingSession`;
  - `RecordedStep`;
  - `LocatorCandidate`;
  - `EvidenceBundle`;
  - `FailureSignature`;
  - `AgentAttempt`;
  - `Patch`;
  - `HealingRule`.
- Criar interfaces explícitas para agentes:
  - `AgentInput`;
  - `AgentOutput`;
  - `PatchCandidate`;
  - `ProgressResult`.
- Criar camada de porta/adaptador para Playwright, evitando espalhar chamadas diretas ao Playwright pelos agentes.

---

# Trechos PlantUML corrigidos ou recomendados

## 1. Correção para falha desconhecida no diagrama de sequência da curadoria

```plantuml
participant "GeneralDiagnosticAgent" as GeneralDiagnosticAgent

...

else Família desconhecida
  AgentOrchestrator -> GeneralDiagnosticAgent : solicitar diagnóstico determinístico geral\ncom base em evidências, histórico e taxonomia
  activate GeneralDiagnosticAgent
  GeneralDiagnosticAgent --> AgentOrchestrator : patch candidato ou hipótese determinística
  deactivate GeneralDiagnosticAgent
end
```

## 2. Remoção de aliases escondidos em diagrama de implantação

Substituir:

```plantuml
TargetBackendAlias -[hidden]-> target_backend
actions_hidden_1 -[hidden]-> git_scripts
```

Por nenhum trecho equivalente. Esses elementos não são necessários para a semântica do diagrama.

## 3. Ajuste recomendado para C4 Container incluindo artefatos finais adicionais

```plantuml
Rel(final_artifact_builder, evidence_repository, "Publica artefatos finais", "script_final.py / test_data.json / locators.json / healing_rules.json / execution_report.json / agent_history.json / fingerprint_summary.json")
```

## 4. Ajuste para deixar `GeneralDiagnosticAgent` consistente no pacote

```plantuml
general_diagnostic --> failure
general_diagnostic --> evidence
general_diagnostic --> knowledge
general_diagnostic --> patch
general_diagnostic --> models
```

## 5. Ajuste para reforçar proteção de dados antes do LLM

```plantuml
LLMFallbackAgent --> SensitiveDataGuard : solicitar mascaramento/tokenização
SensitiveDataGuard --> LLMFallbackAgent : pacote mínimo aprovado
LLMFallbackAgent ..> llm_service : enviar somente evidências mascaradas
llm_service ..> LLMFallbackAgent : retornar hipótese ou patch candidato
LLMFallbackAgent --> PatchValidator : validar antes de aplicar
```

---

# Priorização dos diagramas para implementação

## Prioridade 1 — Fonte de verdade para o esqueleto do projeto

1. **Diagrama de pacotes**  
   Deve ser implementado primeiro porque define a organização do código Python e reduz risco de acoplamento circular.

2. **Diagrama de classes / modelo de domínio**  
   Deve vir logo depois para formalizar os contratos dos JSONs e dos objetos internos.

3. **Diagrama de atividade completo**  
   Serve como roteiro macro para backlog, épicos e milestones do protótipo.

## Prioridade 2 — Fluxos críticos executáveis

4. **Diagrama de sequência da gravação enriquecida**  
   Orienta a implementação do `record` e da persistência incremental.

5. **Diagrama de sequência da curadoria multiagente**  
   Orienta a implementação do `curate`, dos agentes e do loop patch/execução/progresso.

6. **Diagramas de estados da RecordingSession e FailureSignature**  
   Devem guiar validações, persistência de status e retomada segura do processo.

## Prioridade 3 — Operação local e visão executiva

7. **Diagrama de implantação runtime local**  
   Útil para explicar ambiente, dependências locais, arquivos e integração com Playwright.

8. **C4 Container**  
   Ideal para comunicação de arquitetura com pessoas que não precisam ver todos os detalhes UML.

9. **Diagrama detalhado de self-healing/implantação**  
   Útil depois que o loop de curadoria estiver prototipado, para consolidar runtime, regras finais e fallback controlado.
