# PLANO DE DESENVOLVIMENTO — VIDEO CLIPS AI

## 1. OBJETIVO DO PROJETO

Desenvolver uma ferramenta de automação para identificar e extrair os melhores momentos de vídeos do YouTube, utilizando inteligência artificial local.

O usuário deverá enviar um link de vídeo por meio de um bot do Telegram. A partir dessa mensagem, o n8n iniciará e orquestrará o processamento completo.

O sistema deverá:

1. Receber uma URL do YouTube pelo Telegram.
2. Validar a solicitação.
3. Baixar o vídeo autorizado.
4. Extrair o áudio.
5. Transcrever o conteúdo com timestamps.
6. Utilizar um LLM local para selecionar os melhores momentos.
7. Gerar clipes de aproximadamente um minuto.
8. Validar os arquivos produzidos.
9. Enviar os clipes pelo Telegram.
10. Registrar o resultado e o estado do processamento.

O projeto deverá priorizar modularidade, execução local, baixo custo operacional, confiabilidade, facilidade de manutenção e possibilidade de expansão.

## 2. PRINCÍPIOS ARQUITETURAIS

- O n8n será responsável exclusivamente pela orquestração dos workflows.
- O Python será responsável pela lógica de processamento de mídia.
- O LLM local será responsável pela análise semântica da transcrição e seleção dos melhores momentos.
- O FFmpeg será responsável pelos cortes e pela exportação dos vídeos.
- O Telegram será a interface de entrada, acompanhamento e entrega dos resultados.
- O processamento pesado deverá ocorrer em segundo plano.
- Cada processamento deverá possuir um identificador único.
- Os resultados intermediários deverão ser persistidos para evitar processamento desnecessário após falhas.
- As configurações deverão ser centralizadas e não deverão ficar espalhadas pelo código.
- As integrações deverão ser implementadas por meio de interfaces ou serviços desacoplados, facilitando a substituição de tecnologias.
- Nenhum segredo, token ou chave de API deverá ser armazenado diretamente no código-fonte.

## 3. STACK TECNOLÓGICA

Utilizar inicialmente as seguintes tecnologias:

- Linguagem: Python 3.
- API: FastAPI.
- Orquestração: n8n.
- Interface: Telegram Bot API.
- Download: yt-dlp.
- Transcrição: faster-whisper.
- Inteligência artificial: LLM local acessível por API compatível com OpenAI, como llama.cpp ou LM Studio.
- Processamento de vídeo: FFmpeg.
- Persistência inicial: SQLite.
- Armazenamento de arquivos: sistema de arquivos local.
- Testes: pytest.
- Controle de versão: Git.
- Empacotamento: Docker e Docker Compose quando compatíveis com o ambiente de execução e os requisitos de GPU.

As tecnologias deverão ser utilizadas de acordo com suas responsabilidades, sem duplicar funcionalidades desnecessariamente.

A implementação inicial deverá priorizar o funcionamento local. Caso seja necessário acessar o sistema remotamente, deverão ser consideradas as limitações de conectividade, segurança e acesso aos arquivos.

## 4. ARQUITETURA GERAL

O sistema deverá ser organizado em quatro componentes principais.

### 4.1. Telegram Bot

Responsabilidades:

- Receber links enviados pelo usuário.
- Validar comandos.
- Informar o início do processamento.
- Informar o progresso das etapas.
- Notificar erros.
- Enviar os vídeos gerados.
- Disponibilizar comandos básicos de consulta e cancelamento.

### 4.2. n8n

Responsabilidades:

- Receber eventos do Telegram.
- Validar e encaminhar solicitações.
- Criar e acompanhar trabalhos.
- Chamar a API Python.
- Consultar o estado dos trabalhos.
- Enviar notificações.
- Entregar os arquivos pelo Telegram.
- Tratar falhas e executar novas tentativas quando apropriado.

O n8n não deverá implementar diretamente a lógica de download, transcrição, seleção de trechos ou edição dos vídeos.

### 4.3. API Python

Responsabilidades:

