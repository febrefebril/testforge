
# TestForge — Project Context

## Goal
Implementar gravador inteligente de testes com Playwright + LLM.

## Architecture
- **Hybrid**: Python + TypeScript
- **CLI**: Typer
- **LLM**: GPT-4.1-mini via Azure API
- **Storage**: JSONL/filesystem (DB futuramente)
- **Script generation**: AST (`ast` module), Playwright Python puro
- **Overlay**: `add_init_script` com guarda DOM (try/catch + `document.body`)
- **Notifications**: env vars `TF_NOTIFY_EMAIL_*` e `TF_NOTIFY_TEAMS_WEBHOOK`. Desligado por padrão, graceful skip.
- **Report**: `<script_name>_report.json` dentro de `<script_name>_artifacts/` ao lado do script + data.json. Screenshots em `screenshots/`, trace como `trace.zip`.
- **Browser config**: args `--no-first-run`, `--disable-sync`, `--disable-translate`, `--disable-notifications`, etc. Context locale `pt-BR`.

## Key Technical Decisions

### Event capture
- **`pointerup`** (window, capture phase) em vez de `click`/`mousedown`/`mouseup` — Chromium não dispara eventos de mouse em elementos `disabled`. Só `pointerup` funciona consistentemente.
- **Synthetic click sem DOM mutation**: para elementos `disabled`, dispara `mousedown`+`mouseup`+`click` (`isTrusted=false`) sem remover `disabled`.
- **Listener no `window`** (não `document`): evita que handlers de página em capture phase no `document` impeçam a captura.

### Fill detection
- Unificada: `input` + `keydown` + `change` + polling (500ms)
- Campos com máscara JS (Caixa, bancos) não disparam `input` events — detectados via `keydown` + verificação periódica de valor.

### Recording Strategy (overlay.js)
- **Evidence Collector**: captura TODOS os atributos (id, class, data-*, aria-*, role, rect, parentChain, framework)
- **N Strategies per step**: `generateStrategies(el)` gera data-testid, id, name, aria-label, placeholder, has-text, href, alt, class, dom-path
- **Primary selector**: best strategy (ID > data-testid > name > aria-label > ...)
- **Page technology**: detectado via `_tf_detectPageTech()` (PrimeFaces, jQuery UI, Kendo, Angular)
- **Framework detection**: `detectFramework(el)` por DOM inspection (não só window globals)

## Architecture Shift (2026-06-11)
- **Overlay = Evidence Collector**: captura TUDO do elemento (atributos, rect, parentChain, framework). NÃO tenta "adivinhar" qual elemento importa.
- **Self-healing resolve falhas**: Layer 1 (catálogo determinístico), Layer 2 (agente especialista por framework), Layer 3 (LLM healer com payload).
- **Para cada novo framework**: só adicionar agente no Layer 2, não modificar overlay.js.

### Modes
- **`full`**: overlay com UI DOM (botões, painel)
- **`shortcuts`**: sem UI DOM, apenas listeners ativos. Zero interferência visual.

### Autocomplete
- Após clique em `.ui-menu-item`, verifica valor do input focado após 50ms e cria fill step com o valor final.

### Dialog handling
- `page.on("dialog")` com auto-accept em runner e session — `alert()`/`confirm()` bloqueiam Playwright se não houver handler.

## Important Behaviors
- `page.fill()` não dispara `input` events no DOM
- `page.click('a')` com múltiplos matches **não** lança erro — clica no primeiro elemento
- `page.fill(selector, value)` espera seletor único, visível e habilitado
- `locator.check()` é a API correta para radio buttons (idempotente, não toggle)

## Completed Epics
- **Epic 1 completo**: Stories 1-0 a 1-8
  - 1-3: Execução headed/headless, step timeout, recovery, relatório partial
  - 1-4: Asserts multi-tipo (texto, estado, visível, automático)
  - 1-5: Relatório em duas camadas + histórico com `--period` e `--status`
  - 1-6: Notificação e-mail (SMTP) e Teams (webhook)
  - 1-7: Upload/download de arquivos
  - 1-8: Shadow DOM, select com `label=`, date picker, autocomplete
