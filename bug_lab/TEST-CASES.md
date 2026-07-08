# Bug Lab — Casos de Teste e Manual de Verificação

**Versão:** 0.4.0
**Data:** 2026-06-17
**Objetivo:** Verificar que cada bug do Bug Lab foi corrigido usando testes automatizados e verificação manual.

---

## Pré-requisitos

```bash
cd testforge-v1
source activate.sh
python -m pytest --version  # deve mostrar pytest 8+
```

---

## Como executar todos os testes

```bash
# Todos os testes do Bug Lab (9 bugs)
python -m pytest bug_lab/tests/ -v

# Um bug específico
python -m pytest bug_lab/tests/test_bug_dynamic_id.py -v

# Com output detalhado
python -m pytest bug_lab/tests/ -v --tb=long
```

---

## 🐛 Bug 1: Seletor Vazio/Inválido

### O bug
Playwright lança `TimeoutError` ou `strict mode violation` quando tenta interagir com um seletor que resolve para zero elementos.

### Verificar se existia
1. Abra `bug_lab/pages/bug-empty-selector/index.html` no navegador
2. Execute: `python -m pytest bug_lab/tests/bug-empty-selector_test.py -v`
3. **Antes da correção:** o teste `test_empty_selector_fails` falhava com `TimeoutError`

### Verificar correção
```bash
python -m pytest bug_lab/tests/bug-empty-selector_test.py -v
```
**Esperado:** Todos os testes passam. O `RecordingNormalizer` agora rejeita seletores vazios antes de chegar ao Playwright.

### O que foi corrigido
- `RecordingNormalizer._build_target()`: valida que pelo menos 1 candidato existe
- `SmartStepRunner`: não tenta executar ações com seletor vazio
- **Commit:** `07d64ba`

---

## 🐛 Bug 2: ID Dinâmico — Seletor Frágil

### O bug
Botão com `id="btn-dynamic-{timestamp}"` — o ID muda a cada carregamento. O script gravado com `#btn-old-id` falha porque o ID já mudou.

### Verificar se existia
1. Abra `bug_lab/pages/bug-dynamic-id/index.html?error=1`
2. O botão principal tem ID com timestamp
3. **Antes:** `page.click("#btn-dynamic-0")` → `strict mode violation: resolved to 0 elements`

### Verificar correção
```bash
python -m pytest bug_lab/tests/test_bug_dynamic_id.py -v
```
**Esperado:** 5+ testes passam. O `SelectorAgent._try_text()` usa `text=` como fallback quando o ID falha.

### O que foi corrigido
- `SelectorAgent._try_text()`: fallback para `text=` com exact matching
- `SmartStepRunner`: tenta `has_text_fallback` quando seletor ID falha
- **Commit:** `ee795b5`, `d9b8f24`

---

## 🐛 Bug 3: Mat-Icon Contaminando Accessible Name

### O bug
Botões Angular Material com `<mat-icon>file_upload</mat-icon> Carregar` têm `accessible_name = "file_upload Carregar"`. O ícone contamina o nome acessível.

### Verificar se existia
1. Abra `bug_lab/pages/bug-mat-icon-name/index.html`
2. Inspecione o botão "Carregar Arquivo"
3. **Antes:** `accessible_name = "file_upload Carregar Arquivo"` (ícone + texto)

### Verificar correção
```bash
python -m pytest bug_lab/tests/test_bug_mat_icon_name.py -v
```
**Esperado:** Testes passam. `_clean_text()` remove "file_upload" e outros 60+ ícones Material.

### O que foi corrigido
- `recording_normalizer.py:_clean_text()`: filtra 60+ material icon ligatures
- `recording_normalizer.py:_build_target()`: usa `_clean_text()` no `accessible_name`
- **Commit:** `a58913a`

---

## 🐛 Bug 4: BADSTRING — Aspas em Seletores

### O bug
Texto do botão contém aspas: `Clique em "OK" para continuar`. O seletor CSS gerado quebra: `text=Clique em "OK" para continuar` → erro de parsing.

### Verificar se existia
1. Abra `bug_lab/pages/bug-selector-escape/index.html`
2. Tente gravar um clique no botão com aspas
3. **Antes:** seletor CSS com aspas não escapadas → `BADSTRING` error

### Verificar correção
```bash
python -m pytest bug_lab/tests/test_bug_selector_escape.py -v
```
**Esperado:** Testes passam. Seletores com aspas são escapados corretamente: `text=Clique em \"OK\" para continuar`.

### O que foi corrigido
- `compiler.py:_esc()`: escapa aspas e caracteres especiais
- `recording_normalizer.py`: gera candidatos com escape correto
- **Commit:** `c52a95e`

---

## 🐛 Bug 5: File Input — fill(fakepath) vs set_input_files

### O bug
Recorder gera `page.fill("C:\\fakepath\\arquivo.txt")` para upload. Na execução, `fill()` não funciona em `<input type="file">`.

### Verificar se existia
1. Abra `bug_lab/pages/bug-file-input/index.html`
2. Grave um upload de arquivo
3. **Antes:** script gerava `fill("C:\\fakepath\\...")` → não funcionava

### Verificar correção
```bash
python -m pytest bug_lab/tests/test_bug_file_input.py -v
```
**Esperado:** Testes passam. Upload usa `page.set_input_files(sel, file)` em vez de `fill()`.