- Disponibilizar endpoints HTTP.
- Gerenciar trabalhos de processamento.
- Executar as etapas de mídia.
- Integrar-se ao transcritor e ao LLM local.
- Validar os intervalos selecionados.
- Gerar os clipes.
- Persistir estados, metadados e resultados.
- Disponibilizar os resultados para o n8n.

### 4.4. LLM local

Responsabilidades:

- Analisar a transcrição.
- Identificar trechos relevantes.
- Avaliar a capacidade de cada trecho funcionar isoladamente.
- Sugerir timestamps correspondentes aos segmentos da transcrição.
- Retornar títulos, justificativas e pontuações de relevância.
- Produzir saída estruturada em JSON.

O LLM não deverá executar os cortes diretamente nem ter autoridade para criar timestamps sem correspondência com os dados reais da transcrição.

## 5. FLUXO COMPLETO DE PROCESSAMENTO

O fluxo deverá seguir esta sequência:

1. O usuário envia uma URL pelo Telegram.
2. O Telegram Trigger do n8n recebe a mensagem.
3. O n8n verifica se o remetente está autorizado.
4. O n8n valida o formato básico da URL.
5. O n8n envia uma mensagem confirmando o recebimento.
6. O n8n solicita à API Python a criação de um trabalho.
7. A API cria um registro persistente com um identificador único.
8. O serviço de download obtém o vídeo e seus metadados.
9. O serviço de áudio extrai o áudio necessário para transcrição.
10. O faster-whisper gera a transcrição com timestamps.
11. A transcrição é armazenada em formato estruturado.
12. O serviço de seleção envia a transcrição ao LLM local.
13. O LLM retorna os candidatos a cortes.
14. O Python valida e consolida os candidatos.
15. O FFmpeg gera os clipes.
16. O sistema verifica a integridade e a duração dos arquivos.
17. O trabalho é marcado como concluído.
18. O n8n recebe ou consulta o resultado.
19. O bot envia os clipes pelo Telegram.
20. O n8n envia um resumo final da execução.

Se uma etapa falhar, o sistema deverá registrar o erro e preservar os dados já produzidos sempre que possível.

## 6. ESTRUTURA INICIAL DE DIRETÓRIOS

Criar uma estrutura semelhante à seguinte:

video-clips-ai/
    app/
        api/
            routes_jobs.py
            routes_clips.py
            routes_health.py
        models/
            job.py
            transcript.py
            clip.py
        schemas/
            job_schemas.py
            clip_schemas.py
        services/
            download_service.py
            audio_service.py
            transcription_service.py
            clip_selection_service.py
            clipping_service.py
        infrastructure/
            llm_client.py
            ffmpeg_client.py
            database.py
            storage.py
        config.py
        main.py
    tests/
        unit/
        integration/
        fixtures/
    workflows/
        README.md
    storage/
    .env.example
    .gitignore
    requirements.txt
    Dockerfile
    docker-compose.yml
    README.md

A estrutura poderá ser ajustada conforme as necessidades reais de implementação, desde que as responsabilidades permaneçam separadas.

Não criar arquivos vazios apenas para preencher a estrutura. Cada módulo deverá possuir uma responsabilidade clara e ser criado quando necessário.

O diretório storage deverá conter os arquivos de processamento e não deverá ser versionado pelo Git.

O arquivo .env deverá ser ignorado pelo Git. Somente o .env.example deverá ser versionado, sem credenciais reais.

## 7. FASES DE DESENVOLVIMENTO

O projeto deverá ser desenvolvido incrementalmente. Implementar e validar uma fase antes de avançar para a próxima.

### FASE 1 — FUNDAÇÃO

Objetivos:

- Criar o projeto Python.
- Configurar o ambiente de desenvolvimento.
- Criar o ambiente virtual.
- Instalar e verificar as dependências.
- Configurar o FastAPI.
- Configurar o sistema de logs.
- Criar a configuração centralizada.
- Verificar a disponibilidade do FFmpeg.
- Verificar a conectividade com o endpoint do LLM local.
- Criar o endpoint GET /health.
- Configurar o Git e o .gitignore.
- Criar o README inicial.

Critérios de aceite:

- A aplicação inicia corretamente.
- O endpoint de saúde responde.
- Dependências ausentes são identificadas com mensagens claras.
- As configurações podem ser modificadas sem alterar o código-fonte.
- Nenhuma credencial real é armazenada no repositório.

