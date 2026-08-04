
temos um bug: quando acabamos de atualizar abrindo a gui. Ele faz a atualização mas ele acaba executando a versão antiga antes de executar a nova.

sanitizar os nomes dos artefatos de testes que serão salvos e que serão enviados para o git

Melhorar as estrutura das pastas geradas para gravação, compilação, execução e outros elementos produzidos para os nossos testes. Hoje em dia está todo espalhado pelo projeto o ideal seria uma estrtura em que tudo ficasse agrupada por sistema/suite/caso_de_teste/teste/{gravacao, execucao, falhas, evidencia.

criar o PlayCode - gui que roda os testes

criar um script que varre todo o repositório e pegue todos os erros da gravação, execução, compilação e gere um arquivo de log que servirá para ajudar na correção de bugs e na criação de estratégias de gravação e cura.

Logo após a atualização automática pela gui (que usa o git) ele ainda abre a gui antiga. Ele deve abrir a que acabou de ser atualizada 