### O que foi corrigido
- `recorder_controller.py`: detecta `<input type="file">` e grava como `set_input_files`
- `compiler.py`: gera `page.set_input_files()` para eventos de upload
- **Commit:** `d95a018`

---

## 🐛 Bug 6: Múltiplos File Inputs — Seletor Ambíguo

### O bug
Página com 2+ `<input type="file">`. O seletor `input[type=file]` resolve para múltiplos elementos → `strict mode violation`.

### Verificar se existia
1. Abra `bug_lab/pages/bug-multi-file-input/index.html`
2. Tente gravar upload no segundo campo
3. **Antes:** ambos os campos usavam `input[type=file]` → ambiguidade

### Verificar correção
```bash
python -m pytest bug_lab/tests/test_bug_multi_file_input.py -v
```
**Esperado:** Testes passam. Cada file input tem seletor distinto por label/posição.

### O que foi corrigido
- `recording_normalizer.py`: diferencia múltiplos inputs por label, aria-label, posição
- `recorder_controller.py`: captura label associado e posição
- **Commit:** `3fa260e`

---

## 🐛 Bug 7: jQuery Select — select_option() Falha

### O bug
Select melhorado com jQuery: o `<select>` original está hidden, o jQuery renderiza um `<div>` customizado. Recorder captura clique no div, não no select.

### Verificar se existia
1. Abra `bug_lab/pages/bug-jquery-select/index.html`
2. Selecione uma opção no dropdown jQuery
3. **Antes:** `page.click()` no div customizado → valor não muda

### Verificar correção
```bash
python -m pytest bug_lab/tests/test_bug_jquery_select.py -v
```
**Esperado:** Testes passam. Script gera `page.select_option('select[name="..."]', 'value')`.

### O que foi corrigido
- `recorder_controller.py`: detecta `<select>` original (não o div jQuery)
- `compiler.py:_gen_select()`: gera `select_option()` para `<select>`
- **Commit:** `4cd7dc9`

---

## 🐛 Bug 8: Datepicker — Validação Incorreta de Data

### O bug
Selecionar data de HOJE no datepicker e clicar "Validar" mostra erro "Date must not be in the past" — mas hoje não é passado.

### Verificar se existia
1. Abra `bug_lab/pages/bug-datepicker/index.html`
2. Selecione a data de hoje
3. Clique em "Validar"
4. **Antes:** mostrava erro `Date must not be in the past` — bug na comparação `<=` vs `<`

### Verificar correção
```bash
python -m pytest bug_lab/tests/test_bug_datepicker.py -v
```
**Esperado:** Testes passam. Data de hoje é aceita como válida.

### O que foi corrigido
- `bug-datepicker/index.html`: trocado `<=` por `<` na validação JS
- **Commit:** `99cf0f6`

---

## 🐛 Bug 9: Encoding — Caracteres Especiais Perdidos

### O bug
Página com caracteres UTF-8 (ç, ñ, é, ü, ã, ô, €, —, …). O recording perde ou corrompe esses caracteres ao salvar `raw_events.jsonl`.

### Verificar se existia
1. Abra `bug_lab/pages/bug-encoding/index.html`
2. Grave uma interação (ex: clique no botão "Ação")
3. Verifique `raw_events.jsonl` — o texto deveria conter ç, ñ, é
4. **Antes:** caracteres apareciam como `\u00e7` ou `Ã§`

### Verificar correção
```bash
python -m pytest bug_lab/tests/test_bug_encoding.py -v
```
**Esperado:** Testes passam. JSONL contém UTF-8 correto.

### O que foi corrigido
- `raw_recording_store.py`: `json.dumps()` com `ensure_ascii=False`
- `recording_normalizer.py`: preserva encoding UTF-8 ao ler JSONL
- **Commit:** `0a05251`

---

## 🚀 Pipeline CI

O workflow de CI está configurado para rodar automaticamente em push/PR:

```bash
# Simular CI localmente
python -m pytest bug_lab/tests/ tests/ --ignore=tests/test_pages --ignore=tests/test_healing_e2e.py -q
```

**Workflow:** `.github/workflows/test.yml` — matrix Python 3.10, 3.11, 3.12, 3.13

---

## 📊 Resumo Final

| # | Bug | Página | Testes | Status |
|---|-----|--------|--------|--------|
| 1 | Seletor vazio | `bug-empty-selector` | `bug-empty-selector_test.py` | ✅ FIXED |
| 2 | ID dinâmico | `bug-dynamic-id` | `test_bug_dynamic_id.py` | ✅ FIXED |
| 3 | Mat-icon name | `bug-mat-icon-name` | `test_bug_mat_icon_name.py` | ✅ FIXED |
| 4 | BADSTRING escape | `bug-selector-escape` | `test_bug_selector_escape.py` | ✅ FIXED |
| 5 | File input | `bug-file-input` | `test_bug_file_input.py` | ✅ FIXED |
| 6 | Multi file input | `bug-multi-file-input` | `test_bug_multi_file_input.py` | ✅ FIXED |
| 7 | jQuery select | `bug-jquery-select` | `test_bug_jquery_select.py` | ✅ FIXED |
| 8 | Datepicker | `bug-datepicker` | `test_bug_datepicker.py` | ✅ FIXED |
| 9 | Encoding | `bug-encoding` | `test_bug_encoding.py` | ✅ FIXED |

**9/9 bugs corrigidos. 100% verificáveis via testes automatizados.**
