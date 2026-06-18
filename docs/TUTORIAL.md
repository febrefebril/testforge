# TestForge v1 — Tutorial de Teste Manual

Guia para testar cada componente e encontrar bugs.

---

## Pre-requisitos

```bash
# Terminal 1: Fake bank app
cd synthetic_lab/fake-react-bank-app
python3 -m http.server 8765

# Terminal 2: Pagina de teste ancestral
cd tests/pagina-de-teste
python3 -m http.server 8080

# Terminal 3: Ambiente TestForge
cd /home/febre/Projetos/testforge-v1
source .venv/bin/activate
```

---

## 1. Teste Rapido (1 comando)

```bash
python scripts/test_all.py
```

Verifica: unit tests + pipeline E2E completa.

---

## 2. Teste Manual — Modo Headed (vendo o navegador)

### 2.1 Demo Completa

```bash
python scripts/demo.py
```

O que observar:
- [ ] Navegador abre e fecha sozinho? (headless)
- [ ] raw_events.jsonl tem eventos `navigation`, `fill`, `click`?
- [ ] steps.jsonl tem asserts `textual` e `visivel`?
- [ ] Screenshots foram gerados?
- [ ] Script Python foi compilado em `semantic_tests/`?
- [ ] `evidence/DEMO-001/manifest.json` existe?

### 2.2 Stress Test (6 cenarios)

```bash
python scripts/stress_test.py
```

Cada cenario abre uma pagina nova. O que observar:
- [ ] 01: preenche campo sem ID → assert
- [ ] 02: clica botao fora do form → assert visivel
- [ ] 03: preenche CPF com mascara → assert
- [ ] 04: preenche combobox → assert
- [ ] 05: preenche campo upload → assert
- [ ] 06: checka checkbox → assert estado

---

## 3. Teste Componente por Componente

### 3.1 Recorder (Shift+P, Shift+S, Shift+A)

```bash
python -m testforge.cli.app record http://localhost:8765 --name meu-teste
```

Enquanto grava, teste os atalhos:
- [ ] `Shift+P` — overlay mostra "Pausado"?
- [ ] `Shift+P` de novo — volta "Gravando"?
- [ ] `Shift+A` — overlay muda para modo assert?
- [ ] Clica num elemento — aparece menu com 4 opcoes?
- [ ] Seleciona "Texto" — assert registrado?
- [ ] Seleciona "Estado" — assert_state preenchido?
- [ ] Seleciona "Visivel" — expected_value = "visible"?
- [ ] Seleciona "Auto" — igual textual?
- [ ] `Shift+S` — gravacao finaliza?

### 3.2 Artefatos Gerados

Apos gravar, verifique `recordings/meu-teste/`:
- [ ] `recording_metadata.json` — status "completed"?
- [ ] `raw_events.jsonl` — cada linha e JSON valido?
- [ ] `steps.jsonl` — asserts com `assert_type`?
- [ ] `screenshots/` — PNGs para cada evento?
- [ ] `dom_snapshots/` — HTML para cada evento?
- [ ] `network_log.json` — requests/responses?

### 3.3 Evidence

```bash
python -c "
from testforge.evidence import EvidenceStore
store = EvidenceStore()
print('Runs:', store.list_runs())
print('Pending:', store.list_pending_reviews())
"
```

- [ ] Lista todos os runs?
- [ ] Mostra runs com sensitive data alerts?

### 3.4 MIS + Compiler

```bash
python -c "
from testforge.semantic import RecordingNormalizer, PlaywrightCompiler
stc = RecordingNormalizer().normalize('recordings/DEMO-001', 'ST-TEST', 'app', 'http://localhost:8765')
print(f'Steps: {len(stc.steps)}')
for s in stc.steps:
    t = s.target
    cands = len(t.candidates) if t and t.candidates else 0
    print(f'  {s.action}: {cands} candidatos')
path = PlaywrightCompiler().compile(stc, 'semantic_tests/ST-TEST')
print(f'Script: {path}')
"
```

- [ ] Steps tem candidatos de locator?
- [ ] Script gerado compila (sem SyntaxError)?
- [ ] Script tem `for _sel in _sels` (fallback loop)?
- [ ] Script tem `expect(...).to_contain_text(...)`?

### 3.5 Rodar Script Gerado

```bash
python -m pytest semantic_tests/ST-TEST/test_st_test.py --base-url http://localhost:8765 -v
```

- [ ] Teste passa?
- [ ] Se falhar, o erro e claro?

### 3.6 Oracle

```bash
python -c "
from playwright.sync_api import sync_playwright
from testforge.oracle import OracleRunner
with sync_playwright() as pw:
    p = pw.chromium.launch().new_page()
    p.goto('http://localhost:8765')
    p.fill('[placeholder=\"000.000.000-00\"]', '999')
    p.click('button:has-text(\"Pesquisar\")')
    p.wait_for_timeout(500)
    o = OracleRunner(p)
    for r in o.run_all([
        {'type': 'visual_dom', 'selector': '#resultadoSection', 'expected': '999'},
        {'type': 'business_state', 'selector': '#cpfResultado', 'expected': '999'},
    ]):
        print(f'{r.status:12s} {r.oracle_type}: {r.message}')
"
```

