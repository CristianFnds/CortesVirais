4. Plano de desenvolvimento por fases

Fase 1 — Fundação do projeto
Prioridade P0
Objetivo: preparar o ambiente e definir os contratos técnicos.
- Criar o repositório Git.
- Configurar Python, ambiente virtual e dependências.
- Verificar disponibilidade do FFmpeg.
- Definir configuração por variáveis de ambiente.
- Criar a estrutura de pastas.
- Configurar logs e identificadores de processamento.
- Validar a comunicação com a API do modelo local.
Entrega: projeto executável com configuração centralizada e documentação inicial.
Critério de aceite: a aplicação inicia, verifica suas dependências e informa claramente quais componentes estão disponíveis.




Fase 2 — Download e preparação de mídia
Prioridade P0
Objetivo: receber um vídeo e preparar os arquivos para análise.
- Implementar validação de URLs permitidas.
- Obter metadados e duração.
- Baixar o vídeo usando yt-dlp.
- Extrair o áudio com FFmpeg.
- Criar diretórios isolados por trabalho.
- Tratar falhas de rede, formatos indisponíveis e falta de espaço.
Entrega: serviço de preparação de mídia com metadados persistidos.
Critério de aceite: um vídeo de teste autorizado é baixado, seu áudio é extraído e os arquivos são identificados pelo mesmo ID de trabalho.




Fase 3 — Transcrição com timestamps
Prioridade P0
Objetivo: converter o áudio em dados estruturados.
- Integrar faster-whisper.
- Permitir selecionar o idioma ou detectá-lo automaticamente.
- Gerar segmentos com início, fim e texto.
- Salvar o resultado em JSON.
- Validar a ordem temporal dos segmentos.
- Tratar áudios sem fala e erros de transcrição.
Entrega: serviço de transcrição independente.
Critério de aceite: o sistema gera uma transcrição que pode ser reutilizada sem baixar ou transcrever o vídeo novamente.




Fase 4 — Seleção inteligente dos melhores momentos
Prioridade P0
Objetivo: transformar a transcrição em uma lista de cortes candidatos.
- Criar um serviço de integração com o LLM local.
- Desenvolver um prompt especializado em vídeos curtos.
- Definir um formato JSON de saída.
- Avaliar gancho inicial, relevância, autonomia e conclusão.
- Implementar validação dos intervalos.
- Remover trechos repetidos ou muito sobrepostos.
- Permitir configurar a quantidade e a duração dos clipes.
Entrega: lista de candidatos com tempos, título, justificativa e pontuação.
Critério de aceite: todas as sugestões respeitam a duração do vídeo, possuem intervalos válidos e podem ser processadas sem depender de texto livre do modelo.




Fase 5 — Geração e validação dos clipes
Prioridade P0
Objetivo: converter os intervalos selecionados em vídeos utilizáveis.
- Implementar cortes com FFmpeg.
- Validar os tempos de início e fim.
- Gerar arquivos MP4 com nomes previsíveis.
- Validar duração, tamanho e integridade dos arquivos.
- Registrar falhas por clipe.
- Garantir que repetir uma etapa não gere duplicações desnecessárias.
Entrega: serviço de geração de clipes.
Critério de aceite: cada arquivo final é reproduzível, possui áudio sincronizado e respeita a duração configurada, dentro das tolerâncias técnicas.




Fase 6 — Integração com n8n e Telegram
Prioridade P0
Objetivo: automatizar o processo de ponta a ponta.
- Criar e configurar o bot no Telegram.
- Criar o workflow de recebimento da URL.
- Validar o remetente e a entrada.
- Chamar a API Python para iniciar o trabalho.
- Consultar o status periodicamente ou receber notificações de conclusão.
- Enviar mensagens de progresso.
- Enviar os clipes e o resumo final.
- Criar um workflow de tratamento de erros.
Entrega: automação completa a partir de uma mensagem no Telegram.
Critério de aceite: enviar uma URL inicia o trabalho, e o bot entrega o resultado ou comunica a falha sem exigir intervenção manual.




Fase 7 — Testes, confiabilidade e otimização
Prioridade P1
Objetivo: tornar a ferramenta confiável para uso recorrente.
- Criar testes unitários e de integração.
- Testar vídeos curtos, longos, com silêncio e com falhas.
- Medir o tempo de cada etapa.
- Implementar limpeza de arquivos temporários.
- Impedir trabalhos duplicados acidentais.
- Avaliar consumo de CPU, RAM e VRAM.
- Ajustar o tamanho dos vídeos enviados pelo Telegram.
Entrega: MVP documentado, testado e pronto para uso pessoal contínuo.