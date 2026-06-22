# TestForge — Critérios de Aceite do Recorder Sensorial

**Versão:** 0.2.1  
**Status:** draft  
**Data:** 2026-06-12  
**Política de dados sensíveis:** `alert_only`; não mascarar automaticamente no MVP.

---

# 1. Objetivo do Recorder Sensorial

O Recorder Sensorial é responsável por capturar uma sessão real de interação do usuário no navegador e persistir uma `RawRecordedSession` rica em evidências, sem gerar diretamente o teste final e sem escolher um locator definitivo.

Fluxo esperado:

```text
Interação do usuário
  -> Recorder Sensorial
  -> RawRecordedSession
  -> SemanticTestCase
  -> Playwright Test gerado
```

---

# 2. Critérios de aceite gerais do gravador

## AC-RC-001 — Sessão de gravação

- Deve ser possível iniciar uma sessão de gravação.
- Cada sessão deve possuir `recording_id` único.
- Cada sessão deve criar diretório próprio em `recordings/{recording_id}`.
- Cada sessão deve gerar `recording_metadata.json`.
- Cada sessão deve gerar `raw_events.jsonl`.
- A sessão deve registrar `started_at`, `finished_at`, `status`, `application`, `base_url` e `recorder_version`.
- Uma sessão finalizada não deve aceitar novos eventos.

## AC-RC-002 — Eventos mínimos capturados

O gravador deve capturar, no mínimo:

- `navigation`;
- `fill` ou `input`;
- `click`;
- `submit`, quando detectável;
- `select`, quando aplicável;
- `check` e `uncheck`, quando aplicável.

Cada evento deve conter:

- `event_id`;
- `sequence`;
- `timestamp`;
- `type`;
- `url`;
- `page_title`;
- `target`, quando houver alvo DOM;
- `artifacts`, quando houver snapshots associados.

## AC-RC-003 — Alvo da ação

Para cada evento com alvo DOM, o gravador deve capturar:

- `tag`;
- `text`;
- `role`;
- `accessible_name`;
- `id`;
- `name`;
- `data-testid` ou equivalentes configurados;
- `placeholder`;
- `label` inferida;
- `attributes` relevantes;
- `bounding_box`, quando disponível;
- `frame_context`;
- `shadow_context`;
- `ancestor_summary`;
- `sibling_summary`.

O gravador **não deve** escolher locator definitivo.

## AC-RC-004 — Contexto da página

Para cada evento relevante, o gravador deve capturar:

- URL atual;
- título da página;
- textos próximos ao alvo;
- região, formulário, seção ou modal quando detectável;
- índice aproximado do alvo no container;
- snapshot DOM;
- snapshot de accessibility tree quando disponível;
- screenshot do estado do navegador.

## AC-RC-005 — Rede

Durante a gravação, o gravador deve capturar eventos básicos de rede:

- request URL;
- request method;
- resource type;
- response URL;
- response status;
- timestamps;
- associação aproximada com evento de usuário quando possível.

O log deve ser salvo em:

```text
recordings/{recording_id}/network_log.json
```

## AC-RC-006 — Dados sensíveis em modo alert_only

No MVP, o gravador deve:

- detectar padrões simples de possível dado sensível, como CPF, CNPJ e identificadores numéricos longos;
- registrar alerta em `sensitive_data_alert.json`;
- registrar resumo do alerta em `recording_metadata.json`;
- manter `masking_applied: false`;
- manter `policy: alert_only`;
- não mascarar, remover ou alterar `raw_events.jsonl`, screenshots, DOM snapshots, AX snapshots ou network logs.

## AC-RC-007 — Integridade dos artefatos

Ao finalizar uma sessão, devem existir:

```text
recordings/{recording_id}/recording_metadata.json
recordings/{recording_id}/raw_events.jsonl
recordings/{recording_id}/network_log.json
recordings/{recording_id}/sensitive_data_alert.json
recordings/{recording_id}/screenshots/
recordings/{recording_id}/dom_snapshots/
recordings/{recording_id}/ax_snapshots/
```

Os eventos em `raw_events.jsonl` devem referenciar os artefatos associados por caminho relativo.

## AC-RC-008 — Reprocessabilidade

Uma gravação bruta deve ser reprocessável.

- Deve ser possível ler `raw_events.jsonl` após a gravação.
- Deve ser possível gerar um `SemanticTestCase` a partir da gravação.
- A gravação não deve depender de estado em memória após finalizada.
- A gravação deve conter `schema_version`.

## AC-RC-009 — Não acoplamento ao teste gerado

O gravador não deve gerar diretamente o teste final como fonte de verdade.

- O gravador gera `RawRecordedSession`.
- O normalizador gera `SemanticTestCase`.
- O compilador gera Playwright test como artefato derivado.

## AC-RC-010 — Testabilidade automática

O gravador deve possuir testes automáticos que validem:

- criação e finalização da sessão;
- captura de eventos `navigation`, `fill` e `click`;
- persistência de `raw_events.jsonl`;
- criação de screenshots e DOM snapshots;
- criação de `sensitive_data_alert.json` em modo alert_only;
- ausência de mascaramento automático;
- geração posterior de `SemanticTestCase` a partir da gravação.
