# language: pt
Funcionalidade: SIMAX - Massagem Expressa

  Cenario: Fluxo iniciado por 'Novo agendamento'
    Dado que acesso "https://simax.caixa/simax/"
    Dado que acesso "https://simax.caixa/simax/novo_agendamento.asp"
    Quando clico no botao "Novo agendamento"
    E seleciono "0" em "UF"
    E seleciono "GO" em "UF"
    E seleciono "GO" em "UF"
    E seleciono "0" em "Edifício"
    E seleciono "21" em "Edifício"
    E seleciono "21" em "Edifício"
    E seleciono "0" em "Data"
    E seleciono "2026-07-09" em "Data"
    E seleciono "2026-07-09" em "Data"
    Entao vejo o texto "Reservado"
