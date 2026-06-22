# TestForge — Épico e Histórias do Recorder Sensorial

**Versão:** 0.2.0  
**Status:** draft  
**Data:** 2026-06-12  
**Decisão incorporada:** o `EvidenceCollector` e o `Recorder Sensorial` operam inicialmente em modo `alert_only` para dados sensíveis, sem mascaramento automático.

---

# EP-03 — Recorder Sensorial

## Objetivo

Implementar o componente responsável por capturar interações reais do usuário no navegador, preservando o máximo de evidências úteis para posterior transformação em Modelo Intermediário Semântico, sem tentar gerar diretamente o teste final e sem escolher um locator definitivo durante a gravação.

O Recorder Sensorial deve capturar eventos, contexto, snapshots e metadados de forma auditável, permitindo que uma sessão gravada seja convertida posteriormente em:

```text
RawRecordedSession
  -> SemanticTestCase
  -> Playwright Test gerado
  -> Execução com Shadow Mode / Evidence / Oracle / Promotion Gate
```

## Princípios

1. O gravador observa; ele não decide a cura.
2. O gravador não gera o script final como fonte de verdade.
3. O gravador não escolhe um locator definitivo.
4. O gravador captura sinais ricos para o MIS.
5. O teste semântico é a fonte de verdade; o Playwright gerado é artefato derivado.
6. Dados sensíveis são apenas alertados no MVP; não mascarados.

---

# Histórias

## US-03.01 — Iniciar e finalizar sessão de gravação

Como usuário do TestForge, quero iniciar e finalizar uma sessão de gravação para capturar um fluxo de interação no navegador.

### Critérios de aceite

- O usuário consegue iniciar uma sessão de gravação.
- A sessão recebe um `recording_id` único.
- A sessão cria diretório em `recordings/{recording_id}`.
- A sessão gera `recording_metadata.json`.
- A sessão registra application, base_url, started_at, finished_at e status.
- A sessão pode ser finalizada explicitamente.
- A sessão finalizada não aceita novos eventos.

### Artefatos esperados

```text
recordings/{recording_id}/recording_metadata.json
recordings/{recording_id}/raw_events.jsonl
```

---

## US-03.02 — Capturar eventos básicos de usuário

Como Recorder Sensorial, quero capturar eventos básicos de interação para representar o fluxo executado pelo usuário.

### Eventos mínimos

- click;
- fill/input;
- select;
- check/uncheck;
- navigation;
- submit, quando detectável;
- keypress relevante, quando necessário.

### Critérios de aceite

- Cada evento capturado é salvo em `raw_events.jsonl`.
- Cada evento possui `event_id`, `timestamp`, `type`, `url`, `page_title` e `target`.
- Eventos de fill/input registram valor de forma configurável conforme política de sensibilidade.
- No MVP, valores são preservados, mas o evento deve registrar alerta se possível dado sensível for detectado.
- O recorder não escolhe locator final.

### Artefato esperado

```json
{
  "event_id": "evt_0001",
  "type": "click",
  "timestamp": "2026-06-12T15:20:00-03:00",
  "url": "http://localhost:3000/consulta",
  "page_title": "Consulta de Cliente",
  "target": {
    "tag": "button",
    "text": "Pesquisar",
    "role": "button",
    "accessible_name": "Pesquisar"
  }
}
```

---

## US-03.03 — Capturar snapshot do alvo da ação

Como Recorder Sensorial, quero capturar informações ricas do elemento alvo para permitir geração posterior de candidatos de locator.

### Critérios de aceite

- Para cada evento com alvo DOM, captura tag, text, role, accessible_name, id, name, test_id, placeholder, label inferida e attributes relevantes.
- Captura bounding box quando disponível.
- Captura frame context quando aplicável.
- Captura shadow DOM context quando aplicável.
- Captura parent/ancestor summary em profundidade limitada.
- Captura sibling summary em profundidade limitada.
- Não gera XPath absoluto como locator preferencial.

### Artefato esperado

O objeto `target` do evento deve conter sinais semânticos e estruturais suficientes para alimentar `SemanticTarget`.

---

## US-03.04 — Capturar contexto da página e textos próximos

Como Recorder Sensorial, quero capturar contexto ao redor do elemento para permitir desambiguação posterior no MIS e no ranking de locators.

### Critérios de aceite

- Captura URL e page title.
- Captura textos próximos ao alvo.
- Captura nome de formulário, seção, modal ou região quando detectável.
- Captura índice aproximado do alvo dentro do container.
- Captura contexto visual mínimo via screenshot.
- Captura DOM snapshot por evento ou por passo configurável.
- Captura accessibility snapshot quando disponível.

### Artefatos esperados

```text
recordings/{recording_id}/screenshots/evt_0001.png
recordings/{recording_id}/dom_snapshots/evt_0001.html
recordings/{recording_id}/ax_snapshots/evt_0001.json
```

---

## US-03.05 — Capturar eventos de rede associados à gravação

Como Recorder Sensorial, quero registrar eventos de rede relevantes para apoiar oracles e validação pós-ação.

### Critérios de aceite

- Captura request method, URL, resource_type e timestamp.
- Captura response URL, status e timestamp.
- Associa eventos de rede próximos a uma ação quando possível.
- Salva `network_log.json` na sessão de gravação.
- Não depende de backend real para funcionar no Synthetic Lab.

### Artefato esperado

```text
recordings/{recording_id}/network_log.json
```

