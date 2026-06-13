# TestForge

Gravador inteligente de testes E2E com self-healing deterministico.

## Arquitetura

```
Recorder Sensorial → SemanticTestCase → Compiler Playwright → Runner + Healing
```

## Diretorios

| Diretorio | Proposito |
|-----------|-----------|
| `src/testforge/` | Codigo fonte |
| `recordings/` | Sessoes de gravacao brutas |
| `semantic_tests/` | Contratos semanticos (YAML) |
| `generated_tests/` | Scripts Playwright gerados |
| `evidence/` | Evidencias de execucao |
| `policies/` | Politicas versionadas |
| `schemas/` | Schemas de contrato |
| `adrs/` | Architecture Decision Records |
| `synthetic_lab/` | App falsa + mutation matrix |
| `tests/` | Testes unitarios e integracao |
| `scripts/` | Scripts utilitarios |

## Stack

Python 3.10+, Playwright, Typer, YAML, JSONL

## Como Executar

```bash
# Instalar dependencias
pip install -e .

# Synthetic lab
cd synthetic_lab/fake-react-bank-app && python -m http.server 3000

# Rodar testes
pytest tests/ -v
```

## Pipeline

BMAD (planejamento) → GSD Core (execucao) → Git (versionamento)
