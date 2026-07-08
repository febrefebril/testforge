# TestForge v0.1.0 — Release Notes

**Data**: 2026-07-08
**Tipo**: Initial public clean release
**Sanity**: 450 passed, 1 xfailed (`pytest -m "unit or contract or regression"`)

---

## Sobre esta release

Primeira release pública clean do TestForge. Contém gravador de intenção com self-healing, publisher com filtro por destino (GitHub vs repo local), PII detector observability-only, alerta de gravação em produção.

Repo público (GitHub): **APENAS** código + docs sanitizadas. Gravações e massa de teste vão para o repo local (rede CORPORATIVO) via `testforge publish --target=local`.

---

## O que está dentro

### Recorder + Overlay
- Recorder Playwright com overlay de status (Shift+A assert, Shift+S stop, Shift+P pause)
- 4 camadas de healing: L0 catálogo → L1 fallback → L2 agents especialistas → L3 LLM
- SemanticTestCase + Playwright compiler nativo (get_by_role, get_by_label, get_by_placeholder)
- Detector de auto-fire (Bootstrap Carousel, Swiper, Slick, Owl) para reduzir ruído de gravação
- Filtro `_isOverlayElement` guard em `_pushEvent` (defense in depth)
- `<button type="button">` em todos os botões do overlay
- Pause com feedback visual (Pausado/Gravando)
- External step counter cross-origin (sobrevive nav entre subdomínios)

### Publisher
- `PublishTarget.LOCAL` — envia tudo (gravações + massa + configs) para repo interno
- `PublishTarget.GITHUB` — bloqueia artefatos sensíveis via `_GITHUB_BLOCKLIST_GLOBS`
- CLI: `testforge publish --target=local|github` (default: local)

### Segurança / Compliance
- PII detector observability-only (CPF, CNPJ, matrículas CORPORATIVO, senhas, emails, telefones)
- `keystroke_buffer.jsonl` no `.gitignore` (senha em plaintext nunca vai pro repo)
- Recording scanner varre `keystroke_buffer.jsonl` e alerta por fingerprint password
- Alerta ao gravar em URL de produção (dominios corporativos sem sufixo `-des/-tqs/-hom`) — **não bloqueia**
- Docs sanitizadas: CPFs/matrículas/senhas reais substituídos por placeholders

### Diagnostic Mode
- Framework detector (Angular, React, Vue, MUI, PrimeFaces)
- Capture quality tracker
- Replay check via Playwright locator
- Gherkin writer pt-BR
- Publisher para Azure DevOps

### Recording lifecycle
- Taxonomy 4 níveis: `system/subsystem/suite/test_case` (subsystem opcional)
- Timestamp suffix em duplicatas (`_YYYYMMDD-HHMMSS`)
- Sanitize unicode NFKD (`ç → c`, `ã → a`)
- Dedup detector por hash de sequência de events
- Migração retroativa de recordings sem taxonomy (`testforge migrate-uncategorized`)
- `recordings_failed/` com README + auto-prune de artifacts pesados
- Banner ao compile/run recording com schema antigo

---

## Getting Started

Veja a documentação completa:

| Guia | Link |
|------|------|
| Instalação (Windows e Linux) | [INSTALL.md](USER-GUIDE/INSTALL.md) |
| Interface Gráfica | [GUI-LAUNCHER.md](USER-GUIDE/GUI-LAUNCHER.md) |
| Como Gravar um Teste | [GRAVAR-FLUXO.md](USER-GUIDE/GRAVAR-FLUXO.md) |
| Arquivos da Gravação | [RECORDING-FILES.md](REFERENCIA/RECORDING-FILES.md) |
| Glossário | [GLOSSARY.md](REFERENCIA/GLOSSARY.md) |
| Workflow do QA | [qa-workflow.md](TUTORIAIS/qa-workflow.md) |

---

## Contratos hard

1. **Nada bloqueia** gravação ou publicação local. Só alerta.
2. **Massa de teste sempre gravada** — senhas, CPFs, PII vão para o disco local.
3. **GitHub público** = **APENAS código + docs sanitizadas**.
4. **Repo local rede CORPORATIVO** = tudo (gravações + massa + configs).

---

## Known issues (para v0.2.x)

### KI-01 — Estrutura de pastas de gravação suja
**Sintoma**: cada gravação cria 21 itens no root (7 JSONL, 5 JSON, 8 pastas, 1 MD). Debug (dom/ax) misturado com essencial (raw_events).