- **Epic A**: Estabilização Gravador contra Taxonomia — done
- **Epic B**: Curador Inteligente — done (stories B.1 a B.6)
- **Epic D**: Páginas de Teste e Roteiro Manual — done
- **Epic E**: Runner Resiliência e Recuperação — done (E.1)
- **Epic F.0 + F.1**: Páginas de Teste + Detecção overlay.js — done (2026-06-11)

## Done (2026-06-12)
- **Recipe Auto-Healing (Layer 0)**: `HealingRecipe` modelo + `HealingCatalog` CRUD + `_try_with_recipes()` no runner
- **LLM Recipe Generation**: `_generate_recipe_from_failure()` chama GPT-4.1-mini e salva recipe no catálogo
- **`wait_for_function` timeout handling**: se a espera pós-action falha, recipe não é reportada como sucesso
- **`.env` auto-load**: `python-dotenv` carrega `.env` do CWD para AZURE_OPENAI_KEY/ENDPOINT/MODEL/API_VERSION
- **LLM client sem `--llm` flag**: `_get_llm_client()` agora funciona independente de `self.llm_validate` (recipe generation não depende de `--llm`)

## In Progress
- **F.2**: Runner — Execução PrimeFaces com Fallbacks (parcial)
  - `_try_primefaces_select()` implementado
  - Pendente: testes com `testforge run` real, ajustes no builder

## Backlog
- **F.3**: Healing — Agente Especialista PrimeFaces (FAM-08)
- **F.2 finalização**: Ajustar builder para gerar código PrimeFaces + testes completos
- **Testes multi-framework**: jQuery UI SelectMenu, Kendo DropDownList, Angular Material mat-select
- **F.4**: Curador Automático — valida por execução, registra no catálogo (learned), stale detection 90d

## Backlog
- **F.3**: Healing — Agente Especialista PrimeFases (FAM-08)
- **F.2 finalização**: Ajustar builder para gerar código PrimeFaces + testes completos
- **Testes multi-framework**: jQuery UI SelectMenu, Kendo DropDownList, Angular Material mat-select

## PrimeFaces Widget Detection (overlay.js)
- `detectFramework(el)`: detecta PrimeFaces (`.ui-selectonemenu`, `.ui-autocomplete`), jQuery UI (`$.ui`), Kendo (`k-dropdownlist`), Angular Material (`mat-select`, `[role="listbox"]`)
- `_tf_detectPageTech()`: popula `window.__tfPageTech` via detecção de globais (`PrimeFaces`, `jQuery.ui`, `kendo`, `angular`)
- `resolveElement()`: resolução de `.ui-selectonemenu` → hidden `<select>`, `.k-dropdownlist` → input, `mat-select` → trigger
- `capturePointerUp()`: suggestion detection extendida para `.ui-selectonemenu-item`, `.ui-autocomplete-item`, `.k-item`, `.mat-option`
- `generateBestSelector()`: `<li>` agora gera `li:has-text("...")` em vez de `li.classe`

## PrimeFaces Runner Strategy (runner.py)
1. **`select_option(force=True)`**: tentativa rápida no hidden `<select>` — funciona mesmo com `display:none`
2. **Trigger click**: clica no `.ui-selectonemenu-trigger` para abrir o panel
3. **Item click**: clica no `.ui-selectonemenu-item` com `:has-text()` ou JS evaluate
4. **JS setter**: `sel.selectedIndex = i` + dispatch `change` — fallback final

