# TestForge — Troubleshooting

## Problemas Comuns

### Gravação não inicia

| Causa | Solução |
|-------|---------|
| Chrome não encontrado | `playwright install chromium` |
| Porta ocupada | Mate outros processos na porta ou use `--port` |
| VPN ativa | Desative a VPN — pode mascarar URLs internas |

### Atalhos não funcionam

- Verifique se o navegador está com foco (clique na página)
- Shift+S, Shift+A e Shift+P funcionam apenas durante gravação ativa
- No Linux, verifique se outro programa não está capturando os atalhos

### Assert não registra

- Pressione Shift+A e **depois** clique no elemento
- Não clique no fundo da página — clique no elemento específico
- O overlay deve mostrar "Modo Assert" antes de clicar

### Script não compila

- Provavelmente seletor com aspas não escapadas
- Execute `testforge compile <nome>` para ver o erro exato
- Reporte ao time de engenharia com o erro completo

### Teste falha ao executar

- Verifique se o servidor da aplicação está no ar
- O self-healing tenta recuperar automaticamente (L0-L3)
- Consulte o relatório em `runs/<id>/execution_report.json`

---

**Ainda com problemas?** Abra uma issue no GitHub com:
- O comando executado
- O log de erro completo
- O conteúdo de `recordings/<nome>/`
