# Extension Bugs (War Room Prototype)

## BUG-EXT-001: background.service_worker não suportado no Firefox

**Contexto:** Manifest V3 exige `background.service_worker` no Chrome, mas Firefox (versão atual) não suporta service worker como background. O erro aparece ao carregar a extensão temporária.

**Sintoma:** Extensão não carrega, console do about:debugging mostra `background.service_worker is currently disabled`.

**Solução:** Substituir `service_worker` por `background.scripts` (cria uma background page persistente) ou usar `manifest.json` diferente por navegador (build step).

**Impacto:** Chrome MV3 exige service worker. Se quiser suportar ambos, precisa de 2 manifests + build step.

**Cross-browser:**
| Navegador | Abordagem |
|-----------|-----------|
| Chrome | `service_worker` (MV3 obrigatório) |
| Edge | `service_worker` (Chromium, igual Chrome) |
| Firefox | `scripts` (MV3 aceita, persistente) ou `service_worker` (experimental) |

---

## BUG-EXT-002: Content script perde estado em navegação completa

**Contexto:** Content script é reexecutado do zero a cada navegação completa (F5, link externo, form submit síncrono). Em navegações SPA (history.pushState) o estado persiste porque a página não recarrega.

**Sintoma:** Botão "Gravar" volta ao estado inicial, steps desaparecem do overlay.

**Solução:** Background page (persistente no Firefox) segura o estado. Content script, ao iniciar, pergunta ao background via `chrome.runtime.sendMessage({ type: 'getState' })` e restaura overlay + steps.

**Impacto:** Resolvido no Firefox (background persistente). No Chrome (service worker não-persistente), o worker pode ser destruído — estado perdido de novo. Precisa de `storage.session` API para Chrome.

**Cross-browser:**
| Navegador | Background | Solução |
|-----------|-----------|---------|
| Chrome | Service worker (não persistente) | Precisa `chrome.storage.session` para persistir |
| Edge | Service worker (não persistente) | Idem Chrome |
| Firefox | Background page (persistente) | `chrome.runtime.sendMessage` resolve |

---

## Summary

| Bug | Chrome | Edge | Firefox | Status |
|-----|--------|------|---------|--------|
| BUG-EXT-001 | ✅ funciona | ✅ funciona | ❌ `scripts` (workaround) | Workaround aplicado |
| BUG-EXT-002 | ❌ perde estado | ❌ perde estado | ✅ resolvido (background persistente) | Resolvido FF, pendente Chrome/Edge |
