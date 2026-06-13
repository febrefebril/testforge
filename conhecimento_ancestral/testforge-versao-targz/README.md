# TestForge 🔬

**AI-powered test recorder, generator, self-healer and optimizer.**

> Record user interactions → Generate pytest code → Self-heal broken selectors → Optimize performance

---

## Architecture

```
User Interaction
      │
      ▼
┌─────────────────────────────────────────────────────────────┐
│ PHASE 1 — Recording                                         │
│  ├── Playwright Codegen (primary)                           │
│  ├── JS Injection Recorder (fallback / legacy stacks)       │
│  └── Stack Fingerprinting (React, Vue, jQuery, iframes...)  │
└──────────────────────────┬──────────────────────────────────┘
                           │ recording.json
                           ▼
┌─────────────────────────────────────────────────────────────┐
│ PHASE 2 — Test Generation (Azure GPT-4o-mini)               │
│  ├── Multi-selector generation (5 selectors/element)        │
│  ├── Smart wait injection                                    │
│  └── Assert inference from name + description + last step   │
└──────────────────────────┬──────────────────────────────────┘
                           │ tests/generated/test_*.py
                           ▼
┌─────────────────────────────────────────────────────────────┐
│ PHASE 3 — Self-Healing                                      │
│  ├── Run pytest, detect selector failures                   │
│  ├── Try 4 local fallback selectors per failure             │
│  ├── LLM heal: screenshot + DOM → new selectors             │
│  └── Patch test file in place, re-run                       │
└──────────────────────────┬──────────────────────────────────┘
                           │ tests/generated/test_*.py (patched)
                           ▼
┌─────────────────────────────────────────────────────────────┐
│ PHASE 4 — Performance Optimization                          │
│  ├── Inject timing wrappers into wait calls                 │
│  ├── Profile real wait durations                            │
│  ├── LLM suggests timeout reductions                        │
│  └── Validate + save to tests/optimized/                    │
└─────────────────────────────────────────────────────────────┘
```

---

## Installation

```bash
# 1. Clone / copy the testforge/ directory
cd testforge

# 2. Create virtual environment
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Install Playwright browsers
playwright install chromium

# 5. Configure Azure OpenAI
cp .env.example .env
# Edit .env with your Azure credentials
```

### `.env` file

```env
AZURE_OPENAI_KEY=your_azure_api_key_here
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com
AZURE_OPENAI_DEPLOYMENT=gpt-4o-mini
AZURE_OPENAI_API_VERSION=2024-02-01
```

---

## Usage

### Full pipeline (recommended)

```bash
python testforge.py run-all \
  --url https://app.example.com/login \
  --name "Login com usuário inválido" \
  --assert "A mensagem 'Usuário ou senha inválidos' deve aparecer" \
  --description "Fluxo negativo de autenticação" \
  --tags auth,negativo
```

---

### Individual phases

#### Phase 1 — Record

```bash
# Playwright Codegen (opens browser, record, close to finish)
python testforge.py record \
  --url https://app.example.com/checkout \
  --name "Checkout sem endereço" \
  --assert "Erro de endereço obrigatório deve aparecer" \
  --recorder codegen

# JS Injection recorder (for legacy/jQuery apps, iframes)
python testforge.py record \
  --url https://legacy.intranet.com/form \
  --name "Envio de formulário jQuery" \
  --assert "Mensagem de sucesso deve aparecer" \
  --recorder js
```

#### Phase 2 — Generate test

```bash
python testforge.py generate \
  --recording recordings/login_invalido_20240101_120000.json
```

#### Phase 3 — Self-heal

```bash
python testforge.py heal \
  --test tests/generated/test_login_invalido.py \
  --max-cycles 5
```

#### Phase 4 — Optimize

```bash
python testforge.py optimize \
  --test tests/generated/test_login_invalido.py
```

---

### Inspect recordings

```bash
# List all recordings
python testforge.py list --recordings

# Show details + events of a recording
python testforge.py show-recording recordings/login_invalido.json --events
```

---

## Supported Stacks

