# TestForge — Plano Autocontido para Implementação do Executor Incremental, Healing Validado e Relatórios

**Data:** 17/06/2026  
**Objetivo:** orientar outra LLM a implementar, verificar e validar o conjunto de mudanças planejadas para estabilizar o TestForge até amanhã.  
**Escopo:** TestForge apenas. Não implementar MCP RTC/RQM/RDNG, MCP mestre nem SpecKit.  
**Princípio central:** o TestForge deve parar de tratar “step executou sem exception” como sinônimo de “fluxo funcionou”. O novo fluxo deve validar cada passo por pré-condição, execução, pós-condição, evidência, healing e oracle.

---

## 1. Contexto mínimo do projeto

O TestForge é um gravador e executor de testes E2E com Playwright Python e self-healing determinístico/LLM. O pipeline atual possui gravação (`record`), compilação (`compile`), execução (`run`), coleta de evidências, curadoria/healing, métricas, oráculo e promotion gate.

Componentes existentes relevantes:

- `src/testforge/cli/app.py`: CLI atual com `record`, `compile`, `run`, `pipeline`, `demo-heal`.
- `src/testforge/runner/fallback_runner.py`: contém `FallbackRunner` e `SmartStepRunner`.
- `src/testforge/healing/curator.py`: contém `CuradorAutomatico`, `CurationOutcome` e `ProgressResult`.
- `src/testforge/healing/llm_healer.py`: contém `LLMHealer`, `MockLLMHealer`, `LLMHealingProposal`.
- `src/testforge/healing/agents/`: agentes especialistas L2 por família.
- `src/testforge/evidence/evidence_collector.py`: coleta DOM, screenshot, console, rede e gera `EvidencePayload`.
- `src/testforge/oracle/oracle_runner.py`: validações `visual_dom` e `business_state`.
- `src/testforge/promotion/promotion_gate.py`: decide promoção com base em evidência, oracle e unicidade.
- `src/testforge/metrics/metrics_repository.py`: métricas por execução e por step.
- `src/testforge/actionability/actionability_validator.py`: valida elemento visível, habilitado e com bounding box positiva.
- `src/testforge/reporting/run_report.py`: base para relatório de execução.

Problemas que motivam esta implementação:

1. Fluxos reais estão instáveis; às vezes demora horas para passar por data, valor e botão.
2. Páginas de teste locais funcionam, mas páginas reais expõem falhas de sequência, timing, mascaramento, navegação e asserts.
3. O `run` atual mistura carregamento, execução, healing, métricas e relatório em uma função grande.
4. O healing pode ser contado como sucesso mesmo quando o efeito esperado não ocorreu.
5. Precisamos de um executor incremental que mostre exatamente onde o fluxo quebra.

---

## 2. Decisões de arquitetura

### D1 — Criar `run-incremental`

Criar um novo comando CLI:

```bash
testforge run-incremental <script> --headless --verbose --data <json> --browser chromium|chrome|edge
```

Esse comando deve executar o teste passo a passo, validando:

1. pré-condições;
2. execução;
3. pós-condições;
4. evidências before/after;
5. healing com `CuradorAutomatico`;
6. oracle pós-healing;
7. métricas e relatório.

### D2 — Separar responsabilidades

Criar novos módulos:

```text
src/testforge/runner/
├── incremental_runner.py
├── step_executor.py
├── step_precondition.py
├── step_postcondition.py
├── step_result.py
└── incremental_ui.py
```

### D3 — Curador não valida sozinho healing verdadeiro

Regra obrigatória:

```text
CuradorAutomatico retorna PASSED_STEP
    = proposta executou sem exception.

Oracle/pós-condição passou
    = healing verdadeiro.

Logo:
    PASSED_STEP + oracle falhou = healing_rejected.
    PASSED_STEP + oracle passou = healed_validated.
```

### D4 — Métricas por step são obrigatórias

Registrar separadamente:

- `FAILURE_DETECTED`
- `HEALING_ATTEMPTED`
- `HEALING_APPLIED`
- `ORACLE_VALIDATED`
- `HEALING_REJECTED`

### D5 — Relatório completo é obrigatório

Cada execução incremental deve gerar:

```text
runs/<recording_id>/<timestamp>/
├── execution_report.json
├── healing_report.md
├── summary.md
├── metrics.json
├── steps/
├── screenshots/
├── dom/
└── sensitive_data_alert.json
```

---

## 3. Épicos, histórias, tarefas e critérios de aceite

# Épico 1 — Fundação do Executor Incremental

## História 1.1 — Criar comando `run-incremental`

**Como** QA/desenvolvedor,  
**quero** executar um teste passo a passo,  
**para** diagnosticar exatamente onde o fluxo falha.

### Tarefas

- T1.1.1 — Adicionar subcomando `run-incremental` em `src/testforge/cli/app.py`.
- T1.1.2 — Criar `src/testforge/runner/incremental_runner.py`.
- T1.1.3 — Implementar carregamento do script e extração de `BASE_URL`.
- T1.1.4 — Implementar identificação de `recording_id` a partir do script.
- T1.1.5 — Reutilizar `RecordingNormalizer` para carregar `steps`.
- T1.1.6 — Suportar flags `--headless`, `--timeout`, `--verbose`, `--data`, `--browser`, `--stop-on-failure`, `--interactive`, `--no-healing`, `--shadow`.

### Critérios de aceite

- CA1 — `testforge run-incremental <script>` executa sem erro estrutural.
- CA2 — O comando mostra URL base, script, recording e modo de healer.
- CA3 — Se não houver steps, mensagem clara é exibida.
- CA4 — O comando não quebra o `testforge run` existente.

### Testes

- `tests/test_run_incremental_cli.py::test_cli_has_run_incremental_command`
- `tests/test_run_incremental_cli.py::test_run_incremental_fails_with_missing_script`
- `tests/test_run_incremental_cli.py::test_run_incremental_loads_script_metadata`

---

## História 1.2 — Criar modelo de resultado incremental

### Tarefas

- T1.2.1 — Criar `src/testforge/runner/step_result.py`.
- T1.2.2 — Implementar `PreconditionResult`.
- T1.2.3 — Implementar `PostconditionResult`.
- T1.2.4 — Implementar `HealingAttempt`.
- T1.2.5 — Implementar `IncrementalStepResult`.
- T1.2.6 — Implementar serialização para JSON.

### Critérios de aceite

- CA1 — Cada step registra `step_num`, `action`, `status`, `original_locator`, `selected_locator`, `value`, `precondition`, `postcondition`, `healing`, `error_message`, `evidence_before`, `evidence_after`, `duration_ms`.
- CA2 — O resultado pode ser salvo em JSON sem objetos não serializáveis.

### Testes

- `tests/test_incremental_step_result.py::test_step_result_serializes_to_json`
- `tests/test_incremental_step_result.py::test_healing_attempt_has_required_fields`

---

# Épico 2 — Pré-condições por Step

## História 2.1 — Implementar `StepPreconditionValidator`

**Como** executor incremental,  
**quero** validar se um step pode ser executado,  
**para** falhar cedo com explicação clara.

### Tarefas

- T2.1.1 — Criar `src/testforge/runner/step_precondition.py`.
- T2.1.2 — Integrar `ActionabilityValidator`.
- T2.1.3 — Validar `skip_reason`.
- T2.1.4 — Validar `depends_on`.
- T2.1.5 — Validar selector ausente.
- T2.1.6 — Validar candidato primário.
- T2.1.7 — Validar `click`.
- T2.1.8 — Validar `fill`.
- T2.1.9 — Validar `select_option`.
- T2.1.10 — Validar `assert`.

### Critérios de aceite

- CA1 — `click` exige elemento visível, habilitado e área positiva.
- CA2 — `fill` exige selector, valor e elemento editável/não readonly.
- CA3 — `select_option` exige alvo `<select>` e option existente.
- CA4 — `assert` exige expected quando aplicável.
- CA5 — Dependente de step falho vira `blocked`, não `failed`.

### Testes

- `tests/test_step_precondition.py::test_click_requires_actionable_element`
- `tests/test_step_precondition.py::test_fill_requires_value`
- `tests/test_step_precondition.py::test_select_requires_select_tag`
- `tests/test_step_precondition.py::test_assert_requires_expected_text`
- `tests/test_step_precondition.py::test_dependency_blocks_step`

---

# Épico 3 — Execução Incremental de Steps

## História 3.1 — Implementar `StepExecutor`

### Tarefas

- T3.1.1 — Criar `src/testforge/runner/step_executor.py`.
- T3.1.2 — Implementar execução de `navigation`.
- T3.1.3 — Implementar execução de `click`.
- T3.1.4 — Implementar execução de `fill`.
- T3.1.5 — Implementar execução de `select_option`.
- T3.1.6 — Implementar execução de `assert` quando necessário.
- T3.1.7 — Suportar data-driven com `--data`.
- T3.1.8 — Detectar campos mascarados e usar estratégia compatível quando necessário.
- T3.1.9 — Registrar selector usado e tentativa executada.

### Critérios de aceite

- CA1 — `click` tenta candidato principal.
- CA2 — `fill` usa valor do step ou do data file.
- CA3 — `select_option` usa Playwright `select_option`, não `fill` nem `click`.
- CA4 — Erros de execução são propagados para `_heal_failed_step`.
- CA5 — Step executor não decide sozinho se o step passou semanticamente; isso é papel da pós-condição.

### Testes

- `tests/test_step_executor.py::test_execute_click_success`
- `tests/test_step_executor.py::test_execute_click_raises_for_missing_selector`
- `tests/test_step_executor.py::test_execute_fill_success`
- `tests/test_step_executor.py::test_execute_select_option_success`
- `tests/test_step_executor.py::test_execute_select_option_does_not_call_fill`

---

# Épico 4 — Pós-condições e Oracle

## História 4.1 — Implementar `StepPostconditionValidator`

**Como** TestForge,  
**quero** validar o efeito de cada ação,  
**para** impedir falso positivo e falso healing.

### Tarefas

- T4.1.1 — Criar `src/testforge/runner/step_postcondition.py`.
- T4.1.2 — Integrar `OracleRunner`.
- T4.1.3 — Validar `fill` por valor final normalizado.
- T4.1.4 — Validar `select_option` por selected value/label.
- T4.1.5 — Validar `click` por oracles explícitos, próximo step visível ou navegação.
- T4.1.6 — Validar `assert` via `OracleRunner`.
- T4.1.7 — Retornar `PostconditionResult` com `oracle_results`.

### Critérios de aceite

- CA1 — `fill` só passa se valor final for compatível.
- CA2 — `select_option` só passa se valor/label selecionado for compatível.
- CA3 — `click` não é considerado válido apenas por não lançar exception quando houver oracle/consequência esperada.
- CA4 — `assert` usa `OracleRunner`.
- CA5 — `PostconditionResult` registra mensagem e failures.

### Testes

- `tests/test_step_postcondition.py::test_fill_postcondition_validates_value`
- `tests/test_step_postcondition.py::test_select_postcondition_validates_selected_value`
- `tests/test_step_postcondition.py::test_click_postcondition_validates_next_step_visible`
- `tests/test_step_postcondition.py::test_assert_postcondition_uses_oracle_runner`
- `tests/test_step_postcondition.py::test_oracle_failure_returns_failed_postcondition`

---

# Épico 5 — Integração com CuradorAutomatico

## História 5.1 — Implementar `_make_curator`

### Tarefas

- T5.1.1 — Implementar `_make_curator` no `IncrementalRunner`.
- T5.1.2 — Criar `SmartStepRunner(self.page)`.
- T5.1.3 — Criar função `step_runner(step_data)` que chama `SmartStepRunner.execute(step_data, strategy)`.
- T5.1.4 — Retornar `CuradorAutomatico(catalog=HealingCatalog(), step_runner=step_runner)`.
- T5.1.5 — Permitir injeção de `catalog` e `step_runner` para testes.

### Critérios de aceite

- CA1 — `_make_curator()` retorna `CuradorAutomatico`.
- CA2 — O `step_runner` injetado é chamado em teste.
- CA3 — O método funciona sem precisar chamar LLM real.

### Testes

- `tests/test_incremental_curator.py::test_make_curator_returns_curador_automatico`
- `tests/test_incremental_curator.py::test_make_curator_uses_injected_step_runner`

---

## História 5.2 — Implementar `_build_healing_payload`

### Tarefas

- T5.2.1 — Montar `step_context` com action, selector, value, text, intention, url, framework, step_number, failure_phase, original_error.
- T5.2.2 — Chamar `EvidenceCollector.build_llm_payload()`.
- T5.2.3 — Verificar `payload.is_sufficient`.
- T5.2.4 — Registrar motivo de evidência insuficiente no relatório.

### Critérios de aceite

- CA1 — Payload com DOM suficiente permite healing.
- CA2 — Payload sem DOM suficiente bloqueia healing com mensagem clara.

### Testes

- `tests/test_incremental_healing_payload.py::test_build_healing_payload_contains_step_context`
- `tests/test_incremental_healing_payload.py::test_insufficient_payload_blocks_healing`

---

## História 5.3 — Implementar `_validate_curator_proposal`

### Tarefas

- T5.3.1 — Rejeitar outcome ausente.
- T5.3.2 — Rejeitar proposta sem locator.
- T5.3.3 — Rejeitar confidence menor que 0.5.
- T5.3.4 — Rejeitar family/taxonomy ausentes.
- T5.3.5 — Rejeitar strategy ausente.
- T5.3.6 — Rejeitar locator genérico/perigoso (`body`, `button`, `text=Selecione`, XPath absoluto frágil etc.).
- T5.3.7 — Rejeitar strategy incompatível com action.
- T5.3.8 — Rejeitar proposta igual ao locator original quebrado, exceto L0 quando justificável.

### Critérios de aceite

- CA1 — Proposta genérica é rejeitada antes do Oracle.
- CA2 — Proposta válida segue para validação pós-healing.
- CA3 — Motivos de rejeição aparecem no relatório.

### Testes

- `tests/test_incremental_curator_proposal.py::test_rejects_missing_locator`
- `tests/test_incremental_curator_proposal.py::test_rejects_low_confidence`
- `tests/test_incremental_curator_proposal.py::test_rejects_generic_locator`
- `tests/test_incremental_curator_proposal.py::test_rejects_incompatible_strategy`
- `tests/test_incremental_curator_proposal.py::test_accepts_valid_proposal`

---

## História 5.4 — Implementar `_heal_failed_step`

### Tarefas

- T5.4.1 — Registrar `FAILURE_DETECTED`.
- T5.4.2 — Construir `EvidencePayload`.
- T5.4.3 — Bloquear healing se evidência insuficiente.
- T5.4.4 — Criar curador com `_make_curator`.
- T5.4.5 — Registrar `HEALING_ATTEMPTED`.
- T5.4.6 — Chamar `curator.cure(step_data, original_error, payload)`.
- T5.4.7 — Mapear `CurationOutcome` para `result.healing`.
- T5.4.8 — Validar proposta com `_validate_curator_proposal`.
- T5.4.9 — Se outcome não for `PASSED_STEP`, registrar `HEALING_REJECTED`.
- T5.4.10 — Se outcome for `PASSED_STEP`, registrar `HEALING_APPLIED`.
- T5.4.11 — Rodar `_validate_healing_with_oracle`.
- T5.4.12 — Se oracle passou, registrar `ORACLE_VALIDATED` e status `healed_validated`.
- T5.4.13 — Se oracle falhou, registrar `HEALING_REJECTED` e status `healing_rejected`.
- T5.4.14 — Rodar `PromotionGate` somente depois de `healed_validated`.

### Critérios de aceite

- CA1 — Curador `PASSED_STEP` sem oracle aprovado não vira `healed_validated`.
- CA2 — Curador `PASSED_STEP` + oracle falho vira `healing_rejected`.
- CA3 — Curador `PASSED_STEP` + oracle aprovado vira `healed_validated`.
- CA4 — Métricas refletem cada transição.
- CA5 — Relatório mostra locator original, locator proposto, layer, family, taxonomy, strategy, confidence e oracle_passed.

### Testes

- `tests/test_incremental_heal_failed_step.py::test_heal_failed_step_validates_true_healing`
- `tests/test_incremental_heal_failed_step.py::test_heal_failed_step_rejects_false_healing`
- `tests/test_incremental_heal_failed_step.py::test_heal_failed_step_blocks_insufficient_evidence`
- `tests/test_incremental_heal_failed_step.py::test_heal_failed_step_records_metrics`
- `tests/test_incremental_heal_failed_step.py::test_heal_failed_step_rejects_invalid_proposal`

---

# Épico 6 — Métricas de Healing

## História 6.1 — Registrar métricas por step

### Tarefas

- T6.1.1 — Usar `MetricsRepository.record_step()` em cada fase.
- T6.1.2 — Registrar falha detectada.
- T6.1.3 — Registrar healing tentado.
- T6.1.4 — Registrar healing aplicado.
- T6.1.5 — Registrar oracle validado.
- T6.1.6 — Registrar healing rejeitado.
- T6.1.7 — Gerar `metrics.json` por execução.

### Critérios de aceite

- CA1 — Falha sem healing incrementa apenas `falhas_detectadas`.
- CA2 — Healing tentado incrementa `healings_tentados`.
- CA3 — Curador `PASSED_STEP` incrementa `aplicados`.
- CA4 — Oracle aprovado incrementa `validados`.
- CA5 — Oracle falho incrementa `rejeitados`.

### Testes

- `tests/test_incremental_metrics.py::test_metrics_for_validated_healing`
- `tests/test_incremental_metrics.py::test_metrics_for_rejected_healing`
- `tests/test_incremental_metrics.py::test_metrics_for_failed_without_healing`

---

# Épico 7 — Relatórios e Evidências

## História 7.1 — Capturar evidência before/after por step

### Tarefas

- T7.1.1 — Integrar `EvidenceCollector` ao `IncrementalRunner`.
- T7.1.2 — Capturar screenshot antes do step.
- T7.1.3 — Capturar DOM antes do step.
- T7.1.4 — Capturar screenshot depois do step.
- T7.1.5 — Capturar DOM depois do step.
- T7.1.6 — Registrar quality flags quando DOM for insuficiente.
- T7.1.7 — Manter política de dados sensíveis como `alert_only`, sem mascaramento automático.

### Critérios de aceite

- CA1 — Cada step executado possui evidência before/after quando possível.
- CA2 — DOM vazio não é salvo silenciosamente.
- CA3 — Alertas de dados sensíveis são registrados sem mascaramento automático.

### Testes

- `tests/test_incremental_evidence.py::test_captures_before_after_evidence`
- `tests/test_incremental_evidence.py::test_empty_dom_generates_quality_flag`
- `tests/test_incremental_evidence.py::test_sensitive_data_policy_is_alert_only`

---

## História 7.2 — Gerar `execution_report.json`

### Tarefas

- T7.2.1 — Criar diretório `runs/<recording_id>/<timestamp>/`.
- T7.2.2 — Salvar relatório JSON com resumo da execução.
- T7.2.3 — Salvar lista completa de steps.
- T7.2.4 — Salvar candidatos completos, sem truncar no arquivo.
- T7.2.5 — Registrar skipped e blocked com motivo.

### Critérios de aceite

- CA1 — Relatório contém total, passed, failed, healed_validated, healing_rejected, blocked e skipped.
- CA2 — Cada step contém precondition, execution, postcondition, healing, evidence.
- CA3 — Candidatos completos aparecem no arquivo, mesmo que terminal mostre resumo.

### Testes

- `tests/test_incremental_report.py::test_execution_report_is_created`
- `tests/test_incremental_report.py::test_report_contains_full_candidates`
- `tests/test_incremental_report.py::test_report_explains_skipped_and_blocked_steps`

---

## História 7.3 — Gerar `healing_report.md`

### Tarefas

- T7.3.1 — Criar relatório Markdown de healing.
- T7.3.2 — Listar healings validados.
- T7.3.3 — Listar healings rejeitados.
- T7.3.4 — Exibir motivo de rejeição.
- T7.3.5 — Exibir recomendação operacional quando possível.

### Critérios de aceite

- CA1 — Markdown mostra layer, family, taxonomy, strategy e confidence.
- CA2 — Markdown diferencia `healed_validated` de `healing_rejected`.
- CA3 — Markdown é legível para revisão humana.

### Testes

- `tests/test_incremental_healing_report.py::test_healing_report_md_is_created`
- `tests/test_incremental_healing_report.py::test_healing_report_lists_validated_and_rejected_healings`

---

# Épico 8 — Execução de múltiplos steps em sequência

## História 8.1 — Implementar `_run_one_step`

### Tarefas

- T8.1.1 — Criar `IncrementalRunner._run_one_step(index, step)`.
- T8.1.2 — Validar dependências.
- T8.1.3 — Executar pré-condição.
- T8.1.4 — Capturar evidência before.
- T8.1.5 — Executar step.
- T8.1.6 — Validar pós-condição.
- T8.1.7 — Acionar `_heal_failed_step` em falha de pré, execução ou pós.
- T8.1.8 — Capturar evidência after.
- T8.1.9 — Marcar step blocking falho para bloquear dependentes.

### Critérios de aceite

- CA1 — Step `healed_validated` permite continuar a sequência.
- CA2 — Step `failed` ou `healing_rejected` com `blocking=True` bloqueia dependentes.
- CA3 — Step bloqueado não é contado como falha independente.
- CA4 — Ordem dos steps é preservada.

### Testes

- `tests/test_incremental_sequence.py::test_sequence_continues_after_validated_healing`
- `tests/test_incremental_sequence.py::test_sequence_blocks_after_failed_blocking_step`
- `tests/test_incremental_sequence.py::test_sequence_blocks_after_false_healing`
- `tests/test_incremental_sequence.py::test_skipped_step_is_reported_with_reason`

---

# Épico 9 — Testes de integração com páginas locais

## História 9.1 — Criar páginas HTML mínimas para run-incremental

### Tarefas

- T9.1.1 — Criar página para selector quebrado curável por texto.
- T9.1.2 — Criar página para falso healing: click executa, resultado errado.
- T9.1.3 — Criar página para select_option.
- T9.1.4 — Criar página para fill com valor.
- T9.1.5 — Criar página para dependência/bloqueio.

### Critérios de aceite

- CA1 — Páginas rodam localmente sem sistemas internos.
- CA2 — Cada página reproduz um cenário determinístico.
- CA3 — Cada página possui teste automatizado.

### Testes

- `tests/test_pages/test_incremental_true_healing.py`
- `tests/test_pages/test_incremental_false_healing.py`
- `tests/test_pages/test_incremental_select_option.py`
- `tests/test_pages/test_incremental_dependencies.py`

---

# Épico 10 — Documentação operacional para a próxima LLM

## História 10.1 — Documentar fluxo de implementação

### Tarefas

- T10.1.1 — Criar `docs/run-incremental.md`.
- T10.1.2 — Explicar arquitetura.
- T10.1.3 — Explicar estados de step.
- T10.1.4 — Explicar contrato Curador vs Oracle.
- T10.1.5 — Explicar métricas.
- T10.1.6 — Explicar como rodar testes.

### Critérios de aceite

- CA1 — Documento permite que outro desenvolvedor/LLM implemente sem contexto externo.
- CA2 — Documento explicita que MCP e SpecKit estão fora do escopo.
- CA3 — Documento lista todos os comandos de verificação.

### Testes/verificações

- `python -m pytest tests/test_incremental_* -v`
- `python -m pytest tests/test_pages/test_incremental_* -v`
- `testforge run-incremental <script> --headless --verbose`

---

## 4. Guia de implementação detalhado

### 4.1. Criar `step_result.py`

Implementar dataclasses:

```python
@dataclass
class PreconditionResult:
    passed: bool
    checks: dict[str, bool] = field(default_factory=dict)
    failures: list[str] = field(default_factory=list)
    message: str = ""

@dataclass
class PostconditionResult:
    passed: bool
    checks: dict[str, bool] = field(default_factory=dict)
    oracle_results: list[Any] = field(default_factory=list)
    failures: list[str] = field(default_factory=list)
    message: str = ""

@dataclass
class HealingAttempt:
    attempted: bool = False
    layer: str = ""
    family: str = ""
    taxonomy_id: str = ""
    strategy: str = ""
    original_locator: str = ""
    proposed_locator: str = ""
    confidence: float = 0.0
    status: str = ""
    validated: bool = False
    oracle_passed: bool = False
    rejection_reason: list[str] = field(default_factory=list)

@dataclass
class IncrementalStepResult:
    step_num: int
    action: str
    status: str
    original_locator: str = ""
    selected_locator: str = ""
    value: str = ""
    precondition: Optional[PreconditionResult] = None
    postcondition: Optional[PostconditionResult] = None
    healing: dict = field(default_factory=dict)
    error_message: str = ""
    evidence_before: dict = field(default_factory=dict)
    evidence_after: dict = field(default_factory=dict)
    duration_ms: int = 0
```

### 4.2. Implementar `_primary_selector`

```python
def _primary_selector(self, step) -> str:
    if step.target and step.target.candidates:
        return step.target.candidates[0].selector or ""
    return ""
```

### 4.3. Implementar `_make_curator`

```python
def _make_curator(self, catalog=None, step_runner=None):
    if step_runner is None:
        smart_runner = SmartStepRunner(self.page)

        def step_runner(step_data: dict):
            strategy = step_data.get("strategy", "")
            return smart_runner.execute(step_data, strategy)

    return CuradorAutomatico(
        catalog=catalog or HealingCatalog(),
        step_runner=step_runner,
    )
```

### 4.4. Implementar `_heal_failed_step`

Usar o fluxo completo descrito no Épico 5, História 5.4.

### 4.5. Implementar validação de proposta

Rejeitar:

```text
missing_outcome
missing_new_locator
low_confidence
missing_family
missing_taxonomy_id
missing_strategy
generic_or_dangerous_locator
incompatible_action_strategy
same_locator_as_failed_original
```

### 4.6. Implementar validação com Oracle

Regra:

```text
Só chamar ORACLE_VALIDATED se postcondition.passed == True.
```

### 4.7. Implementar sequência

Pseudocódigo:

```python
for i, step in enumerate(self.steps):
    result = self._run_one_step(i, step)
    self.step_results.append(result)

    if result.status in ("failed", "healing_rejected") and step.blocking:
        self.failed_step_indices.add(i)

    if self.stop_on_failure and result.status in ("failed", "healing_rejected"):
        break
```

---

## 5. Plano de testes consolidado

### 5.1. Testes unitários obrigatórios

```bash
python -m pytest tests/test_incremental_step_result.py -v
python -m pytest tests/test_step_precondition.py -v
python -m pytest tests/test_step_executor.py -v
python -m pytest tests/test_step_postcondition.py -v
python -m pytest tests/test_incremental_curator.py -v
python -m pytest tests/test_incremental_curator_proposal.py -v
python -m pytest tests/test_incremental_heal_failed_step.py -v
python -m pytest tests/test_incremental_metrics.py -v
python -m pytest tests/test_incremental_report.py -v
python -m pytest tests/test_incremental_sequence.py -v
```

### 5.2. Testes de integração obrigatórios

```bash
python -m pytest tests/test_pages/test_incremental_true_healing.py -v
python -m pytest tests/test_pages/test_incremental_false_healing.py -v
python -m pytest tests/test_pages/test_incremental_select_option.py -v
python -m pytest tests/test_pages/test_incremental_dependencies.py -v
```

### 5.3. Verificações manuais mínimas

```bash
testforge run-incremental semantic_tests/ST-demo/test_st_demo.py --headless --verbose
```

Verificar:

- O terminal mostra step por step.
- Steps curados aparecem como `healed_validated`.
- Falso healing aparece como `healing_rejected`.
- Relatório JSON é criado.
- Relatório Markdown de healing é criado.
- Métricas batem com a execução.

---

## 6. Cenários de teste essenciais

### Cenário A — Healing verdadeiro

Dado:

```html
<button id="btnNovo">Pesquisar</button>
<div id="resultado" style="display:none"></div>
<script>
  document.getElementById("btnNovo").addEventListener("click", () => {
    document.getElementById("resultado").style.display = "block";
    document.getElementById("resultado").textContent = "CPF consultado";
  });
</script>
```

Step original:

```text
click #btnAntigo
```

Esperado:

```text
Curador propõe/clica em botão por texto.
Oracle encontra "CPF consultado".
Status = healed_validated.
Métricas: failure_detected=1, healing_attempted=1, applied=1, validated=1, rejected=0.
```

### Cenário B — Falso healing

Dado:

```html
<button>Pesquisar</button>
<div id="resultado">Resultado errado</div>
```

Step original:

```text
click #btnAntigo
```

Esperado:

```text
Curador executa proposta.
Oracle não encontra "CPF consultado".
Status = healing_rejected.
Métricas: failure_detected=1, healing_attempted=1, applied=1, validated=0, rejected=1.
```

### Cenário C — Select option

Dado:

```html
<label for="lstUf">UF</label>
<select id="lstUf" name="lstUf">
  <option value="">Selecione</option>
  <option value="MT">MT</option>
</select>
```

