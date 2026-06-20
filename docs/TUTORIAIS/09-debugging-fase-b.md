# Fase B — Runbook de Debugging

Guia operacional para depurar problemas no pipeline de reconstrução de intenção
(IntentReconstructor, RecordingNormalizer, SemanticTestCase).

---

## 1. Como debugar field_values ausentes

### Sintoma

Após `testforge compile <gravação> --check`, o relatório indica campos sem valor:

```
REVIEW  campo: cpf — sem valor (blind_spot)
REVIEW  campo: renda — sem valor (blind_spot)
```

### Diagnóstico passo a passo

**1. Verifique quais arquivos foram gerados pela gravação:**

```bash
ls runs/<nome-da-gravação>/
# Esperado: raw_events.jsonl, field_snapshots.jsonl, value_mutations.jsonl,
#           network_log.json, final_state_snapshot.json
```

Se algum arquivo estiver ausente, a fonte correspondente não estará disponível.

**2. Inspecione os raw_events:**

```bash
python -c "
import json
with open('runs/<gravação>/raw_events.jsonl') as f:
    for line in f:
        ev = json.loads(line)
        if ev.get('type') == 'fill':
            print(ev.get('target', {}).get('name'), '->', ev.get('value'))
"
```

**3. Verifique field_snapshots para o campo:**

```bash
python -c "
import json
with open('runs/<gravação>/field_snapshots.jsonl') as f:
    for line in f:
        batch = json.loads(line)
        for snap in batch.get('snapshots', [batch]):
            ids = snap.get('identifiers', {})
            if 'cpf' in (ids.get('name', '') + ids.get('id', '')).lower():
                print(snap.get('timestamp'), '->', snap.get('value'))
"
```

Se aparecer apenas uma linha (sem transição), o snapshot_diff não vai disparar.

**4. Verifique network_log para o campo:**

```bash
python -c "
import json
with open('runs/<gravação>/network_log.json') as f:
    entries = json.load(f)
for e in entries:
    if e.get('method') in ('POST', 'PUT', 'PATCH') and e.get('post_data'):
        print(e.get('url'))
        print(e.get('post_data')[:200])
"
```

**5. Rode o reconstructor em modo debug:**

```bash
python -c "
from testforge.semantic.intent_reconstructor import IntentReconstructor
from testforge.semantic.model import SemanticAction, SemanticTarget

reconstructor = IntentReconstructor()
# Substitua pelo caminho real
entries = reconstructor.reconstruct_all('runs/<gravação>', steps=[])
for e in entries:
    print(e['field_key'], '->', e['value'], '(', e['source'], ')')
"
```

### Causas comuns e soluções

| Causa | Sintoma | Solução |
|-------|---------|---------|
| Campo com mask JS — valor nunca foi capturado pelo input event | Nenhum snapshot com valor preenchido | Use `--data` e preencha `test_data.json` manualmente |
| Campo em iframe | raw_events não registra o campo | Verifique `field_snapshots.jsonl` — recorder captura via polling |
| Campo preenchido programaticamente (JS `element.value = ...`) | Ausente nos snapshots | Verifique `value_mutations.jsonl` |
| POST sem body (fetch sem `Content-Type: application/x-www-form-urlencoded`) | network_payload vazio | O backend pode usar JSON — verifique `post_data` no network_log |

---

## 2. Como inspecionar blind_spots em uma SemanticTestCase

### O que são blind_spots

Campos que o recorder detectou (via DOM polling ou evento) mas não conseguiu
capturar o valor. Ficam listados em `SemanticTestCase.blind_spots`.

### Inspecionar via CLI

```bash
testforge compile <gravação> --check
# Exibe: campos resolvidos, campos com blind_spot, fonte por campo
```

### Inspecionar via Python

```bash
python -c "
from testforge.semantic.recording_normalizer import RecordingNormalizer

normalizer = RecordingNormalizer()
stc = normalizer.normalize('runs/<gravação>', test_id='ST-DEBUG')

print('=== field_values ===')
for k, fv in stc.field_values.items():
    print(f'  {k}: {fv.value!r}  (fonte: {fv.source})')

print()
print('=== blind_spots ===')
for bs in stc.blind_spots:
    print(f'  {bs}')
"
```

### Estrutura de um blind_spot

```python
{
    "field_key": "cpf",
    "step_index": 2,
    "reason": "no_value_captured",
    "identifiers": {"name": "cpf", "id": "input_cpf", "label": "CPF"}
}
```

### Resolvendo blind_spots

Opção A — fornecer via `--data`:

```bash
testforge compile <gravação> --data
# Editar: semantic_tests/ST-<gravação>/test_data.json
# Adicionar:  "cpf": "123.456.789-00"
```

Opção B — rodar o gravador novamente com formulário mais lento para o
polling conseguir capturar o valor antes do submit.