### FASE 2 — DOWNLOAD E PREPARAÇÃO

Objetivos:

- Implementar o serviço de download utilizando yt-dlp.
- Validar URLs e hosts permitidos.
- Obter metadados do vídeo.
- Registrar título, duração e identificador da origem.
- Extrair o áudio com FFmpeg.
- Criar diretórios específicos para cada trabalho.
- Tratar erros de rede, formatos indisponíveis e falta de espaço.
- Impedir acesso arbitrário a arquivos ou recursos internos por meio de URLs não confiáveis.

Critérios de aceite:

- Um vídeo autorizado pode ser baixado.
- O áudio pode ser extraído.
- Os metadados são persistidos.
- Os arquivos são associados ao trabalho correto.
- Erros são registrados sem interromper indevidamente o serviço.

### FASE 3 — TRANSCRIÇÃO

Objetivos:

- Integrar o faster-whisper.
- Permitir configuração do modelo de transcrição.
- Detectar ou configurar o idioma.
- Gerar segmentos contendo início, fim e texto.
- Salvar a transcrição em JSON.
- Validar a ordem e os limites temporais dos segmentos.
- Tratar vídeos sem fala e falhas de processamento.
- Permitir reutilizar a transcrição sem baixar ou transcrever novamente.

Formato sugerido:

{
  "language": "pt",
  "segments": [
    {
      "start": 0.0,
      "end": 4.25,
      "text": "Exemplo de texto transcrito."
    }
  ]
}

Critérios de aceite:

- A transcrição é salva em formato válido.
- Os timestamps correspondem ao áudio de origem.
- Os segmentos são ordenados.
- O resultado pode ser recuperado independentemente do serviço de transcrição.

### FASE 4 — SELEÇÃO DE MOMENTOS COM IA

Objetivos:

- Implementar o cliente do LLM local.
- Configurar URL, modelo, timeout e parâmetros de inferência.
- Criar um prompt especializado em seleção de momentos para vídeos curtos.
- Implementar a divisão de transcrições longas em blocos.
- Preservar o contexto temporal entre os blocos.
- Consolidar candidatos de diferentes blocos.
- Validar a saída JSON.
- Rejeitar intervalos inválidos.
- Eliminar duplicações e sobreposições excessivas.
- Registrar os resultados da análise.

Critérios de avaliação dos candidatos:

- Qualidade do gancho inicial.
- Relevância do conteúdo.
- Clareza da mensagem.
- Capacidade de compreensão sem o vídeo completo.
- Existência de começo, desenvolvimento e conclusão.
- Potencial de interesse para o público.
- Adequação à duração configurada.

Formato sugerido:

{
  "clips": [
    {
      "start": 125.4,
      "end": 183.7,
      "title": "Título do clipe",
      "reason": "Justificativa da seleção",
      "hook": "Resumo do gancho inicial",
      "score": 0.92
    }
  ]
}

Os valores são ilustrativos.

O serviço deverá verificar se os tempos estão dentro da duração real do vídeo, se a duração do intervalo é válida e se os tempos correspondem à transcrição.

O campo score será uma pontuação heurística, não uma probabilidade comprovada de viralização.

Se o LLM retornar uma resposta inválida, implementar uma nova tentativa limitada e, em seguida, registrar a falha.

Critério de aceite:

- A análise retorna candidatos válidos.
- Os timestamps são derivados dos dados reais.
- O processamento não depende de texto livre não validado.
- Transcrições extensas podem ser processadas sem exceder desnecessariamente o contexto do modelo.

### FASE 5 — GERAÇÃO DOS CLIPES

Objetivos:

- Implementar o serviço de corte com FFmpeg.
- Receber candidatos validados.
- Gerar arquivos MP4.
- Manter o formato original do vídeo na primeira versão.
- Permitir configuração da duração mínima, máxima e desejada.
- Validar duração, integridade e presença de áudio.
- Registrar os caminhos dos arquivos.
- Evitar duplicação de arquivos em novas tentativas.
- Tratar falhas por clipe individualmente.

Configuração inicial sugerida:

