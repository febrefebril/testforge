# TestForge Roadmap v0.2.0

**Base**: v0.1.0 (2026-07-08)
**Objetivo**: refatorar estrutura de pastas + policy de evidence + fullscreen opt-in

---

## Temas

1. **Estrutura de pastas limpa** (KI-01)
2. **Screenshot capture robusto** (KI-02, KI-03)
3. **Fullscreen opt-in** (KI-04)
4. **Publish differentiator por severidade** (extensão do PublishTarget)

---

## Tema 1 — Refatoração estrutura de pastas

### Problema

Cada gravação hoje cria 21 itens no root do recording:
```
recording/
├── raw_events.jsonl
├── steps.jsonl
├── value_mutations.jsonl
├── field_snapshots.jsonl
├── keystroke_buffer.jsonl
├── rrweb_events.jsonl
├── suggested_assertions.jsonl
├── recording_metadata.json
├── recording_config.json
├── final_state_snapshot.json
├── submission_report.json
├── network_log.json
├── ax_snapshots/
├── dom_snapshots/
├── completeness/
├── readiness/
├── diagnostic/
├── _pilot_runs/
├── _pilot_tmp/
├── recordings_failed/
└── SUMMARY.md
```

Debug (dom/ax) misturado com essencial (raw_events). Publisher envia tudo indiscriminadamente. Repo interno cresce ~1GB por gravação de SPA grande.

### Estrutura alvo

```
recording/
├── metadata.json          # merge recording_metadata + recording_config + fingerprint
├── events/                # essencial — sempre enviado ao repo local
│   ├── raw.jsonl
│   ├── steps.jsonl
│   ├── value_mutations.jsonl
│   ├── field_snapshots.jsonl
│   ├── network.json
│   ├── rrweb.jsonl
│   └── suggested_assertions.jsonl
├── secrets/               # NUNCA vai para repo (nem local)
│   └── keystroke_buffer.jsonl
├── evidence/              # só se: evidence_level=full OU compile/run falhou
│   ├── dom/
│   ├── ax/
│   ├── screenshots/
│   └── final_state.json
├── reports/               # só existem quando compile/run rodou
│   ├── completeness.md
│   ├── completeness.json
│   ├── readiness.md
│   ├── readiness.json
│   ├── submission.json
│   └── diagnostic/
├── pilot/                 # sempre limpado após run (não versiona)
│   └── (temporário — gitignore)
└── SUMMARY.md             # human-readable
```

### Contrato de publicação por camada

| Camada | Local (rede CORPORATIVO) | GitHub (público) |
|--------|-------------------|-----------------|
| `metadata.json` | ✅ | ✅ (sem PII) |
| `events/` | ✅ | ❌ |
| `secrets/` | ❌ nem no repo local | ❌ |
| `evidence/` | ✅ **só se falha** | ❌ |
| `reports/` | ✅ | ❌ |
| `SUMMARY.md` | ✅ | ✅ (sanitizado) |

Publisher decide por camada, não por arquivo individual.

### Impacto

- `raw_recording_store.py` — paths novos
- `recorder_controller.py` — writes novos
- `recording_normalizer.py` — leituras
- `semantic/compiler.py` — leituras
- `publisher/git_publisher.py` — copies por camada
- `validation/intent_completeness.py` + `readiness_gate.py` — outputs em `reports/`
- ~30 testes que assumem paths atuais

### Estratégia de migração

**Não quebrar recordings v0.1.0 existentes**:
- Adicionar `RecordingStructureVersion` no `metadata.json`
- Reader detecta v0.1.0 (root flat) vs v0.2.0 (subpastas)
- CLI `testforge migrate-structure <recording>` opt-in

### Estimativa: 2 dias (uma semana com regressão bem coberta)

---

## Tema 2 — Screenshot capture robusto

### Problema (KI-02)

Modo `evidence_level=full` deveria capturar screenshot por evento. Em Angular SPAs, só a tela de login é capturada; navegações internas falham silenciosamente.

**Causa provável**:
- `wait_for_load_state("domcontentloaded", 2000)` timeout em SPA
- Exception caught em `except: pass`
- Angular history API nav não dispara `load` event

### Problema (KI-03)

Modo full causa flicker durante gravação e execução (`testforge run`). Tela pisca entre pequeno e grande — provavelmente ao chamar `page.screenshot(full_page=False)`.

**Causa provável**:
- `page.screenshot` internamente pode alterar viewport pra capturar full page
- Overlay `tf-panel` (position: fixed) reposiciona a cada resize
- Angular observa `resize` event → re-layout → gera novos eventos → loop

### Solução alvo

1. **Trocar `page.screenshot` por Playwright tracing**:
   ```python
   context.tracing.start(screenshots=True, snapshots=True)
   # ... gravação
   context.tracing.stop(path="trace.zip")
   ```
   - Screenshot por action nativo
   - Sem viewport resize
   - Abre em trace.playwright.dev

2. **Suprimir overlay antes de screenshot**:
   ```python
   self._page.evaluate("document.getElementById('tf-panel').style.visibility='hidden'")
   data = self._page.screenshot(...)
   self._page.evaluate("document.getElementById('tf-panel').style.visibility=''")
   ```

3. **Fallback robusto para SPA nav**:
   ```python
   # Detecta SPA nav via URL change em vez de load event
   self._page.wait_for_url("**/*", timeout=2000)
   # OU: hook em history.pushState via init script
   ```

