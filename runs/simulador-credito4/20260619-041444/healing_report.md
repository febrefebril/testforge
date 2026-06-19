# TestForge Healing Report

- Validados: 1
- Rejeitados: 1

## Healings validados
### Step 3 — click
- Locator original: `label:has-text("Não, tenho menos de 3 anos") + input`
- Locator proposto: `text=Não, tenho menos de 3 anos`
- Layer: L2 | Family: FAM-06 | Strategy: press_sequentially
- Confidence: 0.85

## Healings rejeitados
### Step 4 — click
- Motivo: postcondition_failed,next_step_not_visible
- Locator proposto: `text=Não, só eu`