- Quantidade máxima: 5 clipes.
- Duração desejada: 60 segundos.
- Duração mínima: 45 segundos.
- Duração máxima: 65 segundos.
- Formato de saída: MP4.
- Proporção: original.
- Processamento: um trabalho por vez inicialmente.

Os parâmetros deverão ser configuráveis.

A duração dos cortes deverá respeitar os limites definidos. Não criar conteúdo artificial para completar um clipe.

Utilizar parâmetros de FFmpeg adequados para manter a sincronização de áudio e vídeo. Priorizar precisão dos cortes quando a recodificação for necessária.

Critérios de aceite:

- Os vídeos são reproduzíveis.
- A duração está dentro dos limites.
- O áudio permanece sincronizado.
- Os arquivos são associados aos candidatos correspondentes.
- Uma falha em um clipe não apaga os resultados válidos dos demais.

### FASE 6 — API DE PROCESSAMENTO

Implementar os seguintes endpoints:

GET /health

Verifica a disponibilidade da aplicação e de suas dependências essenciais.

POST /jobs

Cria um novo trabalho e retorna seu identificador.

GET /jobs/{job_id}

Consulta o estado e a etapa atual.

POST /jobs/{job_id}/retry

Solicita a repetição de uma etapa recuperável.

POST /jobs/{job_id}/cancel

Solicita o cancelamento do trabalho.

GET /jobs/{job_id}/clips

Lista os clipes gerados.

GET /jobs/{job_id}/clips/{clip_id}

Retorna os metadados de um clipe.

Exemplo de requisição:

{
  "source_url": "https://www.youtube.com/watch?v=EXEMPLO",
  "options": {
    "max_clips": 5,
    "target_duration_seconds": 60,
    "min_duration_seconds": 45,
    "max_duration_seconds": 65,
    "output_format": "original"
  }
}

Exemplo de resposta:

{
  "job_id": "job_123",
  "status": "queued",
  "message": "Processamento registrado"
}

Os exemplos são contratos iniciais e poderão ser refinados durante a implementação.

A criação do trabalho deverá retornar rapidamente. O processamento de mídia não deverá bloquear a requisição HTTP até sua conclusão.

A API deverá validar entradas, limitar o tamanho das requisições e proteger os endpoints contra acessos não autorizados.

### FASE 7 — PERSISTÊNCIA E GERENCIAMENTO DE ESTADOS

Utilizar SQLite na primeira versão.

Cada trabalho deverá registrar, no mínimo:

- Identificador único.
- URL de origem.
- Identificador do usuário do Telegram.
- Estado atual.
- Etapa atual.
- Data de criação.
- Data de início.
- Data de conclusão.
- Número de tentativas.
- Metadados do vídeo.
- Caminhos dos arquivos intermediários.
- Caminhos dos clipes.
- Mensagens de erro.
- Configurações utilizadas.

Estados sugeridos:

- QUEUED
- DOWNLOADING
- TRANSCRIBING
- ANALYZING
- CUTTING
- COMPLETED
- FAILED
- CANCELLED

O sistema deverá validar transições de estado e impedir que um trabalho marcado como concluído seja processado novamente por engano.

Persistir os estados em banco de dados, e não somente na memória do processo.

### FASE 8 — INTEGRAÇÃO COM N8N E TELEGRAM

Criar um bot do Telegram e configurar as credenciais por meio de variáveis de ambiente ou do gerenciador de credenciais do n8n.

Implementar três workflows.

WORKFLOW A — RECEBIMENTO

1. Telegram Trigger recebe a mensagem.
2. Validar usuário autorizado.
3. Extrair e validar a URL.
4. Enviar mensagem de confirmação.
5. Registrar o trabalho.
6. Chamar POST /jobs.
7. Guardar o job_id para acompanhamento.

WORKFLOW B — ACOMPANHAMENTO E ENTREGA

1. Consultar GET /jobs/{job_id}.
2. Verificar o estado.
3. Aguardar e consultar novamente enquanto estiver em andamento.
4. Aplicar timeout máximo e limite de tentativas.
5. Quando concluído, consultar os clipes.
6. Enviar os arquivos pelo Telegram.
7. Enviar um resumo final.
8. Notificar falhas quando necessário.