**Impacto**: publisher local envia tudo indiscriminadamente. Debug artifacts pesados (~1GB em SPA grandes) vão para repo interno mesmo quando gravação passou.

**Workaround**: `testforge prune-snapshots <recording>` após run OK.

**Fix planejado**: v0.2.0 refatoração `metadata/events/secrets/evidence/reports/`. Ver `docs/ROADMAP-V0.2.md`.

### KI-02 — Screenshot só na tela de login em algumas gravações
**Sintoma**: modo `evidence_level=full` deveria capturar screenshot por evento. Em alguns sistemas (Angular SPA), só a tela de login foi capturada; navegações internas não geram screenshot.

**Causa provável**:
- Angular SPA nav via History API sem `load` event firing
- `wait_for_load_state("domcontentloaded", 2000)` timeout silencioso
- Exception caught em `except: pass` (linhas 619-624 `recorder_controller.py`)

**Workaround**: usar Playwright tracing (`--use-cdp-recorder`) que captura viewport nativamente.

**Fix planejado**: v0.2.0 substituir `page.screenshot` por Playwright tracing. Filtrar overlay antes de screenshot para evitar `tf-panel` sobreposto.

### KI-03 — Modo full trava gravação em algumas páginas (flicker de tela)
**Sintoma**: em modo `evidence_level=full`, algumas páginas ficam mudando o tamanho da tela durante gravação. Na execução (`testforge run`), a tela pisca alternando entre tamanho pequeno e grande — provavelmente ao tirar screenshot.

**Causa provável**:
- `page.screenshot(type="png", full_page=False)` em modo full pode redimensionar viewport internamente
- Overlay `tf-panel` (position: fixed) reposiciona a cada resize
- Angular observa resize event e dispara re-layout → gera novos eventos → loop

**Workaround**: usar `evidence_level=light` (default). Ou desabilitar overlay via `TESTFORGE_DISABLE_OVERLAY=1`.

**Fix planejado**: v0.2.0
- Screenshot via Playwright tracing sem resize
- Suprimir `tf-panel` antes de screenshot (evaluate `display=none` → screenshot → restore)
- Trocar `no_viewport=True` por viewport fixo do tamanho da tela do testador (ver KI-04)

### KI-04 — Feature request: browser em fullscreen do testador
**Pedido**: usuário sugeriu que o navegador abra no tamanho fullscreen da tela do testador em vez de menor (default Playwright headed ~1280x720).

**Estado atual**: `cli/app.py:114` usa `no_viewport=True` em modo headed. Browser abre em tamanho de janela do sistema, geralmente menor que fullscreen.

**Impacto positivo**: gravações em resolução real do usuário (evita layouts diferentes entre gravação e replay).

**Precisa estudo**:
- Playwright Trace Viewer + screenshot podem quebrar se viewport for muito grande
- Testes de replay em CI (que rodam headless 1280x720) podem falhar se elementos renderizarem diferente
- Sistemas com layouts responsivos podem se comportar diferente em desktop wide (4K) vs 1080p vs 1280x720
- Screenshots ficariam pesados (1GB+ em modo full)

**Fix planejado**: v0.2.0 com opt-in `--fullscreen` flag. Default continua atual. Documentar trade-offs.

---

## Como atualizar

Nada a atualizar — release inicial.

## Como testar

```bash
source activate.sh
pip install -e ".[dev]"
playwright install chromium
pytest -m "unit or contract or regression" -q
# Esperado: 450 passed, 1 xfailed
```

## Como usar

```bash
# Gravar
testforge record https://sistema.tqs.example.com/ --name teste-login

# Compile + validate
testforge compile teste-login --data

# Executar (com healing)
testforge run-incremental semantic_tests/ST-teste-login/test_st_teste_login.py

# Publish local (rede CORPORATIVO)
testforge publish teste-login --target=local

# Publish github (só código + docs)
testforge publish teste-login --target=github  # bloqueia gravação
```

## Commits desde origem

Branch órfão `v0.1.0-clean` com 1 commit único (`45fb75b`). Histórico completo preservado em `feature/inline-overlay-prompt` local.

## Créditos

Contribuidores: André PN + assistentes LLM (Claude Opus 4.7, Claude Sonnet 4.6).
