# TestForge — Guia Completo de Gravação

## Requisitos

- Python 3.10 ou superior
- Google Chrome ou Chromium instalado

## Instalação

```bash
pip install -e .
playwright install chromium
```

## Como gravar um fluxo

Execute o comando abaixo substituindo `NOME` pelo nome do teste e `URL` pela URL inicial:

```bash
testforge record --app CAIXA https://habitacao.caixa.gov.br/simulador --name simulador-credito
```

O navegador abre automaticamente. Realize o fluxo normalmente — cada ação é capturada.

### Atalhos durante a gravação

| Atalho   | Ação                                      |
|----------|-------------------------------------------|
| Shift+S  | Parar gravação e salvar                   |
| Shift+A  | Marcar verificação (assert) em um elemento|
| Shift+P  | Pausar / retomar gravação                 |

**Como usar o assert (Shift+A):** Pressione Shift+A, depois clique no elemento que quer verificar — não clique no fundo da página.

## Como enviar a gravação

Após parar com Shift+S, a gravação fica salva em `recordings/simulador-credito/`.

Compacte a pasta completa:

```bash
zip -r simulador-credito.zip recordings/simulador-credito/
```

Envie o arquivo `simulador-credito.zip` para o time de engenharia.

## O que NÃO fazer

- NÃO edite nenhum arquivo dentro de `recordings/{nome}/`
- NÃO renomeie a pasta da gravação
- NÃO grave com VPN ativa (pode mascarar URLs internas)
- NÃO feche o navegador manualmente — sempre use Shift+S para encerrar

---

**Veja também:** [Quick Start](QUICK-START.md) — [Troubleshooting](TROUBLESHOOTING.md)