WORKFLOW C — ERROS

1. Capturar falhas das execuções do n8n.
2. Registrar o trabalho e a etapa afetada.
3. Classificar o erro como recuperável ou definitivo.
4. Repetir somente as operações que possam ser repetidas com segurança.
5. Notificar o usuário.
6. Preservar os arquivos válidos já produzidos.

O workflow não deverá permanecer aguardando indefinidamente.

A integração deverá considerar os limites de tamanho de arquivos da Bot API utilizada. Quando um clipe não puder ser enviado diretamente, implementar uma alternativa segura, como disponibilizar um link temporário para download.

Se o n8n estiver em outro computador ou servidor, configurar comunicação segura com a API Python. Não presumir que localhost de um serviço representa o mesmo host dos demais.

### FASE 9 — TESTES

Utilizar pytest.

Criar testes unitários para:

- Validação de URLs.
- Validação de timestamps.
- Validação do JSON retornado pelo LLM.
- Cálculo da duração dos cortes.
- Transições de estado.
- Tratamento de falhas.
- Regras de seleção e remoção de duplicações.

Criar testes de integração para:

- Download de vídeo de teste autorizado.
- Extração de áudio.
- Transcrição.
- Comunicação com o LLM local.
- Geração de clipes.
- Persistência dos trabalhos.
- Endpoints da API.

Criar testes do fluxo completo, incluindo a integração com o Telegram e o n8n, utilizando mocks quando não for apropriado executar serviços externos.

Não depender de acesso à internet ou de um modelo real em todos os testes automatizados.

### FASE 10 — OTIMIZAÇÃO E CONFIABILIDADE

Objetivos:

- Medir o tempo de execução de cada etapa.
- Registrar o consumo de recursos quando possível.
- Implementar limpeza configurável de arquivos temporários.
- Recuperar trabalhos interrompidos.
- Limitar a concorrência.
- Evitar download e transcrição repetidos.
- Implementar timeouts e novas tentativas limitadas.
- Avaliar a precisão dos cortes.
- Validar o comportamento em vídeos longos.
- Documentar instalação, configuração e solução de problemas.

A concorrência inicial deverá ser limitada a um trabalho por vez. Só permitir paralelismo após avaliar consumo de memória, VRAM, CPU e armazenamento.

## 8. FUNCIONALIDADES DO BOT

Implementar inicialmente:

/start

Apresenta o bot e explica como enviar uma URL.

/status

Consulta os trabalhos em andamento do usuário.

/cancelar

Solicita o cancelamento de um trabalho.

/config

Poderá ser implementado posteriormente para configurar quantidade e duração dos clipes.

O envio de uma URL válida deverá ser suficiente para iniciar o fluxo padrão.

O bot deverá aceitar apenas usuários autorizados na primeira versão.

## 9. REQUISITOS NÃO FUNCIONAIS

Segurança:

- Validar URLs e restringir os hosts permitidos.
- Evitar SSRF e acesso a endereços internos por meio de URLs controladas pelo usuário.
- Não expor a API Python publicamente sem autenticação.
- Não registrar tokens ou segredos nos logs.
- Restringir o acesso aos arquivos produzidos.
- Respeitar direitos autorais, permissões e termos aplicáveis às fontes dos vídeos.

Confiabilidade:

- Persistir estados.
- Registrar erros com contexto suficiente para diagnóstico.
- Preservar resultados intermediários válidos.
- Limitar novas tentativas.
- Permitir recuperação após reinicialização.

Manutenibilidade:

- Separar regras de negócio, infraestrutura e API.
- Utilizar tipagem quando apropriado.
- Criar funções pequenas e testáveis.
- Documentar decisões técnicas relevantes.
- Evitar dependência direta entre os serviços de mídia e o n8n.

Desempenho:

- Executar inicialmente um trabalho por vez.
- Evitar carregamentos desnecessários de arquivos grandes em memória.
- Configurar timeouts.
- Registrar métricas de tempo.
- Considerar o consumo de GPU e CPU.

## 10. FORA DO ESCOPO DO MVP

Não implementar inicialmente:

