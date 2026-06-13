# Páginas de Teste para Curadoria (B.2.4)

Cada página simula uma família da taxonomia com duas variantes:
- **v1** (sem `?error=1`): página limpa para gravação
- **v2** (com `?error=1`): página com erro induzido para testar self-healing

## Páginas

| Pasta | Família | v1 (limpa) | v2 (erro) | Cura esperada |
|-------|---------|-----------|-----------|---------------|
| `fam-01-selector/` | FAM-01 | Botão com `data-testid` + `id` | Remove `data-testid` e `id` | Layer 1: `has-text` |
| `fam-02-timing/` | FAM-02 | Botão aparece em 100ms | Botão aparece em 5s | Layer 2: wait strategy |
| `fam-03-context/` | FAM-03 | Iframe carrega em 100ms | Iframe vazio (sem srcdoc) | Layer 1: iframe switch |
| `fam-04-state/` | FAM-04 | Botão "Confirmar" enabled após "Avançar" | "Avançar" oculto, "Confirmar" disabled | Layer 1: force click |
| `fam-04-state-input-disabled/` | FAM-04 | Input text normal | Input `disabled` | Layer 1: synthetic click |
| `fam-05-dom-dinamico/` | FAM-05 | Lista com 3 itens + botão reordenar | Lista parcial no erro | Layer 2: dynamic DOM |
| `fam-06-fill/` | FAM-06 | Input sem máscara | Input com máscara JS de CPF | Layer 1: `pressSequentially` |
| `fam-06-input-select-simulado/` | FAM-06 | `<select>` normal | `<select>` substituído por div | Layer 1: click option |
| `fam-07-capture/` | FAM-07 | Input file com `accept` | `accept` removido | Layer 2: upload strategy |
| `fam-08-assertion/` | FAM-08 | Texto "Salvo com sucesso" | Texto "Erro ao processar" | Layer 3b: LLM Healer |
| `fam-09-recorder/` | FAM-09 | Botão com data-testid | Overlay bloqueante + botão oculto | Layer 1: modal dismiss |
| `fam-10-execution/` | FAM-10 | `alert()` simples | Console.error + alert bloqueante | Layer 1: dialog handler |
| `fam-11-browser/` | FAM-11 | `window.open` popup | localStorage + console.error | Layer 2: popup handler |

## Forçando cada camada

- **Layer 1 (catálogo)**: páginas cujo erro tem entry pré-povoada no `healing-catalog.jsonl`
- **Layer 2 (agentes futuros)**: páginas com sintomas não catalogados, resolvíveis por heurística
- **Layer 3a (Evidence Collector)**: mockar L1+L2 como UNRESOLVED → monta payload
- **Layer 3b (LLM Healer)**: mockar L2 como UNRESOLVED → força chamada LLM
- **Layer 3c (Curador Automático)**: LLM propõe cura → valida executando → registra `learned`
- **UNRESOLVED**: caso onde LLM retorna confidence < 0.5
