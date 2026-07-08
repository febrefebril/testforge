# TestForge - run-incremental

Executor incremental que orquestra pre-condicao -> execucao -> pos-condicao -> evidencia -> healing -> oracle -> metricas -> relatorio por step.

## Arquitetura

```
IncrementalRunner
├── StepPreconditionValidator
├── StepExecutor
├── StepPostconditionValidator
├── EvidenceCollector
├── CuradorAutomatico (L0->L3)
├── SmartStepRunner
├── OracleRunner
├── PromotionGate
└── MetricsRepository
```

## Estados de step

- `passed` - passou sem healing
- `healed_validated` - healing aplicado + oracle aprovou
- `healing_rejected` - healing executou mas pos-condicao falhou
- `failed` - curador nao conseguiu (ou healing desativado)
- `blocked` - dependencia anterior falhou
- `skipped` - step ignorado por regra
- `shadow_healed` - em shadow-mode, proposta funcionaria

## Contrato Curador x Oracle

```
PASSED_STEP + oracle aprovado = healed_validated
PASSED_STEP + oracle falho    = healing_rejected
```

## CLI

```
testforge run-incremental <script> [--headless] [--verbose] [--data <json>]
                          [--browser chromium|chrome|edge]
                          [--no-stop-on-failure] [--no-healing] [--shadow]
```

## Saida

```
runs/<recording_id>/<timestamp>/
├── execution_report.json
├── healing_report.md
└── metrics.json
```

## Escopo

Este plano cobre **apenas o TestForge**. MCP RTC/RQM/RDNG, MCP mestre e SpecKit estao fora.