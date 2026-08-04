# TestForge — regras para agentes de codigo

## Ambiente (nao negociavel)
- Windows corporativo com AppLocker. Tudo deve rodar por `python -m <modulo>`
  ou `python scripts/tf.py`.
- Sem Docker, sem privilegio administrativo, sem assumir internet aberta.
- **Os bundles de navegador do Playwright nao podem ser baixados.** Usa-se
  sempre o navegador ja instalado no sistema, pelo `channel` (msedge/chrome).
  Nunca sugira `playwright install`.
- LangChain e LangGraph sao proibidos neste projeto.
- Codigo entregue tem que executar. Trecho que nao roda nao conta como entrega.

## Fluxo de trabalho
- Snapshot: `python scripts/tf.py snapshot --path <pasta> --out ctx.txt`
  Nunca peca o projeto inteiro quando o trabalho e local a um modulo.
- Patch: um incremento por arquivo JSON, pequeno e reversivel.
- Aplicacao: `python scripts/tf.py apply --manifest patch-manifest.json`
  A ferramenta valida, aplica, roda o gate e commita. Falha = rollback.
- Rollback: `python scripts/tf.py rollback --to <ID>`

## Formato de patch aceito
`{"version": 1, "changes": [...]}` com os tipos:
`create_file`, `add_file`, `replace_file`, `append_to_file`, `delete_file`,
`text_replace` (preferido: literal, com `count` e `must_contain`),
`regex_replace`, `replace_function`, `replace_class`.

Prefira `text_replace` a `regex_replace`: e revisavel e falha alto quando a
base mudou.

## O que nao fazer
- Nao reescrever `semantic/recording_normalizer.py`, `semantic/compiler.py` nem
  `healing/` inteiros para resolver um problema localizado.
- Nao regenerar os snapshots golden automaticamente.
- Nao remover contrato legado sem depreciar antes.
- Nao declarar sucesso sem mostrar o comando executado e a saida.
