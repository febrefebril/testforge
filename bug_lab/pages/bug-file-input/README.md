# BUG: File Input — `set_input_files` vs `fill(fakepath)`

## Symptom
Playwright recorder gera `fill("C:\\fakepath\\arquivo.txt")` para upload de arquivo.
Na reprodução, o `fill()` falha ou não faz nada — arquivo nunca é enviado.

## Cause
1. Navegadores bloqueiam atribuição programática de `.value` em `<input type="file">` (segurança).
2. Quando usuário seleciona arquivo, navegador mostra `C:\fakepath\filename` como valor (privacidade).
3. Recorder captura esse valor e gera `fill()` — que não funciona com file inputs.

## Reproduction
```bash
# 1. Iniciar servidor de teste
python -m http.server 8700 -d bug_lab/pages &

# 2. Rodar testes
pytest bug_lab/tests/test_bug_file_input.py -v
```

## Validation
- ✅ `set_input_files()` funciona — arquivo é carregado, onchange dispara
- ❌ `fill("C:\\fakepath\\...")` não funciona — navegador bloqueia
- ✅ Após `fill()` falhar, `set_input_files()` ainda funciona
- ✅ `input.value` contém `fakepath` por privacidade (raiz do bug)

## Fix
No compilador (`src/testforge/semantic/compiler.py`):
- Detectar `<input type="file">` no evento de gravação
- Emitir `locator.set_input_files("path/to/fixture")` ao invés de `locator.fill(...)`
- Remover cliques redundantes que apenas abrem diálogo nativo de upload

## Fixture
`bug_lab/fixtures/test-upload.txt` — arquivo simples para testes de upload.