Step:

```text
select_option select[name="lstUf"] value MT
```

Esperado:

```text
Pré-condição valida que é select.
Execução usa select_option.
Pós-condição confirma selected value = MT.
```

### Cenário D — Dependência bloqueada

Dado:

```text
Step 1 blocking falha e não cura.
Step 2 depends_on step_0001.
```

Esperado:

```text
Step 1 = failed ou healing_rejected.
Step 2 = blocked.
Step 2 não conta como falha independente.
```

---

## 7. Ordem recomendada para implementar até amanhã

### Bloco 1 — Estrutura e comando

1. Criar `step_result.py`.
2. Criar `incremental_runner.py` mínimo.
3. Adicionar CLI `run-incremental`.
4. Testar carregamento de script e steps.

### Bloco 2 — Pré, execução e pós

5. Criar `StepPreconditionValidator`.
6. Criar `StepExecutor`.
7. Criar `StepPostconditionValidator`.
8. Testar click/fill/select/assert.

### Bloco 3 — Healing com Curador

9. Implementar `_make_curator`.
10. Implementar `_build_healing_payload`.
11. Implementar `_validate_curator_proposal`.
12. Implementar `_heal_failed_step`.
13. Implementar `_validate_healing_with_oracle`.

### Bloco 4 — Métricas e sequência

14. Registrar métricas por step.
15. Implementar `_run_one_step`.
16. Implementar bloqueio de dependentes.
17. Testar múltiplos steps em sequência.

### Bloco 5 — Relatórios

18. Criar `execution_report.json`.
19. Criar `healing_report.md`.
20. Criar `metrics.json`.
21. Rodar suíte incremental.

---

## 8. Prompt para a próxima LLM implementar

Use este prompt como entrada para outra LLM:

```text
Você é uma LLM desenvolvedora atuando no projeto TestForge.

Contexto:
- O TestForge grava interações web e gera scripts Playwright Python.
- O projeto já possui CuradorAutomatico, SmartStepRunner, EvidenceCollector, OracleRunner, PromotionGate e MetricsRepository.
- O objetivo agora é implementar o executor incremental `run-incremental`.
- Não implementar MCP RTC/RQM/RDNG, MCP mestre nem SpecKit.
- Dados sensíveis devem gerar alerta, não mascaramento automático.

Objetivo:
Implementar um fluxo incremental de execução que rode cada step com:
1. pré-condição;
2. execução;
3. pós-condição/oracle;
4. evidência before/after;
5. healing com CuradorAutomatico;
6. validação do healing com oracle;
7. métricas por step;
8. relatório JSON/Markdown.

Regras obrigatórias:
- CuradorAutomatico retornando PASSED_STEP não significa healing verdadeiro.
- Healing verdadeiro só ocorre se o Oracle/pós-condição passar.
- PASSED_STEP + Oracle falho deve virar healing_rejected.
- PASSED_STEP + Oracle aprovado deve virar healed_validated.
- PromotionGate só deve rodar depois de healed_validated.
- Métricas devem separar failure_detected, healing_attempted, healing_applied, oracle_validated e healing_rejected.

Arquivos a criar:
- src/testforge/runner/incremental_runner.py
- src/testforge/runner/step_executor.py
- src/testforge/runner/step_precondition.py
- src/testforge/runner/step_postcondition.py
- src/testforge/runner/step_result.py
- src/testforge/runner/incremental_ui.py, se necessário

Arquivos a alterar:
- src/testforge/cli/app.py
- src/testforge/reporting/run_report.py, se necessário
- tests/ com novos testes incrementais

Implementar todos os épicos, histórias, tarefas, critérios de aceite e testes descritos no documento TestForge — Plano Autocontido para Implementação do Executor Incremental, Healing Validado e Relatórios.

Ao final, rodar:
python -m pytest tests/test_incremental_* -v
python -m pytest tests/test_pages/test_incremental_* -v
python -m pytest tests/ -q
```

---

## 9. Definição de pronto

A entrega estará pronta quando:

```text
[ ] `testforge run-incremental` existir.
[ ] O executor carregar steps a partir da gravação/script.
[ ] Cada step tiver pré-condição.
[ ] Cada step tiver pós-condição.
[ ] `_make_curator` funcionar com SmartStepRunner.
[ ] `_heal_failed_step` chamar CuradorAutomatico.
[ ] Oracle validar healing verdadeiro.
[ ] Falso healing for rejeitado.
[ ] Métricas por step forem registradas.
[ ] Relatórios JSON e Markdown forem gerados.
[ ] Sequência continuar após healed_validated.
[ ] Sequência bloquear dependentes após failed/healing_rejected blocking.
[ ] Todos os testes incrementais passarem.
```

---

## 10. Frase-guia para implementação

> O CuradorAutomatico responde: “consegui executar uma alternativa?”  
> O IncrementalRunner responde: “essa alternativa resolveu o step?”  
> O Oracle responde: “o efeito esperado apareceu?”  
> O PromotionGate responde: “essa cura pode virar aprendizado?”

Apendice:
Histórico das interações com llm
acabamos de aplicar inúmeras mudanças no nosso projeto e queremos alinhar quais são os próximos passos necessários. A possibilidade que me atraí mais é: adicionar um fluxo que irá adicionar ao projeto a opção de, ao final de cada gravação, enviar os arquivos gerados. Com isso queremos que os usuário comecem a testar gravando em diversos ambientes enquanto a gente tenta compilar os script, curar os erros e aprender com o processo. Por hora gere o script que irá fazer uma apanhado de todos os dados necessários do projeto como arquivo de código fonte, arquivos de gravação, documentação e o resumo da llm que está em doc. Junte tudo em um arquivo só
Copilot said:
Copilot

Processamento concluído em 5 etapas
Perfeito, Andre. Gerei um script Python pronto para uso que faz exatamente esse “apanhado” do projeto: junta em um único arquivo Markdown os dados relevantes para análise por LLM, incluindo código-fonte, gravações, testes semânticos, documentação e o resumo da LLM quando estiver em .docx, .md, .txt etc.

Arquivo para download:

Baixar gerar_apanhado_projeto.py

O que o script faz
Ele gera um arquivo único, por padrão apanhado_projeto.md, contendo:

árvore dos arquivos incluídos;
resumo por categoria;
arquivos de código-fonte;
arquivos de gravação;
arquivos de semantic_tests;
documentação em docs, doc, documentation, adr, arquitetura;
arquivos relacionados a prompts/resumos de LLM;
metadados por arquivo:
caminho;
categoria;
tamanho;
data de modificação;
SHA-256;
conteúdo textual embutido em blocos Markdown;
extração textual de .docx usando apenas biblioteca padrão do Python.
Como usar no TestForge
Na raiz do projeto:




PowerShell
python gerar_apanhado_projeto.py --root . --output apanhado_testforge.md
Uso mais direcionado ao nosso cenário atual:




PowerShell
python gerar_apanhado_projeto.py --root . --output apanhado_testforge.md --focus src tests recordings semantic_tests docs doc documentation prompts adr arquitetura
Se quiser varrer o projeto inteiro, respeitando exclusões como .git, .venv, node_modules, __pycache__, dist, build etc.:




PowerShell
python gerar_apanhado_projeto.py --root . --output apanhado_testforge.md --all
Se algum arquivo for grande demais e você quiser aumentar o limite de conteúdo embutido por arquivo:




PowerShell
python gerar_apanhado_projeto.py --root . --output apanhado_testforge.md --max-file-mb 5
Observações importantes
Arquivos .docx são lidos e o texto é extraído automaticamente.
Arquivos .doc antigos/binários são apenas inventariados, porque extraí-los de forma confiável exigiria dependência externa ou conversão para .docx.
Imagens, vídeos, bancos SQLite, ZIPs e binários são inventariados, mas o conteúdo não é embutido.
O resultado final é ideal para enviar para uma LLM analisar o estado do projeto, curar erros e entender o que foi gravado.
Próximo passo recomendado
Depois desse script, o próximo incremento natural é criar no TestForge um comando tipo:




PowerShell
testforge collect-context --output apanhado_testforge.md
e, na sequência, acoplar isso ao fluxo pós-gravação:




Plain Text
fim da gravação
    -> gerar arquivos da gravação
    -> gerar apanhado/contexto do projeto
    -> perguntar se deseja enviar/compartilhar pacote
    -> registrar metadados da submissão
Isso casa bem com a ideia de colocar usuários gravando em vários ambientes enquanto a equipe compila scripts, cura falhas e aprende com os casos reais.










md
apanhado_projeto
You said:
O que podemos fazer pra estabilisar o projeto? Ontem ficamos a noite toda para ele passar de um campo de data e preencher um valor e clicar em um botão. Está absurdo executar um fluxo gravado. A cada passo novo paramos e não conseguimos superar
Copilot said:
Copilot
Andre, o que você descreveu não é um bug isolado — é um sintoma clássico de pipeline base instável. E o material do teu próprio projeto confirma isso: vocês estão batendo diretamente nos Bugs P0 estruturais, não em problemas pontuais.
sharepoint

Vou ser direto e pragmático (nível “sobrevivência do projeto”):

🚨 Diagnóstico real (por que está impossível avançar)
O problema não é o fluxo.

O problema é que cada camada da pipeline está vazando erro ao mesmo tempo:

1. Recorder gera evento errado
<select> vira click ou fill
campo de data vira sequência de eventos inválidos
2. Normalização está suja
múltiplos fills para o mesmo campo
eventos duplicados / inconsistentes
3. Compilador gera script errado
seletor incompatível
estratégia inadequada para o tipo de elemento
4. Runner não consegue executar de forma confiável
browser instável (ambiente corporativo)
falta de fallback robusto
👉 Resultado:

cada novo campo = novo ponto de falha = vocês "paramam e brigam com o sistema"

✔️ Isso bate 100% com os sintomas que você descreveu
✔️ E bate com os Bugs P0 documentados
sharepoint

🧠 Mudança crítica de mentalidade (senão vai travar sempre)
Hoje vocês estão operando assim:

“vamos rodar um fluxo real e ir corrigindo”

🚫 Isso NÃO funciona enquanto a base não estiver estável

✅ Vocês precisam mudar para:

“vamos estabilizar a pipeline mínima com 1 fluxo controlado”

✅ Plano de estabilização (ordem certa — sem isso não anda)
🔵 Fase 1 — “Pipeline mínima confiável”
Escolham UM fluxo bem simples:

abrir página
preencher 1 campo
clicar 1 botão
E só.

Agora validem:

✅ Critérios obrigatórios (não negocia)
grava → compila → executa sem intervenção manual
script roda do início ao fim
logs fazem sentido
step count consistente
Se isso falhar → não avancem

🔴 Fase 2 — corrigir os 3 bugs que estão te matando
Baseado no apanhado:

🎯 BUG CRÍTICO #1 – SELECT incorreto
Esse aqui sozinho já explica seu problema de data/form

✔️ Regra:




Python
page.select_option("select[name='campo']", "valor")
❌ Nunca:




Python
click + fill em select
📌 Isso quebra metade dos fluxos

🎯 BUG CRÍTICO #2 – múltiplos fills (ruído)
Hoje deve estar assim:

fill "1"
fill "12"
fill "12/0"
fill "12/05"
fill "12/05/2026"
✔️ Correto:

fill "12/05/2026"
👉 Sem isso:

script vira lixo
debugging impossível
🎯 BUG CRCRÍTICO #3 – step inconsistente
Se o recorder mostra 1 passo e executa 10: 👉 você nunca consegue debugar

✔️ Precisa alinhar:

raw_events
semantic_steps
script final
🟡 Fase 3 — estabilidade do browser
Ambiente CAIXA = problema real

✔️ Implementar fallback automático:

chromium
edge
chrome
CDP
Sem isso:

você nunca sabe se o bug é do sistema ou do ambiente
🧪 Estratégia que vocês NÃO estão usando (e precisam)
Hoje vocês estão testando no sistema real.

🚫 Péssimo para estabilizar

✅ Façam isso:

Criem uma página de teste controlada com:

input simples
select
date
botão
👉 Validem TODA a pipeline nela

Só depois voltem para o sistema real.

⚙️ Regra de ouro (evita noites perdidas)
Nunca mais sigam esse fluxo:

gravação → tenta rodar → quebra → corrige → tenta de novo

✅ Substituam por:

1. grava
2. inspeciona artefatos (raw_events, steps, script)
3. valida coerência
4. executa
📉 Por que vocês ficaram travados ontem
Porque estavam tentando resolver isso:

UI real complexa
+ seletor errado
+ evento sujo
+ script inconsistente
+ browser instável
👉 impossível vencer isso na força bruta

✅ Estado que vocês precisam alcançar (meta)
Quando estiver certo, deve acontecer isso:

record → compile → run
✅ passa do início ao fim
✅ sem intervenção
✅ replicável
E só então:

adiciona campo novo
adiciona step novo
💡 Recomendação estratégica (importante)
Você mesmo já percebeu isso nos outras conversas:

arquitetura enxuta = caminho de execução

👉 Esse é o momento de aplicar isso

🔥 Ignore totalmente por agora:

LLM
self-healing avançado
taxonomia complexa
👉 Isso é “luxo” enquanto a base quebra

🎯 Próximo passo (claro e acionável)
Faça isso AGORA:

Pegue 1 fluxo mínimo (1 input + 1 botão)
Ajuste:
select_option correto
deduplicação de fills
step count consistente
Rode até passar 100% sem intervenção
Se quiser, posso fazer o próximo passo contigo de forma cirúrgica:

👉 pegar um exemplo real teu (raw_events ou script atual)
👉 apontar exatamente onde está quebrando
👉 e te devolver a versão corrigida

Isso acelera absurdamente a estabilização.

Fontes








You said:
Nós já criamos um monte de páginas para testar a taxonomia. Para essas páginas elas funcionam. Mas essas páginas são só imitação. Qual a diferença entre gravar um fluxo completo e ir executando passo 1 e para, depois passo 1 e passo 2 e para e ir continuando assim até o fim? Dessa forma podemos unir a forçar das gravações que devem, agora, estar estabilizada, dado que gravamos a intenção e pegamos o máximo de informação, e não geramos o script propriamente dito e, criamos esses scripts que vão incrementalmente sendo executados. O que acha disso?
Copilot said:
Copilot
Andre, essa ideia que você trouxe é muito forte — e vou te dizer direto: ela resolve exatamente o principal problema que vocês estão enfrentando hoje.

Vou estruturar a análise com base no que já temos no projeto.

🔍 1. O que existe hoje (baseline)
Pelo que está documentado:

O pipeline atual é: gravar → compilar → gerar script → executar → healing
meus prompts
A gravação é:
rica em intenção ✅
mas ainda gera script frágil ou incorreto ❌
bugs
E na prática vocês estão vendo:

“não conseguimos rodar um fluxo simples ponta a ponta”

⚖️ 2. Diferença conceitual (o ponto chave da sua pergunta)
✅ Abordagem atual (fluxo completo)
Você grava tudo → gera um script grande → tenta executar tudo de uma vez

Problemas:
acoplamento alto
erro em um step quebra tudo
difícil diagnosticar (onde falhou?)
nenhum feedback incremental
healing atua tarde demais
✅ Abordagem que você propôs (incremental)
Executa:

step 1 → valida → 
step 1+2 → valida → 
step 1+2+3 → valida → ...
Mudança fundamental:
👉 Você transforma o problema de"executar fluxo" 👉 num problema de"validar step a step"

🧠 3. O insight mais importante (isso aqui muda o jogo)
Essa sua abordagem separa dois problemas que hoje estão misturados:

Antes (misturado):
geração do script
execução
validação
healing
Depois (separado):
✅ intenção (gravação)
✅ execução incremental
✅ validação por step
✅ aprendizagem contínua
🚀 4. Por que isso é MUITO melhor (técnico)
🔹 4.1 Isolamento de falha
Hoje:

falha no step 15 → você não sabe se é:
step 15
efeito acumulado dos 14 anteriores
Com incremental:

falhou no step 3 → causa clara
🔹 4.2 Healing mais inteligente
Hoje:

healing tenta "salvar o fluxo inteiro"
Com incremental:

healing vira:
local, contextual e rastreável
Isso encaixa perfeitamente com a ideia do curador:

cada falha tem entrada, saída e sucesso definidos
testforge_curador_cap1-1

🔹 4.3 Geração de evidência natural
Você ganha automaticamente:

evidência por step
histórico de sucesso
mapa de falhas por posição
👉 Isso alimenta direto:

ranking de locators
score de estabilidade
promotion gate
🔹 4.4 Compatível com sua arquitetura de intenção
Na Documentação Iniciativa Playcode AI_V0:

a intenção vira input do compilador
Documentação Iniciativa Playcode AI_V0
Sua ideia dá um passo além:

👉 você não precisa compilar tudo imediatamente

Você passa a:

intenção → execução direta (interpretador)
⚠️ 5. O risco (tem um!)
Se fizer errado, você cai em:

❌ modo "replay burro"
repetir eventos sem entender estado
pseudo-gravação frágil
Mas dá pra evitar com 2 regras:

✅ 6. Como tornar essa abordagem sólida (regras de ouro)
🔹 Regra 1 — step precisa ter contexto
Cada step precisa carregar:




JSON
{
  "action": "click",
  "intent": "clicar em salvar",
  "pre_state": "...",
  "expected_post_state": "botão desabilitado ou navegação",
}
🔹 Regra 2 — precisa validar após cada step
Sem isso você só está fazendo replay incremental.

Você precisa:

👉 Oracle pós-ação (leve)

Ex:

elemento desapareceu
valor foi preenchido
página mudou
botão ficou enabled
🔹 Regra 3 — persistir histórico por step
Isso desbloqueia:

score de locator
ranking de fallback
confiança
🔹 Regra 4 — permitir substituição local
Se step falhar:

você NÃO recalcula o fluxo
você ajusta só aquele step
🧩 7. O grande insight arquitetural
O que você está propondo é na prática:

👉 Um INTERPRETADOR de testes
(e não um compilador)

Antes:
Gravação → Compilador → Script → Execução
Depois:
Gravação → Interpretador incremental → Execução + aprendizado
💡 8. Impacto real no TestForge
Essa abordagem resolve diretamente vários bugs que você listou:

❌ steps inconsistentes
❌ script inválido
❌ falha no meio do fluxo
❌ falta de assert
❌ duplicidade
👉 porque você elimina o "big bang execution"

🧠 9. Minha opinião direta
👉 Essa é provavelmente a melhor direção que vocês já levantaram até agora.

Mas com um refinamento importante:

✅ 10. Versão ideal da sua ideia
Não use:

incremental apenas para execução

Use:

👉 incremental + aprendizado + validação
🔥 11. Nome disso (pra clareza interna)
Você acabou de descrever:

👉 “Execution-first architecture”
ou

👉 “Stepwise adaptive execution engine”
✅ Conclusão
✔️ Sim, sua ideia é correta
✔️ Resolve o principal gargalo atual
✔️ Reduz brutalmente complexidade
✔️ Conecta perfeitamente com self-healing
✔️ Forma base para evolução futura com LLM

🚀 Próximo passo natural
Se quiser, posso te ajudar a transformar isso em:

arquitetura (componentes)
fluxo detalhado
pseudo-código do executor incremental
ou já gerar um MVP em Python
👉 Quer que eu desenhe o “Executor incremental do TestForge” com interface e fluxo completo?

Fontes
docx








You said:
Desenhe o executor incremental com fluxo e interfaceForneça pseudo-código para execução incrementalExplique como implementar validação passo a passo
Copilot said:
Copilot
Perfeito — vou estruturar isso como um artefato de arquitetura executável, no nível que você precisa para já começar a implementar no TestForge.

Vou dividir em 3 partes:

🔷 Arquitetura + fluxo do Executor Incremental
🔷 Interface (contratos principais)
🔷 Pseudo-código completo
🔷 Validação passo a passo (como implementar de verdade)
🔷 1. Arquitetura do Executor Incremental
🧠 Visão geral (o que você está construindo)
Recording (intenção)
        ↓
Incremental Executor (interpreta)
        ↓
Step Runner
        ↓
Validator (oracle leve)
        ↓
Evidence + Metrics + History
        ↓
(Se falhar) Healing local
🔁 Fluxo de execução



Mermaid
flowchart TD

A[Recording / Steps] --> B[Loop Incremental]

B --> C[Seleciona Step N]
C --> D[Resolve Locator Candidates]
D --> E[Executa Step]

E --> F[Validação Pós-Ação]

F -->|✅ Sucesso| G[Persistir Evidência + Score]
F -->|❌ Falha| H[Healing Local]

H --> I[Reexecutar Step]
I --> F

G --> J[Avança para próximo Step]

J -->|Se último| K[Finalizar Execução]
J -->|Senão| C

Mostrar mais linhas
💡 Ideia chave
👉 Você não executa um script
👉 Você executa uma lista de intenções validadas incrementalmente

🔷 2. Interface (contratos principais)
✅ 2.1 Step (unidade de execução)



Python
class Step:
    id: str
    action: str  # click, fill, select...
    intent: str  # "clicar no botão salvar"

    target: dict  # informações semânticas do elemento
    candidates: list[LocatorCandidate]

    input_data: any

    pre_state: dict | None
    expected_post_state: dict | None
✅ 2.2 LocatorCandidate



Python
class LocatorCandidate:
    strategy: str
    value: any
    playwright_expr: str

    score: float
    success_rate: float
    last_success: datetime | None
✅ 2.3 ExecutionResult



Python
class ExecutionResult:
    success: bool
    error: Exception | None
    locator_used: LocatorCandidate | None

    dom_snapshot: str
    screenshot_path: str | None

    duration_ms: int
✅ 2.4 ValidationResult



Python
class ValidationResult:
    success: bool
    signals: list[str]  # "element_found", "value_set", etc.
    confidence: float
✅ 2.5 HistoryStore (essencial!)



Python
class HistoryStore:
    def record(step_id, locator, success)
    def get_best_candidates(step_id) -> list[LocatorCandidate]
🔷 3. Pseudo-código (Executor Incremental)
Agora o coração do sistema.

✅ 3.1 Loop principal



Python
def execute_incremental(test_case):

    state = ExecutionState()

    for step in test_case.steps:

        result = execute_step_with_healing(step, state)

        if not result.success:
            return ExecutionSummary(failed_step=step.id)

    return ExecutionSummary(success=True)
✅ 3.2 Execução com healing



Python
def execute_step_with_healing(step, state):

    candidates = rank_candidates(step)

    for candidate in candidates:

        result = try_execute(step, candidate)

        validation = validate_step(step, result)

        if validation.success:

            persist_success(step, candidate, result)
            return result

        else:
            persist_failure(step, candidate, result)

    # fallback: chamar LLM / heurística
    healed_candidate = heal(step)

    if healed_candidate:
        return try_execute(step, healed_candidate)

    return ExecutionResult(success=False)

Mostrar mais linhas
✅ 3.3 Execução real do step



Python
def try_execute(step, candidate):

    locator = resolve(candidate)

    try:
        if step.action == "click":
            locator.click()

        elif step.action == "fill":
            locator.fill(step.input_data)

        elif step.action == "select":
            locator.select_option(step.input_data)

        return ExecutionResult(
            success=True,
            locator_used=candidate,
            dom_snapshot=capture_dom()
        )

    except Exception as e:
        return ExecutionResult(
            success=False,
            error=e,
            locator_used=candidate
        )

Mostrar mais linhas
🔷 4. Como implementar validação passo a passo (CRÍTICO)
Isso é o ponto mais importante do sistema.

Sem isso → você só tem replay.

✅ 4.1 Regra principal
👉 Cada step precisa ter um oracle mínimo verificável

✅ 4.2 Tipos de validação (práticos)
🔹 Tipo 1 — Actionability básica
(usado em todos os steps)




Python
def validate_actionability(result):
    return result.success
🔹 Tipo 2 — Validação por efeito direto
Exemplo 1: click



Python
def validate_click(step, result):

    return any([
        element_disappeared(step),
        url_changed(),
        new_element_visible(),
        button_disabled()
    ])
Exemplo 2: fill



Python
def validate_fill(step, result):

    value = get_element_value(step)

    return value == step.input_data
Exemplo 3: select



Python
def validate_select(step, result):

    selected = get_selected_option(step)

    return selected == step.input_data
✅ 4.3 Oráculo genérico (fallback)



Python
def generic_post_action_oracle(before, after):

    if before.dom != after.dom:
        return True

    if before.url != after.url:
        return True

    return False
✅ 4.4 Validação composta (recomendada)



Python
def validate_step(step, result):

    checks = []

    checks.append(validate_actionability(result))

    if step.action == "click":
        checks.append(validate_click(step, result))

    elif step.action == "fill":
        checks.append(validate_fill(step, result))

    elif step.action == "select":
        checks.append(validate_select(step, result))

    success = any(checks)

    return ValidationResult(
        success=success,
        confidence=len([c for c in checks if c]) / len(checks)
    )

Mostrar mais linhas
✅ 4.5 Persistência de aprendizado



Python
def persist_success(step, candidate, result):

    history.record(
        step_id=step.id,
        locator=candidate,
        success=True
    )

def persist_failure(step, candidate, result):

    history.record(
        step_id=step.id,
        locator=candidate,
        success=False
    )

Mostrar mais linhas
🔥 5. O que isso destrava imediatamente
Com esse executor:

✔️ Você não depende mais do compilador
✔️ Você começa a rodar fluxos reais HOJE
✔️ Healing vira local e simples
✔️ Você gera dados reais para score de locator
✔️ Você consegue medir falso healing (finalmente)

🧠 6. Próximo passo sugerido (altamente recomendado)
Se você quiser avançar rápido:

👉 Próximo artefato ideal é:

🔷 "ExecutionState + Context Engine"
Com:

estado da página
histórico de steps
contexto para healing
cache de locators resolvidos
✅ Conclusão
Você acabou de definir:

✔️ o runtime real do TestForge
✔️ substituto do modelo “script first”
✔️ base para self-healing confiável

Se quiser, posso te entregar o próximo nível:

👉 implementação já em Python (Playwright) pronta para rodar
👉 ou integração disso com o EvidenceCollector + PromotionGate que vocês já têm planejado

---------------------------------------------------------------------------------------------------------------------

Ontem tentamos, inúmera vezes, corrigir erros que vão surgindo em cada passo. Hoje pensamos em solucionar isso da seguinte forma: alterar a forma do compilador para um interpretador que irá, testar a gravação passo a passo. Conversamos sobre isso em um prompt aqui e pareceu bem crível e que iria, aparentemente, produzir resultados rápidos dado que a gente transformou o gravador em gravação de intenção que irá permitir que não precisemos mais alterar o gravador o que irá possibilitar que distribuiremos nosso gravador para a equipe começar a gravar os sistemas e gerar uma massa para podermos progredir rapidamente. Precisamos mudar nossa arquitetura para ir testantando incrementalmente cada passo da execução (pegar o script grande e executar só o passo 1, depois executar só o passo 1 e 2, depois só executar o 1, 2 e 3... até executarmos ele todo). Queremos aprender com cada correção e execução e queremos que todas as gravações e logs sejam enviadas para o nosso repositório para podermos ter insumos para nosso aprimoramento. Agora quero que você estude nosso projeto atual e critique ele, valide se essa ideia consegue parar em pé, se existe, hoje em dia, estudos que já fazem o que queremos fazer, pesquise sobre as melhores práticas de gravação, de testes automatizados, de selfhealing. Produza um plano de incremento para nossa aplicação. Desenhe o executor incremental com fluxo e interfaceForneça pseudo-código para execução incrementalExplique como implementar validação passo a passo
Mostre o código Python do executor incrementalExplique como integrar o executor com self-healingDetalhe o fluxo de validação passo a passo
Copilot said:
Copilot

Processamento concluído em 11 etapas
Andre, analisei o apanhado_projeto e também fiz uma busca no M365 sobre TestForge/executor incremental; a busca interna retornou“Several emails”, 26 reuniões e centenas/milhares de resultados em arquivos, com destaque para apanhado_projeto, BUGS_UNICOS_POR_CONTEUDO, project_context e discussões anteriores sobre gravação manual como origem do script. A busca web que tentei para Playwright/debug/self-healing retornou resultados expirados nesta chamada, então não vou fingir citação externa; vou tratar “estado da arte” como análise técnica baseada em práticas conhecidas de automação UI, Playwright, record/replay, trace/debug step-by-step e self-healing com oráculo.
sharepoint
+3

1. Minha conclusão direta
Sim: a ideia para em pé. E mais: ela parece ser o próximo movimento correto para o TestForge.

Mas eu faria uma distinção importante:

Não é substituir o compilador por um interpretador.
É mudar o centro de gravidade do projeto: o artefato principal deixa de ser o “script Python grande gerado” e passa a ser o teste semântico interpretável, executado passo a passo.

O compilador pode continuar existindo como saída opcional, para gerar Playwright Python legível. Mas o caminho mais robusto para estabilizar agora é:




