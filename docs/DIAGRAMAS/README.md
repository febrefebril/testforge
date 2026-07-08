# Diagramas TestForge

Este diretório concentra diagramas de arquitetura e fluxo do TestForge.

## Como regenerar PNGs

```bash
cd docs/DIAGRAMAS
plantuml *.puml
```

Os PNGs gerados devem ficar em `docs/DIAGRAMAS/png/`.

## Diagramas de comparativo ATUAL vs ALVO

- `sequencia-resolver-ATUAL.puml`
- `sequencia-resolver-ALVO.puml`
- `sequencia-curator-runner-ATUAL.puml`
- `sequencia-curator-runner-ALVO.puml`
- `sequencia-bug-detection-recording-ALVO.puml`

## Diagramas principais de pipeline

- `fluxograma-pipeline-v2.puml`
- `sequencia-fluxo-completo-v2.puml`
- `sequencia-assert-flow.puml`
- `fluxograma-diagnostic-mode.puml`
- `sequencia-diagnostic-gherkin.puml`

## Checklist de atualização

- Atualizar `.puml` impactados por mudanças de fluxo.
- Regenerar PNGs com PlantUML.
- Confirmar renderização sem erro.
- Referenciar novos diagramas em `docs/ARCHITECTURE-V2.md` quando aplicável.
