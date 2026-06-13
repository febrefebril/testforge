# Milestone 3 — Plano: EvidenceCollector + EvidenceStore

## Objetivo
Coletar evidencias de execucao e disponibiliza-las para o healing e auditoria.

## Tarefas

### T1: EvidenceCollector
- [x] `src/testforge/evidence/evidence_collector.py`
  - screenshot_before / screenshot_after
  - dom_before / dom_after
  - network_log da sessao
  - manifest.json
  - sensitive_data_alert (alert_only)

### T2: EvidenceStore (JSONL)
- [x] `src/testforge/evidence/evidence_store.py`
  - Persistencia em JSONL + filesystem
  - evidence/{run_id}/ com subdiretorios
  - Query: list_pending, list_by_run

### T3: Integracao com Recorder
- [x] Coletar evidencias durante gravacao
- [x] Salvar evidence package ao finalizar

## Artefatos Esperados
```
evidence/{run_id}/
├── manifest.json
├── steps.jsonl
├── screenshots/before_evt_NNNN.png
├── screenshots/after_evt_NNNN.png
├── dom/before_evt_NNNN.html
├── dom/after_evt_NNNN.html
├── network_log.json
└── sensitive_data_alert.json
```