Opção C — inspecionar `final_state_snapshot.json` — o reconstructor já
tenta esse fallback automaticamente.

---

## 3. Como usar --data para missing_fill

O comando `--data` extrai todos os valores resolvidos para um JSON externo
e cria placeholders para campos com blind_spot.

### Fluxo

```bash
# 1. Compilar e extrair massa de dados
testforge compile meu-fluxo --data

# 2. Arquivo gerado:
cat semantic_tests/ST-meu-fluxo/test_data.json
# {
#   "fields": {
#     "cpf": "123.456.789-00",
#     "renda": "__MISSING__"    ← blind_spot
#   },
#   "sensitive_alerts": []
# }

# 3. Preencher os valores ausentes
vim semantic_tests/ST-meu-fluxo/test_data.json
# Substituir "__MISSING__" pelos valores reais

# 4. Executar — o runner usa os valores do JSON
testforge run semantic_tests/ST-meu-fluxo/test_st_meu_fluxo.py
```

### Alterar valor sem recompilar

```bash
vim semantic_tests/ST-meu-fluxo/test_data.json
# Alterar "cpf": "999.888.777-66"
testforge run semantic_tests/ST-meu-fluxo/test_st_meu_fluxo.py
# Usa o novo CPF sem precisar regravar
```

---

## 4. Exemplos de comandos

### Compilar e verificar completude

```bash
testforge compile simulador-credito --check
# Saída:
# ✓ campo: cpf            (form_values, confidence 1.0)
# ✓ campo: renda          (network_payload, confidence 0.7)
# ✗ campo: data_nascimento (blind_spot — não resolvido)
```

### Verificar completude sem compilar

```bash
# Inspecionar diretamente o SemanticTestCase
python -c "
from testforge.semantic.recording_normalizer import RecordingNormalizer
from testforge.validation.intent_completeness import IntentCompletenessChecker

normalizer = RecordingNormalizer()
stc = normalizer.normalize('runs/simulador-credito', test_id='ST-DEBUG')
checker = IntentCompletenessChecker()
result = checker.check(stc)
print('Completude:', result.completeness_score)
print('Campos ausentes:', result.missing_fields)
"
```

### Gravar com validação automática

```bash
testforge record http://localhost:8765 --name simulador --validate-before-ready
# Ao final: pergunta valores para campos com blind_spot
# Salva readiness_report.md na pasta da gravação
```

### Ver relatório de readiness

```bash
cat runs/simulador-credito/readiness_report.md
```

---

## 5. Troubleshooting: campo com máscara não capturado

### Problema

Campos com máscara JavaScript (CPF, CNPJ, telefone, moeda) frequentemente
têm o value mascarado ou vazio nos eventos input/change. O recorder pode
capturar `"123"` em vez de `"123.456.789-00"`.

### Por que acontece

1. A máscara intercepta o evento e chama `event.preventDefault()`
2. O JavaScript define `element.value` diretamente (não dispara InputEvent)
3. O valor formatado só aparece no estado DOM após a máscara processar

### Estratégias do IntentReconstructor

| Estratégia | Como captura | Confiança |
|------------|-------------|-----------|
| `setter_hook` | Intercepta `Object.defineProperty(input, 'value', ...)` | Alta |
| `snapshot_diff` | Polling periódico do DOM — compara valores entre snapshots | Alta |
| `network_payload` | Corpo do POST/PUT — valor já formatado pelo backend | Média |
| `final_state` | Dump do estado final — valor já preenchido | Média |

### Diagnóstico

```bash
# Verificar se value_mutations.jsonl capturou o campo mascarado
python -c "
import json
with open('runs/<gravação>/value_mutations.jsonl') as f:
    for line in f:
        m = json.loads(line)
        print(m.get('name') or m.get('fingerprint'), '->', m.get('new_value'))
"
```

Se `setter_hook` não capturou e `snapshot_diff` também não (campo preenchido
muito rápido entre dois polls), a estratégia mais confiável é `network_payload`.

### Solução de emergência

Se nenhuma estratégia capturou o valor:

```bash
testforge compile <gravação> --data
# Editar test_data.json e inserir o valor correto manualmente
```

Para evitar regressão, registre o campo como blind_spot esperado no plano de
teste (PLANO-DE-TESTE.md), indicando que o valor deve ser fornecido via
`--data` nesse fluxo específico.

---

## 6. Referências

| Documento | Conteúdo |
|-----------|---------|
| [PLANO-DE-TESTE.md](PLANO-DE-TESTE.md) | 27+ casos de teste manuais |
| [BUGS.md](BUGS.md) | Bugs documentados e corrigidos |
| [run-incremental.md](run-incremental.md) | Executor passo a passo |
| `src/testforge/semantic/intent_reconstructor.py` | Código do reconstructor |
| `tests/test_sprint4_intent_reconstructor.py` | Testes do reconstructor |