Plain Text
recording bruto
→ normalização
→ semantic_steps.jsonl
→ executor interpretado incremental
→ evidências por step
→ healing controlado
→ aprendizado versionado
→ opcionalmente gerar script final estável
Isso ataca exatamente a dor que você descreveu: ontem vocês ficavam “apagando incêndio” erro por erro dentro de um fluxo grande. O executor incremental transforma isso em um processo controlado:




Plain Text
executa 1
executa 1..2
executa 1..3
executa 1..4
...
executa 1..N
Com isso, cada correção tem contexto, evidência, log, tela, DOM, rede, candidato de locator, tentativa de healing e validação pós-ação.

2. Crítica ao projeto atual
O apanhado_projeto mostra um projeto já bem avançado: TestForge v0.3.1, com gravador inteligente, MIS, compilador Playwright, runner, evidence, oracle, promotion gate, taxonomia, métricas e healing L0→L3. A estrutura inventariada inclui 130 arquivos, com 47 arquivos de código-fonte, 44 testes, documentação, resumos LLM, configurações e artefatos relevantes do projeto.
sharepoint
+1
sharepoint

O problema não parece mais ser “faltam peças”. O problema é que o pipeline ainda está muito acoplado ao modelo:




Plain Text
gravar → compilar script grande → executar tudo → descobrir erro tarde
Esse modelo é ruim para sistemas corporativos reais porque um erro no passo 4 contamina os passos 5, 6, 7, 8… e depois vocês perdem tempo tentando curar efeitos colaterais, não a causa raiz.

Os próprios bugs documentados apontam para isso: há problemas de <select> virando input, DOM snapshots vazios, contagem divergente entre gravação/compilação/execução, event_id reiniciando, sessões misturadas, goto() excessivo, métricas inconsistentes e falhas em cascata.
sharepoint

A frase mais importante da análise anterior continua válida:

O maior bug não é “o seletor falhou”.
O maior bug é que o contrato entre raw_events, steps, semantic_steps, script, runner e métricas ainda não está suficientemente estável.
sharepoint

O executor incremental é uma forma prática de estabilizar esse contrato sem ficar reescrevendo o gravador a cada novo comportamento estranho.

3. Por que o interpretador incremental é melhor agora
3.1. Ele reduz erro em cascata
Hoje, se o passo “selecionar UF” falha no SIMAX, os passos “selecionar Edifício”, “selecionar Data” e “Reservar” também falham. Isso gera ruído. O executor incremental deve marcar os passos dependentes como:




Plain Text
blocked_by_previous_failure
em vez de tratá-los como falhas independentes.

3.2. Ele transforma debugging em processo
Em vez de executar um script inteiro e receber 15 falhas, vocês recebem:




Plain Text
Run 001 — steps 1..1 — PASS
Run 002 — steps 1..2 — PASS
Run 003 — steps 1..3 — PASS
Run 004 — steps 1..4 — FAIL — causa real
Isso muda a conversa. A correção deixa de ser tentativa e erro e passa a ser diagnóstico progressivo.

3.3. Ele combina muito bem com gravação por intenção
A decisão de transformar o gravador em “gravação de intenção” foi correta. Agora, a execução também precisa ser orientada por intenção.

Em vez de o TestForge depender do script compilado:




Python
page.click("label:has-text('UF') + input")
ele deve interpretar:




JSON
{
  "action": "select_option",
  "intent": "selecionar UF",
  "target": {
    "tag": "select",
    "name": "lstUf",
    "label": "UF"
  },
  "value": "MT"
}
A partir disso, o executor decide como agir.

3.4. Ele gera massa de aprendizado real
A ideia de distribuir o gravador para a equipe começar a gravar sistemas é excelente, desde que cada gravação gere:

raw_events.jsonl
semantic_steps.jsonl
incremental_report.json
run_report.json
screenshots
DOM snapshots
network logs
healing attempts
alertas de dados sensíveis, sem mascaramento automático neste MVP, conforme vocês decidiram anteriormente
Isso cria insumo real para melhorar locator engine, normalizador, heurísticas por framework e self-healing.

4. Ajuste arquitetural recomendado
4.1. Antes



Plain Text
QA grava
  ↓
raw_events.jsonl
  ↓
normalizer
  ↓
compiler
  ↓
script Python grande
  ↓
runner executa script
  ↓
healing quando falha
4.2. Depois



Plain Text
QA grava intenção
  ↓
raw_events.jsonl
  ↓
normalizer
  ↓
semantic_steps.jsonl  ← artefato principal
  ↓
incremental interpreter
  ↓
step runner + locator engine + self-healing
  ↓
oracle pós-ação
  ↓
evidence store + reports + catálogo de aprendizado
  ↓
compiler opcional gera script final estabilizado

Mostrar mais linhas
4.3. Diagrama de fluxo



Mermaid
flowchart TD
    A[Recording bruto] --> B[Normalizer]
    B --> C[semantic_steps.jsonl]
    C --> D[Executor Incremental]

    D --> E1[Rodada 1: steps 1..1]
    D --> E2[Rodada 2: steps 1..2]
    D --> E3[Rodada 3: steps 1..3]
    D --> EN[Rodada N: steps 1..N]

    E1 --> V[Validação por step]
    E2 --> V
    E3 --> V
    EN --> V

    V -->|passou| R[Registrar evidência]
    V -->|falhou| H[Self-healing L0/L1/L2/L3]
    H --> O[Oracle pós-ação]
    O -->|validado| L[Aprender / registrar receita]
    O -->|não validado| P[Pendente de curadoria]

    R --> Repo[Repositório de evidências/logs]
    L --> Repo
    P --> Repo

Mostrar mais linhas
5. Interface recomendada
Eu criaria um novo comando, sem remover o run atual:




Shell
testforge run-incremental semantic_tests/ST-simax/semantic_steps.jsonl
Opções:




Shell
# Executa 1..N incrementalmente
testforge run-incremental semantic_tests/ST-simax/semantic_steps.jsonl

# Executa somente até um step específico
testforge run-incremental semantic_tests/ST-simax/semantic_steps.jsonl --until-step 7

# Para na primeira falha real
testforge run-incremental semantic_tests/ST-simax/semantic_steps.jsonl --stop-on-failure

# Continua mesmo após falha, marcando dependentes como blocked/skipped
testforge run-incremental semantic_tests/ST-simax/semantic_steps.jsonl --continue-after-failure

# Roda visível para debug
testforge run-incremental semantic_tests/ST-simax/semantic_steps.jsonl --headed

# Não aplica healing, só simula o que faria
testforge run-incremental semantic_tests/ST-simax/semantic_steps.jsonl --shadow-healing

# Aplica healing, mas só promove se oracle passar
testforge run-incremental semantic_tests/ST-simax/semantic_steps.jsonl --apply-healing

Mostrar mais linhas
Saída esperada:




Plain Text
[TestForge] Incremental run: ST-simax
[TestForge] Total semantic steps: 15

[Round 001] Executando steps 1..1
  ✓ Step 001 navigation — passed
  ✓ Oracle — passed
  ✓ Evidência salva em runs/ST-simax/round_001/

[Round 002] Executando steps 1..2
  ✓ Step 001 navigation — passed
  ✓ Step 002 click "Novo agendamento" — passed
  ✓ Oracle — passed

[Round 003] Executando steps 1..3
  ✓ Step 001 navigation — passed
  ✓ Step 002 click "Novo agendamento" — passed
  ✗ Step 003 select UF — failed
    Taxonomia: FAM-01 / SEL-004
    Locator original: label:has-text("UF") + input
    Candidato aprovado: select[name="lstUf"]
    Healing: applied
    Oracle pós-ação: passed
    Status: healed_validated

[TestForge] Aprendizado registrado: locator para intenção "selecionar UF"

Mostrar mais linhas
6. Pseudocódigo do executor incremental



Python
def run_incremental(test_case, options):
    total = len(test_case.steps)

    for round_until in range(1, total + 1):
        run_id = create_run_id(test_case.id, round_until)
        context = create_execution_context(run_id)

        open_browser(context)

        try:
            for step in test_case.steps[:round_until]:
                if is_blocked(step, context):
                    mark_blocked(step, context)
                    continue

                pre = validate_preconditions(step, context)
                if not pre.ok:
                    handle_failure(step, pre.error, context)
                    break

                result = execute_step_with_healing(step, context)

                save_step_evidence(step, result, context)

                if not result.ok:
                    if options.stop_on_failure:
                        break

                post = validate_postconditions(step, context)
                save_oracle_result(step, post, context)

                if not post.ok:
                    mark_possible_false_healing(step, context)
                    if options.stop_on_failure:
                        break

            save_round_report(context)

        finally:
            close_browser(context)

    save_incremental_summary()

Mostrar mais linhas
7. Código Python do executor incremental
Abaixo está uma versão inicial, pensada para entrar como:




Plain Text
src/testforge/runner/incremental_executor.py
Ela assume que vocês vão usar semantic_steps.jsonl como fonte principal. O código está deliberadamente simples para ser implementável rápido e evoluir depois.




Python
from __future__ import annotations

import json
import traceback
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from playwright.sync_api import sync_playwright, Page, Browser, TimeoutError as PlaywrightTimeoutError


@dataclass
class IncrementalOptions:
    headless: bool = True
    stop_on_failure: bool = True
    apply_healing: bool = True
    shadow_healing: bool = False
    timeout_ms: int = 8000
    output_dir: Path = Path("runs")


@dataclass
class StepResult:
    step_id: str
    index: int
    action: str
    intent: str = ""
    status: str = "unknown"
    error: str = ""
    locator_used: str = ""
    healing_applied: bool = False
    healing_layer: str = ""
    healing_strategy: str = ""
    oracle_status: str = "not_run"
    evidence_dir: str = ""


@dataclass
class RoundResult:
    round_id: str
    until_step: int
    status: str = "unknown"
    started_at: str = ""
    finished_at: str = ""
    step_results: list[StepResult] = field(default_factory=list)


class IncrementalExecutor:
    """
    Executor incremental do TestForge.

    Ideia:
    - Carrega semantic_steps.jsonl.
    - Executa rodadas 1..N.
    - Em cada rodada, executa do início até o step N.
    - Para cada step, valida precondição, executa, tenta healing se necessário,
      valida pós-ação e salva evidência.
    """

    def __init__(self, semantic_steps_path: str | Path, options: Optional[IncrementalOptions] = None):
        self.semantic_steps_path = Path(semantic_steps_path)
        self.options = options or IncrementalOptions()
        self.steps = self._load_steps(self.semantic_steps_path)

    def run(self) -> listall_results: list[RoundResult] = []

        total = len(self.steps)
        if total == 0:
            raise ValueError(f"Nenhum step encontrado em {self.semantic_steps_path}")

        for until in range(1, total + 1):
            result = self._run_round(until)
            all_results.append(result)

            if self.options.stop_on_failure and result.status == "failed":
                break

        self._save_incremental_summary(all_results)
        return all_results

    def _load_steps(self, path: Path) -> list[dict[str, Any]]:
        if not path.exists():
            raise FileNotFoundError(f"Arquivo não encontrado: {path}")

        steps: list[dict[str, Any]] = []

        if path.suffix.lower() == ".jsonl":
            with path.open("r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        steps.append(json.loads(line))
            return steps

        if path.suffix.lower() == ".json":
            data = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(data, dict) and "steps" in data:
                return data["steps"]
            if isinstance(data, list):
                return data

        raise ValueError(f"Formato não suportado para semantic steps: {path}")

    def _run_round(self, until_step: int) -> RoundResult:
        round_id = f"{self.semantic_steps_path.stem}_round_{until_step:03d}"
        round_dir = self.options.output_dir / self.semantic_steps_path.stem / f"round_{until_step:03d}"
        round_dir.mkdir(parents=True, exist_ok=True)

        round_result = RoundResult(
            round_id=round_id,
            until_step=until_step,
            status="running",
            started_at=datetime.now().isoformat(timespec="seconds"),
        )

        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=self.options.headless)
            page = browser.new_page()

            try:
                self._attach_basic_observability(page, round_dir)

                for idx, step in enumerate(self.steps[:until_step], start=1):
                    step_result = self._execute_one_step(page, step, idx, round_dir)
                    round_result.step_results.append(step_result)

                    if step_result.status not in ("passed", "healed_validated", "skipped"):
                        round_result.status = "failed"
                        if self.options.stop_on_failure:
                            break

                if round_result.status == "running":
                    round_result.status = "passed"

            except Exception as exc:
                round_result.status = "failed"
                self._write_text(round_dir / "fatal_error.txt", traceback.format_exc())

            finally:
                round_result.finished_at = datetime.now().isoformat(timespec="seconds")
                self._save_round_report(round_dir, round_result)
                browser.close()

        return round_result

    def _execute_one_step(self, page: Page, step: dict[str, Any], index: int, round_dir: Path) -> StepResult:
        step_id = str(step.get("id") or step.get("step_id") or f"step_{index:03d}")
        action = str(step.get("action", ""))
        intent = str(step.get("intent", step.get("intention", "")))

        step_dir = round_dir / f"{index:03d}_{self._safe_name(action)}"
        step_dir.mkdir(parents=True, exist_ok=True)

        result = StepResult(
            step_id=step_id,
            index=index,
            action=action,
            intent=intent,
            evidence_dir=str(step_dir),
        )

        try:
            self._capture_before(page, step_dir)

            pre = self._validate_pre_action(page, step)
            if not pre["ok"]:
                result.status = "failed_precondition"
                result.error = pre["error"]
                self._capture_after(page, step_dir)
                return result

            exec_result = self._execute_action(page, step)
            result.locator_used = exec_result.get("locator_used", "")

            if not exec_result["ok"]:
                healing_result = self._try_healing(page, step, exec_result["error"], step_dir)

                result.healing_layer = healing_result.get("layer", "")
                result.healing_strategy = healing_result.get("strategy", "")
                result.healing_applied = bool(healing_result.get("applied", False))
                result.locator_used = healing_result.get("locator_used", result.locator_used)

                if healing_result["ok"]:
                    oracle = self._validate_post_action(page, step)
                    result.oracle_status = "passed" if oracle["ok"] else "failed"

                    if oracle["ok"]:
                        result.status = "healed_validated"
                    else:
                        result.status = "false_healing_suspected"
                        result.error = oracle["error"]

                else:
                    result.status = "failed"
                    result.error = healing_result.get("error", exec_result["error"])

            else:
                oracle = self._validate_post_action(page, step)
                result.oracle_status = "passed" if oracle["ok"] else "failed"

                if oracle["ok"]:
                    result.status = "passed"
                else:
                    result.status = "failed_postcondition"
                    result.error = oracle["error"]

            self._capture_after(page, step_dir)
            self._save_step_report(step_dir, step, result)
            return result

        except Exception as exc:
            result.status = "failed"
            result.error = repr(exc)
            self._write_text(step_dir / "exception.txt", traceback.format_exc())
            self._capture_after(page, step_dir)
            self._save_step_report(step_dir, step, result)
            return result

    def _execute_action(self, page: Page, step: dict[str, Any]) -> dict[str, Any]:
        action = step.get("action")
        target = step.get("target") or {}
        value = step.get("value", "")
        url = step.get("url") or step.get("initial_url")

        locator = self._choose_locator(step)

        try:
            if action in ("navigation", "goto"):
                if not url:
                    return {"ok": False, "error": "navigation sem URL"}
                page.goto(url, timeout=self.options.timeout_ms)
                return {"ok": True, "locator_used": ""}

            if action == "click":
                page.locator(locator).click(timeout=self.options.timeout_ms)
                return {"ok": True, "locator_used": locator}

            if action == "fill":
                page.locator(locator).fill(str(value), timeout=self.options.timeout_ms)
                return {"ok": True, "locator_used": locator}

            if action == "press_sequentially":
                page.locator(locator).press_sequentially(str(value), timeout=self.options.timeout_ms)
                return {"ok": True, "locator_used": locator}

            if action == "select_option":
                page.locator(locator).select_option(str(value), timeout=self.options.timeout_ms)
                return {"ok": True, "locator_used": locator}

            if action == "check":
                page.locator(locator).check(timeout=self.options.timeout_ms)
                return {"ok": True, "locator_used": locator}

            if action == "uncheck":
                page.locator(locator).uncheck(timeout=self.options.timeout_ms)
                return {"ok": True, "locator_used": locator}

            if action == "assert_text":
                expected = str(step.get("expected") or value)
                page.locator(locator).wait_for(timeout=self.options.timeout_ms)
                text = page.locator(locator).inner_text(timeout=self.options.timeout_ms)
                if expected not in text:
                    return {
                        "ok": False,
                        "error": f"assert_text falhou: esperado trecho {expected!r}, obtido {text!r}",
                        "locator_used": locator,
                    }
                return {"ok": True, "locator_used": locator}

            return {"ok": False, "error": f"Ação não suportada: {action}", "locator_used": locator}

        except Exception as exc:
            return {"ok": False, "error": repr(exc), "locator_used": locator}

    def _try_healing(self, page: Page, step: dict[str, Any], error: str, step_dir: Path) -> dict[str, Any]:
        """
        Ponto de integração com self-healing.

        Aqui vocês podem chamar:
        - FailureClassifier
        - HealingCatalog L0
        - FallbackRunner L1
        - SpecialistAgents L2
        - LLMHealer L3
        - SmartStepRunner
        - PromotionGate
        """

        if self.options.shadow_healing:
            simulated = {
                "ok": False,
                "applied": False,
                "layer": "shadow",
                "strategy": "",
                "error": "shadow_healing ativo: nenhuma cura aplicada",
            }
            self._write_json(step_dir / "healing_shadow.json", simulated)
            return simulated

        if not self.options.apply_healing:
            return {
                "ok": False,
                "applied": False,
                "layer": "",
                "strategy": "",
                "error": error,
            }

        candidates = self._candidate_locators(step)

        attempts = []
        for candidate in candidates:
            patched = dict(step)
            patched["locator"] = candidate

            exec_result = self._execute_action(page, patched)
            attempts.append({
                "candidate": candidate,
                "ok": exec_result["ok"],
                "error": exec_result.get("error", ""),
            })

            if exec_result["ok"]:
                healing = {
                    "ok": True,
                    "applied": True,
                    "layer": "L1",
                    "strategy": "candidate_fallback",
                    "locator_used": candidate,
                    "attempts": attempts,
                }
                self._write_json(step_dir / "healing_attempts.json", healing)
                return healing

        healing = {
            "ok": False,
            "applied": False,
            "layer": "L1",
            "strategy": "candidate_fallback",
            "error": error,
            "attempts": attempts,
        }
        self._write_json(step_dir / "healing_attempts.json", healing)
        return healing

    def _choose_locator(self, step: dict[str, Any]) -> str:
        if step.get("locator"):
            return str(step["locator"])

        target = step.get("target") or {}
        candidates = target.get("candidates") or step.get("candidates") or []

        if isinstance(candidates, list) and candidates:
            first = candidates[0]
            if isinstance(first, dict):
                return str(first.get("selector") or first.get("playwright_expr") or "")
            return str(first)

        selector = target.get("selector") or step.get("selector")
        if selector:
            return str(selector)

        raise ValueError(f"Step sem locator/candidato: {step}")

    def _candidate_locators(self, step: dict[str, Any]) -> list[str]:
        target = step.get("target") or {}
        raw_candidates = target.get("candidates") or step.get("candidates") or []

        candidates: list[str] = []

        for c in raw_candidates:
            if isinstance(c, dict):
                selector = c.get("selector") or c.get("playwright_expr")
                if selector:
                    candidates.append(str(selector))
            elif isinstance(c, str):
                candidates.append(c)

        primary = None
        try:
            primary = self._choose_locator(step)
        except Exception:
            pass

        if primary and primary not in candidates:
            candidates.insert(0, primary)

        return self._dedupe([c for c in candidates if c])

    def _validate_pre_action(self, page: Page, step: dict[str, Any]) -> dict[str, Any]:
        action = step.get("action")

        if action in ("navigation", "goto"):
            url = step.get("url") or step.get("initial_url")
            if not url:
                return {"ok": False, "error": "URL inicial ausente"}
            return {"ok": True}

        try:
            locator = self._choose_locator(step)
            loc = page.locator(locator)

            if loc.count() == 0:
                return {"ok": False, "error": f"locator não encontrou elementos: {locator}"}

            if action in ("click", "fill", "select_option", "check", "uncheck", "press_sequentially"):
                loc.first.wait_for(state="visible", timeout=self.options.timeout_ms)

            return {"ok": True}

        except Exception as exc:
            return {"ok": False, "error": repr(exc)}

    def _validate_post_action(self, page: Page, step: dict[str, Any]) -> dict[str, Any]:
        """
        Oracle mínimo.
        Evoluir depois para:
        - URL esperada
        - texto esperado
        - estado de campo
        - request de rede concluída
        - alteração de DOM
        - assert explícito do semantic step
        """

        expected_text = step.get("expected_text") or step.get("expected")
        if expected_text:
            try:
                page.locator("body").wait_for(timeout=self.options.timeout_ms)
                body = page.locator("body").inner_text(timeout=self.options.timeout_ms)
                if str(expected_text) not in body:
                    return {
                        "ok": False,
                        "error": f"texto esperado não encontrado no body: {expected_text!r}",
                    }
            except Exception as exc:
                return {"ok": False, "error": repr(exc)}

        return {"ok": True}

    def _attach_basic_observability(self, page: Page, round_dir: Path) -> None:
        console_path = round_dir / "console.log"
        network_path = round_dir / "network.jsonl"

        def on_console(msg):
            with console_path.open("a", encoding="utf-8") as f:
                f.write(f"[{msg.type}] {msg.text}\n")

        def on_request(req):
            with network_path.open("a", encoding="utf-8") as f:
                f.write(json.dumps({
                    "type": "request",
                    "method": req.method,
                    "url": req.url,
                    "resource_type": req.resource_type,
                }, ensure_ascii=False) + "\n")

        def on_response(resp):
            with network_path.open("a", encoding="utf-8") as f:
                f.write(json.dumps({
                    "type": "response",
                    "url": resp.url,
                    "status": resp.status,
                }, ensure_ascii=False) + "\n")

        page.on("console", on_console)
        page.on("request", on_request)
        page.on("response", on_response)

    def _capture_before(self, page: Page, step_dir: Path) -> None:
        self._safe_screenshot(page, step_dir / "before.png")
        self._safe_dom(page, step_dir / "before.html")

    def _capture_after(self, page: Page, step_dir: Path) -> None:
        self._safe_screenshot(page, step_dir / "after.png")
        self._safe_dom(page, step_dir / "after.html")

    def _safe_screenshot(self, page: Page, path: Path) -> None:
        try:
            page.screenshot(path=str(path), full_page=True)
        except Exception:
            pass

    def _safe_dom(self, page: Page, path: Path) -> None:
        try:
            html = page.content()
            path.write_text(html, encoding="utf-8")
        except Exception:
            pass

    def _save_step_report(self, step_dir: Path, step: dict[str, Any], result: StepResult) -> None:
        self._write_json(step_dir / "step.json", step)
        self._write_json(step_dir / "result.json", result.__dict__)

    def _save_round_report(self, round_dir: Path, result: RoundResult) -> None:
        data = {
            "round_id": result.round_id,
            "until_step": result.until_step,
            "status": result.status,
            "started_at": result.started_at,
            "finished_at": result.finished_at,
            "step_results": [r.__dict__ for r in result.step_results],
        }
        self._write_json(round_dir / "round_report.json", data)

    def _save_incremental_summary(self, results: list[RoundResult]) -> None:
        summary_dir = self.options.output_dir / self.semantic_steps_path.stem
        summary_dir.mkdir(parents=True, exist_ok=True)

        data = {
            "semantic_steps_path": str(self.semantic_steps_path),
            "total_steps": len(self.steps),
            "rounds": [
                {
                    "round_id": r.round_id,
                    "until_step": r.until_step,
                    "status": r.status,
                    "started_at": r.started_at,
                    "finished_at": r.finished_at,
                }
                for r in results
            ],
        }

        self._write_json(summary_dir / "incremental_summary.json", data)

    def _write_json(self, path: Path, data: Any) -> None:
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    def _write_text(self, path: Path, text: str) -> None:
        path.write_text(text, encoding="utf-8")

    def _safe_name(self, value: str) -> str:
        value = value or "step"
        return "".join(ch if ch.isalnum() or ch in ("-", "_") else "_" for ch in value.lower())[:60]

    def _dedupe(self, values: list[str]) -> list[str]:
        seen = set()
        result = []
        for v in values:
            if v not in seen:
                seen.add(v)
                result.append(v)
        return result

Mostrar mais linhas
8. Como integrar com o self-healing existente
O TestForge já tem componentes para healing L0→L3, SmartStepRunner, agentes especialistas, catálogo, evidence payload e LLM healer. O README consolidado descreve o pipeline com L0 HealingCatalog, L1 FallbackRunner, L2 SpecialistAgents e L3 LLMHealer, além de estratégias como visibility_wait, press_sequentially, overlay_dismiss, iframe_switch, has_text_fallback, semantic_locator_conversion e xpath_fallback.
sharepoint

A integração correta é substituir o método _try_healing() simplificado acima por algo assim:




Python
def _try_healing(self, page, step, error, step_dir):
    failure = FailureClassifier().classify(error)

    evidence_payload = EvidenceCollector(page).build_llm_payload({
        "action": step.get("action"),
        "selector": self._choose_locator(step),
        "value": step.get("value"),
        "intention": step.get("intent"),
        "url": page.url,
    })

    # L0 — catálogo
    recipe = HealingCatalog().match(failure.family_code, error, step)
    if recipe:
        patched_step = apply_recipe(step, recipe)
        result = SmartStepRunner(page).execute(patched_step, recipe.strategy)
        if result.ok:
            return validate_and_return("L0", recipe.strategy, patched_step, result)

    # L1 — candidatos do próprio step
    for candidate in candidates_by_score(step):
        patched_step = replace_locator(step, candidate)
        result = SmartStepRunner(page).execute(patched_step, "candidate_fallback")
        if result.ok:
            return validate_and_return("L1", "candidate_fallback", patched_step, result)

    # L2 — agente especialista por família
    proposal = route_to_specialist_agent(failure.family_code).propose(step, error, evidence_payload)
    if proposal:
        patched_step = apply_proposal(step, proposal)
        result = SmartStepRunner(page).execute(patched_step, proposal.strategy)
        if result.ok:
            return validate_and_return("L2", proposal.strategy, patched_step, result)

    # L3 — LLM último recurso
    proposal = LLMHealer().heal_or_unresolved(evidence_payload, error, failure.family_code)
    if proposal.confidence >= 0.5:
        patched_step = apply_llm_proposal(step, proposal)
        result = SmartStepRunner(page).execute(patched_step, proposal.strategy)
        if result.ok:
            return validate_and_return("L3", proposal.strategy, patched_step, result)

    return unresolved()

Mostrar mais linhas
Mas o detalhe decisivo é:

Nenhum healing deve ser considerado verdadeiro só porque o clique/fill não lançou exceção.

Ele só vira healed_validated se passar no oráculo pós-ação.

9. Fluxo detalhado de validação passo a passo
Para cada step, eu usaria este contrato:

9.1. Antes da ação
Validar:




Plain Text
1. O step tem action conhecida?
2. O step tem locator/candidatos?
3. Se for navigation, tem URL?
4. Se for click/fill/select, o alvo existe?
5. O alvo é único ou a ambiguidade está justificada?
6. O elemento está visível?
7. O elemento está habilitado?
8. O elemento é acionável?
9. O step depende de outro step que falhou?
Se falhar aqui, status:




Plain Text
failed_precondition
9.2. Durante a ação
Executar com estratégia apropriada:




Plain Text
navigation       → page.goto
click            → locator.click
fill             → locator.fill
masked input     → press_sequentially + Tab
select           → select_option
checkbox/radio   → check/uncheck
upload           → set_input_files
assert           → expect/locator/body validation
Se falhar, classificar pela taxonomia:




Plain Text
FAM-01 selector
FAM-02 timing
FAM-03 context
FAM-04 state
FAM-05 dynamic DOM
FAM-06 input
FAM-07 upload
FAM-08 assertion
FAM-09 recorder
FAM-10 execution
FAM-11 technical limit
9.3. Healing
Tentar:




Plain Text
L0 catálogo
L1 candidatos ordenados por score
L2 agente especialista
L3 LLM
Sempre registrar:




JSON
{
  "step": "step_004",
  "original_locator": "label:has-text('UF') + input",
  "failure": "locator not found",
  "taxonomy": "FAM-01/SEL-004",
  "attempts": [
    {
      "layer": "L1",
      "candidate": "select[name='lstUf']",
      "score": 0.94,
      "status": "passed"
    }
  ],
  "healing_status": "candidate_applied"
}

Mostrar mais linhas
9.4. Pós-ação
Validar consequência:




Plain Text
click em botão de pesquisa → resultado apareceu?
select UF → select ficou com valor esperado?
click em link → URL mudou ou próxima tela apareceu?
fill CPF → campo manteve valor esperado?
click Calcular → requisição terminou e seção de resultado apareceu?
Sem consequência verificável, status:




Plain Text
executed_but_unvalidated
Com consequência correta:




Plain Text
passed
Com healing e consequência correta:




Plain Text
healed_validated
Com healing mas consequência errada:




Plain Text
false_healing_suspected
10. Plano incremental de implementação
Incremento 1 — semantic_steps.jsonl como contrato oficial
Objetivo: garantir que o executor não dependa do script Python grande.

Entregas:

compile sempre gera semantic_steps.jsonl.
Cada step tem id, action, intent, target, candidates, value, depends_on, blocking, expected.
Documentar contrato.
Critério de aceite:




Plain Text
raw_events.jsonl     = tudo capturado
steps.jsonl          = asserts/manual/hints
semantic_steps.jsonl = fluxo executável normalizado
script.py            = renderização opcional
Incremento 2 — executor incremental mínimo
Objetivo: executar 1..N sem healing avançado.

Entregas:

IncrementalExecutor
comando run-incremental
reports por rodada
screenshots/DOM antes/depois
Critério de aceite:




Shell
testforge run-incremental semantic_tests/ST-demo/semantic_steps.jsonl
gera:




Plain Text
runs/ST-demo/round_001/
runs/ST-demo/round_002/
runs/ST-demo/incremental_summary.json
Incremento 3 — validação por step
Objetivo: não aceitar ação “sem exceção” como sucesso.

Entregas:

pre_action_validator
post_action_oracle
status padronizados
Critério de aceite:




Plain Text
passed
failed_precondition
failed_action
failed_postcondition
blocked_by_previous_failure
skipped_compacted
healed_validated
false_healing_suspected
Incremento 4 — integração com healing existente
Objetivo: conectar SmartStepRunner, FallbackRunner, agentes e catálogo.

Entregas:

_try_healing() real
relatório de tentativas
camada usada
estratégia usada
Critério de aceite:




Plain Text
Step falhou → classifica → tenta L0/L1/L2/L3 → valida oracle → salva evidence
Incremento 5 — aprendizado versionado
Objetivo: enviar gravações/logs para o repositório sem poluir o projeto.

Estrutura sugerida:




Plain Text
runs/
  ST-simax/
    incremental_summary.json
    round_001/
    round_002/
recordings/
semantic_tests/
healing_catalog/
reports/
Critério de aceite:

Cada execução tem ID.
Cada step tem evidência.
Cada healing tem justificativa.
Dados sensíveis geram alerta, não mascaramento automático.
Incremento 6 — checkpoint/state reuse
O modelo 1..N do zero é ótimo para começar, mas tem custo O(n²). Em fluxos longos, ficará pesado.

Depois, evoluir para:




Plain Text
step 1 passa → salva storage_state/context snapshot
step 2 reutiliza checkpoint do step 1
step 3 reutiliza checkpoint do step 2
Mas não comece por isso. Primeiro faça simples.

11. Pontos de cuidado
11.1. Não transformar healing em “máquina de mentir”
Se o sistema clica em qualquer botão e a página não explode, isso não é healing. Healing só é válido quando o oracle confirma a intenção.

11.2. Não mandar tudo para o repositório sem política
Gravações reais podem conter dado sensível. Como vocês decidiram, o MVP deve alertar presença de dados sensíveis, não mascarar automaticamente. Mas o report deve marcar:




JSON
{
  "sensitive_alerts": [
    {
      "type": "CPF",
      "field": "cpf",
      "step_id": "step_003",
      "policy": "alert_only"
    }
  ]
}
11.3. Não abandonar o compilador ainda
O compilador ainda é útil para:

exportar teste final legível;
permitir revisão humana;
rodar em CI;
comparar execução interpretada vs execução compilada.
Mas ele deixa de ser o principal mecanismo de debug.

12. Ordem recomendada para vocês agora
Eu faria exatamente nesta ordem:

Congelar o gravador por enquanto
Só mexer se houver bug crítico de captura.

Garantir semantic_steps.jsonl auditável
Este vira o contrato principal.

Implementar run-incremental simples
Sem tentar resolver tudo.

Salvar evidência por rodada e por step

Adicionar pre/post validation

Conectar L1 fallback por candidatos

Conectar FailureClassifier + SmartStepRunner

Conectar L0 catálogo e L2 agentes

Só então L3 LLM

Criar relatório consolidado para commit/repositório

13. Minha recomendação arquitetural final
A nova arquitetura deve ser:




Plain Text
Recorder = coleta intenção
Normalizer = estabiliza contrato
Incremental Interpreter = descobre onde quebra
SmartStepRunner = executa ação correta
Self-Healing = propõe alternativas
Oracle = impede falso healing
EvidenceStore = preserva aprendizado
Compiler = exporta script final, não dirige o debug
Essa mudança tem grande chance de reduzir o sofrimento que vocês tiveram ontem, porque vocês deixam de “consertar um script gigante” e passam a “validar incrementalmente uma intenção executável”.

Se vocês implementarem só uma coisa hoje, eu implementaria:

testforge run-incremental semantic_steps.jsonl --headed --stop-on-failure

com relatório por rodada.

Isso já dará valor imediato para o time gravar sistemas reais, gerar massa, descobrir o primeiro ponto instável de cada fluxo e alimentar o aprendizado do TestForge de forma organizada.

2 Jun
Terça-feira
PoC Automação_Squad Inovação
15:00 - 16:00
GESQI03 - Qualidade de software - Canais e Serviços Bancários organizou isso

Perguntar

----------------------------------------------------------------------------------------------------------------------------------

Dado o nossa interação anterior (Plano e Executor Increment...) Explique como implementar o comando run-incremental, Detalhe como validar pre e pós-condições em cada passo, Sugira melhorias para o relatório de evidências e healing
Copilot said:
Copilot

Processamento concluído em 3 etapas
Andre, pela situação atual do TestForge, eu implementaria o run-incremental não como “mais um modo de rodar script”, mas como o novo executor principal de depuração/estabilização. O run atual já tem várias peças úteis: carrega steps da gravação, executa inline, tenta healing, registra RunReport, usa MetricsRepository, CuradorAutomatico, EvidenceCollector, OracleRunner, PromotionGate e já salva relatório completo. Mas ele ainda mistura muita responsabilidade dentro de cmd_run, o que dificulta evoluir validação passo a passo, interface e relatório.
sharepoint
+1

A proposta é extrair essa lógica para um IncrementalRunner e criar o comando CLI testforge run-incremental.
sharepoint
+1

1. Como implementar o comando run-incremental
1.1. Objetivo do comando
O comando deve executar o teste um passo por vez, com este ciclo:




Plain Text
carregar semantic_steps
↓
abrir browser
↓
para cada step:
    validar pré-condições
    coletar evidência before
    executar ação
    validar pós-condições
    coletar evidência after
    se falhou:
        tentar healing
        validar healing com oracle
    registrar decisão
↓
gerar relatório incremental

Mostrar mais linhas
A diferença para o run atual é que o run-incremental deve deixar explícito por que cada passo passou, falhou, foi bloqueado, foi pulado ou foi curado. Isso responde diretamente aos problemas já identificados no projeto: métricas inconsistentes, steps pulados sem explicação, falsos healings e falta de contrato claro entre raw_events, steps, semantic_steps e script executável.
sharepoint
+1

1.2. Novo comando no CLI
Em src/testforge/cli/app.py, adicionar:




Python
inc = sub.add_parser("run-incremental", help="Executar teste passo a passo com pré/pós-condições")
inc.add_argument("script", help="Caminho do script Python gerado")
inc.add_argument("--headless", action="store_true")
inc.add_argument("--timeout", type=int, default=60)
inc.add_argument("--verbose", action="store_true")
inc.add_argument("--data", type=str, default="")
inc.add_argument("--browser", choices=["chromium", "chrome", "edge"], default="chromium")
inc.add_argument("--stop-on-failure", action="store_true")
inc.add_argument("--interactive", action="store_true", help="Pausa entre passos")
inc.add_argument("--no-healing", action="store_true", help="Executa sem aplicar healing")
inc.add_argument("--shadow", action="store_true", help="Simula healing sem alterar resultado final")
inc.set_defaults(func=cmd_run_incremental)

Mostrar mais linhas
E criar:




Python
def cmd_run_incremental(args):
    from testforge.runner.incremental_runner import IncrementalRunner

    runner = IncrementalRunner(
        script_path=args.script,
        headless=args.headless,
        timeout=args.timeout,
        verbose=args.verbose,
        data_file=args.data,
        browser_type=args.browser,
        stop_on_failure=args.stop_on_failure,
        interactive=args.interactive,
        healing_enabled=not args.no_healing,
        shadow_mode=args.shadow,
    )

    result = runner.run()

    print()
    print("[TestForge] Execução incremental finalizada")
    print(f"  Status: {result.status}")
    print(f"  Steps: {result.total_steps}")
    print(f"  Passaram: {result.passed_steps}")
    print(f"  Falharam: {result.failed_steps}")
    print(f"  Curados: {result.healed_steps}")
    print(f"  Bloqueados: {result.blocked_steps}")
    print(f"  Relatório: {result.report_path}")

Mostrar mais linhas
Isso preserva o cmd_run atual, mas cria um caminho mais limpo para estabilizar o projeto sem quebrar o fluxo existente.
sharepoint
+1

2. Estrutura sugerida de arquivos
Eu criaria estes novos módulos:




Plain Text
src/testforge/runner/
├── incremental_runner.py
├── step_executor.py
├── step_precondition.py
├── step_postcondition.py
├── step_result.py
└── incremental_ui.py
Responsabilidades



Plain Text
incremental_runner.py
    Orquestra o fluxo inteiro.

step_executor.py
    Executa fill, click, select_option, assert, navigation etc.

step_precondition.py
    Valida se o passo pode ser executado.

step_postcondition.py
    Valida se o passo produziu o efeito esperado.

step_result.py
    Define os modelos de resultado por step.

incremental_ui.py
    Renderiza saída de terminal e, no futuro, interface interativa.

Mostrar mais linhas
Isso é importante porque hoje o cmd_run concentra muita lógica dentro de uma única função: carregamento de steps, execução, data-driven fill, espera de consequência, healing, métricas e relatório. A extração reduz risco e torna cada parte testável isoladamente.
sharepoint
+1

3. Modelo de resultado incremental
Criaria um modelo claro para cada step.




Python
from dataclasses import dataclass, field
from typing import Optional, Any


@dataclass
class PreconditionResult:
    passed: bool
    checks: dict[str, bool] = field(default_factory=dict)
    failures: list[str] = field(default_factory=list)
    message: str = ""


@dataclass
class PostconditionResult:
    passed: bool
    checks: dict[str, bool] = field(default_factory=dict)
    oracle_results: list[Any] = field(default_factory=list)
    failures: list[str] = field(default_factory=list)
    message: str = ""


@dataclass
class HealingAttempt:
    attempted: bool = False
    layer: str = ""
    family: str = ""
    taxonomy_id: str = ""
    strategy: str = ""
    original_locator: str = ""
    proposed_locator: str = ""
    confidence: float = 0.0
    status: str = ""
    oracle_passed: bool = False
    rationale: str = ""


@dataclass
class IncrementalStepResult:
    step_num: int
    action: str
    status: str  # passed, failed, healed, blocked, skipped, shadow_healed
    original_locator: str = ""
    selected_locator: str = ""
    value: str = ""
    precondition: Optional[PreconditionResult] = None
    postcondition: Optional[PostconditionResult] = None
    healing: Optional[HealingAttempt] = None
    error_message: str = ""
    evidence_before: dict = field(default_factory=dict)
    evidence_after: dict = field(default_factory=dict)
    duration_ms: int = 0

Mostrar mais linhas
Esse modelo resolve um problema central: parar de tratar “curou” como um booleano solto. O relatório precisa dizer falhou onde, com qual locator, qual pré-condição falhou, qual pós-condição confirmou ou rejeitou o healing.
sharepoint
+1

4. Pseudocódigo do IncrementalRunner



Python
class IncrementalRunner:
    def run(self):
        self._load_script_metadata()
        self._load_semantic_steps()
        self._load_data_file()
        self._start_report()

        with sync_playwright() as pw:
            browser = launch_browser(
                pw,
                self.browser_type,
                headless=self.headless,
            )
            page = browser.new_page()
            page.set_viewport_size({"width": 1280, "height": 720})

            self.page = page
            self.evidence = EvidenceCollector(page, evidence_root="runs")
            self.evidence.start(self.run_id)

            page.goto(self.base_url)
            page.wait_for_timeout(500)

            for index, step in enumerate(self.steps):
                result = self._run_one_step(index, step)
                self.report.add_step(result)

                if self.interactive:
                    input("Pressione ENTER para continuar...")

                if self.stop_on_failure and result.status == "failed":
                    break

            browser.close()

        return self._finalize_report()

Mostrar mais linhas
E o coração:




Python
def _run_one_step(self, index, step):
    step_num = index + 1
    started = time.time()

    result = IncrementalStepResult(
        step_num=step_num,
        action=step.action,
        value=step.value or "",
        original_locator=self._primary_selector(step),
        selected_locator=self._primary_selector(step),
    )

    # 1. Dependências
    if self._is_blocked_by_dependency(step):
        result.status = "blocked"
        result.error_message = f"blocked_by_previous_failure: {step.depends_on}"
        return result

    # 2. Pré-condições
    pre = self.precondition_validator.validate(step, page=self.page)
    result.precondition = pre

    if not pre.passed:
        result.evidence_before = self._capture_evidence(step_num, "pre_failed")
        result.status = "failed"

        if self.healing_enabled:
            return self._try_healing(step, result, pre.message)

        return result

    # 3. Evidência antes
    result.evidence_before = self._capture_evidence(step_num, "before")

    # 4. Execução
    try:
        self.step_executor.execute(step, self.page, self.data_values)
    except Exception as exc:
        result.error_message = str(exc)
        result.status = "failed"

        if self.healing_enabled:
            return self._try_healing(step, result, str(exc))

        return result

    # 5. Pós-condições
    post = self.postcondition_validator.validate(step, page=self.page)
    result.postcondition = post
    result.evidence_after = self._capture_evidence(step_num, "after")

    if post.passed:
        result.status = "passed"
    else:
        result.status = "failed"
        result.error_message = post.message

        if self.healing_enabled:
            return self._try_healing(step, result, post.message)

    result.duration_ms = int((time.time() - started) * 1000)
    return result

Mostrar mais linhas
5. Como validar pré-condições em cada passo
As pré-condições respondem:“posso executar este passo agora?”

5.1. Pré-condições gerais
Para todos os steps:




Plain Text
1. Step não está marcado como skipped.
2. Dependência anterior foi satisfeita.
3. Página/browser ainda estão ativos.
4. Se step tem selector, existe pelo menos um candidato.
5. Se step é blocking e depende de outro, o depends_on está resolvido.
O projeto já possui campos como blocking, depends_on e skip_reason no modelo semântico/execução, e o cmd_run atual já trata parcialmente steps dependentes marcando blocked_by_previous_failure. O run-incremental deve formalizar isso em um validador próprio.
sharepoint
+1

5.2. Pré-condições para click
Antes de clicar:




Plain Text
- locator existe;
- locator resolve para pelo menos um elemento;
- preferencialmente resolve para 1 elemento;
- elemento está attached;
- elemento está visible;
- elemento está enabled;
- bounding box tem área > 0;
- elemento não está coberto por overlay conhecido;
- se causa navegação, preparar captura de URL antes.
O projeto já tem ActionabilityValidator, que valida visibilidade, enabled e bounding box positiva, rejeitando elementos com área zero. Ele deve ser reutilizado no run-incremental.
sharepoint
+1

Exemplo:




Python
from testforge.actionability import ActionabilityValidator


class StepPreconditionValidator:
    def __init__(self, page):
        self.page = page
        self.actionability = ActionabilityValidator(page)

    def validate_click(self, step):
        selector = self._primary_selector(step)

        if not selector:
            return PreconditionResult(
                passed=False,
                failures=["missing_selector"],
                message="Step click sem selector principal",
            )

        actionability = self.actionability.validate(selector)

        checks = {
            "selector_present": bool(selector),
            "visible": actionability.visible,
            "enabled": actionability.enabled,
            "area_positive": actionability.area_positive,
            "actionable": actionability.actionable,
        }

        if not actionability.actionable:
            return PreconditionResult(
                passed=False,
                checks=checks,
                failures=actionability.failures,
                message=actionability.message,
            )

        return PreconditionResult(passed=True, checks=checks)

Mostrar mais linhas
5.3. Pré-condições para fill
Para fill:




Plain Text
- elemento existe;
- está visível;
- está habilitado;
- é input/textarea/contenteditable;
- não é readonly;
- se possui máscara, estratégia preferencial pode ser press_sequentially;
- valor está disponível no step ou no data file.
O TestForge já identificou casos em que fill() não funciona bem em campos com máscara, especialmente em Angular Material/currencymask, e o projeto já usa press_sequentially para campos mascarados. O run-incremental deve detectar isso antes da ação, não apenas depois da falha.
sharepoint
+1

Exemplo:




Python
def validate_fill(self, step):
    selector = self._primary_selector(step)
    value = step.value or ""

    if not selector:
        return PreconditionResult(False, failures=["missing_selector"])

    if value == "":
        return PreconditionResult(
            False,
            failures=["missing_value"],
            message="Step fill sem valor",
        )

    actionability = self.actionability.validate(selector)

    try:
        readonly = self.page.locator(selector).first.get_attribute("readonly")
        disabled = self.page.locator(selector).first.get_attribute("disabled")
    except Exception:
        readonly = None
        disabled = None

    checks = {
        "actionable": actionability.actionable,
        "has_value": bool(value),
        "not_readonly": readonly is None,
        "not_disabled_attr": disabled is None,
    }

    failures = []
    if not actionability.actionable:
        failures += actionability.failures
    if readonly is not None:
        failures.append("readonly")
    if disabled is not None:
        failures.append("disabled_attr")

    return PreconditionResult(
        passed=len(failures) == 0,
        checks=checks,
        failures=failures,
        message="; ".join(failures),
    )

Mostrar mais linhas
5.4. Pré-condições para select_option
Esse ponto é crítico para o TestForge por causa dos bugs reais em que <select> virou seletor de <input>. O run-incremental deve impedir que um step de select execute se o alvo não for realmente <select>.
sharepoint
+1

Pré-condições:




Plain Text
- tag do target é select;
- selector resolve para select;
- option desejada existe por value ou label;
- valor não é texto genérico como "Selecione", salvo se for intencional;
- select está enabled.
Exemplo:




Python
def validate_select_option(self, step):
    selector = self._primary_selector(step)
    value = step.value or ""

    if not selector:
        return PreconditionResult(False, failures=["missing_selector"])

    locator = self.page.locator(selector).first

    try:
        tag = locator.evaluate("el => el.tagName.toLowerCase()")
    except Exception as exc:
        return PreconditionResult(False, failures=["selector_not_found"], message=str(exc))

    if tag != "select":
        return PreconditionResult(
            False,
            failures=["target_not_select"],
            message=f"Esperado select, encontrado {tag}",
        )

    options = locator.evaluate("""
        el => Array.from(el.options).map(o => ({
            value: o.value,
            text: o.textContent.trim()
        }))
    """)

    exists = any(o["value"] == value or o["text"] == value for o in options)

    return PreconditionResult(
        passed=exists,
        checks={
            "target_is_select": tag == "select",
            "option_exists": exists,
        },
        failures=[] if exists else ["option_not_found"],
        message="" if exists else f"Option não encontrada: {value}",
    )

Mostrar mais linhas
5.5. Pré-condições para assert
Para assert:




Plain Text
- selector existe ou assert pode ser feito no body;
- se assert é textual, expected_value não está vazio;
- se assert é estado, estado esperado é válido;
- se assert é visibilidade, locator existe.
Também é importante evitar asserts frágeis com CSS estrutural longo e valores dinâmicos, problema já visto no simulador habitacional: resultado com valor monetário gravado não bate quando a massa muda.
sharepoint
+1

6. Como validar pós-condições em cada passo
As pós-condições respondem:“a ação produziu o efeito esperado?”

Essa é a parte que mais reduz falso healing.

6.1. Pós-condição para fill
Depois de preencher:




Plain Text
- valor do input mudou;
- valor atual contém/normaliza o valor esperado;
- se campo tem máscara, comparar valor normalizado;
- se Angular/React, verificar blur/tab quando necessário;
- se havia data file, valor usado deve ser registrado.
Exemplo:




Python
def validate_fill_postcondition(self, step):
    selector = self._primary_selector(step)
    expected = step.value or ""

    try:
        actual = self.page.locator(selector).first.input_value(timeout=3000)
    except Exception as exc:
        return PostconditionResult(
            passed=False,
            failures=["cannot_read_input_value"],
            message=str(exc),
        )

    expected_norm = self._normalize_value(expected)
    actual_norm = self._normalize_value(actual)

    passed = expected_norm in actual_norm or actual_norm in expected_norm

    return PostconditionResult(
        passed=passed,
        checks={
            "value_changed": bool(actual),
            "expected_matches_actual_normalized": passed,
        },
        failures=[] if passed else ["value_mismatch"],
        message="" if passed else f"Esperado {expected}, obtido {actual}",
    )

Mostrar mais linhas
6.2. Pós-condição para click
Para click, não basta “não deu exception”. Esse foi um problema recorrente: o click pode ocorrer no elemento errado e ainda assim o runner seguir. O run-incremental deve validar consequência.
sharepoint
+1

Validações possíveis:




Plain Text
- se causes_navigation=True: URL mudou ou load ocorreu;
- se próximo step tem selector: próximo selector apareceu;
- se click abre modal: modal apareceu;
- se click dispara cálculo/API: houve resposta de rede relevante;
- se click em botão de submit: formulário mudou estado;
- se não houver oracle específico: no mínimo DOM mudou ou próximo step ficou acionável.
O cmd_run atual já possui uma função _wait_for_consequence() que espera a consequência do próximo step em vez de usar sleeps arbitrários; isso deve virar uma pós-condição formal no StepPostconditionValidator.
sharepoint
+1

Exemplo:




Python
def validate_click_postcondition(self, step, next_step=None, url_before=""):
    causes_navigation = step.context.get("causes_navigation", False) if step.context else False

    checks = {}

    if causes_navigation:
        self.page.wait_for_timeout(800)
        url_changed = self.page.url != url_before
        checks["url_changed"] = url_changed

        if not url_changed:
            return PostconditionResult(
                passed=False,
                checks=checks,
                failures=["url_not_changed"],
                message="Click deveria causar navegação, mas URL não mudou",
            )

        return PostconditionResult(passed=True, checks=checks)

    if next_step and next_step.target and next_step.target.candidates:
        next_selector = next_step.target.candidates[0].selector
        try:
            self.page.wait_for_selector(next_selector, state="visible", timeout=12000)
            checks["next_step_visible"] = True
            return PostconditionResult(passed=True, checks=checks)
        except Exception:
            checks["next_step_visible"] = False

    # fallback mínimo
    return PostconditionResult(
        passed=True,
        checks=checks,
        message="Sem oracle específico; click não gerou erro",
    )

Mostrar mais linhas
6.3. Pós-condição para select_option
Depois do select:




Plain Text
- selected value é o esperado;
- selected label é compatível;
- se o select causa reload/postback, URL ou DOM mudou;
- se há dependentes, o próximo campo ficou disponível.
Exemplo:




Python
def validate_select_postcondition(self, step, next_step=None):
    selector = self._primary_selector(step)
    expected = step.value or ""

    locator = self.page.locator(selector).first

    selected = locator.evaluate("""
        el => {
            const opt = el.options[el.selectedIndex];
            return {
                value: el.value,
                text: opt ? opt.textContent.trim() : ""
            };
        }
    """)

    ok = selected["value"] == expected or selected["text"] == expected

    if not ok:
        return PostconditionResult(
            passed=False,
            checks={"selected_matches_expected": False},
            failures=["selected_value_mismatch"],
            message=f"Esperado {expected}, selecionado {selected}",
        )

    return PostconditionResult(
        passed=True,
        checks={"selected_matches_expected": True},
    )

Mostrar mais linhas
6.4. Pós-condição para assert
Para assert, a própria assertiva é a pós-condição.




Python
def validate_assert_postcondition(self, step):
    selector = self._primary_selector(step) or "body"
    expected = step.value or ""
    assert_type = step.context.get("assert_type", "textual") if step.context else "textual"

    oracle = OracleRunner(self.page)

    if assert_type in ("textual", "automatico"):
        result = oracle.run_visual_dom(selector, expected)
    elif assert_type == "visivel":
        result = oracle.run_visual_dom(selector)
    else:
        result = oracle.run_business_state(selector, expected)

    return PostconditionResult(
        passed=result.status == "passed",
        oracle_results=[result],
        failures=[] if result.status == "passed" else ["assert_oracle_failed"],
        message=result.message,
    )

Mostrar mais linhas
O projeto já possui OracleRunner com visual_dom e business_state, e isso deve ser reaproveitado para transformar asserts e validações pós-ação em uma regra comum.
sharepoint
+1

7. Onde entra o healing no run-incremental
O healing deve ser chamado em três situações:




Plain Text
1. pré-condição falhou:
   - selector não existe;
   - elemento não acionável;
   - opção não existe;
   - bounding box zero.

2. execução falhou:
   - click timeout;
   - fill falhou;
   - select falhou;
   - navegação não ocorreu.

3. pós-condição falhou:
   - click aconteceu mas não produziu efeito;
   - fill alterou valor errado;
   - assert não bateu;
   - oracle rejeitou.

Mostrar mais linhas
A diferença mais importante: healing só deve ser considerado verdadeiro se a pós-condição passar depois da ação curada. Isso evita falso healing.
sharepoint
+1

7.1. Fluxo de healing sugerido



Python
def _try_healing(self, step, result, error_message):
    if self.shadow_mode:
        return self._simulate_healing(step, result, error_message)

    evidence_payload = self._build_healing_payload(step, result, error_message)

    outcome = self.curator.cure(
        step_data={
            "selector": result.selected_locator,
            "action": step.action,
            "value": step.value or "",
            "base_url": self.base_url,
        },
        error_message=error_message,
        evidence=evidence_payload,
    )

    healing = HealingAttempt(
        attempted=True,
        layer=outcome.layer_used,
        family=outcome.family,
        taxonomy_id=outcome.taxonomy_id,
        status=outcome.status,
    )

    if outcome.proposal:
        healing.strategy = outcome.proposal.strategy
        healing.proposed_locator = outcome.proposal.new_locator
        healing.confidence = outcome.proposal.confidence
        healing.rationale = outcome.proposal.rationale

    result.healing = healing

    if outcome.status != "PASSED_STEP":
        result.status = "failed"
        return result

    # Validação pós-healing
    post = self.postcondition_validator.validate(step, page=self.page)
    result.postcondition = post

    if post.passed:
        result.status = "healed"
        healing.oracle_passed = True
    else:
        result.status = "failed"
        healing.oracle_passed = False
        result.error_message = "Healing executou, mas pós-condição/oracle falhou"

    return result

Mostrar mais linhas
O projeto já tem CuradorAutomatico com L0/L2/L3, HealingCatalog, agentes especialistas, MockLLMHealer/LLM real, e SmartStepRunner; o run-incremental deve usar isso, mas sempre acoplado à validação pós-ação.
sharepoint
+1

8. Interface/saída esperada no terminal
Eu sugiro uma saída assim:




Plain Text
[TestForge] run-incremental
  Script: semantic_tests/ST-simax/test_st_simax.py
  Recording: simax_agenda
  URL base: https://...
  Healer: MockLLMHealer
  Modo: incremental

Step 1/15 navigation
  PRE  ✓ url_base_presente
  EXEC ✓ already at base url
  POST ✓ página carregada
  EVID before/after salvos

Step 2/15 select_option — Selecionar UF
  Locator original: label:has-text("UF") + input
  PRE  ✗ target_not_select / selector_not_found
  HEAL L2 FAM-01 SEL-004
       proposta: select[name="lstUf"]
       estratégia: semantic_locator_conversion
       confiança: 0.91
  EXEC ✓ select_option("MT")
  POST ✓ selected value = MT
  STATUS healed_validated

Step 3/15 select_option — Selecionar Edifício
  PRE  ✓ actionable
  EXEC ✓ select_option(...)
  POST ✓ próximo campo Data visível
  STATUS passed

Step 4/15 click — Calcular
  PRE  ✓ actionable
  EXEC ✓ click
  POST ✗ resultado esperado não apareceu
  HEAL L2 FAM-02 TIM-005 visibility_wait
  EXEC ✓ retry
  POST ✓ resultado apareceu
  STATUS healed_validated

Mostrar mais linhas
Isso deixa evidente a diferença entre:




Plain Text
passed              passou sem healing
healed_validated    healing aplicado e validado
failed              falhou e não curou
blocked             não executou por dependência anterior
skipped             omitido por regra explícita
shadow_healed       teria curado, mas não alterou resultado final
9. Melhorias no relatório de evidências
Hoje já existe RunReport e StepReport, e o cmd_run já salva relatório completo, incluindo candidatos, selector usado, erro, healing layer, família, proposta e raw response. O run-incremental deve evoluir isso para um relatório mais rico e navegável.
sharepoint
+1

9.1. Estrutura de diretório recomendada



Plain Text
runs/
└── <recording_id>/
    └── <timestamp>/
        ├── execution_report.json
        ├── healing_report.md
        ├── summary.md
        ├── metrics.json
        ├── steps/
        │   ├── step_0001.json
        │   ├── step_0002.json
        │   └── ...
        ├── screenshots/
        │   ├── step_0001_before.png
        │   ├── step_0001_after.png
        │   ├── step_0002_before.png
        │   └── ...
        ├── dom/
        │   ├── step_0001_before.html
        │   ├── step_0001_after.html
        │   └── ...
        ├── network/
        │   └── network_log.json
        └── sensitive_data_alert.json

Mostrar mais linhas
Isso separa o relatório da gravação original e evita poluir recordings/. A gravação é fonte histórica; o runs/ é execução.
sharepoint
+1

9.2. execution_report.json
Exemplo de estrutura:




JSON
{
  "run_id": "simax_agenda_20260617_201500",
  "recording_id": "simax_agenda",
  "script_path": "semantic_tests/ST-simax_agenda/test_st_simax_agenda.py",
  "base_url": "https://...",
  "started_at": "2026-06-17T20:15:00-03:00",
  "finished_at": "2026-06-17T20:17:42-03:00",
  "mode": "incremental",
  "shadow_mode": false,
  "summary": {
    "total_steps": 15,
    "passed": 10,
    "failed": 1,
    "healed_validated": 3,
    "blocked": 1,
    "skipped": 0
  },
  "metrics": {
    "falhas_detectadas": 4,
    "healings_tentados": 4,
    "healings_aplicados": 3,
    "healings_validados": 3,
    "healings_rejeitados": 1,
    "false_heal_rate": 0.25,
    "precision": 0.75
  },
  "steps": []
}

Mostrar mais linhas
9.3. Dados por step
Cada step deveria registrar:




JSON
{
  "step_num": 2,
  "action": "select_option",
  "intent": "Selecionar UF",
  "status": "healed_validated",
  "blocking": true,
  "depends_on": null,
  "original_locator": "label:has-text(\"UF\") + input",
  "selected_locator": "select[name=\"lstUf\"]",
  "value": "MT",
  "precondition": {
    "passed": false,
    "failures": ["selector_not_found", "target_not_select"],
    "checks": {
      "selector_present": true,
      "target_is_select": false,
      "actionable": false
    }
  },
  "execution": {
    "attempts": [
      {
        "locator": "label:has-text(\"UF\") + input",
        "status": "failed",
        "error": "not found"
      },
      {
        "locator": "select[name=\"lstUf\"]",
        "status": "passed",
        "strategy": "semantic_locator_conversion"
      }
    ]
  },
  "postcondition": {
    "passed": true,
    "checks": {
      "selected_matches_expected": true
    }
  },
  "healing": {
    "attempted": true,
    "layer": "L2",
    "family": "FAM-01",
    "taxonomy_id": "SEL-004",
    "strategy": "semantic_locator_conversion",
    "confidence": 0.91,
    "original_locator": "label:has-text(\"UF\") + input",
    "proposed_locator": "select[name=\"lstUf\"]",
    "oracle_passed": true,
    "promotable": true
  },
  "evidence": {
    "before_screenshot": "screenshots/step_0002_before.png",
    "after_screenshot": "screenshots/step_0002_after.png",
    "before_dom": "dom/step_0002_before.html",
    "after_dom": "dom/step_0002_after.html",
    "quality_flags": []
  }
}

Mostrar mais linhas
Esse formato elimina ambiguidade entre locator gravado, locator usado e locator curado, que foi uma das principais recomendações anteriores para melhorar seletores e métricas.
sharepoint
+1

10. Melhorias específicas para relatório de healing
10.1. Separar healing “tentado”, “aplicado” e “validado”
O relatório deve parar de usar “curado” de forma ampla. Recomendo estes estados:




Plain Text
healing_not_needed
healing_attempted
healing_applied
healing_validated
healing_rejected
healing_shadow_positive
healing_shadow_negative
Mapeamento:




Plain Text
healing_attempted:
    Curador foi acionado.

healing_applied:
    Proposta foi executada sem erro.

healing_validated:
    Pós-condição/oracle confirmou.

healing_rejected:
    Proposta falhou ou oracle rejeitou.

healing_shadow_positive:
    Em shadow mode, proposta teria funcionado.

healing_shadow_negative:
    Em shadow mode, proposta não teria funcionado.

Mostrar mais linhas
Isso corrige o problema já documentado de métricas inconsistentes entre resumo e contadores internos.
sharepoint
+1

10.2. Relatório Markdown para leitura humana
Gerar healing_report.md assim:




Markdown
# TestForge Healing Report

## Resumo

- Total de steps: 15
- Falhas detectadas: 4
- Healings tentados: 4
- Healings validados: 3
- Healings rejeitados: 1
- Precisão: 75%
- False heal rate: 25%

## Healings validados

### Step 2 — Selecionar UF

- Falha original: selector not found
- Locator original: `label:has-text("UF") + input`
- Família: FAM-01 / SEL-004
- Camada: L2
- Estratégia: `semantic_locator_conversion`
- Locator proposto: `select[name="lstUf"]`
- Pré-condição original: falhou
- Execução curada: passou
- Pós-condição: selected value = `MT`
- Status: `healed_validated`

## Healings rejeitados

### Step 12 — Resultado do cálculo

- Falha original: assert textual não encontrado
- Causa provável: selector contém valor monetário dinâmico
- Locator original: `role=listitem[name="Valor mínimo de entrada R$ 13.514,64"]`
- Proposta: `text=Valor mínimo de entrada`
- Resultado: elemento encontrado, mas oracle de valor divergiu
- Status: `healing_rejected`
- Recomendação: transformar assert em assert parcial por rótulo + validação dinâmica do valor

Mostrar mais linhas
11. Melhorias para evidência antes/depois

Hoje o EvidenceCollector captura screenshot, DOM, console e network; o EvidencePayload exige DOM suficiente e sanitiza DOM para LLM. O run-incremental deve tornar isso obrigatório por step crítico. [caixa-my.s...epoint.com], [caixa-my.s...epoint.com]
11.1. Evidência mínima por step
Para cada step:
Plain Textbefore:    screenshot    DOM snapshot    URL    title    candidate list    selected locator    actionability resultafter:    screenshot    DOM snapshot    URL    title    postcondition result    oracle result    network deltaMostrar mais linhas
11.2. Network delta
Como o recorder já captura request/response, o incremental runner deveria capturar delta de rede por step:
Plain Textnetwork_before_index = len(network_buffer)executa stepnetwork_after = network_buffer[network_before_index:]Mostrar mais linhas
Isso ajuda principalmente em cálculos assíncronos, submits e telas Angular/SPA em que a mudança visual demora. O arquivo de análise já aponta que network_log.json existe, mas ainda não é usado no replay. [caixa-my.s...epoint.com], [caixa-my.s...epoint.com]

12. Melhorias no healing para evitar falso positivo
12.1. Healing nunca deve ser promovido sem pós-condição
Regra:
Plain TextSe healing executou mas não há pós-condição positiva:    status = healing_applied_but_unvalidated    promotion = blockedMostrar mais linhas
O projeto já possui PromotionGate, que exige evidência, oracle e uniqueness mínima; o run-incremental deve acionar esse gate sempre que uma cura for candidata à promoção. [caixa-my.s...epoint.com], [caixa-my.s...epoint.com]

12.2. Penalizar healing genérico
No relatório, marcar candidato suspeito quando:
Plain Text- locator é text=Selecione;- locator é button genérico;- locator é body;- locator tem baixa unicidade;- locator mudou tag de forma incompatível;- locator não está no mesmo contexto do step original.Mostrar mais linhas
Isso conversa diretamente com o problema de candidatos genéricos como text=Selecione e locators frágeis já identificados. [caixa-my.s...epoint.com], [caixa-my.s...epoint.com]

12.3. Registrar “por que não curou”
Para todo healing rejeitado:
JSON{  "healing_rejection_reason": [    "oracle_failed",    "postcondition_failed",    "locator_not_unique",    "actionability_failed"  ]}Mostrar mais linhas
Sem isso, a equipe só vê “falhou”, mas não sabe se o problema foi selector, timing, ação errada, valor esperado dinâmico ou oracle fraco.

13. Ordem prática de implementação
Eu faria em 5 fatias pequenas:
Fatia 1 — Criar comando e esqueleto
Entregável:
Plain Texttestforge run-incremental <script>Mostrar mais linhas
Critérios:
Plain Text- carrega script;- identifica recording_id;- normaliza steps;- abre browser;- executa navigation/fill/click/assert básico;- imprime status por step.Mostrar mais linhas

Fatia 2 — Pré-condições
Entregável:
Plain TextStepPreconditionValidatorMostrar mais linhas
Critérios:
Plain Text- usa ActionabilityValidator;- valida selector vazio;- valida depends_on/blocking;- valida select como select;- valida fill com valor;- explica failures.Mostrar mais linhas

Fatia 3 — Pós-condições
Entregável:
Plain TextStepPostconditionValidatorMostrar mais linhas
Critérios:
Plain Text- fill verifica valor final;- click verifica navegação ou próximo step;- select verifica selected value/text;- assert usa OracleRunner;- falha de pós-condição aciona healing.Mostrar mais linhas

Fatia 4 — Healing incremental
Entregável:
Plain TextIntegração com CuradorAutomatico + SmartStepRunnerMostrar mais linhas
Critérios:
Plain Text- healing só vira sucesso se pós-condição passar;- shadow mode registra hipótese sem alterar resultado;- relatório mostra camada, família, estratégia e confiança.Mostrar mais linhas

Fatia 5 — Relatório completo
Entregável:
Plain Textruns/<id>/<timestamp>/execution_report.jsonruns/<id>/<timestamp>/healing_report.mdMostrar mais linhas
Critérios:
Plain Text- mostra pré e pós-condições;- lista candidates completos;- mostra locator original/usado/curado;- registra evidência before/after;- separa attempted/applied/validated/rejected;- explica skipped e blocked.Mostrar mais linhas

14. Recomendação final
Minha recomendação é: não tentar estabilizar o fluxo gravado apenas melhorando selectors dentro do run atual. O ganho real virá quando cada step tiver um ciclo fechado:
Plain Textpré-condição → execução → pós-condição → evidência → healing → oracle → decisãoMostrar mais linhas
O run-incremental deve virar o “microscópio” do TestForge: ele mostra exatamente onde o fluxo diverge da gravação, se o problema é locator, actionability, timing, dado dinâmico, assert frágil ou falso healing. Isso ataca diretamente a dor que vocês sentiram ontem: ficar horas tentando passar por campo de data, preencher valor e clicar em botão sem saber exatamente qual camada estava falhando.
FontesForneça seus comentários sobre o BizChatYou said: Como integrar o IncrementalRunner com o CuradorAutomatico? Como validar se o healing foi realmente aplicado?Copilot said: CopilotProcessamento concluído em 1 etapaAndre, a integração ideal é tratar o CuradorAutomatico como um serviço de cura por step, chamado pelo IncrementalRunner somente quando uma das três fases falhar:
Plain Text1. pré-condição falhou2. execução do step falhou3. pós-condição falhouMostrar mais linhas
E a validação do healing deve ser feita em duas camadas:
Plain TextA. validação operacional:   a ação curada executou sem erro?B. validação semântica:   a ação curada produziu o efeito esperado?Mostrar mais linhas
Ou seja: não basta o SmartStepRunner.execute() passar. O healing só é verdadeiro se, depois da ação curada, o PostconditionValidator/OracleRunner confirmar o resultado esperado. O projeto já tem as peças principais para isso: CuradorAutomatico, EvidencePayload, SmartStepRunner, OracleRunner, PromotionGate, MetricsRepository e RunReport; falta organizar a orquestração no IncrementalRunner. [caixa-my.s...epoint.com]

1. Papel de cada componente
A integração fica assim:
Plain TextIncrementalRunner ├── StepPreconditionValidator ├── StepExecutor ├── StepPostconditionValidator ├── EvidenceCollector ├── CuradorAutomatico │    ├── L0 HealingCatalog │    ├── L2 SpecialistAgents │    └── L3 LLMHealer / MockLLMHealer ├── SmartStepRunner ├── OracleRunner ├── PromotionGate └── IncrementalReportMostrar mais linhas
O CuradorAutomatico já orquestra o pipeline L0→L2→L3, usando catálogo de receitas, agentes especialistas e LLM/mock como fallback. Ele recebe step_data, error_message e EvidencePayload, monta uma proposta de cura, executa via step_runner e retorna um CurationOutcome. [caixa-my.s...epoint.com]
A mudança principal é: o IncrementalRunner deve fornecer ao CuradorAutomatico um step_runner que execute a proposta e depois rode uma validação pós-ação fora do curador.

2. Fluxo recomendado de integração
Fluxo completo
Plain TextStep falha↓IncrementalRunner coleta evidência↓FailureClassifier classifica implicitamente dentro do CuradorAutomatico↓CuradorAutomatico tenta L0/L2/L3↓SmartStepRunner executa proposta↓CuradorAutomatico retorna PASSED_STEP ou UNRESOLVED↓IncrementalRunner roda pós-condição/oracle↓Se pós-condição passou:    healing_validatedSenão:    false_healing ou healing_rejectedMostrar mais linhas
O ponto crítico é que PASSED_STEP significa: a tentativa técnica executou sem erro. Ainda precisamos responder: executou a coisa certa? Essa resposta pertence ao IncrementalRunner, usando pós-condições e oracles. [caixa-my.s...epoint.com]

3. Interface sugerida no IncrementalRunner
Eu criaria um método dedicado:
Pythondef _heal_failed_step(    self,    step,    step_num: int,    original_error: str,    failure_phase: str,    result,):    ...Mostrar mais linhas
Onde:
Plain Textstep             = SemanticAction atualstep_num         = número do steporiginal_error   = erro de pré-condição, execução ou pós-condiçãofailure_phase    = "precondition" | "execution" | "postcondition"result           = IncrementalStepResult em construçãoMostrar mais linhas

4. Montando o EvidencePayload
O CuradorAutomatico precisa de uma evidência suficiente. O projeto já possui EvidenceCollector.build_llm_payload(), que monta EvidencePayload com contexto do step, DOM sanitizado, console, network e screenshot opcional. O EvidencePayload considera DOM suficiente quando há snapshot com pelo menos 100 caracteres. [caixa-my.s...epoint.com]
Exemplo:
Pythondef _build_healing_payload(self, step, step_num, original_error, failure_phase):    selector = self._primary_selector(step)    step_context = {        "action": step.action,        "selector": selector or "(empty)",        "value": step.value or "",        "text": step.target.text if step.target else "",        "intention": self._describe_intention(step, step_num),        "url": self.page.url,        "framework": self.app_name or "generic",        "step_number": step_num,        "failure_phase": failure_phase,        "original_error": original_error,    }    payload = self.evidence_collector.build_llm_payload(        step_context,        include_screenshot=False,    )    return payloadMostrar mais linhas
Minha recomendação: para MVP, include_screenshot=False continua aceitável, porque DOM + contexto já são suficientes para a maioria dos healings determinísticos. Depois, podemos ligar screenshot quando quisermos ajudar o LLM ou auditoria.

5. Criando o step_runner para o CuradorAutomatico
O CuradorAutomatico recebe um step_runner. Hoje no cmd_run, ele é montado com SmartStepRunner(page). A mesma ideia deve ser usada no IncrementalRunner. [caixa-my.s...epoint.com]
Pythonfrom testforge.runner.fallback_runner import SmartStepRunnerfrom testforge.healing import CuradorAutomatico, HealingCatalogdef _make_curator(self):    smart_runner = SmartStepRunner(self.page)    def step_runner(step_data: dict):        strategy = step_data.get("strategy", "")        return smart_runner.execute(step_data, strategy)    return CuradorAutomatico(        catalog=HealingCatalog(),        step_runner=step_runner,    )Mostrar mais linhas
O step_data que vai para o curador deve ser pequeno e objetivo:
Pythonstep_data = {    "selector": original_selector,    "action": step.action,    "value": step.value or "",    "base_url": self.base_url,}Mostrar mais linhas
O próprio CuradorAutomatico troca o selector no _build_step_copy() quando recebe uma proposta nova de locator/estratégia. [caixa-my.s...epoint.com]

6. Implementação do _heal_failed_step
Exemplo completo:
Pythondef _heal_failed_step(    self,    step,    step_num: int,    original_error: str,    failure_phase: str,    result,):    original_selector = self._primary_selector(step)    payload = self._build_healing_payload(        step=step,        step_num=step_num,        original_error=original_error,        failure_phase=failure_phase,    )    if not payload.is_sufficient:        result.status = "failed"        result.error_message = (            f"Healing não tentado: evidência insuficiente — "            f"{payload.insufficiency_reason}"        )        result.healing = {            "attempted": False,            "reason": "insufficient_evidence",        }        return result    curator = self._make_curator()    step_data = {        "selector": original_selector or "",        "action": step.action,        "value": step.value or "",        "base_url": self.base_url,    }    outcome = curator.cure(        step_data=step_data,        error_message=original_error,        evidence=payload,    )    result.healing = self._map_curation_outcome(        outcome=outcome,        original_selector=original_selector,        failure_phase=failure_phase,    )    if outcome.status != "PASSED_STEP":        result.status = "failed"        result.error_message = (            f"Healing rejeitado ou não resolvido: {outcome.status} "            f"{outcome.error_message or ''}"        )        return result    # Validação semântica obrigatória pós-healing    post = self.postcondition_validator.validate(        step=step,        page=self.page,        next_step=self._next_executable_step(step_num),    )    result.postcondition = post    if post.passed:        result.status = "healed_validated"        result.healing["validated"] = True        result.healing["oracle_passed"] = True        result.healing["rejection_reason"] = []    else:        result.status = "failed"        result.healing["validated"] = False        result.healing["oracle_passed"] = False        result.healing["rejection_reason"] = [            "postcondition_failed",            *post.failures,        ]        result.error_message = (            "Healing executou, mas a pós-condição falhou: "            f"{post.message}"        )    return resultMostrar mais linhas
Esse é o coração da integração.

7. Como validar se o healing foi realmente aplicado
Eu usaria uma validação em 5 níveis.

Nível 1 — O curador retornou proposta válida?
Verificar:
Plain Text- outcome existe;- outcome.status == PASSED_STEP;- outcome.layer_used foi preenchido;- proposal existe quando aplicável;- confidence >= threshold;- taxonomy_id/family são válidos.Mostrar mais linhas
O CuradorAutomatico já valida confidence e taxonomia quando executa L2/L3. Ele só segue com proposta se a confiança e a taxonomia forem aceitáveis. [caixa-my.s...epoint.com]
Mas isso ainda não prova que o healing é verdadeiro. Prova apenas que a proposta foi considerada executável.

Nível 2 — O locator curado foi realmente usado?
Esse é um ponto importante. Precisamos registrar:
Plain Textlocator_originallocator_propostolocator_executadoestratégia_executadaMostrar mais linhas
Hoje o CurationOutcome carrega proposal.new_locator, proposal.strategy, layer_used, family e taxonomy_id. O IncrementalRunner deve copiar isso para o relatório do step. [caixa-my.s...epoint.com]
Exemplo:
Pythondef _map_curation_outcome(self, outcome, original_selector, failure_phase):    data = {        "attempted": True,        "status": outcome.status,        "layer": outcome.layer_used,        "family": outcome.family,        "taxonomy_id": outcome.taxonomy_id,        "failure_phase": failure_phase,        "original_locator": original_selector,        "validated": False,        "oracle_passed": False,        "rejection_reason": [],    }    if outcome.proposal:        data.update({            "strategy": outcome.proposal.strategy,            "proposed_locator": outcome.proposal.new_locator,            "confidence": outcome.proposal.confidence,            "rationale": outcome.proposal.rationale,            "raw_response": outcome.proposal.raw_response,        })    return dataMostrar mais linhas
Se proposed_locator estiver vazio ou igual ao locator original quebrado, isso deve aparecer no relatório.

Nível 3 — A ação curada executou sem erro?
Isso é o que o SmartStepRunner confirma indiretamente: se o step runner não levantou exceção, o CuradorAutomatico classifica como PASSED_STEP. [caixa-my.s...epoint.com]
Mas aqui existe uma armadilha:
Plain Textclick sem erro ≠ click corretofill sem erro ≠ valor corretoassert sem erro ≠ regra certaselect sem erro ≠ opção certa se o selector estava erradoMostrar mais linhas
Portanto, esse nível é necessário, mas insuficiente.

Nível 4 — A pós-condição passou?
Essa deve ser a regra oficial:
Plain TextHealing só é verdadeiro se a pós-condição passar.Mostrar mais linhas
Exemplos:
Para fill
Plain Text- valor atual do campo equivale ao valor esperado;- se máscara, comparação normalizada;- se Angular/currencymask, blur/Tab foi aplicado e valor ficou estável.Mostrar mais linhas
Para select_option
Plain Text- selected value ou selected label é o esperado.Mostrar mais linhas
Para click
Plain Text- se esperava navegação, URL mudou;- se esperava próximo elemento, ele apareceu;- se esperava resultado, oracle visual/dom passou;- se esperava API, houve resposta de rede compatível.Mostrar mais linhas
Para assert
Plain Text- assert esperado passou via OracleRunner.Mostrar mais linhas
O projeto já tem OracleRunner com validações visual_dom e business_state, e o PromotionGate usa resultados de oracle para aprovar ou rejeitar promoções. [caixa-my.s...epoint.com]

Nível 5 — O PromotionGate autorizou promoção?
Nem todo healing validado deve virar receita permanente imediatamente.
Recomendo:
Plain Texthealed_validated:    passou nesta execuçãopromotable:    pode ser considerado pelo PromotionGatepromoted:    aprovado para catálogo/histórico depois de critérios adicionaisMostrar mais linhas
O PromotionGate já avalia evidência, oracles e uniqueness mínima. Se falta screenshot, oracle ou uniqueness adequada, ele bloqueia. [caixa-my.s...epoint.com]
Exemplo:
Pythondef _evaluate_healing_promotion(self, result):    oracle_results = []    if result.postcondition:        oracle_results = result.postcondition.oracle_results    evidence = {        "screenshots": [            result.evidence_before.get("screenshot"),            result.evidence_after.get("screenshot"),        ]    }    uniqueness_score = result.healing.get("uniqueness_score", 1.0)    decision = self.promotion_gate.evaluate(        oracle_results=oracle_results,        evidence=evidence,        uniqueness_score=uniqueness_score,    )    result.healing["promotion_state"] = decision.state.value    result.healing["promotion_allowed"] = decision.allowed    result.healing["promotion_reasons"] = decision.reasons    result.healing["promotion_blocks"] = decision.blocksMostrar mais linhas

8. Critério oficial: quando marcar cada status
Eu usaria estes status no IncrementalRunner:
Plain Textpassed    step passou sem healing.failed    step falhou e não foi curado.healing_attempted    curador foi chamado, mas ainda sem decisão final.healed_applied    proposta executou sem erro, mas ainda sem validação semântica.healed_validated    proposta executou e pós-condição/oracle passou.healing_rejected    proposta executou ou foi proposta, mas pós-condição/oracle falhou.shadow_healed    em shadow mode, proposta teria funcionado, mas não alterou o resultado oficial.blocked    step não executado por dependência anterior.skipped    step omitido por motivo explícito.Mostrar mais linhas
Regra prática:
Pythonif outcome.status == "PASSED_STEP" and postcondition.passed:    status = "healed_validated"elif outcome.status == "PASSED_STEP" and not postcondition.passed:    status = "healing_rejected"elif outcome.status != "PASSED_STEP":    status = "failed"Mostrar mais linhas

9. Como tratar Shadow Mode
No modo --shadow, o sistema deve simular o healing, mas não pode alterar o resultado oficial do teste.
Fluxo:
Plain Textstep original falha↓curador gera proposta↓runner tenta proposta em ambiente controlado ou no mesmo estado, quando seguro↓se proposta funcionaria:    registrar shadow_healed    mas status oficial continua failed↓se proposta não funcionaria:    registrar shadow_negativeMostrar mais linhas
Exemplo:
Pythonif self.shadow_mode:    shadow_result = self._try_shadow_healing(step, error_message)    result.healing = shadow_result.healing    if shadow_result.postcondition.passed:        result.status = "failed"        result.healing["shadow_status"] = "shadow_healed"        result.healing["official_result_changed"] = False    else:        result.status = "failed"        result.healing["shadow_status"] = "shadow_rejected"    return resultMostrar mais linhas
Isso permite medir precisão sem promover automaticamente. Essa ideia já está alinhada com o planejamento do TestForge para shadow mode, false healing e PromotionGate. [caixa-my.s...epoint.com]

10. Exemplo de relatório de healing validado
JSON{  "step_num": 4,  "action": "click",  "status": "healed_validated",  "original_locator": "label:has-text(\"UF\") + input",  "healing": {    "attempted": true,    "status": "PASSED_STEP",    "layer": "L2",    "family": "FAM-01",    "taxonomy_id": "SEL-004",    "strategy": "semantic_locator_conversion",    "original_locator": "label:has-text(\"UF\") + input",    "proposed_locator": "select[name=\"lstUf\"]",    "confidence": 0.91,    "validated": true,    "oracle_passed": true,    "promotion_state": "shadow_validated",    "promotion_allowed": true,    "promotion_blocks": []  },  "postcondition": {    "passed": true,    "checks": {      "selected_value_matches": true    }  }}Mostrar mais linhas

11. Exemplo de falso healing
JSON{  "step_num": 12,  "action": "assert",  "status": "healing_rejected",  "original_locator": "role=listitem[name=\"Valor mínimo de entrada R$ 13.514,64\"]",  "healing": {    "attempted": true,    "status": "PASSED_STEP",    "layer": "L2",    "family": "FAM-08",    "taxonomy_id": "AST-001",    "strategy": "has_text_fallback",    "proposed_locator": "text=\"Valor mínimo de entrada\"",    "confidence": 0.78,    "validated": false,    "oracle_passed": false,    "rejection_reason": [      "postcondition_failed",      "dynamic_value_mismatch"    ],    "promotion_allowed": false,    "promotion_blocks": [      "oracle_failed"    ]  },  "postcondition": {    "passed": false,    "message": "Texto encontrado, mas valor esperado diverge da massa atual"  }}Mostrar mais linhas
Esse caso é importante porque o projeto já identificou problema com selectors de resultado contendo valores monetários dinâmicos: o locator gravado com R$ 13.514,64 falha quando a massa de dados muda para produzir R$ 42.000,00. [caixa-my.s...epoint.com]

12. Métricas corretas para validar healing
Eu registraria no MetricsRepository:
Pythonmetrics.record_step(StepOutcome.FAILURE_DETECTED, ...)metrics.record_step(StepOutcome.HEALING_ATTEMPTED, ...)if outcome.status == "PASSED_STEP":    metrics.record_step(StepOutcome.HEALING_APPLIED, ...)if postcondition.passed:    metrics.record_step(StepOutcome.ORACLE_VALIDATED, ...)else:    metrics.record_step(StepOutcome.HEALING_REJECTED, ...)Mostrar mais linhas
O projeto já possui StepOutcome com esses estados: FAILURE_DETECTED, HEALING_ATTEMPTED, HEALING_APPLIED, ORACLE_VALIDATED e HEALING_REJECTED. [caixa-my.s...epoint.com]
A métrica que importa não é apenas:
Plain Texthealings_aplicadosMostrar mais linhas
Mas sim:
Plain Texthealings_validados / healings_tentadosMostrar mais linhas
E também:
Plain Textfalse_heal = healing aplicado, mas oracle/pós-condição falhouMostrar mais linhas

13. Testes automatizados necessários
Eu criaria testes específicos para garantir que a integração está correta.
Teste 1 — Healing aplicado e validado
Plain TextDado um botão cujo ID mudouQuando o step original falhaE o curador propõe text=PesquisarE o click produz o resultado esperadoEntão o status deve ser healed_validatedE oracle_passed deve ser trueMostrar mais linhas
Teste 2 — Healing executa, mas pós-condição falha
Plain TextDado um selector alternativo que clica no botão erradoQuando o curador retorna PASSED_STEPMas o resultado esperado não apareceEntão status deve ser healing_rejectedE false_heal deve ser registradoMostrar mais linhas
Teste 3 — Pré-condição falha e healing corrige
Plain TextDado um selector original inexistenteQuando a pré-condição falhaEntão o curador deve ser chamadoE, se locator alternativo passar, status deve ser healed_validatedMostrar mais linhas
Teste 4 — Select curado
Plain TextDado um step gravado errado como label + inputQuando o elemento real é select[name=lstUf]Então healing deve propor select[name=lstUf]E pós-condição selected value = MT deve passarMostrar mais linhas
Teste 5 — Shadow mode
Plain TextDado um step que falhaQuando shadow mode está ativoEntão a proposta é avaliadaMas o resultado oficial não é alteradoMostrar mais linhas