## Test Pages
- `tests/pagina-de-teste/primefaces/primefaces.html` — SelectOneMenu + AutoComplete (PrimeFaces simulado)
- `tests/pagina-de-teste/primefaces/jqueryui-selectmenu.html` — jQuery UI SelectMenu (CDN)
- `tests/pagina-de-teste/primefaces/kendo-dropdown.html` — Kendo DropDownList (CDN)
- `tests/pagina-de-teste/primefaces/angular-select.html` — Angular Material mat-select (ARIA roles)
- `tests/pagina-de-teste/primefaces/index.html` — Grid de navegação

## Curation Pipeline
- **Layer 0**: Recipe Auto-Healing. Catálogo JSONL de receitas geradas por LLM ou seed manual. Aplicado ANTES dos fallbacks (`_try_with_recipes()`). Suporta pre/post action evals, `wait_for_function`/`wait_for_selector`, `validate_eval`. Se a espera falha (timeout), a recipe NÃO é reportada como sucesso.
- **Layer 1**: Catálogo (custo zero, <50ms). Match exato por família + sintoma.
- **Layer 2**: Agente especialista (~200 tok). Selector/Timing/Input/Context/State Agents.
- **Layer 3a**: Evidence Collector (sem LLM). Estrutura DOM, screenshot, console, network, contexto.
- **Layer 3b**: LLM Healer (~500 tok). Prompt enxuto + payload estruturado do collector.
- **Layer 3c**: Curador Automático. Valida por execução, registra no catálogo (learned), stale detection 90d.

## Recipe Model (HealingRecipe)
- `trigger_action` / `trigger_framework` / `trigger_selector_pattern` / `trigger_symptom` — match conditions
- `pre_action_eval` — JS executado antes da ação (ex: dispatch blur)
- `post_action_wait_eval` — `wait_for_function()` polling até retornar truthy (ex: `document.querySelector(...)?.textContent.includes('155.144')`)
- `post_action_wait_selector` — `wait_for_selector()` alternativo
- `post_action_wait_timeout` — timeout da espera (default 15000ms)
- `post_action_eval` — JS executado após ação
- `validate_eval` — JS que retorna true/false; se falso, recipe reporta `⚠️ (action ok)`
- `priority` — ordenação de recipes candidatas

## Relevant Files
- `packages/core/testforge/core/recording/overlay.js` — overlay injection, event capture, selector generation
- `packages/core/testforge/core/recording/session.py` — recording session, overlay injection with fallback
- `packages/core/testforge/core/execution/runner.py` — test execution, click/fill fallbacks, radio `check()`, fill pre-check, jQuery autocomplete, JS_FIND, Angular Material datepicker fallback `_inject_button_has_text()`, recipe healing (`_try_with_recipes`, `_generate_recipe_from_failure`), LLM client with `.env` auto-load
- `packages/core/testforge/core/browser_config.py` — shared browser launch args and context options
- `packages/core/testforge/core/cli/record.py` — CLI flags `--name`, `--mode`
- `packages/core/testforge/core/script/selectors.py` — `generate_strategies()` selector generation
- `packages/core/testforge/core/models/step.py` — `RecordedStep` model
- `packages/core/testforge/core/script/builder.py` — script generation from steps
- `packages/core/testforge/core/execution/runner.py` — `_try_with_fallbacks()`
- `packages/core/testforge/core/script/serializer.py` — `generate_test_files()` with pytest-safe naming
- `packages/core/testforge/core/script/builder.py` — `ScriptBuilder` with `_selector_list()`, `_build_fallback_block()`
- `packages/core/testforge/core/healing/models.py` — `HealingRecipe` dataclass
- `packages/core/testforge/core/healing/storage.py` — `HealingCatalog` CRUD (add_recipe, match_recipes, update/delete)
- `packages/core/testforge/core/config/loader.py` — `load_llm_config()` with `.env` auto-load
- `packages/core/testforge/core/config/schema.py` — `LLMConfig` with `api_version`
- `README-EPIC1.md` — manual test guide

