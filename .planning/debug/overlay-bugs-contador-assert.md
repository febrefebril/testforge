---
slug: overlay-bugs-contador-assert
status: investigating
trigger: "3 bugs no overlay JS do gravador: contadores steps/asserts não atualizam em tempo real; menu de tipo de assert não abre no Shift+A"
created: 2026-06-19
updated: 2026-06-19
---

## Symptoms

- **Expected:** Overlay mostra contagem de steps e asserts atualizada em tempo real; Shift+A abre menu de tipo de assert
- **Actual:** Contadores ficam zerados/desatualizados; menu de assert não aparece
- **Error messages:** Nenhum erro visível ao usuário
- **Timeline:** Contadores: sempre assim desde início. Menu de assert: funcionava antes, parou recentemente (regressão)
- **Reproduction:** Sempre, desde o início de qualquer gravação

## Bugs

- BUG-1: Contador de steps não atualiza em tempo real
- BUG-2: Contador de asserts não atualiza em tempo real
- BUG-3: Menu de tipo de assert (textual/estado/visível) não abre ao Shift+A

## Current Focus

hypothesis: "Os contadores não são atualizados porque o JS não recebe/processa eventos de step capturado; o menu de assert foi removido ou seu trigger foi quebrado em commit recente"
next_action: "Ler _OVERLAY_JS em recorder_controller.py — localizar código dos contadores e do menu de assert"

## Evidence

## Eliminated

## Resolution

root_cause:
fix:
verification:
files_changed:
