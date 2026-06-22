# Plano de Teste — Recorder Sensorial + Asserts

Validacao do Milestone 2: gravacao com comandos de teclado e 4 tipos de assert.

---

## Ambiente

```bash
# Terminal 1: Servir pagina de teste
cd tests/pagina-de-teste && python3 -m http.server 8080

# Terminal 2: TestForge
source .venv/bin/activate

# Rodar todos os testes automatizados
python -m pytest tests/ -v
```

---

## Paginas de Teste

| Pagina | URL | Descricao |
|--------|-----|-----------|
| `tests/pagina-de-teste/index.html` | `http://localhost:8080` | 78 taxonomias em 11 familias |
| `synthetic_lab/fake-react-bank-app/index.html` | `http://localhost:8765` | Fluxo CPF com mutacoes |

---

## TC-01: Fluxo Basico — Fill + Click + Assert Textual

**Objetivo:** Validar gravacao de fill, click e assert textual.

**Pre-condicao:** Servidor na porta 8080.

**Passos:**
1. `testforge record http://localhost:8080 --name tc-01`
2. Clicar no campo "Campo sem ID" (SEL-004) e digitar "teste"
3. Clicar no primeiro botao "Acao" (SEL-001)
4. `Shift+A` → clicar no elemento de resultado → selecionar "Texto"
5. `Shift+S` para finalizar

**Validar:**
- [ ] `recordings/tc-01/raw_events.jsonl` contem eventos `fill`, `click`
- [ ] `recordings/tc-01/steps.jsonl` contem step `assert` com `assert_type: textual`
- [ ] `expected_value` do assert contem o texto do elemento
- [ ] Screenshots gerados para cada evento
- [ ] DOM snapshots gerados

---

## TC-02: Asserts — Todos os 4 Tipos

**Objetivo:** Validar que os 4 tipos de assert funcionam.

**Pre-condicao:** Servidor na porta 8080.

**Passos:**
1. `testforge record http://localhost:8080 --name tc-02`
2. Clicar em qualquer elemento visivel
3. `Shift+A` → selecionar `📝 Texto`
4. `Shift+A` → clicar em checkbox → selecionar `🔘 Estado`
5. `Shift+A` → clicar em elemento visivel → selecionar `👁 Visivel`
6. `Shift+A` → clicar em elemento → selecionar `🤖 Auto`
7. `Shift+S`

**Validar:**
- [ ] `steps.jsonl` contem 4 steps com `action: assert`
- [ ] `assert_type`: `textual`, `estado`, `visivel`, `automatico`
- [ ] `textual`: `expected_value` = texto do elemento
- [ ] `estado`: `assert_state` = `enabled` ou `checked` ou `disabled`
- [ ] `visivel`: `expected_value` = `visible`
- [ ] `automatico`: `expected_value` = texto (igual textual)

---

## TC-03: Assert Estado — Checkbox Checked/Unchecked

**Objetivo:** Validar assert de estado em checkbox.

**Pre-condicao:** Servidor na porta 8765 (fake-react-bank-app).

**Passos:**
1. Navegar para pagina com checkbox (ou criar um checkbox simples)
2. `Shift+A` → clicar no checkbox → selecionar `🔘 Estado`
3. `assert_state` deve ser `checked` ou `unchecked`
4. `Shift+S`

**Validar:**
- [ ] `assert_type: estado`
- [ ] `assert_state` em (`checked`, `unchecked`)

---

## TC-04: Comandos de Teclado

**Objetivo:** Validar que Shift+P (pause) e Shift+S (stop) funcionam.

**Pre-condicao:** Servidor ativo.

**Passos:**
1. `testforge record http://localhost:8080 --name tc-04`
2. `Shift+P` → overlay deve mostrar "Pausado"
3. Clicar em um botao (nao deve capturar — esta pausado)
4. `Shift+P` → overlay volta para "Gravando"
5. Clicar em um botao (deve capturar)
6. `Shift+S` → gravacao finaliza

**Validar:**
- [ ] Durante pause, nenhum evento capturado
- [ ] Apos retomar, eventos capturados normalmente
- [ ] Stop finaliza e salva a sessao

---

## TC-05: Fake Bank — Fluxo Completo com Asserts

**Objetivo:** Testar o fluxo end-to-end com asserts no fake bank.

**Pre-condicao:** Servidor na porta 8765.

**Passos:**
1. `testforge record http://localhost:8765 --name tc-05`
2. Clicar no campo CPF e digitar "12345678900"
3. Clicar no botao "Pesquisar"
4. Esperar resultado aparecer
5. `Shift+A` → clicar na secao resultado → selecionar `📝 Texto`
6. `Shift+A` → clicar na secao resultado → selecionar `👁 Visivel`
7. `Shift+S`

**Validar:**
- [ ] `raw_events.jsonl`: navigation → fill → click
- [ ] `steps.jsonl`: assert textual + assert visivel
- [ ] `textual.expected_value` contem "CPF consultado"
- [ ] `visivel.expected_value` = "visible"
- [ ] `screenshots/`: pelo menos 3 screenshots
- [ ] `network_log.json`: presente

---

## TC-06: Modo Headless (Automatizado)

**Objetivo:** Validar que o recorder funciona em modo headless.

```bash
python -m pytest tests/test_recorder_e2e.py -v
```

**Validar:**
- [ ] `test_recorder_complete_flow` — 3 eventos + 2 asserts
- [ ] `test_assert_types_all` — 4 tipos de assert capturados

---

## Resumo de Cobertura

| Funcionalidade | TC-01 | TC-02 | TC-03 | TC-04 | TC-05 | TC-06 |
|---------------|-------|-------|-------|-------|-------|-------|
| Fill | ✓ | | | | ✓ | ✓ |
| Click | ✓ | | | ✓ | ✓ | ✓ |
| Assert Textual | ✓ | ✓ | | | ✓ | ✓ |
| Assert Estado | | ✓ | ✓ | | | ✓ |
| Assert Visivel | | ✓ | | | ✓ | ✓ |
| Assert Auto | | ✓ | | | | ✓ |
| Pause (Shift+P) | | | | ✓ | | |
| Stop (Shift+S) | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Headless | | | | | | ✓ |
| Screenshots | ✓ | | | | ✓ | ✓ |
| DOM Snapshots | ✓ | | | | ✓ | ✓ |
| Network Log | | | | | ✓ | ✓ |
