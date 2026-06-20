# Versionamento e Sincronização de Diagramas

**Versão**: v0.4.0 (2026-06-20)  
**Status**: Fase A congelada (Recorder) — Fases B/C planejadas

## 🎯 Objetivo

Manter diagramas PlantUML sincronizados com código durante evolução do projeto:
- Fase A (congelada): Recorder, gravação de intenção
- Fase B: Consumo em módulos downstream (normalizer, reconstructor)
- Fase C: Validação piloto com 5 gravações CAIXA
- Fase D: Distribuição ao time de testers

## 📊 Diagramas Atuais (14)

| Categoria | Diagramas | Última Atualização | Status |
|-----------|-----------|-------------------|--------|
| **C4 Architecture** | c4-context.puml, c4-container.puml, c4-context-v1.puml | 2026-06-20 | ✅ Aligned |
| **Componentes** | componentes-v1.puml, componentes-llm-healing.puml | 2026-06-20 | ✅ Aligned |
| **Classes** | classes-llm-healing.puml | 2026-06-20 | ✅ Aligned |
| **Deploy** | deploy-llm-healing.puml | 2026-06-20 | ✅ Aligned |
| **Estados** | estados-recording-session.puml, estados-curacao-outcome.puml | 2026-06-20 | ✅ Aligned |
| **Fluxogramas** | fluxograma-pipeline-v1.puml | 2026-06-20 | ✅ Aligned |
| **Sequências** | sequencia-curadoria-l0-l3.puml, sequencia-data-driven.puml, sequencia-fluxo-completo.puml, sequencia-integracao-cmd-run.puml | 2026-06-20 | ✅ Aligned |

## 🔄 Sincronização por Fase

### Fase A (Congelada ❄️)
**Escopo**: Recorder sensorial + gravação de intenção  
**Diagramas críticos**:
- `c4-context.puml` — QA grava fluxo via browser
- `estados-recording-session.puml` — Estados da sessão
- `sequencia-fluxo-completo.puml` — E2E: Gravação → Compilação → Execução

**Mudança de código? Não atualiza diagramas.** Fase A está congelada.

### Fase B (Planejada)
**Escopo**: Consumo em módulos downstream (normalizer, reconstructor, evidence)  
**Diagramas a atualizar**:
- `c4-container.puml` — Adicionar fluxo de normalização/reconstrução
- `sequencia-fluxo-completo.puml` — Adicionar Intent Completeness Checker
- **NOVO**: `sequencia-fase-b-normalizacao.puml` — Detalhe de normalização
- **NOVO**: `sequencia-fase-b-reconstrucao.puml` — Detalhe de reconstrução com 3 estratégias

**Checklist**:
- [ ] Código implementado em `src/testforge/semantic/`
- [ ] Testes em `tests/test_sprint4_*.py`
- [ ] Atualizar `c4-container.puml`
- [ ] Gerar `sequencia-fase-b-*.puml` (2 novos)
- [ ] Regenerar PNGs: `java -jar ~/.emacs.d/lib/plantuml-lgpl-1.2026.2.jar -tpng docs/diagramas/*.puml -o png/`
- [ ] Commit: `docs: atualizar diagramas Fase B — normalização + reconstrução`

### Fase C (Planejada)
**Escopo**: Validação piloto (intent completeness, readiness gate)  
**Diagramas a atualizar**:
- `c4-container.puml` — Adicionar Validation layer
- `sequencia-integracao-cmd-run.puml` — Adicionar validação incremental
- **NOVO**: `sequencia-fase-c-validacao.puml` — Detalhe de pipeline de validação
- **NOVO**: `estados-validacao-incremental.puml` — Estado machine de validação

**Checklist**:
- [ ] Código implementado em `src/testforge/validation/`
- [ ] Testes em `tests/test_sprint5_*.py`, `tests/intent_lab/`
- [ ] Atualizar `c4-container.puml`
- [ ] Gerar `sequencia-fase-c-*.puml` (2 novos)
- [ ] Regenerar PNGs
- [ ] Commit: `docs: atualizar diagramas Fase C — validação incremental + readiness`

### Fase D (Planejada)
**Escopo**: Distribuição ao time de testers  
**Diagramas a atualizar**:
- `deploy-llm-healing.puml` — Adicionar CI/CD pipeline de distribuição
- **NOVO**: `sequencia-fase-d-distribuicao.puml` — Fluxo de packaging e release

## 🚀 Regenerar PNGs

Após qualquer mudança em `.puml`:

```bash
# Opção 1: Usar JAR diretamente
java -jar ~/.emacs.d/lib/plantuml-lgpl-1.2026.2.jar -tpng docs/diagramas/*.puml -o png/

# Opção 2: Script wrapper (criar se necessário)
bash scripts/generate-diagrams.sh
```

Depois committar:
```bash
git add docs/diagramas/png/
git commit -m "docs: regenerar PNGs — [descrição da mudança]"
```

## 📋 Checklist de Sincronização

Antes de cada milestone (sprint/fase):

- [ ] Listar todos os commits em `src/testforge/` desde última atualização
- [ ] Verificar se houve mudanças em:
  - Nomes de classes/módulos
  - Fluxos de controle (sequência de passos)
  - Estados/máquinas de estado
  - Componentes adicionados/removidos
- [ ] Atualizar `.puml` correspondentes
- [ ] Validar graficamente (abrir PNGs)
- [ ] Regenerar PNGs
- [ ] Commit com mensagem: `docs: atualizar diagramas [Fase/Sprint X] — [mudanças]`

## 🔍 Validação de Alinhamento

Para auditar diagramas vs. código:

```bash
# Listar módulos em src/testforge/
ls -1 src/testforge/

# Verificar classes críticas
grep -r "^class " src/testforge/ | grep -v test | wc -l

# Verificar máquinas de estado
grep -r "class.*State\|@enum\|Enum\)" src/testforge/ | grep -v test
```

## 📝 Versionamento por Milestone

Cada milestone (v0.4.0, v0.5.0, etc.) deve:
1. Atualizar versão em todos os `.puml` (título)
2. Regenerar PNGs
3. Committar com tag: `git tag -a v0.5.0-diagrams -m "Diagrams v0.5.0"`

## 🎓 Convenções PlantUML

- **Atores**: `actor "Nome" as CODE`
- **Componentes**: `component "Nome\n(Info)" as CODE`
- **Bancos**: `database "Nome\n(Storage)" as CODE`
- **Clouds**: `cloud "Nome\n(External)" as CODE`
- **Retângulos**: `rectangle "Namespace" as NS { ... }`
- **Estados**: `state "Nome" as S1 --> S2`
- **Cores**: `#LightBlue`, `#LightGreen`, `#LightGray`, `#FFFFFF`

## 🔗 Referências

- PlantUML Docs: https://plantuml.com/
- C4 Model: https://c4model.com/
- Diagramas: `docs/diagramas/*.puml`
- PNGs: `docs/diagramas/png/`