| Stack | Recorder | Notes |
|-------|----------|-------|
| React / Next.js | Codegen + JS | Full support, SPA navigation tracked |
| Vue 2/3 / Nuxt | Codegen + JS | Vue devtools fingerprint |
| Angular / AngularJS | Codegen + JS | ng-version detection |
| Svelte | Codegen + JS | Class-based fingerprint |
| jQuery / AJAX | JS injection | Extra waits added automatically |
| Django / Flask templates | Codegen + JS | SSR, no extra config |
| JSP / Thymeleaf | Codegen + JS | Java backend SSR |
| ASP.NET Razor | Codegen + JS | Full support |
| Shadow DOM | JS injection | shadow host selector generated |
| iframes | JS injection | Injection into each frame |

---

## Project Structure

```
testforge/
├── testforge.py              # CLI entry point
├── config.yaml               # Global settings
├── .env                      # Azure OpenAI credentials
├── conftest.py               # pytest shared fixtures
├── requirements.txt
│
├── recorder/
│   ├── codegen_recorder.py   # Playwright codegen subprocess
│   ├── js_recorder.py        # Browser injection recorder
│   ├── stack_detector.py     # Framework fingerprinting
│   └── injection.js          # Multi-selector event capture script
│
├── generator/
│   ├── llm_client.py         # Azure OpenAI client
│   ├── test_generator.py     # Prompt builder + code generator
│   └── prompts/
│       ├── system_prompt.txt
│       └── assert_strategies.txt
│
├── healer/
│   ├── runner.py             # pytest runner + heal orchestration
│   ├── self_healer.py        # Local fallback + LLM heal logic
│   └── patcher.py            # In-place AST/regex file patching
│
├── optimizer/
│   ├── profiler.py           # Timing injection + measurement
│   └── tuner.py              # LLM optimization + validation
│
├── recording_manager.py      # Save/load/list recordings
│
├── recordings/               # *.json recording files
├── tests/
│   ├── generated/            # Phase 2 output
│   └── optimized/            # Phase 4 output
└── reports/                  # Healing + performance reports
```

---

## Assert Strategies

TestForge combines **4 signals** to generate the final assertion:

1. **`--name`** — test name, e.g. "Login com usuário inválido"
2. **`--description`** — free-text description
3. **`--assert`** — explicit hint (highest priority), e.g. "mensagem de erro deve aparecer"
4. **Last recorded action** — last click/submit event + its DOM context

The LLM also applies pattern matching:
- Form submit → check for error/success message
- Navigation → check URL or page title  
- Modal trigger → check dialog visibility
- Table update → check row count

---

## Self-Healing Strategy

When a selector fails during test execution:

```
Failure detected
     │
     ▼
Try 4 other selectors (local fallback)
  data_testid → aria → text → css → xpath
     │
     ├── Found? → Patch file, continue
     │
     └── Not found? → LLM Heal
          ├── Capture screenshot
          ├── Extract DOM snippet
          ├── Ask GPT-4o-mini for new selectors
          ├── Try each suggestion
          ├── Found? → Patch file, continue
          └── Not found? → Mark as failed
```

---

## Configuration (`config.yaml`)

```yaml
healing:
  max_heal_attempts: 5        # LLM heal retries per selector
  llm_heal_enabled: true      # Disable for offline use

optimization:
  min_timeout_ms: 500         # Never reduce timeouts below this
  max_timeout_reduction_pct: 70  # Cap reduction at 70%

selectors:
  priority_order:             # Order to try selectors
    - data_testid
    - aria
    - text
    - css
    - xpath
```

---

## Reports

### Healing report (`reports/healing_report_<test>.json`)
```json
{
  "final_status": "PASS",
  "healed_selectors": 2,
  "failed_heals": 0,
  "cycles": [...]
}
```

### Performance report (`reports/performance_report_<test>.json`)
```json
{
  "original_total_wait_ms": 8400,
  "estimated_saving_ms": 3200,
  "reduction_pct": 38.1,
  "optimizations_applied": [...]
}
```

---

## Tips

- Always provide `--assert` with specific UI text for best results
- Use `--recorder js` for legacy apps with iframes or jQuery
- Add `data-testid` attributes to your components for most reliable selectors
- The `run-all` command saves all intermediate artifacts — nothing is lost if a phase fails
