# TestForge Healing Report

- Validados: 2
- Rejeitados: 1

## Healings validados
### Step 2 — click
- Locator original: `a:has-text("Simulação Completa Confira o valor do seu financiamento de a")`
- Locator proposto: `text=fact_check Simulação Completa  Confira o valor do seu financiamento de acordo co`
- Layer: L3 | Family: FAM-11 | Strategy: synthetic_click
- Confidence: 0.85

### Step 6 — click
- Locator original: `input[placeholder="000.000.000-00"]`
- Locator proposto: `input[placeholder="000.000.000-00"]`
- Layer: L2 | Family: FAM-06 | Strategy: press_sequentially
- Confidence: 0.82

## Healings rejeitados
### Step 14 — fill
- Motivo: postcondition_failed,value_mismatch
- Locator proposto: `input[placeholder="000.000.000-00"]`
