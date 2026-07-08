# Arquivos de uma Gravação

Toda gravação do TestForge produz um diretório com múltiplos arquivos. Este documento explica o que cada um significa e quando você deve se importar com ele.

---

## Visão geral

```
recordings/<sistema>/<suite>/<caso-de-teste>/
├── recording_metadata.json       ← Quem, quando, status
├── raw_events.jsonl              ← TUDO que aconteceu (source of truth)
├── steps.jsonl                   ← Asserts manuais (Shift+A)
├── value_mutations.jsonl         ← Valores de campos ao digitar
├── field_snapshots.jsonl         ← Estado de todos os campos visíveis
├── final_state_snapshot.json     ← DOM completo ao final
├── keystroke_buffer.jsonl        ← Teclas digitadas (debug)
├── network_log.json              ← Requisições de rede
├── rrweb_events.jsonl            ← Gravação visual (rrweb)
├── suggested_assertions.jsonl    ← Asserts sugeridos automaticamente
├── recording_config.json         ← Configuração da gravação
├── submission_report.json        ← Relatório de publicação (Git)
├── sensitive_alerts.json         ← Alertas de dados sensíveis (PII)
├── completeness/                 ← Relatório de campos pendentes
│   └── intent_completeness_report.md
├── readiness/                    ← Gate de prontidão
│   └── readiness_report.md
├── diagnostic/                   ← Telemetria e qualidade de captura
│   ├── session.json
│   ├── capture_quality_report.md
│   └── scenario.feature
├── dom_snapshots/                 ← Snapshots HTML por evento
├── ax_snapshots/                  ← Árvore de acessibilidade por evento
└── _pilot_runs/                   ← Resultados de execuções de validação
```

---

## Arquivos essenciais (você vai usar sempre)

### `recording_metadata.json`
**O que é:** Metadados da gravação — sistema, suite, caso de teste, URL, status, fingerprint do recorder.
**Quando ler:** Para saber o contexto da gravação, versão do recorder que gerou, status atual.
**Exemplo:**
```json
{
  "recording_id": "CT-001",
  "system": "MYSYSTEM",
  "suite": "credito",
  "test_case": "fluxo end-to-end",
  "base_url": "https://app.example.com",
  "status": "intent_complete",
  "fingerprint": {"capture_schema_version": 4}
}
```

### `raw_events.jsonl`
**O que é:** Todos os eventos capturados durante a gravação — cliques, digitações, navegações, asserts. **Source of truth.**
**Quando ler:** Para debugar o que foi capturado. O normalizer lê este arquivo para gerar o teste.
**Formato:** Uma linha JSON por evento.
```json
{"event_id":"evt_00001","type":"navigation","timestamp":"...","url":"...","page_title":"..."}
{"event_id":"evt_00002","type":"fill","timestamp":"...","target":{...},"value":"123.456.789-00"}
```

### `steps.jsonl`
**O que é:** Apenas os asserts que você adicionou manualmente com **Shift+A**.
**Quando ler:** Para ver quais verificações foram adicionadas.
**Importante:** Este arquivo **não** contém cliques e preenchimentos — só asserts. As ações vêm do `raw_events.jsonl`.

### `submission_report.json`
**O que é:** Relatório gerado no publish para o Git. Contém versão do TestForge, métricas, critérios de prontidão.
**Quando ler:** Para saber se a gravação foi publicada com sucesso e qual o veredito.
```json
{
  "testforge_version": "0.1.0",
  "verdict": "pass",
  "criteria_passed": 5, "criteria_total": 5,
  "criteria": {"completeness_passed": true, "all_steps_passed": true, ...},
  "failing_criteria": []
}
```

---

## Arquivos de diagnóstico (debug)

### `value_mutations.jsonl`
Registra cada vez que o valor de um campo mudou durante a digitação. Ex: ao digitar "123.456.789-00" em um campo CPF, você verá ~14 linhas representando cada caractere inserido. Útil para debugar máscaras de input.

### `field_snapshots.jsonl`
Snapshot periódico do estado de todos os campos visíveis na página. Cada entrada contém valor, identificadores (id, name, placeholder, label) e fingerprint do campo.

### `keystroke_buffer.jsonl`
Cada tecla pressionada, individualmente. Usado para reconstruir digitação e para detecção de PII. **Este arquivo nunca vai para o GitHub** (contém teclas de campos password).

### `network_log.json`
Todas as requisições de rede (fetch/XHR) capturadas durante a gravação.

### `rrweb_events.jsonl`
Gravação visual no formato rrweb. Permite reproduzir a sessão como um vídeo.

### `suggested_assertions.jsonl`
Asserts que o TestForge sugere automaticamente baseado em mudanças no DOM. Cada sugestão tem um score de confiança.

---

## Arquivos de qualidade (gate de prontidão)

### `completeness/intent_completeness_report.md`
Relatório que mostra quais campos foram detectados, quais têm valor, e quais estão pendentes. Gerado quando você usa `--complete`.

- ✅ **Resolvidos:** campos com valor capturado ou fornecido pelo usuário
- ⚠️ **Pendentes:** campos detectados mas sem valor
- ❌ **Não resolvidos:** campos que o normalizador não conseguiu determinar

### `readiness/readiness_report.md`
Gate de prontidão. Gerado com `--validate-before-ready`. Avalia 5 critérios:

| Critério | O que verifica |
|----------|---------------|
| `completeness_passed` | Todos os campos têm valor? |
| `all_steps_passed` | O teste compilado executa sem falhas? |
| `blocking_steps_resolved` | Passos bloqueantes foram curados ou corrigidos? |
| `user_supplied_values_validated` | Valores fornecidos pelo QA são válidos? |
| `healing_oracles_passed` | As curas aplicadas produziram resultados corretos? |

**Vereditos possíveis:**
- **READY** — todos os 5 critérios passaram. Gravação pronta para o time.
- **REVIEW** — alguns critérios falharam. Precisa revisão humana.
- **FAIL** — critérios bloqueantes falharam. Gravação não está pronta.

---

## Diretórios de snapshot

### `dom_snapshots/`
Snapshots HTML do DOM no momento de cada evento. Útil para debugar seletores.

### `ax_snapshots/`
Árvore de acessibilidade (Accessibility Tree) no momento de cada evento. Usado pelo resolver L0.

**Importante:** Estes diretórios podem ser grandes. O comando `testforge prune-snapshots <id>` remove ambos para economizar espaço.

---

## Arquivos que NÃO vão para o GitHub

Por política de segurança, estes arquivos existem apenas localmente e nunca são enviados ao repositório Git:

- `keystroke_buffer.jsonl` — contém teclas individuais incluindo senhas
- `recording_config.json` — pode conter paths locais
- `.testforge/config.yml` — configurações de ambiente
- `sensitive_alerts.json` — alertas de PII (referência, não os dados)

---

## Resumo: quais arquivos você precisa conhecer

| Se você é... | Se importe com... |
|-------------|-------------------|
| **QA gravando** | `recording_metadata.json`, `completeness/`, `readiness/` |
| **QA revisando** | `submission_report.json`, `readiness/readiness_report.md` |
| **Dev debuggando** | `raw_events.jsonl`, `value_mutations.jsonl`, `dom_snapshots/` |
| **Dev melhorando seletores** | `raw_events.jsonl`, `ax_snapshots/`, `suggested_assertions.jsonl` |
| **Segurança** | `sensitive_alerts.json`, `keystroke_buffer.jsonl` |