14. Decisão técnica recomendada
Minha recomendação objetiva:

O CuradorAutomatico não deve decidir sozinho se o healing é verdadeiro.
Ele deve decidir se há uma proposta executável.
O IncrementalRunner deve decidir se a proposta foi validada semanticamente.
O PromotionGate deve decidir se a proposta pode ser promovida/reutilizada.

Ficaria assim:
Plain TextCuradorAutomatico:    "consegui executar uma alternativa?"IncrementalRunner:    "essa alternativa produziu o efeito certo?"PromotionGate:    "essa alternativa tem evidência suficiente para virar aprendizado?"Mostrar mais linhas
Essa separação deixa o TestForge muito mais seguro, porque impede que “click sem erro” seja confundido com “teste correto”.
FontesForneça seus comentários sobre o BizChatYou said: Como implementar o _heal_failed_step? Como registrar métricas de healing? Como testar o CuradorAutomatico?Copilot said: CopilotProcessamento concluído em 1 etapaAndre, eu implementaria o _heal_failed_step como uma ponte controlada entre o IncrementalRunner e o CuradorAutomatico: ele recebe o step que falhou, monta evidência, chama o curador, executa a proposta pelo SmartStepRunner, valida pós-condição/oracle e registra métricas. O ponto central é: CuradorAutomatico pode dizer que a tentativa executou (PASSED_STEP), mas quem decide se foi healing verdadeiro é o IncrementalRunner, via pós-condição/oracle. O projeto já tem CuradorAutomatico, CurationOutcome, ProgressResult, EvidencePayload, SmartStepRunner, MetricsRepository, StepOutcome, OracleRunner e PromotionGate, então a implementação deve reutilizar essas peças em vez de criar outro pipeline paralelo. [caixa-my.s...epoint.com]

1. Como implementar o _heal_failed_step
1.1. Assinatura recomendada
No futuro arquivo:
Plain Textsrc/testforge/runner/incremental_runner.pyMostrar mais linhas
eu colocaria:
Pythondef _heal_failed_step(    self,    step,    step_num: int,    original_error: str,    failure_phase: str,    result,):    ...Mostrar mais linhas
Onde:
Plain Textstep             = SemanticAction que falhoustep_num         = número do step, começando em 1original_error   = erro da pré-condição, execução ou pós-condiçãofailure_phase    = "precondition" | "execution" | "postcondition"result           = IncrementalStepResult em construçãoMostrar mais linhas
A fase da falha é importante porque um healing acionado por pré-condição falha é diferente de um healing acionado por pós-condição falha. Exemplo: selector inexistente é diferente de “click executou, mas resultado não apareceu”.

1.2. Implementação-base
Pythonfrom testforge.healing import CuradorAutomatico, HealingCatalog, ProgressResultfrom testforge.runner.fallback_runner import SmartStepRunnerfrom testforge.metrics import StepOutcomedef _heal_failed_step(    self,    step,    step_num: int,    original_error: str,    failure_phase: str,    result,):    """    Tenta curar um step falho usando CuradorAutomatico.    Regras:    1. Registra falha detectada.    2. Monta EvidencePayload.    3. Chama CuradorAutomatico.    4. Se o curador aplicar a proposta, valida pós-condição.    5. Só marca como healed_validated se o oracle/pós-condição passar.    """    original_selector = self._primary_selector(step)    # 1. Métrica: falha detectada    self.metrics.record_step(        StepOutcome.FAILURE_DETECTED,        step_num=step_num,        action=step.action,        selector=original_selector or "",    )    # 2. Coleta evidência para o curador/LLM/agentes    payload = self._build_healing_payload(        step=step,        step_num=step_num,        original_error=original_error,        failure_phase=failure_phase,    )    if not payload.is_sufficient:        result.status = "failed"        result.error_message = (            "Healing não tentado: evidência insuficiente — "            f"{payload.insufficiency_reason}"        )        result.healing = {            "attempted": False,            "reason": "insufficient_evidence",            "failure_phase": failure_phase,            "original_error": original_error,        }        return result    # 3. Cria curador com SmartStepRunner    curator = self._make_curator()    step_data = {        "selector": original_selector or "",        "action": step.action,        "value": step.value or "",        "base_url": self.base_url,    }    # 4. Métrica: healing tentado    self.metrics.record_step(        StepOutcome.HEALING_ATTEMPTED,        step_num=step_num,        action=step.action,        selector=original_selector or "",    )    # 5. Chama CuradorAutomatico    outcome = curator.cure(        step_data=step_data,        error_message=original_error,        evidence=payload,    )    # 6. Mapeia outcome para relatório incremental    result.healing = self._map_curation_outcome(        outcome=outcome,        original_selector=original_selector,        failure_phase=failure_phase,        original_error=original_error,    )    family_code = outcome.family or result.healing.get("family", "")    healing_layer = outcome.layer_used or result.healing.get("layer", "")    # 7. Se o curador não conseguiu executar a proposta    if outcome.status != ProgressResult.PASSED_STEP:        self.metrics.record_step(            StepOutcome.HEALING_REJECTED,            step_num=step_num,            action=step.action,            family_code=family_code,            healing_layer=healing_layer,            selector=original_selector or "",        )        result.status = "failed"        result.error_message = (            f"Healing não resolvido: {outcome.status}. "            f"{outcome.error_message or ''}"        )        result.healing["validated"] = False        result.healing["rejection_reason"] = [            "curator_outcome_not_passed_step",            outcome.status,        ]        return result    # 8. Métrica: healing aplicado tecnicamente    self.metrics.record_step(        StepOutcome.HEALING_APPLIED,        step_num=step_num,        action=step.action,        family_code=family_code,        healing_layer=healing_layer,        selector=result.healing.get("proposed_locator", original_selector or ""),    )    # 9. Validação semântica pós-healing    post = self.postcondition_validator.validate(        step=step,        page=self.page,        next_step=self._next_executable_step(step_num),    )    result.postcondition = post    if post.passed:        # 10. Métrica: oracle/pós-condição validou o healing        self.metrics.record_step(            StepOutcome.ORACLE_VALIDATED,            step_num=step_num,            action=step.action,            family_code=family_code,            healing_layer=healing_layer,            selector=result.healing.get("proposed_locator", original_selector or ""),        )        result.status = "healed_validated"        result.healing["validated"] = True        result.healing["oracle_passed"] = True        result.healing["rejection_reason"] = []        # Opcional: avaliar promoção        self._evaluate_healing_promotion(result)        return result    # 11. Curador executou, mas a pós-condição falhou => falso healing/rejeitado    self.metrics.record_step(        StepOutcome.HEALING_REJECTED,        step_num=step_num,        action=step.action,        family_code=family_code,        healing_layer=healing_layer,        selector=result.healing.get("proposed_locator", original_selector or ""),    )    result.status = "healing_rejected"    result.error_message = (        "Healing executou, mas a pós-condição/oracle falhou: "        f"{post.message}"    )    result.healing["validated"] = False    result.healing["oracle_passed"] = False    result.healing["rejection_reason"] = [        "postcondition_failed",        *getattr(post, "failures", []),    ]    return resultMostrar mais linhas

2. Métodos auxiliares necessários
2.1. _make_curator
O CuradorAutomatico precisa receber um step_runner. Hoje, no fluxo atual, o cmd_run cria um SmartStepRunner e passa uma função runner para o curador. A ideia deve ser a mesma no IncrementalRunner. [caixa-my.s...epoint.com]
Pythondef _make_curator(self):    smart_runner = SmartStepRunner(self.page)    def step_runner(step_data: dict):        strategy = step_data.get("strategy", "")        return smart_runner.execute(step_data, strategy)    return CuradorAutomatico(        catalog=HealingCatalog(),        step_runner=step_runner,    )Mostrar mais linhas

2.2. _build_healing_payload
O EvidenceCollector.build_llm_payload() já monta um EvidencePayload com contexto do step, DOM sanitizado, console, network e screenshot opcional. O EvidencePayload marca a evidência como suficiente quando há DOM com pelo menos 100 caracteres. [caixa-my.s...epoint.com]
Pythondef _build_healing_payload(    self,    step,    step_num: int,    original_error: str,    failure_phase: str,):    selector = self._primary_selector(step)    text_value = ""    if step.target:        text_value = step.target.text or step.target.label or step.target.accessible_name or ""    step_context = {        "action": step.action,        "selector": selector or "(empty — no selector available)",        "value": step.value or "",        "text": text_value,        "intention": self._describe_intention(step, step_num),        "url": self.page.url,        "framework": self.app_name or "generic",        "step_number": step_num,        "failure_phase": failure_phase,        "original_error": original_error,    }    return self.evidence_collector.build_llm_payload(        step_context=step_context,        include_screenshot=False,    )Mostrar mais linhas

2.3. _map_curation_outcome
Pythondef _map_curation_outcome(    self,    outcome,    original_selector: str,    failure_phase: str,    original_error: str,):    healing = {        "attempted": True,        "status": outcome.status,        "layer": outcome.layer_used,        "family": outcome.family,        "taxonomy_id": outcome.taxonomy_id,        "failure_phase": failure_phase,        "original_error": original_error,        "original_locator": original_selector,        "validated": False,        "oracle_passed": False,        "rejection_reason": [],        "entry_id": outcome.entry_id,    }    if outcome.proposal:        healing.update({            "strategy": outcome.proposal.strategy,            "proposed_locator": outcome.proposal.new_locator,            "confidence": outcome.proposal.confidence,            "rationale": outcome.proposal.rationale,            "raw_response": outcome.proposal.raw_response or "",        })    if outcome.error_message:        healing["curator_error_message"] = outcome.error_message    return healingMostrar mais linhas

2.4. _evaluate_healing_promotion
O PromotionGate já existe e bloqueia promoção quando evidência está incompleta, oracle está ausente/falhou/conflitou ou uniqueness é baixa. O incremental deve chamar o gate depois que a pós-condição passar. [caixa-my.s...epoint.com]
Pythondef _evaluate_healing_promotion(self, result):    oracle_results = []    if result.postcondition:        oracle_results = getattr(result.postcondition, "oracle_results", []) or []    evidence = {        "screenshots": [            result.evidence_before.get("screenshot"),            result.evidence_after.get("screenshot"),        ]    }    uniqueness_score = result.healing.get("uniqueness_score", 1.0)    decision = self.promotion_gate.evaluate(        oracle_results=oracle_results,        evidence=evidence,        uniqueness_score=uniqueness_score,    )    result.healing["promotion_state"] = decision.state.value    result.healing["promotion_allowed"] = decision.allowed    result.healing["promotion_reasons"] = decision.reasons    result.healing["promotion_blocks"] = decision.blocksMostrar mais linhas

3. Como registrar métricas de healing
O projeto já tem MetricsRepository e StepOutcome com os eventos necessários:
Pythonclass StepOutcome(str, Enum):    FAILURE_DETECTED = "falha_detectada"    HEALING_ATTEMPTED = "healing_tentado"    HEALING_APPLIED = "aplicado"    ORACLE_VALIDATED = "validado"    HEALING_REJECTED = "rejeitado"Mostrar mais linhas
Esses contadores alimentam métricas por step: falhas_detectadas, healings_tentados, aplicados, validados, rejeitados e healing_success_rate. [caixa-my.s...epoint.com]

3.1. Regra de contagem correta
Use esta sequência:

1. Step falhou:
   FAILURE_DETECTED

2. Curador foi chamado:
   HEALING_ATTEMPTED

3. Curador conseguiu executar proposta:
   HEALING_APPLIED

4. Pós-condição/oracle passou:
   ORACLE_VALIDATED

5. Curador falhou ou pós-condição falhou:
   HEALING_REJECTED

A diferença entre APPLIED e VALIDATED é essencial. Um healing pode ser aplicado tecnicamente, mas rejeitado semanticamente. Esse é exatamente o controle necessário para medir falso healing. [caixa-my.s...epoint.com]

3.2. Helper para registrar métricas
Para evitar duplicação no _heal_failed_step, eu criaria:
Pythondef _record_healing_metric(    self,    outcome,    metric_outcome,    step_num: int,    step,    selector: str = "",):    family_code = ""    healing_layer = ""    if outcome:        family_code = outcome.family or ""        healing_layer = outcome.layer_used or ""    self.metrics.record_step(        metric_outcome,        step_num=step_num,        action=step.action,        family_code=family_code,        healing_layer=healing_layer,        selector=selector or self._primary_selector(step) or "",    )Mostrar mais linhas
Uso:
Pythonself._record_healing_metric(    outcome=None,    metric_outcome=StepOutcome.FAILURE_DETECTED,    step_num=step_num,    step=step,)self._record_healing_metric(    outcome=outcome,    metric_outcome=StepOutcome.HEALING_ATTEMPTED,    step_num=step_num,    step=step,)if outcome.status == ProgressResult.PASSED_STEP:    self._record_healing_metric(        outcome=outcome,        metric_outcome=StepOutcome.HEALING_APPLIED,        step_num=step_num,        step=step,        selector=result.healing.get("proposed_locator", ""),    )Mostrar mais linhas

3.3. Métrica final da execução
Ao final do IncrementalRunner.run(), agregue:
Pythondef _finalize_metrics(self):    healed_validated = sum(        1 for r in self.step_results        if r.status == "healed_validated"    )    healing_rejected = sum(        1 for r in self.step_results        if r.status == "healing_rejected"    )    failed = sum(        1 for r in self.step_results        if r.status == "failed"    )    llm_used = any(        getattr(r, "healing", {}).get("layer") == "L3"        for r in self.step_results    )    self.metrics.record_run(        healed=healed_validated > 0,        false_heal=healing_rejected > 0,        oracle_passed=healed_validated,        oracle_failed=healing_rejected + failed,        llm_used=llm_used,    )Mostrar mais linhas
Mas atenção: no relatório, eu daria mais destaque às métricas por step do que às globais, porque a granularidade por step é mais confiável para diagnosticar o problema.

4. Como testar o CuradorAutomatico
Eu testaria em três níveis:
Plain Text1. Teste unitário do CuradorAutomatico com step_runner fake.2. Teste unitário com EvidencePayload suficiente/insuficiente.3. Teste de integração com Playwright + página HTML simples.Mostrar mais linhas
O CuradorAutomatico já possui comportamento importante: rejeita evidência insuficiente, tenta catálogo L0, tenta agentes L2, usa L3/mock como fallback, valida confidence/taxonomia e retorna CurationOutcome. [caixa-my.s...epoint.com]

4.1. Teste 1 — evidência insuficiente
Objetivo: se o DOM é pequeno/vazio, o curador não deve tentar healing.
Pythonfrom testforge.healing import CuradorAutomatico, EvidencePayload, ProgressResultdef test_curador_rejects_insufficient_evidence():    curator = CuradorAutomatico(step_runner=lambda step: True)    payload = EvidencePayload(        step_context={            "action": "click",            "selector": "#missing",        },        dom_snapshot="",    )    payload.validate()    outcome = curator.cure(        step_data={            "selector": "#missing",            "action": "click",            "value": "",        },        error_message="element not found",        evidence=payload,    )    assert outcome.status == ProgressResult.UNRESOLVED    assert "Insufficient evidence" in outcome.error_messageMostrar mais linhas

4.2. Teste 2 — L2 resolve selector quebrado
Objetivo: falha FAM-01 deve chamar SelectorAgent/mock e executar o step_runner.
Pythonfrom testforge.healing import CuradorAutomatico, EvidencePayload, ProgressResultdef test_curador_l2_selector_healing_passes_with_step_runner():    executed = {        "called": False,        "selector": "",        "strategy": "",    }    def fake_step_runner(step_data):        executed["called"] = True        executed["selector"] = step_data.get("selector", "")        executed["strategy"] = step_data.get("strategy", "")        return True    curator = CuradorAutomatico(step_runner=fake_step_runner)    payload = EvidencePayload(        step_context={            "action": "click",            "selector": "#old-button",            "text": "Pesquisar",            "value": "",            "framework": "generic",        },        dom_snapshot="""            <html>              <body>                <button id="new-button">Pesquisar</button>              </body>            </html>        """ * 5,    )    payload.validate()    outcome = curator.cure(        step_data={            "selector": "#old-button",            "action": "click",            "value": "",        },        error_message="Step 1: click failed — selector '#old-button' not found",        evidence=payload,    )    assert outcome.status == ProgressResult.PASSED_STEP    assert executed["called"] is True    assert outcome.layer_used in ("L2", "L3", "L0")Mostrar mais linhas
Observação: dependendo do erro e do DOM, pode cair em L2 ou L3 mock. Para teste estrito de L2, dá para forçar mensagem/taxonomia esperada ou mockar route_to_agent.

4.3. Teste 3 — step_runner falha e curador retorna unresolved
Objetivo: se a proposta não executa, não pode marcar como healing verdadeiro.
Pythonfrom testforge.healing import CuradorAutomatico, EvidencePayload, ProgressResultdef test_curador_returns_unresolved_when_runner_fails():    def failing_step_runner(step_data):        raise Exception("patched locator also failed")    curator = CuradorAutomatico(step_runner=failing_step_runner)    payload = EvidencePayload(        step_context={            "action": "click",            "selector": "#old",            "text": "Pesquisar",            "framework": "generic",        },        dom_snapshot="<html><body><button>Pesquisar</button></body></html>" * 5,    )    payload.validate()    outcome = curator.cure(        step_data={            "selector": "#old",            "action": "click",            "value": "",        },        error_message="element not found",        evidence=payload,    )    assert outcome.status == ProgressResult.UNRESOLVEDMostrar mais linhas

4.4. Teste 4 — L0 HealingCatalog
Objetivo: quando há receita com prioridade alta no catálogo, o curador deve usar L0.
Pythonfrom pathlib import Pathfrom testforge.healing import (    CuradorAutomatico,    EvidencePayload,    HealingCatalog,    HealingRecipe,    ProgressResult,)def test_curador_uses_l0_catalog(tmp_path):    catalog_path = tmp_path / "healing-catalog.jsonl"    catalog = HealingCatalog(str(catalog_path))    recipe = HealingRecipe(        trigger_family="FAM-01",        trigger_code="SEL-004",        trigger_pattern="element not found",        trigger_framework="generic",        solution_strategy="has_text_fallback",        solution_selector="text=Pesquisar",        priority=10,        status="active",    )    catalog.add_recipe(recipe)    executed = {"selector": ""}    def fake_step_runner(step_data):        executed["selector"] = step_data.get("selector", "")        return True    curator = CuradorAutomatico(        catalog=catalog,        step_runner=fake_step_runner,    )    payload = EvidencePayload(        step_context={            "action": "click",            "selector": "#old",            "text": "Pesquisar",            "framework": "generic",        },        dom_snapshot="<html><body><button>Pesquisar</button></body></html>" * 5,    )    payload.validate()    outcome = curator.cure(        step_data={            "selector": "#old",            "action": "click",            "value": "",        },        error_message="element not found",        evidence=payload,    )    assert outcome.status == ProgressResult.PASSED_STEP    assert outcome.layer_used == "L0"    assert executed["selector"] == "text=Pesquisar"Mostrar mais linhas

4.5. Teste 5 — Integração com Playwright
Esse é o teste mais importante para evitar falso positivo.
Crie uma página mínima:
HTML<html>  <body>    <input id="cpf" placeholder="CPF">    <button id="btnNovo">Pesquisar</button>    <div id="resultado" style="display:none"></div>    <script>      document.getElementById("btnNovo").addEventListener("click", () => {        document.getElementById("resultado").style.display = "block";        document.getElementById("resultado").textContent = "CPF consultado";      });    </script>  </body></html>Mostrar mais linhas
Teste:
Pythonfrom playwright.sync_api import Pagefrom testforge.healing import CuradorAutomatico, EvidencePayload, ProgressResultfrom testforge.runner.fallback_runner import SmartStepRunnerfrom testforge.oracle import OracleRunnerdef test_curador_with_playwright_validates_real_effect(page: Page):    page.set_content("""        <html>          <body>            <button id="btnNovo">Pesquisar</button>            <div id="resultado" style="display:none"></div>            <script>              document.getElementById("btnNovo").addEventListener("click", () => {                document.getElementById("resultado").style.display = "block";                document.getElementById("resultado").textContent = "CPF consultado";              });            </script>          </body>        </html>    """)    smart = SmartStepRunner(page)    def step_runner(step_data):        strategy = step_data.get("strategy", "")        return smart.execute(step_data, strategy)    curator = CuradorAutomatico(step_runner=step_runner)    payload = EvidencePayload(        step_context={            "action": "click",            "selector": "#btnAntigo",            "text": "Pesquisar",            "value": "",            "framework": "generic",        },        dom_snapshot=page.content(),    )    payload.validate()    outcome = curator.cure(        step_data={            "selector": "#btnAntigo",            "action": "click",            "value": "",        },        error_message="element not found: #btnAntigo",        evidence=payload,    )    assert outcome.status == ProgressResult.PASSED_STEP    oracle = OracleRunner(page)    oracle_result = oracle.run_visual_dom("#resultado", "CPF consultado")    assert oracle_result.status == "passed"Mostrar mais linhas
Esse teste valida o mais importante: não só que o curador retornou PASSED_STEP, mas que o efeito esperado apareceu na tela.

5. Como testar o _heal_failed_step diretamente
Depois de criar o IncrementalRunner, faça um teste com dublês/mocks:
Pythondef test_heal_failed_step_marks_healed_validated_when_postcondition_passes():    runner = make_incremental_runner_for_test()    step = make_click_step(        selector="#btnAntigo",        text="Pesquisar",        action="click",    )    result = IncrementalStepResult(        step_num=1,        action="click",        status="failed",        original_locator="#btnAntigo",    )    runner.postcondition_validator = FakePostconditionValidator(passed=True)    healed = runner._heal_failed_step(        step=step,        step_num=1,        original_error="element not found",        failure_phase="execution",        result=result,    )    assert healed.status == "healed_validated"    assert healed.healing["attempted"] is True    assert healed.healing["validated"] is True    assert healed.healing["oracle_passed"] is TrueMostrar mais linhas
E o caso negativo:
Pythondef test_heal_failed_step_rejects_when_postcondition_fails():    runner = make_incremental_runner_for_test()    step = make_click_step(        selector="#btnAntigo",        text="Pesquisar",        action="click",    )    result = IncrementalStepResult(        step_num=1,        action="click",        status="failed",        original_locator="#btnAntigo",    )    runner.postcondition_validator = FakePostconditionValidator(        passed=False,        message="Resultado esperado não apareceu",        failures=["expected_result_not_visible"],    )    healed = runner._heal_failed_step(        step=step,        step_num=1,        original_error="element not found",        failure_phase="execution",        result=result,    )    assert healed.status == "healing_rejected"    assert healed.healing["validated"] is False    assert "postcondition_failed" in healed.healing["rejection_reason"]Mostrar mais linhas

6. Critérios de aceite para essa entrega
Eu colocaria os critérios assim:
Plain TextCA-01 — _heal_failed_step chama CuradorAutomatico quando step falha.CA-02 — Evidência insuficiente impede tentativa de healing e registra motivo.CA-03 — Métricas registram falha detectada, healing tentado, aplicado, validado ou rejeitado.CA-04 — Healing só recebe status healed_validated se pós-condição/oracle passar.CA-05 — Healing aplicado mas não validado vira healing_rejected.CA-06 — Relatório registra locator original, locator proposto, camada, família, taxonomia, estratégia e confidence.CA-07 — Testes cobrem sucesso, rejeição, evidência insuficiente, L0 catalog e integração com Playwright.Mostrar mais linhas

7. Recomendação prática para o próximo passo
Eu começaria implementando nesta ordem:

Criar _make_curator.
Criar _build_healing_payload.
Criar _map_curation_outcome.
Implementar _heal_failed_step.
Conectar métricas com MetricsRepository.
Criar testes unitários do CuradorAutomatico.
Criar um teste de integração com Playwright validando pós-condição.

A regra de ouro é esta:
Plain TextCuradorAutomatico decide se existe uma proposta executável.IncrementalRunner decide se a proposta resolveu o step.PromotionGate decide se a solução pode virar aprendizado.Mostrar mais linhas
Essa separação é o que vai impedir o TestForge de confundir “não deu exception” com “o fluxo realmente funcionou”.
FontesForneça seus comentários sobre o BizChatYou said: Como implementar o método _make_curator? Como validar a proposta do curador? Como garantir que o oracle valide o healing?Copilot said: CopilotProcessamento concluído em 1 etapaAndre, eu implementaria esses três pontos como um contrato claro entre IncrementalRunner, CuradorAutomatico e Oracle:
Plain Text_make_curator()    cria o CuradorAutomatico com um step_runner real baseado no SmartStepRunner_validar_proposta_do_curador()    garante que a proposta é segura antes/depois de executar_oracle_valida_healing()    confirma que a ação curada produziu o efeito esperadoMostrar mais linhas
A ideia central é: o curador propõe e tenta executar; o IncrementalRunner valida; o Oracle confirma o efeito. Isso evita considerar como “healing verdadeiro” um simples click/fill que não gerou exception, mas também não produziu o resultado esperado. O projeto já possui CuradorAutomatico, SmartStepRunner, EvidencePayload, OracleRunner, PromotionGate e MetricsRepository, então a integração deve reaproveitar essas peças. [caixa-my.s...epoint.com]

1. Como implementar o método _make_curator

1.1. Objetivo
O _make_curator deve criar uma instância do CuradorAutomatico com um step_runner capaz de executar a proposta de healing no browser atual. No projeto, o CuradorAutomatico espera receber uma função step_runner(step_data); internamente ele monta um patched_step com novo selector e estratégia, e chama esse runner para validar se a proposta executa. [caixa-my.s...epoint.com]
A implementação recomendada é:
Pythonfrom testforge.healing import CuradorAutomatico, HealingCatalogfrom testforge.runner.fallback_runner import SmartStepRunnerdef _make_curator(self) -> CuradorAutomatico:    """    Cria o CuradorAutomatico integrado ao browser atual do IncrementalRunner.    Responsabilidade:    - Instanciar SmartStepRunner com a page atual.    - Criar função step_runner compatível com CuradorAutomatico.    - Retornar CuradorAutomatico com HealingCatalog.    """    smart_runner = SmartStepRunner(self.page)    def step_runner(step_data: dict):        strategy = step_data.get("strategy", "")        return smart_runner.execute(step_data, strategy)    return CuradorAutomatico(        catalog=HealingCatalog(),        step_runner=step_runner,    )Mostrar mais linhas
Esse desenho mantém o CuradorAutomatico desacoplado do Playwright e deixa o IncrementalRunner responsável por fornecer o ambiente real de execução. O código atual do projeto já usa padrão semelhante no cmd_run, criando SmartStepRunner(page) e passando uma função runner para o curador. [caixa-my.s...epoint.com]

1.2. Versão melhorada com injeção de dependências
Para testes, eu recomendo permitir injetar catálogo e runner fake:
Pythondef _make_curator(    self,    catalog=None,    step_runner=None,) -> CuradorAutomatico:    """    Factory do CuradorAutomatico.    Permite injeção em testes:    - catalog fake ou temporário    - step_runner fake    """    if step_runner is None:        smart_runner = SmartStepRunner(self.page)        def step_runner(step_data: dict):            strategy = step_data.get("strategy", "")            return smart_runner.execute(step_data, strategy)    return CuradorAutomatico(        catalog=catalog or HealingCatalog(),        step_runner=step_runner,    )Mostrar mais linhas
Isso facilita testar o IncrementalRunner sem abrir navegador real, e também permite testar L0 usando um HealingCatalog temporário. O CuradorAutomatico aceita catálogo e step runner opcionais, então essa abordagem é compatível com a arquitetura atual. [caixa-my.s...epoint.com]

2. Como validar a proposta do curador
A validação da proposta deve acontecer em duas etapas:
Plain Text1. validação estrutural:   a proposta é coerente, segura e compatível?2. validação prática:   a proposta executou e produziu o resultado esperado?Mostrar mais linhas
O próprio CuradorAutomatico já valida confidence mínima e taxonomia para propostas L2/L3, mas o IncrementalRunner deve fazer uma validação adicional para impedir propostas genéricas, vazias ou perigosas. [caixa-my.s...epoint.com]