- Interface web completa.
- Publicação automática em redes sociais.
- Sistema de contas de usuários.
- Pagamentos ou assinaturas.
- Geração automática de títulos e hashtags avançados.
- Reenquadramento vertical inteligente.
- Legendas estilizadas.
- Edição visual avançada.
- Processamento paralelo de vários vídeos.
- Treinamento ou fine-tuning de modelos.

Essas funcionalidades deverão ser avaliadas após a validação do fluxo principal.

## 11. CRITÉRIOS FINAIS DE ACEITE

O MVP será considerado concluído quando:

1. Um usuário autorizado enviar uma URL válida pelo Telegram.
2. O n8n iniciar o processamento automaticamente.
3. O sistema baixar um vídeo autorizado.
4. O áudio for transcrito com timestamps válidos.
5. O LLM local selecionar momentos coerentes.
6. O sistema validar os intervalos selecionados.
7. O FFmpeg produzir clipes MP4 dentro dos limites de duração configurados.
8. Os clipes forem enviados pelo Telegram ou disponibilizados por um mecanismo seguro de entrega.
9. O trabalho tiver seu estado e resultados persistidos.
10. Falhas forem registradas e comunicadas.
11. O sistema puder ser reiniciado sem perder o histórico persistido dos trabalhos.
12. Os testes automatizados essenciais forem executados com sucesso.
13. A documentação permitir configurar e executar o projeto em um ambiente compatível.

## 12. ORDEM OBRIGATÓRIA DE IMPLEMENTAÇÃO

Desenvolver na seguinte ordem:

1. Fundação e configuração.
2. Download e preparação de mídia.
3. Transcrição.
4. Seleção dos melhores momentos pelo LLM.
5. Geração de clipes.
6. API e persistência.
7. Integração com n8n.
8. Integração com Telegram.
9. Testes de ponta a ponta.
10. Otimização e documentação final.

É permitido ajustar a ordem de tarefas internas quando houver uma dependência técnica real, mas não avançar prematuramente para funcionalidades fora do escopo.

## 13. INSTRUÇÕES PARA A IA DE DESENVOLVIMENTO

Atue como engenheiro de software sênior responsável pela implementação deste projeto.

Antes de alterar arquivos:

1. Inspecione o ambiente e o repositório existente.
2. Identifique tecnologias e funcionalidades já presentes.
3. Verifique quais dependências estão instaladas.
4. Identifique incompatibilidades e decisões que precisam ser confirmadas.
5. Apresente um resumo da implementação planejada para a próxima fase.

Durante o desenvolvimento:

- Trabalhe por fases pequenas e verificáveis.
- Não implemente todas as fases em uma única operação.
- Implemente apenas a fase atual e suas dependências imediatas.
- Crie testes para as funcionalidades desenvolvidas.
- Execute os testes relevantes após cada alteração.
- Não substitua implementações funcionais sem necessidade.
- Não invente resultados de testes.
- Não deixe operações críticas sem tratamento de erros.
- Não use dados fictícios em produção.
- Não armazene segredos no código.
- Não adicione dependências desnecessárias.
- Documente decisões técnicas relevantes.
- Preserve compatibilidade com o ambiente local de execução.
- Informe os arquivos criados ou alterados e os comandos necessários para executar e testar o projeto.

Ao concluir cada fase:

1. Apresente um resumo do que foi implementado.
2. Liste os arquivos modificados.
3. Informe os testes executados e seus resultados reais.
4. Registre limitações ou problemas pendentes.
5. Compare a implementação com os critérios de aceite.
6. Aguarde autorização para iniciar a próxima fase.

## 14. PRIMEIRA TAREFA

Comece exclusivamente pela FASE 1 — FUNDAÇÃO DO PROJETO.

Não implemente ainda o download, a transcrição, a análise pelo LLM, os cortes ou os workflows do n8n.

Primeiro inspecione o ambiente existente, confirme as condições de execução e identifique eventuais decisões bloqueantes.

Depois implemente a fundação, o endpoint de saúde, a configuração centralizada, os logs, a verificação das dependências e os testes iniciais.

Ao finalizar, apresente o resultado e aguarde autorização para prosseguir para a FASE 2.