- [ ] visual_dom: passed?
- [ ] business_state: passed?

### 3.7 PromotionGate

```bash
python -c "
from testforge.promotion import PromotionGate
from testforge.oracle import OracleResult
gate = PromotionGate()
# Cenario: oracles passam
d1 = gate.evaluate([OracleResult('v','passed'), OracleResult('b','passed')], {'screenshots':['x']})
print(f'Todos pass: {d1.state.value} (allowed={d1.allowed})')
# Cenario: oracle falha
d2 = gate.evaluate([OracleResult('v','failed')], {'screenshots':['x']})
print(f'Um falha: {d2.state.value} (allowed={d2.allowed}) blocks={d2.blocks}')
"
```

- [ ] Promove quando todos passam?
- [ ] Rejeita quando oracle falha?
- [ ] Bloqueios listados claramente?

### 3.8 Taxonomia

```bash
python -c "
from testforge.taxonomy import FailureClassifier
c = FailureClassifier()
tests = [
    'element not found',
    'element is obscured by overlay',
    'element is not enabled',
    'Timeout waiting for selector',
    'net::ERR_CONNECTION_REFUSED',
]
for t in tests:
    r = c.classify(t)
    print(f'{r.code:25s} {r.family.value:20s} recoverable={r.recoverable}')
"
```

- [ ] Todos os 11 codigos classificam corretamente?
- [ ] `recoverable` faz sentido para cada caso?

### 3.9 FallbackRunner

```bash
python -c "
from playwright.sync_api import sync_playwright
from testforge.runner import FallbackRunner
with sync_playwright() as pw:
    p = pw.chromium.launch().new_page()
    p.set_content('<input id=\"real\" placeholder=\"x\"><button id=\"btn\">Go</button>')
    fr = FallbackRunner(p)
    # Cenario 1: primeiro candidato falha, segundo funciona
    ok = fr.try_fill([{'selector':'#fake','score':0.9},{'selector':'#real','score':0.8}], 'hello')
    print(f'Fill fallback: {ok}')
    # Cenario 2: click funciona
    ok = fr.try_click([{'selector':'#btn','score':0.9}])
    print(f'Click: {ok}')
"
```

- [ ] Fallback tenta candidatos em ordem?
- [ ] Para no primeiro que funciona?
- [ ] Timeout de 2s por candidato?

### 3.10 Metricas

```bash
python -c "
from testforge.metrics import MetricsRepository
m = MetricsRepository()
m.record_run(healed=True, false_heal=False, oracle_passed=2)
m.record_run(healed=True, false_heal=True, oracle_passed=1)
m.record_run(healed=False, oracle_passed=3)
print(m.summary())
"
```

- [ ] precision = 50% (1 true, 1 false)?
- [ ] false_heal_rate = 50%?

---

## 4. Teste de Mutacoes (Synthetic Lab)

```bash
python -m pytest tests/test_mutations.py -v
```

Cada mutacao deve quebrar o teste base:
- [ ] `change_id` — ID regenerado, seletor por ID falha
- [ ] `change_accessible_name` — label muda, seletor por label falha
- [ ] `duplicate_button_text` — ambiguidade de seletor
- [ ] `overlay_blocks_click` — elemento coberto
- [ ] `disabled_button` — botao desabilitado

---

## 5. Teste na Pagina Ancestral (78 taxonomias)

```bash
# Servir pagina
cd tests/pagina-de-teste && python3 -m http.server 8080 &

# Abrir no navegador para inspecao manual
firefox http://localhost:8080
```

Secoes para testar manualmente:
- [ ] **SEL-001**: dois botoes identicos — recorder captura ambos?
- [ ] **SEL-004**: campo sem ID — gera candidato por name? placeholder?
- [ ] **SEL-006**: texto "Salvar" em span, nao button
- [ ] **SEL-009**: botoes com texto duplicado
- [ ] **CTX-001**: iframe — recorder captura eventos dentro?
- [ ] **CTX-003**: shadow DOM — recorder penetra?
- [ ] **INP-007**: mascara CPF — captura valor formatado final?
- [ ] **STA-004**: alert/confirm nativo — auto-accept funciona?
- [ ] **DOM-002**: lista reordenada — recorder captura apos DOM change?
- [ ] **DOM-005**: conteudo lazy/dinamico — espera antes de capturar?

---

## 6. Bugs Conhecidos para Procurar

| Area | O que procurar |
|------|---------------|
| **Recorder** | Eventos duplicados entre sessoes, `add_init_script` acumulando |
| **Compiler** | Aspas em seletores quebrando sintaxe Python |
| **Fallback** | Candidato `has-text` resolvendo para elemento errado |
| **Oracle** | Falso positivo quando elemento existe mas valor errado |
| **Gate** | Promocao com evidencia incompleta |
| **MIS** | Candidato com score > 1.0 ou < 0.0 |

---

## 7. Validação de Intenção (Sprints 3-7)

### 7.1 Field Snapshots + Setter Hooks

