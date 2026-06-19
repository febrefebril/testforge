---
status: testing
phase: 1-foundacao-synthetic-lab
source: PLAN.md
started: 2026-06-18T21:04:24Z
updated: 2026-06-18T21:04:24Z
---

## Current Test

number: 1
name: Fake Bank App — Formulario CPF com mutation support
expected: |
  synthetic_lab/fake-react-bank-app/index.html existe, carrega no browser, mostra campo CPF com label acessivel e botao Pesquisar com accessible name. Query string ?mutation=change_id altera IDs.
awaiting: user response

## Tests

### 1. Fake Bank App — Formulario CPF
expected: Synthetic lab app exists, loads in browser, shows CPF field with accessible label and Pesquisar button with accessible name. Query string `?mutation=change_id` alters IDs.
result: [pending]

### 2. Mutation Matrix — 5 mutations defined
expected: `synthetic_lab/mutation_matrix.yaml` exists with 5 mutations: change_id, change_accessible_name, duplicate_button_text, overlay_blocks_click, disabled_button. Each has code, technology, url_query, expected fields.
result: [pending]

### 3. Base Test Passes — fluxo sem mutacao
expected: `pytest tests/test_fake_bank_flow.py -v` passes. Fills CPF, clicks Pesquisar, verifies resultado visivel.
result: [pending]

### 4. Mutation change_id — quebra o teste base
expected: With `?mutation=change_id`, the base selector breaks. `pytest tests/test_mutations.py -k change_id -v` detects the failure correctly.
result: [pending]

### 5. Mutation change_accessible_name — quebra o teste base
expected: With `?mutation=change_accessible_name`, aria-label changes. Mutation test detects the expected taxonomy code.
result: [pending]

### 6. Mutation duplicate_button_text — quebra o teste base
expected: With `?mutation=duplicate_button_text`, two buttons with same text appear. Mutation test detects ambiguous target.
result: [pending]

### 7. Mutation overlay_blocks_click — quebra o teste base
expected: With `?mutation=overlay_blocks_click`, overlay covers the button. Mutation test detects click interception.
result: [pending]

### 8. Mutation disabled_button — quebra o teste base
expected: With `?mutation=disabled_button`, button is disabled. Mutation test detects disabled state.
result: [pending]

## Summary

total: 8
passed: 0
issues: 0
pending: 8
skipped: 0
blocked: 0

## Gaps

[none yet]
