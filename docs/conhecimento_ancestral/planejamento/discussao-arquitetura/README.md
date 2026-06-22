# TestForge — Pacote Consolidado da Discussão

Este pacote consolida a discussão sobre a evolução arquitetural do TestForge para gravação resiliente, modelo intermediário semântico, self-healing determinístico, shadow mode, oracles pós-ação, evidências automáticas, Promotion Gate e Synthetic Lab.

## Decisão atualizada sobre dados sensíveis

Durante a discussão, foi decidido que, no MVP inicial, o `EvidenceCollector` **não deve mascarar automaticamente** CPF ou outros dados sensíveis.

A política inicial será:

```text
Detectar e alertar a possível presença de dados sensíveis.
Não alterar, mascarar ou remover automaticamente o conteúdo coletado.
Registrar o alerta no Evidence Package.
Deixar a decisão de mascaramento para uma etapa posterior de governança.
```

Motivo: nesta fase, o objetivo é preservar fidelidade das evidências para depuração, revisão e validação do healing. O mascaramento automático pode introduzir perda de contexto ou distorcer a análise. A preocupação com dados sensíveis permanece registrada e deve ser tratada por política de armazenamento, acesso e revisão.

## Conteúdo principal

- `00_conversa_testforge_perguntas_respostas.md`: perguntas do Andre e respostas consolidadas.
- `01_decisao_dados_sensiveis_alert_only.md`: decisão atualizada sobre dados sensíveis.
- `02_indice_arquivos_gerados.md`: índice de artefatos incluídos.
- `artefatos/`: todos os arquivos gerados ao longo da conversa.
- `pacotes/`: pacotes zip intermediários gerados durante a conversa.
- `codigo_referencia/`: arquivos Python/SQL/YAML principais para implementação.

## Observação

Este pacote é uma consolidação do material produzido na conversa. Alguns artefatos são versões incrementais e exploratórias; a implementação final deve versionar formalmente os contratos, schemas e políticas que forem adotados.