O recorder agora captura snapshots periódicos de todos os campos da página
a cada 1s, além de interceptar setters de `value` via JS.

```bash
# Após gravar, verifique:
ls recordings/REC-*/field_snapshots.jsonl   # snapshots periódicos
ls recordings/REC-*/value_mutations.jsonl   # setters interceptados
```

- [ ] `field_snapshots.jsonl` tem linhas com `fingerprint`, `tag`, `value`, `checked`, `focused`?
- [ ] `value_mutations.jsonl` tem mutations de `HTMLInputElement.value`?
- [ ] Final state salvo em sessionStorage ao parar?

### 7.2 Intent Reconstructor

Reconstroi intenção do usuário a partir de 3 estratégias:

1. **snapshot_diff**: diff entre snapshots consecutivos
2. **form_values**: valores do form no submit
3. **network_payload**: payload de POST capturado

```bash
python -c "
from testforge.semantic import RecordingNormalizer
stc = RecordingNormalizer().normalize('recordings/REC-XXXX', 'ST-TEST', 'web', 'http://localhost')
for k, v in stc.field_values.items():
    src = getattr(v, 'source', '?')
    val = getattr(v, 'value', '?')
    print(f'  {k}: {val} (source={src})')
"
```

- [ ] Campos com source = snapshot_diff / form_values / network_payload?
- [ ] Nenhum campo missing após reconstructor?

### 7.3 RecordingReadinessGate

Avalia 5 critérios antes de marcar gravação como pronta:

```bash
testforge record http://localhost:8765 --name "meu-teste" --validate-before-ready
```

- [ ] Completude: todos campos resolvidos?
- [ ] Steps: todos passaram?
- [ ] Blocking: steps bloqueantes resolvidos?
- [ ] User-supplied: valores informados validados?
- [ ] Healing oracles: passaram?

Verifique o relatório:
```bash
cat recordings/meu-teste/readiness/readiness_report.md
```

### 7.4 Modo Piloto

```bash
testforge record http://localhost:8765 --name "meu-teste" --pilot-mode
```

- [ ] Valida automaticamente após gravar?
- [ ] Se campo faltando, CLI pergunta valor?
- [ ] Status final é ready_for_team se tudo OK?

### 7.5 Intent Lab — Páginas de Teste

Sirva as páginas e teste cada fluxo:

```bash
cd tests/intent_lab && python -m http.server 8080 &
```

| Página | URL | O que testar |
|--------|-----|-------------|
| ready-flow | `/pages/ready-flow/` | Fluxo feliz completo |
| missing-fill-gap | `/pages/missing-fill-gap/` | Gap de digitação |
| prevent-default-input | `/pages/prevent-default-input/` | preventDefault |
| currency-mask | `/pages/currency-mask/` | Máscara monetária |
| native-select | `/pages/native-select/` | Select nativo |
| custom-combobox | `/pages/custom-combobox/` | role=combobox |
| contenteditable | `/pages/contenteditable/` | Editor rico |
| network-payload-only | `/pages/network-payload-only/` | POST via form |
| iframe-field | `/pages/iframe-field/` | Iframe same-origin |
| shadow-dom-field | `/pages/shadow-dom-field/` | Shadow DOM |
| upload-file | `/pages/upload-file/` | Input type=file |
| two-similar-fields | `/pages/two-similar-fields/` | Campos parecidos |
| dynamic-result | `/pages/dynamic-result/` | Resultado dinâmico |
| blocking-step-failure | `/pages/blocking-step-failure/` | Falha em cascata |

Para cada página:
- [ ] Gravação finaliza sem crash?
- [ ] Status é compatível com o fluxo (READY / REVIEW / FAIL)?
- [ ] Relatório de readiness é compreensível?

## 8. Relatório Consolidado do Piloto (Sprint 8)

```bash
# Após ter várias gravações com --validate-before-ready:
testforge pilot-report
```

- [ ] `reports/pilot_readiness_report.md` gerado?
- [ ] Mostra total de gravações, prontas, incompletas?
- [ ] Lista falhas por categoria?
- [ ] Ajuda a priorizar correções?

## 9. Execução Incremental (Sprint 5+)

```bash
testforge run-incremental semantic_tests/ST-meu-teste/test_st_meu_teste.py
```

- [ ] Passos executam um a um?
- [ ] Pré-condições e pós-condições são avaliadas?
- [ ] Healing é tentado por step?
- [ ] Relatório final mostra resumo por step?

## 10. Testes Automatizados

```bash
# Todos os testes (194)
python -m pytest tests/ -v

# Apenas Sprints 3-8
python -m pytest tests/test_sprint3_field_snapshots.py \
                 tests/test_sprint4_intent_reconstructor.py \
                 tests/test_sprint5_readiness_gate.py \
                 tests/intent_lab/ \
                 tests/test_sprint7_cli_integration.py \
                 tests/test_sprint8_pilot_metrics.py -v
```

---

*Tutorial criado em 2026-06-13. Atualizado em 2026-06-18 (Sprints 3-8). Execute `python -m pytest tests/ -v` para validacao.*