2.1. Método _validate_curator_proposal
Pythondef _validate_curator_proposal(self, outcome, step, original_selector: str):    """    Valida se a proposta retornada pelo CuradorAutomatico é aceitável    antes de considerá-la candidata a healing verdadeiro.    Importante:    - Não valida efeito de negócio.    - Apenas valida estrutura, coerência e risco da proposta.    """    failures = []    if outcome is None:        failures.append("missing_outcome")        return False, failures    if not outcome.layer_used:        failures.append("missing_layer_used")    # L0 pode não ter proposal explícita se veio de receita do catálogo.    proposal = outcome.proposal    if proposal:        if not proposal.new_locator:            failures.append("missing_new_locator")        if proposal.confidence < 0.5:            failures.append("low_confidence")        if not proposal.family:            failures.append("missing_family")        if not proposal.taxonomy_id:            failures.append("missing_taxonomy_id")        if not proposal.strategy:            failures.append("missing_strategy")        if self._is_dangerously_generic_locator(proposal.new_locator):            failures.append("generic_or_dangerous_locator")        if self._is_incompatible_action_strategy(step, proposal.strategy):            failures.append("incompatible_action_strategy")        if proposal.new_locator == original_selector and outcome.layer_used != "L0":            failures.append("same_locator_as_failed_original")    return len(failures) == 0, failuresMostrar mais linhas
Essa validação é necessária porque o projeto já identificou risco de candidatos genéricos, como text=Selecione, locators muito amplos, selectors estruturais frágeis e propostas que executam, mas não necessariamente atuam sobre o elemento correto. [caixa-my.s...epoint.com]

2.2. Bloquear locators genéricos ou perigosos
Pythondef _is_dangerously_generic_locator(self, locator: str) -> bool:    if not locator:        return True    normalized = locator.strip().lower()    generic_exact = {        "body",        "html",        "button",        "input",        "select",        "a",        "div",        "span",        "text=selecione",        "text=ok",        "text=cancelar",        "text=sim",        "text=não",        "text=nao",    }    if normalized in generic_exact:        return True    # XPath absoluto costuma ser frágil.    if normalized.startswith("/html/") or normalized.startswith("xpath=/html/"):        return True    # nth-child sem contexto é arriscado.    if "nth-child" in normalized and len(normalized) < 30:        return True    return FalseMostrar mais linhas
Isso não significa que textos como “OK” ou “Calcular” nunca possam ser usados; significa que eles não devem ser aceitos sem contexto, unicidade e validação pós-ação. O problema de candidatos genéricos e de ranking frágil já foi apontado no planejamento do TestForge. [caixa-my.s...epoint.com]

2.3. Validar compatibilidade entre ação e estratégia
Pythondef _is_incompatible_action_strategy(self, step, strategy: str) -> bool:    action = step.action    if action == "fill":        allowed = {            "press_sequentially",            "masked_input_detection",            "semantic_locator_conversion",            "label_click",            "synthetic_click",            "visibility_wait",        }        return strategy not in allowed    if action == "click":        allowed = {            "semantic_locator_conversion",            "has_text_fallback",            "visibility_wait",            "overlay_dismiss",            "dialog_handler",            "iframe_switch",            "label_click",            "synthetic_click",            "xpath_fallback",        }        return strategy not in allowed    if action == "select_option":        allowed = {            "semantic_locator_conversion",            "visibility_wait",            "xpath_fallback",        }        return strategy not in allowed    if action == "assert":        allowed = {            "semantic_locator_conversion",            "has_text_fallback",            "visibility_wait",        }        return strategy not in allowed    return FalseMostrar mais linhas
O projeto já possui várias estratégias no SmartStepRunner e nos agentes, como visibility_wait, press_sequentially, overlay_dismiss, iframe_switch, has_text_fallback, semantic_locator_conversion e outras; o ponto é impedir que uma estratégia adequada para input seja aplicada de forma cega em assert, select ou click. [caixa-my.s...epoint.com]

3. Como garantir que o Oracle valide o healing
3.1. Regra principal
A regra deve ser explícita no código:
Plain Textoutcome.status == PASSED_STEPnão é suficiente para status healed_validated.healed_validated só acontece quando:    CuradorAutomatico retornou PASSED_STEP    E PostconditionValidator/OracleRunner passouMostrar mais linhas
O CuradorAutomatico confirma que uma proposta foi executada pelo step_runner; o OracleRunner e as pós-condições confirmam que o resultado esperado apareceu. Essa separação é importante porque click/fill sem exception não garante que o fluxo funcionou. [caixa-my.s...epoint.com]

3.2. Método _validate_healing_with_oracle
Pythondef _validate_healing_with_oracle(self, step, step_num: int, result):    """    Valida semanticamente se o healing resolveu o step.    Retorna:    - postcondition result    - boolean indicando se healing foi validado    """    post = self.postcondition_validator.validate(        step=step,        page=self.page,        next_step=self._next_executable_step(step_num),    )    result.postcondition = post    if post.passed:        result.status = "healed_validated"        result.healing["validated"] = True        result.healing["oracle_passed"] = True        result.healing["rejection_reason"] = []        return True    result.status = "healing_rejected"    result.healing["validated"] = False    result.healing["oracle_passed"] = False    result.healing["rejection_reason"] = [        "postcondition_failed",        *getattr(post, "failures", []),    ]    result.error_message = (        "Healing executou, mas o oracle/pós-condição falhou: "        f"{post.message}"    )    return FalseMostrar mais linhas
O PostconditionValidator deve chamar o OracleRunner quando houver assert ou condição esperada; para clicks e selects, ele pode usar checks específicos, como URL alterada, próximo step visível, selected value correto ou texto de resultado visível. O projeto já usa OracleRunner para validações visual_dom e business_state. [caixa-my.s...epoint.com]

4. PostconditionValidator com Oracle
4.1. Interface recomendada
Pythonclass StepPostconditionValidator:    def __init__(self, page):        self.page = page        self.oracle = OracleRunner(page)    def validate(self, step, page, next_step=None):        if step.action == "fill":            return self._validate_fill(step)        if step.action == "select_option":            return self._validate_select_option(step)        if step.action == "click":            return self._validate_click(step, next_step)        if step.action == "assert":            return self._validate_assert(step)        if step.action == "navigation":            return self._validate_navigation(step)        return PostconditionResult(            passed=True,            checks={"no_specific_postcondition": True},            message="Sem pós-condição específica",        )Mostrar mais linhas
Essa abordagem transforma o Oracle em uma camada explícita do executor incremental, em vez de deixar a validação implícita dentro do runner. [caixa-my.s...epoint.com]

4.2. Validação para assert
Pythondef _validate_assert(self, step):    selector = self._primary_selector(step) or "body"    expected = step.value or ""    assert_type = "textual"    if step.context:        assert_type = step.context.get("assert_type", "textual")    if assert_type in ("textual", "automatico"):        oracle_result = self.oracle.run_visual_dom(selector, expected)    elif assert_type == "visivel":        oracle_result = self.oracle.run_visual_dom(selector, "")    else:        oracle_result = self.oracle.run_business_state(selector, expected)    return PostconditionResult(        passed=oracle_result.status == "passed",        checks={"oracle_status": oracle_result.status == "passed"},        oracle_results=[oracle_result],        failures=[] if oracle_result.status == "passed" else ["oracle_failed"],        message=oracle_result.message,    )Mostrar mais linhas
O OracleRunner existente já oferece run_visual_dom, que verifica se o elemento está visível e contém texto, e run_business_state, que extrai valor via JS e compara com o esperado. [caixa-my.s...epoint.com]

4.3. Validação para fill
Pythondef _validate_fill(self, step):    selector = self._primary_selector(step)    expected = step.value or ""    try:        actual = self.page.locator(selector).first.input_value(timeout=3000)    except Exception as exc:        return PostconditionResult(            passed=False,            failures=["cannot_read_input_value"],            message=str(exc),        )    expected_norm = self._normalize_value(expected)    actual_norm = self._normalize_value(actual)    matched = (        expected_norm == actual_norm        or expected_norm in actual_norm        or actual_norm in expected_norm    )    return PostconditionResult(        passed=matched,        checks={            "input_value_matches": matched,            "actual_value_present": bool(actual),        },        failures=[] if matched else ["value_mismatch"],        message="" if matched else f"Esperado {expected}, obtido {actual}",    )Mostrar mais linhas
Isso é especialmente importante para campos com máscara, como CPF e currencymask; o projeto já identificou que press_sequentially pode ser necessário para campos mascarados em Angular Material. [caixa-my.s...epoint.com]

4.4. Validação para select_option
Pythondef _validate_select_option(self, step):    selector = self._primary_selector(step)    expected = step.value or ""    try:        selected = self.page.locator(selector).first.evaluate("""            el => {                const opt = el.options[el.selectedIndex];                return {                    value: el.value,                    text: opt ? opt.textContent.trim() : ""                };            }        """)    except Exception as exc:        return PostconditionResult(            passed=False,            failures=["cannot_read_selected_option"],            message=str(exc),        )    matched = (        selected["value"] == expected        or selected["text"] == expected    )    return PostconditionResult(        passed=matched,        checks={"selected_option_matches": matched},        failures=[] if matched else ["selected_option_mismatch"],        message="" if matched else f"Esperado {expected}, selecionado {selected}",    )Mostrar mais linhas
Essa validação endereça diretamente os bugs críticos de <select> tratados como <input> e a necessidade de garantir que select_option realmente selecionou UF/Edifício/Data corretamente. [caixa-my.s...epoint.com]

4.5. Validação para click
Pythondef _validate_click(self, step, next_step=None):    causes_navigation = False    if step.context:        causes_navigation = step.context.get("causes_navigation", False)    # 1. Se houver oracle explícito no step, usar oracle.    explicit_oracles = self._extract_oracles_from_step(step)    if explicit_oracles:        results = self.oracle.run_all(explicit_oracles)        passed = all(r.status == "passed" for r in results)        return PostconditionResult(            passed=passed,            checks={"explicit_oracles_passed": passed},            oracle_results=results,            failures=[] if passed else ["explicit_oracle_failed"],            message="Oracles explícitos executados",        )    # 2. Se há próximo step, verificar se próximo elemento ficou disponível.    if next_step and next_step.target and next_step.target.candidates:        next_selector = next_step.target.candidates[0].selector        try:            self.page.wait_for_selector(                next_selector,                state="visible",                timeout=12000,            )            return PostconditionResult(                passed=True,                checks={"next_step_visible": True},                message=f"Próximo step visível: {next_selector}",            )        except Exception:            return PostconditionResult(                passed=False,                checks={"next_step_visible": False},                failures=["next_step_not_visible"],                message=f"Próximo step não apareceu: {next_selector}",            )    # 3. Fallback: click sem oracle específico.    return PostconditionResult(        passed=True,        checks={"click_no_exception": True},        message="Click executou sem oracle específico",    )Mostrar mais linhas
A recomendação é que, com o tempo, cada step relevante tenha oracle explícito ou pelo menos uma consequência esperada, porque usar apenas “click sem exception” ainda permite falsos positivos. O próprio plano do TestForge já prioriza oráculo pós-ação para evitar falso healing. [caixa-my.s...epoint.com]

5. Integração final dentro do _heal_failed_step
A integração completa fica assim:
Pythondef _heal_failed_step(    self,    step,    step_num: int,    original_error: str,    failure_phase: str,    result,):    original_selector = self._primary_selector(step)    payload = self._build_healing_payload(        step=step,        step_num=step_num,        original_error=original_error,        failure_phase=failure_phase,    )    if not payload.is_sufficient:        result.status = "failed"        result.healing = {            "attempted": False,            "reason": "insufficient_evidence",        }        return result    curator = self._make_curator()    step_data = {        "selector": original_selector or "",        "action": step.action,        "value": step.value or "",        "base_url": self.base_url,    }    outcome = curator.cure(        step_data=step_data,        error_message=original_error,        evidence=payload,    )    result.healing = self._map_curation_outcome(        outcome=outcome,        original_selector=original_selector,        failure_phase=failure_phase,        original_error=original_error,    )    proposal_ok, proposal_failures = self._validate_curator_proposal(        outcome=outcome,        step=step,        original_selector=original_selector,    )    if not proposal_ok:        result.status = "healing_rejected"        result.healing["validated"] = False        result.healing["rejection_reason"] = proposal_failures        result.error_message = (            "Proposta do curador rejeitada: "            + ", ".join(proposal_failures)        )        return result    if outcome.status != "PASSED_STEP":        result.status = "failed"        result.healing["validated"] = False        result.healing["rejection_reason"] = [            "curator_did_not_pass_step",            outcome.status,        ]        return result    oracle_ok = self._validate_healing_with_oracle(        step=step,        step_num=step_num,        result=result,    )    if oracle_ok:        self._evaluate_healing_promotion(result)    return resultMostrar mais linhas
Esse método garante a sequência correta:
Plain Textevidência suficiente↓curador tenta↓proposta é validada↓execução técnica passou↓oracle/pós-condição confirmou↓healing_validatedMostrar mais linhas

6. Como garantir por contrato que o Oracle sempre valide o healing
Eu sugiro três travas.
6.1. Trava 1 — Status oficial só muda no Oracle
Nunca faça isso:
Pythonif outcome.status == "PASSED_STEP":    result.status = "healed_validated"Mostrar mais linhas
Faça sempre:
Pythonif outcome.status == "PASSED_STEP":    oracle_ok = self._validate_healing_with_oracle(...)    if oracle_ok:        result.status = "healed_validated"    else:        result.status = "healing_rejected"Mostrar mais linhas
Essa trava impede que o status do curador vire automaticamente status de sucesso do teste. [caixa-my.s...epoint.com]

6.2. Trava 2 — Métrica ORACLE_VALIDATED só após pós-condição passar
Registre:
Pythonself.metrics.record_step(StepOutcome.HEALING_APPLIED, ...)Mostrar mais linhas
assim que o curador executar a proposta.
Mas registre:
Pythonself.metrics.record_step(StepOutcome.ORACLE_VALIDATED, ...)Mostrar mais linhas
somente depois de:
Pythonpost.passed is TrueMostrar mais linhas
O projeto já separa HEALING_APPLIED de ORACLE_VALIDATED em StepOutcome, então o incremental deve usar essa separação corretamente. [caixa-my.s...epoint.com]

6.3. Trava 3 — PromotionGate só depois do Oracle
Só chame:
Pythonself._evaluate_healing_promotion(result)Mostrar mais linhas
depois de:
Pythonresult.status == "healed_validated"Mostrar mais linhas
O PromotionGate já bloqueia promoção por evidência incompleta, oracle ausente/falho/conflitante e uniqueness baixa. Logo, chamar o gate antes do oracle enfraquece a governança. [caixa-my.s...epoint.com]

7. Critérios de aceite
Eu registraria estes critérios para essa implementação:
Plain TextCA-01 — _make_curator cria CuradorAutomatico com SmartStepRunner usando a page atual.CA-02 — _make_curator permite injeção de catalog/step_runner para testes.CA-03 — Proposta sem locator, sem estratégia, com baixa confiança ou genérica é rejeitada.CA-04 — outcome.status == PASSED_STEP não marca automaticamente healed_validated.CA-05 — Oracle/pós-condição é obrigatório para marcar healed_validated.CA-06 — Healing aplicado mas não validado vira healing_rejected.CA-07 — PromotionGate só roda depois de oracle aprovado.CA-08 — Métricas separam HEALING_APPLIED de ORACLE_VALIDATED.Mostrar mais linhas

8. Minha recomendação prática
A ordem de implementação deve ser:
Plain Text1. implementar _make_curator2. implementar _validate_curator_proposal3. implementar _validate_healing_with_oracle4. plugar tudo no _heal_failed_step5. registrar métricas separadas6. criar teste onde Curador retorna PASSED_STEP mas Oracle falhaMostrar mais linhas
Esse último teste é essencial. Ele prova que o TestForge não está mais confundindo ação executada com healing correto.
FontesForneça seus comentários sobre o BizChatYou said: Como testar o método _make_curator? Como simular falha do Oracle em um teste? Como garantir que o Oracle valide apenas healing verdadeiro?Copilot said: CopilotProcessamento concluído em 1 etapaAndre, eu testaria isso criando três camadas de garantia:

Teste unitário do_make_curator: garante que ele cria um CuradorAutomatico com step_runner funcional e injetável.
Teste de falha do Oracle: simula um healing que executa tecnicamente, mas não gera o resultado esperado.
Teste de “healing verdadeiro”: só marca healed_validated quando o Oracle/pós-condição confirma o efeito esperado.

A regra central deve ser:
Plain TextCuradorAutomatico retornou PASSED_STEP    significa: a proposta executou sem exception.Oracle/Postcondition passou    significa: o healing resolveu o problema real.Logo:    PASSED_STEP sem Oracle aprovado = healing_rejected    PASSED_STEP com Oracle aprovado = healed_validatedMostrar mais linhas
Essa separação é importante porque o projeto já possui CuradorAutomatico, SmartStepRunner, OracleRunner, PromotionGate e MetricsRepository, mas o PASSED_STEP do curador representa sucesso operacional da tentativa, não necessariamente sucesso semântico do fluxo. [caixa-my.s...epoint.com]

1. Como testar o método _make_curator
1.1. O que o teste deve garantir
O _make_curator deve garantir três coisas:
Plain Text1. Retorna uma instância de CuradorAutomatico.2. O CuradorAutomatico possui um step_runner funcional.3. Permite injetar step_runner fake e HealingCatalog fake/temporário para testes.Mostrar mais linhas
A versão recomendada do método é:
Pythonfrom testforge.healing import CuradorAutomatico, HealingCatalogfrom testforge.runner.fallback_runner import SmartStepRunnerdef _make_curator(self, catalog=None, step_runner=None) -> CuradorAutomatico:    if step_runner is None:        smart_runner = SmartStepRunner(self.page)        def step_runner(step_data: dict):            strategy = step_data.get("strategy", "")            return smart_runner.execute(step_data, strategy)    return CuradorAutomatico(        catalog=catalog or HealingCatalog(),        step_runner=step_runner,    )Mostrar mais linhas
Essa assinatura facilita teste porque você não precisa abrir browser real só para validar a factory. O CuradorAutomatico já aceita catalog e step_runner opcionais, então essa injeção é compatível com a estrutura atual do projeto. [caixa-my.s...epoint.com]

1.2. Teste unitário simples do _make_curator
Exemplo com um IncrementalRunner fake:
Pythonimport pytestfrom testforge.healing import CuradorAutomaticoclass FakeIncrementalRunner:    def __init__(self):        self.page = None    def _make_curator(self, catalog=None, step_runner=None):        from testforge.healing import CuradorAutomatico, HealingCatalog        if step_runner is None:            def step_runner(step_data: dict):                return True        return CuradorAutomatico(            catalog=catalog or HealingCatalog(),            step_runner=step_runner,        )def test_make_curator_returns_curador_automatico():    runner = FakeIncrementalRunner()    curator = runner._make_curator()    assert isinstance(curator, CuradorAutomatico)Mostrar mais linhas
Esse teste só confirma a factory. Ele é útil, mas ainda é fraco. O próximo teste valida que o step_runner realmente é usado.

1.3. Teste garantindo que o step_runner injetado é chamado
Pythonfrom testforge.healing import EvidencePayload, ProgressResultdef test_make_curator_uses_injected_step_runner():    runner = FakeIncrementalRunner()    called = {        "value": False,        "step_data": None,    }    def fake_step_runner(step_data: dict):        called["value"] = True        called["step_data"] = step_data        return True    curator = runner._make_curator(step_runner=fake_step_runner)    payload = EvidencePayload(        step_context={            "action": "click",            "selector": "#btnAntigo",            "text": "Pesquisar",            "framework": "generic",        },        dom_snapshot="<html><body><button>Pesquisar</button></body></html>" * 5,    )    payload.validate()    outcome = curator.cure(        step_data={            "selector": "#btnAntigo",            "action": "click",            "value": "",        },        error_message="element not found: #btnAntigo",        evidence=payload,    )    assert outcome.status == ProgressResult.PASSED_STEP    assert called["value"] is True    assert called["step_data"] is not NoneMostrar mais linhas
Esse teste comprova que o CuradorAutomatico recebeu o step_runner e conseguiu usá-lo durante o ciclo de cura. O CuradorAutomatico executa a proposta por meio do step_runner configurado e retorna PASSED_STEP quando a execução técnica passa. [caixa-my.s...epoint.com]

2. Como simular falha do Oracle em um teste
A melhor forma é criar uma situação em que:
Plain Text1. O curador aplica uma proposta.2. A ação executa sem exception.3. O resultado esperado NÃO aparece.4. O Oracle falha.5. O status final deve ser healing_rejected.Mostrar mais linhas
Isso testa exatamente o cenário mais perigoso: falso healing.

2.1. Página HTML para simular falso healing
Neste exemplo, o botão curado existe e recebe click, mas não escreve o texto esperado.
Pythondef test_oracle_failure_rejects_healing(page):    page.set_content("""        <html>          <body>            <button id="btnNovo">Pesquisar</button>            <div id="resultado" style="display:block">Nada aconteceu</div>            <script>              document.getElementById("btnNovo").addEventListener("click", () => {                document.getElementById("resultado").textContent = "Resultado errado";              });            </script>          </body>        </html>    """)    from testforge.healing import CuradorAutomatico, EvidencePayload, ProgressResult    from testforge.runner.fallback_runner import SmartStepRunner    from testforge.oracle import OracleRunner    smart = SmartStepRunner(page)    def step_runner(step_data):        strategy = step_data.get("strategy", "")        return smart.execute(step_data, strategy)    curator = CuradorAutomatico(step_runner=step_runner)    payload = EvidencePayload(        step_context={            "action": "click",            "selector": "#btnAntigo",            "text": "Pesquisar",            "framework": "generic",        },        dom_snapshot=page.content(),    )    payload.validate()    outcome = curator.cure(        step_data={            "selector": "#btnAntigo",            "action": "click",            "value": "",        },        error_message="element not found: #btnAntigo",        evidence=payload,    )    assert outcome.status == ProgressResult.PASSED_STEP    oracle = OracleRunner(page)    oracle_result = oracle.run_visual_dom(        "#resultado",        "CPF consultado",    )    assert oracle_result.status == "failed"Mostrar mais linhas
Esse teste prova a diferença entre:
Plain TextCurador executou proposta:    PASSED_STEPOracle validou efeito:    failedMostrar mais linhas
Logo, no IncrementalRunner, esse caso deve virar:
Plain Texthealing_rejectedMostrar mais linhas
e nunca:
Plain Texthealed_validatedMostrar mais linhas
O OracleRunner atual possui run_visual_dom, que verifica se o elemento existe, está visível e contém o texto esperado; por isso ele é adequado para validar se o efeito pós-ação realmente ocorreu. [caixa-my.s...epoint.com]

3. Como testar que Oracle falho gera healing_rejected
Agora precisamos testar o comportamento do _heal_failed_step, não apenas do CuradorAutomatico.
A ideia é usar um PostconditionValidator fake que retorna falha.

3.1. Fakes necessários
Pythonfrom dataclasses import dataclass, field@dataclassclass FakePostconditionResult:    passed: bool    message: str = ""    failures: list[str] = field(default_factory=list)    oracle_results: list = field(default_factory=list)class FakePostconditionValidator:    def __init__(self, passed: bool, message: str = "", failures=None):        self.passed = passed        self.message = message        self.failures = failures or []    def validate(self, step, page, next_step=None):        return FakePostconditionResult(            passed=self.passed,            message=self.message,            failures=self.failures,            oracle_results=[],        )Mostrar mais linhas

3.2. Teste do _heal_failed_step rejeitando falso healing
Pythondef test_heal_failed_step_rejects_when_oracle_fails(page):    """    Cenário:    - Curador consegue executar proposta.    - Pós-condição/Oracle falha.    - Resultado final precisa ser healing_rejected.    """    page.set_content("""        <html>          <body>            <button>Pesquisar</button>            <div id="resultado">Resultado errado</div>          </body>        </html>    """)    runner = make_incremental_runner_for_test(page)    runner.postcondition_validator = FakePostconditionValidator(        passed=False,        message="Texto esperado não apareceu",        failures=["oracle_failed"],    )    step = make_fake_step(        action="click",        selector="#btnAntigo",        text="Pesquisar",        value="",    )    result = make_fake_step_result(        step_num=1,        action="click",        original_locator="#btnAntigo",    )    healed = runner._heal_failed_step(        step=step,        step_num=1,        original_error="element not found: #btnAntigo",        failure_phase="execution",        result=result,    )    assert healed.status == "healing_rejected"    assert healed.healing["attempted"] is True    assert healed.healing["validated"] is False    assert healed.healing["oracle_passed"] is False    assert "postcondition_failed" in healed.healing["rejection_reason"]    assert "oracle_failed" in healed.healing["rejection_reason"]Mostrar mais linhas
Esse teste é obrigatório. Ele garante que o IncrementalRunner não transforma PASSED_STEP em healed_validated sem validação semântica. [caixa-my.s...epoint.com]

4. Como garantir que o Oracle valide apenas healing verdadeiro
Você garante isso com três contratos de código e três testes obrigatórios.

4.1. Contrato 1 — PASSED_STEP não é sucesso final
Nunca faça:
Pythonif outcome.status == ProgressResult.PASSED_STEP:    result.status = "healed_validated"Mostrar mais linhas
Faça:
Pythonif outcome.status == ProgressResult.PASSED_STEP:    oracle_ok = self._validate_healing_with_oracle(        step=step,        step_num=step_num,        result=result,    )    if oracle_ok:        result.status = "healed_validated"    else:        result.status = "healing_rejected"Mostrar mais linhas
Esse contrato separa execução técnica de validação semântica. O CuradorAutomatico executa a proposta via step_runner; o Oracle/pós-condição valida se o efeito esperado aconteceu. [caixa-my.s...epoint.com]

4.2. Contrato 2 — Métrica ORACLE_VALIDATED só depois do Oracle passar
Use esta ordem:
Pythonself.metrics.record_step(StepOutcome.HEALING_APPLIED, ...)Mostrar mais linhas
quando o curador retorna PASSED_STEP.
E só use:
Pythonself.metrics.record_step(StepOutcome.ORACLE_VALIDATED, ...)Mostrar mais linhas
quando:
Pythonpostcondition.passed is TrueMostrar mais linhas
O projeto já possui StepOutcome.HEALING_APPLIED e StepOutcome.ORACLE_VALIDATED, justamente para separar healing executado de healing validado. [caixa-my.s...epoint.com]

4.3. Contrato 3 — PromotionGate só roda depois de healed_validated
Nunca promova healing antes do Oracle.
Pythonif result.status == "healed_validated":    self._evaluate_healing_promotion(result)Mostrar mais linhas
O PromotionGate já bloqueia casos com evidência incompleta, oracle ausente, oracle falho/conflitante ou uniqueness baixa; mas ele deve ser chamado somente depois que o Oracle confirmou a cura. [caixa-my.s...epoint.com]

5. Testes obrigatórios para garantir healing verdadeiro
Teste A — Curador passa, Oracle passa
Resultado esperado:
Plain Texthealed_validatedMostrar mais linhas
Pythondef test_healing_validated_only_when_oracle_passes(page):    page.set_content("""        <html>          <body>            <button>Pesquisar</button>            <div id="resultado">CPF consultado</div>          </body>        </html>    """)    runner = make_incremental_runner_for_test(page)    runner.postcondition_validator = FakePostconditionValidator(        passed=True,        message="Oracle passou",        failures=[],    )    step = make_fake_step(        action="click",        selector="#btnAntigo",        text="Pesquisar",    )    result = make_fake_step_result(        step_num=1,        action="click",        original_locator="#btnAntigo",    )    healed = runner._heal_failed_step(        step=step,        step_num=1,        original_error="element not found",        failure_phase="execution",        result=result,    )    assert healed.status == "healed_validated"    assert healed.healing["validated"] is True    assert healed.healing["oracle_passed"] is TrueMostrar mais linhas

Teste B — Curador passa, Oracle falha
Resultado esperado:
Plain Texthealing_rejectedMostrar mais linhas
Pythondef test_healing_rejected_when_oracle_fails(page):    page.set_content("""        <html>          <body>            <button>Pesquisar</button>            <div id="resultado">Resultado errado</div>          </body>        </html>    """)    runner = make_incremental_runner_for_test(page)    runner.postcondition_validator = FakePostconditionValidator(        passed=False,        message="Oracle falhou",        failures=["oracle_failed"],    )    step = make_fake_step(        action="click",        selector="#btnAntigo",        text="Pesquisar",    )    result = make_fake_step_result(        step_num=1,        action="click",        original_locator="#btnAntigo",    )    healed = runner._heal_failed_step(        step=step,        step_num=1,        original_error="element not found",        failure_phase="execution",        result=result,    )    assert healed.status == "healing_rejected"    assert healed.healing["validated"] is False    assert healed.healing["oracle_passed"] is FalseMostrar mais linhas

