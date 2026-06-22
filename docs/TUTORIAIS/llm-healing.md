# TestForge — Tutorial: LLM Self-Healing

**Versão:** 0.3.0
**Data:** 2026-06-15

---

## 1. Visão Geral

O TestForge grava fluxos de usuário e gera scripts Playwright que se auto-consertam quando seletores quebram. O healing funciona em 4 camadas:

```
L0 — HealingCatalog     (<50ms, JSONL)     → Receitas pré-cadastradas
L1 — FallbackRunner     (2s timeout)       → Candidatos alternativos do MIS
L2 — SpecialistAgents   (determinístico)   → 6 agentes por família de falha
L3 — LLM Healer         (~500 tok)         → Azure GPT-4.1-mini (off critical path)
```

---

## 2. Pré-requisitos

```bash
# Ativar ambiente
source activate.sh

# Fake-bank para testes (já incluso)
cd synthetic_lab/fake-react-bank-app
python -m http.server 8765 &
```

**LLM real (opcional):**
```bash
export AZURE_OPENAI_KEY="sua-chave"
export AZURE_OPENAI_ENDPOINT="https://seu-recurso.openai.azure.com/"
export AZURE_OPENAI_DEPLOYMENT="gpt-4.1-mini"
```

Sem essas variáveis, o `MockLLMHealer` é usado (determinístico, sem API).

---

## 3. Fluxo Básico

### 3.1 Gravar um fluxo

```bash
testforge record http://localhost:8765 --name "consulta-cpf"
```

Modo interativo:
- Preencha o CPF
- Clique em Pesquisar
- **Shift+S** para parar a gravação

### 3.2 Compilar com massa de dados externa

```bash
testforge compile consulta-cpf --data
```

Gera:
- `recordings/consulta-cpf/test_data.json` — massa de dados extraída
- `semantic_tests/ST-consulta-cpf/test_st_consulta_cpf.py` — script Playwright

### 3.3 Executar o script

```bash
testforge run semantic_tests/ST-consulta-cpf/test_st_consulta_cpf.py
```

### 3.4 Alterar a massa de dados

Edite `semantic_tests/ST-consulta-cpf/test_data.json`:

```json
{
  "fields": {
    "cpf": "99988877766"
  }
}
```

Execute novamente — o script usa o novo CPF sem recompilar.

---

## 4. Testando o Healing L3

### 4.1 Com MockLLMHealer (sem API key)

```bash
testforge demo-heal
```

Este comando:
1. Grava fluxo no fake-bank
2. Compila o script
3. Altera o ID do botão (mutation `change_id`)
4. Executa healing determinístico (L1+L2)
5. Valida com Oracle + Gate

### 4.2 Com LLM real (Azure)

```bash
# Configurar env vars do Azure
export AZURE_OPENAI_KEY="..."
export AZURE_OPENAI_ENDPOINT="https://..."

# Rodar demo
testforge demo-heal
```

O `CuradorAutomatico` detecta automaticamente as env vars e usa LLM real no L3.

---

## 5. Entendendo o Pipeline de Cura

### 5.1 Classificação da falha

Toda falha é classificada em 11 famílias (FAM-01 a FAM-11) com 88 códigos taxonômicos:

| Família | Código | Exemplo de falha |
|---------|--------|-----------------|
| FAM-01 | SEL-004 | Elemento não encontrado (#btn quebrou) |
| FAM-02 | TIM-005 | Timeout esperando elemento |
| FAM-03 | CTX-001 | Elemento dentro de iframe |
| FAM-04 | STA-002 | Overlay bloqueando clique |
| FAM-05 | DOM-001 | Stale element (DOM mutante) |
| FAM-06 | INP-007 | Campo com máscara JS |

### 5.2 Camadas de healing

```
Step falha
  → FailureClassifier.classify(error)
  → L0: HealingCatalog.match(family, symptom)  → receita exata?
  → L2: route_to_agent(family)                 → agente especialista?
  → L3: LLMHealer.heal(evidence, error)        → LLM ou Mock
  → Validar: confidence ≥ 0.5, taxonomy válida
  → Executar step com novo seletor
  → PASSED_STEP → _register_learned()
  → UNRESOLVED → increment_failure_count()
```

### 5.3 Evidências enviadas ao LLM

O `EvidencePayload` contém:
- **DOM snippet**: 3000 chars (head+tail), sem scripts/styles
- **Console errors**: últimos 5 (nível error/warning)
- **Network state**: últimas 3 requisições
- **Screenshot**: opcional (base64 PNG)

### 5.4 Prompts por família

O LLM recebe prompts especializados para cada família de falha:
- FAM-01: "You are a Playwright selector specialist..."
- FAM-02: "You are a Playwright timing specialist..."
- FAM-06: "You are a Playwright input/interaction specialist..."

Todos os prompts em **inglês** para máxima acurácia do modelo.

---

## 6. Debugging

### 6.1 Verificar se LLM está ativo

```python
from testforge.healing.llm_client import is_available
print(is_available())  # True se Azure/OpenAI keys configuradas
```

### 6.2 Testar MockLLMHealer

```python
from testforge.healing import MockLLMHealer, EvidencePayload

mock = MockLLMHealer()
payload = EvidencePayload(
    step_context={"action": "click", "text": "Pesquisar"},
    dom_snapshot="<html>...",
)
proposal = mock.heal(payload, "element not found", "FAM-01")
print(proposal.new_locator)  # "text=Pesquisar"
```

### 6.3 Testar CuradorAutomatico

```python
from testforge.healing import CuradorAutomatico
from testforge.evidence import EvidenceCollector

curator = CuradorAutomatico(step_runner=my_runner)
outcome = curator.cure(step_data, error_message, evidence_payload)
print(outcome.status, outcome.layer_used)
```

### 6.4 Simular falha com fake-bank

```bash
# Abrir fake-bank com mutation que quebra o seletor
# O ID do botão muda: #btnPesquisar → #btnPesquisar_XXXXXXXXXXXX
http://localhost:8765/?mutation=change_id
```

---

## 7. Métricas

Após cada execução, o TestForge reporta:

```
Total runs:      10
Total healings:  3
True heals:      2
False heals:     1
LLM escalations: 1

False heal rate: 33.33%
Precision:       66.67%
LLM rate:        10.00%
```

- **False heal rate**: curas que não resolveram o problema
- **LLM rate**: % de execuções que precisaram do LLM (deve ser baixo)
- **Healing layer**: qual camada resolveu (L0, L1, L2, L3)

---

## 8. Troubleshooting

| Problema | Causa provável | Solução |
|----------|---------------|---------|
| Script não compila | Seletor com aspas não escapadas | Verificar compiler._esc() |
| Healing não ativa | L0/L1 resolve antes | Normal — L3 só ativa quando L0-L2 falham |
| MockLLMHealer retorna confiança 0 | Taxonomia ou estratégia inválida | Verificar _parse_response() validation |
| DOM insuficiente | Página não carregou completamente | Aumentar wait_for_timeout antes de coletar |
| is_sufficient=False | DOM < 100 chars | Verificar page.content() retorna HTML válido |
| Console/network vazios | Listeners não registrados antes do goto | Chamar collector.start() antes de page.goto() |
