---
phase: 11-hotfix-piloto-remover-cdp-parar-flick-corrigir-cli
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - src/testforge/cli/app.py
  - src/testforge/recorder/recorder_controller.py
autonomous: true
---

# Phase 11 — Overlay UX + Executor Stability

## Objetivo

Corrigir 5 problemas identificados no piloto Windows:

1. **Viewport flickering** — `cmd_run` chama `set_viewport_size` em headed mode, causando resize visível
2. **Assert counter** — contador #tf-assert-count não incrementa (overlay duplicado após navegação)
3. **Assert confirmation** — após selecionar tipo de assert, mostrar preview com Confirmar/Descartar
4. **Stop sem assert** — Shift+S com assert mode ativo deve perguntar antes de sair
5. **Pause button state** — botão ⏸ não reflete estado atual (pausado vs gravando)

## Tasks

### T1: Remover viewport resize no cmd_run
- `app.py` linha ~628: remover `page.set_viewport_size({"width": 1280, "height": 720})`
- Execução headless já não chega neste caminho; headed mode não deve redimensionar

### T2: Deduplicar overlay em _tf_showOverlay
- Adicionar guard `if (document.getElementById('tf-overlay')) return;`
- Impede duplicação após SPA navigation, preserva contadores

### T3: Adicionar _tf_showAssertConfirm
- Nova função que mostra painel com: tipo, elemento, valor capturado, botões Confirmar/Descartar
- Confirmar → persiste assert + incrementa contadores + fecha painel
- Descartar → fecha painel + reativa modo assert para nova seleção
- Assert menu button onclick → chama confirm em vez de persistir direto

### T4: Adicionar _tf_showStopConfirm
- Nova função que mostra modal "Deseja sair sem marcar o assert?"
- Shift+S keydown → verifica `__tfAssertWaiting` antes de parar
- Stop button onclick → mesma verificação
- Sair sem assert → desativa assert mode + enfileira STOP

### T5: Pause button visual state
- Adicionar `window.__tfIsPaused = false` e `_tf_updatePauseState()`
- updatePauseState: botão ⏸→▶, dot cinza/vermelho, status text
- Shift+P e btn-pause onclick: toggle + chamar updatePauseState

## Critérios de Aceite

- Executor não flicca em headed Windows
- Contador de asserts incrementa corretamente
- Após selecionar tipo, aparece painel de confirmação com valor
- Descartando volta ao modo assert para nova seleção
- Shift+S com assert ativo mostra modal de confirmação
- Botão pause muda visualmente entre ⏸ e ▶
