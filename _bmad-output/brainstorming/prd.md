# PRD — TestForge v1

**Versao:** 1.0
**Status:** Aprovado
**Data:** 2026-06-13

---

## 1. Visao do Produto

TestForge e uma ferramenta CLI que grava a intencao do teste em paginas web e gera scripts Playwright Python com self-healing deterministico. O QA grava uma vez; o script sobrevive a mudancas de UI.

---

## 2. Personas

| Persona | Necessidade | Cenario Principal |
|---------|-------------|-------------------|
| **QA Engineer (Andre)** | Gravar fluxos em apps enterprise (PrimeFaces, Angular) e rodar sem manutencao constante | Andre grava um fluxo de consulta CPF, o script gerado roda no pipeline toda noite. Quando o ID do botao muda, o healing deterministico corrige automaticamente. |
| **Dev** | Validar fluxos durante desenvolvimento | Dev grava o fluxo de login, roda a cada commit, recebe alerta se quebrar. |

---

## 3. Requisitos Funcionais

### RF-01: Gravacao de Fluxo (v0.1.0 ✓)
- Gravacao via Playwright nativo (sem extensao browser)
- Captura: click, fill, navigation
- Comandos de teclado: Shift+P (pause), Shift+S (stop), Shift+A (assert)
- 4 tipos de assert: textual, estado, visivel, automatico
- Artefatos: raw_events.jsonl, steps.jsonl, screenshots, DOM snapshots, network log

### RF-02: Modelo Intermediario Semantico (v0.1.0 ✓)
- Converter RawRecordedSession → SemanticTestCase YAML
- Gerar candidatos de locator com scoring deterministico
- SemanticTestCase como fonte de verdade

### RF-03: Compilacao de Script (v0.1.0 ✓)
- Gerar script Playwright Python com fallback loop
- Suporte a fill, click, assert (4 tipos)
- Script compila e roda via pytest

### RF-04: Evidencias (v0.1.0 ✓)
- Coletar screenshots before/after, DOM snapshots
- JSONL store sem SQLite
- Sensitive data: alert_only

### RF-05: Oracle + PromotionGate (v0.1.0 ✓)
- visual_dom: verifica visibilidade e texto
- business_state: extrai e compara valor
- Gate com 3 estados: experimental, shadow_validated, rejected

### RF-06: Taxonomia + Healing (v0.1.0 ✓)
- Classificar falhas em 6 familias
- ShadowValidator: sugere healing, nao aplica
- FallbackRunner: deterministico, timeout 2s

### RF-07: Metricas (v0.1.0 ✓)
- false_heal_rate, precision, llm_rate
- Review CLI

### RF-08: CLI Installavel (v0.2.0)
- `pip install testforge` → comando `testforge`
- `testforge record <url>` → gravar fluxo
- `testforge compile <recording>` → gerar script
- `testforge run <script>` → executar com healing

### RF-09: Pipeline Run Integrada (v0.2.0)
- Executar script gravado com fallback loop
- Se falhar, tentar candidatos do MIS
- Classificar falha, sugerir healing
- Registrar metricas

### RF-10: Demo Healing Real (v0.2.0)
- Gravar fluxo no fake-bank
- Alterar ID do botao (mutation)
- Executar script → fallback encontra candidato alternativo
- Oracle valida, Gate promove se passar

---

## 4. Requisitos Nao-Funcionais

| RNF | Descricao |
|-----|-----------|
| **Deterministico primeiro** | LLM apenas como curador, off critical path |
| **Zero DB no MVP** | JSONL + filesystem |
| **Playwright nativo** | Sem extensao browser |
| **Tempo de healing** | < 2s por candidato (timeout de fallback) |
| **Testavel** | pytest para todos os modulos (93 testes) |
| **Versionado** | Conventional commits, git hooks |

---

## 5. Escopo

### v0.1.0 (Entregue)
- RF-01 a RF-07
- 9 modulos, 93 testes

### v0.2.0 (Proximo)
- RF-08, RF-09, RF-10
- CLI installavel, pipeline run, demo healing

### Fora do MVP
- LLM Curator integrado
- Dashboard web
- Multiplos frameworks alem de React/PrimeFaces
