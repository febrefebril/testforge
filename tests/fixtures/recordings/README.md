# Recording âncora fixtures

Recordings reais mínimos (JSONL + metadata) usados como golden regression
targets — ver `docs/ANTI-REGRESSION-PLAN.md` Camada 3.

Cada âncora tem:
- Arquivos JSONL essenciais (`raw_events`, `steps`, `value_mutations`,
  `field_snapshots`, etc)
- `recording_metadata.json` + `submission_report.json`
- `expected/pii_scan_summary.json` — golden output do PII scanner

## Âncoras atuais

### `r5a_sifap_credentials/`
- Source: `src/testforge/AGENDAMENTO/Autenticação/Deve logar no AGENDAMENTO com perfil de internet/REC-20260702-144218`
- Cobre: credenciais (CPF QA, password, PIN), Keycloak SSO params
- Golden: 28 hits (22 Keycloak, 4 CPF, 1 password, 1 PIN), 2 critical
- Bugs REC cobertos: REC-06, 24, 31, 35, 37, 38

### `r7a_siopi_producao/`
- Source: `src/testforge/SIMULADOR/suite exploratoria/testar todos os calculos/calculadora1`
- Cobre: detecção de domínio de PRODUÇÃO
- Golden: 0 pattern hits + 1 production_domain critical
- Bugs REC cobertos: REC-59

## Como adicionar novo âncora

1. Escolher recording com bug REC representativo (evitar > 100KB por fixture)
2. Copiar arquivos essenciais (`raw_events.jsonl`, `steps.jsonl`, `value_mutations.jsonl`, `field_snapshots.jsonl`, `recording_metadata.json`, `submission_report.json`)
3. NÃO copiar: `dom_snapshots/`, `ax_snapshots/`, `_pilot_runs/` — inflam repo
4. Gerar golden:
   ```python
   from testforge.security import scan_recording
   report = scan_recording('tests/fixtures/recordings/<name>')
   # ... reduzir e salvar como expected/pii_scan_summary.json
   ```
5. Adicionar teste em `tests/regression/recording/` que carrega âncora + valida golden

## Regra golden update

Se golden precisa mudar (fix pega mais/menos hits):
- Justificar em PR body
- Commit separado com update do golden + comentário explicativo
- Não faça bulk update — cada golden change é 1 decisão consciente