Teste C — Oracle passa, mas proposta do curador é genérica demais
Resultado esperado:
Plain Texthealing_rejectedMostrar mais linhas
Esse teste evita aceitar locators como body, button, text=Selecione.
Pythondef test_generic_locator_proposal_is_rejected_even_before_oracle(page):    runner = make_incremental_runner_for_test(page)    outcome = make_fake_curation_outcome(        status="PASSED_STEP",        layer_used="L3",        strategy="has_text_fallback",        new_locator="button",        confidence=0.90,        family="FAM-01",        taxonomy_id="SEL-004",    )    step = make_fake_step(        action="click",        selector="#btnAntigo",        text="Pesquisar",    )    ok, failures = runner._validate_curator_proposal(        outcome=outcome,        step=step,        original_selector="#btnAntigo",    )    assert ok is False    assert "generic_or_dangerous_locator" in failuresMostrar mais linhas
Esse teste garante que o Oracle não seja usado para “validar” uma proposta perigosa que nem deveria ser aceita como candidata. O projeto já identificou risco de propostas genéricas como text=Selecione ou locators amplos, então esse bloqueio deve existir antes da promoção do healing. [caixa-my.s...epoint.com]

6. Helpers de teste sugeridos
Para deixar os testes limpos, crie helpers em:
Plain Texttests/helpers/incremental_fakes.pyMostrar mais linhas
Exemplo:
Pythonfrom dataclasses import dataclass, field@dataclassclass FakeTarget:    candidates: list    text: str = ""    label: str = ""    accessible_name: str = ""@dataclassclass FakeCandidate:    selector: str    score: float = 1.0@dataclassclass FakeStep:    action: str    value: str = ""    target: FakeTarget = None    context: dict = field(default_factory=dict)    depends_on: str = ""    blocking: bool = False    skip_reason: str = ""def make_fake_step(action="click", selector="#btn", text="", value=""):    return FakeStep(        action=action,        value=value,        target=FakeTarget(            candidates=[FakeCandidate(selector=selector)],            text=text,        ),        context={},    )@dataclassclass FakeStepResult:    step_num: int    action: str    status: str = "failed"    original_locator: str = ""    selected_locator: str = ""    healing: dict = field(default_factory=dict)    error_message: str = ""    postcondition: object = None    evidence_before: dict = field(default_factory=dict)    evidence_after: dict = field(default_factory=dict)def make_fake_step_result(step_num=1, action="click", original_locator="#btn"):    return FakeStepResult(        step_num=step_num,        action=action,        original_locator=original_locator,        selected_locator=original_locator,    )Mostrar mais linhas

7. Checklist final de garantia
Para garantir que o Oracle valide apenas healing verdadeiro, eu colocaria estes critérios no teste e no código:
Plain Text[ ] _make_curator retorna CuradorAutomatico.[ ] _make_curator aceita step_runner fake.[ ] Curador PASSED_STEP não define healed_validated sozinho.[ ] Pós-condição/Oracle falho gera healing_rejected.[ ] Pós-condição/Oracle aprovado gera healed_validated.[ ] ORACLE_VALIDATED só é registrado quando postcondition.passed == True.[ ] PromotionGate só roda quando status == healed_validated.[ ] Proposta genérica é rejeitada antes do Oracle.[ ] Relatório registra original_locator, proposed_locator, strategy, layer, family, taxonomy_id e oracle_passed.Mostrar mais linhas

8. Recomendação prática
Eu faria estes três testes primeiro, nesta ordem:
Plain Text1. test_make_curator_uses_injected_step_runner2. test_healing_rejected_when_oracle_fails3. test_healing_validated_only_when_oracle_passesMostrar mais linhas
Se esses três passarem, vocês terão protegido o ponto mais crítico do run-incremental: não confundir healing executado com healing verdadeiro.
FontesForneça seus comentários sobre o BizChatYou said: Como implementar o _heal_failed_step? Como simular um passo com erro de execução? Como testar múltiplos passos em sequência?Copilot said: CopilotProcessamento concluído em 1 etapaAndre, eu implementaria o _heal_failed_step como o ponto único de recuperação do IncrementalRunner. Ele deve receber um step que falhou, construir evidência, chamar o CuradorAutomatico, validar a proposta, executar/verificar o resultado via pós-condição/Oracle, registrar métricas e devolver um IncrementalStepResult consistente. O projeto já tem as peças principais para isso: CuradorAutomatico, ProgressResult, EvidencePayload, SmartStepRunner, MetricsRepository, StepOutcome, OracleRunner, PromotionGate e RunReport; o que falta é orquestrar essas peças fora do cmd_run, em um runner incremental testável. [caixa-my.s...epoint.com]

1. Implementação recomendada do _heal_failed_step
1.1. Contrato do método
O método deve seguir este contrato:
Plain TextEntrada:    step que falhou    número do step    erro original    fase da falha: precondition | execution | postcondition    resultado incremental em construçãoSaída:    result atualizado com:        status        healing        postcondition        error_message        métricas registradasMostrar mais linhas
Status possíveis:
Plain Texthealed_validated    Curador aplicou proposta e Oracle/pós-condição confirmou.healing_rejected    Curador aplicou proposta, mas Oracle/pós-condição rejeitou.failed    Curador não conseguiu resolver, evidência foi insuficiente ou proposta inválida.Mostrar mais linhas
A regra principal deve ser:
Plain TextCuradorAutomatico retornou PASSED_STEP    significa que a proposta executou sem exception.Postcondition/Oracle passou    significa que o healing foi verdadeiro.Logo:    PASSED_STEP sem Oracle aprovado = healing_rejected.Mostrar mais linhas

1.2. Código-base do _heal_failed_step
Pythonfrom testforge.healing import ProgressResultfrom testforge.metrics import StepOutcomedef _heal_failed_step(    self,    step,    step_num: int,    original_error: str,    failure_phase: str,    result,):    """    Tenta curar um step falho.    Fluxo:    1. Registra falha detectada.    2. Monta EvidencePayload.    3. Chama CuradorAutomatico.    4. Valida proposta retornada.    5. Se proposta executou, valida pós-condição/Oracle.    6. Registra métricas.    7. Retorna result atualizado.    """    original_selector = self._primary_selector(step)    # 1. Métrica: falha detectada    self.metrics.record_step(        StepOutcome.FAILURE_DETECTED,        step_num=step_num,        action=step.action,        selector=original_selector or "",    )    # 2. Montar evidência    payload = self._build_healing_payload(        step=step,        step_num=step_num,        original_error=original_error,        failure_phase=failure_phase,    )    if not payload.is_sufficient:        result.status = "failed"        result.error_message = (            "Healing não tentado: evidência insuficiente — "            f"{payload.insufficiency_reason}"        )        result.healing = {            "attempted": False,            "reason": "insufficient_evidence",            "failure_phase": failure_phase,            "original_error": original_error,        }        return result    # 3. Criar curador    curator = self._make_curator()    step_data = {        "selector": original_selector or "",        "action": step.action,        "value": step.value or "",        "base_url": self.base_url,    }    # 4. Métrica: healing tentado    self.metrics.record_step(        StepOutcome.HEALING_ATTEMPTED,        step_num=step_num,        action=step.action,        selector=original_selector or "",    )    # 5. Chamar CuradorAutomatico    outcome = curator.cure(        step_data=step_data,        error_message=original_error,        evidence=payload,    )    # 6. Mapear retorno para relatório    result.healing = self._map_curation_outcome(        outcome=outcome,        original_selector=original_selector,        failure_phase=failure_phase,        original_error=original_error,    )    # 7. Validar proposta estruturalmente    proposal_ok, proposal_failures = self._validate_curator_proposal(        outcome=outcome,        step=step,        original_selector=original_selector,    )    if not proposal_ok:        self.metrics.record_step(            StepOutcome.HEALING_REJECTED,            step_num=step_num,            action=step.action,            family_code=result.healing.get("family", ""),            healing_layer=result.healing.get("layer", ""),            selector=original_selector or "",        )        result.status = "healing_rejected"        result.error_message = (            "Proposta do curador rejeitada: "            + ", ".join(proposal_failures)        )        result.healing["validated"] = False        result.healing["oracle_passed"] = False        result.healing["rejection_reason"] = proposal_failures        return result    # 8. Curador não conseguiu aplicar    if outcome.status != ProgressResult.PASSED_STEP:        self.metrics.record_step(            StepOutcome.HEALING_REJECTED,            step_num=step_num,            action=step.action,            family_code=outcome.family or "",            healing_layer=outcome.layer_used or "",            selector=original_selector or "",        )        result.status = "failed"        result.error_message = (            f"Healing não resolvido: {outcome.status}. "            f"{outcome.error_message or ''}"        )        result.healing["validated"] = False        result.healing["oracle_passed"] = False        result.healing["rejection_reason"] = [            "curator_did_not_pass_step",            outcome.status,        ]        return result    # 9. Curador aplicou tecnicamente    proposed_selector = result.healing.get("proposed_locator", original_selector or "")    self.metrics.record_step(        StepOutcome.HEALING_APPLIED,        step_num=step_num,        action=step.action,        family_code=outcome.family or "",        healing_layer=outcome.layer_used or "",        selector=proposed_selector,    )    # 10. Validação semântica obrigatória via pós-condição/Oracle    oracle_ok = self._validate_healing_with_oracle(        step=step,        step_num=step_num,        result=result,    )    if oracle_ok:        self.metrics.record_step(            StepOutcome.ORACLE_VALIDATED,            step_num=step_num,            action=step.action,            family_code=outcome.family or "",            healing_layer=outcome.layer_used or "",            selector=proposed_selector,        )        result.status = "healed_validated"        result.healing["validated"] = True        result.healing["oracle_passed"] = True        result.healing["rejection_reason"] = []        self._evaluate_healing_promotion(result)        return result    # 11. Curador executou, mas Oracle rejeitou    self.metrics.record_step(        StepOutcome.HEALING_REJECTED,        step_num=step_num,        action=step.action,        family_code=outcome.family or "",        healing_layer=outcome.layer_used or "",        selector=proposed_selector,    )    result.status = "healing_rejected"    result.healing["validated"] = False    result.healing["oracle_passed"] = False    if "rejection_reason" not in result.healing:        result.healing["rejection_reason"] = []    if "postcondition_failed" not in result.healing["rejection_reason"]:        result.healing["rejection_reason"].insert(0, "postcondition_failed")    return resultMostrar mais linhas
Essa implementação garante a separação entre healing aplicado e healing validado, usando os estados já existentes em StepOutcome: FAILURE_DETECTED, HEALING_ATTEMPTED, HEALING_APPLIED, ORACLE_VALIDATED e HEALING_REJECTED. [caixa-my.s...epoint.com]

2. Métodos auxiliares necessários
2.1. _make_curator
Pythonfrom testforge.healing import CuradorAutomatico, HealingCatalogfrom testforge.runner.fallback_runner import SmartStepRunnerdef _make_curator(self, catalog=None, step_runner=None) -> CuradorAutomatico:    """    Cria CuradorAutomatico ligado à página atual.    Permite injetar catalog/step_runner nos testes.    """    if step_runner is None:        smart_runner = SmartStepRunner(self.page)        def step_runner(step_data: dict):            strategy = step_data.get("strategy", "")            return smart_runner.execute(step_data, strategy)    return CuradorAutomatico(        catalog=catalog or HealingCatalog(),        step_runner=step_runner,    )Mostrar mais linhas
O CuradorAutomatico já aceita catalog e step_runner; no fluxo atual do projeto, o cmd_run usa SmartStepRunner(page) como executor de propostas curadas. [caixa-my.s...epoint.com]

2.2. _build_healing_payload
Pythondef _build_healing_payload(    self,    step,    step_num: int,    original_error: str,    failure_phase: str,):    selector = self._primary_selector(step)    text_value = ""    if step.target:        text_value = (            getattr(step.target, "text", "") or            getattr(step.target, "label", "") or            getattr(step.target, "accessible_name", "") or            ""        )    step_context = {        "action": step.action,        "selector": selector or "(empty — no selector available)",        "value": step.value or "",        "text": text_value,        "intention": self._describe_intention(step, step_num),        "url": self.page.url,        "framework": self.app_name or "generic",        "step_number": step_num,        "failure_phase": failure_phase,        "original_error": original_error,    }    return self.evidence_collector.build_llm_payload(        step_context=step_context,        include_screenshot=False,    )Mostrar mais linhas
O EvidenceCollector.build_llm_payload() já gera um EvidencePayload com DOM sanitizado, console, network e screenshot opcional; o EvidencePayload considera o DOM suficiente quando há pelo menos 100 caracteres. [caixa-my.s...epoint.com]

2.3. _map_curation_outcome
Pythondef _map_curation_outcome(    self,    outcome,    original_selector: str,    failure_phase: str,    original_error: str,):    healing = {        "attempted": True,        "status": outcome.status,        "layer": outcome.layer_used,        "family": outcome.family,        "taxonomy_id": outcome.taxonomy_id,        "failure_phase": failure_phase,        "original_error": original_error,        "original_locator": original_selector,        "validated": False,        "oracle_passed": False,        "rejection_reason": [],        "entry_id": outcome.entry_id,    }    if outcome.proposal:        healing.update({            "strategy": outcome.proposal.strategy,            "proposed_locator": outcome.proposal.new_locator,            "confidence": outcome.proposal.confidence,            "rationale": outcome.proposal.rationale,            "raw_response": outcome.proposal.raw_response or "",        })    if outcome.error_message:        healing["curator_error_message"] = outcome.error_message    return healingMostrar mais linhas

2.4. _validate_curator_proposal
Pythondef _validate_curator_proposal(self, outcome, step, original_selector: str):    failures = []    if outcome is None:        return False, ["missing_outcome"]    if not outcome.layer_used:        failures.append("missing_layer_used")    proposal = outcome.proposal    # L0 pode não ter proposal explícita se veio de catálogo.    if proposal:        if not proposal.new_locator:            failures.append("missing_new_locator")        if proposal.confidence < 0.5:            failures.append("low_confidence")        if not proposal.family:            failures.append("missing_family")        if not proposal.taxonomy_id:            failures.append("missing_taxonomy_id")        if not proposal.strategy:            failures.append("missing_strategy")        if self._is_dangerously_generic_locator(proposal.new_locator):            failures.append("generic_or_dangerous_locator")        if self._is_incompatible_action_strategy(step, proposal.strategy):            failures.append("incompatible_action_strategy")        if proposal.new_locator == original_selector and outcome.layer_used != "L0":            failures.append("same_locator_as_failed_original")    return len(failures) == 0, failuresMostrar mais linhas
Essa validação impede aceitar proposta vazia, genérica, incompatível ou igual ao locator original quebrado. Isso é importante porque o projeto já identificou riscos de locators genéricos e falsos healings. [caixa-my.s...epoint.com]

2.5. _validate_healing_with_oracle
Pythondef _validate_healing_with_oracle(self, step, step_num: int, result) -> bool:    """    Só retorna True se a pós-condição/Oracle confirmar que a cura funcionou.    """    post = self.postcondition_validator.validate(        step=step,        page=self.page,        next_step=self._next_executable_step(step_num),    )    result.postcondition = post    if post.passed:        result.status = "healed_validated"        result.healing["validated"] = True        result.healing["oracle_passed"] = True        result.healing["rejection_reason"] = []        return True    result.status = "healing_rejected"    result.healing["validated"] = False    result.healing["oracle_passed"] = False    result.healing["rejection_reason"] = [        "postcondition_failed",        *getattr(post, "failures", []),    ]    result.error_message = (        "Healing executou, mas Oracle/pós-condição falhou: "        f"{post.message}"    )    return FalseMostrar mais linhas
O OracleRunner já possui validações como visual_dom e business_state, e o PromotionGate já usa resultados de oracle para aprovar ou rejeitar promoções. [caixa-my.s...epoint.com]

3. Como simular um passo com erro de execução
Para testar _heal_failed_step, você precisa de um step que falhe durante a execução original.
Existem duas formas.

3.1. Simulação simples com selector inexistente
Você cria um step com selector quebrado:
Pythonstep = make_fake_step(    action="click",    selector="#btnAntigo",    text="Pesquisar",)Mostrar mais linhas
E uma página que só tem o botão correto:
Pythonpage.set_content("""    <html>      <body>        <button>Pesquisar</button>        <div id="resultado">CPF consultado</div>      </body>    </html>""")Mostrar mais linhas
Erro simulado:
Pythonoriginal_error = "element not found: #btnAntigo"Mostrar mais linhas
Esse erro é suficiente para o FailureClassifier classificar como falha de selector recuperável, permitindo o CuradorAutomatico tentar L2/L3. O projeto já classifica falhas de selector e usa agentes/MockLLMHealer para propor fallback textual. [caixa-my.s...epoint.com]

3.2. Simulação real executando e capturando exception
Você também pode realmente tentar executar o step original antes de chamar _heal_failed_step:
Pythontry:    page.click("#btnAntigo", timeout=1000)except Exception as exc:    original_error = str(exc)Mostrar mais linhas
Depois chama:
Pythonhealed = runner._heal_failed_step(    step=step,    step_num=1,    original_error=original_error,    failure_phase="execution",    result=result,)Mostrar mais linhas
Essa é a forma mais realista, porque usa a mensagem exata do Playwright.

4. Helpers de teste para simular steps
Crie um arquivo:
Plain Texttests/helpers/incremental_fakes.pyMostrar mais linhas
Com:
Pythonfrom dataclasses import dataclass, field@dataclassclass FakeCandidate:    selector: str    score: float = 1.0@dataclassclass FakeTarget:    candidates: list    text: str = ""    label: str = ""    accessible_name: str = ""@dataclassclass FakeStep:    action: str    value: str = ""    target: FakeTarget = None    context: dict = field(default_factory=dict)    depends_on: str = ""    blocking: bool = False    skip_reason: str = ""@dataclassclass FakeStepResult:    step_num: int    action: str    status: str = "failed"    original_locator: str = ""    selected_locator: str = ""    healing: dict = field(default_factory=dict)    error_message: str = ""    postcondition: object = None    evidence_before: dict = field(default_factory=dict)    evidence_after: dict = field(default_factory=dict)def make_fake_step(action="click", selector="#btn", text="", value="", context=None):    return FakeStep(        action=action,        value=value,        target=FakeTarget(            candidates=[FakeCandidate(selector=selector)],            text=text,        ),        context=context or {},    )def make_fake_step_result(step_num=1, action="click", original_locator="#btn"):    return FakeStepResult(        step_num=step_num,        action=action,        original_locator=original_locator,        selected_locator=original_locator,    )Mostrar mais linhas

5. Fake de pós-condição/Oracle
Para testar sem depender inicialmente do OracleRunner real:
Pythonfrom dataclasses import dataclass, field@dataclassclass FakePostconditionResult:    passed: bool    message: str = ""    failures: list[str] = field(default_factory=list)    oracle_results: list = field(default_factory=list)class FakePostconditionValidator:    def __init__(self, passed: bool, message: str = "", failures=None):        self._passed = passed        self._message = message        self._failures = failures or []    def validate(self, step, page, next_step=None):        return FakePostconditionResult(            passed=self._passed,            message=self._message,            failures=self._failures,            oracle_results=[],        )Mostrar mais linhas
Depois você cria dois cenários:
Plain Textpassed=True    healing deve virar healed_validated.passed=False    healing deve virar healing_rejected.Mostrar mais linhas

6. Como testar múltiplos passos em sequência
Aqui você deve testar o comportamento do runner, não só do _heal_failed_step.
O cenário mínimo:
Plain TextStep 1: click com selector quebrado, curado por texto.Step 2: assert do resultado.Step 3: click dependente, só executa se Step 1 passou.Mostrar mais linhas
6.1. Exemplo de página HTML
Pythonpage.set_content("""    <html>      <body>        <button id="btnNovo">Pesquisar</button>        <div id="resultado" style="display:none"></div>        <button id="proximo" style="display:none">Próximo</button>        <script>          document.getElementById("btnNovo").addEventListener("click", () => {            document.getElementById("resultado").style.display = "block";            document.getElementById("resultado").textContent = "CPF consultado";            document.getElementById("proximo").style.display = "inline-block";          });        </script>      </body>    </html>""")Mostrar mais linhas

6.2. Steps simulados
Pythonsteps = [    make_fake_step(        action="click",        selector="#btnAntigo",        text="Pesquisar",    ),    make_fake_step(        action="assert",        selector="#resultado",        text="CPF consultado",        value="CPF consultado",    ),    make_fake_step(        action="click",        selector="#proximo",        text="Próximo",    ),]Mostrar mais linhas

6.3. Teste de sequência com primeiro step curado
Pythondef test_incremental_runner_multiple_steps_first_healed_then_continue(page):    page.set_content("""        <html>          <body>            <button id="btnNovo">Pesquisar</button>            <div id="resultado" style="display:none"></div>            <button id="proximo" style="display:none">Próximo</button>            <script>              document.getElementById("btnNovo").addEventListener("click", () => {                document.getElementById("resultado").style.display = "block";                document.getElementById("resultado").textContent = "CPF consultado";                document.getElementById("proximo").style.display = "inline-block";              });            </script>          </body>        </html>    """)    runner = make_incremental_runner_for_test(page)    runner.steps = [        make_fake_step("click", "#btnAntigo", text="Pesquisar"),        make_fake_step("assert", "#resultado", text="CPF consultado", value="CPF consultado"),        make_fake_step("click", "#proximo", text="Próximo"),    ]    # Aqui use um PostconditionValidator real ou fake por step.    # Para o primeiro step, ele deve validar que #resultado ficou visível.    runner.postcondition_validator = RealOrTestPostconditionValidator(page)    results = []    for index, step in enumerate(runner.steps):        step_num = index + 1        result = make_fake_step_result(            step_num=step_num,            action=step.action,            original_locator=runner._primary_selector(step),        )        try:            runner.step_executor.execute(step, page, data_values={})            result.status = "passed"        except Exception as exc:            result = runner._heal_failed_step(                step=step,                step_num=step_num,                original_error=str(exc),                failure_phase="execution",                result=result,            )        results.append(result)        if result.status in ("failed", "healing_rejected"):            break    assert results[0].status == "healed_validated"    assert results[1].status in ("passed", "healed_validated")    assert len(results) >= 2Mostrar mais linhas

7. Teste de múltiplos passos com bloqueio por falha
Também é importante testar:
Plain TextStep 1 falha e não cura.Step 2 depende do Step 1.Step 2 deve ficar blocked, não failed.Mostrar mais linhas
7.1. Steps com dependência
Pythonstep1 = make_fake_step(    action="click",    selector="#botaoInexistente",    text="Pesquisar",)step1.blocking = Truestep2 = make_fake_step(    action="click",    selector="#proximo",    text="Próximo",)step2.depends_on = "step_0001"Mostrar mais linhas
7.2. Teste
Pythondef test_incremental_runner_blocks_dependent_steps_after_failed_blocking_step(page):    page.set_content("""        <html>          <body>            <button id="outro">Outro botão</button>            <button id="proximo">Próximo</button>          </body>        </html>    """)    runner = make_incremental_runner_for_test(page)    step1 = make_fake_step("click", "#botaoInexistente", text="Pesquisar")    step1.blocking = True    step2 = make_fake_step("click", "#proximo", text="Próximo")    step2.depends_on = "step_0001"    runner.steps = [step1, step2]    results = runner.run_steps_for_test(runner.steps)    assert results[0].status in ("failed", "healing_rejected")    assert results[1].status == "blocked"    assert "blocked_by_previous_failure" in results[1].error_messageMostrar mais linhas
Essa lógica já aparece parcialmente no cmd_run, que controla steps dependentes e marca blocked_by_previous_failure; o IncrementalRunner deve formalizar isso em teste. [caixa-my.s...epoint.com]

8. Teste de múltiplos passos com falso healing
Cenário:
Plain TextStep 1: curador clica em algo, mas resultado esperado não aparece.Oracle falha.Step 1 = healing_rejected.Step 2 depende do Step 1.Step 2 = blocked.Mostrar mais linhas
Pythondef test_false_healing_blocks_dependent_steps(page):    page.set_content("""        <html>          <body>            <button>Pesquisar</button>            <div id="resultado">Resultado errado</div>            <button id="proximo">Próximo</button>          </body>        </html>    """)    runner = make_incremental_runner_for_test(page)    runner.postcondition_validator = FakePostconditionValidator(        passed=False,        message="Resultado esperado não apareceu",        failures=["oracle_failed"],    )    step1 = make_fake_step("click", "#btnAntigo", text="Pesquisar")    step1.blocking = True    step2 = make_fake_step("click", "#proximo", text="Próximo")    step2.depends_on = "step_0001"    runner.steps = [step1, step2]    result1 = make_fake_step_result(1, "click", "#btnAntigo")    result1 = runner._heal_failed_step(        step=step1,        step_num=1,        original_error="element not found",        failure_phase="execution",        result=result1,    )    assert result1.status == "healing_rejected"    # Simula controle de dependência    runner.failed_step_indices.add(0)    result2 = runner._run_one_step(1, step2)    assert result2.status == "blocked"Mostrar mais linhas

9. O que validar no final da sequência
Depois de executar múltiplos steps, valide:
Plain Text1. Ordem dos steps foi preservada.2. Step curado validado permite continuar.3. Step com falso healing bloqueia dependentes se for blocking.4. Step failed sem healing bloqueia dependentes se for blocking.5. Métricas batem com os resultados.Mostrar mais linhas
Exemplo de assert de métricas:
Pythonsnapshot = runner.metrics.snapshotassert snapshot.falhas_detectadas == 1assert snapshot.healings_tentados == 1assert snapshot.aplicados == 1assert snapshot.validados == 1assert snapshot.rejeitados == 0Mostrar mais linhas
Para falso healing:
Pythonsnapshot = runner.metrics.snapshotassert snapshot.falhas_detectadas == 1assert snapshot.healings_tentados == 1assert snapshot.aplicados == 1assert snapshot.validados == 0assert snapshot.rejeitados == 1Mostrar mais linhas

10. Critérios de aceite
Eu registraria estes critérios para essa fatia:
Plain TextCA-01 — _heal_failed_step registra FAILURE_DETECTED quando recebe erro.CA-02 — _heal_failed_step registra HEALING_ATTEMPTED quando chama o CuradorAutomatico.CA-03 — Se CuradorAutomatico retorna PASSED_STEP, registra HEALING_APPLIED.CA-04 — Só registra ORACLE_VALIDATED quando pós-condição/Oracle passa.CA-05 — Curador PASSED_STEP + Oracle falho gera healing_rejected.CA-06 — Curador PASSED_STEP + Oracle aprovado gera healed_validated.CA-07 — Um step healed_validated permite sequência continuar.CA-08 — Um step failed/healing_rejected e blocking bloqueia dependentes.CA-09 — Métricas por step batem com o relatório final.Mostrar mais linhas

11. Recomendação prática

Eu implementaria e testaria nesta ordem:
Plain Text1. Helpers fake de step/result/postcondition.2. _heal_failed_step com métricas.3. Teste: step com erro de execução vira healed_validated.4. Teste: step com erro de execução + Oracle falho vira healing_rejected.5. Teste: sequência de 3 steps continua após healing validado.6. Teste: sequência bloqueia dependentes após falso healing.Mostrar mais linhas
O teste mais importante é este:
Plain TextCuradorAutomatico retorna PASSED_STEP,mas Oracle falha,logo status final deve ser healing_rejected.Mostrar mais linhas
Esse teste protege o TestForge contra o erro mais perigoso: achar que o fluxo foi curado só porque não ocorreu exception.
FontesForneça seus comentários sobre o BizChatYou said: Já temos muita coisa pra fazer até amanhã. Gere épicos, histórias, guia de implementações, testes que verificam que tudo que planejamos foi de fato executado. Verificar, validar, tudo tem que ter tarefa. Lembre-se: iremos passar para outra llm implementar então esse documento deve estar autocontido e conter tudo que discutimos hoje sobre o testforgeCopilot said: CopilotProcessamento concluído em 3 etapasPerfeito, Andre. Consolidei tudo em um documento autocontido para você passar diretamente para outra LLM implementar.
Arquivo gerado:
Baixar o plano autocontido do run-incremental
O documento contém:

Épicos, histórias, tarefas e critérios de aceite.
Guia de implementação do run-incremental.
Implementação planejada de _make_curator, _heal_failed_step, validação da proposta do curador e validação com Oracle.
Plano de métricas de healing.
Estratégia de evidências before/after.
Relatórios execution_report.json, healing_report.md e metrics.json.
Testes unitários, testes de integração e verificações manuais.
Cenários para healing verdadeiro, falso healing, select_option e dependências bloqueadas.
Prompt pronto para enviar para outra LLM.
Definição de pronto/checklist final.

Também deixei explícito que o escopo é apenas TestForge, sem MCP RTC/RQM/RDNG, sem MCP mestre e sem SpecKit, conforme as decisões anteriores do projeto. O plano usa como base a arquitetura e componentes atuais do TestForge: CLI, CuradorAutomatico, SmartStepRunner, EvidenceCollector, OracleRunner, PromotionGate, MetricsRepository, ActionabilityValidator e relatórios existentes.