## Builder: Fallback Loop (2026-06-12)
- **Antes**: builder gerava `page.click(selector)` com seletor único via AST — sem fallback se falhasse
- **Agora**: gera `for/else/try/except/continue/break` loop tentando TODAS as estratégias do data.json:
  ```python
  for _sel in ['primary_sel', 'alt_sel_1', 'alt_sel_2']:
      try:
          page.click(_sel)
          break
      except Exception:
          continue
  else:
      raise AssertionError("click falhou: ...")
  ```
- **Ações com fallback**: `click`, `fill` (mais críticas). `select`, `upload` usam seletor único (`_SEL_LIST_[0]`) por terem fallback via runner.
- **Implementado em**: `ScriptBuilder._selector_list()`, `ScriptBuilder._build_fallback_block()`, templates `CLICK_TEMPLATE`, `FILL_TEMPLATE`
- **Templates via `ast.parse()`**: em vez de montar AST manual, usa `ast.parse(template.replace("_SEL_LIST_", repr(selectors)))` — mais simples e legível

## pytest Naming Conventions (2026-06-12)
- **Filename**: sempre prefixado com `test_` (via `serializer.py:_pytest_safe_name()` e `session.py`)
- **Class name**: sempre prefixado com `Test` (via `builder.py` no `ScriptBuilder.__init__()`)
- **pytest descobre**: por padrão, `test_*.py` e classes `Test*`. Os arquivos gerados agora seguem ambas as convenções.
- **`testforge run`**: não depende dessas convenções — usa o pipeline próprio (runner, healing, fallbacks)

## Angular Material Datepicker (overlay.js — 2026-06-12)
- `resolveElement()`: resolve `<span>` dentro de `.mat-calendar-body-cell-content` para o `<button>` pai (via `.closest('button')`). `.mat-calendar-period-button`, `.mat-calendar-previous-button`, `.mat-calendar-next-button` já são `<button>` — retornados diretamente.
- `detectFramework()`: adicionado `.mat-calendar`, `.mat-datepicker-content`, `.mat-datepicker-toggle` para detectar `pageTechnology='angular'` em datepickers.
- **Limitação conhecida**: calendário Angular Material tem 3 views (multi-year → year → month). Transição entre views pode causar race condition se o próximo click tentar encontrar o elemento antes da animação de transição completar.
- **Workaround runner**: `_inject_button_has_text()` — quando `span:has-text("FEV")` falha, tenta `button:has-text("FEV")` automaticamente. Ajuda recordings antigos que foram feitos antes do fix do resolveElement.

## Known Limitation: pytest vs testforge run
- **`testforge run`** usa o pipeline `runner.py` com `_try_with_fallbacks()` que inclui lógica framework-specific (PrimeFaces select, autocomplete, fill strategies, radio check)
- **`pytest`** executa o script Playwright puro — só tem o fallback loop de seletores do builder. Framework-specific healing NÃO está disponível.
- **Solução parcial**: o builder agora gera fallback de seletores (se um seletor falha, tenta o próximo). Mas não gera fallback framework-specific (ex: abrir panel do SelectOneMenu antes de clicar no item).

## Fill Strategy (runner.py)
1. **Pre-check**: ler `el.value` via JS — se já igual ao valor esperado, pular fill inteiro
2. **`page.fill()`**: tentativa rápida (15% do step_timeout) — falha se overlay/autocomplete bloquear
3. **Re-check**: se valor já OK após `page.fill()`, pular
4. **`pressSequentially`**: tentativa (50% do step_timeout) — digita caractere por caractere (delay 30ms) para triggerar listeners
5. **Native setter**: `Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set.call(el, v)` + `InputEvent` + `change` — fallback final

## Radio/Checkbox Strategy (runner.py)
1. **`locator.check()`**: Playwright nativo, idempotente, lida com visibilidade
2. **Label click**: `_click_with_dispatch` no `label:has-text()` — fallback se `check()` falhar
3. **`locator.click()`**: no input diretamente se label não marcou
4. **`el.checked = true` + `change`**: fallback JS final