4. **Log de exceções** em vez de `except: pass`:
   ```python
   except Exception as exc:
       logger.warning("Screenshot failed for %s: %s", eid, exc)
       self._failed_screenshots.append((eid, str(exc)))
   ```

### Estimativa: 2-3 dias com testes em Angular SPA real

---

## Tema 3 — Fullscreen opt-in

### Pedido

Usuário sugeriu que o navegador abra no tamanho fullscreen da tela do testador em vez de menor (default Playwright headed ~1280x720). Motivo: gravações em resolução real, layouts responsivos que só aparecem em desktop wide, comportamento diferente entre gravação e replay.

### Estado atual

`cli/app.py:108-117`:
```python
def _make_context_kwargs(headless: bool, verify_ssl: bool = True) -> dict:
    kwargs: dict = {}
    if headless:
        kwargs["viewport"] = {"width": 1280, "height": 720}
    else:
        kwargs["no_viewport"] = True   # ← janela abre no tamanho do sistema
    ...
```

### Proposta

Adicionar flag opt-in:
```bash
testforge record https://... --fullscreen
```

Implementação:
```python
if args.fullscreen:
    # Descobrir tamanho da tela do testador
    import tkinter as tk
    root = tk.Tk()
    w, h = root.winfo_screenwidth(), root.winfo_screenheight()
    root.destroy()
    kwargs["viewport"] = {"width": w, "height": h}
    # Args do browser para abrir maximizado
    launch_args = ["--start-maximized"]
```

### Trade-offs (precisam estudo)

**Risco 1 — Testes de replay em CI**:
- CI roda `pytest` headless com viewport 1280x720 fixo
- Se gravação foi em 3840x2160, elementos podem ter positions/selectors diferentes
- **Mitigação**: `viewport` gravado como metadata, replay usa mesmo viewport
- **Risco residual**: CI machine pode não conseguir renderizar 4K

**Risco 2 — Layouts responsivos**:
- Sistemas com breakpoint em 1024px podem mostrar mobile menu em 1024x768 e desktop menu em 1920x1080
- Selectors podem mudar entre resoluções
- **Mitigação**: healing L2 fallback pra selectors alternativos

**Risco 3 — Screenshot pesado**:
- Full-page screenshot em 4K = 10-15MB por evento
- SPA com 100 events = 1-1.5GB
- **Mitigação**: `evidence_level=light` continua default. Fullscreen só afeta viewport, não screenshot policy.

**Risco 4 — tkinter dependency**:
- `tkinter` não vem em todas instalações Python (Alpine linux, minimal Docker)
- **Mitigação**: fallback graceful pra `screeninfo` package ou hardcode `1920x1080` se tkinter falhar

**Risco 5 — Multi-monitor**:
- Testador com 2 monitores: qual "fullscreen"?
- **Mitigação**: usar monitor primário. Opção `--display=1|2`.

### Estimativa: 1-2 dias com testes

---

## Tema 4 — Publish differentiator por severidade

Extensão natural do `PublishTarget`.

Hoje: `local` (tudo) vs `github` (código + docs).

v0.2.0 propõe granularidade:

```bash
testforge publish rec --target=local              # tudo
testforge publish rec --target=local --only-essential  # só metadata + events (sem evidence)
testforge publish rec --target=local --with-evidence   # inclui dom/ax/screenshots
testforge publish rec --target=github             # só código + docs sanitizadas
```

Regra automática:
- `verdict=pass`: `--only-essential` default
- `verdict=fail` ou `verdict=needs_review`: `--with-evidence` default

### Estimativa: 1 dia

---

## Timeline

| Sprint | Dias | Escopo |
|--------|------|--------|
| Sprint 1 | 2 dias | Tema 1 — refatoração estrutura de pastas |
| Sprint 2 | 3 dias | Tema 2 — screenshot capture robusto |
| Sprint 3 | 2 dias | Tema 3 — fullscreen opt-in |
| Sprint 4 | 1 dia | Tema 4 — publish severidade |
| Sprint 5 | 2 dias | Regressão + docs + release |
| **Total** | **10 dias** | v0.2.0 |

Alvo de release: **~2 semanas após v0.1.0**.

---

## Pendências carregadas do v0.1.0

Skip do plano `PENDENCIAS-IMPLEMENTATION-PLAN.md`:
- **REC-50** value_captured por field — mover para v0.2.0
- **REC-13** confidence semantic weights — mover para v0.2.0
- **REC-14** search_and_select cross-framework — mover para v0.2.0
- **0.5** synthetic fixtures — mover para v0.2.0

Nenhum bloqueia release v0.1.0. Todos melhorias incrementais.

---

## Não roadmap

Coisas que **NÃO** vão para v0.2.0:
- Suporte a Firefox/Safari (só Chromium por enquanto)
- Recorder mobile (só web)
- Cloud recorder (só local)
- Distributed run (só single-machine)

Estas ficam para v0.3.0+ se demanda aparecer.

---

## Como contribuir

- Bugs em `docs/RELEASE-NOTES-v0.1.0.md` seção "Known issues" são candidatos naturais.
- PRs devem incluir teste + atualização deste doc se afetar escopo.
- Feature requests via issue GitHub com label `roadmap-v0.2`.