---

## US-03.06 — Persistir RawRecordedSession

Como TestForge, quero persistir a gravação bruta como artefato imutável ou quase imutável para permitir reprocessamento posterior.

### Critérios de aceite

- Cria estrutura de diretórios da sessão.
- Salva `recording_metadata.json`.
- Salva `raw_events.jsonl`.
- Salva screenshots, DOM snapshots e AX snapshots em subdiretórios.
- Salva `network_log.json`.
- Salva `sensitive_data_alert.json` ou campo equivalente no metadata.
- Não mascara dados automaticamente.

### Estrutura esperada

```text
recordings/
└── REC-YYYYMMDD-HHMMSS-001/
    ├── recording_metadata.json
    ├── raw_events.jsonl
    ├── network_log.json
    ├── sensitive_data_alert.json
    ├── screenshots/
    ├── dom_snapshots/
    └── ax_snapshots/
```

---

## US-03.07 — Gerar SemanticTestCase inicial a partir da gravação

Como TestForge, quero converter uma sessão bruta gravada em um Modelo Intermediário Semântico inicial.

### Critérios de aceite

- Lê `recordings/{recording_id}/raw_events.jsonl`.
- Gera `semantic_tests/{test_id}/semantic_test_case.yaml`.
- Cada evento relevante vira uma `SemanticAction`.
- Cada alvo vira um `SemanticTarget`.
- Gera candidatos iniciais de locator.
- Preserva referência à gravação original.
- Não gera auto-heal.

### Artefato esperado

```text
semantic_tests/{test_id}/semantic_test_case.yaml
```

---

## US-03.08 — Compilar teste Playwright inicial a partir do SemanticTestCase

Como TestForge, quero compilar o SemanticTestCase em um teste Playwright Python executável.

### Critérios de aceite

- Lê `semantic_tests/{test_id}/semantic_test_case.yaml`.
- Gera teste em `generated_tests/{test_id}/test_*.py`.
- Usa candidatos priorizados no MIS.
- Inclui oracles básicos quando definidos.
- O teste gerado roda contra o fake-react-bank-app sem mutação.
- O teste gerado é artefato derivado e pode ser regenerado.

### Artefato esperado

```text
generated_tests/{test_id}/test_consulta_cliente.py
```

---

## US-03.09 — Criar teste de ponta a ponta da gravação sintética

Como equipe TestForge, quero validar o fluxo completo: gravar, gerar MIS, compilar teste e executar.

### Critérios de aceite

- O teste inicia sessão de gravação contra fake-react-bank-app.
- O teste executa preenchimento de CPF e clique em Pesquisar.
- O recorder persiste RawRecordedSession.
- O normalizer gera SemanticTestCase.
- O compiler gera Playwright test.
- O Playwright test gerado passa contra fake-react-bank-app sem mutação.
- Todos os artefatos ficam nos diretórios esperados.

---

# Tarefas sugeridas

## Para US-03.01

- T-03.01.01 — Criar `RecordingSession`.
- T-03.01.02 — Criar `RecorderController.start()`.
- T-03.01.03 — Criar `RecorderController.stop()`.
- T-03.01.04 — Persistir `recording_metadata.json`.
- T-03.01.05 — Testar criação/finalização da sessão.

## Para US-03.02

- T-03.02.01 — Criar modelo `RawRecordedEvent`.
- T-03.02.02 — Capturar click.
- T-03.02.03 — Capturar input/fill.
- T-03.02.04 — Capturar navigation.
- T-03.02.05 — Persistir eventos em JSONL.

## Para US-03.03

- T-03.03.01 — Implementar extração de atributos do alvo.
- T-03.03.02 — Implementar inferência de accessible name.
- T-03.03.03 — Implementar inferência de label.
- T-03.03.04 — Capturar bounding box.
- T-03.03.05 — Capturar frame/shadow context.

## Para US-03.04

- T-03.04.01 — Capturar textos próximos.
- T-03.04.02 — Capturar DOM snapshot.
- T-03.04.03 — Capturar accessibility snapshot quando disponível.
- T-03.04.04 — Capturar screenshot por evento.

## Para US-03.05

- T-03.05.01 — Implementar network recorder.
- T-03.05.02 — Associar rede a evento próximo.
- T-03.05.03 — Persistir `network_log.json`.

## Para US-03.06

- T-03.06.01 — Implementar `RawRecordingStore`.
- T-03.06.02 — Criar estrutura `recordings/{recording_id}`.
- T-03.06.03 — Persistir alerta sensitive data alert_only.
- T-03.06.04 — Testar integridade da sessão gravada.

## Para US-03.07

- T-03.07.01 — Implementar `RecordingNormalizer`.
- T-03.07.02 — Implementar conversão evento -> SemanticAction.
- T-03.07.03 — Gerar candidatos iniciais.
- T-03.07.04 — Persistir `semantic_test_case.yaml`.

## Para US-03.08

- T-03.08.01 — Implementar `PlaywrightPythonCompiler`.
- T-03.08.02 — Gerar teste Python.
- T-03.08.03 — Gerar fixture mínima.
- T-03.08.04 — Executar teste gerado contra fake app.

## Para US-03.09

- T-03.09.01 — Criar script `scripts/record_fake_flow.py`.
- T-03.09.02 — Criar script `scripts/compile_recording.py`.
- T-03.09.03 — Criar teste E2E da cadeia gravação -> MIS -> Playwright.
