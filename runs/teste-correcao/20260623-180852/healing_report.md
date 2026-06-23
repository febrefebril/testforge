# TestForge Healing Report

- Validados: 4
- Rejeitados: 1

## Healings validados
### Step 4 — click
- Locator original: `span[contenteditable=""]`
- Locator proposto: `span:has-text("4")`
- Layer: L2 | Family: FAM-01 | Strategy: has_text_fallback
- Confidence: 0.85

### Step 13 — click
- Locator original: `span[contenteditable=""]`
- Locator proposto: `[data-testid='step-13']`
- Layer: L2 | Family: FAM-01 | Strategy: has_text_fallback
- Confidence: 0.85

### Step 14 — click
- Locator original: `span[contenteditable=""]`
- Locator proposto: `text="12"`
- Layer: L2 | Family: FAM-01 | Strategy: has_text_fallback
- Confidence: 0.70

### Step 16 — click
- Locator original: `span[contenteditable=""]`
- Locator proposto: `[data-testid='step-16']`
- Layer: L3 | Family: FAM-01 | Strategy: has_text_fallback
- Confidence: 0.85

## Healings rejeitados
### Step 24 — click
- Motivo: postcondition_failed,next_step_not_visible
- Locator proposto: `[data-testid='step-24']`
