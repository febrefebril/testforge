# Guia do Tester — TestForge

## Requisitos

- Python 3.10 ou superior
- Google Chrome ou Chromium instalado

## Instalacao

```bash
pip install -e .
playwright install chromium
```

## Como gravar um fluxo

Execute o comando abaixo substituindo `NOME` pelo nome do teste e `URL` pela URL inicial:

```bash
testforge record --app CAIXA https://habitacao.caixa.gov.br/simulador --name simulador-credito
```

O navegador abre automaticamente. Realize o fluxo normalmente — cada acao e capturada.

### Atalhos durante a gravacao

| Atalho   | Acao                                      |
|----------|-------------------------------------------|
| Shift+S  | Parar gravacao e salvar                   |
| Shift+A  | Marcar verificacao (assert) em um elemento|
| Shift+P  | Pausar / retomar gravacao                 |

**Como usar o assert (Shift+A):** pressione Shift+A, depois clique no elemento que quer verificar — nao clique no fundo da pagina.

## Como enviar a gravacao

Apos parar com Shift+S, a gravacao fica salva em `recordings/simulador-credito/`.

Compacte a pasta completa:

```bash
zip -r simulador-credito.zip recordings/simulador-credito/
```

Envie o arquivo `simulador-credito.zip` para o time de engenharia.

## O que NAO fazer

- NAO edite nenhum arquivo dentro de `recordings/{nome}/`
- NAO renomeie a pasta da gravacao
- NAO grave com VPN ativa (pode mascarar URLs internas)
- NAO feche o navegador manualmente — sempre use Shift+S para encerrar
