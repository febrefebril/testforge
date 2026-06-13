# TestForge

Gravador inteligente de testes E2E com self-healing deterministico.

## O que e

TestForge grava a intencao do teste em paginas web e transforma em scripts Playwright que rodam ate o fim. Quando um teste quebra por fragilidade de seletor, o sistema se auto-conserta deterministicamente — sem depender de LLM como motor primario.

## Problema

Testes E2E quebram constantemente por fragilidade de seletores em aplicacoes enterprise (PrimeFaces, Angular, JSF). Seletores mudam a cada deploy. QAs perdem horas "consertando" testes que nao deveriam quebrar.

## Solucao

Gravar **intencao**, nao seletores. O recorder captura: role, accessible name, texto visivel, contexto. Isso vira um contrato semantico (SemanticTestCase YAML). Na execucao, se o seletor falhar, o motor deterministico gera candidatos alternativos ordenados por score.

## Arquitetura

Recorder Sensorial (Playwright nativo) → SemanticTestCase (YAML) → Compiler Playwright → Runner + Healing (4 layers: Recipe → Agent → Evidence → LLM)

## Stack

Python 3.10+, Playwright, Typer, JSONL+YAML, pytest

## MVP — 7 Sprints

| Sprint | Foco |
|--------|------|
| S1 | Fundacao + Synthetic Lab (fake-react-bank-app + 4 mutacoes) |
| S2 | Recorder Sensorial (Playwright page.on()) |
| S3 | EvidenceCollector + SQLite store |
| S4 | SemanticTestCase + Compiler Playwright |
| S5 | Oracles + PromotionGate |
| S6 | Taxonomia + ShadowValidator + Fallback |
| S7 | Metricas + Revisao + Relatorio |

## Licoes das 4 tentativas anteriores

1. Recorder funcional EXISTE (projeto-anterior) — nao redesenhá-lo
2. Vertical slice primeiro, governanca depois
3. MIS como camada fina, nao mega-schema
4. LLM apenas como curador, off critical path
