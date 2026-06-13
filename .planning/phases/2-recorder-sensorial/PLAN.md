# Milestone 2 — Plano: Recorder Sensorial

## Objetivo
Implementar captura de eventos do usuario via Playwright nativo, gerando RawRecordedSession completa.

## Tarefas

### T1: RecordingSession + RecorderController (US-03.01)
- [ ] `src/testforge/recorder/recording_session.py` — RecordingSession dataclass
- [ ] `src/testforge/recorder/recorder_controller.py` — RecorderController com start()/stop()
- [ ] `src/testforge/recorder/raw_event.py` — RawRecordedEvent model
- [ ] `src/testforge/recorder/raw_recording_store.py` — Persistencia em JSONL
- [ ] Teste unitario: criar/parar sessao, metadata gerado

### T2: Captura de eventos basicos (US-03.02)
- [ ] Listener `page.on('pointerup')` — click events
- [ ] Listener `page.on('input')` + `page.on('keydown')` — fill events
- [ ] Listener `page.on('load')` — navigation events
- [ ] Cada evento → RawRecordedEvent → append JSONL
- [ ] Target basico: tag, text, role, accessible_name, id, name
- [ ] Teste sintetico contra fake-react-bank-app

### T3: Snapshot do alvo + contexto (US-03.03, US-03.04)
- [ ] Extracao de atributos completos do elemento alvo
- [ ] Inferencia de accessible_name, label, placeholder
- [ ] DOM snapshot por evento (outerHTML)
- [ ] AX snapshot por evento (quando disponivel)
- [ ] Screenshot por evento
- [ ] Textos proximos, form context, frame context

### T4: Network log + sensitive data (US-03.05)
- [ ] `page.on('request')` + `page.on('response')` — network log
- [ ] `network_log.json` na sessao
- [ ] Detector alert_only: CPF, CNPJ, telefone
- [ ] `sensitive_data_alert.json`

### T5: Teste E2E da gravacao (US-03.09)
- [ ] Script `scripts/record_fake_flow.py`
- [ ] Fluxo: iniciar sessao → gravar fake app → finalizar
- [ ] Validar: raw_events.jsonl, screenshots, DOM, metadata

## Artefatos Esperados

```
recordings/REC-YYYYMMDD-HHMMSS-001/
├── recording_metadata.json
├── raw_events.jsonl
├── network_log.json
├── sensitive_data_alert.json
├── screenshots/evt_0001.png
├── dom_snapshots/evt_0001.html
└── ax_snapshots/evt_0001.json
```

## Verificacao
- Sessao inicia/para/finaliza corretamente
- raw_events.jsonl contem eventos de fill e click
- Screenshots e DOM snapshots existem para cada evento
- Network log registra requests/responses
- Sensitive data alert dispara para CPF
- Teste E2E executa fluxo completo contra fake app
